from typing import List, Optional
from patchcommander.core.interfaces import LanguageParser
from patchcommander.core.languages import get_parser
from patchcommander.core.nodes import TreeSitterNode
from patchcommander.core.trees import TreeSitterCodeTree

class PythonCodeTree(TreeSitterCodeTree):
    """Python-specific implementation of CodeTree."""

    def find_classes(self) -> List[TreeSitterNode]:
        """
        Find all class definitions in the code.

        Returns:
            List of nodes representing class definitions
        """
        return self.find_nodes('(class_definition) @class', 'python')

    def find_functions(self) -> List[TreeSitterNode]:
        """
        Find all function definitions in the code.

        Returns:
            List of nodes representing function definitions
        """
        return self.find_nodes('(function_definition) @function', 'python')

    def find_methods(self, class_node: TreeSitterNode) -> List[TreeSitterNode]:
        """
        Find all methods in a class.

        Args:
            class_node: Node representing a class

        Returns:
            List of nodes representing methods
        """
        methods = []
        for child in class_node.get_children():
            if child.get_type() == 'block':
                for inner_child in child.get_children():
                    # Check for both standard and async function definitions
                    if 'function' in inner_child.get_type():
                        methods.append(inner_child)
        return methods

    def add_method_to_class(self, class_node: TreeSitterNode, method_code: str) -> 'PythonCodeTree':
        """
        Add a new method to a class.

        Args:
            class_node: Node representing a class
            method_code: Code for the new method

        Returns:
            New tree with added method

        Raises:
            ValueError: If class body cannot be found
        """
        method_code = method_code.strip('\n')
        body_node = None
        for child in class_node.get_children():
            if child.get_type() == 'block':
                body_node = child
                break
        if not body_node:
            raise ValueError('Cannot find class body')
        methods = self.find_methods(class_node)
        if methods:
            last_method = methods[-1]
            end_byte = last_method.ts_node.end_byte
            indentation = self._get_indentation(last_method.ts_node.start_byte)
            new_code_lines = method_code.splitlines()
            indented_code = '\n\n' + '\n'.join((indentation + line for line in new_code_lines))
            new_code_bytes = self.original_code[:end_byte] + indented_code + self.original_code[end_byte:]
        else:
            return super().add_code_to_body(body_node, method_code)
        parser = get_parser(self.language_code)
        new_tree = parser.parse(bytes(new_code_bytes, 'utf8'))
        return self.__class__(new_tree, new_code_bytes, self.language_code)

    def replace_method_in_class(
        self,
        class_node: TreeSitterNode,
        method_node: TreeSitterNode,
        new_method_code: str,
    ) -> "PythonCodeTree":
        """
        Replace a method in a class with new code, preserving position and indentation.

        Args:
            class_node: Node representing a class
            method_node: Node representing the method to replace
            new_method_code: Code for the new method

        Returns:
            New tree with replaced method
        """
        new_method_code = new_method_code.strip("\n")

        # Get the base indentation for the method
        base_indentation = self._get_indentation(method_node.ts_node.start_byte)

        # Normalize the new method code
        lines = new_method_code.split("\n")

        # Determine indentation of the first line
        first_line_indent = ""
        if lines and lines[0]:
            first_line = lines[0]
            first_line_indent = first_line[: len(first_line) - len(first_line.lstrip())]

        indented_lines = []
        for i, line in enumerate(lines):
            if not line.strip():
                # Empty lines remain unchanged
                indented_lines.append("")
                continue

            # Remove indentation from the original line
            stripped_line = line
            if i == 0 or line.startswith(first_line_indent):
                stripped_line = line[len(first_line_indent) :]

            # Add appropriate indentation
            if i == 0:
                # First line gets the base indentation
                indented_lines.append(base_indentation + stripped_line)
            else:
                # Remaining lines get additional indentation for method body
                # Ensure we use exactly 4 spaces for indentation
                indented_lines.append(base_indentation + "    " + stripped_line)

        indented_method_code = "\n".join(indented_lines)

        # Replace old method with new one
        start_byte = method_node.ts_node.start_byte
        end_byte = method_node.ts_node.end_byte
        new_code = (
            self.original_code[:start_byte]
            + indented_method_code
            + self.original_code[end_byte:]
        )

        # Process the new code
        parser = get_parser(self.language_code)
        new_tree = parser.parse(bytes(new_code, "utf8"))
        return self.__class__(new_tree, new_code, self.language_code)

    def find_method_by_name(self, class_node: TreeSitterNode, method_name: str) -> Optional[TreeSitterNode]:
        """
        Find a method by name in a class.

        Args:
            class_node: Node representing a class
            method_name: Name of the method to find

        Returns:
            Node representing the method or None if not found
        """
        methods = self.find_methods(class_node)
        for method in methods:
            for child in method.get_children():
                if child.get_type() == 'identifier':
                    if child.get_text() == method_name:
                        return method
        return None

class PythonParser(LanguageParser):
    """Python language parser using tree-sitter."""

    def parse(self, code: str) -> PythonCodeTree:
        """
        Parse source code into a syntax tree.

        Args:
            code: Python source code

        Returns:
            Syntax tree representing the code
        """
        parser = get_parser('python')
        tree = parser.parse(bytes(code, 'utf8'))
        return PythonCodeTree(tree, code, 'python')

    def generate(self, tree: PythonCodeTree) -> str:
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
            True if file has .py extension, False otherwise
        """
        return file_path.endswith('.py')