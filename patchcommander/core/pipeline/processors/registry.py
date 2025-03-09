from typing import Dict, List, Type
from rich.console import Console
from .. import Processor, PatchOperation, PatchResult
console = Console()


class ProcessorRegistry:
    """
    Rejestr procesorów do przetwarzania różnych typów operacji.
    """
    _processors: Dict[str, List] = {}
    _processors_by_priority: Dict[int, List] = {}
    _initialized: bool = False

    @classmethod
    def _initialize(cls):
        """
        Inicjalizuje rejestr procesorów, jeśli nie został jeszcze zainicjalizowany.
        """
        if cls._initialized:
            return
        cls._processors = {}
        cls._processors_by_priority = {}
        from .file_processor import FileProcessor
        from .operation_processor import OperationProcessor
        from .python.class_processor import PythonClassProcessor
        from .python.method_diff_match_patch import DiffMatchPatchPythonMethodProcessor

        from .python.function_diff_match_patch import DiffMatchPatchPythonFunctionProcessor

        # cls.register_processor(SimpleDebugMethodProcessor, 1)  # Najwyższy priorytet dla debugowania
        # cls.register_processor(RedBaronPythonMethodProcessor, 3)
        # cls.register_processor(DiffMatchPatchPythonMethodProcessor, 5)
        # cls.register_processor(FileProcessor, 10)
        # cls.register_processor(OperationProcessor, 10)
        # cls.register_processor(PythonClassProcessor, 10)
        # cls.register_processor(PythonFunctionProcessor, 30)
        # cls.register_processor(TreeSitterPythonMethodProcessor, 20)
        # cls.register_processor(RegexPythonMethodProcessor, 120)
        cls._initialized = True

    @classmethod
    def register_processor(cls, processor_class: Type[Processor], priority: int=100) -> None:
        """
        Rejestruje procesor o określonym priorytecie.

        Args:
            processor_class: Klasa procesora
            priority: Priorytet procesora (niższy = wyższy priorytet)
        """
        processor = processor_class()
        if priority not in cls._processors_by_priority:
            cls._processors_by_priority[priority] = []
        cls._processors_by_priority[priority].append(processor)
        console.print(f'Zarejestrowano procesor: {processor.__class__.__name__} z priorytetem {priority}')
        cls._initialized = True

    @classmethod
    def get_processors_for_operation(cls, operation: PatchOperation) -> List[Processor]:
        """
        Zwraca procesory, które mogą obsłużyć daną operację, posortowane według priorytetu.

        Args:
            operation: Operacja do obsłużenia

        Returns:
            Lista procesorów, które mogą obsłużyć operację
        """
        if not cls._initialized:
            cls._initialize()
        compatible_processors = []
        for priority in sorted(cls._processors_by_priority.keys()):
            for processor in cls._processors_by_priority[priority]:
                if processor.can_handle(operation):
                    compatible_processors.append(processor)
        return compatible_processors

    @classmethod
    def process_operation(cls, operation: PatchOperation, result: PatchResult) -> bool:
        """
        Przetwarza operację używając odpowiedniego procesora.
        Jeśli procesor zakończy się niepowodzeniem lub wygeneruje kod z błędami składni,
        próbuje kolejnych procesorów w kolejności priorytetu.

        Args:
            operation: Operacja do przetworzenia
            result: Wynik do aktualizacji

        Returns:
            bool: True jeśli operacja została pomyślnie przetworzona, False w przeciwnym razie
        """
        if not cls._initialized:
            cls._initialize()
        processors = cls.get_processors_for_operation(operation)
        if not processors:
            operation.add_error(f'Nie znaleziono procesora dla operacji typu {operation.name}')
            return False
        original_content = result.current_content
        for processor in processors:
            console.print(f'Próbuję procesor: {processor.__class__.__name__}')
            try:
                result.current_content = original_content
                processor.process(operation, result)

                # DODANE: Wyświetl zawartość pliku po zmianie
                console.print(f'[cyan]===== Zawartość pliku po przetworzeniu przez {processor.__class__.__name__} =====[/cyan]')
                console.print(result.current_content)
                console.print("[cyan]====== Koniec zawartości ======[/cyan]")

                if operation.file_extension == 'py' and result.current_content:
                    try:
                        compile(result.current_content, result.path, 'exec')
                        console.print(f'Procesor {processor.__class__.__name__} pomyślnie obsłużył operację')
                        operation.add_processor(processor.__class__.__name__)
                        return True
                    except SyntaxError as e:
                        error_msg = f'Błąd składni po przetworzeniu przez {processor.__class__.__name__}: {e}'
                        console.print(f'[yellow]{error_msg}[/yellow]')

                        # Naprawiona linia - rozdzielamy problem z ukośnikiem
                        lines = result.current_content.split('\n')
                        if 0 <= e.lineno-1 < len(lines):
                            error_line = lines[e.lineno-1]
                            console.print(f'[yellow]Linia z błędem: {error_line}[/yellow]')

                        operation.add_error(error_msg)
                        continue
                else:
                    console.print(f'Procesor {processor.__class__.__name__} pomyślnie obsłużył operację')
                    operation.add_processor(processor.__class__.__name__)
                    return True
            except Exception as e:
                error_msg = f'Błąd podczas przetwarzania przez {processor.__class__.__name__}: {e}'
                console.print(f'[yellow]{error_msg}[/yellow]')
                operation.add_error(error_msg)
                continue
        operation.add_error('Wszystkie kompatybilne procesory zakończyły się niepowodzeniem')
        return False