import unittest
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path to make patchcommander importable
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from patchcommander.core.pipeline.processors import OperationManipulatorProcessor, FileManipulatorProcessor
from patchcommander.core.pipeline.models import PatchOperation, PatchResult

class TestOperations(unittest.TestCase):

    def setUp(self):
        self.operation_processor = OperationManipulatorProcessor()
        self.file_processor = FileManipulatorProcessor()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = os.path.join(self.temp_dir.name, 'test_file.py')
        with open(self.test_file_path, 'w') as f:
            f.write("# Original content\n\nclass TestClass:\n    def test_method(self):\n        return 'original'\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_file_processor(self):
        operation = PatchOperation(name='FILE', path=self.test_file_path, content="# New content\n\nprint('Hello, world!')\n")
        result = PatchResult(path=self.test_file_path, original_content='# Original content\n', current_content='# Original content\n')
        self.assertTrue(self.file_processor.can_handle(operation))
        self.file_processor.process(operation, result)
        self.assertEqual(result.current_content, "# New content\n\nprint('Hello, world!')\n")

    def test_operation_processor_delete_file(self):
        operation = PatchOperation(name='OPERATION', path=self.test_file_path, action='delete_file', attributes={'source': self.test_file_path})
        result = PatchResult(path=self.test_file_path, original_content='# Original content\n', current_content='# Original content\n')
        self.assertTrue(self.operation_processor.can_handle(operation))
        self.operation_processor.process(operation, result)
        self.assertEqual(result.current_content, '')

    def test_invalid_operation(self):
        operation = PatchOperation(name='OPERATION', path=self.test_file_path, action='invalid_action', attributes={'source': self.test_file_path})
        result = PatchResult(path=self.test_file_path, original_content='# Original content\n', current_content='# Original content\n')
        self.operation_processor.process(operation, result)
        self.assertTrue(any(('Unknown action' in error for error in operation.errors)))
        self.assertEqual(result.current_content, '# Original content\n')

if __name__ == '__main__':
    unittest.main()