from rich.console import Console

from .. import Processor, PatchOperation, PatchResult

console = Console()
from .decorator import register_processor


@register_processor(priority=50)
class FileProcessor(Processor):
    """
    Processor for FILE operations that replace entire file content.
    For partial file modifications (xpath operations), use specialized processors.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.

        Args:
            operation: The operation to check

        Returns:
            bool: True if it's a FILE operation without xpath
        """
        return operation.name == 'FILE' and (not operation.xpath)

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Processes a FILE operation by replacing the entire file content.

        Args:
            operation: The operation to process
            result: The result to update
        """
        result.current_content = operation.content
        console.print(f'[green]Replaced entire content of {result.path}[/green]')