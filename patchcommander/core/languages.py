"""
Centralny rejestr obsługiwanych języków programowania i ich parserów.
"""

import tree_sitter_python
import tree_sitter_javascript
from tree_sitter import Language, Parser

# Inicjalizacja obiektów Language dla obsługiwanych języków
PY_LANGUAGE = Language(tree_sitter_python.language())
JS_LANGUAGE = Language(tree_sitter_javascript.language())

# Mapowanie nazw języków na obiekty Language
LANGUAGES = {
    'python': PY_LANGUAGE,
    'javascript': JS_LANGUAGE
}

# Tworzymy centralne parsery dla każdego języka
_PARSER_CACHE = {}

def get_parser(language_code: str) -> Parser:
    """
    Pobierz parser dla danego języka.

    Args:
        language_code: Kod języka (np. 'python', 'javascript')

    Returns:
        Parser dla danego języka

    Raises:
        ValueError: Jeśli język nie jest obsługiwany
    """
    if language_code not in LANGUAGES:
        raise ValueError(f"Nieznany język: {language_code}")

    # Sprawdź czy parser jest już w cache
    if language_code not in _PARSER_CACHE:
        parser = Parser(LANGUAGES[language_code])
        _PARSER_CACHE[language_code] = parser

    return _PARSER_CACHE[language_code]

# Mapowanie rozszerzeń plików na kody języków
FILE_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'javascript',  # Na razie używamy JavaScript dla TypeScript
    '.tsx': 'javascript'
}


def get_language_code(language_obj) -> str:
    """
    Znajdź kod języka na podstawie obiektu Language.

    Args:
        language_obj: Obiekt Language z tree-sitter

    Returns:
        Kod języka (np. 'python', 'javascript')

    Raises:
        ValueError: Jeśli język nie jest obsługiwany
    """
    for code, lang in LANGUAGES.items():
        if lang == language_obj:
            return code

    raise ValueError("Nieznany obiekt języka")


def get_language_for_file(file_path: str) -> str:
    """
    Określ język na podstawie rozszerzenia pliku.

    Args:
        file_path: Ścieżka do pliku

    Returns:
        Kod języka (np. 'python', 'javascript')

    Raises:
        ValueError: Jeśli nie można określić języka dla pliku
    """
    import os
    _, ext = os.path.splitext(file_path.lower())

    if ext in FILE_EXTENSIONS:
        return FILE_EXTENSIONS[ext]

    raise ValueError(f"Nieobsługiwane rozszerzenie pliku: {ext}")