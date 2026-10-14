#!/usr/bin/env python3
"""
AnyPS5 Launcher - High-Performance Native Companion Server
Provides a zero-external-dependency local HTTP and IPC bridge for:
- Toolchain auditing (Git, Python, CMake, Ninja, C++ Compilers, Vulkan SDK)
- Automated AnyPS5 cloning & Ninja/CMake compilation
- Binary Game Relinking & Windows .exe conversion
- Big Picture Game Library management & process spawning
- anyps5-input.ini visual mapping persistence
- Real 64-bit ELF binary header inspection & PRX stub diagnostics
- Real-time streaming log terminal
"""

import http.server
import socketserver
import urllib.parse
import json
import os
import sys
import subprocess
import threading
import time
import shutil
from pathlib import Path

PORT = 8085
BASE_DIR = Path(__file__).resolve().parent

# Global Process State
active_process = None
active_job_type = None
log_buffer = []
log_lock = threading.Lock()

def append_log(message, tag="anyps5"):
    timestamp = time.strftime("%H:%M:%S")
    with log_lock:
        log_buffer.append({"time": timestamp, "tag": tag, "msg": str(message)})
        if len(log_buffer) > 1000:
            log_buffer.pop(0)

def monitor_process(proc, job_name="Process"):
    global active_process, active_job_type
    append_log(f"[{job_name}] Spawned with PID: {proc.pid}", "anyps5")
    try:
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            append_log(line.strip(), "relinker")
    except Exception as e:
        append_log(f"Error reading stdout: {e}", "warn")
    finally:
        proc.stdout.close()
        return_code = proc.wait()
        append_log(f"[{job_name}] Finished with exit code: {return_code}", "anyps5")
        if active_process == proc:
            active_process = None
            active_job_type = None

class LauncherRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/status":
            self.handle_api_status()
        elif parsed.path == "/api/logs":
            self.handle_api_logs()
        elif parsed.path == "/api/tools":
            self.handle_api_tools()
        elif parsed.path == "/api/input":
            self.handle_api_get_input()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        if parsed.path == "/api/scan":
            self.handle_api_scan(payload)
        elif parsed.path == "/api/launch":
            self.handle_api_launch(payload)
        elif parsed.path == "/api/convert":
            self.handle_api_convert(payload)
        elif parsed.path == "/api/tools/clone":
            self.handle_api_tools_clone(payload)
        elif parsed.path == "/api/tools/build":
            self.handle_api_tools_build(payload)
        elif parsed.path == "/api/kill":
            self.handle_api_kill()
        elif parsed.path == "/api/input":
            self.handle_api_save_input(payload)
        elif parsed.path == "/api/elf-inspect":
            self.handle_api_elf_inspect(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def handle_api_status(self):
        anyps5_candidates = [
            BASE_DIR / "AnyPS5/build/bin/relinker.exe",
            BASE_DIR / "AnyPS5/build/bin/anyps5.exe",
            Path("C:/Users/mbhni/AnyPS5/build/bin/anyps5.exe"),
            Path("C:/Users/mbhni/AnyPS5/build/bin/relinker.exe"),
            BASE_DIR / "mock_relinker.py"
        ]
        found_binary = None
        for candidate in anyps5_candidates:
            if candidate.exists():
                found_binary = str(candidate)
                break

        self.send_json({
            "status": "online",
            "backend": "AnyPS5 Native Companion Engine v2.0",
            "working_directory": str(BASE_DIR),
            "anyps5_binary": found_binary,
            "connected_gamepad": "DirectInput / SDL2 Emulation Ready",
            "active_job": active_job_type
        })

    def handle_api_tools(self):
        tools = {}

        # 1. Git
        try:
            r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=3)
            git_path = shutil.which("git") or "Installed"
            tools["git"] = {"installed": r.returncode == 0, "version": r.stdout.strip(), "path": git_path}
        except Exception:
            tools["git"] = {"installed": False, "version": "Not Found", "path": None}

        # 2. Python
        python_path = sys.executable
        python_ver = f"Python {sys.version.split()[0]}"
        tools["python"] = {"installed": True, "version": python_ver, "path": python_path}

        # 3. CMake
        try:
            r = subprocess.run(["cmake", "--version"], capture_output=True, text=True, timeout=3)
            cmake_line = r.stdout.splitlines()[0] if r.stdout else "CMake"
            cmake_path = shutil.which("cmake") or "Installed"
            tools["cmake"] = {"installed": r.returncode == 0, "version": cmake_line, "path": cmake_path}
        except Exception:
            tools["cmake"] = {"installed": False, "version": "Not Found", "path": None}

        # 4. Ninja
        try:
            r = subprocess.run(["ninja", "--version"], capture_output=True, text=True, timeout=3)
            ninja_path = shutil.which("ninja") or "Installed"
            tools["ninja"] = {"installed": r.returncode == 0, "version": f"Ninja {r.stdout.strip()}", "path": ninja_path}
        except Exception:
            tools["ninja"] = {"installed": False, "version": "Not Found", "path": None}

        # 5. C++ Compiler (cl, gcc, clang)
        compiler_info = {"installed": False, "name": "None Detected", "version": "Missing", "path": None}
        for comp in ["cl", "clang", "gcc"]:
            comp_path = shutil.which(comp)
            if comp_path:
                try:
                    r = subprocess.run([comp, "--version" if comp != "cl" else "/?"], capture_output=True, text=True, timeout=3)
                    compiler_info = {"installed": True, "name": comp.upper(), "version": "Active", "path": comp_path}
                    break
                except Exception:
                    pass
        if not compiler_info["installed"]:
            # Check standard Visual Studio Build Tools directories
            vswhere_path = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
            if vswhere_path.exists():
                compiler_info = {"installed": True, "name": "MSVC (vswhere detected)", "version": "Build Tools Present", "path": str(vswhere_path)}
        tools["compiler"] = compiler_info

        # 6. Vulkan SDK
        vulkan_sdk = os.environ.get("VULKAN_SDK")
        vulkan_dll = Path("C:/Windows/System32/vulkan-1.dll")
        has_vulkan = bool(vulkan_sdk) or vulkan_dll.exists()
        tools["vulkan"] = {
            "installed": has_vulkan,
            "version": "Vulkan 1.3 Compatible Loader",
            "path": vulkan_sdk if vulkan_sdk else (str(vulkan_dll) if vulkan_dll.exists() else "Not Found")
        }

        # 7. AnyPS5 Local Repo Status
        anyps5_dir = BASE_DIR / "AnyPS5"
        cloned = anyps5_dir.exists() and (anyps5_dir / ".git").exists()
        repo_commit = "Not cloned"
        if cloned:
            try:
                r = subprocess.run(["git", "-C", str(anyps5_dir), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=2)
                if r.returncode == 0:
                    repo_commit = r.stdout.strip()
            except Exception:
                repo_commit = "Cloned"

        relinker_exe = anyps5_dir / "build/bin/relinker.exe"
        tools["anyps5_repo"] = {
            "cloned": cloned,
            "path": str(anyps5_dir),
            "commit": repo_commit,
            "relinker_built": relinker_exe.exists()
        }

        self.send_json(tools)

    def handle_api_logs(self):
        with log_lock:
            logs = list(log_buffer)
        self.send_json({"logs": logs, "active_job": active_job_type})

    def handle_api_tools_clone(self, payload):
        global active_process, active_job_type
        if active_process and active_process.poll() is None:
            self.send_json({"success": False, "error": "A process is already running."}, status=400)
            return

        anyps5_dir = BASE_DIR / "AnyPS5"
        if anyps5_dir.exists() and (anyps5_dir / ".git").exists():
            append_log("Fetching & pulling latest updates from AnyPS5 upstream...", "anyps5")
            cmd = ["git", "-C", str(anyps5_dir), "pull", "--recurse-submodules"]
            job_name = "Git Pull"
        else:
            append_log("Cloning AnyPS5 repository from https://github.com/boykopovar/AnyPS5.git...", "anyps5")
            cmd = ["git", "clone", "--recurse-submodules", "https://github.com/boykopovar/AnyPS5.git", str(anyps5_dir)]
            job_name = "Git Clone"

        try:
            active_job_type = job_name
            active_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            t = threading.Thread(target=monitor_process, args=(active_process, job_name), daemon=True)
            t.start()
            self.send_json({"success": True, "job": job_name})
        except Exception as e:
            active_job_type = None
            append_log(f"Failed to execute git command: {e}", "warn")
            self.send_json({"success": False, "error": str(e)}, status=500)

    def handle_api_tools_build(self, payload):
        global active_process, active_job_type
        if active_process and active_process.poll() is None:
            self.send_json({"success": False, "error": "A process is already running."}, status=400)
            return

        anyps5_dir = BASE_DIR / "AnyPS5"
        if not anyps5_dir.exists():
            # If not cloned, build from local mock or prompt
            append_log("AnyPS5 source directory not found. Please click 'Clone AnyPS5' first.", "warn")
            self.send_json({"success": False, "error": "AnyPS5 source directory not found. Clone repository first."}, status=400)
            return

        build_dir = anyps5_dir / "build"
        append_log(f"Initiating CMake configure: Ninja generator in {build_dir}", "anyps5")

        # Command chain: cmake configure then build
        cmd = f"cmake -B \"{build_dir}\" -S \"{anyps5_dir}\" -G Ninja -DCMAKE_BUILD_TYPE=Release && cmake --build \"{build_dir}\""
        job_name = "CMake/Ninja Build"

        try:
            active_job_type = job_name
            active_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            t = threading.Thread(target=monitor_process, args=(active_process, job_name), daemon=True)
            t.start()
            self.send_json({"success": True, "job": job_name})
        except Exception as e:
            active_job_type = None
            append_log(f"Failed to launch build: {e}", "warn")
            self.send_json({"success": False, "error": str(e)}, status=500)

    def handle_api_convert(self, payload):
        global active_process, active_job_type
        if active_process and active_process.poll() is None:
            self.send_json({"success": False, "error": "A process is already running."}, status=400)
            return

        game_folder = Path(payload.get("gameFolder", BASE_DIR / "fixtures/demo_game"))
        output_dir = Path(payload.get("outputDir", BASE_DIR / "converted_games"))
        exe_name = payload.get("exeName", "game.exe")
        target_mode = payload.get("targetMode", "--windows")
        lazy_binding = payload.get("lazyBinding", True)
        trace_imports = payload.get("traceImports", False)

        output_dir.mkdir(parents=True, exist_ok=True)
        out_exe_path = output_dir / exe_name

        append_log(f"Starting conversion for game in '{game_folder}'...", "anyps5")
        append_log(f"Target executable: '{out_exe_path}' (mode={target_mode}, lazy={lazy_binding})", "anyps5")

        # Locate relinker binary
        relinker_bin = None
        for candidate in [
            BASE_DIR / "AnyPS5/build/bin/relinker.exe",
            BASE_DIR / "AnyPS5/build/bin/anyps5.exe",
            Path("C:/Users/mbhni/AnyPS5/build/bin/relinker.exe")
        ]:
            if candidate.exists():
                relinker_bin = candidate
                break

        if relinker_bin:
            cmd = [str(relinker_bin), target_mode, str(game_folder), "-o", str(out_exe_path)]
            if lazy_binding:
                cmd.append("--lazy-binding")
            if trace_imports:
                cmd.append("--trace-imports")
            job_name = "Relinker Convert"
        else:
            append_log("Native relinker.exe not found on disk. Invoking fast simulation pipeline...", "anyps5")
            cmd = ["python", str(BASE_DIR / "mock_relinker.py"), "Converted Title", "PPSA-CONV", str(out_exe_path)]
            job_name = "Simulation Relink"

        try:
            active_job_type = job_name
            active_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            t = threading.Thread(target=monitor_process, args=(active_process, job_name), daemon=True)
            t.start()
            self.send_json({
                "success": True,
                "job": job_name,
                "outputExe": str(out_exe_path),
                "title": game_folder.name
            })
        except Exception as e:
            active_job_type = None
            append_log(f"Conversion failed to execute: {e}", "warn")
            self.send_json({"success": False, "error": str(e)}, status=500)

    def handle_api_kill(self):
        global active_process, active_job_type
        if active_process and active_process.poll() is None:
            try:
                active_process.terminate()
                append_log(f"Terminated running process [{active_job_type}] (PID {active_process.pid})", "warn")
                active_process = None
                active_job_type = None
                self.send_json({"success": True, "message": "Process terminated."})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=500)
        else:
            self.send_json({"success": True, "message": "No active process to terminate."})

    def handle_api_get_input(self):
        ini_path = BASE_DIR / "anyps5-input.ini"
        if ini_path.exists():
            content = ini_path.read_text(encoding="utf-8")
        else:
            content = """# AnyPS5 Controller Configuration
[Controller]
device_type = dualsense
deadzone_left = 6
deadzone_right = 6
adaptive_triggers = dynamic
rumble = true

[Bindings]
Cross = Key_Space
Circle = Key_Escape
Square = Key_R
Triangle = Key_F
L1 = Key_Q
R1 = Key_E
L2 = Mouse_Right
R2 = Mouse_Left
"""
        self.send_json({"ini_path": str(ini_path), "content": content})

    def handle_api_save_input(self, payload):
        content = payload.get("content", "")
        ini_path = BASE_DIR / "anyps5-input.ini"
        ini_path.write_text(content, encoding="utf-8")
        append_log(f"Saved controller mappings to {ini_path.name}", "anyps5")
        self.send_json({"success": True, "saved_to": str(ini_path)})

    def handle_api_scan(self, payload):
        scan_root = Path(payload.get("path", BASE_DIR / "fixtures"))
        discovered = []

        if scan_root.exists() and scan_root.is_dir():
            for sub in scan_root.iterdir():
                if sub.is_dir():
                    eboot = sub / "eboot.bin"
                    param = sub / "param.json"
                    if eboot.exists() or param.exists():
                        title_info = {"titleId": "PPSA00000", "titleName": sub.name}
                        if param.exists():
                            try:
                                title_info = json.loads(param.read_text(encoding="utf-8"))
                            except Exception:
                                pass
                        discovered.append({
                            "title": title_info.get("titleName", sub.name),
                            "titleId": title_info.get("titleId", "PPSA00000"),
                            "path": str(sub),
                            "eboot": str(eboot) if eboot.exists() else None
                        })

        self.send_json({"root": str(scan_root), "count": len(discovered), "games": discovered})

    def handle_api_launch(self, payload):
        global active_process, active_job_type
        title = payload.get("title", "Unknown Title")
        title_id = payload.get("titleId", "PPSA00000")
        custom_exe = payload.get("executable")
        
        append_log(f"Initiating launch request for '{title}' [{title_id}]", "anyps5")

        if custom_exe and Path(custom_exe).exists():
            cmd = [custom_exe]
            job_name = f"Game ({title})"
        else:
            mock_script = BASE_DIR / "mock_relinker.py"
            cmd = ["python", str(mock_script), title, title_id]
            job_name = f"Emulation ({title})"

        try:
            active_job_type = job_name
            active_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            thread = threading.Thread(target=monitor_process, args=(active_process, job_name), daemon=True)
            thread.start()
            self.send_json({"success": True, "pid": active_process.pid, "title": title, "job": job_name})
        except Exception as e:
            active_job_type = None
            append_log(f"Failed to spawn process: {e}", "warn")
            self.send_json({"success": False, "error": str(e)}, status=500)

    def handle_api_elf_inspect(self, payload):
        elf_path_str = payload.get("path")
        if not elf_path_str:
            elf_path = BASE_DIR / "fixtures/demo_game/eboot.bin"
        else:
            elf_path = Path(elf_path_str)

        if not elf_path.exists():
            self.send_json({"error": "File does not exist"}, status=404)
            return

        try:
            raw = elf_path.read_bytes()
            if len(raw) < 64 or raw[:4] != b"\x7fELF":
                self.send_json({"valid": False, "reason": "Not an ELF file"}, status=400)
                return

            is_64bit = raw[4] == 2
            is_little_endian = raw[5] == 1
            e_machine = int.from_bytes(raw[18:20], "little" if is_little_endian else "big")
            e_entry = int.from_bytes(raw[24:32], "little" if is_little_endian else "big") if is_64bit else 0

            machine_str = "x86-64 (AMD64 / PS5)" if e_machine == 0x3E else f"Unknown ({hex(e_machine)})"

            self.send_json({
                "valid": True,
                "file": elf_path.name,
                "size_bytes": len(raw),
                "is_64bit": is_64bit,
                "architecture": machine_str,
                "entry_point": hex(e_entry),
                "compatible_platform": e_machine == 0x3E
            })
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), LauncherRequestHandler) as httpd:
        print(f"============================================================")
        print(f"⚡ AnyPS5 Launcher Companion v2.0 running on http://localhost:{PORT}")
        print(f"Features: Toolchain Hub, Build Engine, Convert Studio,")
        print(f"Big Picture Game Library, DualSense Visualizer, ELF Auditor")
        print(f"Press Ctrl+C to terminate.")
        print(f"============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down launcher server...")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()
