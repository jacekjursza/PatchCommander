
"""
Initialize input_preprocessors module.
Handles processing and normalizing input before tag parsing.
"""
from patchcommander.core.input_preprocessors.base import InputPreprocessor
from patchcommander.core.input_preprocessors.multiple_methods_splitter import MultipleMethodsSplitter

__all__ = ['preprocess_input']

def preprocess_input(input_text):
    """
    Apply all input preprocessors to input text.
    
    Args:
        input_text: Raw input text
        
    Returns:
        Preprocessed text
    """
    preprocessors = [
        MultipleMethodsSplitter(),
    ]
    
    current_text = input_text
    for preprocessor in preprocessors:
        current_text = preprocessor.process(current_text)
    
    return current_text
