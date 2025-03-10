"""
Processor for Python class methods using the diff-match-patch library.
"""
import re
from rich.console import Console
from ..decorator import register_processor
from .method_base import BasePythonMethodProcessor
from .base_diff_match_patch import BaseDiffMatchPatchProcessor, DMP_AVAILABLE
from ...models import PatchOperation, PatchResult
console = Console()

@register_processor(priority=5)
class DiffMatchPatchPythonMethodProcessor(BasePythonMethodProcessor, BaseDiffMatchPatchProcessor):
    """
    Processor handling operations on Python class methods using diff-match-patch.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        return DMP_AVAILABLE and super().can_handle(operation)

    def _format_new_method(self, method_content: str, base_indent: str) -> str:
        """
        Formats a new method, preserving the original indentation from the input content.
        """
        return self._format_with_indent(method_content, base_indent)

    def _process_method(self, operation: PatchOperation, result: PatchResult, class_name: str, method_name: str) -> None:
        """
        Processes a method, updating or adding it to the class.
        """
        if not DMP_AVAILABLE:
            raise ValueError('The diff-match-patch library is not available')
        console.print('[blue]Using replace mode (merge mode is disabled)[/blue]')
        try:
            class_pattern = f'(^|\\n)class\\s+{re.escape(class_name)}\\s*(\\([^)]*\\))?\\s*:'
            class_match = re.search(class_pattern, result.current_content)
            if not class_match:
                raise ValueError(f'Class {class_name} not found')
            class_end = class_match.end()
            next_class_match = re.search('(^|\\n)class\\s+', result.current_content[class_end:])
            if next_class_match:
                class_content = result.current_content[class_end:class_end + next_class_match.start()]
            else:
                class_content = result.current_content[class_end:]
            
            # Improved method pattern to include decorators
            # Look for decorators or method definition
            method_with_decorators_pattern = f'(\\n+)([ \\t]*)((?:@[^\\n]+\\n+[ \\t]*)*)(def\\s+{re.escape(method_name)}\\s*\\([^)]*\\)\\s*(->\\s*[^:]+)?\\s*:)'
            method_match = re.search(method_with_decorators_pattern, class_content)
            
            if not method_match:
                console.print(f'[yellow]Method {method_name} does not exist - adding a new one[/yellow]')
                base_indent = self._detect_base_indent(class_content)
                new_method_content = operation.content.strip()
                formatted_method = self._format_new_method(new_method_content, base_indent)
                if next_class_match:
                    insert_pos = class_end + next_class_match.start()
                else:
                    insert_pos = len(result.current_content)
                prefix = result.current_content[:insert_pos]
                if prefix and (not prefix.endswith('\n\n')):
                    if prefix.endswith('\n'):
                        prefix += '\n'
                    else:
                        prefix += '\n\n'
                suffix = result.current_content[insert_pos:]
                new_code = prefix + formatted_method + '\n\n' + suffix
                result.current_content = new_code
                console.print(f'[green]Added new method {class_name}.{method_name}[/green]')
                return
                
            # We found the method with potential decorators
            console.print(f'[green]Replacing entire method {method_name}[/green]')
            method_indent = method_match.group(2)
            decorators_text = method_match.group(3) or ''  # Captured decorators text
            method_def_text = method_match.group(4)        # Captured method definition
            
            # Calculate actual start position (before decorators)
            method_start_rel = method_match.start()
            method_start_abs = class_end + method_start_rel
            
            # Find the end of the method
            method_def_rel = method_match.end()
            rest_of_code = class_content[method_def_rel:]
            method_end_rel = method_def_rel
            
            # Scan through lines to find where method ends
            for (i, line) in enumerate(rest_of_code.splitlines(keepends=True)):
                if i == 0:
                    method_end_rel += len(line)
                    continue
                if not line.strip():
                    method_end_rel += len(line)
                    continue
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= len(method_indent) and (not line.lstrip().startswith('@')):
                    break
                method_end_rel += len(line)
                
            method_end_abs = class_end + method_end_rel
            
            # Capture newlines before the method (including decorators)
            original_newlines_before = method_match.group(1)
            
            # Format the new method content
            new_method_content = operation.content.strip()
            formatted_method = self._format_new_method(new_method_content, method_indent)
            
            # Construct the new code
            prefix = result.current_content[:method_start_abs]
            suffix = result.current_content[method_end_abs:]
            
            # Ensure we have proper spacing after the method
            if not suffix.startswith('\n\n') and suffix.strip():
                if suffix.startswith('\n'):
                    suffix = '\n' + suffix  # Add one more newline
                else:
                    suffix = '\n\n' + suffix  # Add two newlines
                    
            new_code = prefix + original_newlines_before + formatted_method + suffix
            result.current_content = new_code
            console.print(f'[green]Replaced the entire method {class_name}.{method_name}[/green]')
            
        except Exception as e:
            console.print(f'[red]Error in DiffMatchPatchPythonMethodProcessor: {str(e)}[/red]')
            import traceback
            console.print(f'[red]{traceback.format_exc()}[/red]')
            raise ValueError(f'Error processing method: {str(e)}')