import ast
import os
import textwrap
import re
from rich.console import Console
from config import config
from confirmations import confirm_and_apply_change, confirm_simple_action
from utils import parse_attributes, sanitize_path
from apply_changes import pending_changes
console = Console()
OPERATIONS = {'move_file': ['source', 'target'], 'delete_file': ['source'], 'delete_method': ['source', 'class', 'method']}
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
        if any((c in invalid_chars for c in file_path)):
            console.print(f'[yellow]Warning: Path contains potentially invalid characters for Windows: {invalid_chars}[/yellow]')
            return True
    else:
        invalid_chars = '<>'
        if any((c in invalid_chars for c in file_path)):
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
    invalid_chars = '<>:"|?*' if os.name == 'nt' else '<>'
    tag_pattern = re.compile('<(FILE|CLASS|METHOD|FUNCTION|OPERATION)(\\s+[^>]*)?\\s*(?:>(.*?)</\\1\\s*>|/>)', re.DOTALL)
    problematic_paths = []
    for match in tag_pattern.finditer(input_data):
        tag_type = match.group(1)
        attr_str = match.group(2) or ''
        attrs = parse_attributes(attr_str)
        paths = []
        if 'path' in attrs:
            paths.append(('path', attrs['path']))
        if 'source' in attrs:
            paths.append(('source', attrs['source']))
        if 'target' in attrs:
            paths.append(('target', attrs['target']))
        for (attr_name, path) in paths:
            if not path:
                continue
            has_invalid_chars = any((c in path for c in invalid_chars))
            if has_invalid_chars:
                problematic_paths.append((tag_type, attr_name, path))
    if problematic_paths:
        console.print('[bold red]Found problematic paths:[/bold red]')
        for (tag_type, attr_name, path) in problematic_paths:
            sanitized = sanitize_path(path)
            console.print(f'  [yellow]<{tag_type}>[/yellow] {attr_name}="{path}" → {attr_name}="{sanitized}"')
    else:
        console.print('[green]No problematic paths found.[/green]')


def process_class_tag(attrs, content, pending_changes):
    """
    Process a CLASS tag by updating or adding a class to a file with preserved formatting.

    Args:
        attrs (dict): Attributes from the CLASS tag
        content (str): New content for the class
        pending_changes (list): List to collect pending changes
    """
    try:
        import parso
        import astunparse
    except ImportError:
        console.print('[bold red]Missing required packages. Install with: pip install parso astunparse[/bold red]')
        return
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
    if content.strip().startswith('class '):
        new_class_content = content
    else:
        new_class_content = f"class {class_name}:\n{textwrap.indent(content, '    ')}"
    if not original_code:
        if confirm_simple_action(f"File '{file_path}' not found. Create new file?"):
            update_in_memory_file(file_path, new_class_content)
            confirm_and_apply_change(file_path, new_class_content, f"Create new class '{class_name}'", pending_changes)
        else:
            console.print(f"[yellow]Skipping CLASS tag for '{class_name}'.[/yellow]")
        return
    try:
        code_changed = False
        try:
            import ast
            original_tree = ast.parse(original_code)
            existing_class = None
            for node in original_tree.body:
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    existing_class = node
                    break
            if existing_class:
                new_tree = ast.parse(new_class_content)
                new_class = None
                for node in new_tree.body:
                    if isinstance(node, ast.ClassDef):
                        new_class = node
                        break
                if new_class:
                    old_ast_str = astunparse.unparse(existing_class).strip()
                    new_ast_str = astunparse.unparse(new_class).strip()
                    if old_ast_str == new_ast_str:
                        console.print(f"[green]No code changes detected for class '{class_name}'. Skipping update.[/green]")
                        return
                    code_changed = True
        except Exception as e:
            if config.get('debug_mode'):
                console.print(f'[yellow]Warning: Failed to compare ASTs: {e}. Assuming code changed.[/yellow]')
            code_changed = True
        grammar = parso.grammar.load_grammar()
        module = grammar.parse(original_code)
        class_found = False
        class_node = None
        for child in module.children:
            if child.type == 'classdef':
                for subchild in child.children:
                    if subchild.type == 'name' and subchild.value == class_name:
                        class_found = True
                        class_node = child
                        break
                if class_found:
                    break
        if class_found:
            start_line = class_node.start_pos[0] - 1
            end_line = start_line

            def find_max_line(node):
                nonlocal end_line
                if hasattr(node, 'end_pos'):
                    end_line = max(end_line, node.end_pos[0] - 1)
                if hasattr(node, 'children'):
                    for child in node.children:
                        find_max_line(child)
            find_max_line(class_node)
            class_indent = len(original_code.splitlines()[start_line]) - len(original_code.splitlines()[start_line].lstrip())
            lines = original_code.splitlines()
            i = end_line + 1
            while i < len(lines):
                line = lines[i]
                if line.strip() and len(line) - len(line.lstrip()) <= class_indent:
                    break
                i += 1
                end_line = i - 1
            new_class_lines = new_class_content.splitlines()
            leading_whitespace = ''
            if start_line > 0 and lines[start_line - 1].strip() == '':
                new_lines = lines.copy()
                new_lines[start_line:end_line + 1] = new_class_lines
            else:
                new_lines = lines.copy()
                new_lines[start_line:end_line + 1] = new_class_lines
            new_code = '\n'.join(new_lines)
            if new_code.strip() == original_code.strip() and (not code_changed):
                console.print(f"[green]No significant changes detected for class '{class_name}'. Skipping update.[/green]")
                return
            update_in_memory_file(file_path, new_code)
            confirm_and_apply_change(file_path, new_code, f"Update class '{class_name}'", pending_changes)
        else:
            trailing_newlines = len(original_code) - len(original_code.rstrip('\n'))
            if not original_code.strip():
                new_code = new_class_content
            elif trailing_newlines >= 2:
                new_code = original_code.rstrip('\n') + '\n\n' + new_class_content
            elif trailing_newlines == 1:
                new_code = original_code + '\n' + new_class_content
            else:
                new_code = original_code + '\n\n' + new_class_content
            update_in_memory_file(file_path, new_code)
            confirm_and_apply_change(file_path, new_code, f"Add class '{class_name}'", pending_changes)
    except Exception as e:
        console.print(f'[bold red]Error processing class tag: {e}[/bold red]')
        if config.get('debug_mode'):
            import traceback
            console.print(traceback.format_exc())

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
        import parso
        grammar = parso.grammar.load_grammar()
        module = grammar.parse(original_code)
        func_found = False
        func_node = None
        for child in module.children:
            if child.type == 'funcdef':
                for name_child in child.children:
                    if name_child.type == 'name' and name_child.value == new_function_name:
                        func_found = True
                        func_node = child
                        break
                if func_found:
                    break
        lines = original_code.splitlines()
        if func_found:
            start_line = func_node.start_pos[0] - 1
            end_line = func_node.end_pos[0] - 1
            func_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
            indented_content = textwrap.indent(textwrap.dedent(content), ' ' * func_indent)
            new_lines = lines.copy()
            new_lines[start_line:end_line + 1] = indented_content.splitlines()
            new_code = '\n'.join(new_lines)
            update_in_memory_file(file_path, new_code)
            confirm_and_apply_change(file_path, new_code, f"Update function '{new_function_name}'", pending_changes)
        else:
            if original_code:
                trailing_newlines = len(original_code) - len(original_code.rstrip('\n'))
                if trailing_newlines == 0:
                    new_code = original_code + '\n\n' + content
                elif trailing_newlines == 1:
                    new_code = original_code + '\n' + content
                else:
                    new_code = original_code + content
            else:
                new_code = content
            update_in_memory_file(file_path, new_code)
            confirm_and_apply_change(file_path, new_code, f"Add function '{new_function_name}'", pending_changes)
    except ImportError:
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
    except Exception as e:
        console.print(f'[bold red]Error processing function tag: {e}[/bold red]')
        if config.get('debug_mode'):
            import traceback
            console.print(traceback.format_exc())
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


def process_method_tag(attrs, content, pending_changes):
    """
    Process a METHOD tag with preserved formatting.

    Args:
        attrs (dict): Attributes from the METHOD tag
        content (str): New content for the method
        pending_changes (list): List to collect pending changes
    """
    try:
        import parso
        import ast
        import astunparse
    except ImportError:
        console.print('[bold red]Missing required packages. Install with: pip install parso astunparse[/bold red]')
        return
    file_path = attrs.get('path')
    class_name = attrs.get('class')
    if not file_path or not class_name:
        console.print("[bold red]METHOD tag missing 'path' or 'class' attribute.[/bold red]")
        return
    try:
        method_module = ast.parse(textwrap.dedent(content))
        new_method = extract_method_from_ast(method_module)
        if new_method is None:
            console.print('[bold red]No function definition found in METHOD tag content.[/bold red]')
            return
        new_method_name = new_method.name
    except Exception as e:
        console.print(f'[bold red]Failed to parse new method content: {e}[/bold red]')
        return
    original_code = get_file_content(file_path)
    if not original_code:
        new_class_node = ast.ClassDef(name=class_name, bases=[], keywords=[], body=[new_method], decorator_list=[])
        new_module = ast.Module(body=[new_class_node], type_ignores=[])
        try:
            new_code = astunparse.unparse(new_module)
        except Exception:
            new_code = ast.unparse(new_module)
        if confirm_simple_action(f"File '{file_path}' not found. Create new file with class '{class_name}' containing method '{new_method_name}'?"):
            update_in_memory_file(file_path, new_code)
            confirm_and_apply_change(file_path, new_code, f"Create new class '{class_name}' with method '{new_method_name}'", pending_changes)
        else:
            console.print(f"[yellow]Skipping METHOD tag for '{new_method_name}'.[/yellow]")
        return
    try:
        code_changed = False
        try:
            original_tree = ast.parse(original_code)
            existing_method = None
            for node in original_tree.body:
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    for subnode in node.body:
                        if isinstance(subnode, ast.FunctionDef) and subnode.name == new_method_name:
                            existing_method = subnode
                            break
                    break
            if existing_method:
                old_ast_str = astunparse.unparse(existing_method).strip()
                new_ast_str = astunparse.unparse(new_method).strip()
                if old_ast_str == new_ast_str:
                    console.print(f"[green]No code changes detected for method '{new_method_name}'. Skipping update.[/green]")
                    return
                code_changed = True
        except Exception as e:
            if config.get('debug_mode'):
                console.print(f'[yellow]Warning: Failed to compare ASTs: {e}. Assuming code changed.[/yellow]')
            code_changed = True
        grammar = parso.grammar.load_grammar()
        module = grammar.parse(original_code)
        class_found = False
        class_node = None
        for child in module.children:
            if child.type == 'classdef':
                for subchild in child.children:
                    if subchild.type == 'name' and subchild.value == class_name:
                        class_found = True
                        class_node = child
                        break
                if class_found:
                    break
        if not class_found:
            console.print(f"[bold red]Class '{class_name}' not found in {file_path}.[/bold red]")
            if confirm_simple_action(f"Create class '{class_name}' in file '{file_path}'?"):
                new_class_node = ast.ClassDef(name=class_name, bases=[], keywords=[], body=[new_method], decorator_list=[])
                original_tree = ast.parse(original_code)
                original_tree.body.append(new_class_node)
                try:
                    new_code = astunparse.unparse(original_tree)
                except Exception:
                    new_code = ast.unparse(original_tree)
                update_in_memory_file(file_path, new_code)
                confirm_and_apply_change(file_path, new_code, f"Add class '{class_name}' with method '{new_method_name}'", pending_changes)
            return
        method_found = False
        method_node = None

        def find_method(node):
            nonlocal method_found, method_node
            if node.type == 'funcdef':
                for child in node.children:
                    if child.type == 'name' and child.value == new_method_name:
                        method_found = True
                        method_node = node
                        return True
            return False
        for child in class_node.children:
            if child.type == 'suite':
                for statement in child.children:
                    if hasattr(statement, 'children'):
                        for func_candidate in statement.children:
                            if find_method(func_candidate):
                                break
        lines = original_code.splitlines()
        if method_found:
            start_line = method_node.start_pos[0] - 1
            end_line = method_node.end_pos[0] - 1
            method_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
            indented_content = textwrap.indent(textwrap.dedent(content), ' ' * method_indent)
            new_lines = lines.copy()
            new_lines[start_line:end_line + 1] = indented_content.splitlines()
            new_code = '\n'.join(new_lines)
            if new_code.strip() == original_code.strip() and (not code_changed):
                console.print(f"[green]No significant changes detected for method '{new_method_name}'. Skipping update.[/green]")
                return
            update_in_memory_file(file_path, new_code)
            confirm_and_apply_change(file_path, new_code, f"Update method '{new_method_name}' in class '{class_name}'", pending_changes)
        else:
            class_start_line = class_node.start_pos[0] - 1
            class_indent = len(lines[class_start_line]) - len(lines[class_start_line].lstrip())
            method_indent = class_indent + 4
            last_method_line = class_start_line
            for child in class_node.children:
                if child.type == 'suite':
                    for statement in child.children:
                        if hasattr(statement, 'end_pos'):
                            last_method_line = max(last_method_line, statement.end_pos[0] - 1)
            indented_content = textwrap.indent(textwrap.dedent(content), ' ' * method_indent)
            new_lines = lines.copy()
            if last_method_line < len(new_lines) and new_lines[last_method_line].strip() and (not (last_method_line + 1 < len(new_lines) and (not new_lines[last_method_line + 1].strip()))):
                new_lines.insert(last_method_line + 1, '')
                last_method_line += 1
            new_lines.insert(last_method_line + 1, indented_content)
            new_code = '\n'.join(new_lines)
            update_in_memory_file(file_path, new_code)
            confirm_and_apply_change(file_path, new_code, f"Add method '{new_method_name}' to class '{class_name}'", pending_changes)
    except Exception as e:
        console.print(f'[bold red]Error processing method tag: {e}[/bold red]')
        if config.get('debug_mode'):
            import traceback
            console.print(traceback.format_exc())
def run_process(input_data):
    """
    Process input data containing tags and apply changes to files.

    Args:
        input_data (str): The input data containing tags
    """
    console.print('[bold]Starting processing of tags...[/bold]')
    in_memory_files.clear()
    try:
        import parso
        import astunparse
    except ImportError:
        console.print('[bold red]Required packages not found. Please install:[/bold red]')
        console.print('[yellow]pip install parso astunparse[/yellow]')
        console.print('[yellow]Processing will continue but formatting preservation may be limited.[/yellow]')
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
            process_class_tag(attrs, content, pending_changes)
        elif tag_type == 'METHOD':
            process_method_tag(attrs, content, pending_changes)
        elif tag_type == 'FUNCTION':
            process_function_tag_ast(attrs, content, pending_changes)
    console.print('[green]Processing complete![/green]')
    console.print('[bold]Summary of processed tags:[/bold]')
    console.print(f'  OPERATION: {op_count}')
    for (tag, count) in counts.items():
        console.print(f'  {tag}: {count}')