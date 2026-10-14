# AnyPS5 Launcher ⚡

> **The Ultimate All-in-One Desktop Companion for [AnyPS5](https://github.com/boykopovar/AnyPS5): Automated Toolchain Setup, Source Compiler, Game Relinker Studio, Big Picture Library, DualSense Visualizer & ELF64 Diagnostics.**

[![Platform: Windows & Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue?style=flat-square)](https://github.com/boykopovar/AnyPS5)
[![Backend: Zero Dependencies](https://img.shields.io/badge/Backend-Python%20Standard%20Library-green?style=flat-square)](launcher.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![Design: Pure Vector & CSS](https://img.shields.io/badge/Aesthetics-OLED%20Glassmorphism-cyan?style=flat-square)](css/style.css)

AnyPS5 Launcher is a modern, high-performance desktop hub and developer suite for **AnyPS5**, the PlayStation 5 to PC static relinker and compatibility layer.

It combines **automated toolchain management** (prerequisite detection, 1-click AnyPS5 compiling, and binary executable conversion) with a **Steam / Big Picture-grade interactive visual experience** powered by standard Python 3, a native Windows executable wrapper (`AnyPS5Launcher.exe`), and zero external dependencies.

---

## 📦 Download

Get the standalone Windows release from the [**Releases**](https://github.com/ErenYeager1836/AnyPS5-Launcher/releases) page:
1. Download [**`AnyPS5-Launcher-windows-v1.0.0.zip`**](https://github.com/ErenYeager1836/AnyPS5-Launcher/releases/latest/download/AnyPS5-Launcher-windows-v1.0.0.zip).
2. Extract anywhere on your PC.
3. Double-click **`AnyPS5Launcher.exe`** (or `launch.bat`).

---

## ✨ Core Highlights

### 1. ⚙️ Toolchain Hub & Automated AnyPS5 Compiler
- **Instant Host Audit**: Automatically detects Git, Python 3, CMake, Ninja, C++ Toolchains (MSVC, Clang, GCC), and Vulkan 1.3 Drivers with real-time status pills and system paths (`/api/tools`).
- **1-Click Clone & Sync**: Clones `boykopovar/AnyPS5` or pulls upstream commits into `./AnyPS5` with a single click.
- **CMake + Ninja Build Engine**: Configures and compiles `relinker.exe` with stdout streaming directly to the console terminal.

### 2. 🔄 Relink & Convert Studio
- **Direct Binary Translation**: Converts dumped PlayStation 5 game packages into standalone Windows PE32+ executables (`game.exe`).
- **Full CLI Customization**: Toggle between standard console `--windows` and clean windowless `--windows-gui`, plus `--lazy-binding` and `--trace-imports`.
- **Direct Library Integration**: Finished conversions can be added straight to the Game Library Grid with a single click to play immediately.

### 3. 🎮 Big Picture Game Library
- **Visual Game Cards**: Filterable by Playable vs. In-Game status, searchable by title, publisher, or TitleID (`PPSA...`).
- **Hero Showcase**: Displays selected game parameters (target FPS, internal resolution, compiled shader cache count).
- **Web Audio Feedback**: Tactile acoustic clicks and launch sounds reminiscent of modern console interfaces.

### 4. 🕹️ Interactive DualSense & Input Visualizer
- **Live SVG Gamepad**: Animated PlayStation 5 DualSense controller with real-time button response.
- **Deadzone & Trigger Calibration**: Dynamic left/right stick deadzone sliders and haptic feedback toggles.
- **Direct INI Persistence**: Reads and writes directly to `anyps5-input.ini` on disk (`/api/input`).

### 5. 🔬 Real 64-bit ELF Binary Diagnostics
- **Header Inspection**: Direct file parser (`/api/elf-inspect`) verifying ELF magic bytes, AMD64 machine code (`0x3E`), entry points, and 64-bit mode.
- **SCE PRX Coverage Matrix**: Audits imported Sony PRX functions (`libkernel`, `libSceVideoOut`, `libScePad`, `libSceAudioOut`) with resolution status and fallback hooks.

### 6. 📟 Real-Time Log Terminal Drawer
- **Live Process Monitoring**: Streams stdout/stderr from active conversion jobs, builds, or game instances.
- **Color-Coded Tags**: Distinguishes `[relinker]`, `[build]`, `[vulkan]`, `[audio]`, and `[warn]` messages.

---

## 🚀 Quick Start (Native Desktop App)

You do **not** need to use a browser tab or see `http://localhost:8085`. AnyPS5 Launcher runs as a true standalone Windows desktop application window (no URL bar, no tabs, no navigation toolbar):

### Method 1: Double-Click `AnyPS5Launcher.exe` (Recommended)
Simply double-click **`AnyPS5Launcher.exe`**.
- Starts the background service silently (no command prompt window).
- Opens the interface immediately in its own dedicated, hardware-accelerated desktop application window.
- Automatically closes the background server when you exit the app.

### Method 2: Double-Click `launch.bat`
Double-clicking **`launch.bat`** automatically verifies Python and launches `AnyPS5Launcher.exe`.

### Method 3: Command Line
```bash
# Clone the repository
git clone https://github.com/ErenYeager1836/AnyPS5-Launcher.git
cd AnyPS5-Launcher

# Run with standard Python (Zero external dependencies or pip install required!)
python server/main.py
```

---

## 🧪 Testing Without Commercial Games

AnyPS5 Launcher includes a clean, legal homebrew fixture under `fixtures/demo_game/` containing a valid minimal 64-bit ELF binary (`eboot.bin`) and metadata (`param.json`):
1. Open the **Relink & Convert** tab (pre-filled with `fixtures/demo_game`).
2. Click **START CONVERSION & RELINKING**.
3. Watch the relinker progress bar fill and inspect real-time logs in the bottom drawer.
4. Click **Add to Library & Play Now** to test full lifecycle execution!

---

## 📂 Project Structure

```text
AnyPS5-Launcher/
├── AnyPS5Launcher.exe       # Standalone Windows native desktop application executable
├── launch.bat               # Windows batch starter
├── launcher.py              # Python companion engine (IPC, build, relink, ELF parser)
├── mock_relinker.py         # Standalone test runner for relinker pipeline simulation
├── anyps5-input.ini         # Controller & keybinding configuration
├── src/
│   └── LauncherApp.cs       # Native C# source for AnyPS5Launcher.exe wrapper
├── fixtures/
│   └── demo_game/           # Minimal test package (valid ELF64 eboot.bin + param.json)
├── css/
│   └── style.css            # OLED glassmorphic UI system, toolchain cards, convert grid
├── js/
│   └── app.js               # Frontend controller, toolchain auditor, audio synth, API client
├── index.html               # Main desktop interface
└── README.md                # Documentation
```

---

## ⚖️ Legal & Disclaimer

AnyPS5 Launcher is an independent open-source frontend and workflow automation utility. It does not contain any copyrighted Sony PlayStation 5 game files, decryption keys, or proprietary firmware. Users must dump their own legitimate software from consoles they own.

---

## 👤 Author

* **Nithishvelan M** ([@ErenYeager1836](https://github.com/ErenYeager1836))
