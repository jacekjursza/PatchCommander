"""
Preprocessor do usuwania znaczników Markdown dla bloków kodu.
"""
import re
from rich.console import Console
from ...processor_base import PreProcessor
from ...models import PatchOperation

console = Console()

class MarkdownCodeBlockCleaner(PreProcessor):
    """
    Preprocessor, który usuwa znaczniki Markdown bloków kodu (``` i ```python, ```css itp.)
    z zawartości tagów.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Sprawdza czy preprocessor może obsłużyć daną operację.

        Args:
            operation: Operacja do sprawdzenia

        Returns:
            bool: True dla wszystkich operacji, które mają zawartość tekstową
        """
        # Przetwarzamy wszystkie operacje, które mają jakąś zawartość
        return operation.content is not None and len(operation.content) > 0

    def process(self, operation: PatchOperation) -> None:
        """
        Usuwa znaczniki Markdown dla bloków kodu z zawartości operacji.

        Args:
            operation: Operacja do przetworzenia
        """
        if not self.can_handle(operation):
            return

        content = operation.content

        # Nie robimy nic, jeśli nie ma zawartości
        if not content or len(content.strip()) == 0:
            return

        # Dzielimy zawartość na linie
        lines = content.splitlines()
        if len(lines) < 2:
            # Za mało linii, aby zawierać bloki kodu Markdown
            return

        # Sprawdzamy pierwszą linię - czy zawiera marker otwarcia bloku kodu
        first_line = lines[0].strip()
        first_line_matches = re.match(r'^```\w*$', first_line)

        # Sprawdzamy ostatnią linię - czy zawiera marker zamknięcia bloku kodu
        last_line = lines[-1].strip()
        last_line_matches = re.match(r'^```$', last_line)

        # Jeśli zarówno pierwszy jak i ostatni wiersz pasują do wzorca, usuwamy je
        if first_line_matches and last_line_matches:
            console.print("[blue]Znaleziono blok kodu Markdown - usuwam znaczniki[/blue]")
            # Usuwamy pierwszy i ostatni wiersz
            lines = lines[1:-1]
            operation.content = '\n'.join(lines)
            return

        # Obsługa przypadku, gdy tylko pierwsza linia to znacznik otwarcia
        if first_line_matches:
            console.print("[blue]Znaleziono początek bloku kodu Markdown - usuwam znacznik[/blue]")
            lines = lines[1:]
            operation.content = '\n'.join(lines)
            return

        # Obsługa przypadku, gdy tylko ostatnia linia to znacznik zamknięcia
        if last_line_matches:
            console.print("[blue]Znaleziono koniec bloku kodu Markdown - usuwam znacznik[/blue]")
            lines = lines[:-1]
            operation.content = '\n'.join(lines)
            return

        # Sprawdzmy, czy są jakieś znaczniki w środku zawartości
        # To może być trudniejsze, bo musimy odróżnić prawdziwe znaczniki Markdown
        # od kodu, który może zawierać podobne wzorce

        # Ten fragment jest bardziej eksperymentalny - będziemy usuwać tylko wyraźne
        # bloki kodu Markdown, które są całymi liniami
        modified_lines = []
        skip_next = False

        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            # Sprawdzamy, czy linia to otwarcie bloku kodu Markdown
            if re.match(r'^\s*```\w*\s*$', line):
                # Sprawdźmy, czy jest to tylko fragment większego bloku kodu
                # Jeśli to prawdziwy znacznik Markdown, to kilka linii dalej
                # powinien być znacznik zamykający
                found_closing = False
                for j in range(i+1, min(i+20, len(lines))):
                    if re.match(r'^\s*```\s*$', lines[j]):
                        found_closing = True
                        skip_next = True
                        break

                if found_closing:
                    console.print("[blue]Znaleziono wewnętrzny blok kodu Markdown - usuwam znaczniki[/blue]")
                    continue

            modified_lines.append(line)

        if len(modified_lines) != len(lines):
            operation.content = '\n'.join(modified_lines)