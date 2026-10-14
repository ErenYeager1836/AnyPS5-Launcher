"""
Tests for server/elf_scanner.py
Validates ELF64 parsing, symbol extraction, AnyPS5 symbol database lookup,
and real compatibility scoring.
"""

import unittest
import tempfile
import struct
from pathlib import Path

from server.elf_scanner import Elf64Parser, scan_elf_file, load_anyps5_database

class TestElfScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_invalid_elf_data(self):
        # Empty or random garbage
        parser = Elf64Parser(b"")
        self.assertFalse(parser.is_valid)

        parser = Elf64Parser(b"MZ\x90\x00this is a dos executable not elf")
        self.assertFalse(parser.is_valid)

    def test_database_loads_symbols(self):
        symbol_to_mod, done_syms, todo_syms = load_anyps5_database()
        self.assertGreater(len(done_syms), 3000, "Database should contain >3000 implemented AnyPS5 symbols")
        # Check standard SCE symbols exist in done set
        self.assertIn("sceKernelGetModuleInfo2", done_syms)
        self.assertIn("sceAudioOutOpen", done_syms)
        self.assertIn("scePadReadState", done_syms)
        self.assertIn("sceVideoOutAddFlipEvent", done_syms)

    def test_scan_missing_and_corrupt_file(self):
        missing = self.temp_path / "does_not_exist.elf"
        res = scan_elf_file(missing)
        self.assertFalse(res["valid"])
        self.assertIn("does not exist", res["error"])

        corrupt = self.temp_path / "corrupt.elf"
        corrupt.write_bytes(b"garbage not an elf")
        res = scan_elf_file(corrupt)
        self.assertFalse(res["valid"])
        self.assertIn("Not a valid ELF binary", res["error"])

    def test_scan_synthetic_elf_with_sce_symbols(self):
        # Construct a valid minimal 64-bit little-endian ELF header
        # e_ident: 0x7F, 'E', 'L', 'F', 2 (64-bit), 1 (little-endian), 1 (version), 0...
        e_ident = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8
        e_type = 2 # ET_EXEC
        e_machine = 0x3E # AMD x86-64
        e_version = 1
        e_entry = 0x400000
        e_phoff = 0
        e_shoff = 0
        e_flags = 0
        e_ehsize = 64
        e_phentsize = 56
        e_phnum = 0
        e_shentsize = 64
        e_shnum = 0
        e_shstrndx = 0

        header = e_ident + struct.pack(
            "<HHIQQQIHHHHHH",
            e_type, e_machine, e_version, e_entry,
            e_phoff, e_shoff, e_flags, e_ehsize,
            e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx
        )

        # Inject some real SCE symbols in binary payload
        payload = (
            b"\x00" * 64
            + b"sceKernelUsleep\x00"
            + b"sceKernelGetProcessTime\x00"
            + b"sceVideoOutOpen\x00"
            + b"scePadOpen\x00"
            + b"sceUnknownCustomStubXYZ\x00"
        )
        elf_bytes = header + payload

        test_file = self.temp_path / "test.elf"
        test_file.write_bytes(elf_bytes)

        res = scan_elf_file(test_file)
        self.assertTrue(res["valid"])
        self.assertTrue(res["is_64bit"])
        self.assertEqual(res["architecture"], "x86-64 (AMD64 / PS5)")
        self.assertTrue(res["compatible_platform"])
        self.assertGreater(res["symbols_total"], 0)
        self.assertGreater(res["symbols_resolved"], 0)
        self.assertGreater(res["compat_score"], 0)

if __name__ == "__main__":
    unittest.main()
