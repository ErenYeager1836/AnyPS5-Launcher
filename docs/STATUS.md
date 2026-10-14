# AnyPS5 Launcher Feature Audit & Implementation Status

This document provides an honest, comprehensive audit of every feature in the AnyPS5 Launcher repository, identifying the backing implementation, architecture, and verification status.

Last updated: Phase 6 Quality & Release (October 2026).

---

## 📊 Feature Status Matrix

| Feature | Current State | Backing Implementation | Verification / Status |
| :--- | :--- | :--- | :--- |
| **Relink & Launch Pipeline** | ✅ **100% Real** | `POST /api/launch` and `POST /api/stop` via `subprocess.Popen` without `shell=True`. Arguments passed as clean lists. Spawns real native processes and terminates cleanly on user command or exit. | Tested & verified in `tests/test_endpoints.py` with valid demo binary. |
| **Console Drawer (Engine Logs)** | ✅ **100% Real** | Server-Sent Events (`/api/logs/stream`) connected via HTML5 `EventSource`. Real stdout and stderr piped directly from running processes with color-coded tags (`[relinker]`, `[vulkan]`, `[anyps5]`). | Verified live stream in test suite and runtime. |
| **ELF / PRX Diagnostics Scanner** | ✅ **100% Real** | Zero-dependency ELF64 parser (`server/elf_scanner.py`) extracting section headers, dynamic symbols, and SCE strings. Compares directly against AnyPS5's versioned symbol database (3,200+ symbols) to calculate genuine compatibility scores and stub listings. | Verified in `tests/test_elf_scanner.py` with 64-bit AMD64 ELF binaries. |
| **`anyps5-input.ini` Editor** | ✅ **100% Real** | Canonical AnyPS5 input specification parser and serializer (`server/input_config.py`). Adheres strictly to `Action = Type:Value` format without invalid section headers. Preserves comments, blank lines, deadzone metadata, and custom keys during round-trips. | Verified in `tests/test_input_config.py` with multi-line round-trip tests. |
| **Gamepad Visualizer** | ✅ **100% Real** | HTML5 Gamepad API loop (`navigator.getGamepads()`) actively polls physical controllers (DualSense, Xbox, standard HID gamepads). Lights up SVG buttons, triggers, and analog sticks dynamically. | Live polling loop verified on standard gamepads. |
| **Game Library Grid** | ✅ **100% Real** | Backend recursively discovers `eboot.bin` / ELF games in configured library folder and `converted_games/`. Local metadata (`library.json`) persists custom titles, favorites, play history, and user notes without bundling copyrighted art. | Verified in `tests/test_endpoints.py`. |
| **Toolchain Hub Diagnostics** | ✅ **100% Real** | `/api/tools` audits host system for Git, Python 3, CMake, Ninja, MSVC / Clang / GCC toolchains, and Vulkan 1.3 drivers. | Verified across Windows and Linux environments. |
| **AnyPS5 Git Clone & Sync** | ✅ **100% Real** | `/api/tools/clone` clones `boykopovar/AnyPS5` or pulls upstream commits into `./AnyPS5` with submodule recursion. | Argument-list subprocess execution strictly on 127.0.0.1. |
| **CMake & Ninja Build Engine** | ✅ **100% Real** | `/api/tools/build` invokes CMake configure (`-G Ninja`) and compiles `relinker.exe` target directly without `shell=True`, streaming compiler output to the drawer. | Verified with build target isolation. |

---

## 🗺️ Roadmap to 100% Real Integration

- [x] **Phase 0:** Audit & Honesty (`docs/STATUS.md`, `docs/ANYPS5_INTERFACE.md`, demo badges).
- [x] **Phase 1:** Local Backend Skeleton (`server/main.py`, `launcher.config.json`, 127.0.0.1 binding, path traversal guard).
- [x] **Phase 2:** Real Launch & Live Console (SSE stdout/stderr streaming, `POST /api/launch`, `POST /api/stop`, real process status).
- [x] **Phase 3:** Library Ingestion (real folder scan for `eboot.bin`, metadata store in `library.json`, local covers).
- [x] **Phase 4:** Real ELF/PRX Scanner (ELF64 parser, AnyPS5 3,200+ symbol database from `progress.json`, real missing symbol calculation).
- [x] **Phase 5:** Input Configurator (`anyps5-input.ini` round-trip preservation, Gamepad API visualizer, deadzone/trigger validation).
- [x] **Phase 6:** Quality & Release (20 unit/integration tests, multi-platform GitHub Actions CI, comprehensive README rewrite, LICENSE, CONTRIBUTING.md, issue templates).
