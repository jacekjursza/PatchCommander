"""
Analizator XPath dla pre-procesora.
"""
import re
from ...models import PatchOperation
from ...processor_base import PreProcessor
from rich.console import Console
console = Console()

class XPathAnalyzer(PreProcessor):
    """
    Pre-procesor analizujący i walidujący XPath w operacji.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Sprawdza czy analizator może obsłużyć operację.

        Args:
            operation: Operacja do sprawdzenia

        Returns:
            bool: True jeśli operacja ma atrybut xpath
        """
        return operation.name == 'FILE' and operation.xpath is not None

    def process(self, operation: PatchOperation) -> None:
        """
        Analizuje i waliduje XPath w operacji.

        Args:
            operation: Operacja do przetworzenia
        """
        if not operation.xpath:
            return
        console.print(f"[blue]Analizuję xpath: '{operation.xpath}'[/blue]")
        console.print(f"[blue]Zawartość zaczyna się od: '{operation.content[:40].strip()}...'[/blue]")
        class_method_match = re.match('^([A-Za-z_][A-Za-z0-9_]*?)\\.([A-Za-z_][A-Za-z0-9_]*?)$', operation.xpath)
        if class_method_match:
            (class_name, method_name) = class_method_match.groups()
            operation.attributes['target_type'] = 'method'
            operation.attributes['class_name'] = class_name
            operation.attributes['method_name'] = method_name
            console.print(f'[green]Rozpoznano metodę klasy: {class_name}.{method_name}[/green]')
            return

        # Zaktualizowany wzorzec dla dopasowania deklaracji funkcji z adnotacjami typów zwracanych
        func_def_match = re.search('^\\s*(async\\s+)?def\\s+([A-Za-z_][A-Za-z0-9_]*)', operation.content, re.MULTILINE)
        function_match = re.match('^([A-Za-z_][A-Za-z0-9_]*?)$', operation.xpath)
        if function_match and func_def_match:
            function_name = function_match.group(1)
            if func_def_match.group(2) == function_name:
                operation.attributes['target_type'] = 'function'
                operation.attributes['function_name'] = function_name
                console.print(f'[green]Rozpoznano funkcję: {function_name}[/green]')
                return

        class_match = re.match('^([A-Za-z_][A-Za-z0-9_]*?)$', operation.xpath)
        if class_match:
            class_name = class_match.group(1)
            if re.search('^\\s*class\\s+' + re.escape(class_name), operation.content, re.MULTILINE):
                operation.attributes['target_type'] = 'class'
                operation.attributes['class_name'] = class_name
                console.print(f'[green]Rozpoznano klasę: {class_name}[/green]')
                return
            elif func_def_match:
                operation.attributes['target_type'] = 'function'
                operation.attributes['function_name'] = class_name
                console.print(f'[green]Rozpoznano funkcję: {class_name}[/green]')
                return

        operation.add_error(f'Nieprawidłowy format XPath: {operation.xpath}')
        console.print(f'[red]Nieprawidłowy format XPath: {operation.xpath}[/red]')