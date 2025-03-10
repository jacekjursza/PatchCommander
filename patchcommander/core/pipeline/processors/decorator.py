"""
Decorator for registering processors.
"""
from typing import Type, Callable


def register_processor(priority: int = 100) -> Callable:
    """
    Decorator for registering a processor.

    Args:
        priority: Processor priority (lower = higher priority)

    Returns:
        The decorator function
    """
    def decorator(processor_class):
        # Import here to avoid circular imports
        from .registry import ProcessorRegistry
        ProcessorRegistry.register_processor(processor_class, priority)
        return processor_class
    return decorator