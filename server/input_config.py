"""
AnyPS5 anyps5-input.ini Parser and Serializer
Conforms to AnyPS5 official input specification (Action = Type:Value).
Preserves existing comments, blank lines, and unknown action entries during round-trips.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

SUPPORTED_ACTIONS = {
    "cross", "circle", "triangle", "square",
    "l1", "r1", "l2", "r2", "l3", "r3",
    "options", "up", "right", "down", "left",
    "leftstickleft", "leftstickright", "leftstickup", "leftstickdown",
    "rightstickleft", "rightstickright", "rightstickup", "rightstickdown",
    "touchleft", "touchright", "togglemouse", "togglefullscreen"
}

DEFAULT_BINDINGS = [
    ("Cross", "KEY:Space"),
    ("Circle", "KEY:Escape"),
    ("Square", "KEY:R"),
    ("Triangle", "KEY:F"),
    ("L1", "KEY:Q"),
    ("R1", "KEY:E"),
    ("L2", "MOUSE:Right"),
    ("R2", "MOUSE:Left"),
    ("Options", "KEY:Return"),
    ("LeftStickUp", "KEY:W"),
    ("LeftStickLeft", "KEY:A"),
    ("LeftStickDown", "KEY:S"),
    ("LeftStickRight", "KEY:D"),
    ("ToggleFullscreen", "KEY:F11"),
    ("ToggleMouse", "KEY:F1")
]

class IniLine:
    def __init__(self, raw: str, is_entry: bool = False, action: str = "", val: str = ""):
        self.raw = raw
        self.is_entry = is_entry
        self.action = action
        self.val = val

class AnyPS5InputIni:
    def __init__(self, path: Path):
        self.path = path
        self.lines: List[IniLine] = []
        self.bindings: Dict[str, str] = {}
        self.deadzone_left: int = 6
        self.deadzone_right: int = 6
        self.load()

    def load(self) -> None:
        self.lines = []
        self.bindings = {}
        if not self.path.exists():
            self._create_default()
            return

        text = self.path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";")):
                # Check for deadzone comment metadata
                if "deadzone_left" in stripped.lower() and "=" in stripped:
                    try:
                        self.deadzone_left = int(stripped.split("=")[1].strip())
                    except Exception:
                        pass
                if "deadzone_right" in stripped.lower() and "=" in stripped:
                    try:
                        self.deadzone_right = int(stripped.split("=")[1].strip())
                    except Exception:
                        pass
                self.lines.append(IniLine(line, is_entry=False))
                continue

            if "=" in stripped:
                parts = stripped.split("=", 1)
                act = parts[0].strip()
                val = parts[1].strip()
                self.bindings[act.lower()] = val
                self.lines.append(IniLine(line, is_entry=True, action=act, val=val))
            else:
                self.lines.append(IniLine(line, is_entry=False))

    def _create_default(self) -> None:
        self.lines = [
            IniLine("# AnyPS5 Controller, Keyboard and Mouse Input Configuration"),
            IniLine("# Format: Action = Type:Value"),
            IniLine(f"# deadzone_left = {self.deadzone_left}"),
            IniLine(f"# deadzone_right = {self.deadzone_right}"),
            IniLine("")
        ]
        for act, val in DEFAULT_BINDINGS:
            self.lines.append(IniLine(f"{act} = {val}", is_entry=True, action=act, val=val))
            self.bindings[act.lower()] = val
        self.save()

    def update_binding(self, action: str, type_val: str) -> None:
        act_lower = action.lower()
        self.bindings[act_lower] = type_val

        # Update existing line or append
        found = False
        for line in self.lines:
            if line.is_entry and line.action.lower() == act_lower:
                line.val = type_val
                line.raw = f"{line.action} = {type_val}"
                found = True
                break

        if not found:
            self.lines.append(IniLine(f"{action} = {type_val}", is_entry=True, action=action, val=type_val))

    def set_deadzone(self, left: int, right: int) -> None:
        self.deadzone_left = max(0, min(30, left))
        self.deadzone_right = max(0, min(30, right))
        # Update or add metadata comment in header
        updated_left = False
        updated_right = False
        for line in self.lines:
            if not line.is_entry:
                if "deadzone_left" in line.raw.lower() and "=" in line.raw:
                    line.raw = f"# deadzone_left = {self.deadzone_left}"
                    updated_left = True
                elif "deadzone_right" in line.raw.lower() and "=" in line.raw:
                    line.raw = f"# deadzone_right = {self.deadzone_right}"
                    updated_right = True

        if not updated_left:
            self.lines.insert(2, IniLine(f"# deadzone_left = {self.deadzone_left}"))
        if not updated_right:
            self.lines.insert(3, IniLine(f"# deadzone_right = {self.deadzone_right}"))

    def to_string(self) -> str:
        return "\n".join(line.raw for line in self.lines) + "\n"

    def save(self) -> None:
        self.path.write_text(self.to_string(), encoding="utf-8")
