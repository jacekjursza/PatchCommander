"""
Manipulator functions for applying changes from PatchCommander processing.
"""
import os
import logging
from typing import List, Dict, Optional, Union, Callable, Any, TextIO, Tuple
from patchcommander.core.config import Config
from patchcommander.core.pipeline.models import PatchOperation, PatchResult
from patchcommander.api.processor import _setup_pipeline
from patchcommander.core.text_utils import normalize_line_endings, normalize_indentation

logger = logging.getLogger(__name__)

class PatchCommanderAPI:
    """Main class for interacting with PatchCommander programmatically."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, 
                 logger: Optional[logging.Logger] = None, 
                 auto_approve: bool = False):
        """
        Initialize the PatchCommander API.
        
        Args:
            config: Configuration options
            logger: Custom logger
            auto_approve: Automatically approve all changes
        """
        self.config = Config()
        self._original_settings = {'default_yes_to_all': self.config.get('default_yes_to_all', False)}
        if config:
            for key, value in config.items():
                self.config.set(key, value)
        self.logger = logger or logging.getLogger(__name__)
        self.auto_approve = auto_approve
        if auto_approve:
            self.config.set('default_yes_to_all', True)
        self.pipeline = _setup_pipeline()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.restore_original_settings()
        return False

    def restore_original_settings(self):
        """Restore original configuration settings."""
        for key, value in self._original_settings.items():
            self.config.set(key, value)
        self.logger.debug(f'Restored original settings: {self._original_settings}')

    def process_text(self, input_text: str, normalize_indent: bool = True) -> List[PatchResult]:
        """
        Process text containing PatchCommander tags.
        
        Args:
            input_text: The text containing PatchCommander tags
            normalize_indent: Whether to normalize indentation
            
        Returns:
            List of processing results
        """
        normalized_text = normalize_line_endings(input_text)
        if normalize_indent:
            normalized_text = normalize_indentation(normalized_text)
        self.logger.debug(f'Processing text with {len(normalized_text)} characters')
        results = self.pipeline.run(normalized_text)
        self.logger.info(f'Generated {len(results)} patch results')
        return results

    def process_file(self, file_path: str, normalize_indent: bool = True) -> List[PatchResult]:
        """
        Process a file containing PatchCommander tags.
        
        Args:
            file_path: Path to the file containing PatchCommander tags
            normalize_indent: Whether to normalize indentation
            
        Returns:
            List of processing results
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'File not found: {file_path}')
        self.logger.debug(f'Processing file: {file_path}')
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.process_text(content, normalize_indent=normalize_indent)

    def apply_changes(self, results: List[PatchResult], 
                     approvals: Optional[Dict[str, bool]] = None) -> Tuple[int, int]:
        """
        Apply the changes from processing results.
        
        Args:
            results: Processing results
            approvals: Dictionary mapping file paths to approval booleans
            
        Returns:
            Tuple of (modified_count, operation_count)
        """
        if approvals is None:
            if self.auto_approve:
                approvals = {result.path: True for result in results}
            else:
                approvals = {result.path: False for result in results}
        modified_count = 0
        operation_count = 0
        for result in results:
            if approvals.get(result.path, False):
                try:
                    if hasattr(result, 'attributes') and result.attributes.get('should_delete', False):
                        if os.path.exists(result.path):
                            os.remove(result.path)
                            self.logger.info(f'Deleted file: {result.path}')
                            modified_count += 1
                            operation_count += len(result.operations)
                        else:
                            self.logger.warning(f'File does not exist: {result.path}')
                    elif hasattr(result, 'attributes') and 'target_path' in result.attributes:
                        source_path = result.path
                        target_path = result.attributes['target_path']
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        if os.path.exists(source_path):
                            os.rename(source_path, target_path)
                            self.logger.info(f'Moved file from {source_path} to {target_path}')
                        else:
                            with open(target_path, 'w', encoding='utf-8') as f:
                                f.write(result.current_content)
                            self.logger.info(f'Created file at target location: {target_path}')
                        modified_count += 1
                        operation_count += len(result.operations)
                    else:
                        directory = os.path.dirname(result.path)
                        if directory and (not os.path.exists(directory)):
                            os.makedirs(directory, exist_ok=True)
                        with open(result.path, 'w', encoding='utf-8') as f:
                            f.write(result.current_content)
                        self.logger.info(f'Applied changes to {result.path}')
                        modified_count += 1
                        operation_count += len(result.operations)
                except Exception as e:
                    self.logger.error(f'Error applying changes to {result.path}: {e}')
        return (modified_count, operation_count)

    def generate_diff(self, results: List[PatchResult]) -> Dict[str, str]:
        """
        Generate unified diffs for the changes.
        
        Args:
            results: Processing results
            
        Returns:
            Dictionary mapping file paths to diff strings
        """
        import difflib
        diffs = {}
        for result in results:
            if result.original_content == result.current_content:
                continue
            old_lines = result.original_content.splitlines()
            new_lines = result.current_content.splitlines()
            diff_lines = list(difflib.unified_diff(old_lines, new_lines, 
                                                 fromfile=f'original: {result.path}', 
                                                 tofile=f'modified: {result.path}', 
                                                 lineterm=''))
            if diff_lines:
                diffs[result.path] = '\n'.join(diff_lines)
        return diffs

    def save_diff_to_file(self, results: List[PatchResult], 
                         output_file: Union[str, TextIO]) -> None:
        """
        Save diffs to a file.
        
        Args:
            results: Processing results
            output_file: Output file path or file-like object
        """
        diffs = self.generate_diff(results)
        if not diffs:
            self.logger.info('No changes to write to diff file')
            return
        content = []
        for file_path, diff in diffs.items():
            content.append(f'Changes for {file_path}:\n')
            content.append(diff)
            content.append('\n' + '=' * 80 + '\n')
        if isinstance(output_file, str):
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            self.logger.info(f'Diff saved to {output_file}')
        else:
            output_file.write('\n'.join(content))
            self.logger.info('Diff written to provided file object')

def apply_changes(results: List[PatchResult], 
                 approvals: Optional[Dict[str, bool]] = None, 
                 auto_approve: bool = False, **config) -> Tuple[int, int]:
    """
    Apply the changes from processing results.
    
    Args:
        results: Processing results
        approvals: Dictionary mapping file paths to approval booleans
        auto_approve: Automatically approve all changes
        **config: Additional configuration options
        
    Returns:
        Tuple of (modified_count, operation_count)
    """
    api = PatchCommanderAPI(config=config, auto_approve=auto_approve)
    return api.apply_changes(results, approvals)