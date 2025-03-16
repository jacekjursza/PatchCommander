from patchcommander.core.finder.factory import get_code_finder
from patchcommander.core.manipulator.abstract import AbstractCodeManipulator


class BaseCodeManipulator(AbstractCodeManipulator):

    def __init__(self, language: str='python'):
        self.language = language
        self.finder = get_code_finder(language)

    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        (start_line, end_line) = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, new_function)

    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, new_class_content)

    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, new_method)

    def replace_property(self, original_code: str, class_name: str, property_name: str, new_property: str) -> str:
        (start_line, end_line) = self.finder.find_property(original_code, class_name, property_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, new_property)

    def add_method_to_class(self, original_code: str, class_name: str, method_code: str) -> str:
        (start_line, end_line) = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        modified_lines = lines[:end_line] + [method_code] + lines[end_line:]
        return '\n'.join(modified_lines)

    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
        (start_line, end_line) = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code
        lines = original_code.splitlines()
        modified_lines = lines[:start_line - 1] + lines[end_line:]
        return '\n'.join(modified_lines)

    def replace_entire_file(self, original_code: str, new_content: str) -> str:
        return new_content

    def replace_properties_section(self, original_code: str, class_name: str, new_properties: str) -> str:
        (start_line, end_line) = self.finder.find_properties_section(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code
        return self.replace_lines(original_code, start_line, end_line, new_properties)

    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        (start_line, end_line) = self.finder.find_imports_section(original_code)
        if start_line == 0 and end_line == 0:
            return new_imports + '\n\n' + original_code
        return self.replace_lines(original_code, start_line, end_line, new_imports)

    def replace_lines(self, original_code: str, start_line: int, end_line: int, new_lines: str) -> str:
        if start_line <= 0 or end_line <= 0:
            return original_code
        lines = original_code.splitlines(keepends=True)
        prefix = ''.join(lines[:start_line - 1])
        suffix = ''.join(lines[end_line:])
        if new_lines and (not new_lines.endswith('\n')):
            new_lines += '\n'
        return prefix + new_lines + suffix

    def replace_lines_range(self, original_code: str, start_line: int, end_line: int, new_content: str, preserve_formatting: bool = False) -> str:
        """
        Replace a range of lines in the original code with new content.

        This differs from replace_lines in that it specifically handles line numbers
        provided by the user, rather than from a finder method.

        Args:
        original_code: The original code content
        start_line: The starting line number (1-indexed)
        end_line: The ending line number (1-indexed, inclusive)
        new_content: The new content to replace the lines with
        preserve_formatting: If True, preserves exact formatting of new_content without normalization

        Returns:
        The modified code with the lines replaced
        """
        if not original_code:
            return new_content

        lines = original_code.splitlines(keepends=True)
        total_lines = len(lines)

        # Adjust line numbers to be within range
        start_line = max(1, min(start_line, total_lines))
        end_line = max(start_line, min(end_line, total_lines))

        # Convert to 0-based indexing
        start_idx = start_line - 1
        end_idx = end_line

        prefix = ''.join(lines[:start_idx])
        suffix = ''.join(lines[end_idx:])

        # If preserve_formatting is True, use new_content as-is
        # Otherwise, ensure it ends with a newline if it's not empty
        if not preserve_formatting and new_content and not new_content.endswith('\n'):
            new_content += '\n'

        return prefix + new_content + suffix
