"""
Complete release script for PatchCommander.
This script:
1. Builds the Python package (for PyPI)
2. Builds executables for current platform
3. Optionally publishes to PyPI
"""
import sys
import subprocess
import platform

def run_script(script_name):
    """Run another Python script."""
    print(f'\n=== Running {script_name} ===\n')
    result = subprocess.run([sys.executable, script_name], capture_output=False, text=True)
    return result.returncode == 0

def main():
    """Main function."""
    print(f'PatchCommander Release Script - Running on {platform.system()}')
    print('=' * 60)

    build_pkg = input('Build Python package for PyPI? (y/n): ').lower().strip() == 'y'
    build_exe = input('Build executable for this platform? (y/n): ').lower().strip() == 'y'
    publish_pkg = input('Publish package to PyPI? (y/n): ').lower().strip() == 'y'

    success = True

    if build_pkg:
        if not run_script('build_package.py'):
            print('Failed to build Python package!')
            success = False
            if not input('Continue with other steps? (y/n): ').lower().strip() == 'y':
                return 1

    if build_exe and success:
        if not run_script('build.py'):
            print('Failed to build executable!')
            success = False
            if not input('Continue with other steps? (y/n): ').lower().strip() == 'y':
                return 1

    if publish_pkg and success:
        if not run_script('publish.py'):
            print('Failed to publish to PyPI!')
            success = False

    if success:
        print('\nAll requested operations completed successfully!')
    else:
        print('\nSome operations failed. Check the output above for details.')
        return 1

    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nOperation cancelled by user.')
        sys.exit(130)