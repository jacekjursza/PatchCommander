"""
Base classes for processors in the pipeline.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from .models import PatchOperation, PatchResult

class BaseProcessor(ABC):
    """
    Base class for all processors.
    """

    @property
    def name(self) -> str:
        """
        The name of the processor used in logs and operation history.
        Defaults to the class name, but can be overridden.
        """
        return self.__class__.__name__

    @abstractmethod
    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the given operation.

        Args:
            operation: The operation to check

        Returns:
            bool: True if the processor can handle the operation
        """
        pass

class PreProcessor(BaseProcessor):
    """
    Base class for pre-processors, which prepare operations for processing.
    """

    @abstractmethod
    def process(self, operation: PatchOperation) -> None:
        """
        Processes the operation.

        Args:
            operation: The operation to process
        """
        pass

class Processor(BaseProcessor):
    """
    Base class for processors, which perform operations on file contents.
    """

    @abstractmethod
    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Processes the operation and updates the result.

        Args:
            operation: The operation to process
            result: The result to update
        """
        pass

class PostProcessor(BaseProcessor):
    """
    Base class for post-processors, which perform operations on the results.
    """

    @abstractmethod
    def process(self, result: PatchResult) -> None:
        """
        Processes the result.

        Args:
            result: The result to process
        """
        pass

class GlobalPreProcessor(ABC):
    """
    Special class for a global pre-processor, which processes the entire input text.
    """

    @abstractmethod
    def process(self, input_text: str) -> List[PatchOperation]:
        """
        Processes the input text and generates a list of operations.

        Args:
            input_text: The input text

        Returns:
            List[PatchOperation]: The list of operations to perform
        """
        pass