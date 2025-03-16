from typing import Dict, Any, Type, Optional
from rich.console import Console
from ..processor_base import Processor
from ..models import PatchOperation, PatchResult
from ...manipulator import AbstractCodeManipulator, PythonCodeManipulator, TypeScriptCodeManipulator

console = Console()

class BaseManipulatorProcessor(Processor):
    """
    Base processor that uses code manipulators to process operations.
    This allows for language-specific handling without duplicating code.
    """
    
    # Registry of manipulators by language
    _manipulators: Dict[str, Type[AbstractCodeManipulator]] = {
        'python': PythonCodeManipulator,
        'typescript': TypeScriptCodeManipulator,
        'javascript': TypeScriptCodeManipulator  # JavaScript uses the same manipulator as TypeScript
    }
    
    # Cached manipulator instances
    _manipulator_instances: Dict[str, AbstractCodeManipulator] = {}
    
    def __init__(self):
        super().__init__()
    
    def get_manipulator(self, language: str) -> Optional[AbstractCodeManipulator]:
        """Get the appropriate manipulator for the given language"""
        language = language.lower()
        
        if language not in self._manipulator_instances:
            if language in self._manipulators:
                self._manipulator_instances[language] = self._manipulators[language]()
            else:
                console.print(f"[yellow]Warning: No manipulator available for language: {language}[/yellow]")
                return None
                
        return self._manipulator_instances[language]
    
    def get_language_for_file(self, file_path: str) -> str:
        """Determine the language based on file extension"""
        from ...languages import get_language_for_file
        try:
            return get_language_for_file(file_path)
        except ValueError:
            # Default to python if language can't be determined
            console.print(f"[yellow]Warning: Could not determine language for {file_path}, defaulting to Python[/yellow]")
            return 'python'
    
    def get_manipulator_for_operation(self, operation: PatchOperation) -> Optional[AbstractCodeManipulator]:
        """Get the appropriate manipulator for the given operation"""
        language = operation.attributes.get('language')
        
        if not language:
            language = self.get_language_for_file(operation.path)
            operation.attributes['language'] = language
            
        return self.get_manipulator(language)