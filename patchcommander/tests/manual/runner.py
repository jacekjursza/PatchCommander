"""
Common utilities for running PatchCommander tests.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

# Add project root to sys.path if not already there
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from patchcommander.core.config import config
except ImportError:
    print('Error: Unable to import patchcommander modules.')
    print("Make sure you're running this script from the project root directory.")
    config = None

def find_directory(relative_paths: List[str]) -> Optional[Path]:
    """Find the first existing directory from a list of relative paths."""
    for path in relative_paths:
        full_path = project_root / path
        if full_path.exists():
            return full_path
    return None

def ensure_sandbox_directory() -> Path:
    """Ensure the sandbox directory exists for tests to use."""
    sandbox_dir = project_root / 'patchcommander' / 'tests' / 'manual' / 'sandbox'
    if not sandbox_dir.exists():
        print(f'Creating sandbox directory: {sandbox_dir}')
        sandbox_dir.mkdir(parents=True, exist_ok=True)
    return sandbox_dir

def clean_sandbox_directory() -> bool:
    """
    Clean the sandbox directory by removing all files.
    
    Returns:
        bool: True if cleaning was successful, False otherwise
    """
    sandbox_dir = ensure_sandbox_directory()
    try:
        for item in sandbox_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        print(f'Cleaned sandbox directory: {sandbox_dir}')
        return True
    except Exception as e:
        print(f'Error cleaning sandbox directory: {e}')
        return False

def set_auto_approval(enabled: bool = True) -> bool:
    """
    Set the auto-approval setting and return the original value.
    
    Args:
        enabled: Whether to enable auto-approval
        
    Returns:
        bool: The original setting value
    """
    if config is None:
        print("Warning: Cannot access PatchCommander config. Auto-approval setting not changed.")
        return False
        
    original_setting = config.get('default_yes_to_all', False)
    if original_setting != enabled:
        config.set('default_yes_to_all', enabled)
        print(f'Changed default_yes_to_all setting from {original_setting} to {enabled}')
    return original_setting

def run_test(test_file: Path, verbose: bool = False) -> bool:
    """
    Run a single test file using PatchCommander CLI.
    
    Args:
        test_file: Path to the test file
        verbose: Whether to print verbose output
        
    Returns:
        bool: True if the test passed, False otherwise
    """
    print(f'\n=== Running test: {test_file.name} ===')
    
    if (project_root / 'pc.py').exists():
        cmd = [sys.executable, str(project_root / 'pc.py'), str(test_file)]
    else:
        cmd = [sys.executable, '-m', 'patchcommander.cli', str(test_file)]
        
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f'✅ Test {test_file.name} passed')
        if verbose:
            print('\nOutput:')
            print(result.stdout)
        return True
    else:
        print(f'❌ Test {test_file.name} failed with return code {result.returncode}')
        print('\nSTDOUT:')
        print(result.stdout)
        print('\nSTDERR:')
        print(result.stderr)
        return False

def run_setup_files(verbose: bool = False) -> bool:
    """
    Run PatchCommander on all setup files to regenerate sandbox files.
    
    Args:
        verbose: Whether to print verbose output
        
    Returns:
        bool: True if all setup files were processed successfully, False otherwise
    """
    setup_dir = find_directory(['patchcommander/tests/manual/setup', 'tests/manual/setup'])
    if not setup_dir:
        print('Setup directory not found!')
        print('Please run this script from the project root directory.')
        return False
        
    setup_files = list(setup_dir.glob('*.txt'))
    if not setup_files:
        print(f'No setup files found in {setup_dir}')
        return False
        
    print(f'Found {len(setup_files)} setup files')
    
    # Ensure sandbox directory exists
    ensure_sandbox_directory()
    
    # Remember original auto-approval setting and enable it for setup
    original_setting = set_auto_approval(True)
    
    try:
        success = True
        for setup_file in setup_files:
            print(f'Processing setup file: {setup_file.name}')
            if not run_test(setup_file, verbose):
                success = False
                
        return success
    finally:
        # Restore original auto-approval setting
        if original_setting is not None:
            set_auto_approval(original_setting)
            print(f'Restored default_yes_to_all setting to: {original_setting}')

def run_assertion_tests(test_files=None, verbose: bool = False) -> bool:
    """
    Run tests with assertions.

    Args:
        test_files: Optional list of test files to run. If None, all test files will be discovered
        verbose: Whether to print verbose output

    Returns:
        bool: True if all tests passed, False otherwise
    """
    if test_files is None:
        # Discover test files in both unit and assertions directories
        test_files = []
        test_dirs = [
            project_root / 'patchcommander' / 'tests' / 'unit',
            project_root / 'patchcommander' / 'tests' / 'assertions'
        ]

        for test_dir in test_dirs:
            if test_dir.exists():
                test_files.extend(list(test_dir.glob('test_*.py')))

    if not test_files:
        print("No assertion test files found")
        return False

    print(f'Found {len(test_files)} assertion test files')

    success = True
    for test_file in sorted(test_files):
        print(f'\n=== Running assertion test: {test_file.name} ===')

        # Run the test with the python interpreter directly
        cmd = [sys.executable, str(test_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f'✅ Assertion test {test_file.name} passed')
            if verbose:
                print('\nOutput:')
                print(result.stdout)
        else:
            print(f'❌ Assertion test {test_file.name} failed with return code {result.returncode}')
            print('\nSTDOUT:')
            print(result.stdout)
            print('\nSTDERR:')
            print(result.stderr)
            success = False

    return success

