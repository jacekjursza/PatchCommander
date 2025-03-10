"""
Initialization of Python processors.
"""
from .base import PythonProcessor
from .class_processor import PythonClassProcessor
from .method_base import BasePythonMethodProcessor
from .base_diff_match_patch import BaseDiffMatchPatchProcessor, DMP_AVAILABLE
from .base_python_element_processor import BasePythonElementProcessor
from .method_diff_match_patch import DiffMatchPatchPythonMethodProcessor
from .function_diff_match_patch import DiffMatchPatchPythonFunctionProcessor

__all__ = [
    'PythonProcessor',
    'PythonClassProcessor',
    'BasePythonMethodProcessor',
    'BaseDiffMatchPatchProcessor',
    'BasePythonElementProcessor',
    'DiffMatchPatchPythonMethodProcessor',
    'DiffMatchPatchPythonFunctionProcessor'
]