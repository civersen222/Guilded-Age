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
    # C9.1: the resolution presets the Settings screen cycles through.
    resolutions: tuple = ((1280, 900), (1024, 768), (800, 600), (1440, 900))
    # C9.4: the frame clock's target.
    target_fps: int = 60


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
        fps = data.get("target_fps")
        if isinstance(fps, int) and not isinstance(fps, bool) and fps > 0:
            s.target_fps = fps
        res = data.get("resolutions")
        if isinstance(res, (list, tuple)) and len(res) >= 2:
            pairs = []
            for r in res:
                if isinstance(r, (list, tuple)) and len(r) == 2:
                    try:
                        pairs.append((int(r[0]), int(r[1])))
                    except (TypeError, ValueError):
                        continue
            if pairs:
                s.resolutions = tuple(pairs)
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
    d["resolutions"] = [list(r) for r in settings.resolutions]
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    return p
