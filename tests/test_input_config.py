"""
Tests for server/input_config.py
Validates canonical AnyPS5 input mapping (Action = Type:Value), comment preservation,
deadzone handling, unknown keys preservation, and round-trip fidelity.
"""

import unittest
import tempfile
from pathlib import Path

from server.input_config import AnyPS5InputIni, SUPPORTED_ACTIONS, DEFAULT_BINDINGS

class TestInputConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ini_path = Path(self.temp_dir.name) / "anyps5-input.ini"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_default_ini(self):
        """When the file does not exist, a default INI is created with comments and canonical bindings."""
        self.assertFalse(self.ini_path.exists())
        ini = AnyPS5InputIni(self.ini_path)
        self.assertTrue(self.ini_path.exists())
        
        # Verify default bindings exist
        self.assertEqual(ini.bindings.get("cross"), "KEY:Space")
        self.assertEqual(ini.bindings.get("circle"), "KEY:Escape")
        self.assertEqual(ini.deadzone_left, 6)
        self.assertEqual(ini.deadzone_right, 6)

        # File content check
        content = self.ini_path.read_text(encoding="utf-8")
        self.assertIn("Action = Type:Value", content)
        self.assertIn("Cross = KEY:Space", content)

    def test_round_trip_preserves_comments_and_custom_bindings(self):
        """Comments, empty lines, and unknown/custom action lines are strictly preserved."""
        initial_text = (
            "# Top level comment\n"
            "# deadzone_left = 12\n"
            "# deadzone_right = 14\n"
            "\n"
            "; Custom section comment\n"
            "Cross = KEY:Return\n"
            "CustomAction = KEY:Z\n"
            "# Trailing comment\n"
        )
        self.ini_path.write_text(initial_text, encoding="utf-8")

        ini = AnyPS5InputIni(self.ini_path)
        self.assertEqual(ini.deadzone_left, 12)
        self.assertEqual(ini.deadzone_right, 14)
        self.assertEqual(ini.bindings.get("cross"), "KEY:Return")
        self.assertEqual(ini.bindings.get("customaction"), "KEY:Z")

        # Update Cross binding
        ini.update_binding("Cross", "KEY:Space")
        ini.save()

        saved_text = self.ini_path.read_text(encoding="utf-8")
        self.assertIn("# Top level comment", saved_text)
        self.assertIn("; Custom section comment", saved_text)
        self.assertIn("# Trailing comment", saved_text)
        self.assertIn("Cross = KEY:Space", saved_text)
        self.assertIn("CustomAction = KEY:Z", saved_text)

    def test_update_existing_and_add_new_binding(self):
        ini = AnyPS5InputIni(self.ini_path)
        ini.update_binding("Square", "KEY:E")
        ini.update_binding("TouchLeft", "KEY:T")
        ini.save()

        # Re-read
        reloaded = AnyPS5InputIni(self.ini_path)
        self.assertEqual(reloaded.bindings.get("square"), "KEY:E")
        self.assertEqual(reloaded.bindings.get("touchleft"), "KEY:T")

    def test_deadzone_clamping_and_persistence(self):
        ini = AnyPS5InputIni(self.ini_path)
        
        # Test clamping negative and >30
        ini.set_deadzone(-5, 45)
        self.assertEqual(ini.deadzone_left, 0)
        self.assertEqual(ini.deadzone_right, 30)
        ini.save()

        reloaded = AnyPS5InputIni(self.ini_path)
        self.assertEqual(reloaded.deadzone_left, 0)
        self.assertEqual(reloaded.deadzone_right, 30)

        # Test valid range
        ini.set_deadzone(8, 10)
        ini.save()

        reloaded2 = AnyPS5InputIni(self.ini_path)
        self.assertEqual(reloaded2.deadzone_left, 8)
        self.assertEqual(reloaded2.deadzone_right, 10)

if __name__ == "__main__":
    unittest.main()
