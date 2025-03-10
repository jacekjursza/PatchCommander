"""
Tree implementations for code syntax trees.
"""
from typing import List, Optional
from tree_sitter import Tree as TSTree, Query
from patchcommander.core.interfaces import CodeTree, TreeDiff, Node
from patchcommander.core.languages import get_parser
from patchcommander.core.nodes import TreeSitterNode

class TreeSitterCodeTree(CodeTree):
    """Implementation of CodeTree using tree-sitter."""

    def __init__(self, ts_tree: TSTree, code: str, language_code: str):
        """
        Initialize a TreeSitterCodeTree.

        Args:
            ts_tree: Tree-sitter tree
            code: Original source code
            language_code: Language code (e.g., 'python', 'javascript')
        """
        self.ts_tree = ts_tree
        self.original_code = code
        self.language_code = language_code

    def find_nodes(self, query_string: str, language_code: Optional[str]=None) -> List[Node]:
        """
        Find nodes matching the query.

        Args:
            query_string: Query in tree-sitter query language
            language_code: Language code (defaults to the tree's language)

        Returns:
            List of matching nodes
        """
        from .languages import get_parser
        lang_code = language_code or self.language_code
        parser = get_parser(lang_code)
        query = Query(parser.language, query_string)

        def get_node_text(node):
            return self.original_code[node.start_byte:node.end_byte]
        captures = query.captures(self.ts_tree.root_node, get_node_text)
        nodes = []
        for (capture_name, capture_nodes) in captures.items():
            for node in capture_nodes:
                nodes.append(TreeSitterNode(node, self.original_code))
        return nodes

    def diff(self, other: CodeTree) -> TreeDiff:
        """
        Compare with another tree and return differences.

        Args:
            other: Another tree to compare with

        Returns:
            TreeDiff object containing differences
        """
        diff = TreeDiff()
        if not isinstance(other, TreeSitterCodeTree):
            raise TypeError('Cannot compare with a different tree type')
        if self.original_code != other.original_code:
            diff.modifications.append((self.ts_tree.root_node, other.ts_tree.root_node))
        return diff

    def replace_node(self, node: TreeSitterNode, new_content: str) -> 'TreeSitterCodeTree':
        """
        Replace a node with new content.

        Args:
            node: Node to replace
            new_content: New content

        Returns:
            New tree with the node replaced
        """
        start_byte = node.ts_node.start_byte
        end_byte = node.ts_node.end_byte

        # Remove empty lines from the beginning and end of the content
        new_content = new_content.strip('\n')

        # Preserve the indentation of the original node
        indentation = self._get_indentation(start_byte)

        # Special handling for methods/functions in Python
        if self.language_code == 'python' and node.get_type() == 'function_definition':
            # Split content into lines and apply correct indentation
            lines = new_content.split('\n')
            if not lines:
                return self  # If there is no content, do nothing

            indented_lines = []
            # First line (with 'def') gets basic indentation
            indented_lines.append(indentation + lines[0])

            # Remaining lines get additional indentation (usually 4 more spaces)
            for line in lines[1:]:
                if line.strip():  # If the line is not empty
                    indented_lines.append(indentation + "    " + line)
                else:
                    indented_lines.append("")  # Empty lines remain empty

            new_content = '\n'.join(indented_lines)
        else:
            # Standard indentation application to all lines
            lines = new_content.split('\n')
            indented_lines = []
            for line in lines:
                if line.strip():  # If the line is not empty
                    indented_lines.append(indentation + line)
                else:
                    indented_lines.append("")  # Empty lines remain empty

            new_content = '\n'.join(indented_lines)

        new_code = self.original_code[:start_byte] + new_content + self.original_code[end_byte:]
        parser = get_parser(self.language_code)
        new_tree = parser.parse(bytes(new_code, 'utf8'))
        return self.__class__(new_tree, new_code, self.language_code)

    def add_code_to_body(self, body_node: TreeSitterNode, code_to_add: str) -> 'TreeSitterCodeTree':
        """
        Add code to a body node (e.g., class body, function body).

        Args:
            body_node: Body node to add code to
            code_to_add: Code to add

        Returns:
            New tree with code added
        """
        # Remove empty lines from the beginning and end of the content
        code_to_add = code_to_add.strip('\n')

        end_byte = body_node.ts_node.end_byte - 1
        indentation = self._get_indentation(body_node.ts_node.start_byte)
        indented_code = '\n' + '\n'.join((indentation + '    ' + line for line in code_to_add.split('\n')))
        if body_node.get_text().strip() in ['{}', ':']:
            indented_code = indented_code.lstrip()
        new_code = self.original_code[:end_byte] + indented_code + self.original_code[end_byte:]
        parser = get_parser(self.language_code)
        new_tree = parser.parse(bytes(new_code, 'utf8'))
        return self.__class__(new_tree, new_code, self.language_code)

    def _get_indentation(self, position: int) -> str:
        """
        Get the indentation at a position in the code.

        Args:
            position: Position in bytes

        Returns:
            Indentation string
        """
        line_start = position
        while line_start > 0 and self.original_code[line_start - 1] != '\n':
            line_start -= 1
        indentation = ''
        for i in range(line_start, position):
            char = self.original_code[i]
            if char in ' \t':
                indentation += char
            else:
                break
        return indentation