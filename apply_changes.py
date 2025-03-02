import os
import shutil
from datetime import datetime
from rich.console import Console
console = Console()
pending_changes = []

def backup_file(file_path):
    """
    Create a backup of the specified file before modifying it.
    Respects the backup_enabled setting in configuration.

    Args:
        file_path (str): Path to the file to back up

    Returns:
        str: Path to the backup file, or None if backup wasn't needed or is disabled
    """
    from config import config
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

def apply_all_pending_changes():
    """
    Apply all pending changes that have been confirmed by the user.
    Includes syntax validation and automatic rollback for Python files.
    """
    if not pending_changes:
        console.print('[yellow]No changes to apply.[/yellow]')
        return
    console.print(f'[bold]Applying {len(pending_changes)} change(s)...[/bold]')
    changes_by_file = {}
    for (file_path, new_content, description) in pending_changes:
        if file_path not in changes_by_file:
            changes_by_file[file_path] = []
        changes_by_file[file_path].append((new_content, description))
    success_count = 0
    total_changes = sum((len(changes) for changes in changes_by_file.values()))
    backups = {}
    backup_paths = {}
    for file_path in changes_by_file:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                backups[file_path] = f.read()
            backup_path = backup_file(file_path)
            if backup_path:
                backup_paths[file_path] = backup_path
        else:
            backups[file_path] = ''
    for (file_path, changes_list) in changes_by_file.items():
        try:
            current_content = backups[file_path]
            for (new_content, description) in changes_list:
                try:
                    directory = os.path.dirname(file_path)
                    if directory:
                        os.makedirs(directory, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    if file_path.endswith('.py'):
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
            if file_path in backups:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(backups[file_path])
                    console.print(f'[yellow]Reverted all changes in {file_path} due to error.[/yellow]')
                except Exception as restore_error:
                    console.print(f'[bold red]Failed to restore {file_path}: {restore_error}[/bold red]')
    console.print(f'[bold green]Successfully applied {success_count} out of {total_changes} changes.[/bold green]')
    pending_changes.clear()