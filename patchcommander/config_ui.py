"""
Textual-based UI for PatchCommander configuration.
Provides an interactive interface for managing configuration settings.
"""
import os
from typing import Dict, Any, List, Optional
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Header, Footer, Static, Button, Input, Switch, Select
from textual import work
from textual.reactive import reactive
from rich.text import Text
from rich.console import Console
from rich.panel import Panel
from rich import box

from patchcommander.core.config import config, DEFAULT_CONFIG
from patchcommander import APP_NAME, VERSION

console = Console()

class ConfigItem(Horizontal):
    """Widget representing a single configuration item."""
    
    DEFAULT_CSS = """
    ConfigItem {
        height: auto;
        min-height: 6;
        max-height: 6;  
        margin: 0 0;
        padding: 1;
    }
    
    ConfigItem:hover {
        background: $boost;
    }
    
    ConfigItem > Static.label {
        width: 50%;
        padding-top: 1;
    }
    
    ConfigItem > .input-container {
        width: 50%;
    }
    
    ConfigItem > .button-container {
        width: 20%;
        align: right middle;
    }
    """

    def __init__(self, key: str, value: Any, on_change=None):
        super().__init__()
        self.key = key
        self.value = value
        self.value_type = type(value)
        self.on_change = on_change
        self.original_value = value
        self.description = self._get_description(key)

    def _get_description(self, key: str) -> str:
        """Get a user-friendly description for the config key."""
        descriptions = {
            "backup_enabled": "Create backups of modified files",
            "default_backup_path": "Default directory for file backups",
            "auto_create_dirs": "Automatically create directories if needed",
            "syntax_validation": "Validate syntax after changes",
            "max_diff_context_lines": "Max lines of context in diff view",
            "default_yes_to_all": "Default to yes for all confirmations",
            "debug_mode": "Enable debug mode with extra logging"
        }
        return descriptions.get(key, key.replace("_", " ").capitalize())

    def compose(self) -> ComposeResult:
        yield Static(f"{self.description}:", classes="label")

        with Container(classes="input-container"):
            if isinstance(self.value, bool):
                yield Switch(value=self.value, id=f"switch_{self.key}")
            elif isinstance(self.value, int):
                yield Input(value=str(self.value), id=f"input_{self.key}")
            elif isinstance(self.value, str) or self.value is None:
                yield Input(value=str(self.value or ""), id=f"input_{self.key}")
            elif isinstance(self.value, list):
                # For simplicity, display lists as text
                yield Input(value=", ".join(map(str, self.value)), id=f"input_{self.key}")


        with Container(classes="button-container"):
            yield Button("Reset", id=f"reset_{self.key}", variant="default")

    def on_switch_changed(self, event) -> None:
        """Handle switch toggle."""
        if event.switch.id == f"switch_{self.key}":
            if self.on_change:
                self.on_change(self.key, event.value)

    def on_input_changed(self, event) -> None:
        """Handle input change."""
        if event.input.id == f"input_{self.key}":
            value = event.value

            # Convert to appropriate type
            if self.value_type == int:
                try:
                    value = int(value)
                except ValueError:
                    return
            elif self.value_type == list:
                value = [item.strip() for item in value.split(",") if item.strip()]
            elif self.value is None:
                if not value:
                    value = None

            if self.on_change:
                self.on_change(self.key, value)

    def on_button_pressed(self, event) -> None:
        """Handle button press."""
        if event.button.id == f"reset_{self.key}":
            # Reset to default
            default_value = DEFAULT_CONFIG.get(self.key, self.original_value)

            # Update the widget display
            if isinstance(default_value, bool):
                self.query_one(f"#switch_{self.key}", Switch).value = default_value
            elif isinstance(default_value, (int, str)) or default_value is None:
                self.query_one(f"#input_{self.key}", Input).value = str(default_value or "")
            elif isinstance(default_value, list):
                self.query_one(f"#input_{self.key}", Input).value = ", ".join(map(str, default_value))

            if self.on_change:
                self.on_change(self.key, default_value)

class StatusBar(Static):
    """Status bar widget to display messages."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        background: $accent;
        color: $text;
        height: 1;
        padding: 0 1;
    }
    """

    message = reactive("")

    def on_mount(self) -> None:
        """Initialize the status bar."""
        self.update_status("")

    def update_status(self, message: str) -> None:
        """Update the status message."""
        self.message = message
        self.update(Text(message))

    def watch_message(self, message: str) -> None:
        """Watch for changes to the message."""
        self.update(Text(message))

class ConfigUI(App):
    """Configuration UI for PatchCommander."""

    CSS = """
    Screen {
        background: $background;
    }
    
    #config-container {
        width: 100%;
        height: 90%;
        margin: 1 4 1 4; 
        border: tall $accent;
        background: $background;
        padding: 1;
    }
    
    #title {
        text-align: center;
        background: $accent;
        color: $text;
        padding: 1;
        margin-bottom: 1;
    }
    
    #config-path {
        text-align: center;
        margin-bottom: 1;
        color: $text;
    }
    
    #items-container {
        height: 2fr;
        margin: 1 0;
        overflow-y: auto;
    }
    
    #buttons-container {
        margin-top: 2;
        height: auto;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    
    ConfigItem {
        height: auto;
        min-height: 6;
        max-height: 6;
        margin: 0 0;
        padding: 1;
        color: $text;
    }
    
    ConfigItem > Static.label {
        width: 60%;
        padding-top: 1;
        color: $text;
    }
    
    ConfigItem > .input-container {
        width: 50%;
        color: $text;
    }
    
    Input {
        color: $text;
        background: $surface;
    }
    
    Switch {
        background: $surface;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "save", "Save"),
        ("r", "reset_all", "Reset All")
    ]

    def __init__(self):
        super().__init__()
        self.changes = {}
        self.quit_confirm_active = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)

        with Container(id="config-container"):
            yield Static(f"{APP_NAME} v{VERSION} - Configuration", id="title")
            yield Static(f"Configuration file: {config.config_path}", id="config-path")

            with Vertical(id="items-container"):
                for key, value in config.data.items():
                    yield ConfigItem(key, value, self.on_config_change)

            with Horizontal(id="buttons-container"):
                yield Button("Save", id="btn_save", variant="primary")
                yield Button("Reset All", id="btn_reset_all", variant="default")
                yield Button("Quit", id="btn_quit", variant="default")

        yield StatusBar(id="status-bar")
        yield Footer()

    def on_config_change(self, key: str, value: Any) -> None:
        """Handle configuration changes."""
        self.changes[key] = value
        status = self.query_one("#status-bar", StatusBar)
        status.update_status(f"Changed: {key} = {value} (unsaved)")

    def on_button_pressed(self, event) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "btn_save":
            self.action_save()
        elif button_id == "btn_reset_all":
            self.action_reset_all()
        elif button_id == "btn_quit":
            self.action_quit()

    def action_save(self) -> None:
        """Save configuration changes."""
        if not self.changes:
            self.notify("No changes to save.")
            return

        # Apply changes to config
        for key, value in self.changes.items():
            config.set(key, value)

        # Save the changes to file
        config.save()

        # Update status
        status = self.query_one("#status-bar", StatusBar)
        status.update_status(f"Saved {len(self.changes)} changes.")

        # Clear changes
        self.changes = {}

        self.notify("Configuration saved successfully!")

    def action_reset_all(self) -> None:
        """Reset all configuration settings to defaults."""
        # Reset each config item widget
        for item in self.query(ConfigItem):
            key = item.key
            button = self.query_one(f"#reset_{key}")
            button.press()
        
        status = self.query_one("#status-bar", StatusBar)
        status.update_status("All settings reset to defaults (unsaved)")
        
        self.notify("All settings reset to defaults. Press Save to apply.")
    
    def action_quit(self) -> None:
        """Quit the application."""
        if self.changes:
            # Display notification and confirm quit on second press
            if hasattr(self, "quit_confirm_active") and self.quit_confirm_active:
                self.exit()
            else:
                self.quit_confirm_active = True
                self.notify(
                    "You have unsaved changes! Press 'q' again to quit without saving.",
                    severity="warning",
                    timeout=5.0
                )
                # Reset the flag after 5 seconds
                def reset_flag():
                    self.quit_confirm_active = False
                self.set_timer(5, reset_flag)
        else:
            self.exit()

def run_config_ui():
    """Run the configuration UI."""
    app = ConfigUI()
    app.run()

if __name__ == "__main__":
    run_config_ui()