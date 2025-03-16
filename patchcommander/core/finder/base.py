# patchcommander/core/finder/base.py

from abc import ABC, abstractmethod
from typing import Tuple, Any
from tree_sitter import Node

from patchcommander.core.languages import get_parser


class CodeFinder(ABC):
    language = 'python'

    def __init__(self):
        super().__init__()
        self.parser = get_parser(self.language)

    @abstractmethod
    def find_function(self, code: str, function_name: str) -> Tuple[int, int]:
        pass

    @abstractmethod
    def find_class(self, code: str, class_name: str) -> Tuple[int, int]:
        pass

    @abstractmethod
    def find_method(self, code: str, class_name: str, method_name: str) -> Tuple[int, int]:
        pass

    @abstractmethod
    def find_property(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        pass

    @abstractmethod
    def find_imports_section(self, code: str) -> Tuple[int, int]:
        pass

    @abstractmethod
    def find_properties_section(self, code: str, class_name: str) -> Tuple[int, int]:
        pass

    def _get_tree(self, code: str) -> Tuple[Node, bytes]:
        code_bytes = code.encode('utf8')
        tree = self.parser.parse(code_bytes)
        return tree.root_node, code_bytes

    def _get_node_text(self, node: Node, code_bytes: bytes) -> str:
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')

    def _process_captures(self, captures: Any) -> list:
        result = []
        if isinstance(captures, dict):
            for cap_name, nodes in captures.items():
                for node in nodes:
                    result.append((node, cap_name))
        else:
            result = captures
        return result
