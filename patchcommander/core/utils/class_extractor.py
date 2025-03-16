import ast
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple, Any, Optional, NamedTuple

class ClassField(NamedTuple):
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
    name: str
    signature: str
    body: str
    is_property: bool = False
    decorators: List[str] = []

    def __eq__(self, other):
        if not isinstance(other, ClassMethod):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

class ClassFeatures(NamedTuple):
    name: str
    base_classes: List[str]
    fields: Set[ClassField]
    methods: Set[ClassMethod]
    dunder_methods: Set[ClassMethod]
    properties: Set[ClassMethod]
    class_methods: Set[ClassMethod]
    static_methods: Set[ClassMethod]
    inner_classes: List[Any]

class ClassDiff(NamedTuple):
    added_fields: Set[ClassField]
    removed_fields: Set[ClassField]
    modified_fields: Set[Tuple[ClassField, ClassField]]
    added_methods: Set[ClassMethod]
    removed_methods: Set[ClassMethod]
    modified_methods: Set[Tuple[ClassMethod, ClassMethod]]
    has_significant_changes: bool

class AbstractClassFeatureExtractor(ABC):
    """Abstract base class for language-specific class feature extractors"""
    
    @abstractmethod
    def extract_features_from_code(self, code: str) -> Optional[ClassFeatures]:
        """Extract class features from code string"""
        pass
    
    @abstractmethod
    def find_class_in_code(self, code: str, class_name: str) -> Optional[str]:
        """Find class definition in code"""
        pass
    
    @abstractmethod
    def diff_features(self, old_features: ClassFeatures, new_features: ClassFeatures) -> ClassDiff:
        """Compare two class features and return differences"""
        pass
    
    @abstractmethod
    def merge_classes(self, original_class_code: str, new_class_code: str) -> Tuple[str, bool]:
        """Merge two class implementations"""
        pass

class PythonClassFeatureExtractor(AbstractClassFeatureExtractor):
    """Python implementation of class feature extractor using AST"""

    def extract_features_from_ast(self, node: ast.ClassDef) -> ClassFeatures:
        name = node.name
        base_classes = [base.id if isinstance(base, ast.Name) else ast.unparse(base) for base in node.bases]
        fields = set()
        methods = set()
        dunder_methods = set()
        properties = set()
        class_methods = set()
        static_methods = set()
        inner_classes = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                field_name = item.target.id if isinstance(item.target, ast.Name) else ast.unparse(item.target)
                type_annotation = ast.unparse(item.annotation) if item.annotation else None
                default_value = ast.unparse(item.value) if item.value else None
                fields.add(ClassField(field_name, type_annotation, default_value))
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        fields.add(ClassField(target.id, None, ast.unparse(item.value)))
            elif isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                method_name = item.name
                is_property = False
                is_class_method = False
                is_static_method = False
                decorators = []
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
                params = []
                for param in item.args.args:
                    param_str = param.arg
                    if param.annotation:
                        param_str += f': {ast.unparse(param.annotation)}'
                    params.append(param_str)
                if item.args.vararg:
                    params.append(f'*{item.args.vararg.arg}')
                if item.args.kwonlyargs:
                    if not item.args.vararg:
                        params.append('*')
                    for kwarg in item.args.kwonlyargs:
                        param_str = kwarg.arg
                        if kwarg.annotation:
                            param_str += f': {ast.unparse(kwarg.annotation)}'
                        params.append(param_str)
                if item.args.kwarg:
                    params.append(f'**{item.args.kwarg.arg}')
                signature = f"def {method_name}({', '.join(params)})"
                if item.returns:
                    signature += f' -> {ast.unparse(item.returns)}'
                signature += ':'
                body = ast.unparse(item.body)
                method = ClassMethod(method_name, signature, body, is_property, decorators)
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
            elif isinstance(item, ast.ClassDef):
                inner_classes.append(self.extract_features_from_ast(item))
        return ClassFeatures(name=name, base_classes=base_classes, fields=fields, methods=methods, 
                           dunder_methods=dunder_methods, properties=properties, 
                           class_methods=class_methods, static_methods=static_methods, 
                           inner_classes=inner_classes)

    def extract_features_from_code(self, code: str) -> Optional[ClassFeatures]:
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    return self.extract_features_from_ast(node)
            class_match = re.search(r'class\s+(\w+)', code)
            if class_match:
                class_name = class_match.group(1)
                fixed_code = f'class {class_name}:\n' + '\n'.join(
                    (f'    {line}' for line in code.split('\n') if not line.strip().startswith('class')))
                try:
                    tree = ast.parse(fixed_code)
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            return self.extract_features_from_ast(node)
                except:
                    pass
            return None
        except Exception as e:
            print(f'Failed to parse code: {e}')
            return None

    def find_class_in_code(self, code: str, class_name: str) -> Optional[str]:
        try:
            pattern = f'(class\\s+{re.escape(class_name)}\\s*(?:\\([^)]*\\))?\\s*:.*?)(?:\\n\\s*class|\\Z)'
            match = re.search(pattern, code, re.DOTALL)
            if match:
                return match.group(1)
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    return ast.unparse(node)
            return None
        except Exception as e:
            print(f'Error finding class {class_name}: {e}')
            return None

    def diff_features(self, old_features: ClassFeatures, new_features: ClassFeatures) -> ClassDiff:
        old_fields = {field.name: field for field in old_features.fields}
        new_fields = {field.name: field for field in new_features.fields}
        added_fields = {field for (name, field) in new_fields.items() if name not in old_fields}
        removed_fields = {field for (name, field) in old_fields.items() if name not in new_fields}
        modified_fields = set()
        for (name, old_field) in old_fields.items():
            if name in new_fields:
                new_field = new_fields[name]
                if old_field.type_annotation != new_field.type_annotation or old_field.default_value != new_field.default_value:
                    modified_fields.add((old_field, new_field))
        old_methods = {method.name: method for method in old_features.methods}
        new_methods = {method.name: method for method in new_features.methods}
        added_methods = {method for (name, method) in new_methods.items() if name not in old_methods}
        removed_methods = {method for (name, method) in old_methods.items() if name not in new_methods}
        modified_methods = set()
        for (name, old_method) in old_methods.items():
            if name in new_methods:
                new_method = new_methods[name]
                if old_method.signature != new_method.signature or old_method.body != new_method.body or old_method.decorators != new_method.decorators:
                    modified_methods.add((old_method, new_method))
        has_significant_changes = False
        if removed_methods and old_methods and (len(removed_methods) == len(old_methods)) and (len(added_fields) + len(modified_fields) < 3):
            has_significant_changes = True
        if removed_methods and len(removed_methods) < len(old_methods):
            has_significant_changes = True
        return ClassDiff(added_fields=added_fields, removed_fields=removed_fields, modified_fields=modified_fields, 
                         added_methods=added_methods, removed_methods=removed_methods, 
                         modified_methods=modified_methods, has_significant_changes=has_significant_changes)

    def merge_classes(self, original_class_code: str, new_class_code: str) -> Tuple[str, bool]:
        import re
        original_features = self.extract_features_from_code(original_class_code)
        new_features = self.extract_features_from_code(new_class_code)
        if not original_features or not new_features:
            return (new_class_code, False)
        diff = self.diff_features(original_features, new_features)
        class_pattern = f'class\\s+{re.escape(original_features.name)}\\s*(?:\\([^)]*\\))?\\s*:'
        class_match = re.search(class_pattern, new_class_code)
        class_def = class_match.group(0) if class_match else f'class {original_features.name}:'
        base_indent = '    '
        field_lines = []
        in_class = False
        in_fields = False
        new_code_lines = new_class_code.split('\n')
        for line in new_code_lines:
            line_strip = line.strip()
            if re.match(class_pattern, line_strip):
                in_class = True
                in_fields = True
                continue
            if in_class and in_fields:
                if not line_strip:
                    continue
                if line_strip.startswith('def ') or line_strip.startswith('@'):
                    in_fields = False
                    continue
                field_lines.append(f'{base_indent}{line_strip}')
        original_method_names = set()
        for collection in [original_features.methods, original_features.dunder_methods, original_features.properties, 
                          original_features.class_methods, original_features.static_methods]:
            for method in collection:
                original_method_names.add(method.name)
        new_method_names = set()
        for collection in [new_features.methods, new_features.dunder_methods, new_features.properties, 
                         new_features.class_methods, new_features.static_methods]:
            for method in collection:
                new_method_names.add(method.name)
        methods_to_keep = original_method_names - new_method_names
        method_blocks = []

        def format_method(method_code):
            lines = method_code.strip().split('\n')
            result = []
            for (i, line) in enumerate(lines):
                line_strip = line.strip()
                if not line_strip:
                    result.append('')
                    continue
                if line_strip.startswith('def ') or line_strip.startswith('@'):
                    result.append(f'{base_indent}{line_strip}')
                else:
                    result.append(f'{base_indent}{base_indent}{line_strip}')
            return '\n'.join(result)

        def extract_method(code, method_name):
            pattern = f'((?:\\s*@[^\\n]+\\n+)*\\s*def\\s+{re.escape(method_name)}\\s*\\([^\\n]*\\).*?(?:\\n(?:(?!\\n\\s*(?:def|class|@)\\b)[^\\n]*))*)(?=\\n\\s*(?:def|class|@)\\b|$)'
            match = re.search(pattern, code, re.DOTALL)
            if match:
                return match.group(1).strip()
            return None
        for method_name in new_method_names:
            method_code = extract_method(new_class_code, method_name)
            if method_code:
                method_blocks.append(format_method(method_code))
        for method_name in methods_to_keep:
            method_code = extract_method(original_class_code, method_name)
            if method_code:
                method_blocks.append(format_method(method_code))
        result = [class_def]
        if field_lines:
            for field in field_lines:
                result.append(field)
        else:
            result.append(f'{base_indent}pass')
        if method_blocks:
            result.append('')
            for (i, method) in enumerate(method_blocks):
                if i > 0:
                    result.append('')
                result.append(method)
        return ('\n'.join(result), diff.has_significant_changes)

class JavaScriptClassFeatureExtractor(AbstractClassFeatureExtractor):
    """JavaScript/TypeScript implementation of class feature extractor using Tree-sitter"""
    
    def extract_features_from_code(self, code: str) -> Optional[ClassFeatures]:
        from patchcommander.core.languages import get_parser
        
        try:
            # Determine if we're dealing with JS or TS
            language = 'javascript'  # Default to JavaScript
            if 'interface ' in code or 'namespace ' in code or ': ' in code:
                language = 'typescript'
                
            parser = get_parser(language)
            code_bytes = code.encode('utf8')
            tree = parser.parse(code_bytes)
            root = tree.root_node
            
            # Look for class declaration
            if language == 'typescript':
                query_str = """
                    (class_declaration
                      name: (identifier) @class_name) @class
                """
            else:
                query_str = """
                    (class_declaration
                      name: (identifier) @class_name) @class
                """
                
            query = parser.query(query_str)
            captures = query.captures(root)
            
            # Process the first class found
            class_node = None
            class_name = None
            
            for node, node_type in captures:
                if node_type == 'class':
                    class_node = node
                elif node_type == 'class_name':
                    class_name = str(code_bytes[node.start_byte:node.end_byte], 'utf8')
                    
            if not class_node or not class_name:
                return None
                
            # Get base classes
            base_classes = []
            extends_node = None
            
            if language == 'typescript':
                extends_query = """
                    (class_declaration
                      extends_clause: (extends_clause
                        value: (identifier) @base_class))
                """
            else:
                extends_query = """
                    (class_declaration
                      extends: (class_heritage
                        (identifier) @base_class))
                """
                
            extends_query_result = parser.query(extends_query).captures(root)
            for node, node_type in extends_query_result:
                if node_type == 'base_class':
                    base_class_name = str(code_bytes[node.start_byte:node.end_byte], 'utf8')
                    base_classes.append(base_class_name)
            
            # Get class body
            fields = set()
            methods = set()
            dunder_methods = set()
            properties = set()
            class_methods = set()
            static_methods = set()
            
            # Query for class body items
            body_query = """
                (class_declaration
                  body: (class_body 
                    (field_definition
                      name: (property_identifier) @field_name) @field)
                      
                (class_declaration
                  body: (class_body 
                    (method_definition
                      name: (property_identifier) @method_name) @method))
                      
                (class_declaration
                  body: (class_body 
                    (method_definition
                      name: (property_identifier) @method_name
                      decorators: (decorator) @decorator) @decorated_method))
            """
            
            body_query_result = parser.query(body_query).captures(root)
            
            # Process fields and methods
            for node, node_type in body_query_result:
                if node_type == 'field_name':
                    field_name = str(code_bytes[node.start_byte:node.end_byte], 'utf8')
                    field_value = None
                    type_annotation = None
                    
                    # Try to find field type and value
                    field_node = node.parent
                    if field_node:
                        for child in field_node.children:
                            if child.type == 'type_annotation':
                                type_annotation = str(code_bytes[child.start_byte:child.end_byte], 'utf8')
                            elif child.type == 'value':
                                field_value = str(code_bytes[child.start_byte:child.end_byte], 'utf8')
                    
                    fields.add(ClassField(field_name, type_annotation, field_value))
                    
                elif node_type == 'method_name':
                    method_name = str(code_bytes[node.start_byte:node.end_byte], 'utf8')
                    method_node = node.parent
                    
                    # Extract method body
                    body = None
                    signature = None
                    
                    if method_node:
                        # Check if it's static, async, etc.
                        is_static = False
                        is_async = False
                        is_getter = False
                        is_setter = False
                        
                        for child in method_node.children:
                            if child.type == 'static' or child.text == b'static':
                                is_static = True
                            elif child.type == 'async' or child.text == b'async':
                                is_async = True
                            elif child.type == 'get' or child.text == b'get':
                                is_getter = True
                            elif child.type == 'set' or child.text == b'set':
                                is_setter = True
                        
                        # Get parameters
                        params = []
                        for child in method_node.children:
                            if child.type == 'formal_parameters':
                                for param_child in child.children:
                                    if param_child.type not in ['(', ')', ',']:
                                        params.append(str(code_bytes[param_child.start_byte:param_child.end_byte], 'utf8'))
                        
                        # Get body
                        for child in method_node.children:
                            if child.type == 'statement_block':
                                body = str(code_bytes[child.start_byte:child.end_byte], 'utf8')
                        
                        # Create signature
                        prefix = ''
                        if is_static:
                            prefix += 'static '
                        if is_async:
                            prefix += 'async '
                        if is_getter:
                            prefix += 'get '
                        if is_setter:
                            prefix += 'set '
                            
                        signature = f"{prefix}{method_name}({', '.join(params)}) {{"
                        
                        # Create method object
                        method = ClassMethod(
                            name=method_name,
                            signature=signature,
                            body=body or '',
                            is_property=is_getter or is_setter,
                            decorators=[]
                        )
                        
                        if method_name.startswith('__') and method_name.endswith('__'):
                            dunder_methods.add(method)
                        elif is_getter or is_setter:
                            properties.add(method)
                        elif is_static:
                            static_methods.add(method)
                        else:
                            methods.add(method)
            
            # Create class features
            return ClassFeatures(
                name=class_name,
                base_classes=base_classes,
                fields=fields,
                methods=methods,
                dunder_methods=dunder_methods,
                properties=properties,
                class_methods=class_methods,
                static_methods=static_methods,
                inner_classes=[]  # JS inner classes not yet supported
            )
            
        except Exception as e:
            print(f"Error extracting JS/TS class features: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def find_class_in_code(self, code: str, class_name: str) -> Optional[str]:
        # Use regex as a basic fallback for now
        pattern = f'(class\\s+{re.escape(class_name)}\\s*(?:extends\\s+\\w+\\s*)?{{[\\s\\S]*?}})'
        match = re.search(pattern, code)
        if match:
            return match.group(1)
            
        # Use tree-sitter for more complex cases
        try:
            from patchcommander.core.languages import get_parser
            
            # Determine language
            language = 'javascript'
            if 'interface ' in code or 'namespace ' in code or ': ' in code:
                language = 'typescript'
                
            parser = get_parser(language)
            code_bytes = code.encode('utf8')
            tree = parser.parse(code_bytes)
            
            query_str = f"""
                (class_declaration
                  name: (identifier) @class_name
                  (#eq? @class_name "{class_name}")) @class
            """
            
            query = parser.query(query_str)
            captures = query.captures(tree.root_node)
            
            for node, node_type in captures:
                if node_type == 'class':
                    return str(code_bytes[node.start_byte:node.end_byte], 'utf8')
            
            return None
        except Exception as e:
            print(f"Error finding JS/TS class: {e}")
            return None
    
    def diff_features(self, old_features: ClassFeatures, new_features: ClassFeatures) -> ClassDiff:
        # Reuse the Python implementation for now, as the logic is the same
        # We only differ in how we extract the features, not how we compare them
        old_fields = {field.name: field for field in old_features.fields}
        new_fields = {field.name: field for field in new_features.fields}
        added_fields = {field for (name, field) in new_fields.items() if name not in old_fields}
        removed_fields = {field for (name, field) in old_fields.items() if name not in new_fields}
        modified_fields = set()
        for (name, old_field) in old_fields.items():
            if name in new_fields:
                new_field = new_fields[name]
                if old_field.type_annotation != new_field.type_annotation or old_field.default_value != new_field.default_value:
                    modified_fields.add((old_field, new_field))
                    
        old_methods = {method.name: method for method in old_features.methods}
        new_methods = {method.name: method for method in new_features.methods}
        added_methods = {method for (name, method) in new_methods.items() if name not in old_methods}
        removed_methods = {method for (name, method) in old_methods.items() if name not in new_methods}
        modified_methods = set()
        for (name, old_method) in old_methods.items():
            if name in new_methods:
                new_method = new_methods[name]
                if old_method.signature != new_method.signature or old_method.body != new_method.body or old_method.decorators != new_method.decorators:
                    modified_methods.add((old_method, new_method))
                    
        has_significant_changes = False
        if removed_methods and old_methods and (len(removed_methods) == len(old_methods)):
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
    
    def merge_classes(self, original_class_code: str, new_class_code: str) -> Tuple[str, bool]:
        # Simple implementation for now - more sophisticated merging can be added later
        try:
            # Extract features
            original_features = self.extract_features_from_code(original_class_code)
            new_features = self.extract_features_from_code(new_class_code)
            
            if not original_features or not new_features:
                return (new_class_code, False)
                
            # Compute diff
            diff = self.diff_features(original_features, new_features)
            
            # If there are no significant changes, we can use the new code directly
            if not diff.has_significant_changes and not diff.removed_methods:
                return (new_class_code, False)
                
            # Otherwise, we need to merge the classes
            # Start with the class declaration and opening brace
            class_pattern = f'class\\s+{re.escape(original_features.name)}\\s*(?:extends\\s+[\\w,\\s]+)?\\s*{{'
            class_match = re.search(class_pattern, new_class_code)
            class_decl = class_match.group(0) if class_match else f'class {original_features.name} {{'
            
            # Extract fields from new class
            field_lines = []
            method_lines = []
            
            # Process fields
            all_fields = set()
            all_fields.update(new_features.fields)
            
            # Basic field merge - prioritize new fields, keep old ones if not in new
            for field in original_features.fields:
                if field.name not in [f.name for f in new_features.fields]:
                    all_fields.add(field)
            
            # Extract field lines from the new class
            in_class = False
            in_field = False
            current_field = []
            
            for line in new_class_code.splitlines():
                line_strip = line.strip()
                
                # Check if we're entering the class
                if not in_class and re.match(class_pattern, line_strip):
                    in_class = True
                    continue
                
                # Process class content
                if in_class:
                    # Skip empty lines at the beginning
                    if not line_strip:
                        continue
                        
                    # Method detection - when we hit a method, we're done with fields
                    if line_strip.startswith('constructor') or \
                       line_strip.startswith('static ') or \
                       re.match(r'^[a-zA-Z_$][\w$]*\s*\(', line_strip) or \
                       re.match(r'^(?:async\s+)?(?:get|set)\s+', line_strip):
                        if current_field:
                            field_lines.append('\n'.join(current_field))
                            current_field = []
                        in_field = False
                        break
                        
                    # Field detection
                    if re.match(r'^[a-zA-Z_$][\w$]*\s*(?:=|:|;)', line_strip):
                        if current_field:
                            field_lines.append('\n'.join(current_field))
                            current_field = []
                        in_field = True
                        current_field.append(line.rstrip())
                    elif in_field and line_strip and not line_strip.startswith('//'):
                        current_field.append(line.rstrip())
            
            if current_field:
                field_lines.append('\n'.join(current_field))
            
            # Now extract methods from both classes
            new_method_names = set(m.name for m in new_features.methods)
            kept_methods = []
            
            # Keep all new methods
            for method in new_features.methods:
                kept_methods.append(method)
                
            # Add methods from original class that aren't in the new class
            for method in original_features.methods:
                if method.name not in new_method_names:
                    kept_methods.append(method)
            
            # Extract method text from original code
            def extract_method(code, method_name):
                # This is a simplified method extractor - actual implementation would need to be more robust
                pattern = f'(?:(?:async\\s+)?(?:static\\s+)?(?:get\\s+|set\\s+)?{re.escape(method_name)}\\s*\\([^{{]*{{[\\s\\S]*?}})'
                match = re.search(pattern, code)
                if match:
                    return match.group(0)
                return None
            
            # Extract methods from code
            for method in kept_methods:
                method_code = None
                
                if method.name in new_method_names:
                    method_code = extract_method(new_class_code, method.name)
                else:
                    method_code = extract_method(original_class_code, method.name)
                    
                if method_code:
                    method_lines.append(method_code)
            
            # Build the merged class
            indentation = '  '  # Standard JS indentation
            
            result = [class_decl]
            
            # Add fields
            for field in field_lines:
                lines = field.split('\n')
                for line in lines:
                    if line.strip():
                        result.append(f"{indentation}{line.strip()}")
            
            # Add methods with spacing
            if method_lines:
                if field_lines:
                    result.append('')  # Add blank line between fields and methods
                    
                for i, method in enumerate(method_lines):
                    if i > 0:
                        result.append('')  # Add blank line between methods
                        
                    # Add method with proper indentation
                    lines = method.split('\n')
                    for j, line in enumerate(lines):
                        if j == 0:  # First line
                            result.append(f"{indentation}{line.strip()}")
                        else:
                            indent = indentation
                            if line.strip():  # Indented line inside method
                                indent = indentation + indentation
                            result.append(f"{indent}{line.strip()}")
            
            # Close the class
            result.append('}')
            
            return ('\n'.join(result), diff.has_significant_changes)
            
        except Exception as e:
            print(f"Error merging JS/TS classes: {e}")
            import traceback
            traceback.print_exc()
            return (new_class_code, False)

def get_class_feature_extractor(language: str) -> AbstractClassFeatureExtractor:
    """Factory function to get the appropriate class feature extractor for a language"""
    if language == 'python':
        return PythonClassFeatureExtractor()
    elif language in ['javascript', 'typescript']:
        return JavaScriptClassFeatureExtractor()
    else:
        raise ValueError(f'Unsupported language: {language}')

# For backward compatibility
ClassFeatureExtractor = PythonClassFeatureExtractor()