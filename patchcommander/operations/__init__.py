"""
Initialize operations module and register all operations.
"""
# Import all operations to register them with the factory
from patchcommander.operations.base import Operation, OperationFactory, register_operation
from patchcommander.operations.python_operations import *
