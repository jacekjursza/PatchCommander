from typing import Tuple

from tree_sitter import Query

from patchcommander.core.finder.base import CodeFinder
from patchcommander.core.languages import PY_LANGUAGE


class PythonCodeFinder(CodeFinder):
    language = 'python'

    def find_function(self, code: str, function_name: str) -> Tuple[int, int]:
        root, code_bytes = self._get_tree(code)
        query_str = """
        (
            function_definition
            name: (identifier) @func_name
        )
        """
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for node, cap_name in captures:
            if cap_name == 'func_name' and self._get_node_text(node, code_bytes) == function_name:
                func_node = node
                while func_node is not None and func_node.type != 'function_definition':
                    func_node = func_node.parent
                if func_node is not None:
                    return (func_node.start_point[0] + 1, func_node.end_point[0] + 1)
        return (0, 0)

    def find_class(self, code: str, class_name: str) -> Tuple[int, int]:
        root, code_bytes = self._get_tree(code)
        query_str = """
        (
            class_definition
            name: (identifier) @class_name
        )
        """
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for node, cap_name in captures:
            if cap_name == 'class_name' and self._get_node_text(node, code_bytes) == class_name:
                class_node = node
                while class_node is not None and class_node.type != 'class_definition':
                    class_node = class_node.parent
                if class_node is not None:
                    return (class_node.start_point[0] + 1, class_node.end_point[0] + 1)
        return (0, 0)

    def find_method(self, code: str, class_name: str, method_name: str) -> Tuple[int, int]:
        root, code_bytes = self._get_tree(code)
        query_str = """
        (
            function_definition
            name: (identifier) @method_name
        )
        """
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for node, cap_name in captures:
            if cap_name == 'method_name' and self._get_node_text(node, code_bytes) == method_name:
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_definition':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    curr = curr.parent
                if inside:
                    method_node = node
                    while method_node is not None and method_node.type != 'function_definition':
                        method_node = method_node.parent
                    if method_node:
                        return (method_node.start_point[0] + 1, method_node.end_point[0] + 1)
        return (0, 0)

    def find_property(self, code: str, class_name: str, property_name: str) -> Tuple[int, int]:
        root, code_bytes = self._get_tree(code)
        query_str = """
        (
            assignment
            left: (identifier) @prop_name
        )
        """
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        for node, cap_name in captures:
            if cap_name == 'prop_name' and self._get_node_text(node, code_bytes) == property_name:
                curr = node
                inside = False
                while curr is not None:
                    if curr.type == 'class_definition':
                        class_name_node = curr.child_by_field_name('name')
                        if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                            inside = True
                        break
                    elif curr.type == 'function_definition':
                        break
                    curr = curr.parent
                if inside:
                    assign_node = node
                    while assign_node is not None and assign_node.type != 'assignment':
                        assign_node = assign_node.parent
                    if assign_node is not None:
                        return (assign_node.start_point[0] + 1, assign_node.end_point[0] + 1)
        return (0, 0)

    def find_imports_section(self, code: str) -> Tuple[int, int]:
        root, code_bytes = self._get_tree(code)
        query_str = """
        (import_statement) @import
        (import_from_statement) @import
        """
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        nodes = [node for node, _ in captures]
        if not nodes:
            return (0, 0)
        nodes.sort(key=lambda node: node.start_point[0])
        return (nodes[0].start_point[0] + 1, nodes[-1].end_point[0] + 1)

    def find_properties_section(self, code: str, class_name: str) -> Tuple[int, int]:
        root, code_bytes = self._get_tree(code)
        query_str = """
        (assignment
           left: (identifier) @prop
        )
        """
        query = Query(PY_LANGUAGE, query_str)
        raw_captures = query.captures(root, lambda n: code_bytes[n.start_byte:n.end_byte].decode('utf8'))
        captures = self._process_captures(raw_captures)
        property_nodes = []
        for node, _ in captures:
            curr = node
            inside_class = False
            while curr is not None:
                if curr.type == 'class_definition':
                    class_name_node = curr.child_by_field_name('name')
                    if class_name_node and self._get_node_text(class_name_node, code_bytes) == class_name:
                        inside_class = True
                    break
                elif curr.type == 'function_definition':
                    break
                curr = curr.parent
            if inside_class:
                property_nodes.append(node)
        if not property_nodes:
            return (0, 0)
        property_nodes.sort(key=lambda node: node.start_point[0])
        return (property_nodes[0].start_point[0] + 1, property_nodes[-1].end_point[0] + 1)
