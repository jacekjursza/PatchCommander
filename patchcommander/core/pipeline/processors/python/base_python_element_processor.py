"""
Base processor for Python code elements (functions and methods).
Provides common functionality for both function and method processors.
"""
import re
from rich.console import Console
from .base_diff_match_patch import BaseDiffMatchPatchProcessor
from ...processor_base import Processor
from ...models import PatchOperation, PatchResult
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
                
        return decorators, '\n'.join(remaining_lines)

    def _format_element_with_decorators(self, content: str, base_indent: str, body_indent: str=None) -> str:
        """
        Formats a code element with proper indentation, handling decorators correctly.
        
        Args:
            content: Code content to format
            base_indent: Base indentation for the element definition line
            body_indent: Indentation for the body (defaults to base_indent + 4 spaces)
            
        Returns:
            Formatted code with proper indentation
        """
        decorators, remaining_content = self._detect_element_decorators(content)
        
        # Format the main element (without decorators)
        formatted_element = self._format_without_decorators(remaining_content, base_indent, body_indent)
        if not formatted_element:
            return ""
            
        # Format decorators
        if not decorators:
            return formatted_element
            
        formatted_decorators = '\n'.join(f'{base_indent}{decorator}' for decorator in decorators)
        
        # Combine decorators with the element
        return f'{formatted_decorators}\n{formatted_element}'

    def _find_element_boundaries(self, content: str, element_pattern: str) -> tuple:
        """
        Finds the boundaries of a code element (function or method) using the given pattern.
        
        Args:
            content: The code content to search in
            element_pattern: Regex pattern to match the element
            
        Returns:
            Tuple of (start_position, end_position, element_content, indentation)
            or (None, None, None, None) if element not found
        """
        matches = list(re.finditer(element_pattern, content, re.MULTILINE))
        if not matches:
            return None, None, None, None
            
        match = matches[-1]  # Use the last match in case there are multiple matches
        
        # Determine the start position
        prefix = match.group(1) if len(match.groups()) > 0 else ''
        if prefix == '\n':
            element_start = match.start(1)
        else:
            element_start = match.start()
            
        # Get the indentation
        indentation = match.group(2) if len(match.groups()) > 1 else ''
        
        # Look for decorators before the function/method definition
        decorator_start = element_start
        # Backtrack to find decorators
        pos = element_start - 1
        decorator_lines = []
        
        # Go back until we find a non-decorator line or beginning of content
        while pos >= 0:
            # Find the start of the current line
            line_start = content.rfind('\n', 0, pos)
            if line_start == -1:  # We're at the beginning of content
                line_start = 0
            else:
                line_start += 1  # Skip the newline character
                
            line = content[line_start:pos+1].strip()
            
            # If line is a decorator that belongs to our function (has correct indentation)
            if line.startswith('@') and (line_start == 0 or content[line_start-1:line_start] == '\n'):
                # Check indentation
                spaces_before = len(content[line_start:]) - len(content[line_start:].lstrip())
                if spaces_before == len(indentation):
                    decorator_start = line_start
                    decorator_lines.insert(0, line)
                    pos = line_start - 1
                    continue
            
            # If we reach this point, we've found a non-decorator line
            break
        
        # Find the end of the element
        rest_of_content = content[match.end():]
        
        # Pattern to find the next element at the same or lower indentation level
        next_element_pattern = f"(\\n|^)({re.escape(indentation)}(class|def)\\s+|{re.escape(indentation[:-4] if len(indentation) >= 4 else '')}(class|def)\\s+)"
        next_element_match = re.search(next_element_pattern, rest_of_content)
        
        if next_element_match:
            element_end = match.end() + next_element_match.start()
            if next_element_match.group(1) == '\n':
                element_end += 1
        else:
            element_end = len(content)
            
        element_content = content[decorator_start:element_end]
        
        return decorator_start, element_end, element_content, indentation

    def _normalize_whitespace(self, content: str, element_content: str, 
                             new_element_content: str) -> tuple:
        """
        Normalizes whitespace before and after the element to ensure consistent formatting.
        
        Args:
            content: The full content being modified
            element_content: The original element content
            new_element_content: The new element content to insert
            
        Returns:
            Tuple of (prefix, normalized_element, suffix)
        """
        # Count empty lines before the element
        element_start = content.find(element_content)
        pos = element_start - 1
        empty_lines_before = 0
        
        while pos >= 0 and content[pos] == '\n':
            empty_lines_before += 1
            pos -= 1
            
        # Count empty lines after the element
        element_end = element_start + len(element_content)
        pos = element_end
        empty_lines_after = 0
        
        while pos < len(content) and content[pos] == '\n':
            empty_lines_after += 1
            pos += 1
            
        # Normalize empty lines to consistency
        normalized_lines_before = '\n' * max(2, min(empty_lines_before, self.MAX_EMPTY_LINES))
        normalized_lines_after = '\n' * max(2, min(empty_lines_after, self.MAX_EMPTY_LINES))
        
        # Split the content
        prefix = content[:element_start - empty_lines_before]
        suffix = content[element_end + empty_lines_after:]
        
        # Ensure proper line endings
        if prefix and not prefix.endswith('\n'):
            prefix += '\n'
        if suffix and not suffix.startswith('\n'):
            suffix = '\n\n' + suffix
            
        return prefix, normalized_lines_before + new_element_content + normalized_lines_after, suffix

    def _replace_element(self, content: str, element_name: str, element_pattern: str, 
                        new_element_content: str, indentation: str=None) -> str:
        """
        Replaces an element (function or method) in the given content.
        
        Args:
            content: Content to modify
            element_name: Name of the element to replace
            element_pattern: Regex pattern to find the element
            new_element_content: New content for the element
            indentation: Optional indentation to use (detected if not provided)
            
        Returns:
            Modified content with the element replaced
        """
        # Find the element
        element_start, element_end, element_content, detected_indent = self._find_element_boundaries(content, element_pattern)
        
        if element_start is None:
            # Element not found
            return None
            
        console.print(f"[green]Found element '{element_name}' at position {element_start}-{element_end}[/green]")
        
        # Use provided indentation or detected one
        indent = indentation or detected_indent
        
        # Format the new element with proper indentation
        formatted_element = self._format_without_decorators(new_element_content, indent)
        
        # Handle whitespace
        prefix, normalized_element, suffix = self._normalize_whitespace(content, element_content, formatted_element)
        
        # Combine everything
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
        # Format the new element
        indent = indentation or ''
        formatted_element = self._format_element_with_decorators(new_element_content, indent)
        
        # Determine where to add the element
        if not content:
            return formatted_element
            
        # Add proper spacing
        if content.endswith('\n\n'):
            separator = ''
        elif content.endswith('\n'):
            separator = '\n'
        else:
            separator = '\n\n'
            
        return content + separator + formatted_element + '\n\n'