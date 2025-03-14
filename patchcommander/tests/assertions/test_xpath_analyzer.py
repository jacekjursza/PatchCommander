"""
Unit tests for the XPath analyzer.
"""
import unittest
import os
import sys
from pathlib import Path

# Add project root to path if needed
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from patchcommander.core.pipeline.models import PatchOperation
from patchcommander.core.pipeline.pre_processors.custom.xpath_analyzer import XPathAnalyzer
from patchcommander.core.utils.xpath_utils import analyze_xpath

class TestXPathAnalyzer(unittest.TestCase):
    """Test cases for the XPath analyzer."""

    def setUp(self):
        """Set up the test environment."""
        self.analyzer = XPathAnalyzer()

    def test_analyze_class_xpath(self):
        """Test analyzing a class xpath."""
        operation = PatchOperation(
            name="FILE",
            path="test/path.py",
            xpath="TestClass",
            content="class TestClass:\n    pass"
        )
        
        result = analyze_xpath(operation)
        
        self.assertTrue(result)
        self.assertEqual(operation.attributes.get("target_type"), "class")
        self.assertEqual(operation.attributes.get("class_name"), "TestClass")

    def test_analyze_method_xpath(self):
        """Test analyzing a method xpath."""
        operation = PatchOperation(
            name="FILE",
            path="test/path.py",
            xpath="TestClass.test_method",
            content="def test_method(self):\n    return True"
        )
        
        result = analyze_xpath(operation)
        
        self.assertTrue(result)
        self.assertEqual(operation.attributes.get("target_type"), "method")
        self.assertEqual(operation.attributes.get("class_name"), "TestClass")
        self.assertEqual(operation.attributes.get("method_name"), "test_method")

    def test_analyze_function_xpath(self):
        """Test analyzing a function xpath."""
        operation = PatchOperation(
            name="FILE",
            path="test/path.py",
            xpath="test_function",
            content="def test_function():\n    return True"
        )
        
        result = analyze_xpath(operation)
        
        self.assertTrue(result)
        self.assertEqual(operation.attributes.get("target_type"), "function")
        self.assertEqual(operation.attributes.get("function_name"), "test_function")

    def test_detect_method_in_content(self):
        """Test detecting a method in content when xpath doesn't include class name."""
        operation = PatchOperation(
            name="FILE",
            path="test/path.py",
            xpath="test_method",
            content="def test_method(self, arg1):\n    return self.value + arg1"
        )
        
        # Should detect this is a method due to self parameter
        result = analyze_xpath(operation)
        
        self.assertTrue(result)
        self.assertEqual(operation.attributes.get("target_type"), "function")
        self.assertEqual(operation.attributes.get("function_name"), "test_method")

    def test_invalid_xpath(self):
        """Test handling an invalid xpath."""
        operation = PatchOperation(
            name="FILE",
            path="test/path.py",
            xpath="Invalid.Path.Format",
            content="# Invalid content"
        )
        
        result = analyze_xpath(operation)
        
        self.assertFalse(result)
        self.assertTrue(any("Invalid XPath format" in error for error in operation.errors))

if __name__ == "__main__":
    unittest.main()