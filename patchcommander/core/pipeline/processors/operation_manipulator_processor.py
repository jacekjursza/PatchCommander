from rich.console import Console

from . import register_processor
from ..processor_base import Processor
from ..models import PatchOperation, PatchResult
from .base_manipulator_processor import BaseManipulatorProcessor


console = Console()

@register_processor(priority=10)
class OperationManipulatorProcessor(BaseManipulatorProcessor):
    """
    Processor that handles OPERATION actions using the appropriate code manipulator
    based on the file type. This replaces the old OperationProcessor with more
    structured manipulation.
    """
    
    def can_handle(self, operation: PatchOperation) -> bool:
        return operation.name == 'OPERATION'
    
    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        action = operation.action
        
        if not action:
            operation.add_error('No action specified for OPERATION')
            return
            
        if action == 'move_file':
            self._handle_move_file(operation, result)
        elif action == 'delete_file':
            self._handle_delete_file(operation, result)
        elif action == 'delete_method':
            self._handle_delete_method(operation, result)
        elif action == 'add_method':
            self._handle_add_method(operation, result)
        else:
            operation.add_error(f'Unknown action: {action}')
    
    def _handle_move_file(self, operation: PatchOperation, result: PatchResult) -> None:
        source = operation.attributes.get('source')
        target = operation.attributes.get('target')
        
        if not source or not target:
            operation.add_error("move_file operation requires 'source' and 'target' attributes")
            return
            
        if result.path == source:
            result.current_content = ''
            result.attributes = result.attributes or {}
            result.attributes['target_path'] = target
            console.print(f'[green]File will be moved from {source} to {target}[/green]')
    
    def _handle_delete_file(self, operation: PatchOperation, result: PatchResult) -> None:
        source = operation.attributes.get('source')
        
        if not source:
            operation.add_error("delete_file operation requires 'source' attribute")
            return
            
        if result.path == source:
            result.current_content = ''
            result.attributes = result.attributes or {}
            result.attributes['should_delete'] = True
            console.print(f'[green]File {source} will be deleted[/green]')
    
    def _handle_delete_method(self, operation: PatchOperation, result: PatchResult) -> None:
        source = operation.attributes.get('source')
        class_name = operation.attributes.get('class')
        method_name = operation.attributes.get('method')
        
        if not source or not class_name or not method_name:
            operation.add_error("delete_method operation requires 'source', 'class', and 'method' attributes")
            return
            
        if result.path != source:
            return
            
        manipulator = self.get_manipulator_for_operation(operation)
        
        if not manipulator:
            operation.add_error(f"No manipulator available for operation on {operation.path}")
            return
            
        result.current_content = manipulator.remove_method_from_class(
            result.current_content, class_name, method_name
        )
        console.print(f'[green]Removed method {class_name}.{method_name} from {source}[/green]')
    
    def _handle_add_method(self, operation: PatchOperation, result: PatchResult) -> None:
        source = operation.attributes.get('source')
        class_name = operation.attributes.get('class')
        method_code = operation.content
        
        if not source or not class_name or not method_code:
            operation.add_error("add_method operation requires 'source', 'class', and method content")
            return
            
        if result.path != source:
            return
            
        manipulator = self.get_manipulator_for_operation(operation)
        
        if not manipulator:
            operation.add_error(f"No manipulator available for operation on {operation.path}")
            return
            
        result.current_content = manipulator.add_method_to_class(
            result.current_content, class_name, method_code
        )
        console.print(f'[green]Added new method to class {class_name} in {source}[/green]')