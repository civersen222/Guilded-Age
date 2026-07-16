"""Editorial gate: promote approved, valid staged assets into the final tree."""
from __future__ import annotations
import json
import shutil
from pathlib import Path


def load_manifest(manifest: Path) -> list[dict]:
    return json.loads(manifest.read_text(encoding="utf-8"))["entries"]


def promote(manifest: Path, final_root: Path, *,
            approved: set[str] | None = None) -> list[str]:
    """Copy staged assets into final_root/<kind>/.

    Only entries that validated are eligible. If `approved` is given, only those
    asset_ids are promoted; if None, every valid entry is promoted. Returns the
    list of promoted asset_ids.
    """
    promoted: list[str] = []
    for e in load_manifest(manifest):
        if not e.get("valid"):
            continue
        if approved is not None and e["asset_id"] not in approved:
            continue
        src = Path(e["path"])
        dest = final_root / e["kind"] / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        promoted.append(e["asset_id"])
    return promoted