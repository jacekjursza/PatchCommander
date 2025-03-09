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

        # Ignorujemy atrybut mode - zawsze używamy trybu replace
        console.print(f'[blue]Używam trybu replace (tryb merge został wyłączony)[/blue]')

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

            # Zawsze używamy trybu replace
            console.print(f'[green]Zastępuję całą metodę {method_name}[/green]')
            method_indent = method_match.group(2)
            method_start_rel = method_match.start()
            method_start_abs = class_end + method_start_rel
            method_def_rel = method_match.end()
            rest_of_code = class_content[method_def_rel:]
            method_end_rel = method_def_rel
            in_method = True

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
            original_newlines_before = method_match.group(1)
            new_method_content = operation.content.strip()
            formatted_method = self._format_new_method(new_method_content, method_indent)

            prefix = result.current_content[:method_start_abs]
            suffix = result.current_content[method_end_abs:]
            original_newlines_after = '\n\n'

            if suffix and (not suffix.startswith('\n')):
                console.print(f'[yellow]Brak znaków nowej linii przed następnym elementem - dodaję je[/yellow]')
                suffix = original_newlines_after + suffix

            new_code = prefix + original_newlines_before + formatted_method + suffix
            result.current_content = new_code
            console.print(f'[green]Zastąpiono całą metodę {class_name}.{method_name}[/green]')

        except Exception as e:
            console.print(f'[red]Błąd w DiffMatchPatchPythonMethodProcessor: {str(e)}[/red]')
            import traceback
            console.print(f'[red]{traceback.format_exc()}[/red]')
            raise ValueError(f'Błąd przetwarzania metody: {str(e)}')