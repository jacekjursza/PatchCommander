VERSION = '1.2'
APP_NAME = 'PatchCommander'

def _get_version():
    return VERSION
__version__ = _get_version()
from .cli import main
try:
    from .config_ui import run_config_ui
except ImportError:
    pass

# Export API classes and functions
from .api import PatchCommanderAPI, process_text, process_file, apply_changes