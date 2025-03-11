"""
Base class for processors using the diff-match-patch algorithm.
"""
import re
from rich.console import Console
console = Console()
try:
    from diff_match_patch import diff_match_patch
    DMP_AVAILABLE = True
except ImportError:
    console.print('[yellow]diff-match-patch library is not available. Processors using this algorithm will be disabled.[/yellow]')
    console.print('[yellow]To install: pip install diff-match-patch[/yellow]')
    DMP_AVAILABLE = False

class BaseDiffMatchPatchProcessor:
    """
    Base class for processors using the diff-match-patch algorithm.
    Contains common functionality for method and function processors.
    """
    MAX_EMPTY_LINES = 2
    MIN_EMPTY_LINES = 2

    def _detect_base_indent(self, content: str) -> str:
        """
        Detects the base indentation in a given code fragment.
        """
        for line in content.splitlines():
            if line.strip():
                indent = line[:len(line) - len(line.lstrip())]
                if indent:
                    return indent
        return "    "

    def _format_with_indent(
        self, content: str, base_indent: str, body_indent: str = None
    ) -> str:
        """
        Formats the code with the appropriate indentation.

        Args:
            content: The code content to format.
            base_indent: The base indentation for the first line.
            body_indent: The indentation for the rest of the code (defaults to base_indent + 4 spaces).

        Returns:
            The formatted code with the correct indentation.
        """
        if body_indent is None:
            body_indent = base_indent + "    "

        lines = content.strip().splitlines()
        if not lines:
            return ""

        # Extract decorators
        decorators = []
        remaining_lines = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("@"):
                decorators.append(line)
                i += 1
            else:
                remaining_lines = lines[i:]
                break

        # If there are no decorators, use the original method
        if not decorators:
            return self._format_without_decorators(content, base_indent, body_indent)

        # Format the function/method part
        remaining_content = "\n".join(remaining_lines)
        formatted_function = self._format_without_decorators(
            remaining_content, base_indent, body_indent
        )

        # Format the decorators
        formatted_decorators = "\n".join(
            f"{base_indent}{decorator}" for decorator in decorators
        )

        # Combine decorators with the formatted function
        return f"{formatted_decorators}\n{formatted_function}"

    def _format_without_decorators(
        self, content: str, base_indent: str, body_indent: str = None
    ) -> str:
        """
        Formats the code without decorators with the appropriate indentation,
        preserving the structure of nested blocks.

        Args:
            content: The code content to format.
            base_indent: The base indentation for the first line.
            body_indent: The indentation for the rest of the code (defaults to base_indent + 4 spaces).

        Returns:
            The formatted code with proper indentation.
        """
        if body_indent is None:
            body_indent = base_indent + "    "

        lines = content.strip().splitlines()
        if not lines:
            return ""

        # Format first line (function/method definition)
        formatted = [f"{base_indent}{lines[0].strip()}"]

        if len(lines) == 1:
            return formatted[0]

        # Determine the base indentation level in the original code
        original_base_indent = None
        for i in range(1, len(lines)):
            line = lines[i]
            if line.strip():
                original_base_indent = len(line) - len(line.lstrip())
                break

        if original_base_indent is None:
            original_base_indent = 4  # Default if we can't detect

        # Process each line preserving relative indentation
        for i in range(1, len(lines)):
            line = lines[i]
            if not line.strip():
                formatted.append("")
                continue

            # Calculate the relative indentation compared to the base level
            current_indent = len(line) - len(line.lstrip())

            if current_indent >= original_base_indent:
                # Line is part of the body - preserve its relative indentation
                relative_indent = current_indent - original_base_indent
                new_indent = body_indent + " " * relative_indent
                formatted.append(f"{new_indent}{line.lstrip()}")
            else:
                # Line has less indentation than the base (might be a new definition)
                # In most cases, we'll append with body_indent
                formatted.append(f'{body_indent}{line.lstrip()}')

        return '\n'.join(formatted)

    def _normalize_empty_lines(self, text: str, count: int=None) -> str:
        """
        Normalizes the number of empty lines to a specified value.
        If count is None, uses MIN_EMPTY_LINES.
        """
        if count is None:
            count = self.MIN_EMPTY_LINES
        newline_count = min(text.count('\n'), count)
        return '\n' * max(self.MIN_EMPTY_LINES, newline_count)

    def _ensure_empty_lines(self, text: str, min_count: int=None) -> str:
        """
        Ensures a minimum number of empty lines at the end of text.
        """
        if min_count is None:
            min_count = self.MIN_EMPTY_LINES
        stripped = text.rstrip()
        if not stripped.endswith('\n' * min_count):
            return stripped + '\n' * min_count
        return text

    def _find_function_boundaries(self, content: str, function_name: str):
        """
        Searches for the boundaries of a function with the given name in the code.
        Returns a tuple:
          (function_start, function_end, function_content, indent)
        or (None, None, None, None) if the function is not found.
        """
        pattern = f'(^|\\n)([ \\t]*)(async\\s+)?def\\s+{re.escape(function_name)}\\s*\\('
        match = re.search(pattern, content)
        if not match:
            return (None, None, None, None)
        prefix = match.group(1)
        if prefix == '\n':
            function_start = match.start(1)
        else:
            function_start = match.start()
        indent = match.group(2)
        lines = content[function_start:].splitlines(keepends=True)
        function_lines = []
        for (i, line) in enumerate(lines):
            if i == 0:
                function_lines.append(line)
            elif line.strip() == '':
                function_lines.append(line)
            else:
                current_indent = len(line) - len(line.lstrip())
                if current_indent > len(indent):
                    function_lines.append(line)
                else:
                    break
        function_content = ''.join(function_lines)
        function_end = function_start + len(function_content)
        return (function_start, function_end, function_content, indent)