import os

from patchcommander.core.changes import change_manager
from patchcommander.core.confirmations import confirm_simple_action
from patchcommander.core.console import console
from patchcommander.core.tag_processors.base import TagProcessor
from patchcommander.operations import OperationFactory


class OperationTagProcessor(TagProcessor):
    """Processor for OPERATION tags."""

    def process(self) -> bool:
        """
        Process an OPERATION tag, such as move_file, delete_file, delete_method.

        Returns:
            bool: True if processing was successful, False otherwise
        """
        action = self.tag.get_attribute('action')
        if not action:
            console.print("[bold red]OPERATION tag missing 'action' attribute.[/bold red]")
            return False
        if action == 'move_file':
            return self._handle_move_file()
        elif action == 'delete_file':
            return self._handle_delete_file()
        elif action == 'delete_method':
            return self._handle_delete_method()
        else:
            console.print(f'[bold red]Unknown operation action: {action}[/bold red]')
            return False

    def _handle_move_file(self) -> bool:
        """
        Handle move_file operation.

        Returns:
            bool: True if operation was successful, False otherwise
        """
        source = self.tag.get_attribute('source')
        target = self.tag.get_attribute('target')
        if not source or not target:
            console.print("[bold red]move_file operation requires 'source' and 'target' attributes.[/bold red]")
            return False
        source = self._sanitize_path(source)
        target = self._sanitize_path(target)
        if not os.path.exists(source) and source not in change_manager.in_memory_files:
            console.print(f"[bold red]Source file '{source}' does not exist.[/bold red]")
            return False
        if os.path.exists(target) or target in change_manager.in_memory_files:
            if not confirm_simple_action(f"Target file '{target}' already exists. Overwrite?"):
                console.print('[yellow]Move file operation cancelled.[/yellow]')
                return False
        if not confirm_simple_action(f"Move file from '{source}' to '{target}'?"):
            console.print('[yellow]Move file operation cancelled.[/yellow]')
            return False
        if source in change_manager.in_memory_files:
            content = change_manager.in_memory_files[source]
            change_manager.in_memory_files[target] = content
            del change_manager.in_memory_files[source]
        try:
            target_dir = os.path.dirname(target)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            import shutil
            if os.path.exists(source):
                shutil.move(source, target)
            console.print(f'[green]Moved file from {source} to {target}.[/green]')
            return True
        except Exception as e:
            console.print(f'[bold red]Error moving file: {e}[/bold red]')
            return False

    def _handle_delete_file(self) -> bool:
        """
        Handle delete_file operation.

        Returns:
            bool: True if operation was successful, False otherwise
        """
        source = self.tag.get_attribute('source')
        if not source:
            console.print("[bold red]delete_file operation requires 'source' attribute.[/bold red]")
            return False
        source = self._sanitize_path(source)
        if not os.path.exists(source) and source not in change_manager.in_memory_files:
            console.print(f"[bold red]File '{source}' does not exist.[/bold red]")
            return False
        if not confirm_simple_action(f"Delete file '{source}'?"):
            console.print('[yellow]Delete file operation cancelled.[/yellow]')
            return False
        if source in change_manager.in_memory_files:
            del change_manager.in_memory_files[source]
        try:
            if os.path.exists(source):
                os.remove(source)
            console.print(f'[green]Deleted file: {source}.[/green]')
            return True
        except Exception as e:
            console.print(f'[bold red]Error deleting file: {e}[/bold red]')
            return False

    def _handle_delete_method(self) -> bool:
        """
        Handle delete_method operation.

        Returns:
            bool: True if operation was successful, False otherwise
        """
        source = self.tag.get_attribute('source')
        class_name = self.tag.get_attribute('class')
        method_name = self.tag.get_attribute('method')
        if not source or not class_name or (not method_name):
            console.print("[bold red]delete_method operation requires 'source', 'class', and 'method' attributes.[/bold red]")
            return False
        source = self._sanitize_path(source)
        operation = OperationFactory.create_operation('delete_method', {'path': source, 'class': class_name, 'method': method_name})
        return operation.execute({})
