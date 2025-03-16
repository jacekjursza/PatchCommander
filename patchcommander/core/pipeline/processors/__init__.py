from .decorator import register_processor
# Import new manipulator-based processors
from .file_manipulator_processor import FileManipulatorProcessor
from .operation_manipulator_processor import OperationManipulatorProcessor
from .smart_manipulator_processor import SmartManipulatorProcessor

# We're not importing old processors directly here anymore
# They will be imported dynamically in registry.py if needed