"""
Procesor dla metod klas Python używający biblioteki diff-match-patch.
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
    Procesor obsługujący operacje na metodach klas Python za pomocą diff-match-patch.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        return DMP_AVAILABLE and super().can_handle(operation)

    def _format_new_method(self, method_content: str, base_indent: str) -> str:
        """
        Formatuje nową metodę, zachowując oryginalne wcięcie z wejściowej zawartości.
        """
        return self._format_with_indent(method_content, base_indent)

    def _process_method(self, operation: PatchOperation, result: PatchResult, class_name: str, method_name: str) -> None:
        """
        Przetwarza metodę, aktualizując lub dodając ją do klasy.
        """
        if not DMP_AVAILABLE:
            raise ValueError('Biblioteka diff-match-patch nie jest dostępna')

        # Sprawdzamy tryb operacji - domyślnie 'replace'
        mode = operation.attributes.get('mode', 'replace')
        console.print(f'[blue]Tryb operacji: {mode}[/blue]')

        try:
            class_pattern = f'(^|\\n)class\\s+{re.escape(class_name)}\\s*(\\([^)]*\\))?\\s*:'
            class_match = re.search(class_pattern, result.current_content)
            if not class_match:
                raise ValueError(f'Nie znaleziono klasy {class_name}')
            class_end = class_match.end()
            next_class_match = re.search('(^|\\n)class\\s+', result.current_content[class_end:])
            if next_class_match:
                class_content = result.current_content[class_end:class_end + next_class_match.start()]
            else:
                class_content = result.current_content[class_end:]

            # Zaktualizowany wzorzec uwzględniający adnotacje typów zwracanych
            method_pattern = f'(\\n+)([ \\t]*)def\\s+{re.escape(method_name)}\\s*\\([^)]*\\)\\s*(->\\s*[^:]+)?\\s*:'
            method_match = re.search(method_pattern, class_content)

            if not method_match:
                console.print(f'[yellow]Metoda {method_name} nie istnieje - dodajemy nową[/yellow]')
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
                console.print(f'[green]Dodano nową metodę {class_name}.{method_name}[/green]')
                return

            # Gdy metoda istnieje i tryb to 'replace', zamieniamy całą metodę
            if mode == 'replace':
                console.print(f'[green]Tryb replace - zastępuję całą metodę {method_name}[/green]')

                # Znajdujemy metodę i jej granice
                method_indent = method_match.group(2)
                method_start_rel = method_match.start()
                method_start_abs = class_end + method_start_rel
                method_def_rel = method_match.end()

                # Znajdujemy koniec metody
                rest_of_code = class_content[method_def_rel:]
                method_end_rel = method_def_rel
                in_method = True
                for (i, line) in enumerate(rest_of_code.splitlines(keepends=True)):
                    if i == 0:  # Pierwsza linia jest częścią deklaracji metody
                        method_end_rel += len(line)
                        continue
                    if not line.strip():  # Pusta linia
                        method_end_rel += len(line)
                        continue
                    # Sprawdzamy czy wyszliśmy z metody
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= len(method_indent) and (not line.lstrip().startswith('@')):
                        break
                    method_end_rel += len(line)

                method_end_abs = class_end + method_end_rel

                # Zachowujemy oryginalne znaki nowej linii przed i po metodzie
                original_newlines_before = method_match.group(1)

                # Formatujemy nową metodę z odpowiednim wcięciem
                new_method_content = operation.content.strip()
                formatted_method = self._format_new_method(new_method_content, method_indent)

                # Konstruujemy nowy kod
                prefix = result.current_content[:method_start_abs]
                suffix = result.current_content[method_end_abs:]

                # Sprawdź czy potrzebujemy dodatkowych znaków nowej linii przed suffix
                original_newlines_after = '\n\n'
                if suffix and not suffix.startswith('\n'):
                    # Jeśli suffix nie zaczyna się od nowej linii, dodajemy dwie
                    console.print(f'[yellow]Brak znaków nowej linii przed następnym elementem - dodaję je[/yellow]')
                    suffix = original_newlines_after + suffix

                new_code = prefix + original_newlines_before + formatted_method + suffix

                result.current_content = new_code
                console.print(f'[green]Zastąpiono całą metodę {class_name}.{method_name}[/green]')
                return

            # Gdy tryb to 'merge' (domyślne zachowanie diff-match-patch)
            console.print(f'[green]Tryb merge - inteligentne łączenie metody {method_name}[/green]')

            # Zaktualizowany wzorzec dla śledzenia wcięcia ciała metody
            original_method_pattern = f'\\n([ \\t]*)def\\s+{re.escape(method_name)}\\s*\\([^)]*\\)\\s*(->\\s*[^:]+)?\\s*:\\s*\\n+([ \\t]+)[^\\n]+'
            original_method_match = re.search(original_method_pattern, class_content)
            original_body_indent = None
            if original_method_match:
                original_body_indent = original_method_match.group(3)  # Zaktualizowany indeks grupy
                console.print(f'[blue]Oryginalne wcięcie ciała metody: {repr(original_body_indent)}[/blue]')

            method_indent = method_match.group(2)
            new_method_content = operation.content.strip()

            if original_body_indent:
                def_line = None
                content_lines = new_method_content.splitlines()
                if content_lines:
                    def_line = content_lines[0]
                body_lines = content_lines[1:] if len(content_lines) > 1 else []
                formatted_lines = [f'{method_indent}{def_line}']
                for line in body_lines:
                    if line.strip():
                        formatted_lines.append(f'{original_body_indent}{line.lstrip()}')
                    else:
                        formatted_lines.append('')
                formatted_method = '\n'.join(formatted_lines)
            else:
                formatted_method = self._format_new_method(new_method_content, method_indent)

            console.print(f'[blue]Sformatowana metoda z wcięciami:[/blue]\n{formatted_method}')
            method_start_rel = method_match.start()
            method_start_abs = class_end + method_start_rel
            method_def_rel = method_match.end()
            method_def_abs = class_end + method_def_rel

            console.print(f'[blue]Względna pozycja początku metody w klasie: {method_start_rel}[/blue]')
            original_newlines_before = method_match.group(1)
            console.print(f'[blue]Oryginalne znaki nowej linii przed metodą: {repr(original_newlines_before)}[/blue]')

            rest_of_code = class_content[method_def_rel:]
            method_body_lines = []
            in_method = True
            method_end_rel = method_def_rel

            for (i, line) in enumerate(rest_of_code.splitlines()):
                line_len = len(line) + 1
                if i == 0:
                    method_end_rel += line_len
                    continue
                if not line.strip():
                    method_body_lines.append(line)
                    method_end_rel += line_len
                    next_lines = rest_of_code[method_end_rel:].splitlines()
                    if next_lines:
                        next_line = next_lines[0]
                        if next_line.strip() and len(next_line) - len(next_line.lstrip()) <= len(method_indent) and (not next_line.lstrip().startswith('@')):
                            in_method = False
                            break
                    continue
                if len(line) - len(line.lstrip()) <= len(method_indent) and (not line.lstrip().startswith('@')):
                    in_method = False
                    break
                method_body_lines.append(line)
                method_end_rel += line_len

            method_end_abs = class_end + method_end_rel
            next_element_match = re.search(f'\\n{method_indent}\\S', rest_of_code)
            original_newlines_after = '\n'
            if next_element_match:
                gap_text = rest_of_code[:next_element_match.start() + 1]
                original_newlines_after = self._normalize_empty_lines(gap_text)

            console.print(f'[blue]Wykryte znaki nowej linii po metodzie: {repr(original_newlines_after)}[/blue]')
            prefix = result.current_content[:method_start_abs]
            suffix = result.current_content[method_end_abs:]

            console.print(f'[blue]Prefix kończy się na: {repr(prefix[-20:] if len(prefix) > 20 else prefix)}[/blue]')
            console.print(f'[blue]Suffix zaczyna się od: {repr(suffix[:20] if len(suffix) > 20 else suffix)}[/blue]')

            new_code = prefix + original_newlines_before + formatted_method + original_newlines_after + suffix
            result.current_content = new_code
            console.print(f'[green]Zaktualizowano metodę {class_name}.{method_name}[/green]')

        except Exception as e:
            console.print(f'[red]Błąd w DiffMatchPatchPythonMethodProcessor: {str(e)}[/red]')
            import traceback
            console.print(f'[red]{traceback.format_exc()}[/red]')
            raise ValueError(f'Błąd przetwarzania metody: {str(e)}')