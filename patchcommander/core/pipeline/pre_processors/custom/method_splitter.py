"""
Preprocessor for splitting multiple methods in a single METHOD tag.
"""
import re
from rich.console import Console
from ...processor_base import PreProcessor
from patchcommander.core.pipeline.models import PatchOperation

console = Console()

class MethodSplitter(PreProcessor):
    """
    Preprocessor that splits multiple method definitions in a single METHOD tag.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.

        Args:
            operation: Operation to check

        Returns:
            bool: True if it's a METHOD operation
        """
        return operation.name == "FILE" and operation.attributes.get("target_type") == "method"

    def process(self, operation: PatchOperation) -> None:
        """
        Splits multiple methods within a single METHOD operation into separate operations.

        Args:
            operation: Operation to process
        """
        if not operation.content:
            return

        method_defs = self._split_methods(operation.content)
        if len(method_defs) <= 1:
            return

        # We'll modify the original operation to contain only the first method
        console.print(f"[yellow]Preprocessor: Split {len(method_defs)} methods into separate operations.[/yellow]")
        operation.content = method_defs[0]

    def _split_methods(self, content):
        """
        Split content into separate method definitions.

        Args:
            content: Content of a METHOD tag

        Returns:
            List of method definitions
        """
        normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
        while '\n\n\n' in normalized_content:
            normalized_content = normalized_content.replace('\n\n\n', '\n\n')
        pattern = r'((?:(?:^|\n)\s*@[^\n]+\n)*\s*def\s+\w+\s*\([^)]*\):(?:(?!\n\s*(?:def\s|\s*@))[\s\S])*)'
        matches = re.findall(pattern, normalized_content)
        if not matches or (len(matches) == 1 and matches[0].strip() == normalized_content.strip()):
            return [normalized_content]
        cleaned_matches = [match.strip() for match in matches if match.strip()]
        all_content = '\n\n'.join(cleaned_matches)
        original_no_whitespace = re.sub(r'\s+', '', normalized_content)
        matches_no_whitespace = re.sub(r'\s+', '', all_content)
        if original_no_whitespace != matches_no_whitespace:
            console.print('[yellow]Warning: Unable to safely split methods. Keeping original tag.[/yellow]')
            return [normalized_content]
        return cleaned_matches