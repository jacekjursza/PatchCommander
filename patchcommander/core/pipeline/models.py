from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass, field

@dataclass
class PatchOperation:
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
        self.preprocessors.append(name)

    def add_processor(self, name: str) -> None:
        self.processors.append(name)

    def add_postprocessor(self, name: str) -> None:
        self.postprocessors.append(name)

    def add_error(self, error: str) -> None:
        self.errors.append(error)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

@dataclass
class PatchResult:
    path: str
    original_content: str
    current_content: str
    operations: List[PatchOperation] = field(default_factory=list)
    approved: bool = False
    errors: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def add_operation(self, operation: PatchOperation) -> None:
        self.operations.append(operation)

    def add_error(self, error: str) -> None:
        self.errors.append(error)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def clear_errors(self) -> None:
        self.errors = []