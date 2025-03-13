"""
Script to prepare manual test cases for PatchCommander.

This script:
1. Runs PatchCommander on all setup files in patchcommander/tests/manual/setup/
2. Combines all test case files from tests/manual/test_cases/ into one large file
3. Copies this combined file to the clipboard
"""
import sys
import argparse
import pyperclip
from pathlib import Path
from rich.console import Console

# Add project root to sys.path if not already there
script_path = Path(__file__).resolve()
project_root = script_path.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from patchcommander.tests.manual.runner import (
        find_directory, ensure_sandbox_directory, set_auto_approval,
        clean_sandbox_directory, run_setup_files
    )
except ImportError:
    print('Error: Unable to import runner module.')
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

console = Console()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Prepare manual test cases for PatchCommander')
    parser.add_argument('-c', '--clean', action='store_true', help='Clean sandbox directory before running')
    parser.add_argument('-s', '--skip-setup', action='store_true', help='Skip running setup files')
    return parser.parse_args()

def combine_test_cases():
    """Combine all test case files into one large file and copy to clipboard."""
    test_cases_dir = find_directory(['patchcommander/tests/manual/test_cases', 'tests/manual/test_cases'])
    if not test_cases_dir:
        console.print('[bold red]Test cases directory not found![/bold red]')
        console.print('[yellow]Creating test_cases directory...[/yellow]')
        setup_dir = find_directory(['patchcommander/tests/manual/setup', 'tests/manual/setup'])
        if setup_dir:
            test_cases_dir = setup_dir.parent / 'test_cases'
            test_cases_dir.mkdir(parents=True, exist_ok=True)
        else:
            test_cases_dir = Path('tests/manual/test_cases')
            test_cases_dir.mkdir(parents=True, exist_ok=True)
            
    console.print(f'[blue]Using test cases directory: {test_cases_dir}[/blue]')
    
    test_files = list(test_cases_dir.glob('*.txt'))
    if not test_files:
        console.print(f'[yellow]No test case files found in {test_cases_dir} after creating them[/yellow]')
        return ''
        
    console.print(f'[blue]Found {len(test_files)} test case files[/blue]')
    
    combined_content = ''
    for test_file in sorted(test_files):
        console.print(f'[green]Adding test file: {test_file.name}[/green]')
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    combined_content += f'\n\n# Test case from: {test_file.name}\n{content.strip()}\n'
        except Exception as e:
            console.print(f'[red]Error reading {test_file.name}: {str(e)}[/red]')
            
    return combined_content.strip()

def main():
    """Main function to run the test preparation process."""
    args = parse_arguments()
    
    console.print('[bold blue]PatchCommander Manual Test Preparation[/bold blue]')
    
    # Clean sandbox directory if requested
    if args.clean:
        console.print('[blue]Cleaning sandbox directory...[/blue]')
        if not clean_sandbox_directory():
            console.print('[yellow]Failed to clean sandbox directory[/yellow]')
    
    # Run setup files if not skipped
    if not args.skip_setup:
        if not run_setup_files():
            console.print('[yellow]Failed to run setup files[/yellow]')
            if not input('Continue anyway? (y/n): ').lower().startswith('y'):
                return 1
    
    # Combine test cases
    combined_content = combine_test_cases()
    if combined_content:
        try:
            pyperclip.copy(combined_content)
            console.print('[bold green]Test cases successfully copied to clipboard![/bold green]')
        except Exception as e:
            console.print(f'[bold red]Error copying to clipboard: {str(e)}[/bold red]')
            console.print('[yellow]Writing combined test cases to combined_test_cases.txt instead[/yellow]')
            with open('combined_test_cases.txt', 'w', encoding='utf-8') as f:
                f.write(combined_content)
    else:
        console.print('[bold yellow]Warning: No test cases were combined. Clipboard not updated.[/bold yellow]')
        
    console.print('[bold green]Test cases prepared and copied to clipboard, please run `python pc.py`[/bold green]')
    return 0

if __name__ == '__main__':
    sys.exit(main())