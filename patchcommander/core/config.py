"""
Configuration management for PatchCommander v2.
Handles loading, saving, and accessing configuration settings.
"""
import os
import json
from pathlib import Path
from rich.console import Console

console = Console()

# Default configuration settings
DEFAULT_CONFIG = {
    'backup_enabled': False,
    'default_backup_path': None,
    'auto_create_dirs': True,
    'syntax_validation': True,
    'max_diff_context_lines': 3,
    'default_yes_to_all': False,
    'tag_types': ['FILE', 'CLASS', 'METHOD', 'FUNCTION', 'OPERATION'],
    'debug_mode': False
}

class Config:
    """Configuration manager class."""

    def __init__(self):
        """Initialize the configuration manager."""
        self.data = DEFAULT_CONFIG.copy()
        self.config_path = self._get_config_path()
        self.load()

    def _get_config_path(self):
        """
        Get the path to the configuration file based on platform.

        Returns:
            Path: Path to the configuration file
        """
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', '')) / 'PatchCommander'
        else:  # Unix-like
            config_dir = Path(os.environ.get('XDG_CONFIG_HOME',
                                             Path.home() / '.config')) / 'patchcommander'

        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'config.json'

    def load(self):
        """
        Load configuration from file.

        Returns:
            bool: True if configuration was loaded successfully, False otherwise
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)

                # Update only keys that exist in the default config
                for key, value in user_config.items():
                    if key in self.data:
                        self.data[key] = value

                console.print(f"[blue]Configuration loaded from {self.config_path}[/blue]")
                return True
            except Exception as e:
                console.print(f"[yellow]Error loading config file: {e}. Using defaults.[/yellow]")
                return False
        else:
            # Create default configuration file if it doesn't exist
            self.save()
            return True

    def save(self):
        """
        Save current configuration to file.

        Returns:
            bool: True if configuration was saved successfully, False otherwise
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.data, f, indent=4)

            console.print(f"[green]Configuration saved to {self.config_path}[/green]")
            return True
        except Exception as e:
            console.print(f"[yellow]Error saving config file: {e}[/yellow]")
            return False

    def get(self, key, default=None):
        """
        Get a configuration value.

        Args:
            key (str): Configuration key
            default: Default value to return if key is not found

        Returns:
            Value of the configuration key or default
        """
        return self.data.get(key, default)

    def set(self, key, value):
        """
        Set a configuration value and save it.

        Args:
            key (str): Configuration key
            value: Value to set

        Returns:
            bool: True if the key existed and was updated, False otherwise
        """
        if key in self.data:
            self.data[key] = value
            self.save()
            return True
        return False

    def reset(self):
        """
        Reset configuration to defaults.

        Returns:
            bool: True if reset was successful, False otherwise
        """
        self.data = DEFAULT_CONFIG.copy()
        success = self.save()
        if success:
            console.print("[green]Configuration reset to defaults.[/green]")
        return success

# Create a global config instance
config = Config()