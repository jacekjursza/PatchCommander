from rich.console import Console

from . import register_processor
from ..processor_base import Processor
from ..models import PatchOperation, PatchResult
from .base_manipulator_processor import BaseManipulatorProcessor


console = Console()

@register_processor(priority=50)
class FileManipulatorProcessor(BaseManipulatorProcessor):
    """
    Processor that handles FILE operations using the appropriate code manipulator
    based on the file type. This replaces the old FileProcessor with more 
    structured manipulation.
    """
    
    def can_handle(self, operation: PatchOperation) -> bool:
        return operation.name == 'FILE'
    
    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        manipulator = self.get_manipulator_for_operation(operation)
        
        if not manipulator:
            operation.add_error(f"No manipulator available for operation on {operation.path}")
            return
            
        if not operation.xpath:
            # Replace entire file
            result.current_content = operation.content
            console.print(f'[green]Replaced entire content of {result.path}[/green]')
            return
            
        target_type = operation.attributes.get('target_type')
        
        if target_type == 'class':
            class_name = operation.attributes.get('class_name')
            if not class_name:
                operation.add_error("Class name is missing")
                return
                
            result.current_content = manipulator.replace_class(
                result.current_content, class_name, operation.content
            )
            console.print(f'[green]Updated class {class_name} in {result.path}[/green]')
            
        elif target_type == 'method':
            class_name = operation.attributes.get('class_name')
            method_name = operation.attributes.get('method_name')
            
            if not class_name or not method_name:
                operation.add_error("Class name or method name is missing")
                return
                
            result.current_content = manipulator.replace_method(
                result.current_content, class_name, method_name, operation.content
            )
            console.print(f'[green]Updated method {class_name}.{method_name} in {result.path}[/green]')
            
        elif target_type == 'function':
            function_name = operation.attributes.get('function_name')
            
            if not function_name:
                operation.add_error("Function name is missing")
                return
                
            result.current_content = manipulator.replace_function(
                result.current_content, function_name, operation.content
            )
            console.print(f'[green]Updated function {function_name} in {result.path}[/green]')
            
        else:
            operation.add_error(f"Unknown target type: {target_type}")