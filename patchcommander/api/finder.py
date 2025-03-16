"""
Finder functions for locating code elements.
"""
import os
from typing import Tuple, Optional, Dict, Any
from patchcommander.core.finder.factory import get_code_finder
from patchcommander.core.languages import get_language_for_file

def get_file_content(file_path: str) -> str:
    """
    Get the content of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Content of the file as string
    
    Raises:
        FileNotFoundError: If the file does not exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def find_class(file_path: str, class_name: str) -> Optional[Tuple[int, int, str]]:
    """
    Find a class in a file.
    
    Args:
        file_path: Path to the file
        class_name: Name of the class to find
        
    Returns:
        Tuple of (start_line, end_line, class_content) if found, None otherwise
    """
    try:
        content = get_file_content(file_path)
        language = get_language_for_file(file_path)
        finder = get_code_finder(language)
        
        start_line, end_line = finder.find_class(content, class_name)
        
        if start_line == 0 or end_line == 0:
            return None
        
        lines = content.splitlines()
        class_content = "\n".join(lines[start_line-1:end_line])
        
        return (start_line, end_line, class_content)
    except (FileNotFoundError, ValueError) as e:
        return None

def find_method(file_path: str, class_name: str, method_name: str) -> Optional[Tuple[int, int, str]]:
    """
    Find a method within a class in a file.
    
    Args:
        file_path: Path to the file
        class_name: Name of the class containing the method
        method_name: Name of the method to find
        
    Returns:
        Tuple of (start_line, end_line, method_content) if found, None otherwise
    """
    try:
        content = get_file_content(file_path)
        language = get_language_for_file(file_path)
        finder = get_code_finder(language)
        
        start_line, end_line = finder.find_method(content, class_name, method_name)
        
        if start_line == 0 or end_line == 0:
            return None
        
        lines = content.splitlines()
        method_content = "\n".join(lines[start_line-1:end_line])
        
        return (start_line, end_line, method_content)
    except (FileNotFoundError, ValueError) as e:
        return None

def find_function(file_path: str, function_name: str) -> Optional[Tuple[int, int, str]]:
    """
    Find a standalone function in a file.
    
    Args:
        file_path: Path to the file
        function_name: Name of the function to find
        
    Returns:
        Tuple of (start_line, end_line, function_content) if found, None otherwise
    """
    try:
        content = get_file_content(file_path)
        language = get_language_for_file(file_path)
        finder = get_code_finder(language)
        
        start_line, end_line = finder.find_function(content, function_name)
        
        if start_line == 0 or end_line == 0:
            return None
        
        lines = content.splitlines()
        function_content = "\n".join(lines[start_line-1:end_line])
        
        return (start_line, end_line, function_content)
    except (FileNotFoundError, ValueError) as e:
        return None