from setuptools import setup, find_packages
import os
import re

# Read version from main.py
def get_version():
    with open("main.py", "r") as f:
        content = f.read()
    version_match = re.search(r'VERSION\s*=\s*[\'"]([^\'"]*)[\'"]', content)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string in main.py")

# Read long description from README.md
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="patchcommander",
    version=get_version(),
    author="jacekjursza",
    author_email="jacek.jursza@gmail.com",  # Update with your actual email
    description="A tool for streamlining AI-assisted code development",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jacekjursza/PatchCommander",
    packages=find_packages(),
    py_modules=["main", "utils", "preprocessor", "processing", "apply_changes",
                "confirmations", "line_normalizer", "config", "vcs_integration", "__init__"],
    install_requires=[
        "rich",
        "pyperclip",
    ],
    entry_points={
        "console_scripts": [
            "pcmd=main:main",
            "patchcommander=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
    ],
    python_requires=">=3.8",
)