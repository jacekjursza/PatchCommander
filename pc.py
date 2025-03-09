#!/usr/bin/env python
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patchcommander.cli import main

if __name__ == "__main__":
    sys.exit(main())