"""
Base processor for Python code elements (functions and methods).
Provides common functionality for both function and method processors.
"""
import re

from rich.console import Console

from .base_diff_match_patch import BaseDiffMatchPatchProcessor
from .....parsers.python_parser import PythonParser

console = Console()

class BasePythonElementProcessor(BaseDiffMatchPatchProcessor):
    """
    Base class for processors handling Python code elements (functions and methods).
    Provides common functionality for finding, formatting, and replacing code elements.
    """

    def __init__(self):
        """Initialize with default values."""
        super().__init__()
        self.parser = PythonParser()

    def _detect_element_decorators(self, content: str) -> tuple:
        """
        Detects and extracts decorators from a function or method definition.
        
        Args:
            content: The code content to analyze
            
        Returns:
            Tuple containing a list of decorators and the remaining code
        """
        lines = content.strip().splitlines()
        decorators = []
        remaining_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('@'):
                decorators.append(line)
                i += 1
            else:
                remaining_lines = lines[i:]
                break
        return (decorators, '\n'.join(remaining_lines))

    def _format_element_with_decorators(self, content: str, base_indent: str, body_indent: str=None) -> str:
        """
        Formats a code element (function/method) with correct indentation, taking into account decorators.

        Args:
            content: The code content to format.
            base_indent: The base indentation for the definition line.
            body_indent: The indentation for the body (defaults to base_indent + 4 spaces).

        Returns:
            The formatted code with the proper indentation.
        """
        if body_indent is None:
            body_indent = base_indent + '    '
        (decorators, remaining_content) = self._detect_element_decorators(content)
        formatted_element = self._format_without_decorators(remaining_content, base_indent, body_indent)
        if not formatted_element:
            return ''
        if not decorators:
            return formatted_element
        formatted_decorators = '\n'.join((f'{base_indent}{decorator}' for decorator in decorators))
        return f'{formatted_decorators}\n{formatted_element}'

    def _find_element_boundaries_ast(self, content: str, element_name: str, is_method: bool = False, class_name: str = None) -> tuple:
        """
        Find element boundaries using AST parsing for more accurate results, especially with complex docstrings.
        
        Args:
            content: The code content to search
            element_name: The name of the element (function/method) to find
            is_method: Whether the element is a method (vs a standalone function)
            class_name: The name of the class (only needed for methods)
            
        Returns:
            Tuple of (start_position, end_position, element_content, indentation)
            or (None, None, None, None) if element not found
        """
        try:
            import ast
            import asttokens
            import io
            
            # Try to use asttokens if available for more precise source mapping
            try:
                atok = asttokens.ASTTokens(content, parse=True)
                tree = atok.tree
                have_atok = True
            except (ImportError, Exception):
                have_atok = False
                tree = ast.parse(content)
            
            # Find the class first if this is a method
            target_class = None
            if is_method and class_name:
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == class_name:
                        target_class = node
                        break
                
                if not target_class:
                    return (None, None, None, None)
                
                # Search for the method within the class
                for node in ast.walk(target_class):
                    if (isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef)) and node.name == element_name:
                        if have_atok:
                            start_pos = atok.get_text_range(node)[0]
                            end_pos = atok.get_text_range(node)[1]
                        else:
                            # Fallback to line/col info which is less precise
                            start_line = node.lineno
                            end_line = node.end_lineno if hasattr(node, 'end_lineno') else None
                            
                            if end_line is None:
                                # Find the last line by visiting all child nodes
                                end_line = start_line
                                for child in ast.walk(node):
                                    if hasattr(child, 'lineno'):
                                        end_line = max(end_line, child.lineno)
                            
                            # Map line numbers to positions
                            lines = content.splitlines(True)
                            start_pos = sum(len(lines[i]) for i in range(start_line - 1))
                            end_pos = sum(len(lines[i]) for i in range(end_line))
                        
                        # Find decorators
                        decorator_start = start_pos
                        for decorator in node.decorator_list:
                            dec_line = decorator.lineno if hasattr(decorator, 'lineno') else start_line
                            if dec_line < start_line:
                                if have_atok:
                                    dec_start = atok.get_text_range(decorator)[0]
                                    if dec_start < decorator_start:
                                        decorator_start = dec_start
                                else:
                                    # Approximate decorator position
                                    decorator_start = min(decorator_start, 
                                                         sum(len(lines[i]) for i in range(dec_line - 1)))
                        
                        # Extract text and indentation
                        element_content = content[decorator_start:end_pos]
                        indentation = ' ' * (node.col_offset if hasattr(node, 'col_offset') else 0)
                        
                        return (decorator_start, end_pos, element_content, indentation)
            else:
                # Search for standalone function
                for node in ast.walk(tree):
                    if (isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef)) and node.name == element_name:
                        if have_atok:
                            start_pos = atok.get_text_range(node)[0]
                            end_pos = atok.get_text_range(node)[1]
                        else:
                            # Fallback to line/col info
                            start_line = node.lineno
                            end_line = node.end_lineno if hasattr(node, 'end_lineno') else None
                            
                            if end_line is None:
                                end_line = start_line
                                for child in ast.walk(node):
                                    if hasattr(child, 'lineno'):
                                        end_line = max(end_line, child.lineno)
                            
                            lines = content.splitlines(True)
                            start_pos = sum(len(lines[i]) for i in range(start_line - 1))
                            end_pos = sum(len(lines[i]) for i in range(end_line))
                        
                        # Find decorators
                        decorator_start = start_pos
                        for decorator in node.decorator_list:
                            dec_line = decorator.lineno if hasattr(decorator, 'lineno') else start_line
                            if dec_line < start_line:
                                if have_atok:
                                    dec_start = atok.get_text_range(decorator)[0]
                                    if dec_start < decorator_start:
                                        decorator_start = dec_start
                                else:
                                    decorator_start = min(decorator_start, 
                                                         sum(len(lines[i]) for i in range(dec_line - 1)))
                        
                        element_content = content[decorator_start:end_pos]
                        indentation = ' ' * (node.col_offset if hasattr(node, 'col_offset') else 0)
                        
                        return (decorator_start, end_pos, element_content, indentation)
            
            return (None, None, None, None)
            
        except Exception as e:
            # Fallback to regex-based approach on parsing errors
            import traceback
            print(f"AST parsing error: {e}")
            print(traceback.format_exc())
            return (None, None, None, None)

    def _find_element_boundaries(self, content: str, element_pattern: str, element_name: str = None, is_method: bool = False, class_name: str = None) -> tuple:
        """
        Finds the boundaries of a code element (function or method) using AST first, then falling back to regex.

        Args:
            content: The code content to search in
            element_pattern: Regex pattern to match the element
            element_name: Name of the element to find (for AST parsing)
            is_method: Whether this is a method (for AST parsing)
            class_name: Name of the class (for method AST parsing)

        Returns:
            Tuple of (start_position, end_position, element_content, indentation)
            or (None, None, None, None) if element not found
        """
        # Try AST first if we have element_name
        if element_name:
            result = self._find_element_boundaries_ast(content, element_name, is_method, class_name)
            if result[0] is not None:
                return result
        
        # Fall back to regex approach
        matches = list(re.finditer(element_pattern, content, re.MULTILINE))
        if not matches:
            return (None, None, None, None)
        match = matches[-1]
        prefix = match.group(1) if len(match.groups()) > 0 else ''
        if prefix == '\n':
            element_start = match.start(1)
        else:
            element_start = match.start()
        indentation = match.group(2) if len(match.groups()) > 1 else ''
        decorator_start = element_start
        pos = element_start - 1
        decorator_lines = []
        while pos >= 0:
            line_start = content.rfind('\n', 0, pos)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            line = content[line_start:pos + 1].strip()
            if line.startswith('@') and (line_start == 0 or content[line_start - 1:line_start] == '\n'):
                spaces_before = len(content[line_start:]) - len(content[line_start:].lstrip())
                if spaces_before == len(indentation):
                    decorator_start = line_start
                    decorator_lines.insert(0, line)
                    pos = line_start - 1
                    continue
            break
        rest_of_content = content[match.end():]
        next_element_pattern = f"(\\n|^)({re.escape(indentation)}((?:async\\s+)?class|(?:async\\s+)?def)\\s+|{re.escape(indentation[:-4] if len(indentation) >= 4 else '')}((?:async\\s+)?class|(?:async\\s+)?def)\\s+)"
        next_element_match = re.search(next_element_pattern, rest_of_content)
        if next_element_match:
            element_end = match.end() + next_element_match.start()
            if next_element_match.group(1) == '\n':
                element_end += 1
        else:
            element_end = len(content)
        element_content = content[decorator_start:element_end]
        return (decorator_start, element_end, element_content, indentation)

    def _normalize_whitespace(self, content: str, element_content: str, new_element_content: str) -> tuple:
        """
        Normalizes whitespace before and after the element to ensure consistent formatting.

        Args:
            content: The full content being modified
            element_content: The original element content
            new_element_content: The new element content to insert

        Returns:
            Tuple of (prefix, normalized_element, suffix)
        """
        element_start = content.find(element_content)
        pos = element_start - 1
        empty_lines_before = 0
        while pos >= 0 and content[pos] == '\n':
            empty_lines_before += 1
            pos -= 1
        element_end = element_start + len(element_content)
        pos = element_end
        empty_lines_after = 0
        while pos < len(content) and content[pos] == '\n':
            empty_lines_after += 1
            pos += 1
        is_class_next = False
        if element_end + empty_lines_after < len(content):
            next_lines = content[element_end + empty_lines_after:].lstrip()
            if next_lines.startswith('class '):
                is_class_next = True
        normalized_lines_before = '\n' * min(max(1, empty_lines_before), 2)
        if is_class_next:
            normalized_lines_after = '\n\n'
        else:
            normalized_lines_after = '\n' * min(max(2, empty_lines_after), 3)
        prefix = content[:element_start - empty_lines_before]
        suffix = content[element_end + empty_lines_after:]
        if prefix and (not prefix.endswith('\n')):
            prefix += '\n'
        if suffix and (not suffix.startswith('\n')):
            suffix = '\n' + suffix
        return (prefix, normalized_lines_before + new_element_content + normalized_lines_after, suffix)

    def _replace_element(self, content: str, element_name: str, element_pattern: str, new_element_content: str, indentation: str=None, is_method: bool=False, class_name: str=None) -> str:
        """
        Replaces an element (function or method) in the given content.
        
        Args:
            content: Content to modify
            element_name: Name of the element to replace
            element_pattern: Regex pattern to find the element
            new_element_content: New content for the element
            indentation: Optional indentation to use (detected if not provided)
            is_method: Whether this is a method (for AST parsing)
            class_name: Name of the class (for method AST parsing)
            
        Returns:
            Modified content with the element replaced
        """
        (element_start, element_end, element_content, detected_indent) = self._find_element_boundaries(
            content, element_pattern, element_name, is_method, class_name
        )
        if element_start is None:
            return None
        console.print(f"[green]Found element '{element_name}' at position {element_start}-{element_end}[/green]")
        indent = indentation or detected_indent
        formatted_element = self._format_without_decorators(new_element_content, indent)
        (prefix, normalized_element, suffix) = self._normalize_whitespace(content, element_content, formatted_element)
        return prefix + normalized_element + suffix

    def _handle_element_not_found(self, content: str, element_name: str, new_element_content: str, indentation: str=None) -> str:
        """
        Handles the case when an element is not found and needs to be added.

        Args:
            content: Content to modify
            element_name: Name of the element to add
            new_element_content: Content of the new element
            indentation: Indentation to use (if applicable)

        Returns:
            Modified content with the element added
        """
        indent = indentation or ''
        formatted_element = self._format_element_with_decorators(new_element_content, indent)
        if not content:
            return formatted_element + '\n\n'
        next_is_class = False
        if content.strip():
            lines = content.splitlines()
            non_empty_count = 0
            for i in range(len(lines) - 1, max(0, len(lines) - 10), -1):
                line = lines[i].strip()
                if line:
                    non_empty_count += 1
                    if line.startswith('class '):
                        next_is_class = True
                        break
                if non_empty_count >= 3:
                    break
        if content.endswith('\n\n'):
            separator = ''
        elif content.endswith('\n'):
            separator = '\n'
        else:
            separator = '\n\n'
        if next_is_class:
            return content + separator + formatted_element + '\n\n\n'
        else:
            return content + separator + formatted_element + '\n\n'