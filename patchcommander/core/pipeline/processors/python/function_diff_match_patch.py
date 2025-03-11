"""
Python function processor using diff-match-patch.
Fixed for proper decorator handling.
"""
import re
from rich.console import Console
from ..decorator import register_processor
from .base import PythonProcessor
from .base_diff_match_patch import BaseDiffMatchPatchProcessor, DMP_AVAILABLE
from ...models import PatchOperation, PatchResult

console = Console()

@register_processor(priority=4)
class DiffMatchPatchPythonFunctionProcessor(PythonProcessor, BaseDiffMatchPatchProcessor):
    """
    Processor for Python functions using diff-match-patch.
    """

    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Checks if the processor can handle the operation.
        """
        return (
            DMP_AVAILABLE
            and super().can_handle(operation)
            and operation.attributes.get("target_type") == "function"
        )

    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Processes a function operation with proper decorator handling and spacing.
        """
        if not DMP_AVAILABLE:
            operation.add_error("diff-match-patch library is not available")
            return

        function_name = operation.attributes.get("function_name")
        if not function_name:
            operation.add_error("Missing function_name attribute")
            return

        console.print(f"[blue]Processing function {function_name}[/blue]")

        # If the file is empty, simply add the function
        if not result.current_content:
            result.current_content = operation.content
            console.print(
                f"[green]Created new file with function {function_name}[/green]"
            )
            return

        try:
            # Find function pattern with proper handling of decorators
            pattern = f"(^|\\n)([ \\t]*)(async\\s+)?def\\s+{re.escape(function_name)}\\s*\\([^)]*\\)\\s*(->\\s*[^:]+)?\\s*:"
            match = re.search(pattern, result.current_content)

            if not match:
                # Function doesn't exist, add it with proper spacing
                separator = (
                    "\n\n" if not result.current_content.endswith("\n\n") else ""
                )
                if result.current_content.endswith("\n") and (
                    not result.current_content.endswith("\n\n")
                ):
                    separator = "\n"

                result.current_content = (
                    result.current_content + separator + operation.content
                )

                # Ensure there are two newlines after the function, especially if it's not the end of file
                if not result.current_content.endswith("\n\n"):
                    result.current_content = result.current_content + "\n\n"

                console.print(f"[green]Added new function {function_name}[/green]")
                return

            # Function exists, handle replacing it with proper spacing
            indentation = match.group(2)
            func_start = match.start()

            # Look for decorator lines before the function
            pos = func_start - 1
            while pos >= 0:
                line_start = result.current_content.rfind("\n", 0, pos)
                if line_start == -1:
                    line_start = 0
                else:
                    line_start += 1

                line = result.current_content[line_start : pos + 1].strip()
                if line.startswith("@"):
                    line_indent = len(result.current_content[line_start:]) - len(
                        result.current_content[line_start:].lstrip()
                    )
                    if line_indent == len(indentation):
                        func_start = line_start
                        pos = line_start - 1
                        continue
                break

            func_end = match.end()
            rest_of_content = result.current_content[match.end() :]

            # Careful detection of function end by looking for next def/class at same or lower indentation
            next_def_pattern = f"(^|\\n)({re.escape(indentation)}(class|def)\\s+|{re.escape(indentation[:-4] if len(indentation) >= 4 else '')}(class|def)\\s+)"
            next_def_match = re.search(next_def_pattern, rest_of_content)

            if next_def_match:
                func_end += next_def_match.start()
                if next_def_match.group(1) == "\n":
                    func_end += 1
            else:
                func_end = len(result.current_content)

            orig_function = result.current_content[func_start:func_end]

            # Format the new function content with proper decorator handling
            new_lines = operation.content.strip().splitlines()
            decorators = []
            function_body = []
            collect_decorators = True

            for line in new_lines:
                if collect_decorators and line.strip().startswith("@"):
                    decorators.append(line.strip())
                else:
                    collect_decorators = False
                    function_body.append(line)

            formatted_decorators = "\n".join(
                (f"{indentation}{dec}" for dec in decorators)
            )

            if function_body:
                formatted_body = f"{indentation}{function_body[0]}"
                if len(function_body) > 1:
                    body_indent = indentation + "    "
                    for line in function_body[1:]:
                        if line.strip():
                            formatted_body += f"\n{body_indent}{line.lstrip()}"
                        else:
                            formatted_body += f"\n"
                else:
                    formatted_body = ""

            if decorators:
                new_function = f"{formatted_decorators}\n{formatted_body}"
            else:
                new_function = formatted_body

            # Handle spacing before and after the function
            # Detect what comes next - class or function
            is_class_next = False
            if next_def_match and "class" in next_def_match.group():
                is_class_next = True

            # Count empty lines before and after to preserve or improve spacing
            empty_before = 0
            pos = func_start - 1
            while pos >= 0 and result.current_content[pos] == "\n":
                empty_before += 1
                pos -= 1

            empty_after = 0
            pos = func_end
            while (
                pos < len(result.current_content)
                and result.current_content[pos] == "\n"
            ):
                empty_after += 1
                pos += 1

            # Always ensure at least 2 newlines after function, especially before a class
            norm_after = "\n\n"
            if is_class_next:
                norm_after = "\n\n"  # Force 2 newlines before a class
            else:
                norm_after = "\n" * min(
                    max(2, empty_after), 3
                )  # Between 2-3 newlines in other cases

            # Preserve spacing before or ensure at least 1-2 newlines
            norm_before = "\n" * min(max(1, empty_before), 2)

            prefix = result.current_content[: func_start - empty_before]
            suffix = result.current_content[func_end + empty_after :]

            # Ensure clean transitions
            if prefix and (not prefix.endswith("\n")):
                prefix += "\n"

            if suffix and (not suffix.startswith("\n")):
                suffix = "\n" + suffix

            new_content = prefix + norm_before + new_function + norm_after + suffix
            result.current_content = new_content

            console.print(f"[green]Replaced function {function_name}[/green]")

        except Exception as e:
            console.print(f"[red]Error processing function: {str(e)}[/red]")
            import traceback

            console.print(f"[red]{traceback.format_exc()}[/red]")
            operation.add_error(f"Error processing function: {str(e)}")