import os
import shutil
from datetime import datetime
from rich.console import Console

console = Console()
pending_changes = []

def backup_file(file_path):
    """
    Create a backup of the specified file before modifying it.
    
    Args:
        file_path (str): Path to the file to back up
        
    Returns:
        str: Path to the backup file, or None if backup wasn't needed
    """
    if not os.path.exists(file_path):
        return None
        
    backup_dir = os.path.join(os.path.dirname(file_path), '.patchcommander_backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = os.path.basename(file_path)
    backup_path = os.path.join(backup_dir, f"{filename}.{timestamp}.bak")
    
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
    for file_path, new_content, description in pending_changes:
        changes_by_file[file_path] = (new_content, description)
    
    backups = {}
    backup_paths = {}
    
    # Create backups and store original content
    for file_path in changes_by_file:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                backups[file_path] = f.read()
            backup_path = backup_file(file_path)
            if backup_path:
                backup_paths[file_path] = backup_path
        else:
            backups[file_path] = ''
    
    # Apply changes
    success_count = 0
    for file_path, (new_content, description) in changes_by_file.items():
        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
            # Write new content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Validate Python files for syntax errors
            if file_path.endswith('.py'):
                try:
                    compile(new_content, file_path, 'exec')
                except SyntaxError as se:
                    console.print(f'[bold red]Syntax error detected in {file_path}: {se}[/bold red]')
                    
                    # Restore from backup
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(backups[file_path])
                    
                    console.print(f'[yellow]Reverted changes in {file_path} due to syntax error.[/yellow]')
                    continue
            
            success_count += 1
            console.print(f'[green]Applied change to {file_path} ({description}).[/green]')
            
            if file_path in backup_paths:
                console.print(f'[blue]Backup created at: {backup_paths[file_path]}[/blue]')
                
        except Exception as e:
            console.print(f'[bold red]Error applying changes to {file_path}: {e}[/bold red]')
            
            # Attempt to restore from backup if we have one
            if file_path in backups:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(backups[file_path])
                    console.print(f'[yellow]Reverted changes in {file_path} due to error.[/yellow]')
                except Exception as restore_error:
                    console.print(f'[bold red]Failed to restore {file_path}: {restore_error}[/bold red]')
    
    console.print(f'[bold green]Successfully applied {success_count} out of {len(changes_by_file)} changes.[/bold green]')
    pending_changes.clear()
