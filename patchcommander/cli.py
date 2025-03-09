"""
Command-line interface for PatchCommander v2.
Utilizes refactored pipeline architecture.
"""
import argparse
import os
import sys
import difflib
from typing import List, Dict
from pathlib import Path
import rich
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich import box
import pyperclip
from patchcommander import APP_NAME, VERSION
from patchcommander.core.config import config
from patchcommander.core.text_utils import normalize_line_endings
from patchcommander.core.pipeline.pipeline import Pipeline
from patchcommander.core.pipeline.models import PatchResult
from patchcommander.core.pipeline.pre_processors.global_processor import TagParser
from patchcommander.core.pipeline.pre_processors.custom.xpath_analyzer import XPathAnalyzer
from patchcommander.core.pipeline.post_processors.syntax_validator import SyntaxValidator
console = Console()

def print_banner():
    """
    Displays the PatchCommander banner with version information.
    """
    rich.print(Panel.fit(f'[bold blue]{APP_NAME}[/bold blue] [cyan]v{VERSION}[/cyan]\n[yellow]AI-assisted coding automation tool[/yellow]', border_style='blue'))

def print_config():
    """Displays the current configuration settings."""
    table = Table(title='Current Configuration')
    table.add_column('Setting', style='cyan')
    table.add_column('Value', style='green')
    for (key, value) in config.data.items():
        table.add_row(key, str(value))
    console.print(table)

def find_resource_file(filename):
    """
    Finds a resource file in various possible locations.

    Args:
        filename (str): Name of the file to find

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

def display_llm_docs(include_prompt=True):
    """
    Displays documentation for LLMs.

    Args:
        include_prompt (bool): Whether to include the full prompt (PROMPT.md) or just the syntax instructions (FOR_LLM.md)
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

def setup_argument_parser():
    """
    Configures the command-line argument parser.

    Returns:
        ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(description='Process code fragments marked with tags for AI-assisted development.', formatter_class=argparse.RawDescriptionHelpFormatter, epilog='\nExamples:\n  pcmd input.txt             ---> Process tags from input.txt\n  pcmd                       ---> Process tags from clipboard\n  pcmd --normalize-only file.txt  ---> Only normalize line endings\n  pcmd --config              ---> Show current configuration\n  pcmd --set backup_enabled False  ---> Change a configuration value\n  pcmd --diagnose            ---> Only diagnose paths without applying changes\n')
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

def get_input_data(input_file):
    """
    Gets input data from a file or clipboard.

    Args:
        input_file (str): Path to the input file or None to use clipboard

    Returns:
        str: Content of the file or clipboard
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

def setup_pipeline():
    """
    Configures the PatchCommander processing pipeline.

    Returns:
        Pipeline: Configured pipeline
    """
    pipeline = Pipeline()
    pipeline.set_global_preprocessor(TagParser())
    pipeline.add_preprocessor(XPathAnalyzer())
    pipeline.add_postprocessor(SyntaxValidator())
    return pipeline

def generate_side_by_side_diff(old_lines, new_lines, file_path):
    """
    Generates a side-by-side diff view.

    Args:
        old_lines: List of lines from the original file
        new_lines: List of lines from the new version of the file
        file_path: Path to the modified file

    Returns:
        Rich Table object with side-by-side diff
    """
    from rich.text import Text
    import difflib
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    table = Table(show_header=True, header_style='bold', box=box.SIMPLE)
    table.add_column(f'Current: {file_path}', style='cyan', width=None)
    table.add_column(f'New: {file_path}', style='green', width=None)
    max_context_lines = config.get('max_diff_context_lines', 3)
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

def show_diffs_and_confirm(results: List[PatchResult]) -> Dict[str, bool]:
    """
    Shows diff for each file and asks for confirmation.

    Args:
        results: List of operation results

    Returns:
        Dict[str, bool]: Dictionary with file paths and approval flags
    """
    approvals = {}
    for result in results:
        if result.has_errors():
            console.print(f'[bold red]Errors found in processing {result.path}:[/bold red]')
            for error in result.errors:
                console.print(f'  - {error}')
            for operation in result.operations:
                for error in operation.errors:
                    console.print(f'  - {error}')
            if config.get('default_yes_to_all', False):
                console.print(f"[blue]Continue with other changes despite errors in {result.path}? (Automatically answered 'y' due to default_yes_to_all setting)[/blue]")
                approvals[result.path] = False
                continue
            answer = Prompt.ask(f'Continue with other changes despite errors in {result.path}?', choices=['y', 'n'], default='y')
            if answer.lower() != 'y':
                approvals[result.path] = False
                console.print(f'[yellow]Skipping changes to {result.path}.[/yellow]')
                continue
        if result.original_content == result.current_content:
            console.print(f'[blue]No changes to {result.path}[/blue]')
            approvals[result.path] = False
            continue
        old_lines = result.original_content.splitlines()
        new_lines = result.current_content.splitlines()
        diff_lines = list(difflib.unified_diff(old_lines, new_lines, fromfile=f'current: {result.path}', tofile=f'new: {result.path}', lineterm=''))
        if not diff_lines:
            console.print(f'[blue]No changes detected for {result.path}.[/blue]')
            approvals[result.path] = False
            continue
        diff_text = '\n'.join(diff_lines)
        syntax = Syntax(diff_text, 'diff', theme='monokai', line_numbers=True)
        panel = Panel(syntax, title=f'Changes for: {result.path}', border_style='blue', box=box.DOUBLE)
        console.print(panel)
        if config.get('default_yes_to_all', False):
            console.print(f"[blue]Apply changes to {result.path}? (Automatically answered 'y' due to default_yes_to_all setting)[/blue]")
            approvals[result.path] = True
            continue
        answer = Prompt.ask(f'Apply changes to {result.path}?', choices=['y', 'n', 's', 'd'], default='y')
        if answer.lower() == 'y':
            approvals[result.path] = True
            console.print(f'[green]Change approved for {result.path}.[/green]')
        elif answer.lower() == 's':
            approvals[result.path] = False
            console.print(f'[yellow]Skipping changes to {result.path} for now.[/yellow]')
        elif answer.lower() == 'd':
            console.print('\n[bold]Side-by-side diff view:[/bold]')
            side_diff = generate_side_by_side_diff(old_lines, new_lines, result.path)
            console.print(side_diff)
            second_answer = Prompt.ask(f'Apply changes to {result.path}?', choices=['y', 'n', 's'], default='y')
            if second_answer.lower() == 'y':
                approvals[result.path] = True
                console.print(f'[green]Change approved for {result.path}.[/green]')
            elif second_answer.lower() == 's':
                approvals[result.path] = False
                console.print(f'[yellow]Skipping changes to {result.path} for now.[/yellow]')
            else:
                approvals[result.path] = False
                console.print(f'[yellow]Changes to {result.path} rejected.[/yellow]')
        else:
            approvals[result.path] = False
            console.print(f'[yellow]Changes to {result.path} rejected.[/yellow]')
    return approvals

def apply_changes(results: List[PatchResult], approvals: Dict[str, bool]) -> int:
    """
    Applies approved changes to files.

    Args:
        results: List of operation results
        approvals: Dictionary with approval decisions

    Returns:
        int: Number of modified files
    """
    modified_count = 0
    for result in results:
        if approvals.get(result.path, False):
            try:
                directory = os.path.dirname(result.path)
                if directory:
                    os.makedirs(directory, exist_ok=True)
                with open(result.path, 'w', encoding='utf-8') as f:
                    f.write(result.current_content)
                console.print(f'[green]Applied changes to {result.path}[/green]')
                modified_count += 1
            except Exception as e:
                console.print(f'[bold red]Error applying changes to {result.path}: {e}[/bold red]')
    return modified_count

def main():
    """
    Main function of the program.

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
    try:
        input_data = get_input_data(args.input_file)
        console.print(f'[blue]Loaded {len(input_data)} characters of input data[/blue]')
        input_data = normalize_line_endings(input_data)
        pipeline = setup_pipeline()
        results = pipeline.run(input_data)
        approvals = show_diffs_and_confirm(results)
        modified_count = apply_changes(results, approvals)
        console.print(f'[bold green]Processing completed with {modified_count} file(s) affected.[/bold green]')
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
    return 0