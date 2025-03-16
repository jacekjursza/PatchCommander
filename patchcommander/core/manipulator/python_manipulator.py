import re
import ast
from typing import List, Tuple, Optional

from patchcommander.core.manipulator.base import BaseCodeManipulator
from patchcommander.core.finder.python_code_finder import PythonCodeFinder

class PythonCodeManipulator(BaseCodeManipulator):
    """Python-specific code manipulator that handles Python's syntax requirements."""

    def __init__(self):
        super().__init__('python')
        self.finder = PythonCodeFinder()
    
    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        """Replace the specified function with new content, preserving Python syntax."""
        start_line, end_line = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Function not found
        
        return self._replace_element(original_code, start_line, end_line, new_function)
    
    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        """Replace the specified class with new content, preserving Python syntax."""
        start_line, end_line = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Class not found
        
        return self._replace_element(original_code, start_line, end_line, new_class_content)
    
    def replace_method(self, original_code: str, class_name: str, method_name: str, new_method: str) -> str:
        """Replace the specified method within a class, preserving Python syntax."""
        start_line, end_line = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Method not found
        
        # Determine class indentation
        class_start, _ = self.finder.find_class(original_code, class_name)
        if class_start == 0:
            return original_code  # Class not found
        
        lines = original_code.splitlines()
        class_indent = self._get_indentation(lines[class_start-1]) if class_start <= len(lines) else ""
        method_indent = class_indent + "    "  # Method indentation is class + 4 spaces
        
        # Format the method with correct class method indentation
        formatted_method = self._format_python_code_block(new_method, method_indent)
        
        return self.replace_lines(original_code, start_line, end_line, formatted_method)
    
    def replace_property(self, original_code: str, class_name: str, property_name: str, new_property: str) -> str:
        """Replace the specified property within a class, preserving Python syntax."""
        start_line, end_line = self.finder.find_property(original_code, class_name, property_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Property not found
        
        # For properties, ensure the indentation is preserved
        lines = original_code.splitlines()
        if start_line > 0 and start_line <= len(lines):
            original_line = lines[start_line-1]
            indent = self._get_indentation(original_line)
            
            # Format the new property with the same indentation if not already formatted
            if not new_property.startswith(indent):
                new_property = indent + new_property.lstrip()
            
            return self.replace_lines(original_code, start_line, end_line, new_property)
        
        return original_code
    
    def add_method_to_class(self, original_code: str, class_name: str, method_code: str) -> str:
        """Add a new method to the specified class, with proper Python indentation."""
        start_line, end_line = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Class not found
        
        lines = original_code.splitlines()
        class_indent = self._get_indentation(lines[start_line-1]) if start_line <= len(lines) else ""
        method_indent = class_indent + "    "  # Method indentation is class + 4 spaces
        
        # Format the method with correct indentation
        formatted_method = self._format_python_code_block(method_code, method_indent)
        
        # Check if the class has other methods/content
        is_empty_class = True
        for i in range(start_line, min(end_line, len(lines))):
            if lines[i].strip() and not lines[i].strip().startswith("class"):
                is_empty_class = False
                break
        
        if is_empty_class:
            # Insert as the first method in the class - right after the class declaration
            insertion_point = start_line
            modified_lines = lines[:insertion_point] + [formatted_method] + lines[insertion_point:]
        else:
            # Add a blank line before method if there isn't one already
            if end_line > 1 and lines[end_line-2].strip():
                formatted_method = f"\n{formatted_method}"
            
            # Insert at the end of the class
            modified_lines = lines[:end_line] + [formatted_method] + lines[end_line:]
        
        return '\n'.join(modified_lines)
    
    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
        """Remove the specified method from a class, maintaining Python syntax."""
        start_line, end_line = self.finder.find_method(original_code, class_name, method_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Method not found
        
        lines = original_code.splitlines()
        
        # Check for decorators before the method
        i = start_line - 2  # Look at the line before the method
        decorator_start = start_line
        while i >= 0 and i < len(lines):
            line = lines[i].strip()
            if line.startswith('@'):
                decorator_start = i + 1
                i -= 1
            else:
                break
        
        # Remove method and its decorators
        modified_lines = lines[:decorator_start-1] + lines[end_line:]
        
        # Clean up blank lines - avoid having more than two consecutive blank lines
        result = '\n'.join(modified_lines)
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result
    
    def replace_properties_section(self, original_code: str, class_name: str, new_properties: str) -> str:
        """Replace the properties section of a class with proper Python indentation."""
        start_line, end_line = self.finder.find_properties_section(original_code, class_name)
        if start_line == 0 and end_line == 0:
            # Properties section not found, try to add after class definition
            class_start, _ = self.finder.find_class(original_code, class_name)
            if class_start == 0:
                return original_code  # Class not found
            
            lines = original_code.splitlines()
            class_line = lines[class_start-1] if class_start <= len(lines) else ""
            class_indent = self._get_indentation(class_line)
            property_indent = class_indent + "    "
            
            # Format the properties with correct indentation
            formatted_properties = self._format_property_lines(new_properties, property_indent)
            
            # Insert after class definition
            modified_lines = lines[:class_start] + [formatted_properties] + lines[class_start:]
            return '\n'.join(modified_lines)
        
        return self._replace_element(original_code, start_line, end_line, new_properties)
    
    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        """Replace the imports section of a file, preserving Python syntax."""
        start_line, end_line = self.finder.find_imports_section(original_code)
        if start_line == 0 and end_line == 0:
            # Imports section not found, add at the beginning of the file
            # Check for module docstring first
            lines = original_code.splitlines()
            
            # Check if the first non-blank line is a docstring
            first_non_blank = 0
            while first_non_blank < len(lines) and not lines[first_non_blank].strip():
                first_non_blank += 1
                
            if first_non_blank < len(lines) and lines[first_non_blank].strip().startswith('"""'):
                # Find end of docstring
                docstring_end = first_non_blank
                in_docstring = True
                for i in range(first_non_blank + 1, len(lines)):
                    docstring_end = i
                    if '"""' in lines[i]:
                        in_docstring = False
                        break
                
                if not in_docstring:
                    # Insert after docstring with blank line
                    return '\n'.join(lines[:docstring_end+1]) + '\n\n' + new_imports + '\n\n' + '\n'.join(lines[docstring_end+1:])
            
            # No docstring or couldn't find end, add at the beginning
            return new_imports + '\n\n' + original_code
        
        return self._replace_element(original_code, start_line, end_line, new_imports)
    
    def _replace_element(self, original_code: str, start_line: int, end_line: int, new_content: str) -> str:
        """Helper method to replace code elements with proper indentation."""
        lines = original_code.splitlines()
        if start_line > 0 and start_line <= len(lines):
            original_line = lines[start_line-1]
            indent = self._get_indentation(original_line)
            
            # Format the new content with the same indentation
            if self._is_function_or_method(original_line):
                formatted_content = self._format_python_code_block(new_content, indent)
            else:
                formatted_content = self._format_code_with_indentation(new_content, indent)
            
            return self.replace_lines(original_code, start_line, end_line, formatted_content)
        
        return original_code
    
    def _is_function_or_method(self, line: str) -> bool:
        """Check if a line is a function or method definition."""
        return re.match(r'^\s*(async\s+)?def\s+', line.strip()) is not None
    
    def _is_class_definition(self, line: str) -> bool:
        """Check if a line is a class definition."""
        return re.match(r'^\s*class\s+', line.strip()) is not None
    
    def _get_indentation(self, line: str) -> str:
        """Get the whitespace indentation from a line of code."""
        match = re.match(r'^(\s*)', line)
        return match.group(1) if match else ""

    def _format_property_lines(self, properties: str, indent: str) -> str:
        """Format class property lines with correct indentation."""
        lines = properties.splitlines()
        formatted_lines = []

        for line in lines:
            if line.strip():
                formatted_lines.append(f"{indent}{line.strip()}")
            else:
                formatted_lines.append("")

        return "\n".join(formatted_lines)

    def _format_python_code_block(self, code: str, base_indent: str) -> str:
        lines = code.splitlines()
        if not lines:
            return ""

        # Handle decorators
        decorators = []
        start_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("@"):
                decorators.append(line.strip())
                start_index = i + 1
            else:
                break

        if start_index >= len(lines):
            return "\n".join([f"{base_indent}{dec}" for dec in decorators])

        # Find the function/method signature line
        def_line = None
        def_index = start_index
        for i in range(start_index, len(lines)):
            stripped = lines[i].strip()
            if (
                stripped.startswith("def ")
                or stripped.startswith("async def ")
                or stripped.startswith("class ")
            ):
                def_line = stripped
                def_index = i
                break

        if def_line is None:
            return self._format_code_with_indentation(code, base_indent)

        # Format decorators and function/method signature
        formatted_lines = [f"{base_indent}{dec}" for dec in decorators]
        formatted_lines.append(f"{base_indent}{def_line}")

        # Format the function body with proper indentation
        body_indent = base_indent + "    "

        # First, determine the indentation of the first body line to use as reference
        original_first_body_indent = None
        for i in range(def_index + 1, len(lines)):
            if lines[i].strip():
                original_first_body_indent = len(lines[i]) - len(lines[i].lstrip())
                break

        # If we found a non-empty body line, use it as reference for indentation
        if original_first_body_indent is not None:
            # Process docstrings first if present
            if def_index + 1 < len(lines) and (
                lines[def_index + 1].strip().startswith('"""')
                or lines[def_index + 1].strip().startswith("'''")
            ):
                docstring_delimiter = (
                    '"""' if lines[def_index + 1].strip().startswith('"""') else "'''"
                )
                docstring_lines = []
                docstring_end_index = 0
                in_docstring = True
                docstring_lines.append(lines[def_index + 1].strip())

                for i in range(def_index + 2, len(lines)):
                    docstring_end_index = i
                    docstring_lines.append(lines[i])
                    if docstring_delimiter in lines[i]:
                        in_docstring = False
                        break

                if not in_docstring:
                    for i, line in enumerate(docstring_lines):
                        if i == 0:
                            formatted_lines.append(f"{body_indent}{line}")
                        else:
                            line_content = line.strip()
                            if line_content:
                                formatted_lines.append(f"{body_indent}{line_content}")
                            else:
                                formatted_lines.append("")

                    # Process remaining body lines after docstring
                    remaining_lines = lines[docstring_end_index + 1 :]

                    # Find the indentation pattern in the code
                    if remaining_lines:
                        self._format_body_lines(
                            remaining_lines,
                            formatted_lines,
                            original_first_body_indent,
                            body_indent,
                        )
                else:
                    # If docstring wasn't properly closed, handle entire body
                    self._format_body_lines(lines[def_index + 1:], formatted_lines, original_first_body_indent, body_indent)
            else:
                # No docstring, process all body lines
                self._format_body_lines(lines[def_index + 1:], formatted_lines, original_first_body_indent, body_indent)

        return '\n'.join(formatted_lines)

    def _format_body_lines(
        self, body_lines, formatted_lines, original_indent, base_indent
    ):
        """Helper method to format body lines with proper indentation structure."""
        if not body_lines:
            return

        # Find the minimum indentation in non-empty lines to use as reference
        min_indent = float("inf")
        for line in body_lines:
            if line.strip():
                line_indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, line_indent)

        if min_indent == float("inf"):
            min_indent = original_indent

        # Now format each line preserving relative indentation
        for line in body_lines:
            if not line.strip():
                formatted_lines.append("")
                continue

            line_indent = len(line) - len(line.lstrip())
            if line_indent >= min_indent:
                # Calculate relative indentation difference
                relative_indent = line_indent - min_indent
                formatted_lines.append(f"{base_indent}{' ' * relative_indent}{line.lstrip()}")
            else:
                # Fallback if line has less indentation than min (shouldn't happen in valid Python)
                formatted_lines.append(f'{base_indent}{line.lstrip()}')


    def _format_code_with_indentation(self, code: str, base_indent: str) -> str:
        """Format generic code block with proper indentation."""
        lines = code.splitlines()
        if not lines:
            return ""

        # Check if this is a class definition
        is_class_def = False
        class_body_indent = base_indent + "    "
        if lines and lines[0].strip().startswith("class "):
            is_class_def = True

        # Find the minimum indentation in non-empty lines to use as reference
        min_indent = float("inf")
        for line in lines:
            if line.strip():
                line_indent = len(line) - len(line.lstrip())
                if line_indent > 0:  # Only consider indented lines
                    min_indent = min(min_indent, line_indent)

        if min_indent == float("inf"):
            # No indentation detected, format using simple rules
            formatted_lines = []
            for i, line in enumerate(lines):
                line_content = line.strip()
                if not line_content:
                    formatted_lines.append("")
                    continue

                # Special handling for first line (class/def declaration)
                if i == 0:
                    formatted_lines.append(f"{base_indent}{line_content}")
                # Special handling for class methods - they need extra indentation
                elif is_class_def and line_content.startswith("def "):
                    formatted_lines.append(f"{class_body_indent}{line_content}")
                # Handle other class content
                elif is_class_def:
                    formatted_lines.append(f"{class_body_indent}{line_content}")
                # Regular lines
                else:
                    formatted_lines.append(f"{base_indent}{line_content}")
        else:
            # Indentation detected, preserve the structure
            formatted_lines = []
            for i, line in enumerate(lines):
                line_content = line.strip()
                if not line_content:
                    formatted_lines.append("")
                    continue

                # Special handling for first line (often a class/def declaration)
                if i == 0:
                    formatted_lines.append(f"{base_indent}{line_content}")
                    continue

                # Calculate relative indentation
                line_indent = len(line) - len(line.lstrip())

                # For class definitions, ensure methods have proper indentation
                if is_class_def and line_content.startswith("def "):
                    if line_indent <= min_indent:  # If it's directly under the class
                        formatted_lines.append(f"{class_body_indent}{line_content}")
                        continue

                # For standard indented lines
                if line_indent >= min_indent:
                    relative_indent = line_indent - min_indent

                    # Class content needs one level of base indentation
                    if is_class_def:
                        formatted_lines.append(
                            f"{class_body_indent}{' ' * relative_indent}{line.lstrip()}"
                        )
                    else:
                        formatted_lines.append(
                            f"{base_indent}{' ' * relative_indent}{line.lstrip()}"
                        )
                else:
                    # Fallback for lines with less indentation than our reference
                    if is_class_def:
                        formatted_lines.append(f'{class_body_indent}{line_content}')
                    else:
                        formatted_lines.append(f'{base_indent}{line_content}')

        return '\n'.join(formatted_lines)