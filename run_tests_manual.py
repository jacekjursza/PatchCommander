#!/usr/bin/env python
"""
Script to prepare manual test cases for PatchCommander.

This script:
1. Runs PatchCommander on all setup files in patchcommander/tests/manual/setup/
2. Combines all test case files from tests/manual/test_cases/ into one large file
3. Copies this combined file to the clipboard
"""
import sys
import subprocess
import pyperclip
from pathlib import Path
from rich.console import Console

console = Console()

# Import PatchCommander configuration system
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from patchcommander.core.config import config
except ImportError:
    console.print("[bold red]Could not import PatchCommander config module![/bold red]")
    console.print("[yellow]Make sure you're running this script from the project root.[/yellow]")
    config = None

def find_directory(relative_paths):
    """Find the first existing directory from a list of relative paths."""
    for path in relative_paths:
        if Path(path).exists():
            return Path(path)
    return None

def run_setup_files():
    """Run PatchCommander on all setup files to regenerate sandbox files."""
    # Try to find the setup directory
    setup_dir = find_directory([
        "patchcommander/tests/manual/setup",
        "tests/manual/setup"
    ])

    if not setup_dir:
        console.print("[bold red]Setup directory not found![/bold red]")
        console.print("[yellow]Please run this script from the project root directory.[/yellow]")
        return False

    setup_files = list(setup_dir.glob("*.txt"))
    if not setup_files:
        console.print(f"[yellow]No setup files found in {setup_dir}[/yellow]")
        return False

    console.print(f"[blue]Found {len(setup_files)} setup files[/blue]")

    # Determine the sandbox directory based on the setup directory
    sandbox_dir = setup_dir.parent / "sandbox"
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    # Save original auto-approval setting
    original_setting = None
    if config:
        original_setting = config.get('default_yes_to_all', False)
        console.print(f"[blue]Original default_yes_to_all setting: {original_setting}[/blue]")
        config.set('default_yes_to_all', True)
        console.print("[green]Temporarily enabled auto-approval for tests[/green]")

    try:
        for setup_file in setup_files:
            console.print(f"[green]Processing setup file: {setup_file.name}[/green]")

            # Run PatchCommander on the setup file
            try:
                # Use pc.py to run PatchCommander
                result = subprocess.run(
                    [sys.executable, "pc.py", str(setup_file)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                console.print(f"[green]Successfully processed {setup_file.name}[/green]")
            except subprocess.CalledProcessError as e:
                console.print(f"[bold red]Error processing {setup_file.name}:[/bold red]")
                if e.stderr:
                    console.print(f"[red]{e.stderr}[/red]")

        return True
    finally:
        # Always restore original setting, even if an exception occurs
        if config and original_setting is not None:
            config.set('default_yes_to_all', original_setting)
            console.print(f"[blue]Restored default_yes_to_all setting to: {original_setting}[/blue]")

def combine_test_cases():
    """Combine all test case files into one large file and copy to clipboard."""
    # Try to find the test cases directory
    test_cases_dir = find_directory([
        "patchcommander/tests/manual/test_cases",
        "tests/manual/test_cases"
    ])

    if not test_cases_dir:
        console.print("[bold red]Test cases directory not found![/bold red]")
        console.print("[yellow]Creating test_cases directory...[/yellow]")

        # Try to create the directory based on the setup directory
        setup_dir = find_directory([
            "patchcommander/tests/manual/setup",
            "tests/manual/setup"
        ])

        if setup_dir:
            test_cases_dir = setup_dir.parent / "test_cases"
            test_cases_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Fallback to a relative path
            test_cases_dir = Path("tests/manual/test_cases")
            test_cases_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[blue]Using test cases directory: {test_cases_dir}[/blue]")

    # Now gather all test case files
    test_files = list(test_cases_dir.glob("*.txt"))
    if not test_files:
        console.print(f"[yellow]No test case files found in {test_cases_dir} after creating them[/yellow]")
        return ""

    console.print(f"[blue]Found {len(test_files)} test case files[/blue]")

    # Combine all test case files
    combined_content = ""
    for test_file in sorted(test_files):  # Sort to ensure consistent order
        console.print(f"[green]Adding test file: {test_file.name}[/green]")
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():  # Only add non-empty content
                    combined_content += f"\n\n# Test case from: {test_file.name}\n{content.strip()}\n"
        except Exception as e:
            console.print(f"[red]Error reading {test_file.name}: {str(e)}[/red]")

    return combined_content.strip()

def main():
    """Main function to run the test preparation process."""
    console.print("[bold blue]PatchCommander Manual Test Preparation[/bold blue]")

    # Check if we can access the config
    if config is None:
        console.print("[bold yellow]Warning: Cannot access PatchCommander config.[/bold yellow]")
        console.print("[yellow]Auto-approval will not be enabled, script may prompt for confirmations.[/yellow]")

    # Step 1: Run PatchCommander on all setup files
    if not run_setup_files():
        console.print("[yellow]Skipping setup files processing...[/yellow]")

    # Step 2: Combine all test case files
    combined_content = combine_test_cases()

    if combined_content:
        # Step 3: Copy to clipboard
        try:
            pyperclip.copy(combined_content)
            console.print("[bold green]Test cases successfully copied to clipboard![/bold green]")
        except Exception as e:
            console.print(f"[bold red]Error copying to clipboard: {str(e)}[/bold red]")
            console.print("[yellow]Writing combined test cases to combined_test_cases.txt instead[/yellow]")
            with open("combined_test_cases.txt", 'w', encoding='utf-8') as f:
                f.write(combined_content)
    else:
        console.print("[bold yellow]Warning: No test cases were combined. Clipboard not updated.[/bold yellow]")

    console.print("[bold green]Test cases prepared and copied to clipboard, please run `python pc.py`[/bold green]")

if __name__ == "__main__":
    main()