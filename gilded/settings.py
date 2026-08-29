"""Player settings (mission C6): a JSON file in the working directory that
survives the process. The Settings screen toggles fields and every press
persists, so a fresh launch reads the same values back.

The file is ``gilded_settings.json`` in the current working directory, so a
sandboxed run keeps its settings in the sandbox.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

SETTINGS_NAME = "gilded_settings.json"


@dataclass
class Settings:
    window_size: tuple = (1280, 900)
    narrate: bool = True
    volume: float = 0.7
    mute: bool = False


def settings_path(path=None) -> str:
    if path is None:
        path = os.path.join(os.getcwd(), SETTINGS_NAME)
    return str(path)


def load_settings(path=None) -> Settings:
    """Read the settings file; a missing or broken file yields the defaults."""
    s = Settings()
    p = settings_path(path)
    if not os.path.isfile(p):
        return s
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return s
    if isinstance(data, dict):
        ws = data.get("window_size")
        if isinstance(ws, (list, tuple)) and len(ws) == 2:
            try:
                s.window_size = (int(ws[0]), int(ws[1]))
            except (TypeError, ValueError):
                pass
        if isinstance(data.get("narrate"), bool):
            s.narrate = data["narrate"]
        if isinstance(data.get("volume"), (int, float)):
            s.volume = float(data["volume"])
        if isinstance(data.get("mute"), bool):
            s.mute = data["mute"]
    return s


def save_settings(settings: Settings, path=None) -> str:
    """Write the settings file and return its path."""
    p = settings_path(path)
    d = asdict(settings)
    d["window_size"] = list(settings.window_size)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    return p
