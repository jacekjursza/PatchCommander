"""
Preprocessor for removing Markdown code block markers.
"""
import re
from rich.console import Console
from ...processor_base import PreProcessor
from ...models import PatchOperation

console = Console()

class MarkdownCodeBlockCleaner(PreProcessor):
    """
    Preprocessor that removes Markdown code block markers (``` and ```python, ```css, etc.)
    from the content of tags.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the preprocessor can handle the given operation.

        Args:
            operation: The operation to check.

        Returns:
            bool: True for all operations that have text content.
        """
        # We process all operations that have some content
        return operation.content is not None and len(operation.content) > 0

    def process(self, operation: PatchOperation) -> None:
        """
        Removes Markdown code block markers from the operation's content.

        Args:
            operation: The operation to process.
        """
        if not self.can_handle(operation):
            return

        content = operation.content

        # We do nothing if there is no content
        if not content or len(content.strip()) == 0:
            return

        # We split the content into lines
        lines = content.splitlines()
        if len(lines) < 2:
            # Not enough lines to contain Markdown code blocks
            return

        # We check the first line - if it contains the opening code block marker
        first_line = lines[0].strip()
        first_line_matches = re.match(r'^```\w*$', first_line)

        # We check the last line - if it contains the closing code block marker
        last_line = lines[-1].strip()
        last_line_matches = re.match(r'^```$', last_line)

        # If both the first and the last lines match the pattern, we remove them
        if first_line_matches and last_line_matches:
            console.print("[blue]Found a Markdown code block - removing markers[/blue]")
            # We remove the first and the last lines
            lines = lines[1:-1]
            operation.content = '\n'.join(lines)
            return

        # Handling the case where only the first line is an opening marker
        if first_line_matches:
            console.print("[blue]Found the beginning of a Markdown code block - removing marker[/blue]")
            lines = lines[1:]
            operation.content = '\n'.join(lines)
            return

        # Handling the case where only the last line is a closing marker
        if last_line_matches:
            console.print("[blue]Found the end of a Markdown code block - removing marker[/blue]")
            lines = lines[:-1]
            operation.content = '\n'.join(lines)
            return

        # Let's check if there are any markers in the middle of the content
        # This can be trickier, because we need to distinguish real Markdown markers
        # from code that might contain similar patterns

        # This part is more experimental - we will remove only clear
        # Markdown code blocks that are whole lines
        modified_lines = []
        skip_next = False

        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            # We check if the line is an opening of a Markdown code block
            if re.match(r'^\s*```\w*\s*$', line):
                # Let's check if it is only a fragment of a larger code block
                # If it's a real Markdown marker, a few lines below
                # there should be a closing marker
                found_closing = False
                for j in range(i+1, min(i+20, len(lines))):
                    if re.match(r'^\s*```\s*$', lines[j]):
                        found_closing = True
                        skip_next = True
                        break

                if found_closing:
                    console.print("[blue]Found an inner Markdown code block - removing markers[/blue]")
                    continue

            modified_lines.append(line)

        if len(modified_lines) != len(lines):
            operation.content = '\n'.join(modified_lines)