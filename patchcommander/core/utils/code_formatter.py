"""
Universal code formatting utilities for consistent code output.
"""
import re
from typing import List, Optional, Tuple

class CodeFormatter:
    """
    Universal formatter for Python code elements.
    Provides consistent indentation and spacing for generated code.
    """

    @staticmethod
    def format_class(
        class_def: str, fields: List[str], methods: List[str], base_indent: str = "    "
    ) -> str:
        result = [class_def]

        # Add fields
        if fields:
            for field in fields:
                if not field.strip():
                    continue

                # Ensure proper indentation for fields
                field_indent = field[: len(field) - len(field.lstrip())]
                if not field_indent:
                    result.append(f"{base_indent}{field.lstrip()}")
                else:
                    result.append(field)
        else:
            result.append(f"{base_indent}pass")

        # Add methods with proper spacing
        if methods:
            # Add empty line between fields and methods
            result.append("")

            for i, method in enumerate(methods):
                if i > 0:
                    result.append("")  # Add spacing between methods

                # Format method code with proper indentation
                formatted_method = CodeFormatter._format_method_for_class(
                    method, base_indent
                )
                result.extend(formatted_method)

        return "\n".join(result)

    @staticmethod
    def _format_method_for_class(method_code: str, base_indent: str) -> List[str]:
        result = []
        lines = method_code.strip().split("\n")

        # Find the base indentation in the original method code
        original_indent = None
        for line in lines:
            if line.strip() and line.strip().startswith("def "):
                original_indent = line[: len(line) - len(line.lstrip())]
                break

        # If we couldn't find any indentation, assume none
        original_indent = original_indent or ""

        # Process each line
        for line in lines:
            if not line.strip():
                result.append("")  # Preserve empty lines
                continue

            # Remove original indentation if present
            if line.startswith(original_indent):
                line_content = line[len(original_indent) :]
            else:
                line_content = line.lstrip()

            # Calculate appropriate indentation based on content
            if line_content.startswith("def "):
                # Method definition gets base indent
                result.append(f"{base_indent}{line_content}")
            elif line_content.startswith("@"):
                # Decorator gets base indent
                result.append(f"{base_indent}{line_content}")
            else:
                # Method body gets base indent + extra indent
                result.append(f"{base_indent}{base_indent}{line_content}")

        return result


    @staticmethod
    def format_method(method_code: str, base_indent: str = '    ') -> str:
        lines = method_code.strip().split('\n')
        if not lines:
            return ""

        result = []
        in_decorator = False
        body_indent = base_indent + "    "

        # First pass - identify decorators and the method signature
        decorator_lines = []
        signature_index = -1

        for i, line in enumerate(lines):
            if line.lstrip().startswith('@'):
                decorator_lines.append(i)
            elif line.lstrip().startswith('def '):
                signature_index = i
                break

        # Process the lines
        for i, line in enumerate(lines):
            line_strip = line.strip()
            if not line_strip:
                result.append("")
                continue

            if i in decorator_lines:
                # Format decorator
                result.append(f"{base_indent}{line_strip}")
            elif i == signature_index:
                # Format method signature
                result.append(f"{base_indent}{line_strip}")
            else:
                # Format method body with correct indentation
                result.append(f"{body_indent}{line_strip}")

        return "\n".join(result)

    @staticmethod
    def extract_method_code(code: str, method_name: str) -> Optional[str]:
        """
        Extract complete method code from class code.
        
        Args:
            code: Complete class code
            method_name: Name of the method to extract
            
        Returns:
            Complete method code or None if not found
        """
        # Pattern to match method with decorators
        pattern = f'((?:\\s*@[^\\n]+\\n+)*\\s*(?:async\\s+)?def\\s+{re.escape(method_name)}\\s*\\([^\\n]*\\).*?(?:\\n(?:(?!\\n\\s*(?:def|class|@)\\b)[^\\n]*))*)(?=\\n\\s*(?:def|class|@)\\b|$)'
        match = re.search(pattern, code, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    @staticmethod
    def normalize_spacing(code: str, max_consecutive_blank_lines: int = 2) -> str:
        """
        Normalize spacing in code to avoid excessive blank lines.
        
        Args:
            code: Code to normalize
            max_consecutive_blank_lines: Maximum number of consecutive blank lines to allow
            
        Returns:
            Normalized code
        """
        # Normalize line endings
        normalized = code.replace('\r\n', '\n')
        
        # Avoid excessive blank lines
        while '\n' * (max_consecutive_blank_lines + 1) in normalized:
            normalized = normalized.replace('\n' * (max_consecutive_blank_lines + 1), '\n' * max_consecutive_blank_lines)
            
        return normalized