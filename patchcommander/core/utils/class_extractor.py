"""
Utility for extracting and comparing class features.
"""
import ast
import re
from typing import Dict, List, Set, Tuple, Any, Optional, NamedTuple

class ClassField(NamedTuple):
    """Represents a class field with its type annotations and default value."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    
    def __eq__(self, other):
        if not isinstance(other, ClassField):
            return False
        return self.name == other.name
    
    def __hash__(self):
        return hash(self.name)

class ClassMethod(NamedTuple):
    """Represents a class method with its signature and body."""
    name: str
    signature: str  # Full method signature including decorators
    body: str       # Method body
    is_property: bool = False
    decorators: List[str] = []
    
    def __eq__(self, other):
        if not isinstance(other, ClassMethod):
            return False
        return self.name == other.name
    
    def __hash__(self):
        return hash(self.name)

class ClassFeatures(NamedTuple):
    """Complete set of features extracted from a class."""
    name: str
    base_classes: List[str]
    fields: Set[ClassField]
    methods: Set[ClassMethod]
    dunder_methods: Set[ClassMethod]
    properties: Set[ClassMethod]
    class_methods: Set[ClassMethod]
    static_methods: Set[ClassMethod]
    inner_classes: List[Any]  # Recursive ClassFeatures, but can't type hint like that

class ClassDiff(NamedTuple):
    """Difference between two class versions."""
    added_fields: Set[ClassField]
    removed_fields: Set[ClassField]
    modified_fields: Set[Tuple[ClassField, ClassField]]  # (old, new)
    added_methods: Set[ClassMethod]
    removed_methods: Set[ClassMethod]
    modified_methods: Set[Tuple[ClassMethod, ClassMethod]]  # (old, new)
    # Similarly for other features...
    has_significant_changes: bool  # True if structural changes that might need user confirmation

class ClassFeatureExtractor:
    """
    Extracts features from Python classes and compares them to determine
    how they should be merged.
    """
    
    @staticmethod
    def extract_features_from_ast(node: ast.ClassDef) -> ClassFeatures:
        """
        Extract class features using AST.
        
        Args:
            node: AST ClassDef node
            
        Returns:
            ClassFeatures object with extracted features
        """
        name = node.name
        base_classes = [base.id if isinstance(base, ast.Name) else ast.unparse(base) 
                        for base in node.bases]
        
        fields = set()
        methods = set()
        dunder_methods = set()
        properties = set()
        class_methods = set()
        static_methods = set()
        inner_classes = []
        
        for item in node.body:
            # Handle class fields with annotations
            if isinstance(item, ast.AnnAssign):
                field_name = item.target.id if isinstance(item.target, ast.Name) else ast.unparse(item.target)
                type_annotation = ast.unparse(item.annotation) if item.annotation else None
                default_value = ast.unparse(item.value) if item.value else None
                fields.add(ClassField(field_name, type_annotation, default_value))
            
            # Handle regular assignments (fields without type annotations)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        fields.add(ClassField(target.id, None, ast.unparse(item.value)))
            
            # Handle methods and decorated methods
            elif isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                method_name = item.name
                is_property = False
                is_class_method = False
                is_static_method = False
                decorators = []
                
                # Check decorators
                for decorator in item.decorator_list:
                    dec_str = ast.unparse(decorator)
                    decorators.append(dec_str)
                    if dec_str == 'property':
                        is_property = True
                    elif dec_str.endswith('.setter') or dec_str.endswith('.deleter'):
                        is_property = True
                    elif dec_str == 'classmethod':
                        is_class_method = True
                    elif dec_str == 'staticmethod':
                        is_static_method = True
                
                # Generate method signature
                params = []
                for param in item.args.args:
                    param_str = param.arg
                    if param.annotation:
                        param_str += f": {ast.unparse(param.annotation)}"
                    params.append(param_str)
                
                if item.args.vararg:
                    params.append(f"*{item.args.vararg.arg}")
                
                if item.args.kwonlyargs:
                    if not item.args.vararg:
                        params.append("*")
                    for kwarg in item.args.kwonlyargs:
                        param_str = kwarg.arg
                        if kwarg.annotation:
                            param_str += f": {ast.unparse(kwarg.annotation)}"
                        params.append(param_str)
                
                if item.args.kwarg:
                    params.append(f"**{item.args.kwarg.arg}")
                
                signature = f"def {method_name}({', '.join(params)})"
                if item.returns:
                    signature += f" -> {ast.unparse(item.returns)}"
                signature += ":"
                
                # Get method body
                body = ast.unparse(item.body)
                
                # Create method object
                method = ClassMethod(method_name, signature, body, is_property, decorators)
                
                # Add to appropriate category
                if method_name.startswith('__') and method_name.endswith('__'):
                    dunder_methods.add(method)
                elif is_property:
                    properties.add(method)
                elif is_class_method:
                    class_methods.add(method)
                elif is_static_method:
                    static_methods.add(method)
                else:
                    methods.add(method)
            
            # Handle inner classes
            elif isinstance(item, ast.ClassDef):
                inner_classes.append(ClassFeatureExtractor.extract_features_from_ast(item))
        
        return ClassFeatures(
            name=name,
            base_classes=base_classes,
            fields=fields,
            methods=methods,
            dunder_methods=dunder_methods,
            properties=properties,
            class_methods=class_methods,
            static_methods=static_methods,
            inner_classes=inner_classes
        )
    
    @staticmethod
    def extract_features_from_code(code: str) -> Optional[ClassFeatures]:
        """
        Extract class features from Python code string.
        
        Args:
            code: Python code containing a class definition
            
        Returns:
            ClassFeatures object with extracted features or None if parsing fails
        """
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    return ClassFeatureExtractor.extract_features_from_ast(node)
            
            # If we get here, no class was found. Try to extract class name and try again
            class_match = re.search(r'class\s+(\w+)', code)
            if class_match:
                class_name = class_match.group(1)
                # Try to make the code valid Python for parsing
                fixed_code = f"class {class_name}:\n" + "\n".join(
                    f"    {line}" for line in code.split("\n") if not line.strip().startswith("class")
                )
                try:
                    tree = ast.parse(fixed_code)
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            return ClassFeatureExtractor.extract_features_from_ast(node)
                except:
                    pass
            
            return None
        except Exception as e:
            print(f"Failed to parse code: {e}")
            return None
    
    @staticmethod
    def find_class_in_code(code: str, class_name: str) -> Optional[str]:
        """
        Find a class definition in code.
        
        Args:
            code: Python code string
            class_name: Name of the class to find
            
        Returns:
            String containing the class definition or None if not found
        """
        try:
            # Try regex approach first (more robust for potentially invalid code)
            pattern = rf'(class\s+{re.escape(class_name)}\s*(?:\([^)]*\))?\s*:.*?)(?:\n\s*class|\Z)'
            match = re.search(pattern, code, re.DOTALL)
            if match:
                return match.group(1)
            
            # If regex fails, try AST
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    return ast.unparse(node)
            
            return None
        except Exception as e:
            print(f"Error finding class {class_name}: {e}")
            return None
    
    @staticmethod
    def diff_features(old_features: ClassFeatures, new_features: ClassFeatures) -> ClassDiff:
        """
        Compare two class features to determine differences.
        
        Args:
            old_features: Features of the original class
            new_features: Features of the new class
            
        Returns:
            ClassDiff object describing the differences
        """
        # Compare fields
        old_fields = {field.name: field for field in old_features.fields}
        new_fields = {field.name: field for field in new_features.fields}
        
        added_fields = {field for name, field in new_fields.items() if name not in old_fields}
        removed_fields = {field for name, field in old_fields.items() if name not in new_fields}
        
        modified_fields = set()
        for name, old_field in old_fields.items():
            if name in new_fields:
                new_field = new_fields[name]
                if (old_field.type_annotation != new_field.type_annotation or 
                    old_field.default_value != new_field.default_value):
                    modified_fields.add((old_field, new_field))
        
        # Compare methods (similar approach)
        old_methods = {method.name: method for method in old_features.methods}
        new_methods = {method.name: method for method in new_features.methods}
        
        added_methods = {method for name, method in new_methods.items() if name not in old_methods}
        removed_methods = {method for name, method in old_methods.items() if name not in new_methods}
        
        modified_methods = set()
        for name, old_method in old_methods.items():
            if name in new_methods:
                new_method = new_methods[name]
                if (old_method.signature != new_method.signature or 
                    old_method.body != new_method.body or
                    old_method.decorators != new_method.decorators):
                    modified_methods.add((old_method, new_method))
        
        # Determine if changes are significant enough to need user confirmation
        has_significant_changes = False
        
        # Case 1: All methods were removed but only a few fields changed
        if (removed_methods and old_methods and 
            len(removed_methods) == len(old_methods) and
            (len(added_fields) + len(modified_fields)) < 3):
            has_significant_changes = True
            
        # Case 2: Methods were selectively removed (might be intentional)
        if removed_methods and len(removed_methods) < len(old_methods):
            has_significant_changes = True
        
        return ClassDiff(
            added_fields=added_fields,
            removed_fields=removed_fields,
            modified_fields=modified_fields,
            added_methods=added_methods,
            removed_methods=removed_methods,
            modified_methods=modified_methods,
            has_significant_changes=has_significant_changes
        )
    
    @staticmethod
    def merge_classes(original_class_code: str, new_class_code: str) -> Tuple[str, bool]:
        """
        Intelligently merge two class versions based on their features.
        
        Args:
            original_class_code: Code of the original class
            new_class_code: Code of the new class
            
        Returns:
            Tuple of (merged_code, needs_confirmation)
        """
        original_features = ClassFeatureExtractor.extract_features_from_code(original_class_code)
        new_features = ClassFeatureExtractor.extract_features_from_code(new_class_code)
        
        if not original_features or not new_features:
            return new_class_code, False
        
        diff = ClassFeatureExtractor.diff_features(original_features, new_features)
        
        # Case 1: Only fields changed, preserve all methods
        if ((diff.added_fields or diff.removed_fields or diff.modified_fields) and
            not diff.added_methods and not diff.modified_methods and diff.removed_methods):
            
            # Get class definition line and indentation
            class_def_pattern = rf'class\s+{re.escape(original_features.name)}\s*(?:\([^)]*\))?\s*:'
            class_def_match = re.search(class_def_pattern, original_class_code)
            class_def_line = class_def_match.group(0) if class_def_match else f"class {original_features.name}:"
            
            # Extract indentation from the original class
            first_line_pattern = r'class.*?:\s*\n(\s+)'
            indent_match = re.search(first_line_pattern, original_class_code)
            base_indent = indent_match.group(1) if indent_match else "    "
            
            # Get new fields from the new class code
            fields_lines = []
            for line in new_class_code.split('\n'):
                line_strip = line.strip()
                if line_strip and not line_strip.startswith('class '):
                    if ':' in line_strip and not line_strip.startswith('def ') and not line_strip.startswith('@'):
                        # This is a field definition
                        fields_lines.append(f"{base_indent}{line_strip}")
            
            # Get methods from the original class
            methods_lines = []
            in_method = False
            method_indentation = ""
            for line in original_class_code.split('\n'):
                line_strip = line.strip()
                
                # Detect decorator or method start
                if line_strip.startswith('@') or line_strip.startswith('def '):
                    in_method = True
                    methods_lines.append(line)
                    if not method_indentation and line.startswith(base_indent):
                        method_indentation = line[:len(base_indent)]
                    continue
                
                # Inside method body or between methods
                if in_method:
                    # Check if we've exited the method
                    if line.startswith(base_indent) and not line.startswith(base_indent + " "):
                        # If this is a field line, we've exited the method
                        if ':' in line_strip and not line_strip.startswith('def ') and not line_strip.startswith('@'):
                            in_method = False
                        else:
                            # Still in method or start of another method/decorator
                            methods_lines.append(line)
                            continue
                    else:
                        # Still in method body
                        methods_lines.append(line)
                        continue
            
            # Combine everything
            merged_lines = [class_def_line]
            if fields_lines:
                merged_lines.extend(fields_lines)
            else:
                merged_lines.append(f"{base_indent}pass")
            
            if methods_lines:
                merged_lines.append("")  # Add separation between fields and methods
                merged_lines.extend(methods_lines)
            
            return "\n".join(merged_lines), diff.has_significant_changes
            
        # Default: Just use the new class
        return new_class_code, diff.has_significant_changes