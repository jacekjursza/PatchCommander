"""
Unit tests for the PatchCommander API.
"""
import unittest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the project root to sys.path if needed
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from patchcommander.api import PatchCommanderAPI, process_text, apply_changes


class TestPatchCommanderAPI(unittest.TestCase):
    """Test cases for PatchCommanderAPI."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_process_text_basic(self):
        """Test basic text processing."""
        input_text = f"""
        <FILE path="{self.temp_dir}/test.py">
        def sample_function():
            return "Hello, world!"
        </FILE>
        """

        api = PatchCommanderAPI()
        results = api.process_text(input_text)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path, f"{self.temp_dir}/test.py")
        self.assertIn("def sample_function():", results[0].current_content)

    def test_process_text_with_xpath(self):
        """Test processing text with xpath."""
        # First create a file
        test_file = os.path.join(self.temp_dir, "xpath_test.py")
        with open(test_file, "w") as f:
            f.write("""
class TestClass:
    def method1(self):
        return "Original"

    def method2(self):
        return "Unchanged"
""")

        # Now modify it with xpath
        input_text = f"""
        <FILE path="{test_file}" xpath="TestClass.method1">
        def method1(self):
            return "Modified"
        </FILE>
        """

        api = PatchCommanderAPI()
        results = api.process_text(input_text)

        self.assertEqual(len(results), 1)
        self.assertIn("return \"Modified\"", results[0].current_content)
        self.assertIn("return \"Unchanged\"", results[0].current_content)

    def test_apply_changes(self):
        input_text = f'\n        <FILE path="{self.temp_dir}/applied.py">\n        print("This file was created by the test.")\n        </FILE>\n        '
        api = PatchCommanderAPI()
        results = api.process_text(input_text)
        modified_result = api.apply_changes(results, {results[0].path: True})
        self.assertEqual(modified_result[0], 1)  # One file modified
        self.assertEqual(modified_result[1], len(results[0].operations))  # Operations count
        self.assertTrue(os.path.exists(f'{self.temp_dir}/applied.py'))
        with open(f'{self.temp_dir}/applied.py', 'r') as f:
            content = f.read()
            self.assertIn('This file was created by the test', content)

    def test_generate_diff(self):
        """Test generating diff."""
        # Create a file first
        test_file = os.path.join(self.temp_dir, "diff_test.py")
        with open(test_file, "w") as f:
            f.write("def original():\n    return 'original'\n")

        # Now modify it
        input_text = f"""
        <FILE path="{test_file}">
        def original():
            return 'modified'
        </FILE>
        """

        api = PatchCommanderAPI()
        results = api.process_text(input_text)

        # Generate diff
        diffs = api.generate_diff(results)

        self.assertIn(test_file, diffs)
        self.assertIn("-    return 'original'", diffs[test_file])
        self.assertIn("+    return 'modified'", diffs[test_file])

    def test_operation_delete_file(self):
        test_file = os.path.join(self.temp_dir, 'to_delete.py')
        with open(test_file, 'w') as f:
            f.write('# This file will be deleted\n')
        input_text = f'\n        <OPERATION action="delete_file" source="{test_file}" />\n        '
        api = PatchCommanderAPI()
        results = api.process_text(input_text)
        modified_result = api.apply_changes(results, {test_file: True})
        self.assertEqual(modified_result[0], 1)  # One file modified
        self.assertEqual(modified_result[1], len(results[0].operations))  # Operations count
        self.assertFalse(os.path.exists(test_file))

    def test_convenience_functions(self):
        input_text = f'\n        <FILE path="{self.temp_dir}/convenience.py">\n        # Created via convenience function\n        </FILE>\n        '
        results = process_text(input_text)
        modified_result = apply_changes(results, auto_approve=True)
        self.assertEqual(modified_result[0], 1)  # One file modified
        self.assertEqual(modified_result[1], len(results[0].operations))  # Operations count
        self.assertTrue(os.path.exists(f'{self.temp_dir}/convenience.py'))


if __name__ == "__main__":
    unittest.main()
