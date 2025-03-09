"""
Główny pipeline do przetwarzania operacji PatchCommander.
"""
import os
from typing import List, Dict, Optional

from rich.console import Console

from .models import PatchResult
from .processor_base import PreProcessor, PostProcessor, GlobalPreProcessor
from .processors.registry import ProcessorRegistry

console = Console()

class Pipeline:
    """
    Główny pipeline do przetwarzania operacji PatchCommander.
    """

    def __init__(self):
        """Inicjalizacja pipeline z pustymi listami procesorów."""
        self.global_preprocessor: Optional[GlobalPreProcessor] = None
        self.pre_processors: List[PreProcessor] = []
        self.post_processors: List[PostProcessor] = []

    def set_global_preprocessor(self, preprocessor: GlobalPreProcessor) -> None:
        """
        Ustawia globalny pre-procesor.

        Args:
            preprocessor: Globalny pre-procesor
        """
        self.global_preprocessor = preprocessor

    def add_preprocessor(self, preprocessor: PreProcessor) -> None:
        """
        Dodaje pre-procesor do pipeline.

        Args:
            preprocessor: Pre-procesor do dodania
        """
        self.pre_processors.append(preprocessor)

    def add_postprocessor(self, postprocessor: PostProcessor) -> None:
        """
        Dodaje post-procesor do pipeline.

        Args:
            postprocessor: Post-procesor do dodania
        """
        self.post_processors.append(postprocessor)

    def _get_file_content(self, path: str) -> str:
        """
        Pobiera zawartość pliku, jeśli istnieje.

        Args:
            path: Ścieżka do pliku

        Returns:
            str: Zawartość pliku lub pusty string
        """
        if not os.path.exists(path):
            return ''
        try:
            with open(path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            console.print(f"[bold red]Błąd odczytu pliku '{path}': {e}[/bold red]")
            return ''

    def run(self, input_text: str) -> List[PatchResult]:
        """
        Uruchamia pipeline na tekście wejściowym.

        Args:
            input_text: Tekst wejściowy zawierający tagi

        Returns:
            List[PatchResult]: Lista wyników patch
        """
        if not self.global_preprocessor:
            raise ValueError('Nie ustawiono globalnego pre-procesora')

        # Parsuj operacje przez globalny pre-procesor
        operations = self.global_preprocessor.process(input_text)
        console.print(f'[blue]Wykryto {len(operations)} operacji do przetworzenia[/blue]')

        # Inicjalizuj wyniki dla każdego pliku
        results: Dict[str, PatchResult] = {}
        for operation in operations:
            if operation.path not in results:
                original_content = self._get_file_content(operation.path)
                results[operation.path] = PatchResult(path=operation.path, original_content=original_content, current_content=original_content)
            results[operation.path].add_operation(operation)

        # Przetwarzanie przez pre-procesory
        for pre_processor in self.pre_processors:
            for operation in operations:
                if pre_processor.can_handle(operation):
                    try:
                        pre_processor.process(operation)
                        operation.add_preprocessor(pre_processor.name)
                    except Exception as e:
                        error_msg = f'Błąd w pre-procesorze {pre_processor.name}: {str(e)}'
                        console.print(f'[bold red]{error_msg}[/bold red]')
                        operation.add_error(error_msg)

        # Przetwarzanie przez procesory z rejestru
        for operation in operations:
            if not operation.has_errors():
                # Użyj rejestru procesorów do przetworzenia operacji
                ProcessorRegistry.process_operation(operation, results[operation.path])

        # Przetwarzanie przez post-procesory
        for post_processor in self.post_processors:
            for (path, result) in results.items():
                try:
                    post_processor.process(result)
                    for operation in result.operations:
                        operation.add_postprocessor(post_processor.name)
                except Exception as e:
                    error_msg = f'Błąd w post-procesorze {post_processor.name}: {str(e)}'
                    console.print(f'[bold red]{error_msg}[/bold red]')
                    result.add_error(error_msg)

        return list(results.values())