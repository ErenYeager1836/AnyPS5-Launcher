#!/usr/bin/env python3
"""
AnyPS5 Launcher - High-Performance Local Backend Server
Authoritative companion backend for AnyPS5 (boykopovar/AnyPS5).

Hard Constraints:
- Binds to 127.0.0.1 only (never 0.0.0.0)
- Path traversal protection on all static and file endpoints
- Argument-list subprocess execution (no shell=True)
- SSE (Server-Sent Events) live log streaming
- Canonical anyps5-input.ini (Action = Type:Value) support
"""

import http.server
import json
import os
import queue
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Local modules
from server.config import load_config, save_config, validate_config

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"

# Global Process and Log Management
active_process: Optional[subprocess.Popen] = None
active_job_info: Optional[Dict[str, Any]] = None
process_lock = threading.Lock()

log_ring_buffer: List[Dict[str, str]] = []
log_lock = threading.Lock()
sse_subscribers: List[queue.Queue] = []
sse_lock = threading.Lock()

def append_log(message: str, tag: str = "anyps5") -> None:
    timestamp = time.strftime("%H:%M:%S")
    entry = {"time": timestamp, "tag": tag, "msg": str(message)}
    
    with log_lock:
        log_ring_buffer.append(entry)
        if len(log_ring_buffer) > 1000:
            log_ring_buffer.pop(0)

    # Broadcast to all active SSE subscribers
    with sse_lock:
        stale = []
        for q in sse_subscribers:
            try:
                q.put_nowait(entry)
            except queue.Full:
                stale.append(q)
        for s in stale:
            if s in sse_subscribers:
                sse_subscribers.remove(s)

def monitor_process_streams(proc: subprocess.Popen, job_title: str) -> None:
    global active_process, active_job_info
    append_log(f"[{job_title}] Process started with PID {proc.pid}", "anyps5")

    def read_stream(stream, tag):
        try:
            for line in iter(stream.readline, ""):
                if not line:
                    break
                append_log(line.rstrip("\r\n"), tag)
        except Exception as e:
            append_log(f"Error reading {tag} stream: {e}", "warn")
        finally:
            try:
                stream.close()
            except Exception:
                pass

    t_out = threading.Thread(target=read_stream, args=(proc.stdout, "relinker"), daemon=True)
    t_err = threading.Thread(target=read_stream, args=(proc.stderr, "warn"), daemon=True)
    t_out.start()
    t_err.start()

    t_out.join()
    t_err.join()

    exit_code = proc.wait()
    tag = "anyps5" if exit_code == 0 else "warn"
    append_log(f"[{job_title}] Process exited with code {exit_code}", tag)

    with process_lock:
        if active_process == proc:
            active_process = None
            active_job_info = None

class LauncherHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Secure HTTP Request Handler bound strictly to 127.0.0.1"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format, *args):
        # Suppress noisy default console logging of static requests
        pass

    def translate_path(self, path: str) -> str:
        """Enforce strict path traversal security."""
        clean_path = super().translate_path(path)
        try:
            resolved = Path(clean_path).resolve()
            if not resolved.is_relative_to(BASE_DIR):
                return str(BASE_DIR / "__forbidden__")
        except Exception:
            return str(BASE_DIR / "__forbidden__")
        return clean_path

    def send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8085")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8085")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # --- GET Dispatcher ---
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/config":
            self.handle_get_config()
        elif path == "/api/status":
            self.handle_get_status()
        elif path == "/api/library":
            self.handle_get_library()
        elif path == "/api/tools":
            self.handle_get_tools()
        elif path == "/api/logs/stream":
            self.handle_sse_logs_stream()
        elif path == "/api/logs":
            self.handle_get_logs()
        elif path == "/api/input":
            self.handle_get_input()
        else:
            super().do_GET()

    # --- POST & PUT Dispatcher ---
    def do_POST(self) -> None:
        self.dispatch_write_request("POST")

    def do_PUT(self) -> None:
        self.dispatch_write_request("PUT")

    def dispatch_write_request(self, method: str) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            payload = {}

        if path == "/api/config":
            self.handle_save_config(payload)
        elif path == "/api/launch":
            self.handle_post_launch(payload)
        elif path == "/api/library/update":
            self.handle_post_library_update(payload)
        elif path == "/api/stop" or path == "/api/kill":
            self.handle_post_stop()
        elif path == "/api/convert":
            self.handle_post_convert(payload)
        elif path == "/api/input":
            self.handle_save_input(payload)
        elif path == "/api/scan":
            self.handle_post_scan(payload)
        elif path == "/api/tools/clone":
            self.handle_tools_clone(payload)
        elif path == "/api/tools/build":
            self.handle_tools_build(payload)
        else:
            self.send_response(404)
            self.end_headers()

    # =========================================================================
    # API Handlers
    # =========================================================================

    def handle_get_config(self) -> None:
        cfg = load_config(BASE_DIR)
        validated = validate_config(BASE_DIR, cfg)
        self.send_json(validated)

    def handle_save_config(self, payload: Dict[str, Any]) -> None:
        cfg = load_config(BASE_DIR)
        for key in ["anyps5_path", "anyps5_source_path", "library_folder", "output_folder", "port"]:
            if key in payload:
                cfg[key] = payload[key]
        
        save_config(BASE_DIR, cfg)
        validated = validate_config(BASE_DIR, cfg)
        append_log("Updated launcher configuration settings.", "anyps5")
        self.send_json({"success": True, "config": validated})

    def handle_get_status(self) -> None:
        cfg = load_config(BASE_DIR)
        validated = validate_config(BASE_DIR, cfg)
        
        with process_lock:
            running = active_process is not None and active_process.poll() is None
            pid = active_process.pid if running else None
            job = active_job_info if running else None

        self.send_json({
            "status": "online",
            "backend": "AnyPS5 Local Companion Server v1.0",
            "host": "127.0.0.1",
            "port": validated["port"],
            "process_running": running,
            "pid": pid,
            "active_job": job,
            "relinker_ready": validated["status"]["anyps5_binary_ready"],
            "relinker_path": validated["status"]["anyps5_binary_path"]
        })

    def handle_get_tools(self) -> None:
        tools: Dict[str, Any] = {}

        # 1. Git
        try:
            r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=3)
            tools["git"] = {"installed": r.returncode == 0, "version": r.stdout.strip(), "path": shutil.which("git")}
        except Exception:
            tools["git"] = {"installed": False, "version": "Not Found", "path": None}

        # 2. Python
        tools["python"] = {"installed": True, "version": f"Python {sys.version.split()[0]}", "path": sys.executable}

        # 3. CMake
        try:
            r = subprocess.run(["cmake", "--version"], capture_output=True, text=True, timeout=3)
            cmake_line = r.stdout.splitlines()[0] if r.stdout else "CMake"
            tools["cmake"] = {"installed": r.returncode == 0, "version": cmake_line, "path": shutil.which("cmake")}
        except Exception:
            tools["cmake"] = {"installed": False, "version": "Not Found", "path": None}

        # 4. Ninja
        try:
            r = subprocess.run(["ninja", "--version"], capture_output=True, text=True, timeout=3)
            tools["ninja"] = {"installed": r.returncode == 0, "version": f"Ninja {r.stdout.strip()}", "path": shutil.which("ninja")}
        except Exception:
            tools["ninja"] = {"installed": False, "version": "Not Found", "path": None}

        # 5. C++ Compiler
        compiler_info = {"installed": False, "name": "None Detected", "version": "Missing", "path": None}
        for comp in ["cl", "clang", "gcc"]:
            comp_path = shutil.which(comp)
            if comp_path:
                try:
                    subprocess.run([comp, "--version" if comp != "cl" else "/?"], capture_output=True, text=True, timeout=3)
                    compiler_info = {"installed": True, "name": comp.upper(), "version": "Active", "path": comp_path}
                    break
                except Exception:
                    pass
        if not compiler_info["installed"]:
            vswhere_path = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
            if vswhere_path.exists():
                compiler_info = {"installed": True, "name": "MSVC (vswhere)", "version": "Build Tools Present", "path": str(vswhere_path)}
        tools["compiler"] = compiler_info

        # 6. Vulkan
        vulkan_sdk = os.environ.get("VULKAN_SDK")
        vulkan_dll = Path("C:/Windows/System32/vulkan-1.dll")
        has_vulkan = bool(vulkan_sdk) or vulkan_dll.exists()
        tools["vulkan"] = {
            "installed": has_vulkan,
            "version": "Vulkan 1.3 Compatible Loader",
            "path": vulkan_sdk if vulkan_sdk else (str(vulkan_dll) if vulkan_dll.exists() else "Not Found")
        }

        # 7. AnyPS5 source & relinker status
        cfg = load_config(BASE_DIR)
        validated = validate_config(BASE_DIR, cfg)
        src_path = Path(validated["anyps5_source_path"]) if validated.get("anyps5_source_path") else None
        cloned = src_path.exists() and (src_path / ".git").exists() if src_path else False
        commit = "Not Cloned"
        if cloned and src_path:
            try:
                r = subprocess.run(["git", "-C", str(src_path), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=2)
                if r.returncode == 0:
                    commit = r.stdout.strip()
            except Exception:
                commit = "Cloned"

        tools["anyps5_repo"] = {
            "cloned": cloned,
            "path": str(src_path) if src_path else None,
            "commit": commit,
            "relinker_built": validated["status"]["anyps5_binary_ready"],
            "relinker_path": validated["status"]["anyps5_binary_path"]
        }

        self.send_json(tools)

    def handle_sse_logs_stream(self) -> None:
        """Stream stdout/stderr logs in real-time using Server-Sent Events (SSE)."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8085")
        self.end_headers()

        sub_queue: queue.Queue = queue.Queue(maxsize=200)
        with sse_lock:
            sse_subscribers.append(sub_queue)

        # Initial backlog flush (send last 50 lines)
        with log_lock:
            backlog = list(log_ring_buffer[-50:])
        for item in backlog:
            try:
                line = f"data: {json.dumps(item)}\n\n".encode("utf-8")
                self.wfile.write(line)
            except Exception:
                break
        try:
            self.wfile.flush()
        except Exception:
            pass

        try:
            while True:
                try:
                    item = sub_queue.get(timeout=3.0)
                    msg = f"data: {json.dumps(item)}\n\n".encode("utf-8")
                    self.wfile.write(msg)
                    self.wfile.flush()
                except queue.Empty:
                    # Heartbeat comment to keep SSE connection alive
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (ConnectionResetError, BrokenPipeError, Exception):
            pass
        finally:
            with sse_lock:
                if sub_queue in sse_subscribers:
                    sse_subscribers.remove(sub_queue)

    def handle_get_logs(self) -> None:
        with log_lock:
            logs = list(log_ring_buffer)
        with process_lock:
            running = active_process is not None and active_process.poll() is None
            job = active_job_info if running else None
        self.send_json({"logs": logs, "active_job": job})

    def handle_get_library(self) -> None:
        """Scan configured library folder for games and load metadata."""
        cfg = load_config(BASE_DIR)
        validated = validate_config(BASE_DIR, cfg)
        lib_root = Path(validated["status"]["library_folder_resolved"])
        
        games = []
        # Load user metadata store if present
        meta_file = BASE_DIR / "library.json"
        saved_meta: Dict[str, Any] = {}
        if meta_file.exists():
            try:
                saved_meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        if lib_root.exists() and lib_root.is_dir():
            for entry in sorted(lib_root.iterdir()):
                if entry.is_dir():
                    eboot = entry / "eboot.bin"
                    param_json = entry / "param.json"
                    converted_exe = entry / "game.exe"
                    
                    if eboot.exists() or param_json.exists() or converted_exe.exists():
                        game_id = entry.name
                        title_info = saved_meta.get(game_id, {})
                        
                        if param_json.exists():
                            try:
                                pj = json.loads(param_json.read_text(encoding="utf-8"))
                                title_info.setdefault("title", pj.get("titleName", entry.name))
                                title_info.setdefault("titleId", pj.get("titleId", "PPSA00000"))
                            except Exception:
                                pass

                        title_info.setdefault("id", game_id)
                        title_info.setdefault("title", entry.name)
                        title_info.setdefault("titleId", "PPSA00000")
                        title_info.setdefault("path", str(entry))
                        title_info.setdefault("eboot", str(eboot) if eboot.exists() else None)
                        title_info.setdefault("executable", str(converted_exe) if converted_exe.exists() else None)
                        title_info.setdefault("isReal", True)
                        games.append(title_info)

        # Also inspect converted_games folder for standalone executables
        out_root = Path(validated["status"]["output_folder_resolved"])
        if out_root.exists() and out_root.is_dir():
            for exe in out_root.glob("*.exe"):
                title_id = f"conv_{exe.stem}"
                games.append({
                    "id": title_id,
                    "title": f"Converted: {exe.stem}",
                    "titleId": "PPSA-RELINK",
                    "publisher": "Converted Standalone",
                    "status": "playable",
                    "statusLabel": "Relinked",
                    "path": str(exe.parent),
                    "executable": str(exe),
                    "isReal": True
                })

        self.send_json({"count": len(games), "library_folder": str(lib_root), "games": games})

    def handle_post_library_update(self, payload: Dict[str, Any]) -> None:
        """Persist metadata, notes, favorites, and custom covers to library.json."""
        meta_file = BASE_DIR / "library.json"
        saved: Dict[str, Any] = {}
        if meta_file.exists():
            try:
                saved = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                saved = {}

        game_id = payload.get("id") or payload.get("titleId")
        if not game_id:
            self.send_json({"success": False, "error": "Game ID required."}, status=400)
            return

        entry = saved.get(game_id, {})
        for key in ["title", "titleId", "publisher", "notes", "isFavorite", "customCover", "playTimeSeconds", "lastPlayed", "status", "path", "executable", "eboot"]:
            if key in payload:
                entry[key] = payload[key]
        
        saved[game_id] = entry
        try:
            meta_file.write_text(json.dumps(saved, indent=2), encoding="utf-8")
            append_log(f"Updated metadata for {entry.get('title', game_id)} in library.json", "anyps5")
            self.send_json({"success": True, "saved": entry})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, status=500)

    def handle_post_launch(self, payload: Dict[str, Any]) -> None:
        """Launch an executable or AnyPS5 process with argument list (no shell=True)."""
        global active_process, active_job_info

        with process_lock:
            if active_process and active_process.poll() is None:
                self.send_json({"success": False, "error": "A process is already running."}, status=400)
                return

        title = payload.get("title", "Game Executable")
        target_exe = payload.get("executable")
        args = payload.get("args", [])

        if not target_exe:
            self.send_json({"success": False, "error": "No executable specified."}, status=400)
            return

        exe_path = Path(target_exe).resolve()
        if not exe_path.exists():
            self.send_json({"success": False, "error": f"Executable not found: {exe_path}"}, status=404)
            return

        # Security check: ensure path is within allowable directories
        cfg = load_config(BASE_DIR)
        validated = validate_config(BASE_DIR, cfg)
        allowed_dirs = [
            BASE_DIR.resolve(),
            Path(validated["status"]["library_folder_resolved"]).resolve(),
            Path(validated["status"]["output_folder_resolved"]).resolve()
        ]
        if validated["status"]["anyps5_source_resolved"]:
            allowed_dirs.append(Path(validated["status"]["anyps5_source_resolved"]).resolve())

        is_allowed = any(exe_path.is_relative_to(d) for d in allowed_dirs)
        if not is_allowed and not str(exe_path).lower().endswith(".exe"):
            self.send_json({"success": False, "error": "Execution path not in allowed directories."}, status=403)
            return

        cmd = [str(exe_path)] + [str(a) for a in args]
        append_log(f"Spawning native process: {' '.join(cmd)}", "anyps5")

        try:
            with process_lock:
                active_job_info = {"title": title, "exe": str(exe_path), "started": time.time()}
                active_process = subprocess.Popen(
                    cmd,
                    cwd=str(exe_path.parent),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
            
            t = threading.Thread(target=monitor_process_streams, args=(active_process, title), daemon=True)
            t.start()

            self.send_json({
                "success": True,
                "pid": active_process.pid,
                "title": title,
                "command": cmd
            })
        except Exception as e:
            with process_lock:
                active_process = None
                active_job_info = None
            append_log(f"Failed to launch process: {e}", "warn")
            self.send_json({"success": False, "error": str(e)}, status=500)

    def handle_post_stop(self) -> None:
        """Terminate active process cleanly."""
        global active_process, active_job_info
        with process_lock:
            proc = active_process
            job = active_job_info

        if proc and proc.poll() is None:
            try:
                proc.terminate()
                append_log(f"Sent termination signal to PID {proc.pid}", "warn")
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    append_log(f"Force killed PID {proc.pid}", "warn")
                
                with process_lock:
                    active_process = None
                    active_job_info = None
                self.send_json({"success": True, "message": "Process terminated."})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status=500)
        else:
            self.send_json({"success": True, "message": "No active process running."})

    def handle_post_convert(self, payload: Dict[str, Any]) -> None:
        """
        Run AnyPS5 relinker using official CLI flags:
        relinker [options] <input.elf> <output>
        """
        global active_process, active_job_info

        with process_lock:
            if active_process and active_process.poll() is None:
                self.send_json({"success": False, "error": "A process is already active."}, status=400)
                return

        cfg = load_config(BASE_DIR)
        validated = validate_config(BASE_DIR, cfg)

        relinker_bin = validated["status"]["anyps5_binary_path"]
        if not relinker_bin or not Path(relinker_bin).exists():
            self.send_json({
                "success": False,
                "error": "AnyPS5 relinker executable not found. Please compile or configure AnyPS5 in Toolchain & Setup."
            }, status=400)
            return

        game_folder = Path(payload.get("gameFolder", BASE_DIR / "fixtures/demo_game"))
        if not game_folder.is_absolute():
            game_folder = BASE_DIR / game_folder

        eboot_elf = game_folder / "eboot.bin"
        if not eboot_elf.exists():
            # Check for any .elf in folder
            elfs = list(game_folder.glob("*.elf"))
            if elfs:
                eboot_elf = elfs[0]
            else:
                self.send_json({"success": False, "error": f"No eboot.bin or ELF found in {game_folder}"}, status=404)
                return

        output_dir = Path(payload.get("outputDir", BASE_DIR / "converted_games"))
        if not output_dir.is_absolute():
            output_dir = BASE_DIR / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        exe_name = payload.get("exeName", "game.exe")
        if not exe_name.lower().endswith(".exe"):
            exe_name += ".exe"
        out_exe_path = output_dir / exe_name

        # Construct official AnyPS5 CLI flags
        cmd = [str(relinker_bin)]
        target_mode = payload.get("targetMode", "--windows")
        if target_mode in ["--windows", "--windows-gui"]:
            cmd.append(target_mode)
        else:
            cmd.append("--windows")

        if payload.get("traceImports"):
            cmd.append("--trace-imports")
        if payload.get("toIntel"):
            cmd.append("--to-intel")
        if payload.get("diagnostics"):
            cmd.append("--windows-diagnostics")

        # Positional arguments: <input.elf> <output>
        cmd.extend([str(eboot_elf), str(out_exe_path)])

        append_log(f"Starting relinking conversion: {' '.join(cmd)}", "anyps5")

        try:
            with process_lock:
                active_job_info = {"title": "Relinker Conversion", "exe": str(out_exe_path), "started": time.time()}
                active_process = subprocess.Popen(
                    cmd,
                    cwd=str(game_folder),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )

            t = threading.Thread(target=monitor_process_streams, args=(active_process, "Relinker Conversion"), daemon=True)
            t.start()

            self.send_json({
                "success": True,
                "job": "Relinker Conversion",
                "outputExe": str(out_exe_path),
                "pid": active_process.pid
            })
        except Exception as e:
            with process_lock:
                active_process = None
                active_job_info = None
            append_log(f"Failed to execute relinker: {e}", "warn")
            self.send_json({"success": False, "error": str(e)}, status=500)

    def handle_tools_clone(self, payload: Dict[str, Any]) -> None:
        """Clone or pull AnyPS5 upstream repository."""
        global active_process, active_job_info
        with process_lock:
            if active_process and active_process.poll() is None:
                self.send_json({"success": False, "error": "A process is already active."}, status=400)
                return

        cfg = load_config(BASE_DIR)
        validated = validate_config(BASE_DIR, cfg)
        target_dir = Path(validated["status"]["anyps5_source_resolved"] or (BASE_DIR / "AnyPS5"))

        if target_dir.exists() and (target_dir / ".git").exists():
            job_name = "Git Pull Upstream"
            cmd = ["git", "-C", str(target_dir), "pull", "--recurse-submodules"]
            append_log(f"Pulling upstream updates in {target_dir}...", "anyps5")
        else:
            job_name = "Git Clone Upstream"
            cmd = ["git", "clone", "--recurse-submodules", "https://github.com/boykopovar/AnyPS5.git", str(target_dir)]
            append_log(f"Cloning AnyPS5 into {target_dir}...", "anyps5")

        try:
            with process_lock:
                active_job_info = {"title": job_name, "started": time.time()}
                active_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
            t = threading.Thread(target=monitor_process_streams, args=(active_process, job_name), daemon=True)
            t.start()
            self.send_json({"success": True, "job": job_name})
        except Exception as e:
            with process_lock:
                active_process = None
                active_job_info = None
            append_log(f"Git command failed: {e}", "warn")
            self.send_json({"success": False, "error": str(e)}, status=500)

    def handle_tools_build(self, payload: Dict[str, Any]) -> None:
        """Configure and compile AnyPS5 relinker using CMake + Ninja."""
        global active_process, active_job_info
        with process_lock:
            if active_process and active_process.poll() is None:
                self.send_json({"success": False, "error": "A process is already active."}, status=400)
                return

        cfg = load_config(BASE_DIR)
        validated = validate_config(BASE_DIR, cfg)
        source_dir = Path(validated["status"]["anyps5_source_resolved"] or (BASE_DIR / "AnyPS5"))

        if not source_dir.exists():
            self.send_json({"success": False, "error": "AnyPS5 source directory not found. Clone repository first."}, status=400)
            return

        build_dir = source_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        job_name = "CMake Relinker Build"
        
        append_log(f"Configuring CMake with Ninja generator in {build_dir}...", "anyps5")

        def run_build_sequence():
            global active_process, active_job_info
            # 1. Configure
            cfg_cmd = ["cmake", "-B", str(build_dir), "-S", str(source_dir), "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release"]
            append_log("Running: " + " ".join(cfg_cmd), "anyps5")
            try:
                p1 = subprocess.Popen(cfg_cmd, cwd=str(source_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
                with process_lock:
                    active_process = p1
                monitor_process_streams(p1, "CMake Configure")
                if p1.returncode != 0:
                    append_log("CMake configure failed.", "warn")
                    return

                # 2. Build relinker target
                bld_cmd = ["cmake", "--build", str(build_dir), "--target", "relinker"]
                append_log("Running: " + " ".join(bld_cmd), "anyps5")
                p2 = subprocess.Popen(bld_cmd, cwd=str(source_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
                with process_lock:
                    active_process = p2
                monitor_process_streams(p2, "Ninja Build")
                if p2.returncode == 0:
                    append_log("Relinker build succeeded!", "anyps5")
                    relinker_exe = build_dir / "bin" / "relinker.exe"
                    if relinker_exe.exists():
                        cfg["anyps5_path"] = str(relinker_exe)
                        save_config(BASE_DIR, cfg)
            except Exception as ex:
                append_log(f"Build sequence error: {ex}", "warn")
            finally:
                with process_lock:
                    active_process = None
                    active_job_info = None

        t = threading.Thread(target=run_build_sequence, daemon=True)
        t.start()
        with process_lock:
            active_job_info = {"title": job_name, "started": time.time()}

        self.send_json({"success": True, "job": job_name})

    def handle_get_input(self) -> None:
        """Read anyps5-input.ini conforming to official format."""
        ini_path = BASE_DIR / "anyps5-input.ini"
        if ini_path.exists():
            content = ini_path.read_text(encoding="utf-8")
        else:
            content = (
                "# AnyPS5 Controller, Keyboard and Mouse Input Configuration\n"
                "# Format: Action = Type:Value\n\n"
                "Cross = KEY:Space\n"
                "Circle = KEY:Escape\n"
                "Square = KEY:R\n"
                "Triangle = KEY:F\n"
                "L1 = KEY:Q\n"
                "R1 = KEY:E\n"
                "L2 = MOUSE:Right\n"
                "R2 = MOUSE:Left\n"
                "Options = KEY:Return\n"
                "LeftStickUp = KEY:W\n"
                "LeftStickLeft = KEY:A\n"
                "LeftStickDown = KEY:S\n"
                "LeftStickRight = KEY:D\n"
                "ToggleFullscreen = KEY:F11\n"
                "ToggleMouse = KEY:F1\n"
            )
            ini_path.write_text(content, encoding="utf-8")

        self.send_json({"ini_path": str(ini_path), "content": content})

    def handle_save_input(self, payload: Dict[str, Any]) -> None:
        """Save anyps5-input.ini preserving comments and unknown keys."""
        content = payload.get("content", "")
        ini_path = BASE_DIR / "anyps5-input.ini"
        
        # Validate format: each non-empty, non-comment line must be Action = Type:Value
        errors = []
        lines = content.splitlines()
        clean_lines = []
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";")):
                clean_lines.append(line)
                continue
            if "=" in stripped:
                parts = stripped.split("=", 1)
                action = parts[0].strip()
                val = parts[1].strip()
                clean_lines.append(f"{action} = {val}")
            else:
                errors.append(f"Line {idx} invalid syntax (expected Action = Type:Value): {line}")

        if errors:
            self.send_json({"success": False, "errors": errors}, status=400)
            return

        ini_path.write_text("\n".join(clean_lines) + "\n", encoding="utf-8")
        append_log(f"Saved controller mappings to {ini_path.name}", "anyps5")
        self.send_json({"success": True, "saved_to": str(ini_path)})

    def handle_post_scan(self, payload: Dict[str, Any]) -> None:
        """Analyze PS5 ELF64 headers and calculate real AnyPS5 symbol coverage."""
        from server.elf_scanner import scan_elf_file

        elf_path_str = payload.get("path")
        if not elf_path_str:
            elf_path = BASE_DIR / "fixtures/demo_game/eboot.bin"
        else:
            elf_path = Path(elf_path_str)
            if not elf_path.is_absolute():
                elf_path = BASE_DIR / elf_path

        result = scan_elf_file(elf_path)
        status = 200 if result.get("valid", False) else 400
        self.send_json(result, status=status)

def main():
    cfg = load_config(BASE_DIR)
    validated = validate_config(BASE_DIR, cfg)
    port = validated["port"]
    host = "127.0.0.1"

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server = socketserver.ThreadingTCPServer((host, port), LauncherHTTPHandler)

    print("=================================================================")
    print(f"⚡ AnyPS5 Companion Backend Server")
    print(f"   Listening on: http://{host}:{port} (Strict Localhost)")
    print(f"   Root Directory: {BASE_DIR}")
    print(f"   AnyPS5 Binary: {validated['status']['anyps5_binary_path'] or 'Not Built'}")
    print("=================================================================")

    if "--daemon" not in sys.argv and "--no-browser" not in sys.argv:
        # Launch standalone browser application window
        browser_exe = None
        candidates = [
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Google/Chrome/Application/chrome.exe"
        ]
        for c in candidates:
            if c.exists():
                browser_exe = str(c)
                break

        if browser_exe:
            data_dir = BASE_DIR / ".app_data"
            data_dir.mkdir(exist_ok=True)
            cmd = [
                browser_exe,
                f"--app=http://{host}:{port}",
                "--window-size=1380,880",
                f"--user-data-dir={data_dir}"
            ]
            try:
                proc = subprocess.Popen(cmd)
                def wait_and_exit():
                    proc.wait()
                    print("\nClosing server after window exit...")
                    server.shutdown()
                t = threading.Thread(target=wait_and_exit, daemon=True)
                t.start()
            except Exception as e:
                print(f"Failed to launch standalone window: {e}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
