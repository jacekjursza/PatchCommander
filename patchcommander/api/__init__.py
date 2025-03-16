"""
PatchCommander API - Programmatic interface for code manipulation.
"""
# Re-export main functions for backwards compatibility
from patchcommander.api.processor import process_text, process_file
from patchcommander.api.manipulator import apply_changes, PatchCommanderAPI
from patchcommander.api.finder import (
    find_class, find_method, find_function, get_file_content
)

__all__ = [
    # Core API
    'process_text', 'process_file', 'apply_changes', 'PatchCommanderAPI',
    # Finder API
    'find_class', 'find_method', 'find_function', 'get_file_content',
]