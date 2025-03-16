import re
import ast
from typing import List, Dict, Set, Optional, Tuple
from rich.console import Console
from patchcommander.core.pipeline import PatchResult, PostProcessor
from patchcommander.core.languages import get_language_for_file, get_parser
console = Console()

class DuplicateMethodChecker(PostProcessor):

    def can_handle(self, operation):
        return False

    def process(self, result: PatchResult) -> None:
        if not result.current_content:
            return
            
        try:
            # Determine file language
            try:
                language = get_language_for_file(result.path)
            except ValueError:
                # If we can't determine the language, assume it's a plain text file
                return
                
            duplicates = self._find_duplicates(result.current_content, language)
            if duplicates:
                console.print(f'[yellow]Warning: Found duplicate method/function definitions in {result.path}:[/yellow]')
                for (item_type, name, class_name) in duplicates:
                    if class_name:
                        console.print(f'[yellow]  - Duplicate {item_type}: {class_name}.{name}[/yellow]')
                    else:
                        console.print(f'[yellow]  - Duplicate {item_type}: {name}[/yellow]')
                console.print('[yellow]You may want to review the file manually after changes are applied.[/yellow]')
        except SyntaxError:
            console.print(f"[yellow]Warning: Couldn't check for duplicates in {result.path} due to syntax errors.[/yellow]")
        except Exception as e:
            console.print(f'[yellow]Warning: Error checking for duplicates in {result.path}: {str(e)}[/yellow]')

    def _find_duplicates(self, content: str, language: str) -> List[Tuple[str, str, Optional[str]]]:
        try:
            if language == 'python':
                return self._find_duplicates_with_ast(content)
            else:
                return self._find_duplicates_with_tree_sitter(content, language)
        except Exception as e:
            console.print(f'[yellow]Warning: Error in advanced duplicate detection: {str(e)}. Falling back to regex.[/yellow]')
            return self._find_duplicates_with_regex(content, language)

    def _find_duplicates_with_ast(self, content: str) -> List[Tuple[str, str, Optional[str]]]:
        tree = ast.parse(content)
        functions: Dict[str, int] = {}
        methods: Dict[str, Dict[str, int]] = {}
        duplicates = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                is_method = False
                class_name = None
                for parent in ast.iter_fields(tree):
                    if isinstance(parent[1], list):
                        for item in parent[1]:
                            if isinstance(item, ast.ClassDef) and node in ast.walk(item):
                                is_method = True
                                class_name = item.name
                                break
                        if is_method:
                            break
                if is_method and class_name:
                    if class_name not in methods:
                        methods[class_name] = {}
                    method_name = node.name
                    if method_name in methods[class_name]:
                        methods[class_name][method_name] += 1
                        if methods[class_name][method_name] == 2:
                            duplicates.append(('method', method_name, class_name))
                    else:
                        methods[class_name][method_name] = 1
                else:
                    func_name = node.name
                    if func_name in functions:
                        functions[func_name] += 1
                        if functions[func_name] == 2:
                            duplicates.append(('function', func_name, None))
                    else:
                        functions[func_name] = 1
        return duplicates
        
    def _find_duplicates_with_tree_sitter(self, content: str, language: str) -> List[Tuple[str, str, Optional[str]]]:
        """Find duplicates using tree-sitter for non-Python languages"""
        parser = get_parser(language)
        code_bytes = content.encode('utf8')
        tree = parser.parse(code_bytes)
        root = tree.root_node
        
        functions = {}  # name -> count
        methods = {}    # class_name -> method_name -> count
        classes = {}    # name -> node
        duplicates = []
        
        # First pass: collect all class definitions
        if language in ['javascript', 'typescript']:
            class_query = """
                (class_declaration
                  name: (identifier) @class_name) @class
            """
        else:
            # Default to a generic query
            class_query = """
                (class) @class
            """
            
        query = parser.query(class_query)
        captures = query.captures(root)
        
        for node, type_name in captures:
            if type_name == 'class_name':
                class_name = str(code_bytes[node.start_byte:node.end_byte], 'utf8')
                parent_node = node.parent
                classes[class_name] = parent_node
                
        # Second pass: collect all function definitions
        if language in ['javascript', 'typescript']:
            function_query = """
                (function_declaration
                  name: (identifier) @func_name) @function
                  
                (method_definition
                  name: (property_identifier) @method_name) @method
                  
                (arrow_function) @arrow_func
            """
        else:
            # Default to a generic query
            function_query = """
                (function) @function
            """
            
        query = parser.query(function_query)
        captures = query.captures(root)
        
        for node, type_name in captures:
            if type_name == 'func_name':
                func_name = str(code_bytes[node.start_byte:node.end_byte], 'utf8')
                
                # Check if this function is inside a class
                is_method = False
                class_name = None
                
                for cls_name, cls_node in classes.items():
                    # Check if function node is a descendant of class node
                    parent = node.parent
                    while parent:
                        if parent == cls_node:
                            is_method = True
                            class_name = cls_name
                            break
                        parent = parent.parent
                    if is_method:
                        break
                
                if is_method and class_name:
                    if class_name not in methods:
                        methods[class_name] = {}
                    if func_name in methods[class_name]:
                        methods[class_name][func_name] += 1
                        if methods[class_name][func_name] == 2:
                            duplicates.append(('method', func_name, class_name))
                    else:
                        methods[class_name][func_name] = 1
                else:
                    if func_name in functions:
                        functions[func_name] += 1
                        if functions[func_name] == 2:
                            duplicates.append(('function', func_name, None))
                    else:
                        functions[func_name] = 1
                        
            elif type_name == 'method_name':
                method_name = str(code_bytes[node.start_byte:node.end_byte], 'utf8')
                
                # Find which class this method belongs to
                class_name = None
                parent = node.parent
                while parent:
                    for cls_name, cls_node in classes.items():
                        if parent == cls_node:
                            class_name = cls_name
                            break
                    if class_name:
                        break
                    parent = parent.parent
                
                if class_name:
                    if class_name not in methods:
                        methods[class_name] = {}
                    if method_name in methods[class_name]:
                        methods[class_name][method_name] += 1
                        if methods[class_name][method_name] == 2:
                            duplicates.append(('method', method_name, class_name))
                    else:
                        methods[class_name][method_name] = 1
                        
        return duplicates

    def _find_duplicates_with_regex(self, content: str, language: str) -> List[Tuple[str, str, Optional[str]]]:
        """Fallback method using regex for any language"""
        duplicates = []
        
        if language in ['javascript', 'typescript']:
            # For JS/TS
            class_pattern = r'class\s+(\w+)'
            func_patterns = [
                r'function\s+(\w+)\s*\(',  # Regular functions
                r'(\w+)\s*=\s*function\s*\(',  # Function expressions
                r'(\w+)\s*:\s*function\s*\(',  # Object method
                r'(\w+)\s*\([^)]*\)\s*{',  # Method definition
                r'(\w+)\s*=\s*\([^)]*\)\s*=>'  # Arrow functions
            ]
        else:
            # Default to Python-like pattern
            class_pattern = r'class\s+(\w+)'
            func_patterns = [r'(async\s+)?def\s+(\w+)\s*\(']
        
        # Find all class definitions
        class_matches = re.finditer(class_pattern, content)
        class_positions = {}
        for match in class_matches:
            class_name = match.group(1)
            class_start = match.start()
            class_positions[class_name] = class_start
        
        # Find all function definitions
        functions = {}  # func_name -> count
        methods = {}    # class_name -> method_name -> count
        
        for pattern in func_patterns:
            func_matches = list(re.finditer(pattern, content))
            for match in func_matches:
                if language in ['javascript', 'typescript']:
                    func_name = match.group(1)
                else:
                    # Python pattern might have async group
                    func_name = match.group(2) if len(match.groups()) > 1 else match.group(1)
                
                func_pos = match.start()
                
                # Check if this function is inside a class
                class_name = None
                for cname, cpos in class_positions.items():
                    if cpos < func_pos:
                        # Simple heuristic: if there are no other class declarations between
                        # this class and function, assume the function is a method of this class
                        if content[cpos:func_pos].count('class ') == content[cpos:func_pos].count(f'class {cname}'):
                            class_name = cname
                            break
                
                if class_name:
                    # This is a method
                    if class_name not in methods:
                        methods[class_name] = {}
                    if func_name in methods[class_name]:
                        methods[class_name][func_name] += 1
                        if methods[class_name][func_name] == 2:
                            duplicates.append(('method', func_name, class_name))
                    else:
                        methods[class_name][func_name] = 1
                else:
                    # This is a standalone function
                    if func_name in functions:
                        functions[func_name] += 1
                        if functions[func_name] == 2:
                            duplicates.append(('function', func_name, None))
                    else:
                        functions[func_name] = 1
        
        return duplicates