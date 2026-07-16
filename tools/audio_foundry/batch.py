"""Batch-generate audio jobs into a staging dir with a manifest. dry_run-safe."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from .adapters import openmoss, thinksound
from .validate_audio import validate_file


@dataclass(frozen=True)
class Job:
    kind: str                 # "tts" or "sfx"
    asset_id: str             # unique output stem, e.g. "rome_intro"
    text: str                 # narration line or sfx caption
    voice: str | None = None  # voice_ref for tts jobs


def _out_path(staging: Path, job: Job) -> Path:
    return staging / job.kind / f"{job.asset_id}.wav"


def run_batch(jobs: list[Job], staging: Path, *, dry_run: bool = False) -> Path:
    """Generate every job under staging/, write manifest.json, return its path."""
    entries: list[dict] = []
    for job in jobs:
        out = _out_path(staging, job)
        if job.kind == "tts":
            openmoss.generate(job.text, out, voice=job.voice, dry_run=dry_run)
        elif job.kind == "sfx":
            thinksound.generate(job.text, out, dry_run=dry_run)
        else:
            raise ValueError(f"unknown job kind: {job.kind}")
        ok, msg = validate_file(out)
        entries.append({
            "asset_id": job.asset_id,
            "kind": job.kind,
            "path": str(out),
            "text": job.text,
            "valid": ok,
            "note": msg,
        })
    staging.mkdir(parents=True, exist_ok=True)
    manifest = staging / "manifest.json"
    manifest.write_text(json.dumps({"entries": entries}, indent=2), encoding="utf-8")
    return manifest