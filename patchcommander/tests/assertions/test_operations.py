"""
Unit tests for the operations processors.
"""
import unittest
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path if needed
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from patchcommander.core.pipeline.models import PatchOperation, PatchResult
from patchcommander.core.pipeline.processors.operation_processor import OperationProcessor
from patchcommander.core.pipeline.processors.file_processor import FileProcessor

class TestOperations(unittest.TestCase):
    """Test cases for operation processors."""

    def setUp(self):
        """Set up the test environment."""
        self.operation_processor = OperationProcessor()
        self.file_processor = FileProcessor()
        
        # Create a temporary file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = os.path.join(self.temp_dir.name, "test_file.py")
        with open(self.test_file_path, "w") as f:
            f.write("# Original content\n\nclass TestClass:\n    def test_method(self):\n        return 'original'\n")

    def tearDown(self):
        """Clean up after the test."""
        self.temp_dir.cleanup()

    def test_file_processor(self):
        """Test the FILE processor for entire file replacement."""
        operation = PatchOperation(
            name="FILE",
            path=self.test_file_path,
            content="# New content\n\nprint('Hello, world!')\n"
        )
        
        result = PatchResult(
            path=self.test_file_path,
            original_content="# Original content\n",
            current_content="# Original content\n"
        )
        
        self.assertTrue(self.file_processor.can_handle(operation))
        self.file_processor.process(operation, result)
        
        self.assertEqual(result.current_content, "# New content\n\nprint('Hello, world!')\n")

    def test_operation_processor_delete_file(self):
        """Test the OPERATION processor for deleting a file."""
        operation = PatchOperation(
            name="OPERATION",
            path=self.test_file_path,
            action="delete_file",
            attributes={"source": self.test_file_path}
        )
        
        result = PatchResult(
            path=self.test_file_path,
            original_content="# Original content\n",
            current_content="# Original content\n"
        )
        
        self.assertTrue(self.operation_processor.can_handle(operation))
        self.operation_processor.process(operation, result)
        
        # Should set current_content to empty string to indicate deletion
        self.assertEqual(result.current_content, "")

    def test_invalid_operation(self):
        """Test handling an invalid operation type."""
        operation = PatchOperation(
            name="OPERATION",
            path=self.test_file_path,
            action="invalid_action",
            attributes={"source": self.test_file_path}
        )
        
        result = PatchResult(
            path=self.test_file_path,
            original_content="# Original content\n",
            current_content="# Original content\n"
        )
        
        self.operation_processor.process(operation, result)
        
        # Should have an error
        self.assertTrue(any("Unknown action" in error for error in operation.errors))
        # Content should remain unchanged
        self.assertEqual(result.current_content, "# Original content\n")

if __name__ == "__main__":
    unittest.main()