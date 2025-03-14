"""
Initialization of core utilities module.
"""
from patchcommander.core.utils.xpath_utils import analyze_xpath, find_function_boundaries, find_class_method
from patchcommander.core.utils.diff_utils import generate_unified_diff, display_unified_diff, generate_side_by_side_diff, display_side_by_side_diff, format_with_indentation, normalize_empty_lines
from patchcommander.core.utils.class_extractor import ClassFeatureExtractor, ClassFeatures, ClassField, ClassMethod, ClassDiff

__all__ = [
    'analyze_xpath', 'find_function_boundaries', 'find_class_method',
    'generate_unified_diff', 'display_unified_diff', 'generate_side_by_side_diff', 
    'display_side_by_side_diff', 'format_with_indentation', 'normalize_empty_lines',
    'ClassFeatureExtractor', 'ClassFeatures', 'ClassField', 'ClassMethod', 'ClassDiff'
]