"""
Post-processor for syntax validation.
"""
import os

from patchcommander.core.pipeline import PatchResult, PostProcessor


class SyntaxValidator(PostProcessor):
    """
    Post-processor validating syntax of modified files.
    """

    def can_handle(self, operation):
        """
        This post-processor works at the PatchResult level, so this method is not used.
        """
        return False

    def process(self, result: PatchResult) -> None:
        """
        Validates syntax for the modified file.

        Args:
            result: Result to validate
        """
        # Skip files marked for deletion (empty content)
        if not result.current_content:
            return

        # Check the file extension
        _, ext = os.path.splitext(result.path)
        file_extension = ext.lower()[1:] if ext else ""

        # Validation for Python language
        if file_extension == "py":
            self._validate_python_syntax(result)

        # Here you can add validation for other languages (e.g. JavaScript)

    def _validate_python_syntax(self, result: PatchResult) -> None:
        """
        Validates syntax for Python code.

        Args:
            result: Result to validate
        """
        try:
            compile(result.current_content, result.path, "exec")
        except SyntaxError as e:
            error_message = f"Python syntax error in {result.path} line {e.lineno}, position {e.offset}: {e.msg}"
            result.add_error(error_message)

            # Optionally you can restore the original content
            # result.current_content = result.original_content