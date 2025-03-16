"""
Utility functions for XPath handling in PatchCommander.
"""
import re
from typing import Dict, Optional, Tuple
from rich.console import Console
from patchcommander.core.pipeline.models import PatchOperation

console = Console()

def analyze_xpath(operation: PatchOperation) -> bool:
    if not operation.xpath:
        return False
    console.print(f"[blue]Analyzing xpath: '{operation.xpath}'[/blue]")

    # Lines range matcher (e.g. "lines:10:20")
    lines_match = re.match('^lines:(\\d+):(\\d+)$', operation.xpath)
    if lines_match:
        start_line = int(lines_match.group(1))
        end_line = int(lines_match.group(2))
        operation.attributes['target_type'] = 'lines'
        operation.attributes['start_line'] = start_line
        operation.attributes['end_line'] = end_line
        console.print(f'[green]Recognized lines range: {start_line} to {end_line}[/green]')
        return True

    # Class method matcher (e.g. "ClassName.method_name")
    class_method_match = re.match('^([A-Za-z_][A-Za-z0-9_]*?)\\.([A-Za-z_][A-Za-z0-9_]*?)$', operation.xpath)
    if class_method_match:
        (class_name, method_name) = class_method_match.groups()
        operation.attributes['target_type'] = 'method'
        operation.attributes['class_name'] = class_name
        operation.attributes['method_name'] = method_name
        console.print(f'[green]Recognized class method: {class_name}.{method_name}[/green]')
        return True

    # Simple name matcher (could be class or function)
    simple_name_match = re.match('^([A-Za-z_][A-Za-z0-9_]*?)$', operation.xpath)
    if simple_name_match:
        name = simple_name_match.group(1)

        # First check if it's a class
        class_def_match = re.search('^\\s*class\\s+' + re.escape(name) + '\\s*[:(]', operation.content, re.MULTILINE)
        if class_def_match:
            operation.attributes['target_type'] = 'class'
            operation.attributes['class_name'] = name
            console.print(f'[green]Recognized class: {name}[/green]')
            return True

        # Then check if it's a function definition in the content
        func_def_match = re.search('^\\s*(async\\s+)?def\\s+' + re.escape(name) + '\\s*\\(', operation.content, re.MULTILINE)
        if func_def_match:
            # Check for "self" parameter which indicates it might be a method
            self_param_match = re.search('def\\s+' + re.escape(name) + '\\s*\\(\\s*self\\b', operation.content, re.MULTILINE)
            if self_param_match:
                console.print(f'[yellow]Warning: Function "{name}" has "self" parameter but xpath doesn\'t include class name.[/yellow]')
                console.print(f'[yellow]This might be a method. Consider using "ClassName.{name}" format for methods.[/yellow]')

            operation.attributes['target_type'] = 'function'
            operation.attributes['function_name'] = name
            console.print(f'[green]Recognized function: {name}[/green]')
            return True

        # If not found in content, try to infer from file extension and common language patterns
        if operation.file_extension == 'py':
            # For Python, assume it's a function unless content looks like a class
            if re.search('class\\s+[A-Za-z_]', operation.content, re.MULTILINE):
                console.print(f'[yellow]Warning: Using function xpath "{name}" but content contains class definitions.[/yellow]')
                console.print(f'[yellow]If targeting a specific class, use "ClassName" format.[/yellow]')

            operation.attributes['target_type'] = 'function'
            operation.attributes['function_name'] = name
            console.print(f'[green]Inferred function target: {name}[/green]')
            return True
        elif operation.file_extension in ['js', 'jsx', 'ts', 'tsx']:
            # For JS/TS, check content patterns to guess between component, class or function
            if re.search('(export\\s+)?class\\s+[A-Za-z_]', operation.content, re.MULTILINE):
                console.print(f'[yellow]Warning: Using function xpath "{name}" but content contains class definitions.[/yellow]')
                console.print(f'[yellow]If targeting a specific class, use "ClassName" format.[/yellow]')

            operation.attributes['target_type'] = 'function'
            operation.attributes['function_name'] = name
            console.print(f'[green]Inferred function target: {name}[/green]')
            return True
        else:
            # For other languages, make a best guess based on content
            operation.attributes['target_type'] = 'function'
            operation.attributes['function_name'] = name
            console.print(f'[green]Guessed function target: {name}[/green]')
            return True

    # If we got here, the xpath format wasn't recognized
    operation.add_error(f'Invalid XPath format: {operation.xpath}')
    console.print(f'[red]Invalid XPath format: {operation.xpath}[/red]')
    console.print(f'[yellow]Use "ClassName" for classes, "ClassName.method_name" for methods, or "function_name" for functions.[/yellow]')
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
    class_pattern = '(^|\\n)class\\s+' + re.escape(class_name) + '\\s*(\\([^)]*\\))?\\s*:'
    class_match = re.search(class_pattern, content)
    if not class_match:
        return (None, None, None, None)
    class_end = class_match.end()
    next_class_match = re.search('(^|\\n)class\\s+', content[class_end:])
    if next_class_match:
        class_content = content[class_end:class_end + next_class_match.start()]
    else:
        class_content = content[class_end:]
    method_pattern = '(\\n+)([ \\t]*)(async\\s+)?def\\s+' + re.escape(method_name) + '\\s*\\([^)]*\\)\\s*(->.*?)?:'
    method_match = re.search(method_pattern, class_content)
    if not method_match:
        return (None, None, None, None)
    method_indent = method_match.group(2)
    method_start_rel = method_match.start()
    method_start_abs = class_end + method_start_rel
    method_def_rel = method_match.end()
    rest_of_code = class_content[method_def_rel:]
    method_end_rel = method_def_rel
    for (i, line) in enumerate(rest_of_code.splitlines(keepends=True)):
        if i == 0:
            method_end_rel += len(line)
            continue
        if not line.strip():
            method_end_rel += len(line)
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= len(method_indent) and (not line.lstrip().startswith('@')):
            break
        method_end_rel += len(line)
    method_end_abs = class_end + method_end_rel
    method_text = content[method_start_abs:method_end_abs]
    return (method_start_abs, method_end_abs, method_text, method_indent)

