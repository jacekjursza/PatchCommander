"""
Utility functions for handling diffs in PatchCommander.
"""
import difflib
from typing import List, Tuple, Dict
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

def generate_unified_diff(old_content: str, new_content: str, file_path: str = "") -> List[str]:
    """
    Generates a unified diff between old and new content.

    Args:
        old_content: Original content
        new_content: New content
        file_path: File path to display in the diff header

    Returns:
        List of diff lines
    """
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    
    from_file = f"current: {file_path}" if file_path else "current"
    to_file = f"new: {file_path}" if file_path else "new"
    
    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines, fromfile=from_file, tofile=to_file, lineterm=''))
    
    return diff_lines

def display_unified_diff(old_content: str, new_content: str, file_path: str = "") -> None:
    """
    Displays a unified diff in the console.

    Args:
        old_content: Original content
        new_content: New content
        file_path: File path to display in the diff title
    """
    diff_lines = generate_unified_diff(old_content, new_content, file_path)
    
    if not diff_lines:
        console.print(f'[blue]No changes detected for {file_path}.[/blue]')
        return
    
    diff_text = '\n'.join(diff_lines)
    syntax = Syntax(diff_text, 'diff', theme='monokai', line_numbers=True)
    title = f'Changes for: {file_path}' if file_path else 'Changes'
    panel = Panel(syntax, title=title, border_style='blue', box=box.DOUBLE)
    console.print(panel)


def generate_side_by_side_diff(old_content: str, new_content: str, file_path: str='', max_context_lines: int=3) -> Table:
    """
    Generates a side-by-side diff as a Rich Table.

    Args:
        old_content: Original content
        new_content: New content
        file_path: File path to display in the table headers
        max_context_lines: Maximum number of context lines to show (default: 3)

    Returns:
        Rich Table with the side-by-side diff
    """
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    table = Table(show_header=True, header_style='bold', box=box.SIMPLE)
    from_header = f'Current: {file_path}' if file_path else 'Current'
    to_header = f'New: {file_path}' if file_path else 'New'
    table.add_column(from_header, style='cyan', width=None)
    table.add_column(to_header, style='green', width=None)
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    for (tag, i1, i2, j1, j2) in matcher.get_opcodes():
        if tag == 'equal':
            context_lines = min(max_context_lines, i2 - i1)
            if context_lines > 0:
                table.add_row(Text(old_lines[i1], style='dim'), Text(new_lines[j1], style='dim'))
                if context_lines > 1 and i2 - i1 > 3:
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


def display_side_by_side_diff(old_content: str, new_content: str, file_path: str='', max_context_lines: int=3) -> None:
    """
    Displays a side-by-side diff in the console.

    Args:
        old_content: Original content
        new_content: New content
        file_path: File path to display in the diff title
        max_context_lines: Maximum number of context lines to show (default: 3)
    """
    table = generate_side_by_side_diff(old_content, new_content, file_path, max_context_lines)
    console.print(table)



def format_with_indentation(code: str, base_indent: str, body_indent: str = None) -> str:
    """
    Formats code with the specified indentation.

    Args:
        code: Code to format
        base_indent: Base indentation for the first line
        body_indent: Indentation for the rest of the code (defaults to base_indent + 4 spaces)

    Returns:
        Formatted code with proper indentation
    """
    if body_indent is None:
        body_indent = base_indent + '    '
    
    lines = code.strip().splitlines()
    if not lines:
        return ''
    
    # Detect original indentation pattern if there are multiple lines
    original_body_indent = None
    if len(lines) > 1:
        for line in lines[1:]:
            if line.strip():
                original_body_indent = line[:len(line) - len(line.lstrip())]
                break
    
    # Format with proper indentation
    formatted = [f'{base_indent}{lines[0]}']
    for i, line in enumerate(lines[1:], 1):
        if not line.strip():
            formatted.append('')
            continue
        
        if original_body_indent and line.startswith(original_body_indent):
            line_without_indent = line[len(original_body_indent):]
            formatted.append(f'{body_indent}{line_without_indent}')
        else:
            formatted.append(f'{body_indent}{line.lstrip()}')
    
    return '\n'.join(formatted)

def normalize_empty_lines(text: str, count: int=2) -> str:
    text = text.replace('\r\n', '\n')

    # Replace sequences of count+1 or more newlines with exactly count newlines
    import re
    pattern = '\n' * (count + 1) + '+'
    replacement = '\n' * count
    while re.search(pattern, text):
        text = re.sub(pattern, replacement, text)

    return text

