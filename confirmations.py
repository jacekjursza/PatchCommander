import difflib
from rich.console import Console
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich import box
from rich.panel import Panel
console = Console()

def confirm_and_apply_change(file_path, new_content, description, pending_changes):
    """
    Display a diff of proposed changes and ask for user confirmation.
    Args:
        file_path (str): Path to the file to be modified\
        new_content (str): New content to be written to the file
        description (str): Description of the change
        pending_changes (list): List to append confirmed changes to
    Returns:
        bool: True if change was confirmed, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            old_content = f.read()
    except FileNotFoundError:
        old_content = ''
        console.print(f'[yellow]File {file_path} will be created[/yellow]')
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    diff_lines = list(difflib.unified_diff(old_lines, new_lines, fromfile=f'current: {file_path}', tofile=f'new: {file_path}', lineterm=''))
    if not diff_lines:
        console.print(f'[yellow]No changes detected for {description}.[/yellow]')
        return True
    diff_text = '\n'.join(diff_lines)
    syntax = Syntax(diff_text, 'diff', theme='monokai', line_numbers=True)
    panel = Panel(syntax, title=f'Changes for: {description}', border_style='blue', box=box.DOUBLE)
    console.print(panel)
    answer = Prompt.ask(f'Apply changes to {file_path}?', choices=['y', 'n', 's'], default='y')
    if answer.lower() == 'y':
        pending_changes.append((file_path, new_content, description))
        console.print(f'[green]Change scheduled for {file_path}.[/green]')
        return True
    elif answer.lower() == 's':
        console.print(f'[yellow]Skipping changes to {file_path} for now. You can review them again later.[/yellow]')
        return False
    else:
        console.print(f'[yellow]Changes to {file_path} rejected.[/yellow]')
        return False

def confirm_simple_action(message):
    """
    Ask for user confirmation for a simple action.
    Args:
        message (str): Message to display to the user
    Returns:
        bool: True if action was confirmed, False otherwise
    """
    answer = Prompt.ask(f'{message} (y/n)', choices=['y', 'n'], default='y')
    return answer.lower() == 'y'

def generate_side_by_side_diff(old_lines, new_lines, file_path):
    from rich.table import Table
    from rich.text import Text
    import difflib
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    table = Table(show_header=True, header_style='bold', box=box.SIMPLE)
    table.add_column(f'Current: {file_path}', style='cyan', width=None)
    table.add_column(f'New: {file_path}', style='green', width=None)
    for (tag, i1, i2, j1, j2) in matcher.get_opcodes():
        if tag == 'equal':
            context_lines = min(3, i2 - i1)
            if context_lines > 0:
                table.add_row(Text(old_lines[i1], style='dim'), Text(new_lines[j1], style='dim'))
                if context_lines > 2:
                    if i2 - i1 > 3:
                        table.add_row(Text('...', style='dim'), Text('...', style='dim'))
                if context_lines > 1 and i1 + 1 < i2:
                    table.add_row(Text(old_lines[i2 - 1], style='dim'), Text(new_lines[j2 - 1], style='dim'))
        elif tag == 'replace':
            for line_num in range(max(i2 - i1, j2 - j1)):
                old_idx = i1 + line_num if line_num < i2 - i1 else None
                new_idx = j1 + line_num if line_num < j2 - j1 else None
                old_line = Text(old_lines[old_idx], style='red') if old_idx is not None else Text('')
                new_line = Text(new_lines[new_idx], style='green') if new_idx is not None else Text('')
                table.add_row(old_line, new_line)
        elif tag == 'delete':
            for line_num in range(i1, i2):
                table.add_row(Text(old_lines[line_num], style='red'), Text('', style=''))
        elif tag == 'insert':
            for line_num in range(j1, j2):
                table.add_row(Text('', style=''), Text(new_lines[line_num], style='green'))
    return table