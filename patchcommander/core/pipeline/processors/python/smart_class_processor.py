"""
Smart processor for handling class merging with feature extraction.
"""
import re

from rich.console import Console

from .base import PythonProcessor
from ..decorator import register_processor
from ...models import PatchOperation, PatchResult
from .....core.utils.class_extractor import ClassFeatureExtractor

console = Console()

@register_processor(priority=5)
class SmartClassProcessor(PythonProcessor):
    """
    Processor that uses ClassFeatureExtractor to intelligently merge class fields
    with existing methods.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.

        Args:
            operation: The operation to check

        Returns:
            bool: True if it's a Python class operation
        """
        return (super().can_handle(operation) and
                operation.attributes.get('target_type') == 'class')

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Processes a class operation, smartly merging with existing class if present.

        Args:
            operation: The operation to process
            result: The result to update
        """
        class_name = operation.attributes.get('class_name')
        if not class_name:
            operation.add_error('Class name is missing')
            return

        console.print(f'[blue]SmartClassProcessor: Processing class {class_name}[/blue]')

        # Handle empty file or no existing class case
        if not result.current_content or class_name not in result.current_content:
            console.print(f"[yellow]Class '{class_name}' not found, creating new class[/yellow]")
            if result.current_content:
                separator = "\n\n" if not result.current_content.endswith("\n\n") else ""
                result.current_content = result.current_content + separator + operation.content
            else:
                result.current_content = operation.content
            return

        try:
            # Extract the original class using the proper parser approach
            parser = self._get_parser()
            tree = parser.parse(result.current_content)
            target_class = None
            
            # Find the class using tree-sitter
            classes = tree.find_classes()
            for cls in classes:
                for child in cls.get_children():
                    if child.get_type() == 'identifier' and child.get_text() == class_name:
                        target_class = cls
                        break
                if target_class:
                    break
                    
            if target_class:
                # Extract the class text based on tree-sitter node
                start_byte = target_class.ts_node.start_byte
                end_byte = target_class.ts_node.end_byte
                original_class_code = result.current_content[start_byte:end_byte]
                
                # Use ClassFeatureExtractor for smart merging
                merged_code, needs_confirmation = ClassFeatureExtractor.merge_classes(
                    original_class_code, operation.content)
                
                if needs_confirmation:
                    console.print(f"[yellow]Warning: Significant changes detected in class '{class_name}'[/yellow]")
                    console.print("[yellow]Some methods might have been intentionally removed.[/yellow]")
                
                # Replace the class using exact boundaries from tree-sitter
                result.current_content = (
                    result.current_content[:start_byte] +
                    merged_code +
                    result.current_content[end_byte:]
                )
                console.print(f'[green]Successfully merged class {class_name} using tree-sitter[/green]')
            else:
                # Fallback to traditional approach if tree-sitter doesn't find the class
                console.print(f"[yellow]Could not find class {class_name} using tree-sitter, trying regex fallback[/yellow]")
                original_class_code = ClassFeatureExtractor.find_class_in_code(
                    result.current_content, class_name)
                
                if not original_class_code:
                    console.print(f"[yellow]Could not extract '{class_name}' from file using any method[/yellow]")
                    separator = "\n\n" if not result.current_content.endswith("\n\n") else ""
                    result.current_content = result.current_content + separator + operation.content
                    return
                    
                merged_code, needs_confirmation = ClassFeatureExtractor.merge_classes(
                    original_class_code, operation.content)
                
                pattern = rf'(class\s+{re.escape(class_name)}\s*(?:\([^)]*\))?\s*:.*?)(?:\n\s*class|\Z)'
                result.current_content = re.sub(
                    pattern, merged_code, result.current_content, flags=re.DOTALL)
                console.print(f'[green]Merged class {class_name} using regex fallback[/green]')
                
        except Exception as e:
            operation.add_error(f'Error during smart class processing: {str(e)}')
            import traceback
            console.print(f'[dim]{traceback.format_exc()}[/dim]')
            
            # Fallback to standard replacement
            console.print(f"[yellow]Falling back to standard class replacement due to error[/yellow]")
            try:
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
                        
                if target_class:
                    start_byte = target_class.ts_node.start_byte
                    end_byte = target_class.ts_node.end_byte
                    result.current_content = (
                        result.current_content[:start_byte] +
                        operation.content +
                        result.current_content[end_byte:]
                    )
                    console.print(f'[green]Updated class {class_name} using fallback method[/green]')
                else:
                    # Append as last resort
                    separator = "\n\n" if result.current_content and not result.current_content.endswith("\n\n") else ""
                    result.current_content = result.current_content + separator + operation.content
                    console.print(f'[green]Added new class {class_name} using fallback method[/green]')
            except Exception as inner_e:
                operation.add_error(f'Error during fallback processing: {str(inner_e)}')
                console.print(f'[red]Error in fallback processing: {str(inner_e)}[/red]')
                separator = "\n\n" if result.current_content and not result.current_content.endswith("\n\n") else ""
                result.current_content = result.current_content + separator + operation.content