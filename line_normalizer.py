def normalize_line_endings(content):
    """
    Normalizes line endings in a string to Unix-style line feeds (\n).
    This helps prevent the multiplication of line endings when processing files.

    Args:
        content (str): The content to normalize

    Returns:
        str: Content with normalized line endings
    """
    if not content:
        return content

    # First, normalize all line endings to \n
    # This handles \r\n (Windows) and \r (old Mac) by converting them to \n
    normalized = content.replace('\r\n', '\n').replace('\r', '\n')

    # Then remove any consecutive newlines that may have been created
    while '\n\n\n' in normalized:
        normalized = normalized.replace('\n\n\n', '\n\n')

    return normalized