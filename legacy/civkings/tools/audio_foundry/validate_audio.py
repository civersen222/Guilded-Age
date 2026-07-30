"""Smoke gate: verify produced audio files exist, are non-empty, and are WAV."""
from __future__ import annotations
import sys
import wave
from pathlib import Path


def validate_file(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"missing: {path}"
    if path.stat().st_size == 0:
        return False, f"empty: {path}"
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as w:
                if w.getnframes() == 0:
                    return False, f"zero frames: {path}"
        except wave.Error as e:
            return False, f"bad wav {path}: {e}"
    return True, f"ok: {path}"


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]]
    if not paths:
        print("usage: validate_audio.py FILE [FILE ...]")
        return 2
    failed = False
    for p in paths:
        ok, msg = validate_file(p)
        print(msg)
        failed = failed or not ok
    print("VALIDATE OK" if not failed else "VALIDATE FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
