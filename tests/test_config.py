"""
Tests for server/config.py
Validates config loading, default fallbacks, 127.0.0.1 host enforcement, and path validation.
"""

import unittest
import tempfile
import json
from pathlib import Path

from server.config import load_config, save_config, validate_config, DEFAULT_CONFIG

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_config_generated(self):
        cfg = load_config(self.base_dir)
        self.assertEqual(cfg["host"], "127.0.0.1")
        self.assertEqual(cfg["port"], 8085)
        config_file = self.base_dir / "launcher.config.json"
        self.assertTrue(config_file.exists())

    def test_host_always_enforces_localhost(self):
        # Attempt to inject 0.0.0.0
        bad_config = {"host": "0.0.0.0", "port": 9000}
        save_config(self.base_dir, bad_config)
        
        cfg = load_config(self.base_dir)
        self.assertEqual(cfg["host"], "127.0.0.1", "Backend host must strictly be 127.0.0.1")

    def test_path_validation(self):
        cfg = load_config(self.base_dir)
        validated = validate_config(self.base_dir, cfg)
        self.assertIn("status", validated)
        status = validated["status"]
        self.assertIn("library_folder_ready", status)
        self.assertIn("output_folder_ready", status)
        self.assertTrue(status["output_folder_ready"])

if __name__ == "__main__":
    unittest.main()
