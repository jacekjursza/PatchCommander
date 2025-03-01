#!/usr/bin/env python3
"""
Script to publish PatchCommander to PyPI.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return its output."""
    print(f"Executing: {command}")

    # Use a list for command arguments if not already a list
    if isinstance(command, str):
        # Split the command only if it's a string
        cmd_args = command.split()
    else:
        cmd_args = command

    try:
        process = subprocess.run(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            cwd=cwd
        )

        # Print the output
        if process.stdout:
            print(process.stdout)

        if process.returncode != 0:
            print(f"Error executing command (return code {process.returncode})")
            if process.stderr:
                print(f"STDERR: {process.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Exception while executing command: {e}")
        return False

def clean_previous_builds():
    """Remove previous build artifacts."""
    print("Cleaning previous build artifacts...")

    # Always clean these directories
    dirs_to_clean = ["build", "patchcommander.egg-info"]
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Removing {d}...")
            shutil.rmtree(d)

    # Check if dist directory has distribution files
    has_dist_files = False
    if os.path.exists("dist"):
        dist_files = list(Path("dist").glob("*.whl")) + list(Path("dist").glob("*.tar.gz"))
        has_dist_files = len(dist_files) > 0

    # Only clean dist if there are no distribution files or user confirms
    if os.path.exists("dist") and not has_dist_files:
        print("Removing dist...")
        shutil.rmtree("dist")
    elif os.path.exists("dist") and has_dist_files:
        choice = input("Distribution files found in dist/. Clean anyway? (y/n): ").lower().strip()
        if choice == 'y':
            print("Removing dist...")
            shutil.rmtree("dist")
        else:
            print("Keeping existing distribution files.")

def build_package():
    """Build the Python package."""
    print("Building package...")
    return run_command([sys.executable, "-m", "build"])

def test_build():
    """Test the built package with twine."""
    print("Testing package with twine...")
    wheel_files = list(Path("dist").glob("*.whl"))
    tar_files = list(Path("dist").glob("*.tar.gz"))

    if not wheel_files and not tar_files:
        print("No distribution files found in dist directory!")
        return False

    # Build file lists for command
    files = []
    for f in wheel_files:
        files.append(str(f))
    for f in tar_files:
        files.append(str(f))

    print(f"Found distribution files: {files}")

    cmd = [sys.executable, "-m", "twine", "check"] + files
    return run_command(cmd)

def upload_test_pypi():
    """Upload the package to Test PyPI."""
    choice = input("Upload to Test PyPI? (y/n): ").lower().strip()
    if choice != 'y':
        return True

    print("Uploading to Test PyPI...")
    wheel_files = list(Path("dist").glob("*.whl"))
    tar_files = list(Path("dist").glob("*.tar.gz"))

    # Build file lists for command
    files = []
    for f in wheel_files:
        files.append(str(f))
    for f in tar_files:
        files.append(str(f))

    if not files:
        print("No distribution files found to upload!")
        return False

    cmd = [sys.executable, "-m", "twine", "upload", "--repository", "testpypi"] + files
    return run_command(cmd)

def upload_pypi():
    """Upload the package to PyPI."""
    choice = input("Upload to PyPI? (y/n): ").lower().strip()
    if choice != 'y':
        return True

    print("Uploading to PyPI...")
    wheel_files = list(Path("dist").glob("*.whl"))
    tar_files = list(Path("dist").glob("*.tar.gz"))

    # Build file lists for command
    files = []
    for f in wheel_files:
        files.append(str(f))
    for f in tar_files:
        files.append(str(f))

    if not files:
        print("No distribution files found to upload!")
        return False

    cmd = [sys.executable, "-m", "twine", "upload"] + files
    return run_command(cmd)

def main():
    """Main function."""
    print("PatchCommander Publication Script")
    print("=================================")

    # Install required packages
    print("Installing required packages...")
    run_command([sys.executable, "-m", "pip", "install", "build", "twine", "wheel", "setuptools"])

    # Check if we already have distribution files
    dist_exists = os.path.exists("dist")
    dist_files = []
    if dist_exists:
        wheel_files = list(Path("dist").glob("*.whl"))
        tar_files = list(Path("dist").glob("*.tar.gz"))
        dist_files = wheel_files + tar_files

    should_build = True
    if dist_files:
        print("\nFound existing distribution files:")
        for f in dist_files:
            print(f"- {f}")
        should_build = input("\nBuild new package files? (y/n): ").lower().strip() == 'y'

    # Clean previous builds if we're going to rebuild
    if should_build:
        clean_previous_builds()

    # Build package if needed
    if should_build:
        print("\nThis script will build and publish the Python package to PyPI.")
        print("If you want to build an executable instead, use build.py.\n")

        choice = input("Continue with building Python package? (y/n): ").lower().strip()
        if choice != 'y':
            print("Operation cancelled.")
            return 0

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