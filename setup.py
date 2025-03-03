"""
Setup script for PatchCommander v2.
"""
from setuptools import setup, find_packages

setup(
    name='patchcommander',
    version='1.1.0',
    description='AI-assisted coding automation tool',
    author='PatchCommander Team',
    packages=find_packages(),
    install_requires=[
        'rich',
        'pyperclip',
        'tree-sitter',
        'tree-sitter-python',
        'tree-sitter-javascript'
    ],
    entry_points={
        'console_scripts': [
            'pcmd=cli:main',
            'patchcommander=cli:main'
        ]
    },
    include_package_data=True,
    package_data={
        'patchcommander': ['PROMPT.md', 'FOR_LLM.md'],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
    ],
    python_requires='>=3.8',
)