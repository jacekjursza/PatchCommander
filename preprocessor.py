import re
import textwrap
import ast
from rich.console import Console
from rich.prompt import Prompt
from utils import parse_attributes
console = Console()
TAG_TYPES = ['FILE', 'CLASS', 'METHOD', 'FUNCTION', 'OPERATION']

def process_method_tag_pre(tag_type, attr_str, content):
    attrs = parse_attributes(attr_str)
    dedented_content = textwrap.dedent(content).strip()
    try:
        module_node = ast.parse(dedented_content)
    except Exception as e:
        console.print(f'[yellow]Warning: Failed to parse METHOD content; leaving it unchanged. Error: {e}[/yellow]')
        return [f'<{tag_type}{attr_str}>{content}</{tag_type}>']
    func_defs = [node for node in module_node.body if isinstance(node, ast.FunctionDef)]
    if len(func_defs) > 1:
        answer = Prompt.ask('Detected multiple method definitions in METHOD tag. Split them into separate tags? (y/n)', default='y')
        if answer.lower() != 'y':
            return [f'<{tag_type}{attr_str}>{content}</{tag_type}>']
    if not func_defs:
        return [f'<{tag_type}{attr_str}>{content}</{tag_type}>']
    method_tags = []
    for func in func_defs:
        try:
            func_source = ast.unparse(func).strip()
        except Exception as e:
            console.print(f'[yellow]Warning: Failed to unparse function {func.name}: {e}[/yellow]')
            func_source = ''
        new_tag = f'<{tag_type}{attr_str}>\n{func_source}\n</{tag_type}>'
        method_tags.append(new_tag)
    return method_tags

def process_function_tag_pre(tag_type, attr_str, content):
    # Similar to process_method_tag_pre but for standalone functions
    dedented_content = textwrap.dedent(content).strip()
    try:
        module_node = ast.parse(dedented_content)
    except Exception as e:
        console.print(f'[yellow]Warning: Failed to parse FUNCTION content; leaving it unchanged. Error: {e}[/yellow]')
        return [f'<{tag_type}{attr_str}>{content}</{tag_type}>']
    func_defs = [node for node in module_node.body if isinstance(node, ast.FunctionDef)]
    if len(func_defs) > 1:
        answer = Prompt.ask('Detected multiple function definitions in FUNCTION tag. Split them into separate tags? (y/n)', default='y')
        if answer.lower() != 'y':
            return [f'<{tag_type}{attr_str}>{content}</{tag_type}>']
    if not func_defs:
        return [f'<{tag_type}{attr_str}>{content}</{tag_type}>']
    function_tags = []
    for func in func_defs:
        try:
            func_source = ast.unparse(func).strip()
        except Exception as e:
            console.print(f'[yellow]Warning: Failed to unparse function {func.name}: {e}[/yellow]')
            func_source = ''
        new_tag = f'<{tag_type}{attr_str}>\n{func_source}\n</{tag_type}>'
        function_tags.append(new_tag)
    return function_tags

def process_generic_tag(tag_type, attr_str, content):
    return f'<{tag_type}{attr_str}>{content}</{tag_type}>'

def process_self_closing_tag(tag_type, attr_str):
    return f'<{tag_type}{attr_str} />'

def run_preprocess(input_data):
    console.print('[bold]Starting pre-processing of input data...[/bold]')
    output_tags = []
    tag_pattern = re.compile('<(FILE|CLASS|METHOD|FUNCTION|OPERATION)(\\s+[^>]*)?\\s*(?:>(.*?)</\\1\\s*>|/>)', re.DOTALL)
    counts = {tag_type: 0 for tag_type in TAG_TYPES}
    for match in tag_pattern.finditer(input_data):
        tag_type = match.group(1)
        attr_str = match.group(2) or ''
        content = match.group(3) or ''
        counts[tag_type] += 1
        if tag_type == 'METHOD':
            tags = process_method_tag_pre(tag_type, attr_str, content)
            output_tags.extend(tags)
        elif tag_type == 'FUNCTION':
            tags = process_function_tag_pre(tag_type, attr_str, content)
            output_tags.extend(tags)
        elif tag_type == 'OPERATION':
            output_tags.append(process_self_closing_tag(tag_type, attr_str))
        else:
            output_tags.append(process_generic_tag(tag_type, attr_str, content))
    preprocessed_output = '\n\n'.join(output_tags)
    console.print('[green]Pre-processing complete![/green]')
    console.print('[bold]Summary of tags found:[/bold]')
    for (tag, count) in counts.items():
        console.print(f'  {tag}: {count}')
    return preprocessed_output