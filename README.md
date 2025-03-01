# PatchCommander

PatchCommander is a Python-based tool designed to streamline AI-assisted development. It works by processing code changes generated by Large Language Models (LLMs) that follow a specific tag-based syntax. By instructing LLMs to format their code suggestions using PatchCommander's tags, developers can easily and reliably apply AI-generated changes across their codebase.

## Purpose

Traditional copy-pasting of code suggested by LLMs is error-prone and time-consuming, especially when changes span multiple files or require careful integration into existing code. PatchCommander solves this by:

1. Defining a structured tag syntax that LLMs can be instructed to follow
2. Automatically processing these tags to make precise modifications to your codebase
3. Providing safety features like diff previews and syntax validation before changes are applied

This creates a seamless workflow between AI code suggestions and practical implementation.

## Features

- **LLM-friendly tag syntax**: Simple XML-like tags that AI models can easily adopt
- **Multiple change types**: Support for file, class, function, method, and operation modifications
- **Smart method handling**: Splits multiple method definitions automatically
- **Diff preview**: View changes before applying them
- **Syntax validation**: Automatically checks for syntax errors and reverts changes if errors are found
- **Clipboard support**: Read input directly from clipboard when no file is specified

## Installation

### Option 1: Using pip (recommended)

```bash
pip install patchcommander
```

### Option 2: Using pipx (recommended for command-line tools)

```bash
pipx install patchcommander
```

### Option 3: Using uv

```bash
uv install patchcommander
```

### Option 4: From source

```bash
# Clone the repository
git clone https://github.com/jacekjursza/PatchCommander.git

# Navigate to the directory
cd PatchCommander

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Dependencies

- rich
- pyperclip
- ast (standard library)

## Usage

After installation, you can use PatchCommander with the shorter command:

```bash
# Run with input from clipboard (no arguments)
pcmd

# Run with input from a file
pcmd path/to/input_file.txt

# Show help
pcmd --help
```

The legacy command `patchcommander` is also available but `pcmd` is recommended.

## Tag Syntax for LLMs

When prompting your LLM, instruct it to format code changes using the following tags:

### FILE

Replace an entire file's content:

```
<FILE path="path/to/file.py">
# New file content goes here
</FILE>
```

### CLASS

Update or add a class to a file:

```
<CLASS path="path/to/file.py" class="ClassName">
class ClassName:
    # Class content goes here
</CLASS>
```

### FUNCTION

Update or add a standalone function to a file:

```
<FUNCTION path="path/to/file.py">
def function_name(arg1, arg2):
    # Function body goes here
    return result
</FUNCTION>
```

### METHOD

Update or add a method to a class:

```
<METHOD path="path/to/file.py" class="ClassName">
def method_name(self, arg1, arg2):
    # Method body goes here
    return result
</METHOD>
```

### OPERATION

Perform file operations:

```
<OPERATION action="move_file" source="old/path.py" target="new/path.py" />

<OPERATION action="delete_file" source="path/to/file.py" />

<OPERATION action="delete_method" source="path/to/file.py" class="ClassName" method="method_name" />
```

## AI-Assisted Development Workflow

1. **Prompt the LLM**: Ask your LLM to implement a feature or fix a bug, instructing it to format changes using PatchCommander's tag syntax
2. **Copy the output**: Save the LLM's response with the tagged code changes to a file or clipboard
3. **Run PatchCommander**: Process the changes using `pcmd [filename]` or just `pcmd` for clipboard content
4. **Review the changes**: Examine the diffs for each proposed change
5. **Confirm or reject**: Choose which changes to apply
6. **Apply changes**: All confirmed changes are applied at once at the end of the process

## Example Prompt for LLMs

```
Please implement a user authentication system for my Flask application.
Format your response using PatchCommander tag syntax:
- Use <FILE> tags for new files or complete file replacements
- Use <CLASS> tags for adding or updating classes
- Use <FUNCTION> tags for adding or updating standalone functions
- Use <METHOD> tags for adding or updating methods
- Use <OPERATION> tags for file operations

Example format:
<FILE path="app/auth.py">
[code here]
</FILE>

<FUNCTION path="app/utils.py">
[function code here]
</FUNCTION>

<METHOD path="app/models.py" class="User">
[method code here]
</METHOD>
```

## Example Implementation

```
<FILE path="example.py">
class Example:
    def __init__(self):
        self.value = 42
        
    def get_value(self):
        return self.value
</FILE>

<FUNCTION path="example.py">
def utility_function(param):
    return param * 2
</FUNCTION>

<METHOD path="example.py" class="Example">
def set_value(self, new_value):
    self.value = new_value
</METHOD>

<OPERATION action="move_file" source="old_name.py" target="new_name.py" />
```

## How It Works

1. **Preprocessing**: Tags are parsed and processed (e.g., multiple methods in a METHOD tag are split)
2. **Processing**: Each tag is processed to generate the intended file changes
3. **Confirmation**: Changes are shown as diffs and require confirmation
4. **Application**: All confirmed changes are applied together at the end

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.