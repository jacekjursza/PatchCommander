"""
Base processor for Python files.
"""
from ...processor_base import Processor
from ...models import PatchOperation
from .....parsers.python_parser import PythonParser

class PythonProcessor(Processor):
    """
    Base class for all Python file processors.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle a Python operation.

        Args:
            operation: Operation to check

        Returns:
            bool: True if it's a FILE operation for a Python file
        """
        return operation.name == "FILE" and operation.file_extension == "py"

    def _get_parser(self) -> PythonParser:
        """
        Returns a Python parser.

        Returns:
            PythonParser: Parser for Python files
        """
        return PythonParser()