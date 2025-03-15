"""
Smart processor for handling class merging with feature extraction.
"""
import re
from typing import Optional, Tuple, Dict, Any, List

import rich
from rich.console import Console
from rich.prompt import Prompt
from ..decorator import register_processor
from .base import PythonProcessor
from ...models import PatchOperation, PatchResult
from .....core.utils.class_extractor import ClassFeatureExtractor, ClassFeatures
from .....core.config import config
console = Console()

@register_processor(priority=5)
class SmartClassProcessor(PythonProcessor):
    """
    Processor that uses ClassFeatureExtractor to intelligently merge class fields
    with existing methods.
    """
    MERGE_STRATEGIES = {
        'Smart Merge (fields + methods with intelligent merging)': 'smart',
        'Replace Class (completely replace with new version)': 'replace',
    }

    def can_handle(self, operation: PatchOperation) -> bool:
        return super().can_handle(operation) and operation.attributes.get('target_type') == 'class'

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        class_name = operation.attributes.get('class_name')
        if not class_name:
            operation.add_error('Class name is missing')
            return
            
        console.print(f'[blue]SmartClassProcessor: Processing class {class_name}[/blue]')
        
        # Handle new file or class not found case
        if not result.current_content or class_name not in result.current_content:
            console.print(f"[yellow]Class '{class_name}' not found, creating new class[/yellow]")
            if result.current_content:
                separator = '\n\n' if not result.current_content.endswith('\n\n') else ''
                result.current_content = result.current_content + separator + operation.content
            else:
                result.current_content = operation.content
            return
            
        try:
            # Find the class in the file
            parser = self._get_parser()
            tree = parser.parse(result.current_content)
            classes = tree.find_classes()
            
            target_class = None
            for cls in classes:
                for child in cls.get_children():
                    if child.get_type() == 'identifier' and child.get_text() == class_name:
                        target_class = cls
                        break
                if target_class:
                    break

            self._handle_class_with_tree_sitter(operation, result, target_class, class_name)

        except Exception as e:
            operation.add_error(f'Error during smart class processing: {str(e)}')
            import traceback
            console.print(f'[dim]{traceback.format_exc()}[/dim]')
            
    def _handle_class_with_tree_sitter(self, operation: PatchOperation, result: PatchResult, target_class, class_name: str) -> None:
        """
        Process class using tree-sitter parser.
        """
        start_byte = target_class.ts_node.start_byte
        end_byte = target_class.ts_node.end_byte
        original_class_code = result.current_content[start_byte:end_byte]
        
        # Extract features
        original_features = ClassFeatureExtractor.extract_features_from_code(original_class_code)
        new_features = ClassFeatureExtractor.extract_features_from_code(operation.content)

        rich.print("ORG:")
        rich.print(original_features)
        rich.print("NEW:")
        rich.print(new_features)

        if not original_features or not new_features:
            console.print(f"[yellow]Couldn't extract class features, using simple replacement[/yellow]")
            result.current_content = result.current_content[:start_byte] + operation.content + result.current_content[end_byte:]
            return
            
        # Analyze differences
        diff = ClassFeatureExtractor.diff_features(original_features, new_features)

        rich.print("DIFF:")
        rich.print(diff)

        # Auto-approve mode
        if config.get('default_yes_to_all', False):
            console.print('[blue]Using Smart Merge strategy due to auto-approval[/blue]')
            merged_code, _ = ClassFeatureExtractor.merge_classes(original_class_code, operation.content)
            result.current_content = result.current_content[:start_byte] + merged_code + result.current_content[end_byte:]
            console.print(f'[green]Successfully merged class {class_name} using smart merge[/green]')
            return
            
        # If significant changes, show interactive diff
        if diff.has_significant_changes or diff.added_methods or diff.removed_methods or diff.modified_methods:
            # Prepare class info for the diff viewer
            class_info = {
                'class_name': class_name,
                'original_code': original_class_code,
                'new_code': operation.content,
                'original_features': original_features,
                'new_features': new_features,
                'strategies': self.MERGE_STRATEGIES
            }
            
            # Create temporary merged content for preview
            smart_merged_code, _ = ClassFeatureExtractor.merge_classes(original_class_code, operation.content)
            temp_result = result.current_content[:start_byte] + smart_merged_code + result.current_content[end_byte:]
            
            # Show interactive diff
            from patchcommander.diff_viewer import show_interactive_diff
            interactive_result = show_interactive_diff(
                result.current_content, 
                temp_result, 
                result.path, 
                errors=result.errors, 
                class_info=class_info, 
                processor_name='SmartClassProcessor'
            )

            rich.print("INTERACTIVE result:")
            rich.print(interactive_result)

            if isinstance(interactive_result, tuple) and len(interactive_result) == 2:
                decision, updated_content = interactive_result
                if decision == 'yes':
                    result.approved = True
                    result.current_content = updated_content
                else:
                    result.approved = False
            else:
                if interactive_result == 'yes':
                    result.approved = True
                    result.current_content = temp_result
                else:
                    result.approved = False
            return
            
        # For simple changes, just use smart merge
        console.print('[blue]Using Smart Merge strategy for simple changes[/blue]')
        merged_code, _ = ClassFeatureExtractor.merge_classes(original_class_code, operation.content)
        result.current_content = result.current_content[:start_byte] + merged_code + result.current_content[end_byte:]
        console.print(f'[green]Successfully merged class {class_name} using smart merge[/green]')