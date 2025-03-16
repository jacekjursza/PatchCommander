def normalize_line_endings(content):
    if not content:
        return content
    normalized = content.replace('\r\n', '\n').replace('\r', '\n')
    while '\n\n\n' in normalized:
        normalized = normalized.replace('\n\n\n', '\n\n')
    return normalized

def normalize_indentation(text):
    """
    Normalize indentation in input text to improve processing.
    
    This detects and removes common leading whitespace from all lines,
    which is especially helpful when working with triple-quoted strings
    in Python where the indentation of the string literal might not match
    the desired indentation of the content.
    """
    if not text:
        return text
        
    lines = text.splitlines()
    if not lines:
        return text
        
    # Find minimum indentation (excluding empty lines)
    non_empty_lines = [line for line in lines if line.strip()]
    if not non_empty_lines:
        return text
        
    min_indent = min(len(line) - len(line.lstrip()) for line in non_empty_lines)
    
    if min_indent == 0:
        return text
        
    # Remove common indentation
    normalized_lines = []
    for line in lines:
        if line.strip():
            normalized_lines.append(line[min_indent:])
        else:
            normalized_lines.append(line)
            
    return '\n'.join(normalized_lines)