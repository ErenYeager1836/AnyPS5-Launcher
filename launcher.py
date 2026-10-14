#!/usr/bin/env python3
"""
AnyPS5 Launcher - Local Native Companion Server
Provides a zero-dependency local HTTP and IPC bridge for process execution,
anyps5-input.ini file management, ELF header inspection, and log streaming.
"""

import http.server
import socketserver
import urllib.parse
import json
import os
import subprocess
import threading
import time
from pathlib import Path

PORT = 8085
BASE_DIR = Path(__file__).resolve().parent

# Global Process State
active_process = None
log_buffer = []
log_lock = threading.Lock()

def append_log(message, tag="anyps5"):
    timestamp = time.strftime("%H:%M:%S")
    with log_lock:
        log_buffer.append({"time": timestamp, "tag": tag, "msg": message})
        if len(log_buffer) > 500:
            log_buffer.pop(0)

def monitor_process(proc):
    append_log(f"Subprocess started with PID: {proc.pid}", "anyps5")
    for line in iter(proc.stdout.readline, ''):
        if not line:
            break
        append_log(line.strip(), "relinker")
    proc.stdout.close()
    return_code = proc.wait()
    append_log(f"Process terminated with exit code: {return_code}", "anyps5")

class LauncherRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/status":
            self.handle_api_status()
        elif parsed.path == "/api/logs":
            self.handle_api_logs()
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
            "backend": "Python Native Bridge v1.0",
            "working_directory": str(BASE_DIR),
            "anyps5_binary": found_binary,
            "connected_gamepad": "DirectInput / SDL2 Emulation Ready"
        })

    def handle_api_logs(self):
        with log_lock:
            logs = list(log_buffer)
        self.send_json({"logs": logs})

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
        global active_process
        title = payload.get("title", "Unknown Title")
        title_id = payload.get("titleId", "PPSA00000")
        
        append_log(f"Initiating launch request for '{title}' [{title_id}]", "anyps5")

        mock_script = BASE_DIR / "mock_relinker.py"
        cmd = ["python", str(mock_script), title, title_id]

        try:
            active_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            thread = threading.Thread(target=monitor_process, args=(active_process,), daemon=True)
            thread.start()
            self.send_json({"success": True, "pid": active_process.pid, "title": title})
        except Exception as e:
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
        print(f"⚡ AnyPS5 Launcher Native Server running on http://localhost:{PORT}")
        print(f"Serving UI & IPC endpoints (Process spawning, INI config, ELF inspection)")
        print(f"Press Ctrl+C to terminate.")
        print(f"============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down launcher server...")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()
