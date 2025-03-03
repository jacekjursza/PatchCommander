"""
Initialize operations module and register all operations.
"""
# Import all operations to register them with the factory
from operations.base import Operation, OperationFactory, register_operation
from operations.python_operations import *
