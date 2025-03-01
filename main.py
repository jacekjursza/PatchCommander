import argparse
import os
import sys
from rich.console import Console
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table
console = Console()
VERSION = '1.0.0'

def print_banner():
    """
    Display the PatchCommander banner with version information.

    PatchCommander - AI-assisted coding automation tool
    ===================================================

    Path Handling:
    -------------
    PatchCommander now automatically sanitizes path attributes in tags:
    - Angle brackets (<>) are replaced with underscores
    - Other invalid characters are properly handled
    - The --diagnose flag can be used to check for problematic paths

    Example of automatic path sanitization:
    <FILE path="path/with<brackets>/file.py"> becomes <FILE path="path/with_brackets_/file.py">

    This makes PatchCommander more robust when processing output from AI models
    that may include template-style or placeholder paths.
    """
    rprint(Panel.fit('[bold blue]PatchCommander[/bold blue] [cyan]v' + VERSION + '[/cyan]\n[yellow]AI-assisted coding automation tool[/yellow]', border_style='blue'))

def print_config(config):
    """Print current configuration settings."""
    table = Table(title='Current Configuration')
    table.add_column('Setting', style='cyan')
    table.add_column('Value', style='green')
    for (key, value) in config.data.items():
        table.add_row(key, str(value))
    console.print(table)

def main():
    parser = argparse.ArgumentParser(description='Process code fragments marked with tags for AI-assisted development.', formatter_class=argparse.RawDescriptionHelpFormatter, epilog='\nExamples:\n  python main.py input.txt             # Process tags from input.txt\n  python main.py                       # Process tags from clipboard\n  python main.py --normalize-only file.txt  # Only normalize line endings\n  python main.py --config              # Show current configuration\n  python main.py --set backup_enabled False  # Change a configuration value\n  python main.py --diagnose            # Only diagnose paths without applying changes\n')
    parser.add_argument('input_file', nargs='?', help='Path to file with tags. If not provided, clipboard content will be used.')
    parser.add_argument('--normalize-only', action='store_true', help='Only normalize line endings in the specified file')
    parser.add_argument('--version', action='store_true', help='Show version information')
    parser.add_argument('--config', action='store_true', help='Show current configuration')
    parser.add_argument('--set', nargs=2, metavar=('KEY', 'VALUE'), help='Set a configuration value')
    parser.add_argument('--reset-config', action='store_true', help='Reset configuration to defaults')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with extra logging')
    parser.add_argument('--diagnose', action='store_true', help='Only diagnose paths without applying changes')
    args = parser.parse_args()
    from line_normalizer import normalize_line_endings
    from config import config
    if args.version:
        print_banner()
        return 0
    if args.config:
        print_banner()
        print_config(config)
        return 0
    if args.set:
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
        config.reset()
        return 0
    if args.debug:
        config.set('debug_mode', True)
    print_banner()
    try:
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
        from utils import get_input_data
        from preprocessor import run_preprocess
        from processing import run_process
        from apply_changes import apply_all_pending_changes
        input_data = get_input_data(args.input_file)
        input_data = normalize_line_endings(input_data)
        if args.diagnose:
            diagnose_paths(input_data)
            console.print('[blue]Diagnosis completed. Use without --diagnose flag to process changes.[/blue]')
            return 0
        console.print('[blue]Note: Invalid characters in paths (<, >, etc.) will be automatically sanitized[/blue]')
        preprocessed_data = run_preprocess(input_data)
        run_process(preprocessed_data)
        apply_all_pending_changes()
        console.print('[bold green]All tasks completed successfully![/bold green]')
    except KeyboardInterrupt:
        console.print('\n[yellow]Operation cancelled by user.[/yellow]')
        return 130
    except Exception as e:
        if config.get('debug_mode'):
            import traceback
            console.print('[bold red]Error stack trace:[/bold red]')
            console.print(traceback.format_exc())
        console.print(f'[bold red]Error: {str(e)}[/bold red]')
        return 1
    return 0
if __name__ == '__main__':
    sys.exit(main())