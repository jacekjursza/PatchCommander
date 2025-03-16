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
    
    def _format_python_code_block(self, code: str, base_indent: str) -> str:
        """
        Format a Python code block (function/method) with correct indentation.
        This handles the Python-specific indentation rules.
        """
        lines = code.splitlines()
        if not lines:
            return ""
        
        # Extract decorators first
        decorators = []
        start_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('@'):
                decorators.append(line.strip())
                start_index = i + 1
            else:
                break
                
        if start_index >= len(lines):
            # Only decorators, no actual code
            return '\n'.join([f"{base_indent}{dec}" for dec in decorators])
        
        # Find the definition line (def/class)
        def_line = None
        def_index = start_index
        for i in range(start_index, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith('def ') or stripped.startswith('async def ') or stripped.startswith('class '):
                def_line = stripped
                def_index = i
                break
        
        if def_line is None:
            # No function/method/class definition found, use standard indentation
            return self._format_code_with_indentation(code, base_indent)
        
        # Format decorators with base indentation
        formatted_lines = [f"{base_indent}{dec}" for dec in decorators]
        
        # Format the definition line
        formatted_lines.append(f"{base_indent}{def_line}")
        
        # Format the body with additional indentation
        body_indent = base_indent + "    "  # Python standard: 4 spaces
        
        # Extract body and handle docstring
        body_lines = lines[def_index + 1:]
        if body_lines and body_lines[0].strip().startswith(('"""', "'''")):
            # Handle multi-line docstring
            docstring_delimiter = '"""' if body_lines[0].strip().startswith('"""') else "'''"
            docstring_lines = []
            docstring_end_index = 0
            in_docstring = True
            
            # First line of docstring
            docstring_lines.append(body_lines[0].strip())
            
            # Find end of docstring
            for i in range(1, len(body_lines)):
                docstring_end_index = i
                docstring_lines.append(body_lines[i])
                if docstring_delimiter in body_lines[i]:
                    in_docstring = False
                    break
            
            if not in_docstring:
                # Format docstring with body indentation
                for i, line in enumerate(docstring_lines):
                    if i == 0:
                        formatted_lines.append(f"{body_indent}{line}")
                    else:
                        stripped = line.strip()
                        if stripped:
                            formatted_lines.append(f"{body_indent}{stripped}")
                        else:
                            formatted_lines.append("")
                
                # Format remaining body with body indentation
                for line in body_lines[docstring_end_index + 1:]:
                    stripped = line.strip()
                    if stripped:
                        formatted_lines.append(f"{body_indent}{stripped}")
                    else:
                        formatted_lines.append("")
            else:
                # Unterminated docstring - treat as normal code
                for line in body_lines:
                    stripped = line.strip()
                    if stripped:
                        formatted_lines.append(f"{body_indent}{stripped}")
                    else:
                        formatted_lines.append("")
        else:
            # No docstring, format all body lines
            for line in body_lines:
                stripped = line.strip()
                if stripped:
                    formatted_lines.append(f"{body_indent}{stripped}")
                else:
                    formatted_lines.append("")
        
        return '\n'.join(formatted_lines)
    
    def _format_property_lines(self, properties: str, indent: str) -> str:
        """Format class property lines with correct indentation."""
        lines = properties.splitlines()
        formatted_lines = []
        
        for line in lines:
            if line.strip():
                formatted_lines.append(f"{indent}{line.strip()}")
            else:
                formatted_lines.append("")
        
        return '\n'.join(formatted_lines)
    
    def _format_code_with_indentation(self, code: str, base_indent: str) -> str:
        """
        Format general code with indentation (fallback method).
        Used for code that isn't a Python function/method/class.
        """
        lines = code.splitlines()
        if not lines:
            return ""
        
        # Check if the code already has consistent indentation
        # If so, we need to adjust all lines; if not, we respect the existing structure
        has_indentation = False
        min_indent = float('inf')
        
        for line in lines:
            if line.strip():  # Non-empty line
                spaces = len(line) - len(line.lstrip())
                if spaces > 0:
                    has_indentation = True
                    min_indent = min(min_indent, spaces)
        
        if not has_indentation or min_indent == float('inf'):
            # No indentation in original code, add base_indent to all non-empty lines
            formatted_lines = []
            for line in lines:
                if line.strip():
                    formatted_lines.append(f"{base_indent}{line.strip()}")
                else:
                    formatted_lines.append("")
            return '\n'.join(formatted_lines)
        else:
            # Code has indentation, adjust by the difference
            formatted_lines = []
            for line in lines:
                if line.strip():
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent >= min_indent:
                        # Adjust indentation level
                        relative_indent = current_indent - min_indent
                        formatted_lines.append(f"{base_indent}{' ' * relative_indent}{line.lstrip()}")
                    else:
                        # Unexpected indentation, use base indent
                        formatted_lines.append(f"{base_indent}{line.lstrip()}")
                else:
                    formatted_lines.append("")
            return '\n'.join(formatted_lines)