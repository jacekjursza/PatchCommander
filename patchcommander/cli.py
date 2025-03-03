"""
Command-line interface for PatchCommander v2.
Handles parsing of command line arguments and orchestrates the overall workflow.
"""
import argparse
import os
import sys

from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

from patchcommander import APP_NAME, VERSION
from patchcommander.core.config import config, console
from patchcommander.core.processors import process_tags
from patchcommander.core.tag_parser import parse_tags, count_tags_by_type, validate_tag
from patchcommander.core.text_utils import normalize_line_endings


def print_banner():
    """
    Display the PatchCommander banner with version information.
    """
    rprint(Panel.fit(f'[bold blue]{APP_NAME}[/bold blue] [cyan]v{VERSION}[/cyan]\n[yellow]AI-assisted coding automation tool[/yellow]', border_style='blue'))

def print_config():
    """Print current configuration settings."""
    table = Table(title='Current Configuration')
    table.add_column('Setting', style='cyan')
    table.add_column('Value', style='green')
    for key, value in config.data.items():
        table.add_row(key, str(value))
    console.print(table)

def display_llm_docs(include_prompt=True):
    """
    Display documentation for LLMs.

    Args:
        include_prompt (bool): Whether to include full prompt (PROMPT.md) or just syntax guide (FOR_LLM.md)
    """
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
    possible_locations = [
        os.path.join(os.getcwd(), filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename),
        os.path.join(sys.prefix, 'share', 'patchcommander', filename),
        os.path.join(os.path.expanduser('~'), '.patchcommander', filename),
    ]

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

def setup_argument_parser():
    """
    Set up the command line argument parser.

    Returns:
        ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description='Process code fragments marked with tags for AI-assisted development.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='\nExamples:\n  '
               'pcmd input.txt             ---> Process tags from input.txt\n  '
               'pcmd                       ---> Process tags from clipboard\n  '
               'pcmd --normalize-only file.txt  ---> Only normalize line endings\n  '
               'pcmd --config              ---> Show current configuration\n  '
               'pcmd --set backup_enabled False  ---> Change a configuration value\n  '
               'pcmd --diagnose            ---> Only diagnose paths without applying changes\n'
    )
    parser.add_argument('input_file', nargs='?', help='Path to file with tags. If not provided, clipboard content will be used.')
    parser.add_argument('--normalize-only', action='store_true', help='Only normalize line endings in the specified file')
    parser.add_argument('--version', action='store_true', help='Show version information')
    parser.add_argument('--config', action='store_true', help='Show current configuration')
    parser.add_argument('--set', nargs=2, metavar=('KEY', 'VALUE'), help='Set a configuration value')
    parser.add_argument('--reset-config', action='store_true', help='Reset configuration to defaults')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with extra logging')
    parser.add_argument('--diagnose', action='store_true', help='Only diagnose paths without applying changes')
    parser.add_argument('--prompt', action='store_true', help='Display full prompt with instructions for LLMs (PROMPT.md + FOR_LLM.md)')
    parser.add_argument('--syntax', action='store_true', help='Display PatchCommander tag syntax guide for LLMs (FOR_LLM.md)')
    return parser

def sanitize_path(path):
    """
    Sanitize a file path by replacing invalid characters with underscores.

    Args:
        path (str): Path to sanitize

    Returns:
        str: Sanitized path
    """
    if not path:
        return path
    sanitized_path = path
    for char in '<>':
        if char in sanitized_path:
            sanitized_path = sanitized_path.replace(char, '_')
            console.print(f'[yellow]Warning: Replaced invalid character "{char}" in path with underscore.[/yellow]')
    return sanitized_path

def diagnose_paths(input_data):
    """
    Check for problematic paths in tag attributes and report them without making changes.

    Args:
        input_data (str): Input data containing tags
    """
    console.print('[bold]Diagnosing paths in input data...[/bold]')
    invalid_chars = '<>:"|?*' if os.name == 'nt' else '<>'
    tags = parse_tags(input_data)
    problematic_paths = []
    for tag in tags:
        paths = []
        if 'path' in tag.attributes:
            paths.append(('path', tag.attributes['path']))
        if 'source' in tag.attributes:
            paths.append(('source', tag.attributes['source']))
        if 'target' in tag.attributes:
            paths.append(('target', tag.attributes['target']))
        for (attr_name, path) in paths:
            if not path:
                continue
            has_invalid_chars = any((c in path for c in invalid_chars))
            if has_invalid_chars:
                problematic_paths.append((tag.tag_type, attr_name, path))
    if problematic_paths:
        console.print('[bold red]Found problematic paths:[/bold red]')
        for (tag_type, attr_name, path) in problematic_paths:
            sanitized = sanitize_path(path)
            console.print(f'  [yellow]<{tag_type}>[/yellow] {attr_name}="{path}" → {attr_name}="{sanitized}"')
    else:
        console.print('[green]No problematic paths found.[/green]')

def get_input_data(input_file):
    """
    Get input data from a file or clipboard.

    Args:
        input_file (str): Path to input file or None to use clipboard

    Returns:
        str: Content from file or clipboard
    """
    try:
        if input_file:
            if not os.path.exists(input_file):
                console.print(f"[bold red]File '{input_file}' not found.[/bold red]")
                sys.exit(1)
            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read()
            console.print(f'[green]Successfully loaded input from file: {input_file}[/green]')
            return data
        else:
            try:
                import pyperclip
                clipboard_content = pyperclip.paste()
                if clipboard_content.strip() == '':
                    console.print('[bold yellow]Clipboard is empty. Please copy content first. Exiting.[/bold yellow]')
                    sys.exit(1)
                console.print('[green]Using clipboard content as input[/green]')
                return clipboard_content
            except ImportError:
                console.print("[bold red]Error: pyperclip module not found. Please install it with 'pip install pyperclip'.[/bold red]")
                sys.exit(1)
    except Exception as e:
        console.print(f'[bold red]Error getting input: {e}[/bold red]')
        sys.exit(1)

def main():
    """
    Main entry point for the application.

    Returns:
        int: Exit code
    """
    parser = setup_argument_parser()
    args = parser.parse_args()
    if args.version:
        print_banner()
        return 0
    if args.config:
        print_banner()
        print_config()
        return 0
    if args.set:
        print_banner()
        (key, value) = args.set
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False
        elif value.lower() == 'none':
            value = None
        elif value.isdigit():
            value = int(value)
        if config.set(key, value):
            console.print(f'[green]Configuration updated: {key} = {value}[/green]')
        else:
            console.print(f'[red]Unknown configuration key: {key}[/red]')
        return 0
    if args.reset_config:
        print_banner()
        config.reset()
        return 0

    # Add prompt and syntax options handling
    if args.prompt:
        print_banner()
        display_llm_docs(include_prompt=True)
        return 0

    if args.syntax:
        print_banner()
        display_llm_docs(include_prompt=False)
        return 0

    print_banner()
    if args.normalize_only and args.input_file:
        if not os.path.exists(args.input_file):
            console.print(f"[bold red]File '{args.input_file}' not found.[/bold red]")
            return 1
        with open(args.input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        normalized = normalize_line_endings(content)
        with open(args.input_file, 'w', encoding='utf-8', newline='') as f:
            f.write(normalized)
        console.print(f'[bold green]Normalized line endings in {args.input_file}[/bold green]')
        return 0
    if args.diagnose:
        input_data = get_input_data(args.input_file)
        input_data = normalize_line_endings(input_data)
        diagnose_paths(input_data)
        console.print('[blue]Diagnosis completed. Use without --diagnose flag to process changes.[/blue]')
        return 0
    try:
        input_data = get_input_data(args.input_file)
        console.print(f"[blue]Loaded {len(input_data)} characters of input data[/blue]")

        # Normalize line endings
        input_data = normalize_line_endings(input_data)

        # Parse tags from input
        console.print("[bold]Parsing tags from input...[/bold]")
        tags = parse_tags(input_data)

        # Count tags by type and display
        counts = count_tags_by_type(tags)
        console.print("[bold]Tags found:[/bold]")
        for tag_type, count in counts.items():
            if count > 0:
                console.print(f"  {tag_type}: {count}")

        # Validate tags
        invalid_tags = []
        for tag in tags:
            is_valid, error = validate_tag(tag)
            if not is_valid:
                invalid_tags.append((tag, error))

        if invalid_tags:
            console.print('[bold red]Found invalid tags:[/bold red]')
            for (tag, error) in invalid_tags:
                console.print(f'  [yellow]{tag.tag_type}[/yellow]: {error}')
            if not args.debug:
                console.print('[yellow]Use --debug flag to continue despite invalid tags[/yellow]')
                return 1
        console.print('[blue]Note: Invalid characters in paths (<, >, etc.) will be automatically sanitized[/blue]')
        success_count = process_tags(tags)
        console.print(f'[bold green]Successfully processed {success_count} out of {len(tags)} tags.[/bold green]')
    except KeyboardInterrupt:
        console.print('\n[yellow]Operation cancelled by user.[/yellow]')
        return 130
    except Exception as e:
        if args.debug:
            import traceback
            console.print('[bold red]Error stack trace:[/bold red]')
            console.print(traceback.format_exc())
        console.print(f'[bold red]Error: {str(e)}[/bold red]')
        return 1
    console.print('[bold green]Operation completed![/bold green]')
    return 0

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.exit(main())