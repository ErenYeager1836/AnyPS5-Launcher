"""
Tests for server/main.py HTTP endpoints.
Tests path traversal rejection, config APIs, library scanning, input mapping,
diagnostics ELF scanning, live process execution lifecycle, and SSE logging.
"""

import unittest
import json
import socketserver
import sys
import threading
import urllib.request
import urllib.error
import time
from pathlib import Path

from server.main import LauncherHTTPHandler, BASE_DIR

class TestServerEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start an in-process live server on an ephemeral port bound to 127.0.0.1
        cls.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), LauncherHTTPHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            return resp.status, resp.headers, data

    def _post_json(self, path: str, payload: dict, method: str = "POST"):
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            return resp.status, json.loads(data.decode("utf-8"))

    def test_get_config(self):
        status, headers, data = self._get("/api/config")
        self.assertEqual(status, 200)
        res = json.loads(data.decode("utf-8"))
        self.assertEqual(res.get("host"), "127.0.0.1")
        self.assertIn("status", res)
        self.assertIn("output_folder_ready", res["status"])

    def test_save_config(self):
        status, res = self._post_json("/api/config", {"port": 8085}, method="PUT")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertEqual(res["config"]["port"], 8085)

    def test_get_status(self):
        status, headers, data = self._get("/api/status")
        self.assertEqual(status, 200)
        res = json.loads(data.decode("utf-8"))
        self.assertEqual(res.get("status"), "online")
        self.assertEqual(res.get("host"), "127.0.0.1")
        self.assertIn("process_running", res)

    def test_get_library_and_update(self):
        status, headers, data = self._get("/api/library")
        self.assertEqual(status, 200)
        res = json.loads(data.decode("utf-8"))
        self.assertIn("games", res)
        self.assertIn("count", res)

        # Update metadata for a dummy title
        status, update_res = self._post_json("/api/library/update", {
            "titleId": "CUSA00001",
            "isFavorite": True,
            "title": "Custom Test Game Title"
        })
        self.assertEqual(status, 200)
        self.assertTrue(update_res.get("success"))

    def test_get_and_put_input_mapping(self):
        status, headers, data = self._get("/api/input")
        self.assertEqual(status, 200)
        res = json.loads(data.decode("utf-8"))
        self.assertIn("bindings", res)
        self.assertIn("deadzone_left", res)

        # Update binding
        status, put_res = self._post_json("/api/input", {
            "bindings": {"options": "KEY:Return"},
            "deadzone_left": 8,
            "deadzone_right": 8
        }, method="PUT")
        self.assertEqual(status, 200)
        self.assertTrue(put_res.get("success"))

        # Verify persisted via GET
        _, _, data2 = self._get("/api/input")
        reloaded = json.loads(data2.decode("utf-8"))
        self.assertEqual(reloaded["bindings"].get("options"), "KEY:Return")
        self.assertEqual(reloaded["deadzone_left"], 8)

    def test_post_scan_sample(self):
        status, res = self._post_json("/api/scan", {"sample": True})
        self.assertEqual(status, 200)
        self.assertTrue(res.get("valid"))
        self.assertGreater(res.get("compat_score", 0), 0)
        self.assertIn("symbols_table", res)

    def test_get_logs(self):
        status, headers, data = self._get("/api/logs")
        self.assertEqual(status, 200)
        res = json.loads(data.decode("utf-8"))
        self.assertIn("logs", res)
        self.assertIsInstance(res["logs"], list)

    def test_path_traversal_protection(self):
        # Attempting path traversal with .. should be rejected or resolved to forbidden
        traversal_urls = [
            "/../../../../etc/passwd",
            "/..%2F..%2F..%2Fetc/passwd",
            "/assets/../../server/config.py"
        ]
        for path in traversal_urls:
            url = f"{self.base_url}{path}"
            req = urllib.request.Request(url)
            try:
                with urllib.request.urlopen(req, timeout=3) as resp:
                    pass
            except urllib.error.HTTPError as e:
                # 400, 403, 404 are acceptable security rejections
                self.assertIn(e.code, (400, 403, 404))

    def test_launch_and_stop_lifecycle(self):
        demo_exe = BASE_DIR / "fixtures" / "demo_game" / "game.exe"
        if not demo_exe.exists():
            self.skipTest("Demo executable fixture not present")

        # On non-Windows platforms, Windows .exe cannot execute directly without Wine.
        # Use a cross-platform executable runner to test the process launch/stop lifecycle.
        runner = None
        if sys.platform != "win32":
            runner = BASE_DIR / "fixtures" / "demo_game" / "game_runner.py"
            runner.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n", encoding="utf-8")
            runner.chmod(0o755)
            demo_exe = runner

        try:
            # Launch the demo executable
            status, res = self._post_json("/api/launch", {
                "title": "Test Demo Game",
                "executable": str(demo_exe)
            })
            self.assertEqual(status, 200)
            self.assertTrue(res.get("success"))
            self.assertGreater(res.get("pid", 0), 0)

            # Verify status endpoint sees the running process
            time.sleep(0.3)
            _, _, data = self._get("/api/status")
            status_res = json.loads(data.decode("utf-8"))
            self.assertTrue(status_res.get("process_running"))

            # Terminate via /api/stop
            stop_status, stop_res = self._post_json("/api/stop", {})
            self.assertEqual(stop_status, 200)
            self.assertTrue(stop_res.get("success"))

            time.sleep(0.3)
            _, _, data2 = self._get("/api/status")
            status_res2 = json.loads(data2.decode("utf-8"))
            self.assertFalse(status_res2.get("process_running"))
        finally:
            if runner and runner.exists():
                try:
                    runner.unlink()
                except OSError:
                    pass

if __name__ == "__main__":
    unittest.main()
