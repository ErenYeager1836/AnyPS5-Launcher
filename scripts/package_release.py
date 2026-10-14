#!/usr/bin/env python3
"""
Release Packaging Script for AnyPS5 Launcher
Packages all required runtime files, web assets, server, legal demo fixture,
and native executables into a clean, distributable ZIP archive for GitHub Releases.
"""

import os
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INCLUDE_FILES = [
    "AnyPS5Launcher.exe",
    "launch.bat",
    "launcher.py",
    "launcher.config.json",
    "anyps5-input.ini",
    "library.json",
    "index.html",
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
]

INCLUDE_DIRS = [
    ("css", ["*.css"]),
    ("js", ["*.js"]),
    ("server", ["*.py", "data/*.json"]),
    ("fixtures/demo_game", ["*"]),
    ("docs", ["*.md"]),
]

EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".git",
    ".github",
    ".app_data",
    "converted_games",
]

def should_exclude(rel_path: str) -> bool:
    for pat in EXCLUDE_PATTERNS:
        if pat.startswith("*."):
            if rel_path.endswith(pat[1:]):
                return True
        elif pat in rel_path.split(os.sep):
            return True
    return False

def build_package(version: str = "v1.0.0") -> Path:
    dist_dir = BASE_DIR / "dist"
    dist_dir.mkdir(exist_ok=True)
    
    zip_name = f"AnyPS5-Launcher-windows-{version}.zip"
    zip_path = dist_dir / zip_name

    print(f"📦 Packaging AnyPS5 Launcher release: {zip_path.name}...")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Add individual files
        for fname in INCLUDE_FILES:
            fpath = BASE_DIR / fname
            if fpath.exists():
                zf.write(fpath, arcname=fname)
                print(f"  + Added file: {fname}")
            else:
                print(f"  ! Warning: {fname} not found")

        # 2. Add directories
        for dir_name, patterns in INCLUDE_DIRS:
            dir_path = BASE_DIR / dir_name
            if not dir_path.exists():
                continue
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    rel = file_path.relative_to(BASE_DIR)
                    rel_str = str(rel).replace("\\", "/")
                    if not should_exclude(str(rel)):
                        zf.write(file_path, arcname=rel_str)
                        print(f"  + Added: {rel_str}")

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ Successfully created release archive: {zip_path}")
    print(f"   Size: {size_mb:.2f} MB")
    return zip_path

if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "v1.0.0"
    build_package(version)
