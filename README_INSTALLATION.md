## Installation

You can install PatchCommander in several ways:

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

## Usage

After installation, you can run PatchCommander using the shorter command:

```bash
# Process clipboard content
pcmd

# Process a file
pcmd path/to/input_file.txt

# Show all options
pcmd --help
```

The legacy command `patchcommander` is also available but `pcmd` is recommended.