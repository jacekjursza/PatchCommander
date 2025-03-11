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
        Formatuje nową metodę z odpowiednim wcięciem, zachowując dekoratory i docstringi.

        Args:
            method_content: Treść metody do sformatowania
            base_indent: Podstawowe wcięcie dla metody

        Returns:
            Sformatowana treść metody z właściwym wcięciem
        """
        # Podziel treść metody na linie
        lines = method_content.strip().splitlines()
        if not lines:
            return ""

        # Wykryj dekoratory
        decorators = []
        start_idx = 0

        # Zbieraj kolejne linie dekoratorów
        while start_idx < len(lines) and lines[start_idx].strip().startswith("@"):
            decorators.append(lines[start_idx].strip())
            start_idx += 1

        # Jeśli nie znaleziono więcej linii po dekoratorach, zwróć tylko sformatowane dekoratory
        if start_idx >= len(lines):
            return "\n".join(f"{base_indent}{decorator}" for decorator in decorators)

        # Pierwsza linia definicji metody po dekoratorach
        method_def = lines[start_idx].strip()
        formatted_lines = [f"{base_indent}{method_def}"]

        # Formatuj resztę ciała metody z odpowiednim wcięciem
        body_indent = base_indent + "    "  # Standardowe wcięcie dla ciała metody

        for line in lines[start_idx + 1 :]:
            # Puste linie pozostają puste
            if not line.strip():
                formatted_lines.append("")
                continue

            # Dodaj wcięcie dla ciała metody
            formatted_lines.append(f"{body_indent}{line.strip()}")

        # Najpierw połącz sformatowane ciało metody
        formatted_body = "\n".join(formatted_lines)

        # Następnie dodaj dekoratory, jeśli istnieją
        if decorators:
            formatted_decorators = "\n".join(
                f"{base_indent}{decorator}" for decorator in decorators
            )
            return f"{formatted_decorators}\n{formatted_body}"
        else:
            return formatted_body


def _process_method(
    self,
    operation: PatchOperation,
    result: PatchResult,
    class_name: str,
    method_name: str,
) -> None:
    """
    Przetwarza metodę, aktualizując ją lub dodając do klasy.
    """
    from .base_diff_match_patch import DMP_AVAILABLE

    if not DMP_AVAILABLE:
        raise ValueError("The diff-match-patch library is not available")

    console.print("[blue]Using replace mode for method processing[/blue]")

    try:
        # Znajdź klasę
        class_pattern = (
            f"(^|\\n)class\\s+{re.escape(class_name)}\\s*(\\([^)]*\\))?\\s*:"
        )
        class_match = re.search(class_pattern, result.current_content)

        if not class_match:
            raise ValueError(f"Class {class_name} not found")

        class_end = class_match.end()

        # Znajdź następną klasę (jeśli istnieje)
        next_class_match = re.search(
            "(^|\\n)class\\s+", result.current_content[class_end:]
        )

        if next_class_match:
            class_content = result.current_content[
                class_end : class_end + next_class_match.start()
            ]
        else:
            class_content = result.current_content[class_end:]

        # Wzorzec do znajdowania metody (z obsługą dekoratorów)
        method_pattern = f"(\\n+)([ \\t]*)((?:@[^\\n]+\\n+[ \\t]*)*)(def\\s+{re.escape(method_name)}\\s*\\([^)]*\\)\\s*(->\\s*[^:]+)?\\s*:)"

        method_match = re.search(method_pattern, class_content)

        if not method_match:
            # Metoda nie istnieje, dodaj nową
            console.print(
                f"[yellow]Method {method_name} does not exist in class {class_name} - adding a new one[/yellow]"
            )

            # Wykryj wcięcie na podstawie zawartości klasy
            base_indent = self._detect_base_indent(class_content)

            # Usuń zbędne białe znaki z początku i końca zawartości metody
            new_method_content = operation.content.strip()

            # Sformatuj nową metodę zachowując dekoratory i docstringi
            formatted_method = self._format_new_method(new_method_content, base_indent)

            # Określ miejsce wstawienia
            if next_class_match:
                insert_pos = class_end + next_class_match.start()
            else:
                insert_pos = len(result.current_content)

            # Przygotuj części zawartości
            prefix = result.current_content[:insert_pos]

            # Zapewnij właściwe znaki końca linii przed nową metodą
            if prefix and not prefix.endswith("\n\n"):
                if prefix.endswith("\n"):
                    prefix += "\n"
                else:
                    prefix += "\n\n"

            suffix = result.current_content[insert_pos:]

            # Połącz wszystko
            new_code = prefix + formatted_method + "\n\n" + suffix
            result.current_content = new_code

            console.print(f"[green]Added new method {class_name}.{method_name}[/green]")
            return

        # Metoda istnieje - zastąp ją
        console.print(
            f"[green]Replacing entire method {method_name} in class {class_name}[/green]"
        )

        # Pobierz szczegóły metody
        method_indent = method_match.group(2)
        method_start_rel = method_match.start()
        method_start_abs = class_end + method_start_rel
        method_def_rel = method_match.end()

        # Znajdź koniec metody
        rest_of_code = class_content[method_def_rel:]
        method_end_rel = method_def_rel

        # Przeanalizuj każdą linię aby określić granicę metody
        for i, line in enumerate(rest_of_code.splitlines(keepends=True)):
            if i == 0:  # Pierwsza linia po definicji (należy do metody)
                method_end_rel += len(line)
                continue

            if not line.strip():  # Puste linie należą do metody
                method_end_rel += len(line)
                continue

            # Sprawdź, czy linia ma mniejsze lub równe wcięcie co metoda
            current_indent = len(line) - len(line.lstrip())

            # Jeśli wcięcie jest mniejsze lub równe i nie jest to dekorator
            # to jest to początek kolejnej metody/atrybutu
            if current_indent <= len(method_indent) and not line.lstrip().startswith(
                "@"
            ):
                break

            # Linia nadal należy do metody
            method_end_rel += len(line)

        # Oblicz absolutną pozycję końca metody
        method_end_abs = class_end + method_end_rel

        # Zachowaj oryginalne znaki nowej linii przed metodą
        original_newlines_before = method_match.group(1)

        # Sformatuj nową metodę
        new_method_content = operation.content.strip()
        formatted_method = self._format_new_method(new_method_content, method_indent)

        # Przygotuj części kodu
        prefix = result.current_content[:method_start_abs]
        suffix = result.current_content[method_end_abs:]

        # Zapewnij właściwe znaki końca linii po metodzie
        if not suffix.startswith("\n\n") and suffix.strip():
            if suffix.startswith("\n"):
                suffix = "\n" + suffix
            else:
                suffix = "\n\n" + suffix

        # Połącz wszystko
        new_code = prefix + original_newlines_before + formatted_method + suffix
        result.current_content = new_code

        console.print(
            f"[green]Replaced the entire method {class_name}.{method_name}[/green]"
        )

    except Exception as e:
        console.print(
            f"[red]Error in DiffMatchPatchPythonMethodProcessor: {str(e)}[/red]"
        )
        import traceback

        console.print(f"[red]{traceback.format_exc()}[/red]")
        raise ValueError(f"Error processing method: {str(e)}")