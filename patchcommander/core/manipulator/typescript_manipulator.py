import re
from typing import List, Tuple, Optional

from patchcommander.core.manipulator.base import BaseCodeManipulator
from patchcommander.core.finder.typescript_code_finder import TypeScriptCodeFinder

class TypeScriptCodeManipulator(BaseCodeManipulator):
    """TypeScript-specific code manipulator that handles TypeScript's syntax requirements."""

    def __init__(self):
        super().__init__('typescript')
        self.finder = TypeScriptCodeFinder()
    
    def replace_function(self, original_code: str, function_name: str, new_function: str) -> str:
        """Replace the specified function with new content, preserving TypeScript syntax."""
        start_line, end_line = self.finder.find_function(original_code, function_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Function not found
        
        return self._replace_element(original_code, start_line, end_line, new_function)
    
    def replace_class(self, original_code: str, class_name: str, new_class_content: str) -> str:
        """Replace the specified class with new content, preserving TypeScript syntax."""
        start_line, end_line = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Class not found
        
        return self._replace_element(
            original_code, start_line, end_line, new_class_content
        )

    def replace_method(
        self, original_code: str, class_name: str, method_name: str, new_method: str
    ) -> str:
        (start_line, end_line) = self.finder.find_method(
            original_code, class_name, method_name
        )
        if start_line == 0 and end_line == 0:
            return original_code

        # Poprawne użycie find_class
        (class_start, _) = self.finder.find_class(original_code, class_name)

        if class_start == 0:
            return original_code

        lines = original_code.splitlines()
        class_indent = (
            self._get_indentation(lines[class_start - 1])
            if class_start <= len(lines)
            else ""
        )
        method_indent = class_indent + "  "
        formatted_method = self._format_typescript_code_block(new_method, method_indent)
        return self.replace_lines(original_code, start_line, end_line, formatted_method)
    
    def replace_property(self, original_code: str, class_name: str, property_name: str, new_property: str) -> str:
        """Replace the specified property within a class, preserving TypeScript syntax."""
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
        """Add a new method to the specified class, with proper TypeScript indentation."""
        start_line, end_line = self.finder.find_class(original_code, class_name)
        if start_line == 0 and end_line == 0:
            return original_code  # Class not found
        
        lines = original_code.splitlines()
        class_indent = self._get_indentation(lines[start_line-1]) if start_line <= len(lines) else ""
        method_indent = class_indent + "  "  # TypeScript standard: 2 spaces
        
        # Format the method with the correct indentation
        formatted_method = self._format_typescript_code_block(method_code, method_indent)
        
        # Find the last line of the class body (before the closing brace)
        class_end_brace = -1
        for i in range(end_line - 1, start_line - 1, -1):
            if i < len(lines) and lines[i].strip() == '}':
                class_end_brace = i
                break
        
        if class_end_brace > 0:
            # Add a blank line before the method if there isn't one already and the class isn't empty
            is_empty_class = True
            for i in range(start_line, class_end_brace):
                if i < len(lines) and lines[i].strip() and not (lines[i].strip().startswith('class') or lines[i].strip() == '{'):
                    is_empty_class = False
                    break
            
            if is_empty_class:
                # Insert as the first method in the class - right after the opening brace
                insertion_point = start_line + 1  # After class declaration and opening brace
                if insertion_point < len(lines) and lines[insertion_point-1].strip() == '{':
                    modified_lines = lines[:insertion_point] + [formatted_method] + lines[insertion_point:]
                else:
                    modified_lines = lines[:start_line] + [class_indent + '{', formatted_method] + lines[start_line:]
            else:
                # Insert before the closing brace, with a blank line
                if class_end_brace > 1 and lines[class_end_brace-1].strip():
                    formatted_method = f"\n{formatted_method}"
                
                modified_lines = lines[:class_end_brace] + [formatted_method] + lines[class_end_brace:]
            
            return '\n'.join(modified_lines)
        
        # Fallback: append to the end of the class
        modified_lines = lines[:end_line] + [formatted_method] + lines[end_line:]
        return '\n'.join(modified_lines)
    
    def remove_method_from_class(self, original_code: str, class_name: str, method_name: str) -> str:
        """Remove the specified method from a class, maintaining TypeScript syntax."""
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
        (start_line, end_line) = self.finder.find_properties_section(original_code, class_name)
        if start_line == 0 and end_line == 0:
            (class_start, class_end) = self.finder.find_class(original_code, class_name)
            if class_start == 0:
                return original_code
            lines = original_code.splitlines()
            for i in range(class_start, min(class_start + 5, len(lines))):
                if i < len(lines) and '{' in lines[i]:
                    class_indent = self._get_indentation(lines[class_start - 1])
                    property_indent = class_indent + '  '
                    formatted_properties = self._format_property_lines(new_properties, property_indent)
                    modified_lines = lines[:i + 1] + [formatted_properties] + lines[i + 1:]
                    return '\n'.join(modified_lines)
            return original_code
        return self._replace_element(original_code, start_line, end_line, new_properties)
    
    def replace_imports_section(self, original_code: str, new_imports: str) -> str:
        """Replace the imports section of a file, preserving TypeScript syntax."""
        start_line, end_line = self.finder.find_imports_section(original_code)
        if start_line == 0 and end_line == 0:
            # Imports section not found, add at the beginning of the file
            return new_imports + '\n\n' + original_code
        
        return self._replace_element(original_code, start_line, end_line, new_imports)
    
    def _replace_element(self, original_code: str, start_line: int, end_line: int, new_content: str) -> str:
        """Helper method to replace code elements with proper indentation."""
        lines = original_code.splitlines()
        if start_line > 0 and start_line <= len(lines):
            original_line = lines[start_line-1]
            indent = self._get_indentation(original_line)
            
            # Format the new content with the same indentation
            is_function = self._is_function_or_method(original_line) 
            if is_function:
                formatted_content = self._format_typescript_code_block(new_content, indent)
            else:
                formatted_content = self._format_code_with_indentation(new_content, indent)
            
            return self.replace_lines(original_code, start_line, end_line, formatted_content)
        
        return original_code
    
    def _is_function_or_method(self, line: str) -> bool:
        """Check if a line is a function or method definition."""
        return (re.match(r'^\s*(async\s+)?function\s+', line.strip()) is not None or
                re.match(r'^\s*(public|private|protected|static|async)?\s*\w+\s*\(', line.strip()) is not None)
    
    def _get_indentation(self, line: str) -> str:
        """Get the whitespace indentation from a line of code."""
        match = re.match(r'^(\s*)', line)
        return match.group(1) if match else ""
    
    def _format_typescript_code_block(self, code: str, base_indent: str) -> str:
        """
        Format a TypeScript code block (function/method) with correct indentation.
        This handles the TypeScript-specific indentation rules (typically 2 spaces).
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
        
        # Format decorators with base indentation
        formatted_lines = [f"{base_indent}{dec}" for dec in decorators]
        
        # Find signature and opening brace
        signature_line = None
        opening_brace_index = -1
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if not signature_line and (line.startswith('function') or 
                                      line.startswith('async function') or
                                      '(' in line):
                signature_line = line
                if '{' in line:  # Brace on same line as signature
                    opening_brace_index = i
                    break
            elif signature_line and '{' in line:  # Brace on separate line
                opening_brace_index = i
                break
        
        if not signature_line:
            # No function/method signature found, use standard indentation
            return self._format_code_with_indentation(code, base_indent)
        
        # Format the signature line
        formatted_lines.append(f"{base_indent}{signature_line}")
        
        # Format the body with additional indentation if brace is on separate line
        body_indent = base_indent + "  "  # TypeScript standard: 2 spaces
        
        # Handle case where brace is on a separate line
        if opening_brace_index > start_index and '{' in lines[opening_brace_index].strip():
            # Format the brace line if it's separate from signature
            if opening_brace_index != start_index:
                formatted_lines.append(f"{base_indent}{lines[opening_brace_index].strip()}")
            
            # Format body
            for i in range(opening_brace_index + 1, len(lines)):
                line = lines[i].strip()
                if line == '}':  # Closing brace
                    formatted_lines.append(f"{base_indent}{line}")
                elif line:  # Non-empty line
                    formatted_lines.append(f"{body_indent}{line}")
                else:  # Empty line
                    formatted_lines.append("")
        else:
            # Handle case where brace is part of signature or no opening brace found
            in_body = True
            for i in range(start_index + 1, len(lines)):
                line = lines[i].strip()
                if line == '}':  # Closing brace
                    formatted_lines.append(f"{base_indent}{line}")
                elif line:  # Non-empty line
                    formatted_lines.append(f"{body_indent}{line}")
                else:  # Empty line
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
        Used for code that isn't a TypeScript function/method/class.
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