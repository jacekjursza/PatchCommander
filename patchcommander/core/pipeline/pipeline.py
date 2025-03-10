"""
Main pipeline for processing PatchCommander operations.
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
    Main pipeline for processing PatchCommander operations.
    """

    def __init__(self):
        """Initializes the pipeline with empty lists of processors."""
        self.global_preprocessor: Optional[GlobalPreProcessor] = None
        self.pre_processors: List[PreProcessor] = []
        self.post_processors: List[PostProcessor] = []

    def set_global_preprocessor(self, preprocessor: GlobalPreProcessor) -> None:
        """
        Sets the global pre-processor.

        Args:
            preprocessor: The global pre-processor
        """
        self.global_preprocessor = preprocessor

    def add_preprocessor(self, preprocessor: PreProcessor) -> None:
        """
        Adds a pre-processor to the pipeline.

        Args:
            preprocessor: The pre-processor to add
        """
        self.pre_processors.append(preprocessor)

    def add_postprocessor(self, postprocessor: PostProcessor) -> None:
        """
        Adds a post-processor to the pipeline.

        Args:
            postprocessor: The post-processor to add
        """
        self.post_processors.append(postprocessor)

    def _get_file_content(self, path: str) -> str:
        """
        Gets the content of a file, if it exists.

        Args:
            path: The path to the file

        Returns:
            str: The content of the file or an empty string
        """
        if not os.path.exists(path):
            return ''
        try:
            with open(path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            console.print(f"[bold red]Error reading file '{path}': {e}[/bold red]")
            return ''

    def run(self, input_text: str) -> List[PatchResult]:
        """
        Runs the pipeline on the input text.

        Args:
            input_text: The input text containing tags

        Returns:
            List[PatchResult]: A list of patch results
        """
        if not self.global_preprocessor:
            raise ValueError('No global pre-processor set')

        operations = self.global_preprocessor.process(input_text)
        console.print(f'[blue]Detected {len(operations)} operations to process[/blue]')

        results: Dict[str, PatchResult] = {}
        for operation in operations:
            if operation.path not in results:
                original_content = self._get_file_content(operation.path)
                results[operation.path] = PatchResult(path=operation.path, original_content=original_content, current_content=original_content)
            results[operation.path].add_operation(operation)

        for pre_processor in self.pre_processors:
            for operation in operations:
                if pre_processor.can_handle(operation):
                    try:
                        pre_processor.process(operation)
                        operation.add_preprocessor(pre_processor.name)
                    except Exception as e:
                        error_msg = f'Error in pre-processor {pre_processor.name}: {str(e)}'
                        console.print(f'[bold red]{error_msg}[/bold red]')
                        operation.add_error(error_msg)

        for operation in operations:
            if not operation.has_errors():
                ProcessorRegistry.process_operation(operation, results[operation.path])

        for post_processor in self.post_processors:
            for path, result in results.items():
                try:
                    post_processor.process(result)
                    for operation in result.operations:
                        operation.add_postprocessor(post_processor.name)
                except Exception as e:
                    error_msg = f'Error in post-processor {post_processor.name}: {str(e)}'
                    console.print(f'[bold red]{error_msg}[/bold red]')
                    result.add_error(error_msg)

        return list(results.values())