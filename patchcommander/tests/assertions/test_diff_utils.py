"""
Unit tests for the diff utilities.
"""
import unittest
import os
import sys
from pathlib import Path

# Add project root to path if needed
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from patchcommander.core.utils.diff_utils import (
    generate_unified_diff,
    format_with_indentation,
    normalize_empty_lines
)

class TestDiffUtils(unittest.TestCase):
    """Test cases for the diff utilities."""

    def test_generate_unified_diff(self):
        """Test generating a unified diff."""
        old_content = "line 1\nline 2\nline 3\n"
        new_content = "line 1\nmodified line\nline 3\n"
        
        diff_lines = generate_unified_diff(old_content, new_content, "test_file.py")
        
        # Check that the diff contains expected markers
        diff_text = "\n".join(diff_lines)
        self.assertIn("--- current: test_file.py", diff_text)
        self.assertIn("+++ new: test_file.py", diff_text)
        self.assertIn("-line 2", diff_text)
        self.assertIn("+modified line", diff_text)

    def test_format_with_indentation(self):
        """Test formatting code with indentation."""
        code = "def test_function():\nreturn True"
        base_indent = "    "
        
        formatted_code = format_with_indentation(code, base_indent)
        
        expected = "    def test_function():\n        return True"
        self.assertEqual(formatted_code, expected)

    def test_format_with_indentation_preserve_empty_lines(self):
        """Test that empty lines are preserved when formatting with indentation."""
        code = "def test_function():\n\nreturn True"
        base_indent = "    "
        
        formatted_code = format_with_indentation(code, base_indent)
        
        expected = "    def test_function():\n\n        return True"
        self.assertEqual(formatted_code, expected)

    def test_normalize_empty_lines(self):
        """Test normalizing empty lines."""
        text = "line 1\n\n\n\nline 2"

        normalized = normalize_empty_lines(text, 2)

        expected = "line 1\n\nline 2"
        self.assertEqual(normalized, expected)

    def test_normalize_empty_lines_with_count(self):
        """Test normalizing empty lines with specific count."""
        text = "line 1\nline 2"
        
        normalized = normalize_empty_lines(text, 3)
        
        expected = "line 1\nline 2\n\n\n"
        self.assertEqual(normalized, expected)

if __name__ == "__main__":
    unittest.main()