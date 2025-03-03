"""
Change management for PatchCommander v2.
Handles tracking and applying file changes.
"""
import os
import shutil
from datetime import datetime
from typing import Optional
from rich.console import Console
from patchcommander.core.config import config

console = Console()

class ChangeManager:
    """
    Manages pending changes and applies them to files.
    """

    def __init__(self):
        """Initialize an empty change manager."""
        self.pending_changes = []
        self.in_memory_files = {}

    def add_change(self, file_path: str, new_content: str, description: str) -> None:
        """
        Add a change to the pending changes list.

        Args:
            file_path: Path to the file to be modified
            new_content: New content to be written to the file
            description: Description of the change
        """
        self.pending_changes.append((file_path, new_content, description))
        self.in_memory_files[file_path] = new_content

    def get_pending_changes_count(self) -> int:
        """
        Get the number of pending changes.

        Returns:
            Number of pending changes
        """
        return len(self.pending_changes)

    def clear_pending_changes(self) -> None:
        """Clear all pending changes."""
        self.pending_changes.clear()

    def get_file_content(self, file_path: str) -> str:
        """
        Get file content either from in-memory cache or from disk.

        Args:
            file_path: Path to the file

        Returns:
            File content or empty string if file doesn't exist
        """
        if file_path in self.in_memory_files:
            return self.in_memory_files[file_path]

        if not os.path.exists(file_path):
            return ''

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            console.print(f"[bold red]Error reading file '{file_path}': {e}[/bold red]")
            return ''

    def backup_file(self, file_path: str) -> Optional[str]:
        """
        Create a backup of the specified file before modifying it.
        Respects the backup_enabled setting in configuration.

        Args:
            file_path: Path to the file to back up

        Returns:
            Path to the backup file, or None if backup wasn't needed or is disabled
        """
        if not config.get('backup_enabled', False):
            return None

        if not os.path.exists(file_path):
            return None

        backup_dir = os.path.join(os.path.dirname(file_path), '.patchcommander_backups')
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = os.path.basename(file_path)
        backup_path = os.path.join(backup_dir, f'{filename}.{timestamp}.bak')

        shutil.copy2(file_path, backup_path)
        return backup_path

    def apply_all_pending_changes(self) -> None:
        """
        Apply all pending changes that have been confirmed by the user.
        Includes syntax validation and automatic rollback for Python files.
        """
        if not self.pending_changes:
            console.print('[yellow]No changes to apply.[/yellow]')
            return

        console.print(f'[bold]Applying {len(self.pending_changes)} change(s)...[/bold]')

        # Group changes by file
        changes_by_file = {}
        for file_path, new_content, description in self.pending_changes:
            if file_path not in changes_by_file:
                changes_by_file[file_path] = []
            changes_by_file[file_path].append((new_content, description))

        success_count = 0
        total_changes = sum(len(changes) for changes in changes_by_file.values())

        # Create backups of existing files
        backups = {}
        backup_paths = {}

        for file_path in changes_by_file:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    backups[file_path] = f.read()

                backup_path = self.backup_file(file_path)
                if backup_path:
                    backup_paths[file_path] = backup_path
            else:
                backups[file_path] = ''

        # Apply changes
        for file_path, changes_list in changes_by_file.items():
            try:
                current_content = backups[file_path]

                for new_content, description in changes_list:
                    try:
                        # Create directory if it doesn't exist
                        directory = os.path.dirname(file_path)
                        if directory:
                            os.makedirs(directory, exist_ok=True)

                        # Write new content to file
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)

                        # Validate Python syntax
                        if file_path.endswith('.py') and config.get('syntax_validation', True):
                            try:
                                compile(new_content, file_path, 'exec')
                            except SyntaxError as se:
                                console.print(f'[bold red]Syntax error detected in {file_path}: {se}[/bold red]')
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(current_content)
                                console.print(f'[yellow]Reverted changes in {file_path} due to syntax error.[/yellow]')
                                continue

                        current_content = new_content
                        success_count += 1
                        console.print(f'[green]Applied change to {file_path} ({description}).[/green]')

                    except Exception as e:
                        console.print(f'[bold red]Error applying changes to {file_path}: {e}[/bold red]')

                if file_path in backup_paths:
                    console.print(f'[blue]Backup created at: {backup_paths[file_path]}[/blue]')

            except Exception as e:
                console.print(f'[bold red]Error processing changes for {file_path}: {e}[/bold red]')

                # Revert changes if there's an error
                if file_path in backups:
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(backups[file_path])
                        console.print(f'[yellow]Reverted all changes in {file_path} due to error.[/yellow]')
                    except Exception as restore_error:
                        console.print(f'[bold red]Failed to restore {file_path}: {restore_error}[/bold red]')

        console.print(f'[bold green]Successfully applied {success_count} out of {total_changes} changes.[/bold green]')
        self.clear_pending_changes()


# Create a global change manager instance
change_manager = ChangeManager()