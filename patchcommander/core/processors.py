"""
Tag tag_processors for PatchCommander v2.
Handles processing of different tag types and applying changes.
"""
from typing import List

from patchcommander.core.console import console
from patchcommander.core.tag_processors.class_tag import ClassTagProcessor
from patchcommander.core.tag_processors.file_tag import FileTagProcessor
from patchcommander.core.tag_processors.function_tag import FunctionTagProcessor
from patchcommander.core.tag_processors.method_tag import MethodTagProcessor
from patchcommander.core.tag_processors.imports_tag import ImportsTagProcessor
from patchcommander.core.tag_processors.operation_tag import OperationTagProcessor
from patchcommander.core.changes import change_manager
from patchcommander.core.tag_parser import Tag


def process_tag(tag: Tag) -> bool:
    """
    Process a tag using the appropriate processor.

    Args:
        tag: Tag to process

    Returns:
        bool: True if processing was successful, False otherwise
    """
    if tag.tag_type == 'FILE':
        processor = FileTagProcessor(tag)
    elif tag.tag_type == 'CLASS':
        processor = ClassTagProcessor(tag)
    elif tag.tag_type == 'METHOD':
        processor = MethodTagProcessor(tag)
    elif tag.tag_type == 'FUNCTION':
        processor = FunctionTagProcessor(tag)
    elif tag.tag_type == 'OPERATION':
        processor = OperationTagProcessor(tag)
    elif tag.tag_type == 'IMPORTS':
        processor = ImportsTagProcessor(tag)
    else:
        console.print(f'[bold red]Unknown tag type: {tag.tag_type}[/bold red]')
        return False
    return processor.process()

def process_tags(tags: List[Tag]) -> int:
    """
    Process a list of tags.

    Args:
        tags: List of tags to process

    Returns:
        int: Number of successfully processed tags
    """
    console.print('[bold]Processing tags...[/bold]')
    success_count = 0
    operation_tags = [tag for tag in tags if tag.tag_type == 'OPERATION']
    for tag in operation_tags:
        if process_tag(tag):
            success_count += 1
    other_tags = [tag for tag in tags if tag.tag_type != 'OPERATION']
    for tag in other_tags:
        if process_tag(tag):
            success_count += 1
    change_manager.apply_all_pending_changes()
    return success_count