"""Audio foundry configuration: engine paths, output dirs, formats."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = REPO_ROOT / "assets" / "audio"
VOICE_DIR = ASSET_ROOT / "voice"
SFX_DIR = ASSET_ROOT / "sfx"
AMBIENCE_DIR = ASSET_ROOT / "ambience"

SAMPLE_RATE_TTS = 24000
SAMPLE_RATE_SFX = 44100


@dataclass
class EngineConfig:
    openmoss_cli: str = field(
        default_factory=lambda: os.environ.get("OPENMOSS_CLI", "moss-tts-cli")
    )
    thinksound_cli: str = field(
        default_factory=lambda: os.environ.get("THINKSOUND_CLI", "ts-generate")
    )


def ensure_dirs() -> None:
    for d in (VOICE_DIR, SFX_DIR, AMBIENCE_DIR):
        d.mkdir(parents=True, exist_ok=True)
