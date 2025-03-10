"""
Data models for the PatchCommander pipeline.
Defines the structures used throughout the processing.
"""
from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class PatchOperation:
    """
    Represents a single code modification operation.

    Attributes:
        name: Name of the operation ("FILE" or "OPERATION")
        path: Path to the file
        xpath: Optional XPath pointing to an element in the file
        content: Content to be inserted/modified
        action: Optional action for OPERATION (e.g., "move_file", "delete_file")
        file_extension: File extension (automatically detected)
        attributes: Additional attributes from the tag
        preprocessors: List of preprocessors the operation has passed through
        processors: List of processors the operation has passed through
        postprocessors: List of postprocessors the operation has passed through
        errors: List of errors encountered during processing
    """
    name: str
    path: str
    content: str = ''
    xpath: Optional[str] = None
    action: Optional[str] = None
    file_extension: str = ''
    attributes: Dict[str, str] = field(default_factory=dict)
    preprocessors: List[str] = field(default_factory=list)
    processors: List[str] = field(default_factory=list)
    postprocessors: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_preprocessor(self, name: str) -> None:
        """Adds the name of a preprocessor to the history."""
        self.preprocessors.append(name)

    def add_processor(self, name: str) -> None:
        """Adds the name of a processor to the history."""
        self.processors.append(name)

    def add_postprocessor(self, name: str) -> None:
        """Adds the name of a postprocessor to the history."""
        self.postprocessors.append(name)

    def add_error(self, error: str) -> None:
        """Adds an error to the error list."""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """Checks if there are any errors."""
        return len(self.errors) > 0

@dataclass
class PatchResult:
    """
    Represents the result of patching a file.

    Attributes:
        path: Path to the file
        original_content: Original content of the file
        current_content: Current content after all operations
        operations: List of operations performed on the file
        approved: Whether the changes have been approved
        errors: List of errors encountered during processing
    """
    path: str
    original_content: str
    current_content: str
    operations: List[PatchOperation] = field(default_factory=list)
    approved: bool = False
    errors: List[str] = field(default_factory=list)

    def add_operation(self, operation: PatchOperation) -> None:
        """Adds an operation to the list of performed operations."""
        self.operations.append(operation)

    def add_error(self, error: str) -> None:
        """Adds an error to the error list."""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """Checks if there are any errors."""
        return len(self.errors) > 0

    def clear_errors(self) -> None:
        """Clears the error list."""
        self.errors = []