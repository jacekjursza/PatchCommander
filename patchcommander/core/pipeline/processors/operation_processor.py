"""
Procesor dla operacji OPERATION.
"""
import os
from rich.console import Console
from .. import Processor, PatchOperation, PatchResult
from ....parsers.python_parser import PythonParser
from ....parsers.javascript_parser import JavaScriptParser
console = Console()

# Dodajemy dekorator register_processor
from .decorator import register_processor

@register_processor(priority=10)
class OperationProcessor(Processor):
    """
    Procesor dla tagu OPERATION.
    Obsługuje operacje na plikach, takie jak move_file, delete_file, delete_method.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Sprawdza czy procesor może obsłużyć operację.

        Args:
            operation: Operacja do sprawdzenia

        Returns:
            bool: True jeśli to operacja OPERATION
        """
        return operation.name == 'OPERATION'

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Przetwarza operację OPERATION.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
        """
        action = operation.action
        if not action:
            operation.add_error('Brak akcji dla operacji OPERATION')
            return
        if action == 'move_file':
            self._handle_move_file(operation, result)
        elif action == 'delete_file':
            self._handle_delete_file(operation, result)
        elif action == 'delete_method':
            self._handle_delete_method(operation, result)
        else:
            operation.add_error(f'Nieznana akcja: {action}')

    def _handle_move_file(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Obsługuje operację move_file.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
        """
        source = operation.attributes.get('source')
        target = operation.attributes.get('target')
        if not source or not target:
            operation.add_error("Operacja move_file wymaga atrybutów 'source' i 'target'")
            return
        if result.path == source:
            result.current_content = ''

    def _handle_delete_file(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Obsługuje operację delete_file.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
        """
        source = operation.attributes.get('source')
        if not source:
            operation.add_error("Operacja delete_file wymaga atrybutu 'source'")
            return
        if result.path == source:
            result.current_content = ''

    def _handle_delete_method(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Obsługuje operację delete_method.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
        """
        source = operation.attributes.get('source')
        class_name = operation.attributes.get('class')
        method_name = operation.attributes.get('method')
        if not source or not class_name or (not method_name):
            operation.add_error("Operacja delete_method wymaga atrybutów 'source', 'class' i 'method'")
            return
        if result.path != source:
            return
        (_, ext) = os.path.splitext(source)
        file_extension = ext.lower()[1:] if ext else ''
        if file_extension == 'py':
            self._delete_python_method(result, class_name, method_name)
        elif file_extension in ['js', 'jsx', 'ts', 'tsx']:
            self._delete_javascript_method(result, class_name, method_name)
        else:
            operation.add_error(f'Nieobsługiwane rozszerzenie pliku: {file_extension}')

    def _delete_python_method(self, result: PatchResult, class_name: str, method_name: str) -> None:
        """
        Usuwa metodę z klasy Python.

        Args:
            result: Wynik do zaktualizowania
            class_name: Nazwa klasy
            method_name: Nazwa metody
        """
        parser = PythonParser()
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
        if not target_class:
            return
        method = tree.find_method_by_name(target_class, method_name)
        if not method:
            return
        new_tree = tree.replace_node(method, '')
        result.current_content = parser.generate(new_tree)

    def _delete_javascript_method(self, result: PatchResult, class_name: str, method_name: str) -> None:
        """
        Usuwa metodę z klasy JavaScript.

        Args:
            result: Wynik do zaktualizowania
            class_name: Nazwa klasy
            method_name: Nazwa metody
        """
        parser = JavaScriptParser()
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
        if not target_class:
            return
        method = tree.find_method_by_name(target_class, method_name)
        if not method:
            return
        new_tree = tree.replace_node(method, '')
        result.current_content = parser.generate(new_tree)