#!/usr/bin/env python3
"""
Script to publish PatchCommander to PyPI.
"""

import os
import sys
import subprocess
import shutil

def run_command(command, cwd=None):
    """Run a command and return its output."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True,
        cwd=cwd
    )
    stdout, stderr = process.communicate()

    print(stdout)
    if stderr:
        print(f"STDERR: {stderr}")

    return process.returncode == 0

def clean_previous_builds():
    """Remove previous build artifacts."""
    dirs_to_clean = ["build", "dist", "patchcommander.egg-info"]
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Removing {d}...")
            shutil.rmtree(d)

def build_package():
    """Build the Python package."""
    print("Building package...")
    return run_command(f"{sys.executable} -m build")

def test_build():
    """Test the built package with twine."""
    print("Testing package with twine...")
    return run_command(f"{sys.executable} -m twine check dist/*")

def upload_test_pypi():
    """Upload the package to Test PyPI."""
    choice = input("Upload to Test PyPI? (y/n): ").lower().strip()
    if choice != 'y':
        return True

    print("Uploading to Test PyPI...")
    return run_command(f"{sys.executable} -m twine upload --repository testpypi dist/*")

def upload_pypi():
    """Upload the package to PyPI."""
    choice = input("Upload to PyPI? (y/n): ").lower().strip()
    if choice != 'y':
        return True

    print("Uploading to PyPI...")
    return run_command(f"{sys.executable} -m twine upload dist/*")

def main():
    """Main function."""
    print("PatchCommander Publication Script")
    print("=================================")

    # Install required packages
    print("Installing required packages...")
    run_command(f"{sys.executable} -m pip install build twine")

    # Clean previous builds
    clean_previous_builds()

    # Build package
    if not build_package():
        print("Failed to build package!")
        return 1

    # Test the build
    if not test_build():
        print("Package failed Twine checks!")
        choice = input("Continue anyway? (y/n): ").lower().strip()
        if choice != 'y':
            return 1

    # Upload to Test PyPI
    if not upload_test_pypi():
        print("Failed to upload to Test PyPI!")
        choice = input("Continue to PyPI anyway? (y/n): ").lower().strip()
        if choice != 'y':
            return 1

    # Upload to PyPI
    if not upload_pypi():
        print("Failed to upload to PyPI!")
        return 1

    print("\nPublication process completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())