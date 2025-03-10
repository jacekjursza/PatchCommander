from rich.console import Console
from .. import Processor, PatchOperation, PatchResult
from ....parsers.python_parser import PythonParser
from ....parsers.javascript_parser import JavaScriptParser

console = Console()
from .decorator import register_processor


@register_processor(priority=50)
class FileProcessor(Processor):
    """
    Processor for FILE operations.
    Handles modifications of entire files or fragments indicated by xpath.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.

        Args:
            operation: The operation to check

        Returns:
            bool: True if it's a FILE operation
        """
        return operation.name == 'FILE' and (not operation.xpath)

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Processes a FILE operation.

        Args:
            operation: The operation to process
            result: The result to update
        """
        if not operation.xpath:
            result.current_content = operation.content
            return
        console.print(
            f"[blue]Processing xpath '{operation.xpath}' for file {result.path}[/blue]"
        )
        target_type = operation.attributes.get('target_type')
        if not target_type:
            operation.add_error('Unable to determine the target type for XPath')
            console.print('[red]Unable to determine the target type for XPath[/red]')
            return
        console.print(f'[blue]Target type: {target_type}[/blue]')
        if operation.file_extension == 'py':
            self._process_python_file(operation, result)
        elif operation.file_extension in ['js', 'jsx', 'ts', 'tsx']:
            self._process_javascript_file(operation, result)
        else:
            operation.add_error(
                f'Unsupported file extension: {operation.file_extension}'
            )
            console.print(
                f'[red]Unsupported file extension: {operation.file_extension}[/red]'
            )

    def _process_python_file(
        self, operation: PatchOperation, result: PatchResult
    ) -> None:
        """
        Processes a FILE operation for a Python file.

        Args:
            operation: The operation to process
            result: The result to update
        """
        target_type = operation.attributes.get('target_type')
        console.print(
            f'[blue]Processing Python file, target_type={target_type}[/blue]'
        )
        if not result.current_content:
            if target_type == 'class':
                result.current_content = operation.content
            elif target_type == 'method':
                class_name = operation.attributes.get('class_name', 'UnknownClass')
                method_content = operation.content.strip()
                method_lines = method_content.split('\n')
                indented_method = method_lines[0] + '\n' + '\n'.join(
                    [f'    {line}' for line in method_lines[1:]]
                )
                result.current_content = (
                    f'class {class_name}:\n    {indented_method}'
                )
            elif target_type == 'function':
                result.current_content = operation.content
            return
        parser = PythonParser()
        tree = parser.parse(result.current_content)
        if target_type == 'class':
            class_name = operation.attributes.get('class_name')
            if not class_name:
                operation.add_error('Missing class name')
                return
            classes = tree.find_classes()
            target_class = None
            for cls in classes:
                for child in cls.get_children():
                    if (
                        child.get_type() == 'identifier'
                        and child.get_text() == class_name
                    ):
                        target_class = cls
                        break
                if target_class:
                    break
            if target_class:
                start_byte = target_class.ts_node.start_byte
                end_byte = target_class.ts_node.end_byte
                new_content = (
                    result.current_content[:start_byte]
                    + operation.content
                    + result.current_content[end_byte:]
                )
                result.current_content = new_content
                console.print(f'[green]Updated class {class_name}[/green]')
            else:
                separator = (
                    '\n\n'
                    if result.current_content
                    and (not result.current_content.endswith('\n\n'))
                    else ''
                )
                result.current_content = (
                    result.current_content + separator + operation.content
                )
                console.print(f'[green]Added new class {class_name}[/green]')
        elif target_type == 'method':
            class_name = operation.attributes.get('class_name')
            method_name = operation.attributes.get('method_name')
            if not class_name or not method_name:
                operation.add_error('Missing class or method name')
                return
            classes = tree.find_classes()
            target_class = None
            for cls in classes:
                for child in cls.get_children():
                    if (
                        child.get_type() == 'identifier'
                        and child.get_text() == class_name
                    ):
                        target_class = cls
                        break
                if target_class:
                    break
            if not target_class:
                operation.add_error(f'Class {class_name} not found')
                return
            method = tree.find_method_by_name(target_class, method_name)
            if method:
                # By default, we replace the method entirely (behavior before changes)
                new_tree = tree.replace_method_in_class(
                    target_class, method, operation.content
                )
                result.current_content = parser.generate(new_tree)
                console.print(
                    f'[green]Updated method {class_name}.{method_name}[/green]'
                )
            else:
                new_tree = tree.add_method_to_class(
                    target_class, operation.content
                )
                result.current_content = parser.generate(new_tree)
                console.print(
                    f'[green]Added new method {class_name}.{method_name}[/green]'
                )
        elif target_type == 'function':
            function_name = operation.attributes.get('function_name')
            if not function_name:
                operation.add_error('Missing function name')
                return
            console.print(f'[blue]Searching for function {function_name}[/blue]')
            functions = tree.find_functions()
            console.print(f'[blue]Found {len(functions)} functions in the file[/blue]')
            target_function = None
            for func in functions:
                console.print(
                    f'[blue]Checking function: {func.get_text()[:40]}...[/blue]'
                )
                for child in func.get_children():
                    if (
                        child.get_type() == 'identifier'
                        or child.get_type() == 'name'
                    ):
                        console.print(
                            f'[blue]  - Found identifier: {child.get_text()}[/blue]'
                        )
                        if child.get_text() == function_name:
                            target_function = func
                            console.print(
                                f'[green]  - Matched {function_name}![/green]'
                            )
                            break
                if target_function:
                    break
            if target_function:
                console.print(
                    f'[green]Found function {function_name}, replacing...[/green]'
                )
                start_byte = target_function.ts_node.start_byte
                end_byte = target_function.ts_node.end_byte
                new_content = (
                    result.current_content[:start_byte] + operation.content
                )
                if end_byte < len(result.current_content):
                    new_content += result.current_content[end_byte:]
                result.current_content = new_content
                console.print(f'[green]Updated function {function_name}[/green]')
            else:
                console.print(
                    f'[yellow]Function {function_name} not found, adding a new one...[/yellow]'
                )
                separator = (
                    '\n\n'
                    if result.current_content
                    and (not result.current_content.endswith('\n\n'))
                    else ''
                )
                result.current_content = (
                    result.current_content + separator + operation.content
                )
                console.print(f'[green]Added new function {function_name}[/green]')

    def _process_javascript_file(
        self, operation: PatchOperation, result: PatchResult
    ) -> None:
        """
        Processes a FILE operation for a JavaScript file.

        Args:
            operation: The operation to process
            result: The result to update
        """
        target_type = operation.attributes.get('target_type')
        if not result.current_content:
            if target_type == 'class':
                result.current_content = operation.content
            elif target_type == 'method':
                class_name = operation.attributes.get('class_name', 'UnknownClass')
                method_content = operation.content.strip()
                result.current_content = (
                    f'class {class_name} {{\n    {method_content}\n}}'
                )
            elif target_type == 'function':
                result.current_content = operation.content
            return
        parser = JavaScriptParser()
        tree = parser.parse(result.current_content)
        if target_type == 'class':
            class_name = operation.attributes.get('class_name')
            if not class_name:
                operation.add_error('Missing class name')
                return
            classes = tree.find_classes()
            target_class = None
            for cls in classes:
                for child in cls.get_children():
                    if (
                        child.get_type() == 'identifier'
                        and child.get_text() == class_name
                    ):
                        target_class = cls
                        break
                if target_class:
                    break
            if target_class:
                start_byte = target_class.ts_node.start_byte
                end_byte = target_class.ts_node.end_byte
                new_content = (
                    result.current_content[:start_byte]
                    + operation.content
                    + result.current_content[end_byte:]
                )
                result.current_content = new_content
            else:
                separator = (
                    '\n\n'
                    if result.current_content
                    and (not result.current_content.endswith('\n\n'))
                    else ''
                )
                result.current_content = (
                    result.current_content + separator + operation.content
                )
        elif target_type == 'method':
            class_name = operation.attributes.get('class_name')
            method_name = operation.attributes.get('method_name')
            if not class_name or not method_name:
                operation.add_error('Missing class or method name')
                return
            classes = tree.find_classes()
            target_class = None
            for cls in classes:
                for child in cls.get_children():
                    if (
                        child.get_type() == 'identifier'
                        and child.get_text() == class_name
                    ):
                        target_class = cls
                        break
                if target_class:
                    break
            if not target_class:
                operation.add_error(f'Class {class_name} not found')
                return
            method = tree.find_method_by_name(target_class, method_name)
            if method:
                new_tree = tree.replace_node(method, operation.content)
                result.current_content = parser.generate(new_tree)
            else:
                new_tree = tree.add_method_to_class(
                    target_class, operation.content
                )
                result.current_content = parser.generate(new_tree)
        elif target_type == 'function':
            function_name = operation.attributes.get('function_name')
            if not function_name:
                operation.add_error('Missing function name')
                return
            functions = tree.find_functions()
            target_function = None
            for func in functions:
                found = False
                for child in func.get_children():
                    if (
                        child.get_type() == 'identifier'
                        and child.get_text() == function_name
                    ):
                        target_function = func
                        found = True
                        break
                if found:
                    break
            if target_function:
                start_byte = target_function.ts_node.start_byte
                end_byte = target_function.ts_node.end_byte
                new_content = (
                    result.current_content[:start_byte]
                    + operation.content
                    + result.current_content[end_byte:]
                )
                result.current_content = new_content
            else:
                separator = (
                    '\n\n'
                    if result.current_content
                    and (not result.current_content.endswith('\n\n'))
                    else ''
                )
                result.current_content = (
                    result.current_content + separator + operation.content
                )