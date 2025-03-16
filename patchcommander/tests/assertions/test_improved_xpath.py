import unittest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from patchcommander.core.pipeline.models import PatchOperation
from patchcommander.core.utils.xpath_utils import analyze_xpath
from patchcommander.core.pipeline.pre_processors.custom.xpath_method_corrector import XPathMethodCorrector

class TestImprovedXPath(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.tempdir.name)
        
        # Create test files
        self.python_test_file = self.temp_path / "test_file.py"
        with open(self.python_test_file, "w") as f:
            f.write('''
class TestClass:
    def method_with_self(self, arg1):
        return f"Method in class with {arg1}"

    @property
    def prop(self):
        return "property value"

    @staticmethod
    def static_method(arg1):
        return f"Static method: {arg1}"

def standalone_function(arg1):
    return f"Standalone function with {arg1}"

async def async_function(arg1):
    return f"Async function with {arg1}"
''')
        
        # Corrector test file with class method needing correction
        self.corrector_test_file = self.temp_path / "corrector_test.py"
        with open(self.corrector_test_file, "w") as f:
            f.write('''
class FirstClass:
    def some_method(self):
        pass

class TargetClass:
    def method_to_find(self, arg1):
        return f"This should be found by corrector with {arg1}"

    def another_method(self):
        pass

class LastClass:
    def unrelated_method(self):
        pass
''')

    def tearDown(self):
        self.tempdir.cleanup()

    def test_analyze_xpath_class(self):
        """Test that analyze_xpath correctly identifies a class xpath"""
        operation = PatchOperation(
            name='FILE', 
            path=str(self.python_test_file), 
            xpath='TestClass',
            content='''
class TestClass:
    def new_method(self):
        return "New method"
''')
        operation.file_extension = 'py'
        
        result = analyze_xpath(operation)
        
        self.assertTrue(result)
        self.assertEqual(operation.attributes.get('target_type'), 'class')
        self.assertEqual(operation.attributes.get('class_name'), 'TestClass')

    def test_analyze_xpath_method(self):
        """Test that analyze_xpath correctly identifies a method xpath"""
        operation = PatchOperation(
            name='FILE', 
            path=str(self.python_test_file), 
            xpath='TestClass.method_with_self',
            content='''
def method_with_self(self, arg1, arg2):
    return f"Updated method with {arg1} and {arg2}"
''')
        operation.file_extension = 'py'
        
        result = analyze_xpath(operation)
        
        self.assertTrue(result)
        self.assertEqual(operation.attributes.get('target_type'), 'method')
        self.assertEqual(operation.attributes.get('class_name'), 'TestClass')
        self.assertEqual(operation.attributes.get('method_name'), 'method_with_self')

    def test_analyze_xpath_function(self):
        """Test that analyze_xpath correctly identifies a function xpath"""
        operation = PatchOperation(
            name='FILE', 
            path=str(self.python_test_file), 
            xpath='standalone_function',
            content='''
def standalone_function(arg1, arg2, arg3):
    return f"Updated function with {arg1}, {arg2}, and {arg3}"
''')
        operation.file_extension = 'py'
        
        result = analyze_xpath(operation)
        
        self.assertTrue(result)
        self.assertEqual(operation.attributes.get('target_type'), 'function')
        self.assertEqual(operation.attributes.get('function_name'), 'standalone_function')

    def test_analyze_xpath_async_function(self):
        """Test that analyze_xpath correctly identifies an async function xpath"""
        operation = PatchOperation(
            name='FILE', 
            path=str(self.python_test_file), 
            xpath='async_function',
            content='''
async def async_function(arg1, arg2):
    return f"Updated async function with {arg1} and {arg2}"
''')
        operation.file_extension = 'py'
        
        result = analyze_xpath(operation)
        
        self.assertTrue(result)
        self.assertEqual(operation.attributes.get('target_type'), 'function')
        self.assertEqual(operation.attributes.get('function_name'), 'async_function')

    def test_analyze_xpath_lines_range(self):
        """Test that analyze_xpath correctly identifies a lines range xpath"""
        operation = PatchOperation(
            name='FILE', 
            path=str(self.python_test_file), 
            xpath='lines:10:20',
            content="# These lines will replace lines 10-20")
        operation.file_extension = 'py'
        
        result = analyze_xpath(operation)
        
        self.assertTrue(result)
        self.assertEqual(operation.attributes.get('target_type'), 'lines')
        self.assertEqual(operation.attributes.get('start_line'), 10)
        self.assertEqual(operation.attributes.get('end_line'), 20)

    def test_analyze_xpath_invalid(self):
        """Test that analyze_xpath correctly identifies an invalid xpath"""
        operation = PatchOperation(
            name='FILE', 
            path=str(self.python_test_file), 
            xpath='Invalid.xpath.format',
            content="# This has an invalid xpath")
        operation.file_extension = 'py'
        
        result = analyze_xpath(operation)
        
        self.assertFalse(result)
        self.assertTrue(any('Invalid XPath format' in error for error in operation.errors))

    @patch('patchcommander.core.pipeline.pre_processors.custom.xpath_method_corrector.console')
    def test_method_with_self_without_class(self, mock_console):
        """Test method detection with 'self' parameter but no class in xpath"""
        operation = PatchOperation(
            name='FILE', 
            path=str(self.corrector_test_file), 
            xpath='method_to_find',
            content='''
def method_to_find(self, new_arg):
    return f"Updated method with {new_arg}"
''')
        operation.file_extension = 'py'
        operation.attributes = {'target_type': 'function', 'function_name': 'method_to_find'}
        
        corrector = XPathMethodCorrector()
        self.assertTrue(corrector.can_handle(operation))
        corrector.process(operation)
        
        # Verify XPathMethodCorrector updated the xpath with class name
        self.assertEqual(operation.xpath, 'TargetClass.method_to_find')
        self.assertEqual(operation.attributes.get('target_type'), 'method')
        self.assertEqual(operation.attributes.get('class_name'), 'TargetClass')
        self.assertEqual(operation.attributes.get('method_name'), 'method_to_find')

    @patch('patchcommander.core.pipeline.pre_processors.custom.xpath_method_corrector.console')
    def test_property_setter_detection(self, mock_console):
        """Test property setter detection"""
        operation = PatchOperation(
            name='FILE', 
            path=str(self.python_test_file), 
            xpath='prop',
            content='''
@prop.setter
def prop(self, value):
    self._prop = value
''')
        operation.file_extension = 'py'
        operation.attributes = {'target_type': 'function', 'function_name': 'prop'}
        
        corrector = XPathMethodCorrector()
        self.assertTrue(corrector.can_handle(operation))
        corrector.process(operation)
        
        # Verify XPathMethodCorrector attempted to find the class
        mock_console.print.assert_any_call(f"[blue]Found potential class method 'prop' with 'self' parameter but xpath doesn't include class name[/blue]")

    def test_static_method_not_corrected(self):
        """Test that static methods are not wrongly identified as instance methods"""
        operation = PatchOperation(
            name='FILE', 
            path=str(self.python_test_file), 
            xpath='static_method',
            content='''
@staticmethod
def static_method(arg1, arg2):
    return f"Updated static method with {arg1} and {arg2}"
''')
        operation.file_extension = 'py'
        operation.attributes = {'target_type': 'function', 'function_name': 'static_method'}
        
        corrector = XPathMethodCorrector()
        self.assertTrue(corrector.can_handle(operation))
        corrector.process(operation)
        
        # Should not change xpath as there's no self parameter
        self.assertEqual(operation.xpath, 'static_method')
        self.assertEqual(operation.attributes.get('target_type'), 'function')

    def test_nonexistent_file(self):
        """Test behavior with nonexistent file"""
        operation = PatchOperation(
            name='FILE', 
            path=str(self.temp_path / "nonexistent.py"), 
            xpath='some_method',
            content='''
def some_method(self, arg):
    return f"Method with {arg}"
''')
        operation.file_extension = 'py'
        operation.attributes = {'target_type': 'function', 'function_name': 'some_method'}
        
        corrector = XPathMethodCorrector()
        self.assertTrue(corrector.can_handle(operation))
        
        # Should not raise errors for nonexistent files
        corrector.process(operation)
        self.assertEqual(operation.xpath, 'some_method')

if __name__ == '__main__':
    unittest.main()