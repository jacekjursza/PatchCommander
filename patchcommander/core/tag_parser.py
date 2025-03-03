"""
Tag parser for PatchCommander v2.
Handles parsing of XML-like tags from input text.
"""
import re
from typing import Dict, List, Tuple, Optional, Any
from rich.console import Console

console = Console()

# Tag types
TAG_TYPES = ['FILE', 'CLASS', 'METHOD', 'FUNCTION', 'OPERATION']

class Tag:
    """Represents a parsed tag from input text."""

    def __init__(self, tag_type: str, attributes: Dict[str, str], content: Optional[str] = None):
        """
        Initialize a Tag object.

        Args:
            tag_type: Type of the tag (FILE, CLASS, etc.)
            attributes: Dictionary of tag attributes
            content: Content inside the tag or None for self-closing tags
        """
        self.tag_type = tag_type
        self.attributes = attributes
        self.content = content

    def __str__(self) -> str:
        """String representation of the tag."""
        attrs_str = ' '.join(f'{k}="{v}"' for k, v in self.attributes.items())
        if attrs_str:
            attrs_str = ' ' + attrs_str

        if self.content is None:
            return f"<{self.tag_type}{attrs_str} />"
        else:
            return f"<{self.tag_type}{attrs_str}>{self.content}</{self.tag_type}>"

    def get_attribute(self, name: str, default: Any = None) -> Any:
        """
        Get attribute value by name.

        Args:
            name: Attribute name
            default: Default value to return if attribute doesn't exist

        Returns:
            Attribute value or default
        """
        return self.attributes.get(name, default)


def parse_attributes(attr_str: str) -> Dict[str, str]:
    """
    Parse HTML/XML-like attribute string into a dictionary.

    Args:
        attr_str: String containing attributes in format: key="value" key2="value2"

    Returns:
        Dictionary of attribute key-value pairs
    """
    if not attr_str:
        return {}

    attrs = {}
    pattern = r'(\w+)\s*=\s*"([^"]*)"'

    for match in re.finditer(pattern, attr_str):
        key, value = match.groups()
        attrs[key] = value

    return attrs


def parse_tags(input_text: str) -> List[Tag]:
    """
    Parse all tags from input text.

    Args:
        input_text: Input text containing tags

    Returns:
        List of parsed Tag objects
    """
    tags = []

    # Regex for matching tags
    # This matches both normal tags <TAG>content</TAG> and self-closing tags <TAG />
    tag_pattern = re.compile(
        r'<(FILE|CLASS|METHOD|FUNCTION|OPERATION)(\s+[^>]*)?\s*(?:>(.*?)</\1\s*>|/>)',
        re.DOTALL
    )

    for match in tag_pattern.finditer(input_text):
        tag_type = match.group(1)
        attr_str = match.group(2) or ''
        content = match.group(3)  # Will be None for self-closing tags

        # Parse attributes
        attributes = parse_attributes(attr_str)

        # Create tag object
        tag = Tag(tag_type, attributes, content)
        tags.append(tag)

    return tags


def count_tags_by_type(tags: List[Tag]) -> Dict[str, int]:
    """
    Count the number of tags by type.

    Args:
        tags: List of Tag objects

    Returns:
        Dictionary with counts by tag type
    """
    counts = {tag_type: 0 for tag_type in TAG_TYPES}

    for tag in tags:
        if tag.tag_type in counts:
            counts[tag.tag_type] += 1

    return counts


def validate_tag(tag: Tag) -> Tuple[bool, Optional[str]]:
    """
    Validate a tag for required attributes.

    Args:
        tag: Tag to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required attributes for each tag type
    if tag.tag_type == 'FILE':
        if 'path' not in tag.attributes:
            return False, "FILE tag requires 'path' attribute"

    elif tag.tag_type == 'CLASS':
        if 'path' not in tag.attributes:
            return False, "CLASS tag requires 'path' attribute"

    elif tag.tag_type == 'METHOD':
        if 'path' not in tag.attributes:
            return False, "METHOD tag requires 'path' attribute"
        if 'class' not in tag.attributes:
            return False, "METHOD tag requires 'class' attribute"

    elif tag.tag_type == 'FUNCTION':
        if 'path' not in tag.attributes:
            return False, "FUNCTION tag requires 'path' attribute"

    elif tag.tag_type == 'OPERATION':
        if 'action' not in tag.attributes:
            return False, "OPERATION tag requires 'action' attribute"

        action = tag.attributes['action']
        if action == 'move_file':
            if 'source' not in tag.attributes:
                return False, "move_file operation requires 'source' attribute"
            if 'target' not in tag.attributes:
                return False, "move_file operation requires 'target' attribute"

        elif action == 'delete_file':
            if 'source' not in tag.attributes:
                return False, "delete_file operation requires 'source' attribute"

        elif action == 'delete_method':
            if 'source' not in tag.attributes:
                return False, "delete_method operation requires 'source' attribute"
            if 'class' not in tag.attributes:
                return False, "delete_method operation requires 'class' attribute"
            if 'method' not in tag.attributes:
                return False, "delete_method operation requires 'method' attribute"

        else:
            return False, f"Unknown operation action: {action}"

    return True, None