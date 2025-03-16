from typing import Dict, List, Type
from rich.console import Console
from .. import Processor, PatchOperation, PatchResult
console = Console()

class ProcessorRegistry:
    _processors: Dict[str, List] = {}
    _processors_by_priority: Dict[int, List] = {}
    _initialized: bool = False

    @classmethod
    def _initialize(cls):
        if cls._initialized:
            return
        cls._processors = {}
        cls._processors_by_priority = {}

        from .file_manipulator_processor import FileManipulatorProcessor
        from .operation_manipulator_processor import OperationManipulatorProcessor
        from .smart_manipulator_processor import SmartManipulatorProcessor
        
        # Stare procesory jako fallback (niższy priorytet)
        # W przyszłości można je będzie usunąć gdy nowe procesory będą w pełni przetestowane
        try:
            from .file_processor import FileProcessor
            from .operation_processor import OperationProcessor
            try:
                from .python.smart_class_processor import SmartClassProcessor
                from .python.class_processor import PythonClassProcessor
                from .python.method_diff_match_patch import DiffMatchPatchPythonMethodProcessor
                from .python.function_diff_match_patch import DiffMatchPatchPythonFunctionProcessor
            except ImportError:
                console.print("[yellow]Some old Python processors couldn't be imported, but that's OK - using new processors[/yellow]")
        except ImportError:
            console.print("[yellow]Some old processors couldn't be imported, but that's OK - using new processors[/yellow]")
        
        cls._initialized = True

    @classmethod
    def register_processor(cls, processor_class: Type[Processor], priority: int=100) -> None:
        processor = processor_class()
        if priority not in cls._processors_by_priority:
            cls._processors_by_priority[priority] = []
        cls._processors_by_priority[priority].append(processor)
        console.print(f'Registered processor: {processor.__class__.__name__} with priority {priority}')
        cls._initialized = True

    @classmethod
    def get_processors_for_operation(cls, operation: PatchOperation) -> List[Processor]:
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
        if not cls._initialized:
            cls._initialize()
        processors = cls.get_processors_for_operation(operation)
        if not processors:
            operation.add_error(f'No processor found for operation type {operation.name}')
            return False
        processor_names = [processor.__class__.__name__ for processor in processors]
        console.print(f"[blue]Selected processors for operation: {', '.join(processor_names)}[/blue]")
        original_content = result.current_content
        for processor in processors:
            console.print(f'Trying processor: {processor.__class__.__name__}')
            try:
                result.current_content = original_content
                processor.process(operation, result)
                
                # Validate syntax for Python files
                if operation.file_extension == 'py' and result.current_content:
                    try:
                        compile(result.current_content, result.path, 'exec')
                        console.print(f'Processor {processor.__class__.__name__} successfully handled the operation')
                        operation.add_processor(processor.__class__.__name__)
                        return True
                    except SyntaxError as e:
                        error_msg = f'Syntax error after processing by {processor.__class__.__name__}: {e}'
                        console.print(f'[yellow]{error_msg}[/yellow]')
                        lines = result.current_content.split('\n')
                        if 0 <= e.lineno - 1 < len(lines):
                            error_line = lines[e.lineno - 1]
                            console.print(f'[yellow]Line with error: {error_line}[/yellow]')
                        operation.add_error(error_msg)
                        continue
                else:
                    console.print(f'Processor {processor.__class__.__name__} successfully handled the operation')
                    operation.add_processor(processor.__class__.__name__)
                    return True
            except Exception as e:
                error_msg = f'Error during processing by {processor.__class__.__name__}: {e}'
                console.print(f'[yellow]{error_msg}[/yellow]')
                operation.add_error(error_msg)
                continue
        operation.add_error('All compatible processors failed')
        return False