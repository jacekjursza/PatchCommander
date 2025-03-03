"""
Command-line interface for PatchCommander v2.
Handles parsing of command line arguments and orchestrates the overall workflow.
"""
import argparse
import os
import sys

from rich.table import Table

# Import core modules
from core.config import config, console
from core.processors import process_tags
from core.tag_parser import parse_tags, count_tags_by_type, validate_tag
from core.text_utils import normalize_line_endings

# Constants
VERSION = "1.1.0"
APP_NAME = "PatchCommander"

def print_banner():
    """
    Display the PatchCommander banner with version information.
    """
    from rich.panel import Panel
    from rich import print as rprint

    rprint(Panel.fit(
        f"[bold blue]{APP_NAME}[/bold blue] [cyan]v{VERSION}[/cyan]\n"
        f"[yellow]AI-assisted coding automation tool[/yellow]",
        border_style="blue"
    ))

def print_config():
    """Print current configuration settings."""
    table = Table(title='Current Configuration')
    table.add_column('Setting', style='cyan')
    table.add_column('Value', style='green')
    for key, value in config.data.items():
        table.add_row(key, str(value))
    console.print(table)

def setup_argument_parser():
    """
    Set up the command line argument parser.

    Returns:
        ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Process code fragments marked with tags for AI-assisted development.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\nExamples:\n"
               "  python -m v2.cli input.txt             # Process tags from input.txt\n"
               "  python -m v2.cli                       # Process tags from clipboard\n"
               "  python -m v2.cli --normalize-only file.txt  # Only normalize line endings\n"
               "  python -m v2.cli --config              # Show current configuration\n"
               "  python -m v2.cli --set backup_enabled False  # Change a configuration value\n"
               "  python -m v2.cli --diagnose            # Only diagnose paths without applying changes\n"
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        help="Path to file with tags. If not provided, clipboard content will be used."
    )

    parser.add_argument(
        "--normalize-only",
        action="store_true",
        help="Only normalize line endings in the specified file"
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information"
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="Show current configuration"
    )

    parser.add_argument(
        "--set",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Set a configuration value"
    )

    parser.add_argument(
        "--reset-config",
        action="store_true",
        help="Reset configuration to defaults"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with extra logging"
    )

    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Only diagnose paths without applying changes"
    )

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

    # Characters that are invalid in file paths
    invalid_chars = '<>:"|?*' if os.name == 'nt' else '<>'

    # Parse tags
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

        for attr_name, path in paths:
            if not path:
                continue

            has_invalid_chars = any(c in path for c in invalid_chars)

            if has_invalid_chars:
                problematic_paths.append((tag.tag_type, attr_name, path))

    if problematic_paths:
        console.print('[bold red]Found problematic paths:[/bold red]')
        for tag_type, attr_name, path in problematic_paths:
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
    # This is a stub - will be implemented fully in a later step
    try:
        if input_file:
            if not os.path.exists(input_file):
                console.print(f"[bold red]File '{input_file}' not found.[/bold red]")
                sys.exit(1)

            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read()

            console.print(f"[green]Successfully loaded input from file: {input_file}[/green]")
            return data
        else:
            # Try to import pyperclip for clipboard functionality
            try:
                import pyperclip
                clipboard_content = pyperclip.paste()

                if clipboard_content.strip() == '':
                    console.print("[bold yellow]Clipboard is empty. Please copy content first. Exiting.[/bold yellow]")
                    sys.exit(1)

                console.print("[green]Using clipboard content as input[/green]")
                return clipboard_content
            except ImportError:
                console.print("[bold red]Error: pyperclip module not found. Please install it with 'pip install pyperclip'.[/bold red]")
                sys.exit(1)

    except Exception as e:
        console.print(f"[bold red]Error getting input: {e}[/bold red]")
        sys.exit(1)

def main():
    """
    Main entry point for the application.

    Returns:
        int: Exit code
    """
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Handle version display
    if args.version:
        print_banner()
        return 0

    # Handle config display
    if args.config:
        print_banner()
        print_config()
        return 0

    # Handle setting configuration
    if args.set:
        print_banner()
        key, value = args.set

        # Convert string values to appropriate types
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False
        elif value.lower() == 'none':
            value = None
        elif value.isdigit():
            value = int(value)

        if config.set(key, value):
            console.print(f"[green]Configuration updated: {key} = {value}[/green]")
        else:
            console.print(f"[red]Unknown configuration key: {key}[/red]")
        return 0

    # Handle reset configuration
    if args.reset_config:
        print_banner()
        config.reset()
        return 0

    # Print banner at start of operation
    print_banner()

    # Handle normalize-only
    if args.normalize_only and args.input_file:
        if not os.path.exists(args.input_file):
            console.print(f"[bold red]File '{args.input_file}' not found.[/bold red]")
            return 1

        with open(args.input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        normalized = normalize_line_endings(content)

        with open(args.input_file, 'w', encoding='utf-8', newline='') as f:
            f.write(normalized)

        console.print(f"[bold green]Normalized line endings in {args.input_file}[/bold green]")
        return 0

    # Handle diagnose
    if args.diagnose:
        input_data = get_input_data(args.input_file)
        input_data = normalize_line_endings(input_data)
        diagnose_paths(input_data)
        console.print("[blue]Diagnosis completed. Use without --diagnose flag to process changes.[/blue]")
        return 0

    # Get input data and process it
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
            console.print("[bold red]Found invalid tags:[/bold red]")
            for tag, error in invalid_tags:
                console.print(f"  [yellow]{tag.tag_type}[/yellow]: {error}")

            if not args.debug:
                console.print("[yellow]Use --debug flag to continue despite invalid tags[/yellow]")
                return 1

        # Process operations
        console.print("[blue]Note: Invalid characters in paths (<, >, etc.) will be automatically sanitized[/blue]")

        # Process the tags

        success_count = process_tags(tags)

        console.print(f"[bold green]Successfully processed {success_count} out of {len(tags)} tags.[/bold green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        return 130
    except Exception as e:
        if args.debug:
            import traceback
            console.print("[bold red]Error stack trace:[/bold red]")
            console.print(traceback.format_exc())
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        return 1

    console.print("[bold green]Operation completed![/bold green]")
    return 0

if __name__ == "__main__":
    sys.exit(main())