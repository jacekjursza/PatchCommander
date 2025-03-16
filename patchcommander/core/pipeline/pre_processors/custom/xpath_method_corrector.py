import re
import os
from rich.console import Console
from ...processor_base import PreProcessor
from ...models import PatchOperation
from patchcommander.core.finder.factory import get_code_finder

console = Console()

class XPathMethodCorrector(PreProcessor):

    def can_handle(self, operation: PatchOperation) -> bool:
        return operation.name == 'FILE' and operation.file_extension == 'py' and (operation.xpath is not None)

    def process(self, operation: PatchOperation) -> None:
        if not operation.content:
            return
            
        # Skip if this is already a method xpath (contains a dot)
        if '.' in operation.xpath:
            return
            
        # If this is a class, no need to process
        if operation.attributes.get('target_type') == 'class':
            return
            
        # If this is already identified as a function but has no "self" parameter, it's likely correct
        if operation.attributes.get('target_type') == 'function':
            self_param_match = re.search('^\\s*(?:async\\s+)?def\\s+\\w+\\s*\\(\\s*self\\b', operation.content, re.MULTILINE)
            if not self_param_match:
                return
            
        # Check if the content looks like a method definition by searching for "self" parameter
        func_def_match = re.search('^\\s*(?:@\\w+)?\\s*(?:async\\s+)?def\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(\\s*self\\b', operation.content, re.MULTILINE)
        if not func_def_match:
            setter_match = re.search('^\\s*@(\\w+)\\.setter\\s*\\n+\\s*def\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(\\s*self\\b', operation.content, re.MULTILINE)
            if not setter_match:
                return
            else:
                property_name = setter_match.group(1)
                method_name = setter_match.group(2)
                if property_name != method_name:
                    console.print(f"[yellow]Warning: Property setter name '{method_name}' doesn't match property name '{property_name}'[/yellow]")
                method_name = setter_match.group(2)
        else:
            method_name = func_def_match.group(1)
            
        function_name = operation.xpath
        if method_name != function_name:
            console.print(f"[yellow]Warning: Method name '{method_name}' doesn't match xpath '{function_name}'[/yellow]")
            return
            
        console.print(f"[blue]Found potential class method '{method_name}' with 'self' parameter but xpath doesn't include class name[/blue]")
        console.print(f"[yellow]Attempting to identify the containing class...[/yellow]")
        
        if not os.path.exists(operation.path):
            console.print(f"[yellow]File '{operation.path}' doesn't exist, can't determine class name[/yellow]")
            return
            
        try:
            with open(operation.path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
            class_name = self._find_class_with_tree_sitter(file_content, method_name)
            if not class_name:
                class_name = self._find_class_with_regex(file_content, method_name)
                
            if class_name:
                console.print(f"[green]Found method '{method_name}' in class '{class_name}'[/green]")
                operation.xpath = f'{class_name}.{method_name}'
                operation.attributes['target_type'] = 'method'
                operation.attributes['class_name'] = class_name
                operation.attributes['method_name'] = method_name
                operation.processors = []
                console.print(f"[green]Updated xpath to '{operation.xpath}' and cleared processor history[/green]")
                return
            else:
                console.print(f"[yellow]Could not find a class containing method '{method_name}'[/yellow]")
                console.print(f"[yellow]This looks like a method but is being processed as a function. This might cause issues.[/yellow]")
                console.print(f"[yellow]Consider specifying the class name in xpath as 'ClassName.{method_name}'[/yellow]")
        except Exception as e:
            console.print(f'[red]Error while trying to determine class name: {str(e)}[/red]')
            import traceback
            console.print(f'[dim]{traceback.format_exc()}[/dim]')

    def _find_class_with_tree_sitter(self, file_content: str, method_name: str) -> str:
        try:
            finder = get_code_finder('python')
            
            # First try to find all classes
            for class_match in re.finditer('class\\s+(\\w+)', file_content):
                class_name = class_match.group(1)
                console.print(f"[blue]Checking class '{class_name}'[/blue]")
                
                # Try direct method finder first
                (start_line, end_line) = finder.find_method(file_content, class_name, method_name)
                if start_line > 0 and end_line > 0:
                    console.print(f"[green]Found method '{method_name}' in class '{class_name}' using finder[/green]")
                    return class_name
                
                # If direct finder failed, try manual search
                (class_start, class_end) = finder.find_class(file_content, class_name)
                if class_start > 0 and class_end > 0:
                    lines = file_content.splitlines()
                    class_content = '\n'.join(lines[class_start - 1:class_end])
                    
                    method_pattern = '(?:^|\\n)\\s*(?:@\\w+(?:\\(.*?\\))?\\s*)*\\s*def\\s+' + re.escape(method_name) + '\\s*\\(\\s*self\\b'
                    if re.search(method_pattern, class_content, re.MULTILINE):
                        console.print(f"[green]Found method '{method_name}' in class '{class_name}' using content search[/green]")
                        return class_name
                        
            return ''
        except Exception as e:
            console.print(f'Error in tree-sitter approach: {str(e)}')
            import traceback
            console.print(f'[dim]{traceback.format_exc()}[/dim]')
            return ''

    def _find_class_with_regex(self, file_content: str, method_name: str) -> str:
        try:
            class_pattern = '(?:^|\\n)\\s*class\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*(?:\\([^)]*\\))?:'
            class_matches = list(re.finditer(class_pattern, file_content, re.MULTILINE))
            console.print(f'[blue]Found {len(class_matches)} classes using regex[/blue]')
            
            for (i, class_match) in enumerate(class_matches):
                class_name = class_match.group(1)
                class_start = class_match.start()
                class_end = len(file_content)
                
                if i < len(class_matches) - 1:
                    class_end = class_matches[i + 1].start()
                    
                class_content = file_content[class_start:class_end]
                
                # Look for method definition with 'self' parameter
                method_pattern = '(?:^|\\n)\\s*(?:@\\w+(?:\\(.*?\\))?\\s*)*\\s*def\\s+' + re.escape(method_name) + '\\s*\\(\\s*self\\b'
                if re.search(method_pattern, class_content, re.MULTILINE):
                    console.print(f"[green]Found method '{method_name}' in class '{class_name}' using regex[/green]")
                    return class_name
                    
            return ''
        except Exception as e:
            console.print(f'Error in regex approach: {str(e)}')
            return ''