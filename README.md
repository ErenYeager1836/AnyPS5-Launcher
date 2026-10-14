# AnyPS5 Launcher ⚡

> **Next-Generation Game Hub, ELF Diagnostics Scanner & Input Configurator for the [AnyPS5](https://github.com/boykopovar/AnyPS5) Compatibility Layer.**

![AnyPS5 Launcher Hero Banner](assets/images/hero_astro.jpg)

AnyPS5 Launcher is an open-source companion frontend designed specifically for **AnyPS5**, the PlayStation 5 to PC static relinker and compatibility runtime. It bridges the gap between raw command-line tools and a console-grade gaming experience.

---

## ✨ Features

- 🎮 **Steam & Big Picture-Inspired Library**:
  - Grid view featuring high-resolution box art, title badges, and target performance specs.
  - One-click **Relink & Launch** with animated launch pipeline status.
  - Search, filter by compatibility (`Playable`, `In-Game`), and sort.
- 🔬 **Built-in ELF & PRX Diagnostics Scanner**:
  - Drag and drop any `eboot.bin` or PS5 ELF to inspect symbol coverage before playing.
  - Live compatibility score calculator that highlights implemented vs missing SCE system functions.
- 🕹️ **Interactive Controller & `anyps5-input.ini` Editor**:
  - Real-time SVG visualizer for DualSense and XInput gamepads.
  - Deadzone calibration sliders and trigger haptic profiles.
- 📊 **Real-Time Relinker Console Drawer**:
  - Bottom slide-up terminal console displaying live logs from the `anyps5` engine, Vulkan swapchain, and audio backend.
- 🎵 **Synthesized Audio Engine**:
  - Built-in Web Audio API sound effects for smooth, satisfying console UI acoustics.
- ⚡ **Zero-Dependency Architecture**:
  - Pure HTML5, Modular ES6, and Vanilla CSS. No bulky node_modules or build steps required.

---

## 🚀 Quick Start

### Running Locally

You can launch the frontend immediately using Python's built-in web server:

```bash
cd anyps5-launcher
python -m http.server 8080
```

Then open your browser at:
```text
http://localhost:8080
```

---

## 📂 Project Structure

```text
anyps5-launcher/
├── assets/
│   └── images/              # High-res box art and wide banners
├── css/
│   └── style.css            # Dark mode glassmorphism design system
├── js/
│   └── app.js               # Client runtime, diagnostics, audio synth
├── index.html               # Main application interface
└── README.md                # Documentation
```

---

## ⚖️ Legal & Disclaimer

AnyPS5 Launcher is an independent open-source frontend. It does not contain any copyrighted Sony PlayStation 5 game files, decryption keys, or firmware. Users must dump their own legitimate game executables from consoles they own.

---

## 👤 Author

* **Nithishvelan M** ([@ErenYeager1836](https://github.com/ErenYeager1836))
