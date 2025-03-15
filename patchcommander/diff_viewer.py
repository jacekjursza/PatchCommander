import difflib
import os
import tempfile
import subprocess
import sys
from typing import List, Tuple, Optional, Dict, Any, ClassVar
from rich.console import Console
from rich.syntax import Syntax
from rich.text import Text
from rich.panel import Panel
from rich import box
from rich.prompt import Prompt
from textual.app import App, ComposeResult
from textual.binding import BindingType, Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static, Button, Header, Footer, Label, Select
from textual.reactive import reactive
from textual.message import Message

console = Console()


class DiffLine(Static):
    """Widget representing a single line in the diff."""

    def __init__(self, line: str, style: str = ""):
        self.line_content = line
        self.line_style = style
        super().__init__("")
        self.update_content()

    def update_content(self) -> None:
        if self.line_style == "added":
            self.update(Text(f"+ {self.line_content}", style="green"))
        elif self.line_style == "removed":
            self.update(Text(f"- {self.line_content}", style="red"))
        elif self.line_style == "modified":
            self.update(Text(f"~ {self.line_content}", style="yellow"))
        else:
            self.update(Text(f"  {self.line_content}"))


class DiffPanel(VerticalScroll):
    """Panel displaying one side of the diff (old or new code)."""
    BINDINGS: ClassVar[list[BindingType]] = [Binding('up', 'scroll_up', 'Scroll Up', show=True), Binding('down', 'scroll_down', 'Scroll Down', show=True), Binding('[', 'scroll_up', 'Scroll Up', show=False), Binding(']', 'scroll_down', 'Scroll Down', show=False), Binding('left', 'scroll_left', 'Scroll Left', show=False), Binding('right', 'scroll_right', 'Scroll Right', show=False), Binding('home', 'scroll_home', 'Scroll Home', show=False), Binding('end', 'scroll_end', 'Scroll End', show=False), Binding('pageup', 'page_up', 'Page Up', show=False), Binding('pagedown', 'page_down', 'Page Down', show=False)]

    def __init__(self, lines: List[Tuple[str, str]], title: str):
        super().__init__()
        self.can_focus = True
        self.lines = lines
        self.panel_title = title
        self.line_count = len(lines)

    def compose(self) -> ComposeResult:
        yield Static(f'[bold]{self.panel_title}[/bold]', classes='panel-title')
        for (line_text, line_style) in self.lines:
            yield DiffLine(line_text, line_style)
            
    def update_content(self, lines: List[Tuple[str, str]]) -> None:
        """Update the panel content with new lines."""
        self.lines = lines
        self.line_count = len(lines)
        
        # Remove all existing DiffLine widgets
        for child in self.query(DiffLine):
            child.remove()
            
        # Add new DiffLine widgets
        for (line_text, line_style) in self.lines:
            self.mount(DiffLine(line_text, line_style))

    def _on_scroll_changed(self, y: Optional[float]=None):
        if y is not None and hasattr(self, 'parent') and hasattr(self.parent, 'sync_scroll_from'):
            self.parent.app.post_message(self.parent.SyncScroll(self))


class ErrorPanel(Static):
    """Panel displaying errors related to the current file."""

    def __init__(self, errors: List[str]):
        super().__init__("")
        self.errors = errors
        self.update_content()

    def update_content(self) -> None:
        if not self.errors:
            self.update("")
            return
        error_text = "\n".join([f"- {error}" for error in self.errors])
        self.update(
            Panel(
                Text(error_text, style="red"),
                title="[bold red]Errors found[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )


class DiffContainer(Horizontal):
    """Container for diff panels with synchronized scrolling."""

    class SyncScroll(Message):

        def __init__(self, source_panel: DiffPanel):
            super().__init__()
            self.source_panel = source_panel

    def __init__(self, old_highlighted, new_highlighted, file_path):
        super().__init__(id='diff-container')
        self.file_path = file_path
        self.old_highlighted = old_highlighted
        self.new_highlighted = new_highlighted
        self.left_panel = None
        self.right_panel = None

    def compose(self) -> ComposeResult:
        self.left_panel = DiffPanel(self.old_highlighted, f'Current: {self.file_path}')
        self.right_panel = DiffPanel(self.new_highlighted, f'New: {self.file_path}')
        yield self.left_panel
        yield self.right_panel

    def on_mount(self):
        self.watch(self.left_panel, 'scroll_y', self._handle_left_scroll)
        self.watch(self.right_panel, 'scroll_y', self._handle_right_scroll)
        
    def update_diff(self, old_highlighted, new_highlighted):
        """Update the diff display with new content."""
        self.old_highlighted = old_highlighted
        self.new_highlighted = new_highlighted
        
        if self.left_panel and self.right_panel:
            # Remember scroll positions
            left_scroll = self.left_panel.scroll_y
            right_scroll = self.right_panel.scroll_y
            
            # Update panels with new content
            self.left_panel.update_content(old_highlighted)
            self.right_panel.update_content(new_highlighted)
            
            # Restore scroll positions
            self.left_panel.scroll_y = left_scroll
            self.right_panel.scroll_y = right_scroll

    def _handle_left_scroll(self, new_value):
        self.sync_scroll_from(self.left_panel)

    def _handle_right_scroll(self, new_value):
        self.sync_scroll_from(self.right_panel)

    def sync_scroll_from(self, source_panel):
        """Synchronize scrolling between panels proportionally."""
        if hasattr(self, '_sync_in_progress') and self._sync_in_progress:
            return
        target_panel = self.right_panel if source_panel is self.left_panel else self.left_panel
        source_max_scroll = source_panel.virtual_size.height - source_panel.size.height
        if source_max_scroll <= 0:
            return
        scroll_percentage = source_panel.scroll_y / source_max_scroll
        target_max_scroll = target_panel.virtual_size.height - target_panel.size.height
        if target_max_scroll <= 0:
            return
        self._sync_in_progress = True
        target_panel.scroll_y = min(scroll_percentage * target_max_scroll, target_max_scroll)
        self._sync_in_progress = False


class DiffViewer(App):
    """Interactive side-by-side diff viewer."""
    BINDINGS = [
        ("y", "accept", "Accept changes"),
        ("n", "reject", "Reject changes"),
        ("s", "skip", "Skip changes"),
        ("q", "quit", "Quit"),
        ("[", "scroll_up", "Scroll up"),
        ("]", "scroll_down", "Scroll down"),
        ("pageup", "page_up", "Page up"),
        ("pagedown", "page_down", "Page down"),
        ("home", "scroll_home", "Scroll to top"),
        ("end", "scroll_end", "Scroll to bottom"),
    ]
    CSS = """
    .panel-title {
        background: #333;
        color: white;
        padding: 1;
        text-align: center;
    }
    #diff-container {
        height: 1fr;
    }
    .error-panel {
        margin: 1;
        padding: 1;
    }
    #no-changes {
        color: #888;
        text-align: center;
        margin: 2;
    }
    DiffPanel {
        width: 1fr;
        height: 1fr;
        border: solid green;
    }
    Footer {
        background: #222;
        color: white;
    }

    #processor-info {
        text-align: center;
        background: #444;
        color: white;
        padding: 0;
        margin: 0;
        height: auto;
    }

    #strategy-selector {
        margin: 0;
        padding: 0;
        border: solid #555;
        background: #333;
        height: auto;
        min-height: 3;
    }

    #strategy-label {
        margin-right: 1;
        color: white;
    }

    Select {
        width: 60%;
    }
    """
    result = reactive('pending')

    def __init__(self, old_content: str, new_content: str, file_path: str, errors: List[str]=None, 
                 has_changes: bool=True, merge_strategies: Dict[str, str]=None,
                 original_class_code: str=None, new_class_code: str=None,
                 class_name: str=None, class_features=None, processor_name: str=None, **kwargs):
        super().__init__(**kwargs)
        self.old_content = old_content
        self.new_content = new_content
        self.file_path = file_path
        self.errors = errors or []
        self.has_changes = has_changes
        self.old_lines = self.old_content.splitlines()
        self.new_lines = self.new_content.splitlines()
        self.diff_container = None
        self.merge_strategies = merge_strategies or {}
        self.original_class_code = original_class_code
        self.new_class_code = new_class_code
        self.class_name = class_name
        self.class_features = class_features
        self.current_strategy = 'replace'
        self.processor_name = processor_name
        if has_changes:
            (self.old_highlighted, self.new_highlighted) = self._prepare_diff_lines()
        else:
            self.old_highlighted = [(line, '') for line in self.old_lines]
            self.new_highlighted = [(line, '') for line in self.new_lines]

    def on_mount(self) -> None:
        """Handle mounting of the app."""
        if self.has_changes:
            self.diff_container = self.query_one(DiffContainer)
            if self.diff_container:
                self.diff_container.left_panel.focus()
        if self.merge_strategies and self.class_name:
            try:
                strategy_select = self.query_one('#strategy-select', Select)
                if strategy_select:
                    if not self.current_strategy:
                        self.current_strategy = "replace"
                    strategy_select.value = self.current_strategy
            except Exception as e:
                print(f'Warning: Could not set up strategy selector: {e}')

    def _prepare_diff_lines(self) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        matcher = difflib.SequenceMatcher(None, self.old_lines, self.new_lines)
        (old_hl, new_hl) = ([], [])
        for (tag, i1, i2, j1, j2) in matcher.get_opcodes():
            if tag == 'equal':
                for i in range(i1, i2):
                    old_hl.append((self.old_lines[i], ''))
                for j in range(j1, j2):
                    new_hl.append((self.new_lines[j], ''))
            elif tag == 'replace':
                for i in range(i1, i2):
                    old_hl.append((self.old_lines[i], 'removed'))
                for j in range(j1, j2):
                    new_hl.append((self.new_lines[j], 'modified'))
            elif tag == 'delete':
                for i in range(i1, i2):
                    old_hl.append((self.old_lines[i], 'removed'))
            elif tag == 'insert':
                for j in range(j1, j2):
                    new_hl.append((self.new_lines[j], 'added'))
        return (old_hl, new_hl)
        
    def _apply_merge_strategy(self, strategy: str) -> None:
        """Apply the selected merge strategy and update the diff view."""
        if not (self.merge_strategies and self.class_name and self.original_class_code and self.new_class_code and self.class_features):
            return

        if strategy == 'replace':
            merged_code = self.new_class_code
        else:  # Default to smart merge for any other strategy
            from patchcommander.core.utils.class_extractor import ClassFeatureExtractor
            (merged_code, _) = ClassFeatureExtractor.merge_classes(self.original_class_code, self.new_class_code)

        new_content = self.old_content.replace(self.original_class_code, merged_code)
        self.new_content = new_content
        self.new_lines = self.new_content.splitlines()
        (self.old_highlighted, self.new_highlighted) = self._prepare_diff_lines()

        if self.diff_container:
            self.diff_container.update_diff(self.old_highlighted, self.new_highlighted)

    def compose(self) -> ComposeResult:
        """Handle mounting of the app."""
        yield Header(show_clock=True)
        if self.processor_name:
            yield Static(f'[bold blue]Processor: {self.processor_name}[/bold blue]', id='processor-info')
        if self.merge_strategies and self.class_name:
            with Horizontal(id='strategy-selector'):
                yield Label('Merge Strategy:', id='strategy-label')
                # Ustaw opcję domyślną - używając self.current_strategy lub "smart"
                default_strategy = self.current_strategy or "smart"
                options = [(key, desc) for (key, desc) in self.merge_strategies.items()]
                select = Select(options, id='strategy-select', value=default_strategy)
                yield select
        if self.errors:
            yield ErrorPanel(self.errors)
        if not self.has_changes:
            yield Static('[bold blue]No changes detected for this file[/bold blue]', id='no-changes')
        if self.has_changes:
            yield DiffContainer(self.old_highlighted, self.new_highlighted, self.file_path)
        yield Footer()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle change in the strategy selector."""
        if event.select.id == 'strategy-select':
            self.current_strategy = event.select.value
            console.print(f'[blue]User selected merge strategy: {self.current_strategy} - {self.merge_strategies.get(self.current_strategy, "")}[/blue]')
            self._apply_merge_strategy(self.current_strategy)

    def action_accept(self) -> None:
        self.result = 'yes'
        self.exit(True)

    def action_reject(self) -> None:
        self.result = 'no'
        self.exit(False)

    def action_skip(self) -> None:
        self.result = 'skip'
        self.exit('skip')

    def action_quit(self) -> None:
        self.result = 'quit'
        self.exit('quit')

    def action_scroll_up(self) -> None:
        if self.diff_container:
            self.diff_container.left_panel.scroll_up(5)

    def action_scroll_down(self) -> None:
        if self.diff_container:
            self.diff_container.left_panel.scroll_down(5)

    def action_page_up(self) -> None:
        if self.diff_container:
            self.diff_container.left_panel.scroll_page_up()

    def action_page_down(self) -> None:
        if self.diff_container:
            self.diff_container.left_panel.scroll_page_down()

    def action_scroll_home(self) -> None:
        if self.diff_container:
            self.diff_container.left_panel.scroll_home()

    def action_scroll_end(self) -> None:
        if self.diff_container:
            self.diff_container.left_panel.scroll_end()


def show_less_pager(content: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as tmp:
        tmp.write(content)
        tmp_name = tmp.name
    try:
        if os.name == "nt":
            os.system(f'type "{tmp_name}" | more')
        else:
            pager = os.environ.get("PAGER", "less -R")
            subprocess.run(f'{pager} "{tmp_name}"', shell=True)
    finally:
        try:
            os.unlink(tmp_name)
        except:
            pass


def show_interactive_diff(
    old_content: str,
    new_content: str,
    file_path: str,
    errors: List[str] = None,
    class_info: Optional[Dict] = None,
    processor_name: str = None,
) -> str:
    """
    Show an interactive diff with merge strategy selection for classes.

    Args:
        old_content: Original content
        new_content: New content
        file_path: Path to the file
        errors: Optional list of errors
        class_info: Optional dictionary with class information:
            {
                'class_name': name of the class,
                'original_code': original class code,
                'new_code': new class code,
                'original_features': features of original class,
                'new_features': features of new class,
                'strategies': dictionary of available strategies
            }
        processor_name: Optional name of the processor being used

    Returns:
        User decision: 'yes', 'no', 'skip', or 'quit'
    """
    try:
        has_changes = old_content != new_content
        extra_params = {}
        if class_info and "strategies" in class_info:
            extra_params["merge_strategies"] = class_info["strategies"]
            if all(
                (k in class_info for k in ["class_name", "original_code", "new_code"])
            ):
                extra_params["class_name"] = class_info["class_name"]
                extra_params["original_class_code"] = class_info["original_code"]
                extra_params["new_class_code"] = class_info["new_code"]
                if "original_features" in class_info and "new_features" in class_info:
                    extra_params["class_features"] = (
                        class_info["original_features"],
                        class_info["new_features"],
                    )

        # Dodajemy nazwę procesora do parametrów
        if processor_name:
            extra_params["processor_name"] = processor_name

        app = DiffViewer(
            old_content,
            new_content,
            file_path,
            errors=errors,
            has_changes=has_changes,
            **extra_params,
        )
        result = app.run()

        # Zwracamy zarówno decyzję użytkownika, jak i zaktualizowaną zawartość
        if isinstance(result, tuple) and len(result) == 2:
            # Nowy format zwracany przez DiffViewer (decyzja, nowa_zawartość)
            return result
        elif result in (True, "yes"):
            # Dla kompatybilności wstecznej, gdy DiffViewer nie zwraca zawartości
            # W tym przypadku zwracamy oryginalną decyzję i oryginalny new_content
            return ('yes', app.new_content)
        elif result in (False, 'no'):
            return ('no', old_content)
        elif result == 'skip':
            return ('skip', old_content)
        else:
            return ('quit', old_content)
    except Exception as e:
        import traceback
        print(f'[DiffViewer] Error: {str(e)}')
        print(traceback.format_exc())
        return ('no', old_content)