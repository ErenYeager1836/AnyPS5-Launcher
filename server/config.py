"""
Launcher Configuration Manager
Handles loading, saving, and validating launcher.config.json.
Enforces security constraints (127.0.0.1 binding, path validation).
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
    "anyps5_path": "C:/Users/mbhni/AnyPS5/build/bin/relinker.exe",
    "anyps5_source_path": "C:/Users/mbhni/AnyPS5",
    "library_folder": "fixtures",
    "output_folder": "converted_games",
    "host": "127.0.0.1",
    "port": 8085
}

def get_config_path(base_dir: Path) -> Path:
    return base_dir / "launcher.config.json"

def load_config(base_dir: Path) -> Dict[str, Any]:
    config_file = get_config_path(base_dir)
    config = dict(DEFAULT_CONFIG)
    
    # Check if local relative clone exists
    local_anyps5 = base_dir / "AnyPS5"
    if local_anyps5.exists() and not Path(config["anyps5_source_path"]).exists():
        config["anyps5_source_path"] = str(local_anyps5)
        config["anyps5_path"] = str(local_anyps5 / "build" / "bin" / "relinker.exe")

    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception:
            pass
    else:
        # Save default configuration on first load
        save_config(base_dir, config)

    # Strictly enforce localhost
    config["host"] = "127.0.0.1"
    return config

def validate_config(base_dir: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    """Validates configuration paths and returns audit results."""
    validated = dict(config)
    
    # 1. Enforce 127.0.0.1
    validated["host"] = "127.0.0.1"
    
    # 2. Port validation
    try:
        validated["port"] = int(validated.get("port", 8085))
        if not (1024 <= validated["port"] <= 65535):
            validated["port"] = 8085
    except (ValueError, TypeError):
        validated["port"] = 8085

    # 3. AnyPS5 binary validation
    raw_bin = validated.get("anyps5_path", "")
    bin_path = Path(raw_bin) if raw_bin else None
    bin_exists = bin_path.exists() and bin_path.is_file() if bin_path else False

    # Check alternate candidates if specified path does not exist
    if not bin_exists:
        candidates = [
            base_dir / "AnyPS5" / "build" / "bin" / "relinker.exe",
            Path("C:/Users/mbhni/AnyPS5/build/bin/relinker.exe"),
            base_dir / "AnyPS5" / "build" / "bin" / "relinker",
            Path("C:/Users/mbhni/AnyPS5/build/bin/relinker")
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                bin_path = c
                bin_exists = True
                validated["anyps5_path"] = str(c)
                break

    # 4. Library folder validation
    lib_raw = validated.get("library_folder", "fixtures")
    lib_path = Path(lib_raw)
    if not lib_path.is_absolute():
        lib_path = base_dir / lib_path
    
    lib_exists = lib_path.exists() and lib_path.is_dir()
    if not lib_exists:
        try:
            lib_path.mkdir(parents=True, exist_ok=True)
            lib_exists = True
        except Exception:
            pass

    # 5. Output folder validation
    out_raw = validated.get("output_folder", "converted_games")
    out_path = Path(out_raw)
    if not out_path.is_absolute():
        out_path = base_dir / out_path
    
    try:
        out_path.mkdir(parents=True, exist_ok=True)
        out_exists = True
    except Exception:
        out_exists = False

    # 6. Source path validation
    src_raw = validated.get("anyps5_source_path", "")
    src_path = Path(src_raw) if src_raw else None
    src_exists = src_path.exists() and src_path.is_dir() if src_path else False

    validated["status"] = {
        "anyps5_binary_ready": bin_exists,
        "anyps5_binary_path": str(bin_path) if bin_path else None,
        "library_folder_ready": lib_exists,
        "library_folder_resolved": str(lib_path),
        "output_folder_ready": out_exists,
        "output_folder_resolved": str(out_path),
        "anyps5_source_ready": src_exists,
        "anyps5_source_resolved": str(src_path) if src_path else None
    }

    return validated

def save_config(base_dir: Path, config: Dict[str, Any]) -> bool:
    config_file = get_config_path(base_dir)
    # Strictly enforce 127.0.0.1
    config["host"] = "127.0.0.1"
    to_save = {
        "anyps5_path": config.get("anyps5_path", DEFAULT_CONFIG["anyps5_path"]),
        "anyps5_source_path": config.get("anyps5_source_path", DEFAULT_CONFIG["anyps5_source_path"]),
        "library_folder": config.get("library_folder", DEFAULT_CONFIG["library_folder"]),
        "output_folder": config.get("output_folder", DEFAULT_CONFIG["output_folder"]),
        "host": "127.0.0.1",
        "port": int(config.get("port", 8085))
    }
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
        return True
    except Exception:
        return False
