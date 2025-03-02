import ast
import os
import textwrap
import re
from rich.console import Console
from confirmations import confirm_and_apply_change, confirm_simple_action
from utils import parse_attributes, sanitize_path
from apply_changes import pending_changes
console = Console()
OPERATIONS = {'move_file': ['source', 'target'], 'delete_file': ['source'], 'delete_method': ['source', 'class', 'method']}

# Dictionary to store in-memory file content during processing
in_memory_files = {}


def validate_file_path(file_path):
    """
    Validate that a file path is properly formatted and safe.

    Args:
        file_path (str): Path to validate

    Returns:
        bool: True if path is valid, False otherwise
    """
    if not file_path:
        console.print('[bold red]Path cannot be empty.[/bold red]')
        return False

    normalized_path = os.path.normpath(file_path)
    if '..' in normalized_path.split(os.sep):
        console.print('[bold red]Path traversal detected. Please use absolute paths.[/bold red]')
        return False

    if os.name == 'nt':
        invalid_chars = '<>|?*"'
        if any(c in invalid_chars for c in file_path):
            console.print(f'[yellow]Warning: Path contains potentially invalid characters for Windows: {invalid_chars}[/yellow]')
            return True
    else:
        invalid_chars = '<>'
        if any(c in invalid_chars for c in file_path):
            console.print(f'[yellow]Warning: Path contains potentially invalid characters: {invalid_chars}[/yellow]')
            return True

    return True

def get_file_content(file_path):
    """
    Get file content either from in-memory cache or from disk.

    Args:
        file_path (str): Path to the file

    Returns:
        str: File content or empty string if file doesn't exist
    """
    if file_path in in_memory_files:
        return in_memory_files[file_path]

    if not os.path.exists(file_path):
        return ''

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        console.print(f"[bold red]Error reading file '{file_path}': {e}[/bold red]")
        return ''

def update_in_memory_file(file_path, new_content):
    """
    Update the in-memory version of a file.

    Args:
        file_path (str): Path to the file
        new_content (str): New file content
    """
    in_memory_files[file_path] = new_content

def process_file_tag(attrs, content):
    """
    Process a FILE tag by replacing or creating a file with new content.

    Args:
        attrs (dict): Attributes from the FILE tag
        content (str): New content for the file
    """
    file_path = attrs.get('path')
    if not validate_file_path(file_path):
        return
    new_content = content.strip() + '\n'
    description = f'Replace entire file: {file_path}'

    update_in_memory_file(file_path, new_content)
    confirm_and_apply_change(file_path, new_content, description, pending_changes)

def extract_class_name(content):
    match = re.search('class\\s+([A-Za-z_]\\w*)\\s*[\\(:]', content)
    if match:
        return match.group(1)
    return None


def process_class_tag_ast(attrs, content, pending_changes):
    """
    Process a CLASS tag by updating or adding a class to a file.

    Args:
        attrs (dict): Attributes from the CLASS tag
        content (str): New content for the class
        pending_changes (list): List to collect pending changes
    """
    file_path = attrs.get('path')
    class_name = attrs.get('class')

    if not file_path:
        console.print("[bold red]CLASS tag missing 'path' attribute.[/bold red]")
        return

    if not class_name:
        class_name = extract_class_name(content)
        if class_name:
            console.print(f"[yellow]Deducted class name '{class_name}' from CLASS tag content.[/yellow]")
            attrs['class'] = class_name
        else:
            console.print("[bold red]CLASS tag missing 'class' attribute and class name could not be deduced from content.[/bold red]")
            return

    original_code = get_file_content(file_path)

    try:
        tree = ast.parse(original_code) if original_code else ast.Module(body=[], type_ignores=[])
    except SyntaxError as e:
        console.print(f"[bold red]Syntax error in existing file '{file_path}': {e}[/bold red]")
        if confirm_simple_action('Proceed anyway? This will replace the file with corrected syntax.'):
            tree = ast.Module(body=[], type_ignores=[])
        else:
            return
    except Exception as e:
        console.print(f'[bold red]Failed to parse {file_path}: {e}[/bold red]')
        return

    try:
        if content.strip().startswith("class "):
            class_module = ast.parse(textwrap.dedent(content))
            class_nodes = [node for node in class_module.body if isinstance(node, ast.ClassDef)]
            if class_nodes:
                new_class_node = class_nodes[0]  # Bierzemy pierwszą klasę
            else:
                console.print(f'[bold red]Failed to find class definition in content[/bold red]')
                return
        else:
            wrapped_content = f"class {class_name}:\n{textwrap.indent(content, '    ')}"
            class_module = ast.parse(textwrap.dedent(wrapped_content))
            class_nodes = [node for node in class_module.body if isinstance(node, ast.ClassDef)]
            if class_nodes:
                new_class_node = class_nodes[0]  # Bierzemy pierwszą klasę
            else:
                console.print(f'[bold red]Failed to parse class content[/bold red]')
                return
    except SyntaxError as e:
        line_num = e.lineno
        line = content.split('\n')[line_num - 1] if line_num <= len(content.split('\n')) else ''
        console.print(f'[bold red]Syntax error in new class content at line {line_num}:[/bold red]')
        console.print(f'[red]{line}[/red]')
        console.print(f"[red]{' ' * (e.offset - 1)}^[/red]")
        console.print(f'[red]{e}[/red]')
        return
    except Exception as e:
        console.print(f'[bold red]Failed to parse new class body content: {e}[/bold red]')
        return

    class_updated = update_or_add_class_node(tree, class_name, new_class_node)

    try:
        new_code = ast.unparse(tree)
    except Exception as e:
        console.print(f'[bold red]Error unparsing modified AST for {file_path}: {e}[/bold red]')
        return

    action_desc = 'Update' if class_updated else 'Add'
    update_in_memory_file(file_path, new_code)
    confirm_and_apply_change(file_path, new_code, f"{action_desc} class '{class_name}'", pending_changes)


def update_or_add_class_node(tree, class_name, new_class_node):
    """
    Update an existing class with a new class node or add if it doesn't exist.

    Args:
        tree (ast.Module): AST module to modify
        class_name (str): Name of the class to update
        new_class_node (ast.ClassDef): New class node to use as replacement

    Returns:
        bool: True if class was updated, False if it was added
    """
    class_found = False

    for i, node in enumerate(tree.body):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            # Replace the entire class node, not just its body
            tree.body[i] = new_class_node
            class_found = True
            break

    if not class_found:
        tree.body.append(new_class_node)
        console.print(f"[blue]Will add new class '{class_name}' to file[/blue]")
        return False
    else:
        console.print(f"[blue]Will update class '{class_name}' in file[/blue]")
        return True

def process_function_tag_ast(attrs, content, pending_changes):
    file_path = attrs.get('path')
    if file_path:
        sanitized_path = sanitize_path(file_path)
        attrs['path'] = sanitized_path
        file_path = sanitized_path
    if not file_path:
        console.print("[bold red]FUNCTION tag missing 'path' attribute.[/bold red]")
        return
    if not validate_file_path(file_path):
        return
    try:
        func_module = ast.parse(textwrap.dedent(content))
    except Exception as e:
        console.print(f'[bold red]Failed to parse new function content: {e}[/bold red]')
        return
    new_function = extract_function_from_ast(func_module)
    if new_function is None:
        console.print('[bold red]No function definition found in FUNCTION tag content.[/bold red]')
        return
    new_function_name = new_function.name

    original_code = get_file_content(file_path)

    if not original_code:
        handle_new_file_with_function(file_path, new_function, new_function_name, pending_changes)
        return

    try:
        tree = ast.parse(original_code)
    except Exception as e:
        console.print(f'[bold red]Failed to parse {file_path}: {e}[/bold red]')
        return
    function_updated = update_or_add_function(tree, new_function_name, new_function)
    if not function_updated:
        return
    try:
        new_code = ast.unparse(tree)
    except Exception as e:
        console.print(f'[bold red]Error unparsing modified AST for {file_path}: {e}[/bold red]')
        return

    update_in_memory_file(file_path, new_code)
    confirm_and_apply_change(file_path, new_code, f"Update function '{new_function_name}'", pending_changes)

def extract_function_from_ast(func_module):
    for node in func_module.body:
        if isinstance(node, ast.FunctionDef):
            return node
    return None

def handle_new_file_with_function(file_path, new_function, function_name, pending_changes):
    if not confirm_simple_action(f"File '{file_path}' not found. Create new file with function '{function_name}'?"):
        console.print(f"[yellow]Skipping FUNCTION tag for '{function_name}'.[/yellow]")
        return
    new_module = ast.Module(body=[new_function], type_ignores=[])
    new_code = ast.unparse(new_module)

    update_in_memory_file(file_path, new_code)
    confirm_and_apply_change(file_path, new_code, f"Create new file with function '{function_name}'", pending_changes)

def update_or_add_function(tree, function_name, new_function):
    function_found = False
    for (i, node) in enumerate(tree.body):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            tree.body[i] = new_function
            function_found = True
            break
    if not function_found:
        tree.body.append(new_function)
    action = 'update' if function_found else 'add'
    console.print(f"[blue]Will {action} function '{function_name}' in file[/blue]")
    return True

def process_method_tag_ast(attrs, content, pending_changes):
    file_path = attrs.get('path')
    class_name = attrs.get('class')
    if not file_path or not class_name:
        console.print("[bold red]METHOD tag missing 'path' or 'class' attribute.[/bold red]")
        return
    try:
        method_module = ast.parse(textwrap.dedent(content))
    except Exception as e:
        console.print(f'[bold red]Failed to parse new method content: {e}[/bold red]')
        return
    new_method = extract_method_from_ast(method_module)
    if new_method is None:
        console.print('[bold red]No function definition found in METHOD tag content.[/bold red]')
        return
    new_method_name = new_method.name

    original_code = get_file_content(file_path)

    if not original_code:
        handle_new_file_with_method(file_path, class_name, new_method, new_method_name, pending_changes)
        return

    try:
        tree = ast.parse(original_code)
    except Exception as e:
        console.print(f'[bold red]Failed to parse {file_path}: {e}[/bold red]')
        return
    method_updated = update_or_add_method(tree, class_name, new_method_name, new_method, file_path)
    if not method_updated:
        return
    try:
        new_code = ast.unparse(tree)
    except Exception as e:
        console.print(f'[bold red]Error unparsing modified AST for {file_path}: {e}[/bold red]')
        return

    update_in_memory_file(file_path, new_code)
    confirm_and_apply_change(file_path, new_code, f"Update method '{new_method_name}' in class '{class_name}'", pending_changes)

def extract_method_from_ast(method_module):
    for node in method_module.body:
        if isinstance(node, ast.FunctionDef):
            return node
    return None

def handle_new_file_with_method(file_path, class_name, new_method, method_name, pending_changes):
    if not confirm_simple_action(f"File '{file_path}' not found. Create new file with class '{class_name}' containing method '{method_name}'?"):
        console.print(f"[yellow]Skipping METHOD tag for '{method_name}'.[/yellow]")
        return
    new_class_node = ast.ClassDef(name=class_name, bases=[], keywords=[], body=[new_method], decorator_list=[])
    new_module = ast.Module(body=[new_class_node], type_ignores=[])
    new_code = ast.unparse(new_module)

    update_in_memory_file(file_path, new_code)
    confirm_and_apply_change(file_path, new_code, f"Create new class '{class_name}' with method '{method_name}'", pending_changes)

def update_or_add_method(tree, class_name, method_name, new_method, file_path):

    class MethodReplacer(ast.NodeTransformer):

        def __init__(self, target_class, target_method, new_method):
            self.target_class = target_class
            self.target_method = target_method
            self.new_method = new_method
            self.found_class = False
            self.found_method = False
            super().__init__()

        def visit_ClassDef(self, node):
            if node.name == self.target_class:
                self.found_class = True
                found = False
                new_body = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == self.target_method:
                        new_body.append(self.new_method)
                        found = True
                        self.found_method = True
                    else:
                        new_body.append(item)
                if not found:
                    new_body.append(self.new_method)
                    self.found_method = True
                node.body = new_body
                return node
            return self.generic_visit(node)

    replacer = MethodReplacer(class_name, method_name, new_method)
    replacer.visit(tree)
    if not replacer.found_class:
        console.print(f"[bold red]Class '{class_name}' not found in {file_path}.[/bold red]")
        if confirm_simple_action(f"Create class '{class_name}' in file '{file_path}'?"):
            new_class_node = ast.ClassDef(name=class_name, bases=[], keywords=[], body=[new_method], decorator_list=[])
            tree.body.append(new_class_node)
            console.print(f"[blue]Will add new class '{class_name}' with method '{method_name}'[/blue]")
            return True
        return False
    action = 'update' if replacer.found_method else 'add'
    console.print(f"[blue]Will {action} method '{method_name}' in class '{class_name}'[/blue]")
    return True

def process_operation(attrs):
    action = attrs.get('action')
    if action not in OPERATIONS:
        console.print(f'[bold red]Unknown operation action: {action}[/bold red]')
        return
    required_attrs = OPERATIONS[action]
    missing_attrs = [attr for attr in required_attrs if attr not in attrs]
    if missing_attrs:
        console.print(f"[bold red]{action} operation requires {', '.join(missing_attrs)} attributes.[/bold red]")
        return
    if 'source' in attrs:
        attrs['source'] = sanitize_path(attrs['source'])
    if 'target' in attrs:
        attrs['target'] = sanitize_path(attrs['target'])
    if action == 'move_file':
        handle_move_file_operation(attrs)
    elif action == 'delete_file':
        handle_delete_file_operation(attrs)
    elif action == 'delete_method':
        handle_delete_method_operation(attrs)

def handle_move_file_operation(attrs):
    source = attrs.get('source')
    target = attrs.get('target')
    if not os.path.exists(source) and source not in in_memory_files:
        console.print(f"[bold red]Source file '{source}' does not exist.[/bold red]")
        return
    if os.path.exists(target) or target in in_memory_files:
        if not confirm_simple_action(f"Target file '{target}' already exists. Overwrite?"):
            console.print('[yellow]Move file operation cancelled.[/yellow]')
            return
    if not confirm_simple_action(f"Move file from '{source}' to '{target}'?"):
        console.print('[yellow]Move file operation cancelled.[/yellow]')
        return

    # Handle in-memory file first
    if source in in_memory_files:
        content = in_memory_files[source]
        in_memory_files[target] = content
        del in_memory_files[source]

    try:
        target_dir = os.path.dirname(target)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        import shutil
        if os.path.exists(source):
            shutil.move(source, target)
        console.print(f'[green]Moved file from {source} to {target}.[/green]')
    except Exception as e:
        console.print(f'[bold red]Error moving file: {e}[/bold red]')

def handle_delete_file_operation(attrs):
    source = attrs.get('source')
    if not os.path.exists(source) and source not in in_memory_files:
        console.print(f"[bold red]File '{source}' does not exist.[/bold red]")
        return
    if not confirm_simple_action(f"Delete file '{source}'?"):
        console.print('[yellow]Delete file operation cancelled.[/yellow]')
        return

    # Remove from in-memory files if present
    if source in in_memory_files:
        del in_memory_files[source]

    try:
        if os.path.exists(source):
            os.remove(source)
        console.print(f'[green]Deleted file: {source}.[/green]')
    except Exception as e:
        console.print(f'[bold red]Error deleting file: {e}[/bold red]')

def handle_delete_method_operation(attrs):
    source = attrs.get('source')
    class_name = attrs.get('class')
    method_name = attrs.get('method')

    original_code = get_file_content(source)

    if not original_code:
        console.print(f"[bold red]File '{source}' does not exist.[/bold red]")
        return

    try:
        tree = ast.parse(original_code)
    except Exception as e:
        console.print(f'[bold red]Failed to parse {source}: {e}[/bold red]')
        return

    class DeleteMethodTransformer(ast.NodeTransformer):

        def visit_ClassDef(self, node):
            if node.name == class_name:
                node.body = [item for item in node.body if not (hasattr(item, 'name') and item.name == method_name)]
                return node
            return self.generic_visit(node)
    transformer = DeleteMethodTransformer()
    new_tree = transformer.visit(tree)
    try:
        new_code = ast.unparse(new_tree)
    except Exception as e:
        console.print(f'[bold red]Error unparsing AST for {source}: {e}[/bold red]')
        return

    update_in_memory_file(source, new_code)
    confirm_and_apply_change(source, new_code, f"Delete method '{method_name}' from class '{class_name}'", pending_changes)

def diagnose_paths(input_data):
    """
    Check for problematic paths in tag attributes and report them without making changes.

    Args:
        input_data (str): Input data containing tags
    """
    console.print('[bold]Diagnosing paths in input data...[/bold]')

    # Define invalid characters based on operating system
    invalid_chars = '<>:"|?*' if os.name == 'nt' else '<>'

    tag_pattern = re.compile('<(FILE|CLASS|METHOD|FUNCTION|OPERATION)(\\s+[^>]*)?\\s*(?:>(.*?)</\\1\\s*>|/>)', re.DOTALL)
    problematic_paths = []

    for match in tag_pattern.finditer(input_data):
        tag_type = match.group(1)
        attr_str = match.group(2) or ''

        attrs = parse_attributes(attr_str)
        paths = []

        # Collect all path attributes
        if 'path' in attrs:
            paths.append(('path', attrs['path']))
        if 'source' in attrs:
            paths.append(('source', attrs['source']))
        if 'target' in attrs:
            paths.append(('target', attrs['target']))

        # Check each path for invalid characters
        for attr_name, path in paths:
            if not path:
                continue

            # Check if path contains any invalid characters
            has_invalid_chars = any(c in path for c in invalid_chars)
            if has_invalid_chars:
                problematic_paths.append((tag_type, attr_name, path))

    # Report findings
    if problematic_paths:
        console.print('[bold red]Found problematic paths:[/bold red]')
        for tag_type, attr_name, path in problematic_paths:
            sanitized = sanitize_path(path)
            console.print(f'  [yellow]<{tag_type}>[/yellow] {attr_name}="{path}" → {attr_name}="{sanitized}"')
    else:
        console.print('[green]No problematic paths found.[/green]')

def run_process(input_data):
    console.print('[bold]Starting processing of tags...[/bold]')

    # Clear in-memory files at the start of processing
    in_memory_files.clear()

    op_pattern = re.compile('<(OPERATION)(\\s+[^>]*)?\\s*/>', re.DOTALL)
    op_count = 0
    for op_match in op_pattern.finditer(input_data):
        op_count += 1
        attr_str = op_match.group(2) or ''
        attrs = parse_attributes(attr_str)
        process_operation(attrs)
    tag_pattern = re.compile('<(FILE|CLASS|METHOD|FUNCTION)(\\s+[^>]*)?\\s*>(.*?)</\\1\\s*>', re.DOTALL)
    counts = {'FILE': 0, 'CLASS': 0, 'METHOD': 0, 'FUNCTION': 0}
    for match in tag_pattern.finditer(input_data):
        tag_type = match.group(1)
        attr_str = match.group(2) or ''
        content = match.group(3)
        attrs = parse_attributes(attr_str)
        counts[tag_type] += 1
        if tag_type == 'FILE':
            process_file_tag(attrs, content)
        elif tag_type == 'CLASS':
            process_class_tag_ast(attrs, content, pending_changes)
        elif tag_type == 'METHOD':
            process_method_tag_ast(attrs, content, pending_changes)
        elif tag_type == 'FUNCTION':
            process_function_tag_ast(attrs, content, pending_changes)
    console.print('[green]Processing complete![/green]')
    console.print('[bold]Summary of processed tags:[/bold]')
    console.print(f'  OPERATION: {op_count}')
    for (tag, count) in counts.items():
        console.print(f'  {tag}: {count}')