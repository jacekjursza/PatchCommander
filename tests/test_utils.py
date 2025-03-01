import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import format_size, parse_attributes

class TestUtils(unittest.TestCase):
    def test_format_size(self):
        # Test bytes
        self.assertEqual(format_size(100), "100 bytes")
        self.assertEqual(format_size(0), "0 bytes")
        
        # Test kilobytes
        self.assertEqual(format_size(1024), "1.00 KB")
        self.assertEqual(format_size(2048), "2.00 KB")
        
        # Test megabytes
        self.assertEqual(format_size(1048576), "1.00 MB")
        self.assertEqual(format_size(2097152), "2.00 MB")
        
        # Test gigabytes
        self.assertEqual(format_size(1073741824), "1.00 GB")
        
    def test_parse_attributes(self):
        # Test empty string
        self.assertEqual(parse_attributes(""), {})
        
        # Test single attribute
        self.assertEqual(
            parse_attributes('path="file.py"'),
            {"path": "file.py"}
        )
        
        # Test multiple attributes
        self.assertEqual(
            parse_attributes('path="file.py" class="MyClass"'),
            {"path": "file.py", "class": "MyClass"}
        )
        
        # Test attributes with spaces
        self.assertEqual(
            parse_attributes('path = "file.py"  class = "MyClass"'),
            {"path": "file.py", "class": "MyClass"}
        )
        
        # Test with quotes inside attribute value
        self.assertEqual(
            parse_attributes('path="file\\"quote.py"'),
            {"path": 'file"quote.py'}
        )

class TestGetInputData(unittest.TestCase):
    @patch('utils.console')
    def test_file_not_found(self, mock_console):
        from utils import get_input_data
        
        with patch('os.path.exists', return_value=False):
            with self.assertRaises(SystemExit):
                get_input_data("nonexistent_file.txt")
        
        mock_console.print.assert_called_with("[bold red]File 'nonexistent_file.txt' not found.[/bold red]")
    
    @patch('utils.console')
    def test_successful_file_read(self, mock_console):
        from utils import get_input_data
        
        test_content = "Test file content"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write(test_content)
            tmp_name = tmp.name
        
        try:
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', unittest.mock.mock_open(read_data=test_content)):
                    result = get_input_data(tmp_name)
                    self.assertEqual(result, test_content)
        finally:
            os.unlink(tmp_name)
    
    @patch('utils.console')
    @patch('utils.pyperclip.paste', return_value="Test clipboard content")
    def test_clipboard_input(self, mock_paste, mock_console):
        from utils import get_input_data
        
        result = get_input_data(None)
        self.assertEqual(result, "Test clipboard content")
        mock_paste.assert_called_once()
    
    @patch('utils.console')
    @patch('utils.pyperclip.paste', return_value="")
    def test_empty_clipboard(self, mock_paste, mock_console):
        from utils import get_input_data
        
        with self.assertRaises(SystemExit):
            get_input_data(None)
        
        mock_console.print.assert_called_with("[bold yellow]Clipboard is empty. Please copy content first. Exiting.[/bold yellow]")

if __name__ == '__main__':
    unittest.main()
