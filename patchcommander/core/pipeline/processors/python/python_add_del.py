"""
Python-specific operations processor.
"""
from rich.console import Console
from ...processor_base import Processor
from ...models import PatchOperation, PatchResult
from .....parsers.python_parser import PythonParser
from ..decorator import register_processor

console = Console()

@register_processor(priority=15)
class PythonOperationsProcessor(Processor):
    """
    Processor for Python-specific operations like add_method and delete_method.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.

        Args:
            operation: Operation to check

        Returns:
            bool: True if it's a Python operation
        """
        return (operation.name == "OPERATION" and
                operation.action in ("add_method", "delete_method") and
                operation.file_extension == "py")

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Processes Python-specific operations.

        Args:
            operation: Operation to process
            result: Result to update
        """
        action = operation.action
        if action == "add_method":
            self._handle_add_method(operation, result)
        elif action == "delete_method":
            self._handle_delete_method(operation, result)

    def _handle_add_method(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Handles the add_method operation.

        Args:
            operation: Operation to process
            result: Result to update
        """
        class_name = operation.attributes.get('class')
        method_code = operation.content

        if not class_name or not method_code:
            operation.add_error("Missing required attributes for add_method operation")
            return

        try:
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
                operation.add_error(f"Class {class_name} not found in file {result.path}")
                return

            method_name = self._extract_method_name(method_code)
            new_tree = None

            if method_name:
                existing_method = tree.find_method_by_name(target_class, method_name)
                if existing_method:
                    console.print(f"[blue]Method {method_name} already exists in class {class_name}. Replacing it.[/blue]")
                    new_tree = tree.replace_method_in_class(target_class, existing_method, method_code)

            if not new_tree:
                new_tree = tree.add_method_to_class(target_class, method_code)

            result.current_content = parser.generate(new_tree)

        except Exception as e:
            operation.add_error(f"Error during method addition: {e}")

    def _handle_delete_method(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Handles the delete_method operation.

        Args:
            operation: Operation to process
            result: Result to update
        """
        class_name = operation.attributes.get('class')
        method_name = operation.attributes.get('method')

        if not class_name or not method_name:
            operation.add_error("Missing required attributes for delete_method operation")
            return

        try:
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
                operation.add_error(f"Class {class_name} not found in file {result.path}")
                return

            method = tree.find_method_by_name(target_class, method_name)
            if not method:
                operation.add_error(f"Method {method_name} not found in class {class_name}")
                return

            new_tree = tree.replace_node(method, '')
            result.current_content = parser.generate(new_tree)

        except Exception as e:
            operation.add_error(f"Error during method deletion: {e}")

    def _extract_method_name(self, method_code: str) -> str:
        """
        Extracts the method name from method code.

        Args:
            method_code: Method code

        Returns:
            str: Method name or empty string if not found
        """
        import re
        match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', method_code)
        if match:
            return match.group(1)
        return ""