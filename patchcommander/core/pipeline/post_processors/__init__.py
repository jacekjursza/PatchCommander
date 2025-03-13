"""
Initialization of post-processors module.
"""
from .syntax_validator import SyntaxValidator
from .duplicate_checker import DuplicateMethodChecker

__all__ = ['SyntaxValidator', 'DuplicateMethodChecker']