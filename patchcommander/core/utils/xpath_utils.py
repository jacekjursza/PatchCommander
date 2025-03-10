"""
Utility functions for XPath handling in PatchCommander.
"""
import re
from typing import Dict, Optional, Tuple
from rich.console import Console
from patchcommander.core.pipeline.models import PatchOperation

console = Console()

def analyze_xpath(operation: PatchOperation) -> bool:
    """
    Analyzes and validates XPath in the operation.
    Sets appropriate attributes on the operation.

    Args:
        operation: Operation to analyze

    Returns:
        bool: True if analysis was successful, False otherwise
    """
    if not operation.xpath:
        return False

    console.print(f"[blue]Analyzing xpath: '{operation.xpath}'[/blue]")
    console.print(f"[blue]Content starts with: '{operation.content[:40].strip()}...'[/blue]")

    # Check for class.method pattern
    class_method_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*?)\.([A-Za-z_][A-Za-z0-9_]*?)$', operation.xpath)
    if class_method_match:
        class_name, method_name = class_method_match.groups()
        operation.attributes['target_type'] = 'method'
        operation.attributes['class_name'] = class_name
        operation.attributes['method_name'] = method_name
        console.print(f'[green]Recognized class method: {class_name}.{method_name}[/green]')
        return True

    # Check for function pattern by matching with content
    func_def_match = re.search(r'^\s*(async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)', 
                               operation.content, re.MULTILINE)
    function_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*?)$', operation.xpath)
    
    if function_match and func_def_match:
        function_name = function_match.group(1)
        if func_def_match.group(2) == function_name:
            operation.attributes['target_type'] = 'function'
            operation.attributes['function_name'] = function_name
            console.print(f'[green]Recognized function: {function_name}[/green]')
            return True

    # Check for class pattern
    class_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*?)$', operation.xpath)
    if class_match:
        class_name = class_match.group(1)
        if re.search(r'^\s*class\s+' + re.escape(class_name), operation.content, re.MULTILINE):
            operation.attributes['target_type'] = 'class'
            operation.attributes['class_name'] = class_name
            console.print(f'[green]Recognized class: {class_name}[/green]')
            return True
        elif func_def_match:  # If it's a function definition without a class.method pattern
            operation.attributes['target_type'] = 'function'
            operation.attributes['function_name'] = class_name
            console.print(f'[green]Recognized function: {class_name}[/green]')
            return True

    # If we got here, we couldn't identify the xpath
    operation.add_error(f'Invalid XPath format: {operation.xpath}')
    console.print(f'[red]Invalid XPath format: {operation.xpath}[/red]')
    return False

def find_function_boundaries(content: str, function_name: str) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str]]:
    """
    Finds the boundaries of a function in the code.

    Args:
        content: Code content
        function_name: Name of the function to find

    Returns:
        Tuple of (start_position, end_position, function_text, indentation)
        or (None, None, None, None) if function not found
    """
    pattern = r'(^|\n)([ \t]*)(async\s+)?def\s+' + re.escape(function_name) + r'\s*\([^)]*\)\s*(->.*?)?:'
    matches = list(re.finditer(pattern, content, re.MULTILINE))
    
    if not matches:
        return None, None, None, None

    # Use the last match in case there are multiple functions with the same name
    match = matches[-1]
    prefix = match.group(1)
    
    # Determine where the function starts
    if prefix == '\n':
        function_start = match.start(1)
    else:
        function_start = match.start()
    
    indentation = match.group(2)
    
    # Look for the function end by finding the next line with same or less indentation
    # that's not a blank line or a decorator line
    rest_of_code = content[match.end():]
    next_def_pattern = f"(^|\n)({re.escape(indentation)}(class|def)\\s+|{re.escape(indentation[:-4] if len(indentation) >= 4 else '')}def\\s+|{re.escape(indentation[:-4] if len(indentation) >= 4 else '')}class\\s+)"
    
    next_def_match = re.search(next_def_pattern, rest_of_code)
    
    if next_def_match:
        function_end = match.end() + next_def_match.start()
        if next_def_match.group(1) == '\n':
            function_end += 1
    else:
        function_end = len(content)
    
    function_text = content[function_start:function_end]
    
    return function_start, function_end, function_text, indentation

def find_class_method(content: str, class_name: str, method_name: str) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str]]:
    """
    Finds a method within a class.

    Args:
        content: Code content
        class_name: Name of the class
        method_name: Name of the method

    Returns:
        Tuple of (start_position, end_position, method_text, indentation)
        or (None, None, None, None) if method not found
    """
    # First find the class
    class_pattern = r'(^|\n)class\s+' + re.escape(class_name) + r'\s*(\([^)]*\))?\s*:'
    class_match = re.search(class_pattern, content)
    
    if not class_match:
        return None, None, None, None
    
    class_end = class_match.end()
    
    # Find the end of the class by looking for the next class or top-level function
    next_class_match = re.search(r'(^|\n)class\s+', content[class_end:])
    if next_class_match:
        class_content = content[class_end:class_end + next_class_match.start()]
    else:
        class_content = content[class_end:]
    
    # Look for the method in the class content
    method_pattern = r'(\n+)([ \t]*)def\s+' + re.escape(method_name) + r'\s*\([^)]*\)\s*(->.*?)?:'
    method_match = re.search(method_pattern, class_content)
    
    if not method_match:
        return None, None, None, None
    
    method_indent = method_match.group(2)
    method_start_rel = method_match.start()
    method_start_abs = class_end + method_start_rel
    method_def_rel = method_match.end()
    
    # Find the end of the method by checking indentation
    rest_of_code = class_content[method_def_rel:]
    method_end_rel = method_def_rel
    
    for i, line in enumerate(rest_of_code.splitlines(keepends=True)):
        if i == 0:
            method_end_rel += len(line)
            continue
        
        if not line.strip():
            method_end_rel += len(line)
            continue
        
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= len(method_indent) and not line.lstrip().startswith('@'):
            break
        
        method_end_rel += len(line)
    
    method_end_abs = class_end + method_end_rel
    method_text = content[method_start_abs:method_end_abs]
    
    return method_start_abs, method_end_abs, method_text, method_indent