"""
Script to publish PatchCommander to PyPI.
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return its output."""
    print(f'Executing: {command}')
    if isinstance(command, str):
        cmd_args = command.split()
    else:
        cmd_args = command

    try:
        process = subprocess.run(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, cwd=cwd)

        if process.stdout:
            print(process.stdout)

        if process.returncode != 0:
            print(f'Error executing command (return code {process.returncode})')
            if process.stderr:
                print(f'STDERR: {process.stderr}')
            return False

        return True

    except Exception as e:
        print(f'Exception while executing command: {e}')
        return False

def test_build():
    """Test the built package with twine."""
    print('Testing package with twine...')
    wheel_files = list(Path('dist').glob('*.whl'))
    tar_files = list(Path('dist').glob('*.tar.gz'))

    if not wheel_files and (not tar_files):
        print('No distribution files found in dist directory!')
        return False

    files = []
    for f in wheel_files:
        files.append(str(f))
    for f in tar_files:
        files.append(str(f))

    print(f'Found distribution files: {files}')
    cmd = [sys.executable, '-m', 'twine', 'check'] + files

    return run_command(cmd)

def upload_test_pypi():
    """Upload the package to Test PyPI."""
    choice = input('Upload to Test PyPI? (y/n): ').lower().strip()
    if choice != 'y':
        return True

    print('Uploading to Test PyPI...')
    wheel_files = list(Path('dist').glob('*.whl'))
    tar_files = list(Path('dist').glob('*.tar.gz'))

    files = []
    for f in wheel_files:
        files.append(str(f))
    for f in tar_files:
        files.append(str(f))

    if not files:
        print('No distribution files found to upload!')
        return False

    cmd = [sys.executable, '-m', 'twine', 'upload', '--repository', 'testpypi'] + files

    return run_command(cmd)

def upload_pypi():
    """Upload the package to PyPI."""
    choice = input('Upload to PyPI? (y/n): ').lower().strip()
    if choice != 'y':
        return True

    print('Uploading to PyPI...')
    wheel_files = list(Path('dist').glob('*.whl'))
    tar_files = list(Path('dist').glob('*.tar.gz'))

    files = []
    for f in wheel_files:
        files.append(str(f))
    for f in tar_files:
        files.append(str(f))

    if not files:
        print('No distribution files found to upload!')
        return False

    cmd = [sys.executable, '-m', 'twine', 'upload'] + files

    return run_command(cmd)

def main():
    """Main function."""
    print('PatchCommander Publication Script')
    print('=================================')

    print('Installing required packages...')
    run_command([sys.executable, '-m', 'pip', 'install', 'twine', 'wheel', 'setuptools', 'build'])

    dist_exists = os.path.exists('dist')
    dist_files = []

    if dist_exists:
        wheel_files = list(Path('dist').glob('*.whl'))
        tar_files = list(Path('dist').glob('*.tar.gz'))
        dist_files = wheel_files + tar_files

    should_build = True
    if dist_files:
        print('\nFound existing distribution files:')
        for f in dist_files:
            print(f'- {f}')

        should_build = input('\nUse existing package files? (y/n): ').lower().strip() == 'n'

    if should_build:
        print('\nNo existing package files found. Please run build_package.py first.')
        choice = input('Run build_package.py now? (y/n): ').lower().strip()
        if choice != 'y':
            print('Publication cancelled.')
            return 0

        if not run_command([sys.executable, 'build_package.py']):
            print('Failed to build package!')
            return 1

    if not test_build():
        print('Package failed Twine checks!')
        choice = input('Continue anyway? (y/n): ').lower().strip()
        if choice != 'y':
            return 1

    if not upload_test_pypi():
        print('Failed to upload to Test PyPI!')
        choice = input('Continue to PyPI anyway? (y/n): ').lower().strip()
        if choice != 'y':
            return 1

    if not upload_pypi():
        print('Failed to upload to PyPI!')
        return 1

    print('\nPublication process completed!')
    return 0

if __name__ == '__main__':
    sys.exit(main())