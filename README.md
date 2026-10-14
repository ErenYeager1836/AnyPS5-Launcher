# AnyPS5 Launcher ⚡

> **The Authoritative Desktop Companion for [AnyPS5](https://github.com/boykopovar/AnyPS5): Automated Toolchain Setup, Source Compiler, Game Relinker Studio, Dynamic Library Manager, DualSense Visualizer & ELF64 Diagnostics.**

[![CI: Multi-Platform Tests](https://github.com/ErenYeager1836/AnyPS5-Launcher/actions/workflows/ci.yml/badge.svg)](https://github.com/ErenYeager1836/AnyPS5-Launcher/actions/workflows/ci.yml)
[![Platform: Windows & Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue?style=flat-square)](https://github.com/boykopovar/AnyPS5)
[![Backend: Zero Dependencies](https://img.shields.io/badge/Backend-Python%20Standard%20Library-green?style=flat-square)](launcher.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![Design: OLED Glassmorphism](https://img.shields.io/badge/Aesthetics-OLED%20Glassmorphism-cyan?style=flat-square)](css/style.css)

AnyPS5 Launcher is an open-source, high-performance companion hub and desktop environment for **AnyPS5**, the static relinker and Vulkan compatibility layer for PlayStation 5 executables on PC.

It combines **automated toolchain management** (prerequisite detection, 1-click AnyPS5 compiling, and binary executable conversion) with a **Steam / Big Picture-grade interactive visual experience** powered by standard Python 3, a native Windows executable wrapper (`AnyPS5Launcher.exe`), and zero external pip dependencies.

---

## 🏛️ Architecture

AnyPS5 Launcher strictly adheres to local isolation and security standards:

```text
┌─────────────────────────────────────────────────────────────┐
│                 Browser UI (index.html)                    │
│   Vanilla ES6 JS (app.js) + OLED Glassmorphism (style.css) │
│           HTML5 Gamepad API + Web Audio Synthesizer         │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP REST & SSE (Port 8085)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          Local Companion Server (server/main.py)            │
│  - Strictly bound to 127.0.0.1 (Never exposed to 0.0.0.0)   │
│  - Zero third-party pip dependencies (Pure Python 3.8+ std) │
│  - Path traversal validation & subprocess argument-list     │
│  - Live Server-Sent Events (SSE) stdout/stderr log stream   │
│  - ELF64 binary parser & 3,200+ SCE PRX symbol database     │
└──────────────┬──────────────────────────────┬───────────────┘
               │ Subprocess (Popen list)      │ File I/O
               ▼                              ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│      AnyPS5 Relinker CLI     │ │   Configuration & Data     │
│ relinker [opts] <elf> <out>  │ │  - anyps5-input.ini        │
│ --windows / --windows-gui    │ │  - launcher.config.json    │
│ --windows-diagnostics        │ │  - library.json            │
└──────────────────────────────┘ └────────────────────────────┘
```

---

## ✨ Core Features

### 1. ⚙️ Toolchain Hub & Automated AnyPS5 Compiler
- **Instant Host Audit**: Automatically detects Git, Python 3, CMake, Ninja, C++ Toolchains (MSVC, Clang, GCC), and Vulkan 1.3 Drivers with real-time status pills and system paths (`/api/tools`).
- **1-Click Clone & Sync**: Clones `boykopovar/AnyPS5` or pulls upstream commits into `./AnyPS5` with a single click.
- **CMake + Ninja Build Engine**: Configures and compiles `relinker.exe` with stdout streaming directly to the live console drawer.

### 2. 🔄 Relink & Convert Studio
- **Direct Binary Translation**: Converts dumped PlayStation 5 game packages into standalone Windows PE32+ executables (`game.exe`).
- **Official CLI Arguments**: Uses canonical AnyPS5 flags (`--windows`, `--windows-gui`, `--windows-diagnostics`, `--trace-imports`, `--to-intel`).
- **Direct Library Integration**: Automatically imports newly converted executables into your local library.

### 3. 🎮 Big Picture Game Library
- **Scans Configured Folders**: Automatically discovers `eboot.bin` / ELF games in your library directory.
- **Local Persistence (`library.json`)**: Tracks favorites, play times, launch counts, custom titles, and compatibility notes locally.
- **Cover Art & Badges**: Clean presentation with zero copyrighted assets bundled.

### 4. 🕹️ DualSense Visualizer & INI Editor
- **Live Controller Feedback**: Uses the HTML5 Gamepad API to animate DualSense buttons and analog sticks in real-time.
- **Canonical INI Format**: Reads and writes standard `Action = Type:Value` format in `anyps5-input.ini`, preserving comments, blank lines, and custom bindings.
- **Deadzone Calibration**: Configure and persist left/right analog stick deadzones.

### 5. 🔬 Real ELF64 & PRX Compatibility Scanner
- **Zero-Dependency Binary Parser**: Directly inspects ELF magic bytes, 64-bit headers, AMD64 machine target (`0x3E`), entry points, and dynamic symbol tables (`.dynsym` / `.symtab`).
- **Authentic AnyPS5 Symbol Database**: Compares imported SCE functions against versioned AnyPS5 database (3,200+ implemented symbols) to compute genuine compatibility scores and highlight missing stubs.

### 6. 📟 Real-Time Log Terminal Drawer
- **Server-Sent Events (SSE)**: Streams stdout/stderr from active processes, builds, or game instances without page reloads.
- **Color-Coded Tags**: Distinguishes `[relinker]`, `[build]`, `[vulkan]`, and `[warn]` messages.

---

## 🚀 Quick Start

AnyPS5 Launcher runs as a true standalone desktop application window (no URL bar, no browser tabs):

### Method 1: Double-Click `AnyPS5Launcher.exe` (Windows Recommended)
Simply double-click **`AnyPS5Launcher.exe`**:
- Spawns the local server silently in the background.
- Opens the interface immediately in its own hardware-accelerated desktop window.
- Automatically cleans up the background server on application exit.

### Method 2: Double-Click `launch.bat`
Double-clicking **`launch.bat`** verifies Python and launches the app.

### Method 3: Command Line (Cross-Platform)
```bash
# Clone the repository
git clone https://github.com/ErenYeager1836/AnyPS5-Launcher.git
cd AnyPS5-Launcher

# Start local companion server (Zero external dependencies or pip install needed!)
python server/main.py
```
Open your browser to `http://127.0.0.1:8085`.

---

## 🧪 Testing With Demo Fixture

AnyPS5 Launcher bundles a clean, legal test fixture under `fixtures/demo_game/` containing a valid minimal 64-bit ELF binary (`eboot.bin`) and metadata (`param.json`):
1. Navigate to the **Relink & Convert** tab (pre-filled with `fixtures/demo_game`).
2. Click **START CONVERSION & RELINKING**.
3. Watch the relinker progress and inspect real-time logs in the bottom drawer.
4. Click **Play Now** to test process spawning, monitoring, and clean termination!

---

## 🧪 Automated Test Suite

The project includes unit and integration tests covering path-traversal security, config validation, canonical INI round-trips, ELF64 parsing, and REST/SSE endpoints.

Run tests using Python's built-in `unittest` runner:
```bash
python -m unittest discover tests -v
```

All 20+ tests execute in under 2 seconds with zero third-party packages.

---

## 🔧 Configuration (`launcher.config.json`)

Settings are managed via `launcher.config.json` or the **Settings** modal in the UI:

```json
{
  "host": "127.0.0.1",
  "port": 8085,
  "anyps5_path": "C:/Users/.../AnyPS5/build/relinker.exe",
  "anyps5_source_path": "C:/Users/.../AnyPS5",
  "library_folder": "C:/Users/.../PS5_Games",
  "output_folder": "./converted_games"
}
```

*Note: For security reasons, `host` is hardcoded to `127.0.0.1` and cannot be modified to listen on public networks.*

---

## 🛠️ Troubleshooting

### 1. Port 8085 is in use
If another application is using port 8085, you can pass `--port <num>` or edit `launcher.config.json`:
```bash
python server/main.py --port 8090
```

### 2. AnyPS5 Relinker executable not found
Go to the **Toolchain & Setup** tab. Click **Clone AnyPS5** to fetch the source repository, then click **Build Relinker** to compile `relinker.exe` automatically using CMake and Ninja.

### 3. Controller not responding
Ensure your gamepad is connected and press any button to wake the browser Gamepad API. Physical controllers are handled automatically; custom keyboard/mouse mappings can be configured in the **Input Config** tab and saved to `anyps5-input.ini`.

---

## 📂 Project Structure

```text
AnyPS5-Launcher/
├── AnyPS5Launcher.exe       # Standalone Windows native desktop application executable
├── launch.bat               # Windows batch starter
├── launcher.py              # CLI entry point forwarder
├── launcher.config.json     # Launcher path and server settings
├── anyps5-input.ini         # Canonical controller & keybinding configuration
├── library.json             # Local library metadata and play history
├── server/
│   ├── main.py              # Local HTTP & SSE server (127.0.0.1 only)
│   ├── config.py            # Path validation & configuration manager
│   ├── input_config.py      # Canonical Action=Type:Value INI parser & serializer
│   ├── elf_scanner.py       # ELF64 parser & SCE PRX compatibility scanner
│   └── data/
│       └── anyps5_symbols.json # 3,200+ AnyPS5 implemented PRX symbols
├── tests/
│   ├── test_config.py       # Config validation & localhost enforcement tests
│   ├── test_input_config.py # INI parsing, comment preservation & deadzone tests
│   ├── test_elf_scanner.py  # ELF64 parser & symbol scoring tests
│   └── test_endpoints.py    # HTTP endpoints, SSE & path traversal security tests
├── fixtures/
│   └── demo_game/           # Minimal legal test package (ELF64 eboot.bin + param.json)
├── css/
│   └── style.css            # OLED glassmorphic UI design system
├── js/
│   └── app.js               # Frontend controller, audio synth, and API client
├── docs/
│   ├── STATUS.md            # Feature audit table and completion status
│   └── ANYPS5_INTERFACE.md  # AnyPS5 CLI specification, INI format & exit codes
├── index.html               # Main desktop interface
├── LICENSE                  # MIT License
└── README.md                # Documentation
```

---

## ⚖️ Legal & Disclaimer

AnyPS5 Launcher is an independent open-source frontend and workflow automation utility. It is not affiliated with Sony Interactive Entertainment Inc., nor does it redistribute AnyPS5.

This project **does not contain any copyrighted Sony PlayStation 5 game files, decryption keys, or proprietary firmware**. Users must dump their own legitimate software from consoles they own.

---

## 👤 Author

* **Nithishvelan M** ([@ErenYeager1836](https://github.com/ErenYeager1836))
