## Usage

After installation, you can run PatchCommander using the command:

```bash
pcmd
```

This will use clipboard content by default. To process a file:

```bash
pcmd path/to/input_file.txt
```

For more options:

```bash
pcmd --help
```## Installation

You can install PatchCommander in several ways:

### Option 1: Using pip

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

### Option 4: Pre-built Executables

Pre-built executables for Windows, macOS, and Linux are available on the [Releases](https://github.com/jacekjursza/PatchCommander/releases) page.

### Option 5: From source

```bash
# Clone the repository
git clone https://github.com/jacekjursza/PatchCommander.git

# Navigate to the directory
cd PatchCommander

# Install dependencies
pip install -r requirements.txt

# Build and install
pip install .
```