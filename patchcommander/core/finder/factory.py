# patchcommander/core/finder/factory.py

from patchcommander.core.finder.base import CodeFinder
from patchcommander.core.finder.python_code_finder import PythonCodeFinder
from patchcommander.core.finder.typescript_code_finder import TypeScriptCodeFinder

def get_code_finder(language: str) -> CodeFinder:
    if language.lower() == 'python':
        return PythonCodeFinder()
    elif language.lower() in ['typescript', 'javascript']:
        return TypeScriptCodeFinder()
    else:
        raise ValueError(f"Unsupported language: {language}")
