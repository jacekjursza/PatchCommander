"""
Python language operations.
"""
from typing import Dict, Any, Optional
import os
from patchcommander.operations.base import register_operation, Operation
from patchcommander.parsers.python_parser import PythonParser

@register_operation('add_method')
class AddMethodOperation(Operation):
    """Operation to add a method to a class."""

    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the add method operation.

        Args:
            context: Execution context containing method code

        Returns:
            True if operation was successful, False otherwise
        """
        file_path = self.attributes.get('path')
        class_name = self.attributes.get('class')
        method_code = context.get('method_code', '')
        dry_run = context.get('dry_run', False)
        if not file_path or not class_name or (not method_code):
            print(f'Error: Missing required attributes for AddMethodOperation: path={file_path}, class={class_name}, method_code={bool(method_code)}')
            return False
        try:
            if not os.path.exists(file_path):
                print(f'Error: File {file_path} does not exist')
                return False
            with open(file_path, 'r', encoding='utf-8') as file:
                code = file.read()
            parser = PythonParser()
            tree = parser.parse(code)
            classes = tree.find_classes()
            target_class = None
            for cls in classes:
                for child in cls.get_children():
                    if child.get_type() == 'identifier' and child.get_text() == class_name:
                        target_class = cls
                        break
                if target_class:
                    break
            if not target_class:
                print(f'Error: Class {class_name} not found in file {file_path}')
                return False
            method_name = self._extract_method_name(method_code)

            # Zmiana zaczynająca się tutaj
            new_tree = None
            if method_name:
                existing_method = tree.find_method_by_name(target_class, method_name)
                if existing_method:
                    print(f'Info: Method {method_name} already exists in class {class_name}. Replacing it.')
                    # Użyj replace_method_in_class zamiast replace_node i add_method_to_class
                    new_tree = tree.replace_method_in_class(target_class, existing_method, method_code)

            # Dodaj nową metodę tylko jeśli nie zastąpiliśmy istniejącej
            if not new_tree:
                new_tree = tree.add_method_to_class(target_class, method_code)
            # Koniec zmiany

            new_code = parser.generate(new_tree)
            if dry_run:
                context['new_content'] = new_code
                return True
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_code)
            print(f'Success: Added method to class {class_name} in file {file_path}')
            return True
        except Exception as e:
            print(f'Error during method addition: {e}')
            return False

    def _extract_method_name(self, method_code: str) -> Optional[str]:
        """
        Extract method name from code.

        Args:
            method_code: Method code

        Returns:
            Method name or None if it can't be extracted
        """
        import re
        match = re.search('def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(', method_code)
        if match:
            return match.group(1)
        return None

@register_operation('delete_method')
class DeleteMethodOperation(Operation):
    """Operation to delete a method from a class."""

    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the delete method operation.

        Args:
            context: Execution context

        Returns:
            True if operation was successful, False otherwise
        """
        file_path = self.attributes.get('path')
        class_name = self.attributes.get('class')
        method_name = self.attributes.get('method')
        if not file_path or not class_name or (not method_name):
            print('Error: Missing required attributes for DeleteMethodOperation')
            return False
        try:
            if not os.path.exists(file_path):
                print(f'Error: File {file_path} does not exist')
                return False
            with open(file_path, 'r', encoding='utf-8') as file:
                code = file.read()
            parser = PythonParser()
            tree = parser.parse(code)
            classes = tree.find_classes()
            target_class = None
            for cls in classes:
                for child in cls.get_children():
                    if child.get_type() == 'identifier' and child.get_text() == class_name:
                        target_class = cls
                        break
                if target_class:
                    break
            if not target_class:
                print(f'Error: Class {class_name} not found in file {file_path}')
                return False
            method = tree.find_method_by_name(target_class, method_name)
            if not method:
                print(f'Error: Method {method_name} not found in class {class_name}')
                return False
            new_tree = tree.replace_node(method, '')
            new_code = parser.generate(new_tree)
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_code)
            print(f'Success: Deleted method {method_name} from class {class_name} in file {file_path}')
            return True
        except Exception as e:
            print(f'Error during method deletion: {e}')
            return False