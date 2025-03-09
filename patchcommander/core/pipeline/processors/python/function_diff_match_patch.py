"""
Python function processor using diff-match-patch.
"""
import re
from rich.console import Console
from ..decorator import register_processor
from .base import PythonProcessor
from .base_diff_match_patch import BaseDiffMatchPatchProcessor, DMP_AVAILABLE
from ...models import PatchOperation, PatchResult
console = Console()

@register_processor(priority=4)
class DiffMatchPatchPythonFunctionProcessor(PythonProcessor, BaseDiffMatchPatchProcessor):
    """
    Processor for Python functions using diff-match-patch.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.

        Args:
            operation: Operation to check

        Returns:
            bool: True if it's a Python function operation and diff-match-patch is available
        """
        return DMP_AVAILABLE and super().can_handle(operation) and (operation.attributes.get('target_type') == 'function')

    def _validate_function_syntax(self, function_code: str) -> bool:
        """
        Checks if the function code has valid syntax.
        """
        try:
            wrapped_code = function_code + '\n    pass'
            compile(wrapped_code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False

    def _find_function_boundaries_robust(self, content: str, function_name: str):
        """
        More robust version of function boundary detection.
        With support for return type annotations.
        """
        # Zaktualizowany wzorzec uwzględniający adnotacje typów zwracanych
        pattern = f'(^|\\n)([ \\t]*)(async\\s+)?def\\s+{re.escape(function_name)}\\s*\\([^)]*\\)\\s*(->\\s*[^:]+)?\\s*:'
        matches = list(re.finditer(pattern, content))
        if not matches:
            return (None, None, None, None)
        match = matches[-1]
        prefix = match.group(1)
        if prefix == '\n':
            function_start = match.start(1)
        else:
            function_start = match.start()
        indent = match.group(2)
        rest_of_content = content[match.end():]
        next_def_pattern = f"(^|\\n)({re.escape(indent)}(class|def)\\s+|{re.escape(indent[:-4] if len(indent) >= 4 else '')}def\\s+|{re.escape(indent[:-4] if len(indent) >= 4 else '')}class\\s+)"
        next_def_match = re.search(next_def_pattern, rest_of_content)
        if next_def_match:
            function_end = match.end() + next_def_match.start()
            if next_def_match.group(1) == '\n':
                function_end += 1
        else:
            function_end = len(content)
        function_content = content[function_start:function_end]
        return (function_start, function_end, function_content, indent)

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Processes a function operation.

        Args:
            operation: Operation to process
            result: Result to update
        """
        function_name = operation.attributes.get('function_name')
        if not function_name:
            operation.add_error('Missing function_name attribute')
            return

        # Ignorujemy atrybut mode - zawsze używamy trybu replace
        console.print(f'[blue]DiffMatchPatchPythonFunctionProcessor: Processing function {function_name} using replace mode (merge mode is disabled)[/blue]')

        if not result.current_content:
            result.current_content = operation.content
            console.print(f'[green]Created new file with function {function_name}[/green]')
            return

        try:
            boundaries = self._find_function_boundaries_robust(result.current_content, function_name)
            if boundaries[0] is None:
                console.print(f'[yellow]Function {function_name} not found - adding new function[/yellow]')
                new_content = operation.content.strip()
                if result.current_content.endswith('\n\n'):
                    separator = ''
                elif result.current_content.endswith('\n'):
                    separator = '\n'
                else:
                    separator = '\n\n'
                result.current_content = result.current_content + separator + new_content + '\n\n'
                console.print(f'[green]Added new function {function_name}[/green]')
                return

            (function_start, function_end, original_function, indent) = boundaries
            console.print(f'[green]Found function {function_name} at position {function_start}-{function_end}[/green]')

            # Zawsze używamy trybu replace
            empty_lines_before = 0
            pos = function_start - 1
            while pos >= 0 and result.current_content[pos] == '\n':
                empty_lines_before += 1
                pos -= 1

            empty_lines_after = 0
            pos = function_end
            while pos < len(result.current_content) and result.current_content[pos] == '\n':
                empty_lines_after += 1
                pos += 1

            console.print(f'[blue]Empty lines before function: {empty_lines_before}[/blue]')
            console.print(f'[blue]Empty lines after function: {empty_lines_after}[/blue]')

            normalized_lines_before = '\n' * max(2, min(empty_lines_before, self.MAX_EMPTY_LINES))
            normalized_lines_after = '\n' * max(2, min(empty_lines_after, self.MAX_EMPTY_LINES))

            new_function = self._format_with_indent(operation.content, indent)
            console.print(f'[blue]Formatted function with indentation:[/blue]\n{new_function}')

            prefix = result.current_content[:function_start - empty_lines_before]
            suffix = result.current_content[function_end + empty_lines_after:]

            if prefix and (not prefix.endswith('\n')):
                prefix += '\n'

            if suffix and (not suffix.startswith('\n')):
                console.print(f'[yellow]Detected missing newline before next element in suffix - adding them[/yellow]')
                suffix = '\n\n' + suffix

            new_code = prefix + normalized_lines_before + new_function + normalized_lines_after + suffix
            result.current_content = new_code
            console.print(f'[green]Replaced function {function_name}[/green]')

        except Exception as e:
            console.print(f'[red]Error in DiffMatchPatchPythonFunctionProcessor: {str(e)}[/red]')
            import traceback
            console.print(f'[red]{traceback.format_exc()}[/red]')
            operation.add_error(f'Error processing function: {str(e)}')