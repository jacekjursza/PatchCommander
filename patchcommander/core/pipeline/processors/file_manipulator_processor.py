import os

from rich.console import Console

from . import register_processor
from .base_manipulator_processor import BaseManipulatorProcessor
from ..models import PatchOperation, PatchResult

console = Console()

@register_processor(priority=50)
class FileManipulatorProcessor(BaseManipulatorProcessor):

    def can_handle(self, operation: PatchOperation) -> bool:
        return operation.name == 'FILE'

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        manipulator = self.get_manipulator_for_operation(operation)
        if not manipulator:
            operation.add_error(f'No manipulator available for operation on {operation.path}')
            return

        file_exists = os.path.exists(operation.path)
        if not operation.xpath:
            result.current_content = operation.content
            console.print(f"[green]{('Created' if not file_exists else 'Replaced entire content of')} {result.path}[/green]")
            return

        # Handle lines:X:Y xpath format
        if operation.attributes.get('target_type') == 'lines':
            start_line = operation.attributes.get('start_line')
            end_line = operation.attributes.get('end_line')
            if start_line is None or end_line is None:
                operation.add_error('Missing start_line or end_line attribute for lines target type')
                return

            if not file_exists:
                console.print(f'[yellow]File {result.path} does not exist, creating a new file with content[/yellow]')
                result.current_content = operation.content
            else:
                # Use preserve_formatting=True for lines xpath to maintain exact formatting
                result.current_content = manipulator.replace_lines_range(
                    result.current_content, 
                    start_line, 
                    end_line, 
                    operation.content,
                    preserve_formatting=True
                )
                console.print(f'[green]Updated lines {start_line}-{end_line} in {result.path}[/green]')
            return

        if not file_exists:
            console.print(f'[yellow]File {result.path} does not exist, creating a scaffold with the specified element[/yellow]')
            target_type = operation.attributes.get('target_type')
            if target_type == 'class':
                class_name = operation.attributes.get('class_name')
                if not class_name:
                    operation.add_error('Class name is missing')
                    return
                result.current_content = operation.content
                console.print(f'[green]Created file {result.path} with class {class_name}[/green]')
                return
            elif target_type == 'method':
                class_name = operation.attributes.get('class_name')
                method_name = operation.attributes.get('method_name')
                if not class_name or not method_name:
                    operation.add_error('Class name or method name is missing')
                    return
                result.current_content = f'class {class_name}:\n{self._indent_code(operation.content)}'
                console.print(f'[green]Created file {result.path} with class {class_name} containing method {method_name}[/green]')
                return
            elif target_type == 'function':
                function_name = operation.attributes.get('function_name')
                if not function_name:
                    operation.add_error('Function name is missing')
                    return
                result.current_content = operation.content
                console.print(f'[green]Created file {result.path} with function {function_name}[/green]')
                return
            else:
                operation.add_error(f'Unknown target type: {target_type}')
                return

        target_type = operation.attributes.get('target_type')
        if target_type == 'class':
            class_name = operation.attributes.get('class_name')
            if not class_name:
                operation.add_error('Class name is missing')
                return
            result.current_content = manipulator.replace_class(result.current_content, class_name, operation.content)
            console.print(f'[green]Updated class {class_name} in {result.path}[/green]')
        elif target_type == 'method':
            class_name = operation.attributes.get('class_name')
            method_name = operation.attributes.get('method_name')
            if not class_name or not method_name:
                operation.add_error('Class name or method name is missing')
                return
            result.current_content = manipulator.replace_method(result.current_content, class_name, method_name, operation.content)
            console.print(f'[green]Updated method {class_name}.{method_name} in {result.path}[/green]')
        elif target_type == 'function':
            function_name = operation.attributes.get('function_name')
            if not function_name:
                operation.add_error('Function name is missing')
                return
            result.current_content = manipulator.replace_function(result.current_content, function_name, operation.content)
            console.print(f'[green]Updated function {function_name} in {result.path}[/green]')
        else:
            operation.add_error(f'Unknown target type: {target_type}')
            
    def _indent_code(self, code: str, spaces: int = 4) -> str:
        """Helper method to indent code properly for class methods"""
        lines = code.splitlines()
        indented_lines = []
        for line in lines:
            indented_lines.append(' ' * spaces + line)
        return '\n'.join(indented_lines)