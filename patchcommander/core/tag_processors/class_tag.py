from typing import Optional

from patchcommander.core.changes import change_manager
from patchcommander.core.confirmations import confirm_simple_action, confirm_and_apply_change
from patchcommander.core.languages import get_language_for_file
from patchcommander.core.console import console
from patchcommander.core.tag_processors.base import TagProcessor
from patchcommander.parsers.javascript_parser import JavaScriptParser
from patchcommander.parsers.python_parser import PythonParser


class ClassTagProcessor(TagProcessor):
    """Processor for CLASS tags."""

    def process(self) -> bool:
        """
        Process a CLASS tag by updating or adding a class in the file.

        Returns:
            bool: True if processing was successful, False otherwise
        """
        file_path = self.tag.get_attribute('path')
        class_name = self.tag.get_attribute('class')
        content = self.tag.content or ''
        file_path = self._sanitize_path(file_path)
        if not file_path:
            console.print("[bold red]CLASS tag missing 'path' attribute.[/bold red]")
            return False
        if not class_name:
            inferred = self._infer_class_name(content)
            if inferred:
                class_name = inferred
                console.print(f"[yellow]Inferred class name '{class_name}' from content.[/yellow]")
            else:
                console.print("[bold red]CLASS tag missing 'class' attribute and could not infer it.[/bold red]")
                return False
        original_code = change_manager.get_file_content(file_path)
        if not original_code and (not confirm_simple_action(f"File '{file_path}' not found. Create new file?")):
            console.print(f"[yellow]Skipping CLASS tag for '{class_name}'.[/yellow]")
            return False
        try:
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
            if not original_code:
                replaced_code = content
                change_manager.in_memory_files[file_path] = replaced_code
                return confirm_and_apply_change(file_path, replaced_code, f"Create new class '{class_name}'", change_manager.pending_changes)
            tree = parser.parse(original_code)
            classes = tree.find_classes()
            target_class = None
            for cls in classes:
                for child in cls.get_children():
                    if (child.get_type() == 'identifier' or child.get_type() == 'name') and child.get_text() == class_name:
                        target_class = cls
                        break
                if target_class:
                    break
            new_tree = parser.parse(content)
            new_classes = new_tree.find_classes()
            if not new_classes:
                console.print('[bold red]No class definition found in CLASS tag content.[/bold red]')
                return False
            new_class = new_classes[0]
            if target_class:
                replaced_code = original_code[:target_class.ts_node.start_byte] + new_class.get_text() + original_code[target_class.ts_node.end_byte:]
                description = f"Update class '{class_name}'"
            else:
                if original_code.strip():
                    separator = '\n\n' if not original_code.endswith('\n\n') else '\n'
                else:
                    separator = ''
                replaced_code = original_code + separator + new_class.get_text()
                description = f"Add class '{class_name}'"
            change_manager.in_memory_files[file_path] = replaced_code
            return confirm_and_apply_change(file_path, replaced_code, description, change_manager.pending_changes)
        except Exception as e:
            console.print(f'[bold red]Error processing CLASS tag: {e}[/bold red]')
            return False

    def _infer_class_name(self, content: str) -> Optional[str]:
        """
        Infer class name from content.

        Args:
            content: Class content

        Returns:
            Inferred class name or None
        """
        import re
        match = re.search('class\\s+(\\w+)', content)
        return match.group(1) if match else None
