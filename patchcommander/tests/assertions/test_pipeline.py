"""
Unit tests for the PatchCommander pipeline.
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

from patchcommander.core.pipeline.pipeline import Pipeline
from patchcommander.core.pipeline.pre_processors.global_processor import TagParser
from patchcommander.core.pipeline.pre_processors.custom import XPathAnalyzer, MarkdownCodeBlockCleaner


class TestPipeline(unittest.TestCase):
    """Test cases for the pipeline."""

    def setUp(self):
        """Set up the test environment."""
        self.pipeline = Pipeline()
        self.pipeline.set_global_preprocessor(TagParser())
        self.pipeline.add_preprocessor(XPathAnalyzer())
        self.pipeline.add_preprocessor(MarkdownCodeBlockCleaner())

        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

        # Create a test file
        self.test_file = self.test_dir / "test_file.py"
        with open(self.test_file, "w") as f:
            f.write("# Original content\n\nclass TestClass:\n    def test_method(self):\n        return 'original'\n")

    def tearDown(self):
        """Clean up after the test."""
        self.temp_dir.cleanup()

    def test_basic_pipeline(self):
        """Test basic pipeline functionality with a simple FILE operation."""
        # Create input with a FILE tag to modify the test file
        input_text = f'<FILE path="{self.test_file}">\n# Modified content\n\nclass TestClass:\n    def test_method(self):\n        return "modified"\n</FILE>'

        # Run the pipeline
        results = self.pipeline.run(input_text)

        # Verify the results
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.path, str(self.test_file))
        self.assertIn("Modified content", result.current_content)
        self.assertIn('return "modified"', result.current_content)

    def test_multiple_operations(self):
        """Test pipeline with multiple operations."""
        # Create a second test file
        test_file2 = self.test_dir / "test_file2.py"
        with open(test_file2, "w") as f:
            f.write("# Second file\n\ndef standalone_function():\n    return 42\n")

        # Create input with multiple operations
        input_text = f"""
        <FILE path="{self.test_file}" xpath="TestClass.test_method">
        def test_method(self):
            return "updated method"
        </FILE>
        
        <FILE path="{test_file2}" xpath="standalone_function">
        def standalone_function():
            return 100
        </FILE>
        """

        # Run the pipeline
        results = self.pipeline.run(input_text)

        # Verify the results
        self.assertEqual(len(results), 2)

        # Results should be in order of operations
        paths = [result.path for result in results]
        self.assertIn(str(self.test_file), paths)
        self.assertIn(str(test_file2), paths)

        # Check the content of each result
        for result in results:
            if result.path == str(self.test_file):
                self.assertIn('return "updated method"', result.current_content)
            elif result.path == str(test_file2):
                self.assertIn('return 100', result.current_content)

    def test_markdown_code_block_cleaner(self):
        """Test that markdown code blocks are cleaned properly."""
        # Input with markdown code blocks
        input_text = f"""
        <FILE path="{self.test_file}">
        ```python
        # Code inside markdown block
        class TestClass:
            def test_method(self):
                return "from markdown"
        ```
        </FILE>
        """

        # Run the pipeline
        results = self.pipeline.run(input_text)

        # Verify the results
        self.assertEqual(len(results), 1)
        result = results[0]

        # Markdown code block markers should be removed
        self.assertNotIn("```python", result.current_content)
        self.assertNotIn("```", result.current_content)
        self.assertIn('return "from markdown"', result.current_content)


if __name__ == "__main__":
    unittest.main()
