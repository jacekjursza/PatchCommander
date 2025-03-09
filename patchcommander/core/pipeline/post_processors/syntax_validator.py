"""
Post-procesor dla walidacji składni.
"""
import os

from patchcommander.core.pipeline import PatchResult, PostProcessor


class SyntaxValidator(PostProcessor):
    """
    Post-procesor walidujący składnię zmodyfikowanych plików.
    """

    def can_handle(self, operation):
        """
        Ten post-procesor działa na poziomie PatchResult, więc ta metoda nie jest używana.
        """
        return False

    def process(self, result: PatchResult) -> None:
        """
        Waliduje składnię dla zmodyfikowanego pliku.

        Args:
            result: Wynik do zwalidowania
        """
        # Pomijamy pliki oznaczone do usunięcia (pusta zawartość)
        if not result.current_content:
            return

        # Sprawdzamy rozszerzenie pliku
        _, ext = os.path.splitext(result.path)
        file_extension = ext.lower()[1:] if ext else ""

        # Walidacja dla języka Python
        if file_extension == "py":
            self._validate_python_syntax(result)

        # Tutaj można dodać walidację dla innych języków (np. JavaScript)

    def _validate_python_syntax(self, result: PatchResult) -> None:
        """
        Waliduje składnię dla kodu Python.

        Args:
            result: Wynik do zwalidowania
        """
        try:
            compile(result.current_content, result.path, "exec")
        except SyntaxError as e:
            error_message = f"Błąd składni Python w {result.path} wiersz {e.lineno}, pozycja {e.offset}: {e.msg}"
            result.add_error(error_message)

            # Opcjonalnie można przywrócić oryginalną zawartość
            # result.current_content = result.original_content