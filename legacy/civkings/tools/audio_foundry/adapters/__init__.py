"""Engine adapters. Shared dry-run helper."""
from __future__ import annotations
import wave
import struct
from pathlib import Path


def write_silent_wav(out_path: Path, sample_rate: int, seconds: float = 0.1) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = int(sample_rate * seconds)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack("<" + "h" * n, *([0] * n)))
    return out_path
