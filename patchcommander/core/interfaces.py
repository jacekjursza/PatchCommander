"""
Core interfaces for the PatchCommander system.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

class Node(ABC):
    """Abstract node in a syntax tree."""

    @abstractmethod
    def get_text(self) -> str:
        """Get the original text of the node."""
        pass

    @abstractmethod
    def get_type(self) -> str:
        """Get the syntactic type of the node."""
        pass

    @abstractmethod
    def get_children(self) -> List['Node']:
        """Get the list of child nodes."""
        pass

class CodeTree(ABC):
    """Abstract representation of a code syntax tree."""

    @abstractmethod
    def find_nodes(self, query: str, language_code: Optional[str]=None) -> List[Node]:
        """
        Find nodes matching the query.

        Args:
            query: Query in the syntax appropriate for the parser
            language_code: Optional language code

        Returns:
            List of found nodes
        """
        pass

    @abstractmethod
    def diff(self, other: 'CodeTree') -> 'TreeDiff':
        """
        Compare with another tree and return differences.

        Args:
            other: Another tree to compare with

        Returns:
            TreeDiff object containing differences
        """
        pass

class TreeDiff:
    """Representation of differences between two trees."""

    def __init__(self):
        """Initialize an empty diff."""
        self.additions = []
        self.deletions = []
        self.modifications = []

    def is_empty(self) -> bool:
        """
        Check if there are no differences.

        Returns:
            True if there are no differences, False otherwise
        """
        return not (self.additions or self.deletions or self.modifications)

class LanguageParser(ABC):
    """Interface for a programming language parser."""

    @abstractmethod
    def parse(self, code: str) -> CodeTree:
        """
        Parse source code into a syntax tree.

        Args:
            code: Source code

        Returns:
            Syntax tree representing the code
        """
        pass

    @abstractmethod
    def generate(self, tree: CodeTree) -> str:
        """
        Generate source code from a syntax tree.

        Args:
            tree: Syntax tree

        Returns:
            Generated source code
        """
        pass

    @abstractmethod
    def is_compatible(self, file_path: str) -> bool:
        """
        Check if parser can handle the given file.

        Args:
            file_path: Path to file

        Returns:
            True if parser can handle the file, False otherwise
        """
        pass