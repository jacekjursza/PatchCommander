"""
XPath analyzer for preprocessor.
"""
from ...models import PatchOperation
from ...processor_base import PreProcessor
from patchcommander.core.utils.xpath_utils import analyze_xpath

class XPathAnalyzer(PreProcessor):
    """
    Preprocessor that analyzes and validates XPath in operation.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the analyzer can handle the operation.

        Args:
            operation: Operation to check

        Returns:
            bool: True if operation has xpath attribute
        """
        return operation.name == 'FILE' and operation.xpath is not None

    def process(self, operation: PatchOperation) -> None:
        """
        Analyzes and validates XPath in operation.

        Args:
            operation: Operation to process
        """
        if not operation.xpath:
            return
            
        # Use the utility function to analyze the xpath
        analyze_xpath(operation)