from patchcommander.core.console import console
from patchcommander.core.tag_parser import Tag


class TagProcessor:
    """Base class for tag tag_processors."""

    def __init__(self, tag: Tag):
        """
        Initialize a tag processor.

        Args:
            tag: Tag to process
        """
        self.tag = tag

    def process(self) -> bool:
        """
        Process the tag and apply changes.

        Returns:
            bool: True if processing was successful, False otherwise
        """
        raise NotImplementedError('Tag tag_processors must implement the process method')

    def _sanitize_path(self, path: str) -> str:
        """
        Sanitize a file path by replacing invalid characters with underscores.

        Args:
            path: Path to sanitize

        Returns:
            Sanitized path
        """
        if not path:
            return path
        sanitized_path = path
        for char in '<>':
            if char in sanitized_path:
                sanitized_path = sanitized_path.replace(char, '_')
                console.print(f'[yellow]Warning: Replaced invalid character "{char}" in path with underscore.[/yellow]')
        return sanitized_path

    def _validate_file_path(self, file_path: str) -> bool:
        """
        Validate that a file path is properly formatted and safe.

        Args:
            file_path: Path to validate

        Returns:
            bool: True if path is valid, False otherwise
        """
        if not file_path:
            console.print('[bold red]Path cannot be empty.[/bold red]')
            return False
        import os
        normalized_path = os.path.normpath(file_path)
        if '..' in normalized_path.split(os.sep):
            console.print('[bold red]Path traversal detected. Please use absolute paths.[/bold red]')
            return False
        if os.name == 'nt':
            invalid_chars = '<>|?*"'
            if any((c in invalid_chars for c in file_path)):
                console.print(f'[yellow]Warning: Path contains potentially invalid characters for Windows: {invalid_chars}[/yellow]')
                return True
        else:
            invalid_chars = '<>'
            if any((c in invalid_chars for c in file_path)):
                console.print(f'[yellow]Warning: Path contains potentially invalid characters: {invalid_chars}[/yellow]')
                return True
        return True
