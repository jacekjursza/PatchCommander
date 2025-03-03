"""
Node implementations for syntax trees.
"""
from typing import List
from tree_sitter import Node as TSNode
from patchcommander.core.interfaces import Node

class TreeSitterNode(Node):
    """Implementation of Node using tree-sitter."""

    def __init__(self, ts_node: TSNode, code: str):
        """
        Initialize a TreeSitterNode.

        Args:
            ts_node: Tree-sitter node
            code: Original source code
        """
        self.ts_node = ts_node
        self.code = code

    def get_text(self) -> str:
        """
        Get the original text of the node.

        Returns:
            Original text
        """
        start_byte = self.ts_node.start_byte
        end_byte = self.ts_node.end_byte
        return self.code[start_byte:end_byte]

    def get_type(self) -> str:
        """
        Get the syntactic type of the node.

        Returns:
            Node type
        """
        return self.ts_node.type

    def get_children(self) -> List[Node]:
        """
        Get the list of child nodes.

        Returns:
            List of child nodes
        """
        return [TreeSitterNode(child, self.code) for child in self.ts_node.children]

    def __str__(self) -> str:
        """String representation of the node."""
        return f"{self.get_type()}: {self.get_text()[:50]}..."

    def __repr__(self) -> str:
        """Detailed representation of the node."""
        return f"TreeSitterNode({self.get_type()}, {self.ts_node.start_point}-{self.ts_node.end_point})"