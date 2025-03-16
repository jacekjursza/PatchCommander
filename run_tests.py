"""
Script to run all manual tests for PatchCommander.
Uses the common test runner utilities from tests/manual/runner.py.
"""
import os
import sys
import argparse
from pathlib import Path

# Add project root to sys.path if not already there
script_path = Path(__file__).resolve()
project_root = script_path.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from patchcommander.tests.manual.runner import (
        run_test, ensure_sandbox_directory, set_auto_approval,
        clean_sandbox_directory, run_setup_files, run_assertion_tests
    )
except ImportError:
    print('Error: Unable to import runner module.')
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run manual tests for PatchCommander')
    parser.add_argument('-t', '--test', help='Test pattern to match (e.g., test_python_*.txt)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')
    parser.add_argument('-c', '--clean', action='store_true', help='Clean sandbox directory before running tests')
    parser.add_argument('--no-assert', action='store_true', help='Skip running assertion tests')
    parser.add_argument('-s', '--skip-setup', action='store_true', help='Skip running setup files')
    return parser.parse_args()


def run_manual_tests(test_pattern=None, verbose=False, clean=False, no_assert=False, skip_setup=False):
    original_setting = set_auto_approval(True)
    try:
        if clean:
            if not clean_sandbox_directory():
                print('Failed to clean sandbox directory')
                return 1
        if not ensure_sandbox_directory():
            print('Failed to create sandbox directory')
            return 1
        if not skip_setup:
            if not run_setup_files(verbose):
                print('Failed to run setup files')
                if not input('Continue anyway? (y/n): ').lower().startswith('y'):
                    return 1
        test_dir = project_root / 'patchcommander' / 'tests' / 'manual' / 'test_cases'
        if not test_dir.exists():
            print(f'Error: Test directory not found: {test_dir}')
            return 1
        if test_pattern:
            test_files = list(test_dir.glob(test_pattern))
        else:
            test_files = list(test_dir.glob('*.txt'))
        if not test_files:
            print(f"No test files found matching pattern: {test_pattern or '*.txt'}")
            return 1
        print(f'Found {len(test_files)} test files')
        success_count = 0
        failure_count = 0
        for test_file in sorted(test_files):
            if run_test(test_file, verbose):
                success_count += 1
            else:
                failure_count += 1
        print('\n=== Test Summary ===')
        print(f'Passed: {success_count}')
        print(f'Failed: {failure_count}')
        print(f'Total:  {success_count + failure_count}')
        if not no_assert:
            print('\n=== Running Assertion Tests ===')
            if not run_assertion_tests(None, verbose):
                failure_count += 1
        return 0 if failure_count == 0 else 1
    finally:
        set_auto_approval(original_setting)

if __name__ == '__main__':
    args = parse_arguments()
    sys.exit(run_manual_tests(
        test_pattern=args.test,
        verbose=args.verbose,
        clean=args.clean,
        no_assert=args.no_assert,
        skip_setup=args.skip_setup
    ))