"""
Bazowa klasa dla procesorów metod Python.
"""
from rich.console import Console

from . import PythonProcessor
from ...models import PatchOperation, PatchResult

console = Console()

class BasePythonMethodProcessor(PythonProcessor):
    """
    Bazowa klasa dla procesorów obsługujących operacje na metodach klas Python.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Sprawdza czy procesor może obsłużyć operację.

        Args:
            operation: Operacja do sprawdzenia

        Returns:
            bool: True jeśli to operacja na metodzie Python
        """
        return (super().can_handle(operation) and
                operation.attributes.get('target_type') == 'method')

    def _handle_empty_file(self, operation: PatchOperation, result: PatchResult, class_name: str, method_name: str) -> bool:
        """
        Obsługuje przypadek pustego pliku - tworzy nową klasę z metodą.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
            class_name: Nazwa klasy
            method_name: Nazwa metody

        Returns:
            bool: True, jeśli plik był pusty i został obsłużony
        """
        if not result.current_content:
            method_content = operation.content.strip()
            method_lines = method_content.split('\n')
            indented_method = method_lines[0] + '\n' + '\n'.join([f'    {line}' for line in method_lines[1:]])
            result.current_content = f'class {class_name}:\n    {indented_method}'
            console.print(f"[green]Utworzono nowy plik z klasą {class_name} i metodą {method_name}[/green]")
            return True
        return False

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Przetwarza operację na metodzie Python.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
        """
        class_name = operation.attributes.get('class_name')
        method_name = operation.attributes.get('method_name')

        if not class_name or not method_name:
            operation.add_error('Brak nazwy klasy lub metody')
            return

        console.print(f"[blue]{self.__class__.__name__}: Przetwarzanie metody {class_name}.{method_name}[/blue]")

        # Obsługa pustego pliku
        if self._handle_empty_file(operation, result, class_name, method_name):
            return

        # Implementacja specyficzna dla konkretnej strategii - do nadpisania w klasach potomnych
        self._process_method(operation, result, class_name, method_name)

    def _process_method(self, operation: PatchOperation, result: PatchResult, class_name: str, method_name: str) -> None:
        """
        Metoda do nadpisania w klasach potomnych - konkretna implementacja strategii.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
            class_name: Nazwa klasy
            method_name: Nazwa metody
        """
        raise NotImplementedError("Ta metoda musi być zaimplementowana w klasie potomnej")