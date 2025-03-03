"""
JavaScript language parser using tree-sitter.
"""
from typing import List, Optional
from patchcommander.core.interfaces import LanguageParser
from patchcommander.core.nodes import TreeSitterNode
from patchcommander.core.trees import TreeSitterCodeTree
from patchcommander.core.languages import get_parser

class JavaScriptCodeTree(TreeSitterCodeTree):
    """JavaScript-specific implementation of CodeTree."""

    def find_classes(self) -> List[TreeSitterNode]:
        """
        Find class definitions in JavaScript code.

        Returns:
            List of nodes representing class definitions
        """
        return self.find_nodes("(class_declaration) @class", "javascript")

    def find_functions(self) -> List[TreeSitterNode]:
        """
        Find function definitions in JavaScript code.

        Returns:
            List of nodes representing function definitions
        """
        query = """
            [
                (function_declaration) @function
                (arrow_function) @function
                (function_expression) @function
            ]
        """
        return self.find_nodes(query, "javascript")

    def find_methods(self, class_node: TreeSitterNode) -> List[TreeSitterNode]:
        """
        Find methods in a JavaScript class.

        Args:
            class_node: Node representing a class

        Returns:
            List of nodes representing methods
        """
        methods = []
        for child in class_node.get_children():
            if child.get_type() == "class_body":
                for inner_child in child.get_children():
                    if inner_child.get_type() == "method_definition":
                        methods.append(inner_child)
        return methods

    def add_method_to_class(self, class_node: TreeSitterNode, method_code: str) -> 'JavaScriptCodeTree':
        """
        Add a new method to a JavaScript class.

        Args:
            class_node: Node representing a class
            method_code: Code for the new method

        Returns:
            New tree with added method

        Raises:
            ValueError: If class body cannot be found
        """
        body_node = None
        for child in class_node.get_children():
            if child.get_type() == "class_body":
                body_node = child
                break

        if not body_node:
            raise ValueError("Cannot find class body")

        return self.add_code_to_body(body_node, method_code)

    def find_method_by_name(self, class_node: TreeSitterNode, method_name: str) -> Optional[TreeSitterNode]:
        """
        Find a method by name in a JavaScript class.

        Args:
            class_node: Node representing a class
            method_name: Name of the method to find

        Returns:
            Node representing the method or None if not found
        """
        methods = self.find_methods(class_node)

        for method in methods:
            property_name = None
            for child in method.get_children():
                if child.get_type() == "property_identifier":
                    property_name = child.get_text()
                    break

            if property_name == method_name:
                return method

        return None


class JavaScriptParser(LanguageParser):
    """JavaScript language parser."""

    def parse(self, code: str) -> JavaScriptCodeTree:
        """
        Parse source code into a syntax tree.

        Args:
            code: JavaScript source code

        Returns:
            Syntax tree representing the code
        """
        parser = get_parser("javascript")
        tree = parser.parse(bytes(code, "utf8"))
        return JavaScriptCodeTree(tree, code, "javascript")

    def generate(self, tree: JavaScriptCodeTree) -> str:
        """
        Generate source code from a syntax tree.

        Args:
            tree: Syntax tree

        Returns:
            Generated source code
        """
        return tree.original_code

    def is_compatible(self, file_path: str) -> bool:
        """
        Check if parser can handle the given file.

        Args:
            file_path: Path to file

        Returns:
            True if file has .js, .jsx, .ts or .tsx extension, False otherwise
        """
        return file_path.endswith((".js", ".jsx", ".ts", ".tsx"))