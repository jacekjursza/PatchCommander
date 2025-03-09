"""
Dekorator do rejestracji procesorów.
"""
from typing import Type, Callable


def register_processor(priority: int = 100) -> Callable:
    """
    Dekorator do rejestracji procesora.

    Args:
        priority: Priorytet procesora (niższy = wyższy priorytet)

    Returns:
        Funkcja dekoratora
    """
    def decorator(processor_class):
        # Import tutaj, aby uniknąć cyklicznych importów
        from .registry import ProcessorRegistry
        ProcessorRegistry.register_processor(processor_class, priority)
        return processor_class
    return decorator