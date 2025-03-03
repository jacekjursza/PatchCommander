"""
User interaction and confirmation utilities for code changes.
"""
import difflib
from typing import List
from rich.console import Console
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.panel import Panel
from rich import box
from rich.table import Table
from patchcommander.core.config import config

console = Console()

def confirm_and_apply_change(file_path: str, new_content: str, description: str, pending_changes: List) -> bool:
    """
    Display a diff of proposed changes and ask for user confirmation.

    Args:
        file_path: Path to the file to be modified
        new_content: New content to be written to the file
        description: Description of the change
        pending_changes: List to append confirmed changes to

    Returns:
        bool: True if change was confirmed, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            old_content = f.read()
    except FileNotFoundError:
        old_content = ''
        console.print(f"[yellow]File {file_path} will be created[/yellow]")

    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"current: {file_path}",
        tofile=f"new: {file_path}",
        lineterm=''
    ))

    if not diff_lines:
        console.print(f"[yellow]No changes detected for {description}.[/yellow]")
        return True

    # Display diff with syntax highlighting
    diff_text = '\n'.join(diff_lines)
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
    panel = Panel(
        syntax,
        title=f"Changes for: {description}",
        border_style="blue",
        box=box.DOUBLE
    )
    console.print(panel)

    # Ask for confirmation
    answer = Prompt.ask(
        f"Apply changes to {file_path}?",
        choices=["y", "n", "s", "d"],
        default="y"
    )

    if answer.lower() == 'y':
        pending_changes.append((file_path, new_content, description))
        console.print(f"[green]Change scheduled for {file_path}.[/green]")
        return True
    elif answer.lower() == 's':
        console.print(f"[yellow]Skipping changes to {file_path} for now. You can review them again later.[/yellow]")
        return False
    elif answer.lower() == 'd':
        # Side-by-side diff view
        console.print("\n[bold]Side-by-side diff view:[/bold]")
        side_diff = generate_side_by_side_diff(old_lines, new_lines, file_path)
        console.print(side_diff)

        # Ask again after showing detailed diff
        second_answer = Prompt.ask(
            f"Apply changes to {file_path}?",
            choices=["y", "n", "s"],
            default="y"
        )

        if second_answer.lower() == 'y':
            pending_changes.append((file_path, new_content, description))
            console.print(f"[green]Change scheduled for {file_path}.[/green]")
            return True
        elif second_answer.lower() == 's':
            console.print(f"[yellow]Skipping changes to {file_path} for now. You can review them again later.[/yellow]")
            return False
        else:
            console.print(f"[yellow]Changes to {file_path} rejected.[/yellow]")
            return False
    else:
        console.print(f"[yellow]Changes to {file_path} rejected.[/yellow]")
        return False


def confirm_simple_action(message: str, default: str = "y") -> bool:
    """
    Ask for user confirmation for a simple action.

    Args:
        message: Message to display to the user
        default: Default answer (y/n)

    Returns:
        bool: True if action was confirmed, False otherwise
    """
    if config.get('default_yes_to_all', False):
        console.print(f"[blue]{message} (Automatically answered 'y' due to default_yes_to_all setting)[/blue]")
        return True

    answer = Prompt.ask(
        f"{message} (y/n)",
        choices=["y", "n"],
        default=default
    )
    return answer.lower() == 'y'


def generate_side_by_side_diff(old_lines: List[str], new_lines: List[str], file_path: str) -> Table:
    """
    Generate a side-by-side diff view.

    Args:
        old_lines: List of lines from the original file
        new_lines: List of lines from the new file
        file_path: Path to the file being modified

    Returns:
        Rich Table object with side-by-side diff
    """
    from rich.text import Text
    import difflib

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
    table.add_column(f"Current: {file_path}", style="cyan", width=None)
    table.add_column(f"New: {file_path}", style="green", width=None)

    max_context_lines = config.get('max_diff_context_lines', 3)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # Limit the number of context lines to reduce output size
            context_lines = min(max_context_lines, i2 - i1)

            if context_lines > 0:
                # First context line
                table.add_row(
                    Text(old_lines[i1], style="dim"),
                    Text(new_lines[j1], style="dim")
                )

                # If we have more than 3 equal lines, show ellipsis
                if context_lines > 1 and i2 - i1 > 3:
                    table.add_row(
                        Text("...", style="dim"),
                        Text("...", style="dim")
                    )

                # Last context line if we have more than 1 line
                if context_lines > 1 and i1 + 1 < i2:
                    table.add_row(
                        Text(old_lines[i2-1], style="dim"),
                        Text(new_lines[j2-1], style="dim")
                    )

        elif tag == 'replace':
            # Changed lines
            for line_num in range(max(i2 - i1, j2 - j1)):
                old_idx = i1 + line_num if line_num < i2 - i1 else None
                new_idx = j1 + line_num if line_num < j2 - j1 else None

                old_line = Text(old_lines[old_idx], style="red") if old_idx is not None else Text("")
                new_line = Text(new_lines[new_idx], style="green") if new_idx is not None else Text("")

                table.add_row(old_line, new_line)

        elif tag == 'delete':
            # Deleted lines
            for line_num in range(i1, i2):
                table.add_row(
                    Text(old_lines[line_num], style="red"),
                    Text("", style="")
                )

        elif tag == 'insert':
            # Added lines
            for line_num in range(j1, j2):
                table.add_row(
                    Text("", style=""),
                    Text(new_lines[line_num], style="green")
                )

    return table