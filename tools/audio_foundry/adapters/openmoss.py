"""openmoss TTS adapter (text -> speech, optional cloned voice)."""
from __future__ import annotations
import subprocess
from pathlib import Path
from . import write_silent_wav
from ..config import EngineConfig, SAMPLE_RATE_TTS


def generate(text: str, out_path: Path, *, voice: str | None = None,
             dry_run: bool = False, cfg: EngineConfig | None = None) -> Path:
    if dry_run:
        return write_silent_wav(out_path, SAMPLE_RATE_TTS)
    cfg = cfg or EngineConfig()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    argv = [cfg.openmoss_cli, "--text", text, "--out", str(out_path)]  # VERIFY-AT-BUILD: confirm flags via `moss-tts-cli --help`
    if voice:
        argv += ["--voice", voice]  # VERIFY-AT-BUILD
    subprocess.run(argv, check=True)
    return out_path
