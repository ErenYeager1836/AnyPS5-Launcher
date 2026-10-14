# AnyPS5 Launcher Feature Audit & Implementation Status

This document provides an honest, comprehensive audit of every feature in the AnyPS5 Launcher repository, identifying whether each feature is fully backed by real AnyPS5 engine integration or currently simulated with demo data and timers.

Last updated: Phase 0 Audit (October 2026).

---

## 📊 Feature Status Matrix

| Feature | Current State | Backing Implementation | Next Action / Target Architecture |
| :--- | :--- | :--- | :--- |
| **Relink & Launch Pipeline** | ⚠️ **Mocked (Simulation)** | UI runs hardcoded `setTimeout` sequences (700ms–2800ms) with fake log strings and random PID generation. | Replace with `POST /api/launch` using `subprocess.Popen` (without `shell=True`) invoking native `relinker.exe` or converted `.exe`. Stream real process events. |
| **Console Drawer (Engine Logs)** | ⚠️ **Mixed / Mocked** | Backend holds in-memory ring buffer, but frontend appends artificial logs; `/api/convert` falls back to `mock_relinker.py` simulation lines. No SSE stream. | Implement `GET /api/logs/stream` via Server-Sent Events (SSE) streaming real `stdout` and `stderr` directly from the running subprocess. |
| **ELF / PRX Diagnostics Scanner** | ⚠️ **Mocked (Demo Data)** | Renders a static hardcoded array (`sampleSymbols`, 9 items). Scores (98%, 95%, etc.) are static numbers in `gamesDatabase`. `/api/elf-inspect` only checks ELF magic bytes. | Parse ELF64 headers, dynamic section (`PT_DYNAMIC`), and symbol tables (`.dynsym`/`.rela.dyn`) to extract imported NID hashes. Compare against AnyPS5's real PRX database (`progress.json`). |
| **`anyps5-input.ini` Editor** | ⚠️ **Invalid Format** | Writes an INI file with custom sections (`[Controller]`, `[Bindings]`) and custom keys (`deadzone_left`) not recognized by AnyPS5. | Rewrite parser and serializer to conform strictly to AnyPS5's official format: `Action = Type:Value` (no section headers, SDL key/mouse values). |
| **Gamepad Visualizer** | ⚠️ **Mocked (Keyboard Only)** | SVG controller is static; only responds to a single keydown event on the Cross button. Does not read physical gamepads. | Implement HTML5 Gamepad API loop (`navigator.getGamepads()`) with live polling for DualSense, Xbox, and standard HID controllers. |
| **Game Library Grid** | ⚠️ **Mocked (Hardcoded)** | Hardcoded array of 4 fictional titles (`Astro Odyssey`, `Shadow of the Ronin`, etc.). Adding a game only appends to in-memory array. | Scan configured library folder (`launcher.config.json`) for `eboot.bin` / ELF directories. Read local `param.json` or user metadata. Persist in local storage. |
| **Toolchain Hub Diagnostics** | ✅ **Real** | `/api/tools` checks host environment for `git`, `python`, `cmake`, `ninja`, C++ compilers (`cl`, `gcc`, `clang`, `vswhere`), and Vulkan SDK / loader DLL. | Refactor into `server/` architecture with clean error reporting. |
| **AnyPS5 Git Clone & Sync** | ✅ **Real** | `/api/tools/clone` clones `boykopovar/AnyPS5` or runs `git pull --recurse-submodules`. | Retain and bind strictly to 127.0.0.1 with path traversal protection. |
| **CMake & Ninja Build Engine** | ⚠️ **Partially Real** | `/api/tools/build` triggers CMake configure and build, but uses `shell=True` and lacks robust target selection (`--target relinker`). | Migrate to `subprocess.Popen` with argument lists (no `shell=True`), targeting `relinker`. |

---

## 🏷️ Visual Transparency: Demo Data Badges

As of Phase 0, all mocked features in the user interface display an amber **"Demo Data"** or **"Simulated"** badge to ensure complete transparency with users:

1. **Library Cards & Hero Showcase:** Tagged with `Demo Data` to indicate fictional test records.
2. **Diagnostics Table:** Tagged with `Mock Symbols` to indicate hardcoded sample symbols.
3. **Controller Visualizer:** Tagged with `Demo Mode` indicating simulated key-capture.
4. **Relinker Studio:** Displays `Simulation Mode` when no native AnyPS5 binary is present.

---

## 🗺️ Roadmap to 100% Real Integration

- [x] **Phase 0:** Audit & Honesty (this document, `docs/ANYPS5_INTERFACE.md`, demo badges).
- [x] **Phase 1:** Local Backend Skeleton (`server/main.py`, `launcher.config.json`, 127.0.0.1 binding, path traversal guard).
- [x] **Phase 2:** Real Launch & Live Console (SSE stdout/stderr streaming, `POST /api/launch`, `POST /api/stop`, real process status).
- [ ] **Phase 3:** Library Ingestion (real folder scan for `eboot.bin`, metadata store in JSON, local covers).
- [ ] **Phase 4:** Real ELF/PRX Scanner (ELF64 parser, AnyPS5 3,249+ symbol database from `progress.json`, real missing symbol calculation).
- [ ] **Phase 5:** Input Configurator (`anyps5-input.ini` round-trip preservation, Gamepad API visualizer, deadzone/trigger validation).
- [ ] **Phase 6:** Quality & Release (Pytest suite, CI GitHub Actions, comprehensive README, release artifacts).
