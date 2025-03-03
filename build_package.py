"""
Script to build PatchCommander package for PyPI.
This creates the distribution files required for PyPI.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command):
    """Run a command and return its output."""
    print(f'Executing: {command}')
    if isinstance(command, str):
        cmd_args = command.split()
    else:
        cmd_args = command

    process = subprocess.run(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)

    if process.stdout:
        print(process.stdout)

    if process.returncode != 0:
        print(f'Error executing command (return code {process.returncode})')
        if process.stderr:
            print(f'STDERR: {process.stderr}')
        return False

    return True

def clean_previous_builds():
    """Remove previous build artifacts."""
    print('Cleaning previous build artifacts...')
    dirs_to_clean = ['build', 'patchcommander.egg-info']

    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f'Removing {d}...')
            shutil.rmtree(d)

    has_dist_files = False
    if os.path.exists('dist'):
        dist_files = list(Path('dist').glob('*.whl')) + list(Path('dist').glob('*.tar.gz'))
        has_dist_files = len(dist_files) > 0

    if os.path.exists('dist') and (not has_dist_files):
        print('Removing dist...')
        shutil.rmtree('dist')
    elif os.path.exists('dist') and has_dist_files:
        choice = input('Distribution files found in dist/. Clean anyway? (y/n): ').lower().strip()
        if choice == 'y':
            print('Removing dist...')
            shutil.rmtree('dist')
        else:
            print('Keeping existing distribution files.')

def build_package():
    """Build the Python package."""
    print('Building package with setuptools and wheel...')
    dist_path = Path('dist')

    if dist_path.exists():
        print('Cleaning dist directory first...')
        for file in dist_path.glob('*'):
            print(f'Removing {file}...')
            file.unlink()
    else:
        dist_path.mkdir(parents=True, exist_ok=True)

    return run_command([sys.executable, '-m', 'build'])

def main():
    """Main function."""
    print('PatchCommander Package Builder')
    print('=============================')

    print('Installing required packages...')
    run_command([sys.executable, '-m', 'pip', 'install', 'wheel', 'setuptools', 'build'])

    clean_previous_builds()

    print('\nBuilding Python package distribution files...')
    if not build_package():
        print('Failed to build package!')
        return 1

    print('\nPackage files created:')
    for f in Path('dist').glob('*'):
        print(f'- {f}')

    print('\nPackage build completed successfully!')
    print('You can now run publish.py to upload these files to PyPI.')

    return 0

if __name__ == '__main__':
    sys.exit(main())