from abc import ABC, abstractmethod
from typing import Optional, Tuple

class AbstractCodeManipulator(ABC):
    pass

    @abstractmethod
    def replace_properties_section(self, original_code: str, class_name: str, new_properties: str) -> str:
        pass

    @abstractmethod
    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        pass

    @abstractmethod
    def replace_entire_file(self, original_code: str, new_content: str) -> str:
        pass

    @abstractmethod
    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        pass

    @abstractmethod
    def replace_lines_range(self, original_code: str, start_line: int, end_line: int, new_content: str, preserve_formatting: bool = False) -> str:
        """
        Replace a range of lines in the original code with new content.

        Args:
        original_code: The original code content
        start_line: The starting line number (1-indexed)
        end_line: The ending line number (1-indexed, inclusive)
        new_content: The new content to replace the lines with
        preserve_formatting: If True, preserves exact formatting of new_content without normalization

        Returns:
        The modified code with the lines replaced
        """
        pass

    @abstractmethod
    def add_method_to_class(self, original_code: str, class_name: str, method_code: str) -> str:
        pass

    @abstractmethod
    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        pass

    @abstractmethod
    def replace_property(self, original_code: str, class_name: str, property_name: str, new_property: str) -> str:
        pass

    @abstractmethod
    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
        pass

    @abstractmethod
    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        pass

    @abstractmethod
    def replace_lines(self, original_code: str, start_line: int, end_line: int, new_lines: str) -> str:
        pass

    @abstractmethod
    def replace_lines_range(self, original_code: str, start_line: int, end_line: int, new_content: str, preserve_formatting: bool = False) -> str:
        """
        Replace a range of lines in the original code with new content.

        Args:
        original_code: The original code content
        start_line: The starting line number (1-indexed)
        end_line: The ending line number (1-indexed, inclusive)
        new_content: The new content to replace the lines with
        preserve_formatting: If True, preserves exact formatting of new_content without normalization

        Returns:
        The modified code with the lines replaced
        """
        pass