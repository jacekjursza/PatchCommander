"""
Globalny pre-procesor parsujący tagi z wejściowego tekstu.
"""
import re
import os
from typing import List, Dict
from rich.console import Console
from ..models import PatchOperation
from ..processor_base import GlobalPreProcessor
from ....core.text_utils import normalize_line_endings

console = Console()

class TagParser(GlobalPreProcessor):
    """
    Globalny pre-procesor parsujący tagi PatchCommander z wejściowego tekstu.
    """

    def __init__(self):
        """Inicjalizacja parsera."""
        self.valid_operations = {"FILE", "OPERATION"}

    def process(self, input_text: str) -> List[PatchOperation]:
        """
        Parsuje tagi z tekstu wejściowego i tworzy listę operacji.

        Args:
            input_text: Tekst wejściowy zawierający tagi

        Returns:
            List[PatchOperation]: Lista operacji do wykonania
        """
        # Normalizacja tekstu
        normalized_text = normalize_line_endings(input_text)

        # Parsowanie tagów
        operations = []

        # Wzorzec dla tagów FILE i OPERATION
        tag_pattern = re.compile(r'<(FILE|OPERATION)(\s+[^>]*)?(?:>(.*?)</\1\s*>|/>)', re.DOTALL)

        for match in tag_pattern.finditer(normalized_text):
            tag_type = match.group(1)
            attr_str = match.group(2) or ""
            content = match.group(3) or ""

            # Parsowanie atrybutów
            attributes = self._parse_attributes(attr_str)

            # Sprawdzenie wymaganych atrybutów
            if tag_type == "FILE":
                if "path" not in attributes:
                    console.print("[bold red]Tag FILE wymaga atrybutu 'path'.[/bold red]")
                    continue
            elif tag_type == "OPERATION":
                if "action" not in attributes:
                    console.print("[bold red]Tag OPERATION wymaga atrybutu 'action'.[/bold red]")
                    continue

                # Sprawdzenie specyficznych wymagań dla różnych akcji
                action = attributes["action"]
                if action == "move_file":
                    if "source" not in attributes or "target" not in attributes:
                        console.print("[bold red]Operacja move_file wymaga atrybutów 'source' i 'target'.[/bold red]")
                        continue
                elif action == "delete_file":
                    if "source" not in attributes:
                        console.print("[bold red]Operacja delete_file wymaga atrybutu 'source'.[/bold red]")
                        continue
                elif action == "delete_method":
                    if "source" not in attributes or "class" not in attributes or "method" not in attributes:
                        console.print("[bold red]Operacja delete_method wymaga atrybutów 'source', 'class' i 'method'.[/bold red]")
                        continue

            # Utworzenie operacji
            operation = PatchOperation(
                name=tag_type,
                path=attributes.get("path", attributes.get("source", "")),
                content=content.strip(),
                xpath=attributes.get("xpath", None),
                action=attributes.get("action", None),
                attributes=attributes
            )

            # Dodanie rozszerzenia pliku
            if operation.path:
                _, ext = os.path.splitext(operation.path)
                operation.file_extension = ext.lower()[1:] if ext else ""

            operations.append(operation)

        return operations

    def _parse_attributes(self, attr_str: str) -> Dict[str, str]:
        """
        Parsuje atrybuty z tekstu.

        Args:
            attr_str: Tekst zawierający atrybuty w formacie HTML-like

        Returns:
            Dict[str, str]: Słownik atrybutów
        """
        if not attr_str:
            return {}

        attrs = {}
        pattern = r'(\w+)\s*=\s*"([^"]*)"'

        for match in re.finditer(pattern, attr_str):
            key, value = match.groups()
            attrs[key] = value

        return attrs