"""
Base class for Python method processors.
"""
from rich.console import Console

from . import PythonProcessor
from ...models import PatchOperation, PatchResult

console = Console()

class BasePythonMethodProcessor(PythonProcessor):
    """
    Base class for processors handling operations on Python class methods.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.

        Args:
            operation: The operation to check.

        Returns:
            bool: True if it's a Python method operation.
        """
        return (super().can_handle(operation) and
                operation.attributes.get('target_type') == 'method')

    def _handle_empty_file(self, operation: PatchOperation, result: PatchResult, class_name: str, method_name: str) -> bool:
        """
        Handles the case of an empty file - creates a new class with the method.

        Args:
            operation: The operation to process.
            result: The result to update.
            class_name: The class name.
            method_name: The method name.

        Returns:
            bool: True if the file was empty and was handled.
        """
        if not result.current_content:
            method_content = operation.content.strip()
            method_lines = method_content.split('\n')
            indented_method = method_lines[0] + '\n' + '\n'.join([f'    {line}' for line in method_lines[1:]])
            result.current_content = f'class {class_name}:\n    {indented_method}'
            console.print(f"[green]Created a new file with class {class_name} and method {method_name}[/green]")
            return True
        return False

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Processes an operation on a Python method.

        Args:
            operation: The operation to process.
            result: The result to update.
        """
        class_name = operation.attributes.get('class_name')
        method_name = operation.attributes.get('method_name')

        if not class_name or not method_name:
            operation.add_error('Missing class name or method name')
            return

        console.print(f"[blue]{self.__class__.__name__}: Processing method {class_name}.{method_name}[/blue]")

        # Handle empty file
        if self._handle_empty_file(operation, result, class_name, method_name):
            return

        # Strategy-specific implementation - to be overridden in child classes
        self._process_method(operation, result, class_name, method_name)

    def _process_method(self, operation: PatchOperation, result: PatchResult, class_name: str, method_name: str) -> None:
        """
        Method to be overridden in child classes - concrete strategy implementation.

        Args:
            operation: The operation to process.
            result: The result to update.
            class_name: The class name.
            method_name: The method name.
        """
        raise NotImplementedError("This method must be implemented in a child class")