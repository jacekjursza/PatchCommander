"""
Base classes for code operations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

class Operation(ABC):
    """Abstract operation on code."""

    def __init__(self, attributes: Dict[str, Any]):
        """
        Initialize the operation.

        Args:
            attributes: Operation attributes (e.g., file path, class name)
        """
        self.attributes = attributes

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the operation and return status.

        Args:
            context: Operation execution context (e.g., method code)

        Returns:
            True if operation was successful, False otherwise
        """
        pass

class OperationFactory:
    """Factory for creating operations by name."""
    _operations = {}

    @classmethod
    def register_operation(cls, name: str, operation_class: type):
        """
        Register an operation class with a name.

        Args:
            name: Operation name
            operation_class: Operation class
        """
        cls._operations[name] = operation_class

    @classmethod
    def create_operation(cls, name: str, attributes: Dict[str, Any]) -> Operation:
        """
        Create an operation with the given name and attributes.

        Args:
            name: Operation name
            attributes: Operation attributes

        Returns:
            Operation instance

        Raises:
            ValueError: If operation with the given name does not exist
        """
        if name not in cls._operations:
            raise ValueError(f'Unknown operation: {name}')
        return cls._operations[name](attributes)

def register_operation(name: str):
    """
    Decorator for registering operations with the factory.

    Args:
        name: Operation name

    Returns:
        Decorator function
    """
    def decorator(cls):
        OperationFactory.register_operation(name, cls)
        return cls
    return decorator