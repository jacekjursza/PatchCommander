"""
Processor for the OPERATION tag.
"""
import os
from rich.console import Console
from .. import Processor, PatchOperation, PatchResult
from ....parsers.python_parser import PythonParser
from ....parsers.javascript_parser import JavaScriptParser

console = Console()

# Adding the register_processor decorator
from .decorator import register_processor


@register_processor(priority=10)
class OperationProcessor(Processor):
    """
    Processor for the OPERATION tag.
    Handles file operations such as move_file, delete_file, delete_method.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.

        Args:
            operation: The operation to check.

        Returns:
            bool: True if it's an OPERATION operation.
        """
        return operation.name == 'OPERATION'

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Processes the OPERATION operation.

        Args:
            operation: The operation to process.
            result: The result to update.
        """
        action = operation.action
        if not action:
            operation.add_error('No action specified for OPERATION')
            return
        if action == 'move_file':
            self._handle_move_file(operation, result)
        elif action == 'delete_file':
            self._handle_delete_file(operation, result)
        elif action == 'delete_method':
            self._handle_delete_method(operation, result)
        else:
            operation.add_error(f'Unknown action: {action}')

    def _handle_move_file(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Handles the move_file operation.

        Args:
            operation: The operation to process.
            result: The result to update.
        """
        source = operation.attributes.get('source')
        target = operation.attributes.get('target')
        if not source or not target:
            operation.add_error("move_file operation requires 'source' and 'target' attributes")
            return
        if result.path == source:
            result.current_content = ''

    def _handle_delete_file(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Handles the delete_file operation.

        Args:
            operation: The operation to process.
            result: The result to update.
        """
        source = operation.attributes.get('source')
        if not source:
            operation.add_error("delete_file operation requires 'source' attribute")
            return
        if result.path == source:
            result.current_content = ''

    def _handle_delete_method(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Handles the delete_method operation.

        Args:
            operation: The operation to process.
            result: The result to update.
        """
        source = operation.attributes.get('source')
        class_name = operation.attributes.get('class')
        method_name = operation.attributes.get('method')
        if not source or not class_name or (not method_name):
            operation.add_error("delete_method operation requires 'source', 'class', and 'method' attributes")
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
            operation.add_error(f'Unsupported file extension: {file_extension}')

    def _delete_python_method(self, result: PatchResult, class_name: str, method_name: str) -> None:
        """
        Deletes a method from a Python class.

        Args:
            result: The result to update.
            class_name: The class name.
            method_name: The method name.
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
        Deletes a method from a JavaScript class.

        Args:
            result: The result to update.
            class_name: The class name.
            method_name: The method name.
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