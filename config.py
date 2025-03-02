import os
import json
from pathlib import Path
from rich.console import Console
console = Console()

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

    def __init__(self):
        self.data = DEFAULT_CONFIG.copy()
        self.config_path = self._get_config_path()
        self.load()

    def _get_config_path(self):
        """Get the path to the configuration file based on platform."""
        if os.name == 'nt':
            config_dir = os.path.join(os.environ.get('APPDATA', ''), 'PatchCommander')
        else:
            config_dir = os.path.join(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), 'patchcommander')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'config.json')

    def load(self):
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                for (key, value) in user_config.items():
                    if key in self.data:
                        self.data[key] = value
                console.print(f'[blue]Configuration loaded from {self.config_path}[/blue]')
            except Exception as e:
                console.print(f'[yellow]Error loading config file: {e}. Using defaults.[/yellow]')
        else:
            self.save()

    def save(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.data, f, indent=4)
            console.print(f'[green]Configuration saved to {self.config_path}[/green]')
        except Exception as e:
            console.print(f'[yellow]Error saving config file: {e}[/yellow]')

    def get(self, key, default=None):
        """Get a configuration value."""
        return self.data.get(key, default)

    def set(self, key, value):
        """Set a configuration value and save it."""
        if key in self.data:
            self.data[key] = value
            self.save()
            return True
        return False

    def reset(self):
        """Reset configuration to defaults."""
        self.data = DEFAULT_CONFIG.copy()
        self.save()
        console.print('[green]Configuration reset to defaults.[/green]')

    def get_backup_path(self, file_path):
        """Get the backup path for a file based on configuration."""
        custom_path = self.get('default_backup_path')
        if custom_path:
            backup_dir = Path(custom_path)
        else:
            backup_dir = Path(file_path).parent / '.patchcommander_backups'
        backup_dir.mkdir(exist_ok=True, parents=True)
        return backup_dir
config = Config()