"""
Pre-processor that corrects XPaths for methods incorrectly formatted as functions.

This pre-processor identifies when an LLM has incorrectly formatted a class method
as a standalone function in the xpath (using "method_name" instead of "ClassName.method_name").
It detects this by looking for the 'self' parameter in the function definition and
then searches the target file to find which class the method belongs to.
"""
import re
import os
from rich.console import Console
from ...processor_base import PreProcessor
from ...models import PatchOperation
from patchcommander.parsers.python_parser import PythonParser

console = Console()

class XPathMethodCorrector(PreProcessor):
    """
    Pre-processor that corrects XPaths for methods incorrectly formatted as functions.
    
    When LLMs generate an xpath for a class method but omit the class name part
    (using "method_name" instead of "ClassName.method_name"), this pre-processor
    detects it by looking for 'self' parameter and corrects the xpath.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the pre-processor can handle the operation.

        Args:
            operation: Operation to check

        Returns:
            bool: True if it's a Python function operation without a dot in the xpath
        """
        return (operation.name == 'FILE' and 
                operation.file_extension == 'py' and 
                operation.xpath is not None and 
                '.' not in operation.xpath and 
                operation.attributes.get('target_type') == 'function')

    def process(self, operation: PatchOperation) -> None:
        """
        Corrects the xpath if the function is actually a class method.

        Args:
            operation: Operation to process
        """
        if not operation.content:
            return
            
        # Check if this is actually a method by looking for 'self' parameter
        func_def_match = re.search(r'^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*self\b', 
                                  operation.content, re.MULTILINE)
        
        if not func_def_match:
            # Not a method (no self parameter)
            return
            
        method_name = func_def_match.group(1)
        function_name = operation.xpath
        if method_name != function_name:
            # Method name in content doesn't match xpath, something is off
            console.print(f"[yellow]Warning: Method name '{method_name}' doesn't match xpath '{function_name}'[/yellow]")
            return
            
        console.print(f"[blue]Found potential class method '{method_name}' with 'self' parameter but xpath doesn't include class name[/blue]")
        
        # Now we need to find which class this method belongs to
        if not os.path.exists(operation.path):
            console.print(f"[yellow]File '{operation.path}' doesn't exist, can't determine class name[/yellow]")
            return
            
        try:
            with open(operation.path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
            # First try to find using tree-sitter parser
            class_name = self._find_class_with_tree_sitter(file_content, method_name)
            
            # If tree-sitter approach fails, try regex-based approach as a fallback
            if not class_name:
                class_name = self._find_class_with_regex(file_content, method_name)
                
            if class_name:
                console.print(f"[green]Found method '{method_name}' in class '{class_name}'[/green]")
                
                # Update the operation with all necessary attributes
                operation.xpath = f"{class_name}.{method_name}"
                operation.attributes['target_type'] = 'method'
                operation.attributes['class_name'] = class_name
                operation.attributes['method_name'] = method_name
                
                # Clear processors history to allow re-selection
                operation.processors = []
                
                console.print(f"[green]Updated xpath to '{operation.xpath}' and cleared processor history[/green]")
                return
            else:
                console.print(f"[yellow]Could not find a class containing method '{method_name}'[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error while trying to determine class name: {str(e)}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    def _find_class_with_tree_sitter(self, file_content: str, method_name: str) -> str:
        """
        Find a class containing the method using tree-sitter parser.
        
        Args:
            file_content: Content of the file
            method_name: Name of the method to find
            
        Returns:
            str: Name of the class containing the method, or empty string if not found
        """
        try:
            # Use PythonParser to find classes and their methods
            parser = PythonParser()
            tree = parser.parse(file_content)
            classes = tree.find_classes()
            
            console.print(f"[blue]Found {len(classes)} classes in the file[/blue]")
            
            for cls in classes:
                class_name = None
                for child in cls.get_children():
                    if child.get_type() == 'identifier':
                        class_name = child.get_text()
                        break
                        
                if not class_name:
                    console.print("[yellow]Found a class without a name[/yellow]")
                    continue
                    
                console.print(f"[blue]Checking class '{class_name}'[/blue]")
                
                # Check if this class contains the method by manually examining the content
                class_content = cls.get_text()
                method_pattern = r'(?:^|\n)\s*(?:@\w+(?:\(.*?\))?\s*)*\s*def\s+' + re.escape(method_name) + r'\s*\(\s*self\b'
                method_match = re.search(method_pattern, class_content, re.MULTILINE)
                
                if method_match:
                    console.print(f"[green]Found method '{method_name}' in class '{class_name}' using content search[/green]")
                    return class_name
                    
                # Also try tree-sitter's find_methods
                methods = tree.find_methods(cls)
                console.print(f"[blue]Found {len(methods)} methods in class '{class_name}'[/blue]")
                
                for method in methods:
                    # Dump method content for debugging
                    method_content = method.get_text()
                    console.print(f"[blue]Checking method: {method_content[:50]}...[/blue]")
                    
                    method_identifier = None
                    for child in method.get_children():
                        if child.get_type() == 'identifier':
                            method_identifier = child.get_text()
                            console.print(f"[blue]Found method identifier: {method_identifier}[/blue]")
                            break
                            
                    if method_identifier == method_name:
                        return class_name
                        
            # If we get here, we didn't find the method in any class
            return ""
        except Exception as e:
            console.print(f"[red]Error in tree-sitter approach: {str(e)}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return ""
    
    def _find_class_with_regex(self, file_content: str, method_name: str) -> str:
        """
        Find a class containing the method using regex approach.
        
        Args:
            file_content: Content of the file
            method_name: Name of the method to find
            
        Returns:
            str: Name of the class containing the method, or empty string if not found
        """
        try:
            # Find all class definitions
            class_pattern = r'(?:^|\n)\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\))?:'
            class_matches = list(re.finditer(class_pattern, file_content, re.MULTILINE))
            
            console.print(f"[blue]Found {len(class_matches)} classes using regex[/blue]")
            
            for i, class_match in enumerate(class_matches):
                class_name = class_match.group(1)
                class_start = class_match.start()
                
                # Find the end of this class (start of next class or end of file)
                class_end = len(file_content)
                if i < len(class_matches) - 1:
                    class_end = class_matches[i+1].start()
                    
                class_content = file_content[class_start:class_end]
                
                # Look for method in this class content
                method_pattern = r'(?:^|\n)\s*(?:@\w+(?:\(.*?\))?\s*)*\s*def\s+' + re.escape(method_name) + r'\s*\(\s*self\b'
                if re.search(method_pattern, class_content, re.MULTILINE):
                    console.print(f"[green]Found method '{method_name}' in class '{class_name}' using regex[/green]")
                    return class_name
                    
            return ""
        except Exception as e:
            console.print(f"[red]Error in regex approach: {str(e)}[/red]")
            return ""