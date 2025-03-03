import textwrap
from typing import Optional

from patchcommander.core.changes import change_manager
from patchcommander.core.confirmations import confirm_simple_action, confirm_and_apply_change
from patchcommander.core.languages import get_language_for_file
from patchcommander.core.console import console
from patchcommander.core.tag_processors.base import TagProcessor
from patchcommander.parsers.javascript_parser import JavaScriptParser
from patchcommander.parsers.python_parser import PythonParser


class FunctionTagProcessor(TagProcessor):
    """Processor for FUNCTION tags."""

    def process(self) -> bool:
        """
        Process a FUNCTION tag by updating or adding a standalone function to a file.

        Returns:
            bool: True if processing was successful, False otherwise
        """
        file_path = self.tag.get_attribute('path')
        content = self.tag.content or ''
        file_path = self._sanitize_path(file_path)
        if not file_path:
            console.print("[bold red]FUNCTION tag missing 'path' attribute.[/bold red]")
            return False
        if not self._validate_file_path(file_path):
            return False
        func_code = textwrap.dedent(content)
        original_code = change_manager.get_file_content(file_path)
        if not original_code and (not confirm_simple_action(f"File '{file_path}' not found. Create new file?")):
            console.print('[yellow]Skipping FUNCTION tag.[/yellow]')
            return False
        try:
            function_name = self._extract_function_name(func_code)
            if not function_name:
                console.print('[bold red]Could not extract function name from FUNCTION tag content.[/bold red]')
                return False
            if not original_code:
                change_manager.in_memory_files[file_path] = func_code
                return confirm_and_apply_change(file_path, func_code, f"Create new file with function '{function_name}'", change_manager.pending_changes)
            try:
                language = get_language_for_file(file_path)
            except ValueError:
                console.print(f"[bold red]Couldn't determine language for file: {file_path}[/bold red]")
                return False
            if language == 'python':
                parser = PythonParser()
            elif language == 'javascript':
                parser = JavaScriptParser()
            else:
                console.print(f'[bold red]Unsupported language: {language}[/bold red]')
                return False
            tree = parser.parse(original_code)
            functions = tree.find_functions()
            target_function = None
            for func in functions:
                for child in func.get_children():
                    if (child.get_type() == 'identifier' or child.get_type() == 'name') and child.get_text() == function_name:
                        target_function = func
                        break
                if target_function:
                    break
            new_tree = parser.parse(func_code)
            new_functions = new_tree.find_functions()
            if not new_functions:
                console.print('[bold red]No function definition found in FUNCTION tag content.[/bold red]')
                return False
            new_function = new_functions[0]
            if target_function:
                replaced_code = original_code[:target_function.ts_node.start_byte] + new_function.get_text() + original_code[target_function.ts_node.end_byte:]
                description = f"Update function '{function_name}'"
            else:
                if original_code.strip():
                    separator = '\n\n' if not original_code.endswith('\n\n') else '\n'
                else:
                    separator = ''
                replaced_code = original_code + separator + new_function.get_text()
                description = f"Add function '{function_name}'"
            change_manager.in_memory_files[file_path] = replaced_code
            return confirm_and_apply_change(file_path, replaced_code, description, change_manager.pending_changes)
        except Exception as e:
            console.print(f'[bold red]Error processing FUNCTION tag: {e}[/bold red]')
            return False

    def _extract_function_name(self, func_code: str) -> Optional[str]:
        """
        Extract function name from code.

        Args:
            func_code: Function code

        Returns:
            Function name or None
        """
        import re
        match = re.search('def\\s+([a-zA-Z_][a-zA-Z0-9_]*)', func_code)
        if match:
            return match.group(1)
        match = re.search('function\\s+([a-zA-Z_][a-zA-Z0-9_]*)', func_code)
        if match:
            return match.group(1)
        return None
