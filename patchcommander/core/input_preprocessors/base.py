
"""
Base class for input preprocessors.
"""
from abc import ABC, abstractmethod

class InputPreprocessor(ABC):
    """Base class for input preprocessors."""
    
    @abstractmethod
    def process(self, input_text):
        """
        Process input text.
        
        Args:
            input_text: Raw input text
            
        Returns:
            Processed text
        """
        pass
