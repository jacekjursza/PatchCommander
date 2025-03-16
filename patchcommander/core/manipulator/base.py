from patchcommander.core.finder.factory import get_code_finder
from patchcommander.core.manipulator.abstract import AbstractCodeManipulator


class BaseCodeManipulator(AbstractCodeManipulator):
    """Base implementation of code manipulator with language-agnostic functionality."""

    def __init__(self, language: str = 'python'):
        self.language = language
        self.finder = get_code_finder(language)

    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        """Replace the specified function with new content."""
        start_line, end_line = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Function not found
        return self.replace_lines(original_code, start_line, end_line, new_function)

    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        """Replace the specified class with new content."""
        start_line, end_line = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Class not found
        return self.replace_lines(original_code, start_line, end_line, new_class_content)

    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        """Replace the specified method within a class."""
        start_line, end_line = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Method not found
        return self.replace_lines(original_code, start_line, end_line, new_method)

    def replace_property(self, original_code: str, class_name: str, property_name: str, new_property: str) -> str:
        """Replace the specified property within a class."""
        start_line, end_line = self.finder.find_property(original_code, class_name, property_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Property not found
        return self.replace_lines(original_code, start_line, end_line, new_property)

    def add_method_to_class(self, original_code: str, class_name: str, method_code: str) -> str:
        """Add a new method to the specified class (basic implementation)."""
        start_line, end_line = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Class not found
        
        # Simple implementation - add at the end of class
        # Language-specific implementations should override this
        lines = original_code.splitlines()
        modified_lines = lines[:end_line] + [method_code] + lines[end_line:]
        return '\n'.join(modified_lines)

    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
        """Remove the specified method from a class."""
        start_line, end_line = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Method not found
        
        lines = original_code.splitlines()
        modified_lines = lines[:start_line-1] + lines[end_line:]
        return '\n'.join(modified_lines)

    def replace_entire_file(self, original_code: str, new_content: str) -> str:
        """Replace the entire content of a file."""
        return new_content

    def replace_properties_section(self, original_code: str, class_name: str, new_properties: str) -> str:
        """Replace the properties section of a class."""
        start_line, end_line = self.finder.find_properties_section(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Properties section not found
        return self.replace_lines(original_code, start_line, end_line, new_properties)

    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        """Replace the imports section of a file."""
        start_line, end_line = self.finder.find_imports_section(original_code)
        if start_line == 0 and end_line == 0:
            # Imports section not found, add at the beginning of the file
            return new_imports + '\n\n' + original_code
        return self.replace_lines(original_code, start_line, end_line, new_imports)

    def replace_lines(self, original_code: str, start_line: int, end_line: int, new_lines: str) -> str:
        """Replace specified lines from start_line to end_line in the original code with new_lines."""
        if start_line <= 0 or end_line <= 0:
            return original_code
            
        lines = original_code.splitlines(keepends=True)
        prefix = ''.join(lines[:start_line - 1])
        suffix = ''.join(lines[end_line:])
        
        # Ensure new_lines ends with a newline
        if new_lines and not new_lines.endswith('\n'):
            new_lines += '\n'
            
        return prefix + new_lines + suffix