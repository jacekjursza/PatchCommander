from rich.console import Console
from .. import Processor, PatchOperation, PatchResult
from ....parsers.python_parser import PythonParser
from ....parsers.javascript_parser import JavaScriptParser
console = Console()
from .decorator import register_processor

@register_processor(priority=50)
class FileProcessor(Processor):
    """
    Procesor dla operacji FILE.
    Obsługuje modyfikacje plików całych lub fragmentów wskazanych przez xpath.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Sprawdza czy procesor może obsłużyć operację.

        Args:
            operation: Operacja do sprawdzenia

        Returns:
            bool: True jeśli to operacja FILE
        """
        return operation.name == 'FILE' and (not operation.xpath)

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Przetwarza operację FILE.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
        """
        if not operation.xpath:
            result.current_content = operation.content
            return
        console.print(f"[blue]Przetwarzam xpath '{operation.xpath}' dla pliku {result.path}[/blue]")
        target_type = operation.attributes.get('target_type')
        if not target_type:
            operation.add_error('Nie można określić typu celu dla XPath')
            console.print('[red]Nie można określić typu celu dla XPath[/red]')
            return
        console.print(f'[blue]Target type: {target_type}[/blue]')
        if operation.file_extension == 'py':
            self._process_python_file(operation, result)
        elif operation.file_extension in ['js', 'jsx', 'ts', 'tsx']:
            self._process_javascript_file(operation, result)
        else:
            operation.add_error(f'Nieobsługiwane rozszerzenie pliku: {operation.file_extension}')
            console.print(f'[red]Nieobsługiwane rozszerzenie pliku: {operation.file_extension}[/red]')

    def _process_python_file(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Przetwarza operację FILE dla pliku Python.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
        """
        target_type = operation.attributes.get('target_type')
        console.print(f'[blue]Przetwarzam plik Python, target_type={target_type}[/blue]')
        if not result.current_content:
            if target_type == 'class':
                result.current_content = operation.content
            elif target_type == 'method':
                class_name = operation.attributes.get('class_name', 'UnknownClass')
                method_content = operation.content.strip()
                method_lines = method_content.split('\n')
                indented_method = method_lines[0] + '\n' + '\n'.join([f'    {line}' for line in method_lines[1:]])
                result.current_content = f'class {class_name}:\n    {indented_method}'
            elif target_type == 'function':
                result.current_content = operation.content
            return
        parser = PythonParser()
        tree = parser.parse(result.current_content)
        if target_type == 'class':
            class_name = operation.attributes.get('class_name')
            if not class_name:
                operation.add_error('Brak nazwy klasy')
                return
            classes = tree.find_classes()
            target_class = None
            for cls in classes:
                for child in cls.get_children():
                    if child.get_type() == 'identifier' and child.get_text() == class_name:
                        target_class = cls
                        break
                if target_class:
                    break
            if target_class:
                start_byte = target_class.ts_node.start_byte
                end_byte = target_class.ts_node.end_byte
                new_content = result.current_content[:start_byte] + operation.content + result.current_content[end_byte:]
                result.current_content = new_content
                console.print(f'[green]Zaktualizowano klasę {class_name}[/green]')
            else:
                separator = '\n\n' if result.current_content and (not result.current_content.endswith('\n\n')) else ''
                result.current_content = result.current_content + separator + operation.content
                console.print(f'[green]Dodano nową klasę {class_name}[/green]')
        elif target_type == 'method':
            class_name = operation.attributes.get('class_name')
            method_name = operation.attributes.get('method_name')
            if not class_name or not method_name:
                operation.add_error('Brak nazwy klasy lub metody')
                return
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
                operation.add_error(f'Nie znaleziono klasy {class_name}')
                return
            method = tree.find_method_by_name(target_class, method_name)
            if method:
                # Domyślnie zamieniamy metodę całkowicie (zachowanie przed zmianami)
                new_tree = tree.replace_method_in_class(target_class, method, operation.content)
                result.current_content = parser.generate(new_tree)
                console.print(f'[green]Zaktualizowano metodę {class_name}.{method_name}[/green]')
            else:
                new_tree = tree.add_method_to_class(target_class, operation.content)
                result.current_content = parser.generate(new_tree)
                console.print(f'[green]Dodano nową metodę {class_name}.{method_name}[/green]')
        elif target_type == 'function':
            function_name = operation.attributes.get('function_name')
            if not function_name:
                operation.add_error('Brak nazwy funkcji')
                return
            console.print(f'[blue]Szukam funkcji {function_name}[/blue]')
            functions = tree.find_functions()
            console.print(f'[blue]Znaleziono {len(functions)} funkcji w pliku[/blue]')
            target_function = None
            for func in functions:
                console.print(f'[blue]Sprawdzam funkcję: {func.get_text()[:40]}...[/blue]')
                for child in func.get_children():
                    if child.get_type() == 'identifier' or child.get_type() == 'name':
                        console.print(f'[blue]  - Znaleziono identyfikator: {child.get_text()}[/blue]')
                        if child.get_text() == function_name:
                            target_function = func
                            console.print(f'[green]  - Dopasowano do {function_name}![/green]')
                            break
                if target_function:
                    break
            if target_function:
                console.print(f'[green]Znaleziono funkcję {function_name}, zastępuję...[/green]')
                start_byte = target_function.ts_node.start_byte
                end_byte = target_function.ts_node.end_byte
                new_content = result.current_content[:start_byte] + operation.content
                if end_byte < len(result.current_content):
                    new_content += result.current_content[end_byte:]
                result.current_content = new_content
                console.print(f'[green]Zaktualizowano funkcję {function_name}[/green]')
            else:
                console.print(f'[yellow]Nie znaleziono funkcji {function_name}, dodaję nową...[/yellow]')
                separator = '\n\n' if result.current_content and (not result.current_content.endswith('\n\n')) else ''
                result.current_content = result.current_content + separator + operation.content
                console.print(f'[green]Dodano nową funkcję {function_name}[/green]')

    def _process_javascript_file(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Przetwarza operację FILE dla pliku JavaScript.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
        """
        target_type = operation.attributes.get('target_type')
        if not result.current_content:
            if target_type == 'class':
                result.current_content = operation.content
            elif target_type == 'method':
                class_name = operation.attributes.get('class_name', 'UnknownClass')
                method_content = operation.content.strip()
                result.current_content = f'class {class_name} {{\n    {method_content}\n}}'
            elif target_type == 'function':
                result.current_content = operation.content
            return
        parser = JavaScriptParser()
        tree = parser.parse(result.current_content)
        if target_type == 'class':
            class_name = operation.attributes.get('class_name')
            if not class_name:
                operation.add_error('Brak nazwy klasy')
                return
            classes = tree.find_classes()
            target_class = None
            for cls in classes:
                for child in cls.get_children():
                    if child.get_type() == 'identifier' and child.get_text() == class_name:
                        target_class = cls
                        break
                if target_class:
                    break
            if target_class:
                start_byte = target_class.ts_node.start_byte
                end_byte = target_class.ts_node.end_byte
                new_content = result.current_content[:start_byte] + operation.content + result.current_content[end_byte:]
                result.current_content = new_content
            else:
                separator = '\n\n' if result.current_content and (not result.current_content.endswith('\n\n')) else ''
                result.current_content = result.current_content + separator + operation.content
        elif target_type == 'method':
            class_name = operation.attributes.get('class_name')
            method_name = operation.attributes.get('method_name')
            if not class_name or not method_name:
                operation.add_error('Brak nazwy klasy lub metody')
                return
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
                operation.add_error(f'Nie znaleziono klasy {class_name}')
                return
            method = tree.find_method_by_name(target_class, method_name)
            if method:
                new_tree = tree.replace_node(method, operation.content)
                result.current_content = parser.generate(new_tree)
            else:
                new_tree = tree.add_method_to_class(target_class, operation.content)
                result.current_content = parser.generate(new_tree)
        elif target_type == 'function':
            function_name = operation.attributes.get('function_name')
            if not function_name:
                operation.add_error('Brak nazwy funkcji')
                return
            functions = tree.find_functions()
            target_function = None
            for func in functions:
                found = False
                for child in func.get_children():
                    if child.get_type() == 'identifier' and child.get_text() == function_name:
                        target_function = func
                        found = True
                        break
                if found:
                    break
            if target_function:
                start_byte = target_function.ts_node.start_byte
                end_byte = target_function.ts_node.end_byte
                new_content = result.current_content[:start_byte] + operation.content + result.current_content[end_byte:]
                result.current_content = new_content
            else:
                separator = '\n\n' if result.current_content and (not result.current_content.endswith('\n\n')) else ''
                result.current_content = result.current_content + separator + operation.content