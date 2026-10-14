"""
AnyPS5 ELF64 & PRX Symbol Compatibility Scanner
Zero-dependency binary parser for 64-bit ELF executables and SCE PRX dynamic symbols.
Computes real AnyPS5 symbol coverage and lists missing/unimplemented symbols.
"""

import json
import re
import struct
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

DATA_DIR = Path(__file__).resolve().parent / "data"

class Elf64Parser:
    """Parses standard ELF64 executables and extracts symbol tables."""

    SHT_PROGBITS = 1
    SHT_SYMTAB = 2
    SHT_STRTAB = 3
    SHT_RELA = 4
    SHT_HASH = 5
    SHT_DYNAMIC = 6
    SHT_NOTE = 7
    SHT_NOBITS = 8
    SHT_REL = 9
    SHT_SHLIB = 10
    SHT_DYNSYM = 11

    def __init__(self, data: bytes):
        self.data = data
        self.is_valid = False
        self.is_64bit = False
        self.is_little_endian = True
        self.e_machine = 0
        self.e_entry = 0
        self.sections: List[Dict[str, Any]] = []
        self.symbols: List[str] = []
        self._parse_header()

    def _parse_header(self) -> None:
        if len(self.data) < 64 or self.data[:4] != b"\x7fELF":
            return

        self.is_64bit = self.data[4] == 2
        self.is_little_endian = self.data[5] == 1
        endian_fmt = "<" if self.is_little_endian else ">"

        self.e_machine = struct.unpack_from(endian_fmt + "H", self.data, 18)[0]
        self.e_entry = struct.unpack_from(endian_fmt + "Q", self.data, 24)[0] if self.is_64bit else struct.unpack_from(endian_fmt + "I", self.data, 24)[0]
        
        e_shoff = struct.unpack_from(endian_fmt + "Q", self.data, 40)[0] if self.is_64bit else struct.unpack_from(endian_fmt + "I", self.data, 32)[0]
        e_shentsize = struct.unpack_from(endian_fmt + "H", self.data, 58 if self.is_64bit else 46)[0]
        e_shnum = struct.unpack_from(endian_fmt + "H", self.data, 60 if self.is_64bit else 48)[0]
        e_shstrndx = struct.unpack_from(endian_fmt + "H", self.data, 62 if self.is_64bit else 50)[0]

        self.is_valid = True

        if e_shoff == 0 or e_shnum == 0 or e_shoff >= len(self.data):
            return

        # Parse Section Headers
        raw_sections = []
        for i in range(e_shnum):
            offset = e_shoff + i * e_shentsize
            if offset + e_shentsize > len(self.data):
                break
            
            if self.is_64bit:
                sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = struct.unpack_from(
                    endian_fmt + "IIQQQQIIQQ", self.data, offset
                )
            else:
                sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = struct.unpack_from(
                    endian_fmt + "IIIIIIIIII", self.data, offset
                )

            raw_sections.append({
                "index": i,
                "name_offset": sh_name,
                "type": sh_type,
                "flags": sh_flags,
                "addr": sh_addr,
                "offset": sh_offset,
                "size": sh_size,
                "link": sh_link,
                "entsize": sh_entsize,
                "name": ""
            })

        # Resolve section names via shstrtab
        if e_shstrndx < len(raw_sections):
            strtab_sec = raw_sections[e_shstrndx]
            strtab_data = self.data[strtab_sec["offset"]:strtab_sec["offset"] + strtab_sec["size"]]
            for sec in raw_sections:
                sec["name"] = self._read_string(strtab_data, sec["name_offset"])

        self.sections = raw_sections

        # Extract symbols from DYNSYM and SYMTAB sections
        extracted_syms: Set[str] = set()
        for sec in self.sections:
            if sec["type"] in (self.SHT_DYNSYM, self.SHT_SYMTAB):
                link_idx = sec["link"]
                if link_idx < len(self.sections):
                    sym_strtab = self.sections[link_idx]
                    str_data = self.data[sym_strtab["offset"]:sym_strtab["offset"] + sym_strtab["size"]]
                    entsize = sec["entsize"] if sec["entsize"] > 0 else (24 if self.is_64bit else 16)
                    num_syms = sec["size"] // entsize
                    
                    for s_i in range(num_syms):
                        s_offset = sec["offset"] + s_i * entsize
                        if s_offset + entsize > len(self.data):
                            break
                        st_name = struct.unpack_from(endian_fmt + "I", self.data, s_offset)[0]
                        name = self._read_string(str_data, st_name)
                        if name:
                            extracted_syms.add(name)

        self.symbols = sorted(extracted_syms)

    def _read_string(self, buf: bytes, offset: int) -> str:
        if offset >= len(buf):
            return ""
        end = buf.find(b"\x00", offset)
        if end == -1:
            end = len(buf)
        return buf[offset:end].decode("ascii", errors="ignore")

def load_anyps5_database() -> Tuple[Dict[str, str], Set[str], Set[str]]:
    """Loads AnyPS5 database mapping function names to PRX modules and status."""
    db_file = DATA_DIR / "anyps5_symbols.json"
    symbol_to_module: Dict[str, str] = {}
    done_set: Set[str] = set()
    todo_set: Set[str] = set()

    if db_file.exists():
        try:
            db = json.loads(db_file.read_text(encoding="utf-8"))
            for group in db.get("libraries", {}).get("groups", []):
                mod_name = group.get("name", "Unknown.prx")
                if not mod_name.endswith(".prx"):
                    mod_name += ".prx"
                for d in group.get("done_names", []):
                    done_set.add(d)
                    symbol_to_module[d] = mod_name
                for t in group.get("todo_names", []):
                    todo_set.add(t)
                    symbol_to_module[t] = mod_name
        except Exception:
            pass

    return symbol_to_module, done_set, todo_set

def scan_elf_file(file_path: Path) -> Dict[str, Any]:
    """Inspects an ELF executable and compares symbols against AnyPS5."""
    if not file_path.exists():
        return {"valid": False, "error": f"File does not exist: {file_path}"}

    raw = file_path.read_bytes()
    parser = Elf64Parser(raw)

    if not parser.is_valid:
        return {"valid": False, "error": "Not a valid ELF binary"}

    symbol_to_module, done_symbols, todo_symbols = load_anyps5_database()

    # Collect symbols from parser + regex string scan (covers stripped binaries with symbol strings)
    candidate_symbols: Set[str] = set(parser.symbols)
    
    # Also find any sce* identifiers in the binary
    pattern = re.compile(rb"\b(sce[A-Z0-9][a-zA-Z0-9_]{3,60})\b")
    for m in pattern.finditer(raw):
        candidate_symbols.add(m.group(1).decode("ascii", errors="ignore"))

    resolved_list: List[Dict[str, str]] = []
    unresolved_list: List[Dict[str, str]] = []

    for sym in sorted(candidate_symbols):
        mod = symbol_to_module.get(sym)
        if not mod:
            # Guess module from prefix
            if sym.startswith("sceKernel"): mod = "libkernel.prx"
            elif sym.startswith("sceVideo"): mod = "libSceVideoOut.prx"
            elif sym.startswith("sceAudio"): mod = "libSceAudioOut.prx"
            elif sym.startswith("scePad"): mod = "libScePad.prx"
            elif sym.startswith("sceAgc"): mod = "libSceAgc.prx"
            elif sym.startswith("sceSave"): mod = "libSceSaveData.prx"
            else: mod = "libkernel.prx"

        if sym in done_symbols:
            resolved_list.append({
                "module": mod,
                "symbol": sym,
                "status": "IMPLEMENTED",
                "action": "Direct AnyPS5 Hook"
            })
        elif sym in todo_symbols or sym.startswith("sce"):
            unresolved_list.append({
                "module": mod,
                "symbol": sym,
                "status": "STUBBED",
                "action": "Unresolved SCE Stub"
            })

    total = len(resolved_list) + len(unresolved_list)
    if total > 0:
        compat_score = round((len(resolved_list) / total) * 100, 1)
    else:
        # Fallback for minimal homebrew binary with 0 imports
        compat_score = 100.0 if parser.e_machine == 0x3E else 0.0

    # Combine symbols for table (resolved first, then unresolved)
    table_symbols = resolved_list[:30] + unresolved_list[:20]

    return {
        "valid": True,
        "file": file_path.name,
        "size_bytes": len(raw),
        "is_64bit": parser.is_64bit,
        "architecture": "x86-64 (AMD64 / PS5)" if parser.e_machine == 0x3E else f"Machine {hex(parser.e_machine)}",
        "entry_point": hex(parser.e_entry),
        "compatible_platform": parser.e_machine == 0x3E and parser.is_64bit,
        "symbols_total": total,
        "symbols_resolved": len(resolved_list),
        "symbols_unresolved": len(unresolved_list),
        "compat_score": compat_score,
        "symbols_table": table_symbols,
        "unresolved_names": [s["symbol"] for s in unresolved_list[:20]]
    }
