"""
Inicjalizacja modułu pipeline dla PatchCommander.
Udostępnia główne klasy i funkcje potrzebne do przetwarzania tagów.
"""
from .models import PatchOperation, PatchResult
from .processor_base import BaseProcessor, PreProcessor, Processor, PostProcessor, GlobalPreProcessor
from .pipeline import Pipeline

__all__ = [
    'PatchOperation',
    'PatchResult',
    'BaseProcessor',
    'PreProcessor',
    'Processor',
    'PostProcessor',
    'GlobalPreProcessor',
    'Pipeline'
]
