"""
Processor for Python class methods using the diff-match-patch library.
Refactored to use the common BasePythonElementProcessor.
"""
import re
from rich.console import Console
from ..decorator import register_processor
from .method_base import BasePythonMethodProcessor
from .base_python_element_processor import BasePythonElementProcessor
from ...models import PatchOperation, PatchResult
console = Console()

@register_processor(priority=5)
class DiffMatchPatchPythonMethodProcessor(BasePythonMethodProcessor, BasePythonElementProcessor):
    """
    Processor handling operations on Python class methods using diff-match-patch.
    Uses the common BasePythonElementProcessor for shared functionality.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.

        Args:
            operation: Operation to check

        Returns:
            bool: True if it's a Python method operation and diff-match-patch is available
        """
        from .base_diff_match_patch import DMP_AVAILABLE
        return DMP_AVAILABLE and super().can_handle(operation)

    def _format_new_method(self, method_content: str, base_indent: str) -> str:
        """
        Formats a new method with the correct indentation, preserving decorators and docstrings.

        Args:
            method_content: The content of the method to format
            base_indent: The base indentation for the method

        Returns:
            The formatted method content with proper indentation
        """
        # Sprawdź, czy zawartość nie zawiera deklaracji klasy zamiast metody
        class_match = re.search(
            "class\\s+(\\w+)\\s*(?:\\([^)]*\\))?\\s*:", method_content
        )
        if class_match:
            class_name = class_match.group(1)
            console.print(
                f"[yellow]Found class declaration in method content: {class_name}[/yellow]"
            )
            class_content = method_content[class_match.end() :]
            method_content = class_content.strip()

        # Podziel zawartość na linie
        lines = method_content.strip().splitlines()
        if not lines:
            return ""

        # Znajdź wszystkie dekoratory przed definicją metody
        decorators = []
        start_idx = 0
        while start_idx < len(lines) and lines[start_idx].strip().startswith("@"):
            decorators.append(lines[start_idx].strip())
            start_idx += 1

        # Sprawdź czy mamy tylko dekoratory bez definicji metody
        if start_idx >= len(lines):
            return "\n".join((f"{base_indent}{decorator}" for decorator in decorators))

        # Znajdź linię z definicją metody
        method_def = lines[start_idx].strip()

        # Sprawdź, czy to setter dla property
        is_property_setter = False
        for decorator in decorators:
            if re.match(r"@\w+\.setter", decorator):
                is_property_setter = True
                break

        formatted_lines = [f"{base_indent}{method_def}"]
        body_indent = base_indent + "    "

        # Określ domyślne wcięcie dla treści metody
        original_base_indent = None
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if line.strip():
                original_base_indent = len(line) - len(line.lstrip())
                break

        if original_base_indent is None:
            original_base_indent = 4

        # Przetwórz treść metody linijka po linijce
        i = start_idx + 1
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                formatted_lines.append("")
                i += 1
                continue

            stripped_line = line.strip()

            # Sprawdź, czy nie wkraczamy już na kolejną metodę lub klasę
            if (
                re.match("^\\s*def\\s+", stripped_line)
                or re.match("^\\s*class\\s+", stripped_line)
                or re.match("^\\s*@", stripped_line)
            ) and not line.startswith(" " * original_base_indent):
                break

            # Dostosuj wcięcie dla treści metody
            current_indent = len(line) - len(line.lstrip())
            if current_indent >= original_base_indent:
                relative_indent = current_indent - original_base_indent
                new_indent = body_indent + " " * relative_indent
                formatted_lines.append(f"{new_indent}{line.lstrip()}")
            else:
                formatted_lines.append(f"{body_indent}{line.lstrip()}")

            i += 1

        # Złącz sformatowane linie w jedną zawartość
        formatted_body = "\n".join(formatted_lines)

        # Dodaj dekoratory na początek, jeśli istnieją
        if decorators:
            formatted_decorators = "\n".join(
                (f"{base_indent}{decorator}" for decorator in decorators)
            )
            return f"{formatted_decorators}\n{formatted_body}"
        else:
            return formatted_body

    def _process_method(self, operation: PatchOperation, result: PatchResult, class_name: str, method_name: str) -> None:
        """
        Processes a method, updating it or adding it to the class.
        """
        from .base_diff_match_patch import DMP_AVAILABLE
        if not DMP_AVAILABLE:
            raise ValueError('The diff-match-patch library is not available')
        console.print('[blue]Using replace mode for method processing[/blue]')
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
            is_property_setter = False
            setter_pattern = None
            new_content_lines = operation.content.strip().splitlines()
            for line in new_content_lines:
                if re.match('^\\s*@\\w+\\.setter\\s*$', line):
                    is_property_setter = True
                    property_match = re.match('^\\s*@(\\w+)\\.setter\\s*$', line)
                    if property_match:
                        property_name = property_match.group(1)
                        setter_pattern = f'@{property_name}\\.setter'
                    break
            if is_property_setter and setter_pattern:
                method_pattern = f'(\\n+)([ \\t]*){setter_pattern}\\s*\\n+[ \\t]*def\\s+{re.escape(method_name)}\\s*\\('
            else:
                method_pattern = f'(\\n+)([ \\t]*)((?:@[^\\n]+\\n+[ \\t]*)*)((?:async\\s+)?def\\s+{re.escape(method_name)}\\s*\\([^)]*\\)\\s*(->\\s*[^:]+)?\\s*:)'
            method_match = re.search(method_pattern, class_content)
            if not method_match:
                console.print(f'[yellow]Method {method_name} does not exist in class {class_name} - adding a new one[/yellow]')
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
            console.print(f'[green]Replacing entire method {method_name} in class {class_name}[/green]')
            method_indent = method_match.group(2)
            method_start_rel = method_match.start()
            method_start_abs = class_end + method_start_rel
            if is_property_setter:
                def_match = re.search(f'def\\s+{re.escape(method_name)}\\s*\\(', class_content[method_start_rel:])
                if def_match:
                    method_def_rel = method_start_rel + def_match.end()
                else:
                    method_def_rel = method_match.end()
            else:
                method_def_rel = method_match.end()
            rest_of_code = class_content[method_def_rel:]
            method_end_rel = method_def_rel
            in_decorator = False
            for (i, line) in enumerate(rest_of_code.splitlines(keepends=True)):
                if i == 0:
                    method_end_rel += len(line)
                    continue
                if not line.strip():
                    method_end_rel += len(line)
                    continue
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= len(method_indent):
                    if line.lstrip().startswith('@'):
                        break
                    if re.match('^\\s*((?:async\\s+)?def|class)\\s+', line):
                        break
                    if current_indent < len(method_indent):
                        break
                method_end_rel += len(line)
            method_end_abs = class_end + method_end_rel
            original_newlines_before = method_match.group(1)
            new_method_content = operation.content.strip()
            formatted_method = self._format_new_method(new_method_content, method_indent)
            prefix = result.current_content[:method_start_abs]
            suffix = result.current_content[method_end_abs:]
            if suffix.strip() and (not suffix.startswith('\n\n')):
                if suffix.startswith('\n'):
                    suffix = '\n' + suffix
                else:
                    suffix = '\n\n' + suffix
            new_code = prefix + original_newlines_before + formatted_method + suffix
            result.current_content = new_code
            console.print(f'[green]Replaced the entire method {class_name}.{method_name}[/green]')
        except Exception as e:
            console.print(f'[red]Error in DiffMatchPatchPythonMethodProcessor: {str(e)}[/red]')
            import traceback
            console.print(f'[red]{traceback.format_exc()}[/red]')
            raise ValueError(f'Error processing method: {str(e)}')