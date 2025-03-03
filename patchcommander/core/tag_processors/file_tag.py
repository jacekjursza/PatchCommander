from patchcommander.core.changes import change_manager
from patchcommander.core.confirmations import confirm_and_apply_change
from patchcommander.core.tag_processors.base import TagProcessor


class FileTagProcessor(TagProcessor):
    """Processor for FILE tags."""

    def process(self) -> bool:
        """
        Process a FILE tag by replacing or creating a file with new content.

        Returns:
            bool: True if processing was successful, False otherwise
        """
        file_path = self.tag.get_attribute('path')
        content = self.tag.content or ''
        file_path = self._sanitize_path(file_path)
        if not self._validate_file_path(file_path):
            return False
        new_content = content.rstrip('\n') + '\n'
        description = f'Replace entire file: {file_path}'
        change_manager.in_memory_files[file_path] = new_content
        return confirm_and_apply_change(file_path, new_content, description, change_manager.pending_changes)
