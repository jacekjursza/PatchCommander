"""
Central registry of supported programming languages and their parsers.
"""
import tree_sitter_python
import tree_sitter_javascript
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tree_sitter_python.language())
JS_LANGUAGE = Language(tree_sitter_javascript.language())
LANGUAGES = {'python': PY_LANGUAGE, 'javascript': JS_LANGUAGE}
_PARSER_CACHE = {}

def get_parser(language_code: str) -> Parser:
    """
    Get a parser for the given language.

    Args:
        language_code: Language code (e.g., 'python', 'javascript')

    Returns:
        Parser for the given language

    Raises:
        ValueError: If the language is not supported
    """
    if language_code not in LANGUAGES:
        raise ValueError(f'Unknown language: {language_code}')
    if language_code not in _PARSER_CACHE:
        parser = Parser(LANGUAGES[language_code])
        _PARSER_CACHE[language_code] = parser
    return _PARSER_CACHE[language_code]

FILE_EXTENSIONS = {'.py': 'python', '.js': 'javascript', '.jsx': 'javascript', '.ts': 'javascript', '.tsx': 'javascript'}

def get_language_code(language_obj) -> str:
    """
    Find the language code based on a Language object.

    Args:
        language_obj: Language object from tree-sitter

    Returns:
        Language code (e.g., 'python', 'javascript')

    Raises:
        ValueError: If the language is not supported
    """
    for (code, lang) in LANGUAGES.items():
        if lang == language_obj:
            return code
    raise ValueError('Unknown language object')

def get_language_for_file(file_path: str) -> str:
    """
    Determine the language based on the file extension.

    Args:
        file_path: Path to the file

    Returns:
        Language code (e.g., 'python', 'javascript')

    Raises:
        ValueError: If the language cannot be determined for the file
    """
    import os
    (_, ext) = os.path.splitext(file_path.lower())
    if ext in FILE_EXTENSIONS:
        return FILE_EXTENSIONS[ext]
    raise ValueError(f'Unsupported file extension: {ext}')