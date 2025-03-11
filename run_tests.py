#!/usr/bin/env python
"""
Script to run all manual tests for PatchCommander.
Temporarily enables auto-approval and then restores the original setting.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

# Determine the script directory and project root
script_path = Path(__file__).resolve()
project_root = script_path.parent

# Add the project root to the Python path if necessary
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from patchcommander.core.config import config
except ImportError:
    print("Error: Unable to import patchcommander modules.")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

def run_test(test_file, verbose=False):
    """Run a single test file using PatchCommander CLI."""
    print(f"\n=== Running test: {os.path.basename(test_file)} ===")

    # Use the pc.py script if it exists, otherwise use the module
    if (project_root / 'pc.py').exists():
        cmd = [sys.executable, str(project_root / 'pc.py'), str(test_file)]
    else:
        cmd = [sys.executable, '-m', 'patchcommander.cli', str(test_file)]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ Test {os.path.basename(test_file)} passed")
        if verbose:
            print("\nOutput:")
            print(result.stdout)
        return True
    else:
        print(f"❌ Test {os.path.basename(test_file)} failed with return code {result.returncode}")
        print("\nSTDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        return False

def ensure_sandbox_directory():
    """Ensure the sandbox directory exists for tests to use."""
    sandbox_dir = project_root / 'patchcommander' / 'tests' / 'manual' / 'sandbox'
    if not sandbox_dir.exists():
        print(f"Creating sandbox directory: {sandbox_dir}")
        sandbox_dir.mkdir(parents=True, exist_ok=True)
    return sandbox_dir.exists()

def run_manual_tests(test_pattern=None, verbose=False):
    """Run manual tests with auto-approval enabled and restore original setting after."""
    # Save original auto-approval setting
    original_setting = config.get('default_yes_to_all', False)

    try:
        # Enable auto-approval
        print(f"Original default_yes_to_all setting: {original_setting}")
        config.set('default_yes_to_all', True)
        print("Enabled auto-approval for tests")

        # Ensure sandbox directory exists
        if not ensure_sandbox_directory():
            print("Failed to create sandbox directory")
            return 1

        # Find test case files
        test_dir = project_root / 'patchcommander' / 'tests' / 'manual' / 'test_cases'
        if not test_dir.exists():
            print(f"Error: Test directory not found: {test_dir}")
            return 1

        if test_pattern:
            test_files = list(test_dir.glob(test_pattern))
        else:
            test_files = list(test_dir.glob('*.txt'))

        if not test_files:
            print(f"No test files found matching pattern: {test_pattern or '*.txt'}")
            return 1

        print(f"Found {len(test_files)} test files")

        # Run setup files first if they exist
        setup_dir = project_root / 'patchcommander' / 'tests' / 'manual' / 'setup'
        if setup_dir.exists():
            setup_files = list(setup_dir.glob('*.txt'))
            if setup_files:
                print("\n=== Running setup files ===")
                for setup_file in sorted(setup_files):
                    print(f"Setting up: {setup_file.name}")
                    run_test(setup_file, verbose=verbose)

        # Run test files
        success_count = 0
        failure_count = 0

        for test_file in sorted(test_files):
            if run_test(test_file, verbose=verbose):
                success_count += 1
            else:
                failure_count += 1

        # Report summary
        print("\n=== Test Summary ===")
        print(f"Passed: {success_count}")
        print(f"Failed: {failure_count}")
        print(f"Total:  {success_count + failure_count}")

        return 0 if failure_count == 0 else 1

    finally:
        # Always restore original setting, even if an exception occurs
        config.set('default_yes_to_all', original_setting)
        print(f"Restored default_yes_to_all setting to: {original_setting}")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run manual tests for PatchCommander")
    parser.add_argument('-t', '--test', help='Test pattern to match (e.g., test_python_*.txt)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    sys.exit(run_manual_tests(
        test_pattern=args.test,
        verbose=args.verbose
    ))