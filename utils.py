import os
import re
import sys
import pyperclip
from rich.console import Console
console = Console()

def format_size(size_bytes):
    """
    Convert bytes to human-readable size format.

    Args:
        size_bytes (int): Size in bytes

    Returns:
        str: Human-readable size string (e.g., "1.23 KB")
    """
    if size_bytes < 1024:
        return f'{size_bytes} bytes'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.2f} KB'
    elif size_bytes < 1024 * 1024 * 1024:
        return f'{size_bytes / (1024 * 1024):.2f} MB'
    else:
        return f'{size_bytes / (1024 * 1024 * 1024):.2f} GB'

def parse_attributes(attr_str):
    """
    Parse HTML/XML-like attribute string into a dictionary.

    Args:
        attr_str (str): String containing attributes in format: key="value" key2="value2"

    Returns:
        dict: Dictionary of attribute key-value pairs
    """
    if not attr_str:
        return {}
    attrs = {}
    pattern = '(\\w+)\\s*=\\s*"([^"]*)"'
    for match in re.finditer(pattern, attr_str):
        (key, value) = match.groups()
        attrs[key] = value
    return attrs

def get_input_data(filename):
    """
    Get input data from a file or clipboard if no filename is provided.

    Args:
        filename (str): Path to input file or None to use clipboard

    Returns:
        str: Content from file or clipboard

    Raises:
        SystemExit: If file not found or clipboard is empty/inaccessible
    """
    if filename:
        try:
            if not os.path.exists(filename):
                console.print(f"[bold red]File '{filename}' not found.[/bold red]")
                sys.exit(1)
            with open(filename, 'r', encoding='utf-8') as f:
                data = f.read()
            data = data.lstrip('\ufeff')
            data_size = len(data)
            size_info = f'({format_size(data_size)})'
            console.print(f'[green]Successfully loaded input from file: {filename} {size_info}[/green]')
            return data
        except Exception as e:
            console.print(f'[bold red]Error reading file {filename}: {e}[/bold red]')
            sys.exit(1)
    else:
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content.strip() == '':
                console.print('[bold yellow]Clipboard is empty. Please copy content first. Exiting.[/bold yellow]')
                sys.exit(1)
            content_size = len(clipboard_content)
            size_info = f'({format_size(content_size)})'
            console.print(f'[green]Using clipboard content as input {size_info}[/green]')
            return clipboard_content
        except Exception as e:
            console.print(f'[bold red]Clipboard functionality not available: {e}[/bold red]')
            console.print('[yellow]Make sure pyperclip is properly installed and your system supports clipboard access.[/yellow]')
            sys.exit(1)

def sanitize_path(path):
    """Sanitize a file path by replacing invalid characters with underscores."""
    if not path:
        return path
    sanitized_path = path
    for char in '<>':
        if char in sanitized_path:
            sanitized_path = sanitized_path.replace(char, '_')
            console.print(f'[yellow]Warning: Replaced invalid character "{char}" in path with underscore.[/yellow]')
    return sanitized_path