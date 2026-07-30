#!/usr/bin/env python3
"""Batch-generate terrain tiles via ComfyUI HTTP API and pack into sprite atlases."""

import argparse
import json
import math
import os
import random
import shutil
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw

# ── Constants ────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_PATH = SCRIPT_DIR / "comfyui_workflows" / "terrain_workflow.json"
PROMPTS_PATH = SCRIPT_DIR / "terrain_prompts.json"
HEX_MASK_PATH = SCRIPT_DIR / "hex_clip_mask.png"

ZOOM_LEVELS = [64, 96, 128, 192, 256]
COMFYUI_POLL_INTERVAL = 2  # seconds
COMFYUI_TIMEOUT = 300  # max seconds to wait for a single tile


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def post_prompt(url: str, prompt: dict) -> str:
    """Submit a workflow prompt to ComfyUI. Returns prompt_id."""
    resp = requests.post(f"{url}/prompt", json={"prompt": prompt}, timeout=10)
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def wait_for_completion(url: str, prompt_id: str, timeout: int = COMFYUI_TIMEOUT) -> dict:
    """Poll /history until the prompt finishes or times out."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{url}/history/{prompt_id}", timeout=10)
        resp.raise_for_status()
        history = resp.json()
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(COMFYUI_POLL_INTERVAL)
    raise TimeoutError(f"ComfyUI did not complete prompt {prompt_id} within {timeout}s")


def download_image(url: str, output_name: str, dest: Path, subfolder: str = "", img_type: str = "output") -> Path:
    """Download a generated image from ComfyUI's /view endpoint."""
    params = {"filename": output_name, "type": img_type}
    if subfolder:
        params["subfolder"] = subfolder
    resp = requests.get(f"{url}/view", params=params, timeout=30)
    resp.raise_for_status()
    dest.mkdir(parents=True, exist_ok=True)
    out_path = dest / output_name
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


def apply_hex_mask(img: Image.Image, mask: Image.Image) -> Image.Image:
    """Apply hex clipping mask to tile image."""
    mask = mask.resize(img.size, Image.LANCZOS)
    result = img.copy()
    result.putalpha(mask.split()[3])  # Use alpha channel from mask
    return result


def resize_variants(img: Image.Image, sizes: list) -> dict:
    """Resize image to multiple zoom levels. Returns {size: img}."""
    variants = {}
    for size in sizes:
        variants[size] = img.resize((size, size), Image.LANCZOS)
    return variants


def pack_atlas(tiles: dict, zoom: int, terrain_names: list) -> tuple:
    """Pack tiles into a horizontal strip atlas. Returns (Image, dict)."""
    tile_img = next(iter(tiles.values()))
    tw, th = tile_img.size
    atlas_w = tw * len(terrain_names)
    atlas_h = th
    atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))
    coords = {}
    for i, name in enumerate(terrain_names):
        x = i * tw
        atlas.paste(tile_img, (x, 0))
        coords[f"{name}_{zoom}"] = {"x": x, "y": 0, "w": tw, "h": th}
    return atlas, coords


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch-generate terrain tiles via ComfyUI")
    parser.add_argument("--comfyui-url", default="http://127.0.0.1:8188", help="ComfyUI API URL")
    parser.add_argument("--output", default="assets/tiles", help="Output directory for tiles")
    args = parser.parse_args()

    url = args.comfyui_url.rstrip("/")
    output_dir = Path(args.output)

    # Check ComfyUI connectivity
    try:
        resp = requests.get(f"{url}/system_stats", timeout=5)
        resp.raise_for_status()
    except requests.ConnectionError:
        print(f"ERROR: Cannot connect to ComfyUI at {url}")
        print("Please start ComfyUI first (python main.py or similar).")
        sys.exit(1)
    except Exception as e:
        print(f"WARNING: Could not reach ComfyUI ({e})")
        print("Continuing — tiles will be generated if the API becomes available.")

    # Load workflow and prompts
    print(f"Loading workflow from {WORKFLOW_PATH}")
    workflow = load_json(WORKFLOW_PATH)
    print(f"Loading terrain prompts from {PROMPTS_PATH}")
    prompts = load_json(PROMPTS_PATH)
    terrain_names = sorted(prompts.keys())

    # Load hex mask
    if not HEX_MASK_PATH.exists():
        print(f"WARNING: Hex mask not found at {HEX_MASK_PATH}, skipping hex masking")
        hex_mask = None
    else:
        hex_mask = Image.open(HEX_MASK_PATH).convert("RGBA")

    raw_dir = output_dir / "raw"
    tiles_dir = output_dir / "tiles"
    atlas_dir = output_dir / "atlases"
    raw_dir.mkdir(parents=True, exist_ok=True)
    tiles_dir.mkdir(parents=True, exist_ok=True)
    atlas_dir.mkdir(parents=True, exist_ok=True)

    # ── Generate tiles via ComfyUI ────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Generating {len(terrain_names)} terrain tiles via ComfyUI...")
    print(f"{'='*60}\n")

    generated = {}
    for i, terrain in enumerate(terrain_names, 1):
        print(f"[{i}/{len(terrain_names)}] Generating {terrain}...")
        seed = random.randint(0, 2**32 - 1)

        # Clone workflow and replace prompt + seed
        wf = json.loads(json.dumps(workflow))  # deep clone

        # Node 2 = positive prompt, Node 5 = KSampler, Node 7 = SaveImage
        wf["2"]["inputs"]["text"] = prompts[terrain]
        wf["5"]["inputs"]["seed"] = seed
        wf["7"]["inputs"]["filename_prefix"] = f"output/{terrain}"

        try:
            prompt_id = post_prompt(url, wf)
            print(f"  Prompt submitted (id={prompt_id}, seed={seed})")

            history = wait_for_completion(url, prompt_id)
            outputs = history.get("outputs", {})

            # Find the SaveImage node output (node 7)
            if "7" not in outputs:
                print(f"  WARNING: No output from node 7 for {terrain}")
                continue

            file_info = outputs["7"]["images"][0]
            filename = file_info["filename"]
            subfolder = file_info.get("subfolder", "")

            img_path = download_image(url, filename, raw_dir, subfolder, file_info.get("type", "output"))
            print(f"  Saved raw tile: {img_path}")

            # Apply hex mask if available
            if hex_mask:
                raw_img = Image.open(img_path).convert("RGBA")
                masked = apply_hex_mask(raw_img, hex_mask)
                masked_path = raw_dir / f"{terrain}_masked.png"
                masked.save(masked_path)
                print(f"  Applied hex mask: {masked_path}")
                img_path = masked_path

            generated[terrain] = img_path

        except Exception as e:
            print(f"  ERROR generating {terrain}: {e}")
            generated[terrain] = None

    if not generated:
        print("ERROR: No tiles were generated. Exiting.")
        sys.exit(1)

    # ── Post-processing: resize to zoom levels ────────────────────────────
    print(f"\n{'='*60}")
    print(f"Post-processing tiles to {len(ZOOM_LEVELS)} zoom levels...")
    print(f"{'='*60}\n")

    all_variants = {}  # {terrain: {zoom: Image}}
    for terrain, img_path in generated.items():
        if img_path is None:
            continue
        print(f"Resizing {terrain}...")
        img = Image.open(img_path).convert("RGBA")
        variants = resize_variants(img, ZOOM_LEVELS)
        all_variants[terrain] = variants
        for zoom in ZOOM_LEVELS:
            out_path = tiles_dir / f"{terrain}_{zoom}.png"
            variants[zoom].save(out_path)
        print(f"  Saved {len(ZOOM_LEVELS)} variants to {tiles_dir}")

    # ── Pack sprite atlases ───────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Packing sprite atlases...")
    print(f"{'='*60}\n")

    valid_terrains = [t for t in terrain_names if t in all_variants]

    for zoom in ZOOM_LEVELS:
        tiles_for_zoom = {t: all_variants[t][zoom] for t in valid_terrains}
        atlas_img, atlas_json = pack_atlas(tiles_for_zoom, zoom, valid_terrains)

        atlas_tag = str(zoom).zfill(3)
        atlas_path = atlas_dir / f"atlas_z{atlas_tag}.png"
        atlas_meta_path = atlas_dir / f"atlas_z{atlas_tag}.json"

        atlas_img.save(atlas_path)
        save_json(atlas_json, atlas_meta_path)
        print(f"  Atlas z{atlas_tag}: {atlas_path} ({atlas_json.get(list(atlas_json.keys())[0], {}).get('w', 0)}x{atlas_json.get(list(atlas_json.keys())[0], {}).get('h', 0)} per tile)")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Done! Generated {len(valid_terrains)} terrain tiles at {len(ZOOM_LEVELS)} zoom levels.")
    print(f"  Raw tiles:  {raw_dir}")
    print(f"  Individual: {tiles_dir}")
    print(f"  Atlases:    {atlas_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
