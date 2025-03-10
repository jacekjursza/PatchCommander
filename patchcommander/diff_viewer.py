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
from textual.widgets import Static, Button, Header, Footer, Label
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

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "scroll_up", "Scroll Up", show=True),
        Binding("down", "scroll_down", "Scroll Down", show=True),
        Binding("[", "scroll_up", "Scroll Up", show=False),
        Binding("]", "scroll_down", "Scroll Down", show=False),
        Binding("left", "scroll_left", "Scroll Left", show=False),
        Binding("right", "scroll_right", "Scroll Right", show=False),
        Binding("home", "scroll_home", "Scroll Home", show=False),
        Binding("end", "scroll_end", "Scroll End", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
    ]

    def __init__(self, lines: List[Tuple[str, str]], title: str):
        super().__init__()
        self.can_focus = True
        self.lines = lines
        self.panel_title = title
        # Store line count for scroll synchronization
        self.line_count = len(lines)

    def compose(self) -> ComposeResult:
        yield Static(f"[bold]{self.panel_title}[/bold]", classes="panel-title")
        for line_text, line_style in self.lines:
            yield DiffLine(line_text, line_style)

    # Override scroll methods to notify parent of changes
    def _on_scroll_changed(self, y: Optional[float] = None):
        if (
            y is not None
            and hasattr(self, "parent")
            and hasattr(self.parent, "sync_scroll_from")
        ):
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
        super().__init__(id="diff-container")
        self.file_path = file_path
        self.old_highlighted = old_highlighted
        self.new_highlighted = new_highlighted
        self.left_panel = None
        self.right_panel = None

    def compose(self) -> ComposeResult:
        self.left_panel = DiffPanel(self.old_highlighted, f"Current: {self.file_path}")
        self.right_panel = DiffPanel(self.new_highlighted, f"New: {self.file_path}")
        yield self.left_panel
        yield self.right_panel

    def on_mount(self):
        # Listen for scroll changes
        self.watch(self.left_panel, "scroll_y", self._handle_left_scroll)
        self.watch(self.right_panel, "scroll_y", self._handle_right_scroll)

    def _handle_left_scroll(self, new_value):
        # When left panel scrolls, synchronize right panel
        self.sync_scroll_from(self.left_panel)

    def _handle_right_scroll(self, new_value):
        # When right panel scrolls, synchronize left panel
        self.sync_scroll_from(self.right_panel)

    def sync_scroll_from(self, source_panel):
        """Synchronize scrolling between panels proportionally."""
        # Don't sync if we're already handling a sync
        if hasattr(self, "_sync_in_progress") and self._sync_in_progress:
            return

        target_panel = (
            self.right_panel if source_panel is self.left_panel else self.left_panel
        )

        # Calculate the scroll percentage of the source panel
        source_max_scroll = source_panel.virtual_size.height - source_panel.size.height
        if source_max_scroll <= 0:
            # Source panel has no scrollable content
            return

        scroll_percentage = source_panel.scroll_y / source_max_scroll

        # Calculate the corresponding position in the target panel
        target_max_scroll = target_panel.virtual_size.height - target_panel.size.height
        if target_max_scroll <= 0:
            # Target panel has no scrollable content
            return

        # Apply the same percentage to the target panel
        self._sync_in_progress = True
        target_panel.scroll_y = min(
            scroll_percentage * target_max_scroll, target_max_scroll
        )
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
    """
    result = reactive("pending")

    def __init__(
        self,
        old_content: str,
        new_content: str,
        file_path: str,
        errors: List[str] = None,
        has_changes: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.old_content = old_content
        self.new_content = new_content
        self.file_path = file_path
        self.errors = errors or []
        self.has_changes = has_changes
        self.old_lines = self.old_content.splitlines()
        self.new_lines = self.new_content.splitlines()
        self.diff_container = None

        if has_changes:
            self.old_highlighted, self.new_highlighted = self._prepare_diff_lines()
        else:
            self.old_highlighted = [(line, "") for line in self.old_lines]
            self.new_highlighted = [(line, "") for line in self.new_lines]

    def on_mount(self) -> None:
        if self.has_changes:
            # Store references to our diff panels
            self.diff_container = self.query_one(DiffContainer)
            if self.diff_container:
                # Focus the first panel
                self.diff_container.left_panel.focus()

    def _prepare_diff_lines(
        self,
    ) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        matcher = difflib.SequenceMatcher(None, self.old_lines, self.new_lines)
        old_hl, new_hl = [], []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for i in range(i1, i2):
                    old_hl.append((self.old_lines[i], ""))
                for j in range(j1, j2):
                    new_hl.append((self.new_lines[j], ""))
            elif tag == "replace":
                for i in range(i1, i2):
                    old_hl.append((self.old_lines[i], "removed"))
                for j in range(j1, j2):
                    new_hl.append((self.new_lines[j], "modified"))
            elif tag == "delete":
                for i in range(i1, i2):
                    old_hl.append((self.old_lines[i], "removed"))
            elif tag == "insert":
                for j in range(j1, j2):
                    new_hl.append((self.new_lines[j], "added"))
        return old_hl, new_hl

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        if self.errors:
            yield ErrorPanel(self.errors)
        if not self.has_changes:
            yield Static(
                "[bold blue]No changes detected for this file[/bold blue]",
                id="no-changes",
            )
        if self.has_changes:
            yield DiffContainer(
                self.old_highlighted, self.new_highlighted, self.file_path
            )
        yield Footer()

    def action_accept(self) -> None:
        self.result = "yes"
        self.exit(True)

    def action_reject(self) -> None:
        self.result = "no"
        self.exit(False)

    def action_skip(self) -> None:
        self.result = "skip"
        self.exit("skip")

    def action_quit(self) -> None:
        self.result = "quit"
        self.exit("quit")

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
    old_content: str, new_content: str, file_path: str, errors: List[str] = None
) -> str:
    try:
        has_changes = old_content != new_content
        app = DiffViewer(
            old_content, new_content, file_path, errors=errors, has_changes=has_changes
        )
        result = app.run()
        if result in (True, "yes"):
            return "yes"
        elif result in (False, "no"):
            return "no"
        elif result == "skip":
            return "skip"
        else:
            return "quit"
    except Exception as e:
        import traceback

        print(f"[DiffViewer] Error: {str(e)}")
        print(traceback.format_exc())
        return "no"


if __name__ == "__main__":
    # Powielone linie, aby wymusić przewijanie
    old = (
        "def hello():\n"
        '    print("Hello world")\n'
        "    return True\n"
        "def unused():\n"
        "    pass\n"
    ) * 10
    new = ('def hello():\n'
           '    print("Hello updated world!")\n'
           '    print("This is a new line")\n'
           '    return True\n'
           'def new_function():\n'
           '    return "Added function"\n') * 10
    result = show_interactive_diff(old, new, 'example.py')
    print(f'User selected: {result}')