from rich.console import Console
from . import register_processor
from .base_manipulator_processor import BaseManipulatorProcessor
from ..models import PatchOperation, PatchResult
from ...config import config
from ...utils.class_extractor import get_class_feature_extractor
from ...languages import get_language_for_file

console = Console()

@register_processor(priority=5)
class SmartManipulatorProcessor(BaseManipulatorProcessor):
    MERGE_STRATEGIES = {'Smart Merge (fields + methods with intelligent merging)': 'smart', 'Replace Class (completely replace with new version)': 'replace'}

    def can_handle(self, operation: PatchOperation) -> bool:
        return (operation.name == 'FILE' and 
                operation.attributes.get('target_type') == 'class' and 
                operation.attributes.get('target_type') != 'lines')

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        class_name = operation.attributes.get('class_name')
        if not class_name:
            operation.add_error('Class name is missing')
            return
        console.print(f'[blue]SmartManipulatorProcessor: Processing class {class_name}[/blue]')
        manipulator = self.get_manipulator_for_operation(operation)
        if not manipulator:
            operation.add_error(f'No manipulator available for operation on {operation.path}')
            return
        if not result.current_content or class_name not in result.current_content:
            console.print(f"[yellow]Class '{class_name}' not found, creating new class[/yellow]")
            if result.current_content:
                separator = '\n\n' if not result.current_content.endswith('\n\n') else ''
                result.current_content = result.current_content + separator + operation.content
            else:
                result.current_content = operation.content
            return
        try:
            # Determine the language of the file
            language = operation.attributes.get('language')
            if not language:
                language = get_language_for_file(operation.path)
                operation.attributes['language'] = language
            
            # Get the appropriate extractor for this language
            try:
                extractor = get_class_feature_extractor(language)
            except ValueError:
                console.print(f"[yellow]No class feature extractor available for language: {language}. Using simple replacement.[/yellow]")
                result.current_content = manipulator.replace_class(result.current_content, class_name, operation.content)
                return
            
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
            lines = result.current_content.splitlines(True)
            start_byte = sum((len(lines[i]) for i in range(start_line - 1)))
            end_byte = sum((len(lines[i]) for i in range(end_line)))
            original_class_code = result.current_content[start_byte:end_byte]
            
            # Use the extractor to analyze the classes
            original_features = extractor.extract_features_from_code(original_class_code)
            new_features = extractor.extract_features_from_code(operation.content)
            
            if not original_features or not new_features:
                console.print(f"[yellow]Couldn't extract class features, using simple replacement[/yellow]")
                result.current_content = manipulator.replace_class(result.current_content, class_name, operation.content)
                return
                
            # Compare features and determine if merging is needed
            diff = extractor.diff_features(original_features, new_features)
            
            if config.get('default_yes_to_all', False):
                console.print('[blue]Using Smart Merge strategy due to auto-approval[/blue]')
                (merged_code, _) = extractor.merge_classes(original_class_code, operation.content)
                result.current_content = manipulator.replace_class(result.current_content, class_name, merged_code)
                console.print(f'[green]Successfully merged class {class_name} using smart merge[/green]')
                return
                
            if diff.has_significant_changes or diff.added_methods or diff.removed_methods or diff.modified_methods:
                class_info = {'class_name': class_name, 'original_code': original_class_code, 'new_code': operation.content, 'original_features': original_features, 'new_features': new_features, 'strategies': self.MERGE_STRATEGIES}
                (smart_merged_code, _) = extractor.merge_classes(original_class_code, operation.content)
                temp_result = manipulator.replace_class(result.current_content, class_name, smart_merged_code)
                from patchcommander.diff_viewer import show_interactive_diff
                interactive_result = show_interactive_diff(result.current_content, temp_result, result.path, errors=result.errors, class_info=class_info, processor_name='SmartManipulatorProcessor')
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
                
            console.print('[blue]Using Smart Merge strategy for simple changes[/blue]')
            (merged_code, _) = extractor.merge_classes(original_class_code, operation.content)
            result.current_content = manipulator.replace_class(result.current_content, class_name, merged_code)
            console.print(f'[green]Successfully merged class {class_name} using smart merge[/green]')
        except Exception as e:
            operation.add_error(f'Error during smart class processing: {str(e)}')
            import traceback
            console.print(f'[dim]{traceback.format_exc()}[/dim]')