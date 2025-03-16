from rich.console import Console

from . import register_processor
from .base_manipulator_processor import BaseManipulatorProcessor
from ..models import PatchOperation, PatchResult
from ...config import config
from ...utils.class_extractor import ClassFeatureExtractor

console = Console()

@register_processor(priority=5)
class SmartManipulatorProcessor(BaseManipulatorProcessor):
    """
    Smart processor for class operations that uses intelligent merging
    while leveraging the base manipulators for core functionality.
    """
    MERGE_STRATEGIES = {
        'Smart Merge (fields + methods with intelligent merging)': 'smart',
        'Replace Class (completely replace with new version)': 'replace'
    }

    def can_handle(self, operation: PatchOperation) -> bool:
        # Only handle class operations for now
        return (operation.name == 'FILE' and 
                operation.attributes.get('target_type') == 'class')

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        class_name = operation.attributes.get('class_name')
        if not class_name:
            operation.add_error('Class name is missing')
            return

        console.print(f'[blue]SmartManipulatorProcessor: Processing class {class_name}[/blue]')
        
        # Use the manipulator to find the class
        manipulator = self.get_manipulator_for_operation(operation)
        if not manipulator:
            operation.add_error(f"No manipulator available for operation on {operation.path}")
            return
            
        # If the file doesn't exist or class isn't found, just create it
        if not result.current_content or class_name not in result.current_content:
            console.print(f"[yellow]Class '{class_name}' not found, creating new class[/yellow]")
            if result.current_content:
                separator = '\n\n' if not result.current_content.endswith('\n\n') else ''
                result.current_content = result.current_content + separator + operation.content
            else:
                result.current_content = operation.content
            return

        try:
            # Extract the class using our manipulator
            # First find the class boundaries
            finder = manipulator.finder
            (start_line, end_line) = finder.find_class(result.current_content, class_name)
            
            if start_line == 0 and end_line == 0:
                console.print(f"[yellow]Class '{class_name}' not found using finder, creating new class[/yellow]")
                if result.current_content:
                    separator = '\n\n' if not result.current_content.endswith('\n\n') else ''
                    result.current_content = result.current_content + separator + operation.content
                else:
                    result.current_content = operation.content
                return
                
            # Calculate byte positions from line numbers
            lines = result.current_content.splitlines(True)  # Keep line endings
            start_byte = sum(len(lines[i]) for i in range(start_line - 1))
            end_byte = sum(len(lines[i]) for i in range(end_line))
            
            # Extract the class code
            original_class_code = result.current_content[start_byte:end_byte]
            
            # Use ClassFeatureExtractor for analysis
            original_features = ClassFeatureExtractor.extract_features_from_code(original_class_code)
            new_features = ClassFeatureExtractor.extract_features_from_code(operation.content)
            
            if not original_features or not new_features:
                console.print(f"[yellow]Couldn't extract class features, using simple replacement[/yellow]")
                result.current_content = manipulator.replace_class(
                    result.current_content, class_name, operation.content
                )
                return
                
            diff = ClassFeatureExtractor.diff_features(original_features, new_features)
            
            # Auto-approve if configured
            if config.get('default_yes_to_all', False):
                console.print('[blue]Using Smart Merge strategy due to auto-approval[/blue]')
                (merged_code, _) = ClassFeatureExtractor.merge_classes(original_class_code, operation.content)
                result.current_content = manipulator.replace_class(
                    result.current_content, class_name, merged_code
                )
                console.print(f'[green]Successfully merged class {class_name} using smart merge[/green]')
                return
                
            # Show interactive diff if there are significant changes
            if (diff.has_significant_changes or diff.added_methods or 
                diff.removed_methods or diff.modified_methods):
                # Prepare the class info for the diff viewer
                class_info = {
                    'class_name': class_name,
                    'original_code': original_class_code,
                    'new_code': operation.content,
                    'original_features': original_features,
                    'new_features': new_features,
                    'strategies': self.MERGE_STRATEGIES
                }
                
                # Generate a smart-merged version for preview
                (smart_merged_code, _) = ClassFeatureExtractor.merge_classes(
                    original_class_code, operation.content
                )
                
                # Create a temporary result with the smart merge applied
                temp_result = manipulator.replace_class(
                    result.current_content, class_name, smart_merged_code
                )
                
                # Show the interactive diff
                from patchcommander.diff_viewer import show_interactive_diff
                interactive_result = show_interactive_diff(
                    result.current_content, temp_result, result.path,
                    errors=result.errors, class_info=class_info,
                    processor_name='SmartManipulatorProcessor'
                )
                
                # Process the result
                if isinstance(interactive_result, tuple) and len(interactive_result) == 2:
                    (decision, updated_content) = interactive_result
                    if decision == 'yes':
                        result.approved = True
                        result.current_content = updated_content
                    else:
                        result.approved = False
                elif interactive_result == 'yes':
                    result.approved = True
                    result.current_content = temp_result
                else:
                    result.approved = False
                return
                
            # For simple changes, use Smart Merge automatically
            console.print('[blue]Using Smart Merge strategy for simple changes[/blue]')
            (merged_code, _) = ClassFeatureExtractor.merge_classes(
                original_class_code, operation.content
            )
            result.current_content = manipulator.replace_class(
                result.current_content, class_name, merged_code
            )
            console.print(f'[green]Successfully merged class {class_name} using smart merge[/green]')
            
        except Exception as e:
            operation.add_error(f'Error during smart class processing: {str(e)}')
            import traceback
            console.print(f'[dim]{traceback.format_exc()}[/dim]')