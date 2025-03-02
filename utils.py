import os
import re
import sys
import pyperclip
from rich.console import Console

from main import console

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


def display_llm_docs(include_prompt=True):
    """
    Display documentation for LLMs.

    Args:
        include_prompt (bool): Whether to include full prompt (PROMPT.md) or just syntax guide (FOR_LLM.md)
    """
    from rich.markdown import Markdown
    files_to_display = []
    if include_prompt:
        prompt_path = find_resource_file('PROMPT.md')
        if prompt_path and os.path.exists(prompt_path):
            files_to_display.append(('Developer Collaboration Prompt', prompt_path))
        else:
            console.print('[yellow]Warning: Could not find PROMPT.md file.[/yellow]')
    syntax_path = find_resource_file('FOR_LLM.md')
    if syntax_path and os.path.exists(syntax_path):
        files_to_display.append(('Tag Syntax Guide for LLMs', syntax_path))
    else:
        console.print('[yellow]Warning: Could not find FOR_LLM.md file.[/yellow]')
    if not files_to_display:
        console.print('[bold red]Error: Could not find required documentation files.[/bold red]')
        console.print('[yellow]Make sure PROMPT.md and FOR_LLM.md are installed with the package.[/yellow]')
        return
    for (title, file_path) in files_to_display:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            console.print(f'[bold blue]--- {title} ---[/bold blue]')
            console.print(content)
            console.print('\n')
        except Exception as e:
            console.print(f'[red]Error reading {file_path}: {e}[/red]')


def find_resource_file(filename):
    """
    Find a resource file in various possible locations.

    Args:
        filename (str): The name of the file to find

    Returns:
        str or None: Path to the file if found, None otherwise
    """
    possible_locations = [os.path.join(os.getcwd(), filename), os.path.join(os.path.dirname(os.path.abspath(__file__)), filename), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename), os.path.join(sys.prefix, 'share', 'patchcommander', filename), os.path.join(os.path.expanduser('~'), '.patchcommander', filename)]
    for location in possible_locations:
        if os.path.exists(location):
            return location
    try:
        import importlib.resources as pkg_resources
        try:
            from importlib.resources import files
            return str(files('patchcommander').joinpath(filename))
        except ImportError:
            try:
                with pkg_resources.path('patchcommander', filename) as path:
                    return str(path)
            except (ImportError, FileNotFoundError):
                pass
    except ImportError:
        pass
    return None
