#!/usr/bin/env python3
"""
AnyPS5 Launcher Entry Point
Forwards execution to server.main
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server.main import main

if __name__ == "__main__":
    main()
