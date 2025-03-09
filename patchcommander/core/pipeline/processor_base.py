"""
Bazowe klasy dla procesorów w pipeline.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from .models import PatchOperation, PatchResult

class BaseProcessor(ABC):
    """
    Bazowa klasa dla wszystkich procesorów.
    """
    
    @property
    def name(self) -> str:
        """
        Nazwa procesora używana w logach i historii operacji.
        Domyślnie to nazwa klasy, ale można nadpisać.
        """
        return self.__class__.__name__
        
    @abstractmethod
    def can_handle(self, operation: PatchOperation) -> bool:
        """
        Sprawdza czy procesor może obsłużyć daną operację.
        
        Args:
            operation: Operacja do sprawdzenia
            
        Returns:
            bool: True jeśli procesor może obsłużyć operację
        """
        pass
        
class PreProcessor(BaseProcessor):
    """
    Bazowa klasa dla pre-procesorów, które przygotowują operacje do przetworzenia.
    """
    
    @abstractmethod
    def process(self, operation: PatchOperation) -> None:
        """
        Przetwarza operację.
        
        Args:
            operation: Operacja do przetworzenia
        """
        pass
        
class Processor(BaseProcessor):
    """
    Bazowa klasa dla procesorów, które wykonują operacje na zawartości plików.
    """
    
    @abstractmethod
    def process(self, operation: PatchOperation, result: PatchResult) -> None:
        """
        Przetwarza operację i aktualizuje wynik.
        
        Args:
            operation: Operacja do przetworzenia
            result: Wynik do zaktualizowania
        """
        pass
        
class PostProcessor(BaseProcessor):
    """
    Bazowa klasa dla post-procesorów, które wykonują operacje na wynikach.
    """
    
    @abstractmethod
    def process(self, result: PatchResult) -> None:
        """
        Przetwarza wynik.
        
        Args:
            result: Wynik do przetworzenia
        """
        pass
        
class GlobalPreProcessor(ABC):
    """
    Specjalna klasa dla globalnego pre-procesora, który przetwarza cały tekst wejściowy.
    """
    
    @abstractmethod
    def process(self, input_text: str) -> List[PatchOperation]:
        """
        Przetwarza tekst wejściowy i generuje listę operacji.
        
        Args:
            input_text: Tekst wejściowy
            
        Returns:
            List[PatchOperation]: Lista operacji do wykonania
        """
        pass
