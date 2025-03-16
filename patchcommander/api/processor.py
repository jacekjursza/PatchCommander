"""
Processing functions for PatchCommander tags.
"""
from typing import List, Dict, Optional, Union, Any
import logging
from patchcommander.core.text_utils import normalize_line_endings, normalize_indentation
from patchcommander.core.pipeline.pipeline import Pipeline
from patchcommander.core.pipeline.models import PatchResult
from patchcommander.core.pipeline.pre_processors.global_processor import TagParser
from patchcommander.core.pipeline.pre_processors.custom import (
    XPathAnalyzer, MarkdownCodeBlockCleaner, XPathMethodCorrector
)
from patchcommander.core.pipeline.post_processors import SyntaxValidator, DuplicateMethodChecker

logger = logging.getLogger(__name__)

def _setup_pipeline() -> Pipeline:
    """Set up the processing pipeline."""
    pipeline = Pipeline()
    pipeline.set_global_preprocessor(TagParser())
    pipeline.add_preprocessor(MarkdownCodeBlockCleaner())
    pipeline.add_preprocessor(XPathAnalyzer())
    pipeline.add_preprocessor(XPathMethodCorrector())
    pipeline.add_postprocessor(SyntaxValidator())
    pipeline.add_postprocessor(DuplicateMethodChecker())
    return pipeline

def process_text(input_text: str, auto_approve: bool = False, 
                normalize_indent: bool = True, **config) -> List[PatchResult]:
    """
    Process text containing PatchCommander tags.
    
    Args:
        input_text: Text containing PatchCommander tags
        auto_approve: Automatically approve all changes
        normalize_indent: Whether to normalize indentation
        **config: Additional configuration options
        
    Returns:
        List of processing results
    """
    from patchcommander.api.manipulator import PatchCommanderAPI
    
    with PatchCommanderAPI(config=config, auto_approve=auto_approve) as api:
        return api.process_text(input_text, normalize_indent=normalize_indent)

def process_file(file_path: str, auto_approve: bool = False, 
                normalize_indent: bool = True, **config) -> List[PatchResult]:
    """
    Process a file containing PatchCommander tags.
    
    Args:
        file_path: Path to file containing PatchCommander tags
        auto_approve: Automatically approve all changes
        normalize_indent: Whether to normalize indentation
        **config: Additional configuration options
        
    Returns:
        List of processing results
    """
    from patchcommander.api.manipulator import PatchCommanderAPI
    
    with PatchCommanderAPI(config=config, auto_approve=auto_approve) as api:
        return api.process_file(file_path, normalize_indent=normalize_indent)