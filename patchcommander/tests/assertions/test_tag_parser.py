"""
Unit tests for the tag parser.
"""
import unittest
import os
import sys
from pathlib import Path

# Add project root to path if needed
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from patchcommander.core.pipeline.pre_processors.global_processor import TagParser


class TestTagParser(unittest.TestCase):
    """Test cases for the TagParser class."""

    def setUp(self):
        """Set up the test environment."""
        self.parser = TagParser()

    def test_parse_file_tag(self):
        """Test parsing a simple FILE tag."""
        input_text = '<FILE path="test/path.py">\nprint("Hello, world!")\n</FILE>'
        operations = self.parser.process(input_text)

        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0].name, "FILE")
        self.assertEqual(operations[0].path, "test/path.py")
        self.assertEqual(operations[0].content.strip(), 'print("Hello, world!")')
        self.assertIsNone(operations[0].xpath)

    def test_parse_file_tag_with_xpath(self):
        """Test parsing a FILE tag with xpath."""
        input_text = '<FILE path="test/path.py" xpath="MyClass.my_method">\ndef my_method(self):\n    return 42\n</FILE>'
        operations = self.parser.process(input_text)

        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0].name, "FILE")
        self.assertEqual(operations[0].path, "test/path.py")
        self.assertEqual(operations[0].xpath, "MyClass.my_method")
        self.assertEqual(operations[0].content.strip(), 'def my_method(self):\n    return 42')

    def test_parse_operation_tag(self):
        """Test parsing an OPERATION tag."""
        input_text = '<OPERATION action="move_file" source="old/path.py" target="new/path.py" />'
        operations = self.parser.process(input_text)

        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0].name, "OPERATION")
        self.assertEqual(operations[0].action, "move_file")
        self.assertEqual(operations[0].path, "old/path.py")
        self.assertEqual(operations[0].attributes["source"], "old/path.py")
        self.assertEqual(operations[0].attributes["target"], "new/path.py")

    def test_parse_multiple_tags(self):
        """Test parsing multiple tags in one input."""
        input_text = """
        <FILE path="test/path1.py">
        print("File 1")
        </FILE>
        
        <FILE path="test/path2.py" xpath="MyClass">
        class MyClass:
            pass
        </FILE>
        
        <OPERATION action="delete_file" source="test/path3.py" />
        """
        operations = self.parser.process(input_text)

        self.assertEqual(len(operations), 3)
        self.assertEqual(operations[0].name, "FILE")
        self.assertEqual(operations[1].name, "FILE")
        self.assertEqual(operations[2].name, "OPERATION")



if __name__ == "__main__":
    unittest.main()
