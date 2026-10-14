# AnyPS5 Launcher ⚡

> **Lightweight Desktop Game Hub, Process Relinker Runner, ELF Diagnostics & Input Configurator for the [AnyPS5](https://github.com/boykopovar/AnyPS5) Compatibility Layer.**

[![Platform: Windows & Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue?style=flat-square)](https://github.com/boykopovar/AnyPS5)
[![Backend: Python Standard Library](https://img.shields.io/badge/Backend-Python%203%20Native-yellow?style=flat-square)](launcher.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

AnyPS5 Launcher is an open-source companion desktop application designed specifically for **AnyPS5**, the PlayStation 5 to PC static relinker and compatibility layer.

Built with a **zero-dependency architecture** (Standard Python 3 + Modern Web UI), it acts as a local process runner and developer workbench without requiring bulky electron runtimes or node_modules.

---

## ✨ Features

- 🎮 **Steam-Style Library**:
  - Interactive grid view with game performance profiles, title IDs, and status indicators.
  - One-click launch execution that spawns background processes and monitors exit codes.
  - Local directory scanner (`/api/scan`) that auto-discovers game folders with `eboot.bin` / `param.json`.
- 🔬 **Real ELF64 Binary Diagnostics**:
  - Direct binary parser (`/api/elf-inspect`) that inspects ELF64 headers, machine architecture (`EM_X86_64`), entry points, and PRX dependencies on disk.
- 🕹️ **Real `anyps5-input.ini` Configurator**:
  - Interactive SVG visualizer for DualSense and gamepad buttons.
  - Reads and writes real `anyps5-input.ini` configuration files directly to disk (`/api/input`).
- 📊 **Live Relinker Log Terminal**:
  - Slide-up drawer connected to a real-time stdout/stderr log stream (`/api/logs`) captured from active relinker processes.
- ⚡ **Zero External Dependencies**:
  - No `npm`, no `cargo`, no heavy frameworks. Runs immediately with standard Python 3.

---

## 🚀 Quick Start

### 1. Launch the Desktop App

Clone the repository and run the native companion server:

```bash
git clone https://github.com/ErenYeager1836/AnyPS5-Launcher.git
cd AnyPS5-Launcher
python launcher.py
```

Then open your browser at:
```text
http://localhost:8085
```

### 2. Testing Without Commercial Games (Included Demo)

The repository includes a dummy homebrew fixture under `fixtures/demo_game/` containing a valid 64-bit ELF binary and manifest:
- Click **"Scan Local Folder"** in the UI to discover the demo title.
- Click **"ELF Diagnostics"** to inspect the real binary header (x86-64 ELF64).
- Click **"Relink & Launch"** to test live subprocess spawning and stdout log streaming in real time.

---

## 📂 Project Architecture

```text
AnyPS5-Launcher/
├── launcher.py              # Native Python backend (IPC bridge, process runner, INI IO)
├── mock_relinker.py         # Standalone test runner for relinker pipeline simulation
├── fixtures/
│   └── demo_game/           # Minimal test package (valid ELF64 eboot.bin + param.json)
├── css/
│   └── style.css            # Dark mode glassmorphic UI system
├── js/
│   └── app.js               # Frontend state, API client & Web Audio synthesizer
├── index.html               # Main desktop interface
└── README.md                # Documentation
```

---

## ⚖️ Legal & Disclaimer

AnyPS5 Launcher is an independent open-source frontend and diagnostic utility. It does not contain any copyrighted Sony PlayStation 5 game files, decryption keys, or proprietary firmware. Users must dump their own legitimate software from consoles they own.

---

## 👤 Author

* **Nithishvelan M** ([@ErenYeager1836](https://github.com/ErenYeager1836))
