"""
Post-processor for checking duplicate methods and functions.
"""
import re
import ast
from typing import List, Dict, Set, Optional, Tuple
from rich.console import Console
from patchcommander.core.pipeline import PatchResult, PostProcessor

console = Console()

class DuplicateMethodChecker(PostProcessor):
    """
    Post-processor that checks for duplicate method and function definitions in Python files.
    Only displays warnings without modifying content.
    """

    def can_handle(self, operation):
        """
        This post-processor works at the PatchResult level, so this method is not used.
        """
        return False

    def process(self, result: PatchResult) -> None:
        """
        Checks for duplicate methods and functions in Python files.

        Args:
            result: Result to check
        """
        if not result.current_content or not result.path.endswith('.py'):
            return

        try:
            duplicates = self._find_duplicates(result.current_content)
            if duplicates:
                console.print(f"[yellow]Warning: Found duplicate method/function definitions in {result.path}:[/yellow]")
                for item_type, name, class_name in duplicates:
                    if class_name:
                        console.print(f"[yellow]  - Duplicate {item_type}: {class_name}.{name}[/yellow]")
                    else:
                        console.print(f"[yellow]  - Duplicate {item_type}: {name}[/yellow]")
                console.print("[yellow]You may want to review the file manually after changes are applied.[/yellow]")
        except SyntaxError:
            # If there's a syntax error, we can't parse the file
            console.print(f"[yellow]Warning: Couldn't check for duplicates in {result.path} due to syntax errors.[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Warning: Error checking for duplicates in {result.path}: {str(e)}[/yellow]")

    def _find_duplicates(self, content: str) -> List[Tuple[str, str, Optional[str]]]:
        """
        Finds duplicate method and function definitions in the content.
        
        Args:
            content: Python code content
            
        Returns:
            List of tuples (item_type, name, class_name) for duplicate definitions
        """
        try:
            # Try to use AST parser first for more accurate results
            return self._find_duplicates_with_ast(content)
        except SyntaxError:
            # Fall back to regex-based approach if there are syntax errors
            return self._find_duplicates_with_regex(content)

    def _find_duplicates_with_ast(self, content: str) -> List[Tuple[str, str, Optional[str]]]:
        """
        Uses AST parser to find duplicate definitions.
        
        Args:
            content: Python code content
            
        Returns:
            List of tuples (item_type, name, class_name) for duplicate definitions
        """
        tree = ast.parse(content)
        functions: Dict[str, int] = {}  # name -> count
        methods: Dict[str, Dict[str, int]] = {}  # class_name -> {method_name -> count}
        duplicates = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Check if this is a method or a function
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
                        if methods[class_name][method_name] == 2:  # Only add it once to duplicates
                            duplicates.append(("method", method_name, class_name))
                    else:
                        methods[class_name][method_name] = 1
                else:
                    # It's a function
                    func_name = node.name
                    if func_name in functions:
                        functions[func_name] += 1
                        if functions[func_name] == 2:  # Only add it once to duplicates
                            duplicates.append(("function", func_name, None))
                    else:
                        functions[func_name] = 1
                        
        return duplicates

    def _find_duplicates_with_regex(self, content: str) -> List[Tuple[str, str, Optional[str]]]:
        """
        Uses regex to find duplicate definitions (fallback method).
        
        Args:
            content: Python code content
            
        Returns:
            List of tuples (item_type, name, class_name) for duplicate definitions
        """
        duplicates = []
        
        # First find all classes
        class_pattern = r'class\s+(\w+)'
        class_matches = re.finditer(class_pattern, content)
        class_positions = {}
        
        for match in class_matches:
            class_name = match.group(1)
            class_start = match.start()
            class_positions[class_name] = class_start
        
        # Find all function definitions
        func_pattern = r'(async\s+)?def\s+(\w+)\s*\('
        func_matches = list(re.finditer(func_pattern, content))
        
        # Track functions by name
        functions = {}
        # Track methods by class and name
        methods = {}
        
        for match in func_matches:
            func_name = match.group(2)
            func_pos = match.start()
            
            # Determine if this is a method in a class
            class_name = None
            for cname, cpos in class_positions.items():
                if cpos < func_pos:
                    # Check if we're still in this class's scope
                    # This is a simplification and might not be accurate for complex files
                    if content[cpos:func_pos].count('class ') == content[cpos:func_pos].count(f'class {cname}'):
                        class_name = cname
                        break
            
            if class_name:
                # It's a method
                if class_name not in methods:
                    methods[class_name] = {}
                
                if func_name in methods[class_name]:
                    methods[class_name][func_name] += 1
                    if methods[class_name][func_name] == 2:  # Only add it once to duplicates
                        duplicates.append(("method", func_name, class_name))
                else:
                    methods[class_name][func_name] = 1
            else:
                # It's a function
                if func_name in functions:
                    functions[func_name] += 1
                    if functions[func_name] == 2:  # Only add it once to duplicates
                        duplicates.append(("function", func_name, None))
                else:
                    functions[func_name] = 1
        
        return duplicates