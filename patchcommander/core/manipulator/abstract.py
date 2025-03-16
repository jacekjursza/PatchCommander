from abc import ABC, abstractmethod
from typing import Optional, Tuple

class AbstractCodeManipulator(ABC):
    """Abstract base class defining the interface for all code manipulators."""

    @abstractmethod
    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        """Replace the specified function with new content."""
        pass

    @abstractmethod
    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        """Replace the specified class with new content."""
        pass

    @abstractmethod
    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        """Replace the specified method within a class."""
        pass

    @abstractmethod
    def replace_property(self, original_code: str, class_name: str, property_name: str, new_property: str) -> str:
        """Replace the specified property within a class."""
        pass

    @abstractmethod
    def add_method_to_class(self, original_code: str, class_name: str, method_code: str) -> str:
        """Add a new method to the specified class."""
        pass

    @abstractmethod
    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
        """Remove the specified method from a class."""
        pass

    @abstractmethod
    def replace_entire_file(self, original_code: str, new_content: str) -> str:
        """Replace the entire content of a file."""
        pass

    @abstractmethod
    def replace_properties_section(self, original_code: str, class_name: str, new_properties: str) -> str:
        """Replace the properties section of a class."""
        pass

    @abstractmethod
    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        """Replace the imports section of a file."""
        pass

    @abstractmethod
    def replace_lines(self, original_code: str, start_line: int, end_line: int, new_lines: str) -> str:
        """Replace specified lines from start_line to end_line in the original code with new_lines."""
        pass