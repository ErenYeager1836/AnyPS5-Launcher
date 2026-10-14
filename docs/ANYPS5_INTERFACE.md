# AnyPS5 Engine Interface Specification

Authoritative documentation on the real CLI flags, configuration formats, log streams, and system symbol interfaces used by **AnyPS5** (`boykopovar/AnyPS5`).

This specification guides all launcher backend endpoints and ensures the launcher never invents non-existent flags or writes invalid configuration files.

---

## 1. Upstream Engine Architecture

AnyPS5 is a static binary relinker and compatibility layer, **not** an emulator or virtual machine. It works by:
1. Parsing the input PlayStation 5 ELF64 executable (`eboot.bin` or decrypted ELF).
2. Resolving imported function NIDs (Numeric IDs) against native reimplementations of Sony PRX libraries (located in `core/libs/prx`).
3. Stripping or redirecting raw Sony system calls.
4. Constructing a native target dynamic section and generating a native executable:
   - **Windows:** PE32+ `.exe`
   - **Linux:** Native ELF64
   - **macOS:** x86-64 Mach-O (under Rosetta)
5. Translating console shader pipelines (AMD RDNA / Agc / Gnm) into Vulkan SPIR-V.

---

## 2. CLI Command Syntax: `relinker`

The core relinking utility is `relinker` (built into `build/bin/relinker.exe` on Windows or `build/bin/relinker` on Linux).

### General Syntax

```bash
relinker [options] <input.elf> <output>
```

### Exit Codes & Stream Behaviors

| Exit Code | Cause | Output Stream |
| :---: | :--- | :--- |
| `0` | Success, or `--help` requested | Informational messages to `stdout` |
| `1` | Syntax error, unrecognized options, or missing input/output arguments | Usage manual and error message to `stderr` |
| `2` | Relinking or ELF processing failure | Detailed runtime error to `stderr` |

* **Uncaught Exceptions:** AnyPS5 throws `std::runtime_error`; the error text is written to `stderr` before process termination.
* **CPU Extension Check:** Converted binaries verify Zen 2 instruction extensions (AVX2, FMA, F16C, BMI1, BMI2, LZCNT, MOVBE) at startup. Missing extensions cause the executable to abort and log missing instruction sets.

### Command-Line Switches & Arguments

| Flag | Category | Description |
| :--- | :--- | :--- |
| `--help` | Help | Prints usage manual to `stdout` and exits with code 0. No file arguments required. |
| `--windows` | Target | Produces a standard Windows PE32+ (`.exe`) executable targeting the console subsystem. |
| `--windows-gui` | Target Subsystem | Selects the Windows GUI subsystem instead of the console subsystem (windowless). Requires `--windows`. |
| `--windows-diagnostics` | Diagnostics | Includes startup dependency diagnostics in the generated executable. Requires `--windows`. |
| `--windows-fixed-base <addr>` | Memory Layout | Maps lowest ELF load page at a fixed address (64 KiB-aligned, `0x20000` to `0x7fffffff0000`). Main executable has no ASLR. Requires `--windows`. |
| `--linux-fixed-base <addr>` | Memory Layout | Loads Linux executable at a fixed address (`0x10000` to `0x7fffffff0000`). Conflicts with `--windows`. |
| `--macos` | Target | Produces an x86-64 Mach-O executable for macOS under Rosetta. Conflicts with `--windows`. |
| `--to-intel` | CPU Translation | Converts AMD-only CPU instructions into Intel-compatible instructions. |
| `--to-rosetta` | CPU Translation | Converts AMD instructions and patches Rosetta deficiencies (RDSEED -> RDRAND, CLWB -> NOP). Conflicts with `--windows`. |
| `--trace-imports` | Debugging | Passes each function import through `libc.prx` call tracer. Requires `--windows`. |
| `--sce-module-path <path>` | Modules | Specifies parent directory containing bundled modules (`sce_module/`, `sce_modules/`, or `prx/`). |
| `unused-filter=0` | Import Optimization | Keeps all imported NID references (default). |
| `unused-filter=1` | Import Optimization | Filters unused non-PLT imports using control-flow and GOT access analysis. |
| `unused-filter=2` | Import Optimization | Strict unused-import analysis and PLT compaction. |

> [!WARNING]
> **Deprecated Flags (Do Not Use):**
> Upstream marks `--lazy-binding`, `--skip-sce-module`, `--exclude-sce-module <file>`, and `--skip-syscall-check` as deprecated. The launcher must not invoke these flags.

---

## 3. Input Mapping Specification: `anyps5-input.ini`

AnyPS5 supports SDL2-compatible gamepads automatically (DualSense, DualShock 4, Xbox Wireless Controllers). Custom keyboard, mouse, and wheel bindings are configured through `anyps5-input.ini`.

### File Location
1. Directly beside the generated game `.exe` (default).
2. At a custom path specified by the `ANYPS5_INPUT_CONFIG` environment variable.

### Format Rules
- Line format: `Action = Type:Value`
- **No section headers** (do **not** include `[Controller]` or `[Bindings]`).
- Action names are **case-insensitive**.
- Comments start with `#` or `;`.
- The first entry for an action replaces its built-in binding; subsequent entries add alternate secondary inputs.
- UTF-8 encoding (with or without BOM).

### Supported Input Types
- `KEY:<KeyName>` — Any key name accepted by SDL (e.g., `KEY:Space`, `KEY:Return`, `KEY:Escape`, `KEY:W`, `KEY:A`, `KEY:S`, `KEY:D`).
- `MOUSE:<Button>` — `MOUSE:Left`, `MOUSE:Middle`, `MOUSE:Right`, `MOUSE:X1`, `MOUSE:X2`.
- `WHEEL:<Direction>` — `WHEEL:Up`, `WHEEL:Down`.

### Supported Action Names
- **Face Buttons:** `Cross`, `Circle`, `Triangle`, `Square`
- **Shoulder & Triggers:** `L1`, `R1`, `L2`, `R2`
- **Stick Clicks:** `L3`, `R3`
- **Menu & Navigation:** `Options`, `Up`, `Right`, `Down`, `Left`
- **Left Analog Emulation:** `LeftStickLeft`, `LeftStickRight`, `LeftStickUp`, `LeftStickDown`
- **Right Analog Emulation:** `RightStickLeft`, `RightStickRight`, `RightStickUp`, `RightStickDown`
- **Touchpad Clicks:** `TouchLeft`, `TouchRight`
- **System Toggles:** `ToggleMouse`, `ToggleFullscreen`

### Canonical Example `anyps5-input.ini`
```ini
# AnyPS5 Input Configuration
Cross = KEY:Space
Circle = KEY:Escape
Square = KEY:R
Triangle = KEY:F
L1 = KEY:Q
R1 = KEY:E
L2 = MOUSE:Right
R2 = MOUSE:Left
Options = KEY:Return
LeftStickUp = KEY:W
LeftStickLeft = KEY:A
LeftStickDown = KEY:S
LeftStickRight = KEY:D
ToggleFullscreen = KEY:F11
ToggleMouse = KEY:F1
```

---

## 4. SCE PRX Symbol Database & Coverage Scoring

AnyPS5 implements PlayStation 5 system functions across modular PRX libraries:
- `libkernel.prx` (Threads, virtual memory, synchronizations, epoll/equeue)
- `libSceAgc.prx` / `libSceGnm.prx` (Low-level GPU command buffers and context)
- `libScePad.prx` (DualSense / gamepad input)
- `libSceAudioOut.prx` / `libSceAudio3d.prx` (Sound output and spatialization)
- `libSceVideoOut.prx` (Display output and Vulkan swapchain presentation)
- `libSceSaveData.prx` (User save file virtual filesystem mounts)

### Upstream Progress Tracking
- Live status tracked in `boykopovar/AnyPS5`: `tools/progress.py` -> `https://boykopovar.github.io/AnyPS5/progress.json`
- Over **3,249** declared functions are actively implemented.
- The launcher scanner inspects the PS5 ELF's dynamic imports, checks which NIDs and function symbols are required, and compares them against the local versioned `server/data/anyps5_symbols.json` symbol database to compute an authentic compatibility score:

$$\text{Compatibility Score} = \left(\frac{\text{Implemented Functions}}{\text{Total Required Imported Functions}}\right) \times 100\%$$
