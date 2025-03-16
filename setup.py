"""
Setup script for PatchCommander v2.
"""
from setuptools import setup, find_packages

setup(
    name='patchcommander',
    version='1.2.1',
    description='AI-assisted coding automation tool',
    author='PatchCommander Team',
    packages=find_packages(),
    install_requires=[
        'rich>=12.6.0',
        'pyperclip>=1.8.2',
        'tree-sitter>=0.20.0',
        'tree-sitter-python>=0.20.0',
        'tree-sitter-javascript>=0.20.0',
        'tree-sitter-typescript==0.23.2',
        'diff-match-patch>=20200713',
        'textual>=0.14.0',
    ],
    entry_points={
        'console_scripts': [
            'pcmd=patchcommander.cli:main',
            'patchcommander=patchcommander.cli:main'
        ]
    },
    include_package_data=True,
    package_data={
        'patchcommander': ['FOR_LLM.md']
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers'
    ],
    python_requires='>=3.8'
)