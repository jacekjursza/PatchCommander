"""
Procesor dla klas Python.
"""
from rich.console import Console
# Zmieniamy import dekoratora na import z właściwego modułu
from ..decorator import register_processor
from .base import PythonProcessor
from ...models import PatchOperation, PatchResult
console = Console()

@register_processor(priority=10)
class PythonClassProcessor(PythonProcessor):
    """
    Procesor obsługujący operacje na klasach Python.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Sprawdza czy procesor może obsłużyć operację.

        Args:
            operation: Operacja do sprawdzenia

        Returns:
            bool: True jeśli to operacja na klasie Python
        """
        return super().can_handle(operation) and operation.attributes.get('target_type') == 'class'

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Przetwarza operację na klasie Python.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
        """
        class_name = operation.attributes.get('class_name')
        if not class_name:
            operation.add_error('Brak nazwy klasy')
            return
        console.print(f'[blue]PythonClassProcessor: Przetwarzanie klasy {class_name}[/blue]')
        if not result.current_content:
            result.current_content = operation.content
            console.print(f'[green]Utworzono nowy plik z klasą {class_name}[/green]')
            return
        parser = self._get_parser()
        tree = parser.parse(result.current_content)
        classes = tree.find_classes()
        target_class = None
        for cls in classes:
            for child in cls.get_children():
                if child.get_type() == 'identifier' and child.get_text() == class_name:
                    target_class = cls
                    break
            if target_class:
                break
        if target_class:
            start_byte = target_class.ts_node.start_byte
            end_byte = target_class.ts_node.end_byte
            new_content = result.current_content[:start_byte] + operation.content + result.current_content[end_byte:]
            result.current_content = new_content
            console.print(f'[green]Zaktualizowano klasę {class_name}[/green]')
        else:
            separator = '\n\n' if result.current_content and (not result.current_content.endswith('\n\n')) else ''
            result.current_content = result.current_content + separator + operation.content
            console.print(f'[green]Dodano nową klasę {class_name}[/green]')