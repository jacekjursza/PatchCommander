
"""
Preprocessor for splitting multiple methods in a single METHOD tag.
"""
import re
from patchcommander.core.input_preprocessors.base import InputPreprocessor
from patchcommander.core.console import console

class MultipleMethodsSplitter(InputPreprocessor):
    """Preprocessor that splits multiple method definitions in a single METHOD tag."""
    
    def process(self, input_text):
        """
        Split multiple methods within a single METHOD tag into separate METHOD tags.
        
        Args:
            input_text: Raw input text

        Returns:
            Processed text with multiple methods split into separate tags
        """
        # Pattern to match METHOD tags with their attributes and content
        pattern = r'<METHOD\s+([^>]+)>(.*?)</METHOD>'

        def replace_method_tag(match):
            attributes = match.group(1)
            content = match.group(2)

            # Check if there are multiple method definitions in the content
            method_defs = self._split_methods(content)

            if len(method_defs) <= 1:
                # If there's only one method or no methods, return the original tag
                return match.group(0)

            # Build separate tags for each method definition
            result = []
            for method_def in method_defs:
                if method_def.strip():  # Skip empty method definitions
                    # Add proper line breaks before and after the method content
                    formatted_method = f'\n{method_def.strip()}\n'
                    result.append(f'<METHOD {attributes}>{formatted_method}</METHOD>')

            if len(method_defs) > 1:
                console.print(f"[yellow]Preprocessor: Split {len(method_defs)} methods into separate METHOD tags.[/yellow]")

            return '\n\n'.join(result)

        # Apply the replacement on the entire input
        return re.sub(pattern, replace_method_tag, input_text, flags=re.DOTALL)
    
    def _split_methods(self, content):
        """
        Split content into separate method definitions.
        
        Args:
            content: Content of a METHOD tag

        Returns:
            List of method definitions
        """
        # First, normalize line endings and remove any extra blank lines
        normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
        while '\n\n\n' in normalized_content:
            normalized_content = normalized_content.replace('\n\n\n', '\n\n')

        # Pattern to match Python method definitions with decorators
        # This regex captures:
        # 1. Optional decorators (one or more lines starting with @)
        # 2. Function definition line (def name(params):)
        # 3. Function body until the next definition or decorator
        pattern = r'((?:(?:^|\n)\s*@[^\n]+\n)*\s*def\s+\w+\s*\([^)]*\):(?:(?!\n\s*(?:def\s|\s*@))[\s\S])*)'

        # Find all method definitions
        matches = re.findall(pattern, normalized_content)

        # If no matches found or if there's just one that is essentially the same as the input, return the original
        if not matches or (len(matches) == 1 and matches[0].strip() == normalized_content.strip()):
            return [normalized_content]

        # Clean up the matches
        cleaned_matches = [match.strip() for match in matches if match.strip()]

        # Verify that we're not missing content
        all_content = '\n\n'.join(cleaned_matches)
        # Compare ignoring whitespace differences
        original_no_whitespace = re.sub(r'\s+', '', normalized_content)
        matches_no_whitespace = re.sub(r'\s+', '', all_content)

        if original_no_whitespace != matches_no_whitespace:
            # We might be missing some content, better to return the original
            console.print("[yellow]Warning: Unable to safely split methods. Keeping original tag.[/yellow]")
            return [normalized_content]

        return cleaned_matches
