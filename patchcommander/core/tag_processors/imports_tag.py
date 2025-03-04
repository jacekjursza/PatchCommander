"""
Processor for IMPORTS tags.
"""
import re

from patchcommander.core.changes import change_manager
from patchcommander.core.confirmations import confirm_and_apply_change
from patchcommander.core.tag_processors.base import TagProcessor


class ImportsTagProcessor(TagProcessor):
    """Processor for IMPORTS tags."""

    def process(self) -> bool:
        """
        Process an IMPORTS tag by updating or adding import statements to a file.
        Combines existing imports with new ones, removes duplicates, and sorts them.
        Preserves local imports inside functions and methods.

        Returns:
            bool: True if processing was successful, False otherwise
        """
        file_path = self.tag.get_attribute('path')
        content = self.tag.content or ''
        file_path = self._sanitize_path(file_path)

        if not self._validate_file_path(file_path):
            return False

        # Get existing file content
        original_code = change_manager.get_file_content(file_path)
        if not original_code:
            # File doesn't exist, create a new one with just these imports
            change_manager.in_memory_files[file_path] = content
            return confirm_and_apply_change(
                file_path, content, f"Create new file with imports", change_manager.pending_changes
            )

        # Extract only module-level import statements from the original code
        original_imports, module_level_import_positions = self._extract_module_level_imports(original_code)

        # Extract all import statements from the new content
        new_imports = [imp.strip() for imp in content.split('\n') if imp.strip()]

        # Merge, deduplicate and sort imports
        merged_imports = self._merge_and_sort_imports(original_imports, new_imports)

        # Create merged imports string
        merged_imports_str = "\n".join(merged_imports)

        # Handle replacement based on existing imports
        if module_level_import_positions:
            # Get the start of the first import and end of the last import
            import_section_start = module_level_import_positions[0][0]
            import_section_end = module_level_import_positions[-1][1]

            # Replace the existing import section
            new_code = original_code[:import_section_start] + merged_imports_str + original_code[import_section_end:]
        else:
            # Check if there's a module docstring at the beginning
            docstring_match = re.match(r'^(""".*?"""|\'\'\'.*?\'\'\')', original_code, re.DOTALL)

            if docstring_match:
                # Insert imports after the docstring
                insert_pos = docstring_match.end()
                # Add appropriate spacing
                if not original_code[insert_pos:].startswith('\n\n'):
                    if original_code[insert_pos:].startswith('\n'):
                        merged_imports_str = "\n" + merged_imports_str
                    else:
                        merged_imports_str = "\n\n" + merged_imports_str
                # Make sure there's a blank line after imports if needed
                if not merged_imports_str.endswith('\n\n'):
                    if not merged_imports_str.endswith('\n'):
                        merged_imports_str += '\n'
                    if not original_code[insert_pos:].startswith('\n'):
                        merged_imports_str += '\n'

                new_code = original_code[:insert_pos] + merged_imports_str + original_code[insert_pos:]
            else:
                # Insert imports at the beginning
                # Make sure there's a blank line after imports if needed
                if not merged_imports_str.endswith('\n\n'):
                    if not merged_imports_str.endswith('\n'):
                        merged_imports_str += '\n'
                    if not original_code.startswith('\n'):
                        merged_imports_str += '\n'

                new_code = merged_imports_str + original_code

        # Store changes and confirm with user
        change_manager.in_memory_files[file_path] = new_code
        return confirm_and_apply_change(
            file_path, new_code, "Update imports", change_manager.pending_changes
        )

    def _extract_module_level_imports(self, code):
        """
        Extract only module-level import statements from code.

        Args:
            code (str): The code to analyze

        Returns:
            tuple: (list of import statements, list of (start, end) positions)
        """
        lines = code.split('\n')
        imports = []
        positions = []

        # Track indentation level to identify module-level statements
        in_function_or_class = False
        in_docstring = False
        triple_quote = None

        # First pass: identify lines within function/class definitions or docstrings
        non_module_level_lines = set()
        current_indent = 0

        for i, line in enumerate(lines):
            stripped_line = line.strip()

            # Skip empty lines
            if not stripped_line:
                continue

            # Check for docstring start/end
            if not in_docstring and (stripped_line.startswith('"""') or stripped_line.startswith("'''")):
                in_docstring = True
                triple_quote = '"""' if stripped_line.startswith('"""') else "'''"
                # Check if docstring ends on the same line
                if stripped_line.endswith(triple_quote) and len(stripped_line) > 3:
                    in_docstring = False
                    triple_quote = None
            elif in_docstring and triple_quote and stripped_line.endswith(triple_quote):
                in_docstring = False
                triple_quote = None

            # Skip lines in docstrings
            if in_docstring:
                non_module_level_lines.add(i)
                continue

            # Check indentation for function/class scope
            indent = len(line) - len(line.lstrip())

            # If line starts with def/class and is at module level, it begins a new scope
            if not in_function_or_class and (stripped_line.startswith('def ') or stripped_line.startswith('class ')):
                in_function_or_class = True
                current_indent = indent
                non_module_level_lines.add(i)
            # If we're in a function/class and the indent is greater or equal, it's inside
            elif in_function_or_class:
                if indent >= current_indent:
                    non_module_level_lines.add(i)
                else:
                    in_function_or_class = False
                    # Check if this line begins a new function/class
                    if stripped_line.startswith('def ') or stripped_line.startswith('class '):
                        in_function_or_class = True
                        current_indent = indent
                        non_module_level_lines.add(i)

        # Second pass: collect module-level imports
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip if this line is not at module level
            if i in non_module_level_lines:
                i += 1
                continue

            # Check for import statements
            if line.startswith('import ') or line.startswith('from '):
                # Capture start position (in chars)
                start_pos = sum(len(lines[j]) + 1 for j in range(i))

                # Handle multiline imports
                import_stmt = [lines[i]]
                if line.endswith('\\') or ('(' in line and ')' not in line):
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j]
                        import_stmt.append(next_line)
                        if ')' in next_line or not (next_line.strip().endswith('\\') or ('(' in next_line and ')' not in next_line)):
                            break
                        j += 1
                    i = j  # Skip processed lines

                # Calculate end position (in chars)
                end_pos = start_pos + sum(len(line) + 1 for line in import_stmt) - 1

                # Add to results
                imports.append('\n'.join(import_stmt))
                positions.append((start_pos, end_pos))

            i += 1

        return imports, positions

    def _merge_and_sort_imports(self, original_imports, new_imports):
        """
        Merge two lists of imports, remove duplicates, and sort them.

        Args:
            original_imports (list): List of existing imports
            new_imports (list): List of new imports

        Returns:
            list: Sorted list of unique imports
        """
        # Combine all imports
        all_imports = []
        for imp in original_imports + new_imports:
            # Clean up each import statement
            cleaned_imp = imp.strip()
            if cleaned_imp:
                all_imports.append(cleaned_imp)

        # Remove duplicates while preserving order
        unique_imports = []
        seen = set()
        for imp in all_imports:
            normalized_imp = re.sub(r'\s+', ' ', imp)  # Normalize whitespace for comparison
            if normalized_imp not in seen:
                seen.add(normalized_imp)
                unique_imports.append(imp)  # Use original formatting

        # Separate regular imports and from imports
        regular_imports = sorted([imp for imp in unique_imports if imp.startswith('import ')])
        from_imports = sorted([imp for imp in unique_imports if imp.startswith('from ')])

        # Return combined list: regular imports first, then from imports
        return regular_imports + from_imports