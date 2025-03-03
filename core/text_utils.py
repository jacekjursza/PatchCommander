"""
Text utilities for processing code and other text content.
"""

def normalize_line_endings(content):
    """
    Normalizes line endings in a string to Unix-style line feeds (LF).
    This helps prevent the multiplication of line endings when processing files.

    Args:
        content (str): The content to normalize

    Returns:
        str: Content with normalized line endings
    """
    if not content:
        return content

    # Replace CRLF and CR with LF
    normalized = content.replace('\r\n', '\n').replace('\r', '\n')

    # Remove excessive blank lines (more than 2 consecutive newlines)
    while '\n\n\n' in normalized:
        normalized = normalized.replace('\n\n\n', '\n\n')

    return normalized