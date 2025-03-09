"""
Modele danych dla pipeline'u PatchCommander.
Definiuje struktury używane w całym procesie przetwarzania.
"""
from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class PatchOperation:
    """
    Reprezentuje pojedynczą operację modyfikacji kodu.

    Atrybuty:
        name: Nazwa operacji ("FILE" lub "OPERATION")
        path: Ścieżka do pliku
        xpath: Opcjonalny XPath wskazujący na element w pliku
        content: Treść do wstawienia/modyfikacji
        action: Opcjonalna akcja dla OPERATION (np. "move_file", "delete_file")
        file_extension: Rozszerzenie pliku (wykryte automatycznie)
        attributes: Dodatkowe atrybuty z tagu
        preprocessors: Lista preprocessorów, przez które przeszła operacja
        processors: Lista procesorów, przez które przeszła operacja
        postprocessors: Lista postprocessorów, przez które przeszła operacja
        errors: Lista błędów napotkanych podczas przetwarzania
    """
    name: str
    path: str
    content: str = ''
    xpath: Optional[str] = None
    action: Optional[str] = None
    file_extension: str = ''
    attributes: Dict[str, str] = field(default_factory=dict)
    preprocessors: List[str] = field(default_factory=list)
    processors: List[str] = field(default_factory=list)
    postprocessors: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_preprocessor(self, name: str) -> None:
        """Dodaje nazwę preprocessora do historii."""
        self.preprocessors.append(name)

    def add_processor(self, name: str) -> None:
        """Dodaje nazwę procesora do historii."""
        self.processors.append(name)

    def add_postprocessor(self, name: str) -> None:
        """Dodaje nazwę postprocessora do historii."""
        self.postprocessors.append(name)

    def add_error(self, error: str) -> None:
        """Dodaje błąd do listy błędów."""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """Sprawdza czy są błędy."""
        return len(self.errors) > 0

@dataclass
class PatchResult:
    """
    Reprezentuje wynik patchowania pliku.

    Atrybuty:
        path: Ścieżka do pliku
        original_content: Oryginalna zawartość pliku
        current_content: Aktualna zawartość po wszystkich operacjach
        operations: Lista operacji wykonanych na pliku
        approved: Czy zmiany zostały zatwierdzone
        errors: Lista błędów napotkanych podczas przetwarzania
    """
    path: str
    original_content: str
    current_content: str
    operations: List[PatchOperation] = field(default_factory=list)
    approved: bool = False
    errors: List[str] = field(default_factory=list)

    def add_operation(self, operation: PatchOperation) -> None:
        """Dodaje operację do listy wykonanych operacji."""
        self.operations.append(operation)

    def add_error(self, error: str) -> None:
        """Dodaje błąd do listy błędów."""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """Sprawdza czy są błędy."""
        return len(self.errors) > 0

    def clear_errors(self) -> None:
        """Czyści listę błędów."""
        self.errors = []