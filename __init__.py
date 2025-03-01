"""
PatchCommander - A Python-based tool for streamlining AI-assisted code development.

PatchCommander processes code changes generated by Large Language Models (LLMs)
that follow a specific tag-based syntax. By instructing LLMs to format their code
suggestions using PatchCommander's tags, developers can easily and reliably
apply AI-generated changes across their codebase.
"""

# Import version from main.py
import re
import os
import sys

# Read version from main.py
def _get_version():
    main_file = os.path.join(os.path.dirname(__file__), "main.py")
    if not os.path.exists(main_file):
        return "unknown"

    with open(main_file, "r") as f:
        content = f.read()

    version_match = re.search(r'VERSION\s*=\s*[\'"]([^\'"]*)[\'"]', content)
    if version_match:
        return version_match.group(1)
    return "unknown"

__version__ = _get_version()

# CLI entry points
def cli():
    """Entry point for command-line interface."""
    from main import main
    sys.exit(main())

def cli_legacy():
    """Legacy entry point for backward compatibility."""
    import warnings
    warnings.warn(
        "The 'patchcommander' command is deprecated and will be removed in a future version. "
        "Please use 'pcmd' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from main import main
    sys.exit(main())

# Make main functionality available directly from module
from main import main

if __name__ == "__main__":
    cli()