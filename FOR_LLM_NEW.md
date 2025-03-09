## CRITICAL OUTPUT FORMATTING RULES
Your code is automatically processed by PatchCommander. **Strictly adhere** to these tagging conventions for optimal results:

## Correct Tag Usage Patterns

**1. Complete File Modification:**
```
<FILE path="D:\project\app\models.py">
# Complete file content goes here
# All code from beginning to end
</FILE>
```

**2. Class Modification:**
```
<FILE path="D:\project\app\models.py" xpath="ClassName">
class ClassName:
    # Complete class definition
    # All methods and properties
</FILE>
```

**3. Method Modification:**
```
<FILE path="D:\project\app\models.py" xpath="ClassName.method_name" mode="replace">
def method_name(self, arguments):
    # Complete method implementation
    return result
</FILE>
```

**4. Function Modification:**
```
<FILE path="D:\project\app\utils.py" xpath="function_name" mode="merge">
def function_name(arguments):
    # Complete function implementation
    return result
</FILE>
```

**5. File Operations:**
```
<OPERATION action="move_file" source="D:\project\old\module.py" target="D:\project\new\module.py" />

<OPERATION action="delete_file" source="D:\project\app\deprecated.py" />

<OPERATION action="delete_method" source="D:\project\app\models.py" class="ClassName" method="method_name" />
```

## IMPORTANT TAG GUIDELINES

### Effective Tagging Practices:

- **Use complete paths** exactly as they appear in the source code
- **Use correct xpath** for elements in the file:
  - `xpath="ClassName"` for modifying an entire class
  - `xpath="ClassName.method_name"` for modifying a method within a class
  - `xpath="function_name"` for modifying a standalone function
- **Include complete definitions** with all necessary code
- **Choose the appropriate tag** for each modification
- **Use mode attributes** to control how methods/functions are updated:
  - `mode="replace"` (default) - completely replaces the existing method/function
  - `mode="merge"` - intelligently merges changes, preserving decorators and comments

### When to Use Each Tag:

- `<FILE>` without xpath: when replacing or creating an entire file
- `<FILE>` with xpath: when focusing on a specific element in a file
- `<OPERATION>`: when performing file management tasks

## Reminder
Always strictly follow the formatting rules above when producing code. Remember that PatchCommander will automatically process your responses, so format precision is critical.

## Reminder: Best Practices

### For Optimal PatchCommander Integration:

1. **Complete Definitions** - Include all necessary code for each element
2. **Correct xpath Syntax** - use the format:
   ```
   # For an entire class
   <FILE path="D:\project\app\models.py" xpath="ClassName">

   # For a method in a class - using replace mode (default)
   <FILE path="D:\project\app\models.py" xpath="ClassName.method_name">

   # For a method in a class - using merge mode
   <FILE path="D:\project\app\models.py" xpath="ClassName.method_name" mode="merge">

   # For a standalone function
   <FILE path="D:\project\app\utils.py" xpath="function_name">
   ```

3. **Consistent Paths** - Use full paths as they appear in the source code
4. **Appropriate Tags** - Select the most specific tag type for each change

Remember that PatchCommander relies on precise formatting to properly integrate your changes into the codebase.

## Understanding XPath in PatchCommander

The XPath attribute in the FILE tag allows you to target specific code elements precisely:

### XPath Format Examples

- **Class targeting**: `xpath="MyClass"` - finds and modifies the MyClass class
- **Method targeting**: `xpath="MyClass.my_method"` - finds and modifies my_method in the MyClass class
- **Function targeting**: `xpath="my_function"` - finds and modifies the standalone my_function function

### XPath Benefits

- More precise targeting of code elements
- Reduced need for multiple tag types (CLASS, METHOD, FUNCTION)
- Simplified syntax for common operations
- Better support for context-aware modifications

### Mode Attribute

The mode attribute controls how methods/functions are updated:

- **replace mode** (default): Completely replaces the entire method/function with the new code
- **merge mode**: Intelligently merges the new code with the existing code, preserving decorators and the structure

Example of replace mode:
```
<FILE path="D:\project\app\models.py" xpath="User.authenticate" mode="replace">
def authenticate(self, password):
    # This will completely replace the existing method
    return self.password_hash == hash_password(password)
</FILE>
```

