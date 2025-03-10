"""
Processor for Python classes.
"""
from rich.console import Console
# We are changing the decorator import to import from the correct module
from ..decorator import register_processor
from .base import PythonProcessor
from ...models import PatchOperation, PatchResult
console = Console()

@register_processor(priority=10)
class PythonClassProcessor(PythonProcessor):
    """
    Processor handling operations on Python classes.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.

        Args:
            operation: The operation to check

        Returns:
            bool: True if it's a Python class operation
        """
        return super().can_handle(operation) and operation.attributes.get('target_type') == 'class'

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Processes the operation on a Python class.

        Args:
            operation: The operation to process
            result: The result to update
        """
        class_name = operation.attributes.get('class_name')
        if not class_name:
            operation.add_error('Class name is missing')
            return
        console.print(f'[blue]PythonClassProcessor: Processing class {class_name}[/blue]')
        if not result.current_content:
            result.current_content = operation.content
            console.print(f'[green]Created a new file with class {class_name}[/green]')
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
            console.print(f'[green]Updated class {class_name}[/green]')
        else:
            separator = '\n\n' if result.current_content and (not result.current_content.endswith('\n\n')) else ''
            result.current_content = result.current_content + separator + operation.content
            console.print(f'[green]Added a new class {class_name}[/green]')