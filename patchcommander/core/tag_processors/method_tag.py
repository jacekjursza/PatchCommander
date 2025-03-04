import re
import textwrap
from patchcommander.core.changes import change_manager
from patchcommander.core.confirmations import confirm_simple_action, confirm_and_apply_change
from patchcommander.core.languages import get_language_for_file
from patchcommander.core.console import console
from patchcommander.core.tag_processors.base import TagProcessor
from patchcommander.operations import OperationFactory
from patchcommander.parsers.javascript_parser import JavaScriptParser

class MethodTagProcessor(TagProcessor):
    """Processor for METHOD tags."""

    def process(self) -> bool:
        """
        Process a METHOD tag by updating or adding a method to a class.

        Returns:
            bool: True if processing was successful, False otherwise
        """
        file_path = self.tag.get_attribute('path')
        class_name = self.tag.get_attribute('class')
        content = self.tag.content or ''
        file_path = self._sanitize_path(file_path)
        if not file_path or not class_name:
            console.print("[bold red]METHOD tag missing 'path' or 'class' attribute.[/bold red]")
            return False
        original_code = change_manager.get_file_content(file_path)
        if not original_code and (not confirm_simple_action(f"File '{file_path}' not found. Create new file with class '{class_name}'?")):
            console.print('[yellow]Skipping METHOD tag.[/yellow]')
            return False
        try:
            try:
                language = get_language_for_file(file_path)
            except ValueError:
                console.print(f"[bold red]Couldn't determine language for file: {file_path}[/bold red]")
                return False
            method_code = textwrap.dedent(content)
            has_trailing_newline = method_code.endswith('\n')
            method_code = method_code.strip('\n')
            if not original_code:
                if language == 'python':
                    class_template = f"class {class_name}:\n    {method_code.replace(chr(10), chr(10) + '    ')}"
                else:
                    method_indented = method_code.replace(chr(10), chr(10) + '    ')
                    class_template = f'class {class_name} {{\n    {method_indented}\n}}'
                change_manager.in_memory_files[file_path] = class_template
                return confirm_and_apply_change(file_path, class_template, f"Create new class '{class_name}' with method", change_manager.pending_changes)
            method_name = self._extract_method_name(method_code)
            if language == 'python':
                lines = original_code.split('\n')
                class_start_line = -1
                class_indent = ''
                method_start_line = -1
                method_end_line = -1
                for (i, line) in enumerate(lines):
                    if re.search(f'class\\s+{re.escape(class_name)}\\s*[:(]', line):
                        class_start_line = i
                        class_indent = self._get_indentation(line)
                        break
                if class_start_line == -1:
                    console.print(f"[bold red]Class '{class_name}' not found in file {file_path}[/bold red]")
                    return False

                method_indent = class_indent + '    '

                # Find method and any decorators preceding it
                for i in range(class_start_line, len(lines)):
                    line = lines[i]
                    line_indent = self._get_indentation(line)

                    # Exit if we're outside the class body
                    if i > class_start_line and line.strip() and (len(line_indent) <= len(class_indent)):
                        break

                    # Find method definition (with or without async)
                    if re.search(f'{method_indent}(?:async\\s+)?def\\s+{re.escape(method_name)}\\s*\\(', line):
                        # Look backward for decorators
                        decorator_start_line = i
                        for j in range(i-1, class_start_line, -1):
                            decorator_line = lines[j]
                            decorator_indent = self._get_indentation(decorator_line)
                            # If we find a decorator with the right indentation, include it
                            if len(decorator_indent) == len(method_indent) and decorator_line.strip().startswith('@'):
                                decorator_start_line = j
                            else:
                                break

                        method_start_line = decorator_start_line

                        # Find method end
                        for j in range(i + 1, len(lines)):
                            next_line = lines[j]
                            next_line_indent = self._get_indentation(next_line)
                            if next_line.strip() and len(next_line_indent) <= len(method_indent):
                                method_end_line = j - 1
                                break

                        if method_end_line == -1:
                            method_end_line = len(lines) - 1

                        trailing_empty_lines = 0
                        for j in range(method_end_line, min(method_end_line + 3, len(lines))):
                            if not lines[j].strip():
                                trailing_empty_lines += 1
                            else:
                                break
                        method_end_line += trailing_empty_lines - 1
                        break

                method_lines = method_code.split('\n')
                indented_method_lines = [method_indent + line if line.strip() else line for line in method_lines]

                if has_trailing_newline or (method_start_line != -1 and method_end_line + 1 < len(lines) and (not lines[method_end_line + 1].strip())):
                    indented_method_lines.append('')

                indented_method = '\n'.join(indented_method_lines)

                if method_start_line != -1:
                    new_lines = lines[:method_start_line] + indented_method_lines + lines[method_end_line + 1:]
                    new_code = '\n'.join(new_lines)
                    description = f"Update method '{method_name}' in class '{class_name}'"
                else:
                    insert_position = class_start_line + 1

                    for i in range(class_start_line + 1, len(lines)):
                        if i < len(lines) - 1 and lines[i].strip() and (len(self._get_indentation(lines[i])) <= len(class_indent)):
                            break
                        if lines[i].strip() and lines[i].startswith(method_indent):
                            insert_position = i + 1
                            while insert_position < len(lines) and (not lines[insert_position].strip()):
                                insert_position += 1

                    if insert_position > 0 and lines[insert_position - 1].strip():
                        indented_method_lines.insert(0, '')

                    new_lines = lines[:insert_position] + indented_method_lines + lines[insert_position:]
                    new_code = '\n'.join(new_lines)
                    description = f"Add method '{method_name}' to class '{class_name}'"

                change_manager.in_memory_files[file_path] = new_code
                return confirm_and_apply_change(file_path, new_code, description, change_manager.pending_changes)
            else:
                parser = JavaScriptParser() if language == 'javascript' else None
                if not parser:
                    console.print(f'[bold red]Unsupported language: {language}[/bold red]')
                    return False

                operation = OperationFactory.create_operation('add_method', {'path': file_path, 'class': class_name})
                context = {'method_code': method_code, 'dry_run': True}

                if operation.execute(context):
                    updated_content = context.get('new_content')
                    if not updated_content:
                        console.print('[bold red]Error: Failed to generate updated content.[/bold red]')
                        return False

                    description = f"Add/Update method '{method_name}' in class '{class_name}'"
                    confirmed = confirm_and_apply_change(file_path, updated_content, description, change_manager.pending_changes)
                    return confirmed

                return False
        except Exception as e:
            console.print(f'[bold red]Error processing METHOD tag: {e}[/bold red]')
            return False

    def _extract_method_name(self, method_code: str) -> str:
        """
        Extract method name from code.

        Args:
            method_code: Method code

        Returns:
            Method name or "unknown_method"
        """
        import re
        # Check for both async and regular method definitions
        match = re.search('(?:async\\s+)?def\\s+([a-zA-Z_][a-zA-Z0-9_]*)', method_code)
        if match:
            return match.group(1)
        match = re.search('([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(', method_code)
        if match:
            return match.group(1)
        return 'unknown_method'

    def _get_indentation(self, line: str) -> str:
        """
        Get the indentation from a line of code.

        Args:
            line: Line of code

        Returns:
            String containing the indentation characters
        """
        indent = ''
        for char in line:
            if char in ' \t':
                indent += char
            else:
                break
        return indent