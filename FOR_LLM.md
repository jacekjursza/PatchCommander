## CRITICAL OUTPUT FORMATTING RULES
Your code is automatically processed by PatchCommander. **Strictly adhere** to these tagging conventions for optimal results:

### Correct Tag Usage Patterns

**1. Single File Modification:**
```
<FILE path="full/path/to/file.py">
# Complete file content goes here
# All code from beginning to end
</FILE>
```

**2. Single Class Modification:**
```
<CLASS path="full/path/to/file.py">
class ClassName:
    # Complete class definition
    # All methods and properties included
</CLASS>
```

**3. Single Method Modification (Always One Method Per Tag):**
```
<METHOD path="full/path/to/file.py" class="ClassName">
def single_method_name(self, arguments):
    # Complete method implementation
    return result
</METHOD>
```

**4. Single Function Modification (Always One Function Per Tag):**
```
<FUNCTION path="full/path/to/file.py">
def single_function_name(arguments):
    # Complete function implementation
    return result
</FUNCTION>
```

**5. File Operations:**
```
<OPERATION action="move_file" source="old/path.py" target="new/path.py" />

<OPERATION action="delete_file" source="path/to/file.py" />

<OPERATION action="delete_method" source="path/to/file.py" class="ClassName" method="method_name" />
```

## IMPORTANT TAG GUIDELINES

### Clear and Effective Tagging Practices:

- **Use complete paths** exactly as they appear in the source code
- **One definition per tag** is the key to success:
  - Each method requires its own `<METHOD>` tag
  - Each function requires its own `<FUNCTION>` tag
  - Place each definition in its own dedicated tag
- **Include complete definitions** with all necessary code
- **Be explicit** about class names in METHOD tags
- **Choose the appropriate tag** for each modification

### When to Use Each Tag:

- `<FILE>`: When replacing or creating an entire file
- `<CLASS>`: When focusing on a single class definition
- `<FUNCTION>`: When working with one standalone function
- `<METHOD>`: When updating one specific class method
- `<OPERATION>`: When performing file management tasks


## Reminder
Always strictly follow the formatting rules above when producing code. Remember that PatchCommander will automatically process your responses, so format precision is critical.

## Reminder: Best Practices

### For Optimal PatchCommander Integration:

1. **Single Definition Per Tag** - This approach ensures reliable processing:
   ```
   # First method in its own tag
   <METHOD path="path/to/file.py" class="MyClass">
   def method1(self):
       return "Hello"
   </METHOD>
   
   # Second method in its own separate tag
   <METHOD path="path/to/file.py" class="MyClass">
   def method2(self):
       return "World"
   </METHOD>
   ```

2. **Complete Definitions** - Include all necessary code for each element
3. **Proper Attribution** - Always include the class name for methods
4. **Consistent Paths** - Use full paths as they appear in the source code
5. **Appropriate Tags** - Select the most specific tag type for each change

Remember that PatchCommander relies on precise formatting to properly integrate your changes into the codebase.