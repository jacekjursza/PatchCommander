import os
import rich
from patchcommander.core.pipeline import PatchResult, PostProcessor
from patchcommander.core.languages import get_language_for_file, get_parser

class SyntaxValidator(PostProcessor):

    def can_handle(self, operation):
        return False

    def process(self, result: PatchResult) -> None:
        if not result.current_content:
            return
        
        try:
            file_ext = os.path.splitext(result.path)[1].lower()
            # Skip files without extensions
            if not file_ext:
                return
                
            # Get the appropriate language for the file extension
            try:
                language = get_language_for_file(result.path)
            except ValueError:
                # If we can't determine the language, skip validation
                return
                
            if language == 'python':
                self._validate_python_syntax(result)
            else:
                # For other languages, use tree-sitter parsing as validation
                self._validate_tree_sitter_syntax(result, language)
        except Exception as e:
            error_message = f'Syntax validation error in {result.path}: {str(e)}'
            result.add_error(error_message)

    def _validate_python_syntax(self, result: PatchResult) -> None:
        try:
            compile(result.current_content, result.path, 'exec')
        except SyntaxError as e:
            error_message = f'Python syntax error in {result.path} line {e.lineno}, position {e.offset}: {e.msg}'
            result.add_error(error_message)

    def _validate_tree_sitter_syntax(self, result: PatchResult, language: str) -> None:
        try:
            # Get the appropriate parser for the language
            parser = get_parser(language)
            
            # Parse the content
            code_bytes = result.current_content.encode('utf8')
            tree = parser.parse(code_bytes)
            
            # Check for syntax errors by examining the tree structure
            # This is a basic check - if parsing succeeds, we assume syntax is valid
            root_node = tree.root_node
            
            # Look for ERROR nodes, which indicate syntax issues
            error_nodes = []
            
            def collect_error_nodes(node):
                if node.type == 'ERROR':
                    error_nodes.append(node)
                for child in node.children:
                    collect_error_nodes(child)
            
            collect_error_nodes(root_node)
            
            if error_nodes:
                lines = result.current_content.splitlines()
                for error_node in error_nodes:
                    line_num = error_node.start_point[0] + 1
                    col_num = error_node.start_point[1] + 1
                    context = lines[error_node.start_point[0]] if 0 <= error_node.start_point[0] < len(lines) else ""
                    error_message = f'{language.capitalize()} syntax error in {result.path} line {line_num}, column {col_num}: {context}'
                    result.add_error(error_message)
                    
        except Exception as e:
            error_message = f'{language.capitalize()} syntax validation error in {result.path}: {str(e)}'
            result.add_error(error_message)