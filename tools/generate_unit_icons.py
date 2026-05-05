#!/usr/bin/env python3
"""Generate unit icon sprites via ComfyUI HTTP API and pack into sprite atlases."""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

import requests
from PIL import Image

# ── Constants ────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_PATH = SCRIPT_DIR / "comfyui_workflows" / "terrain_workflow.json"

ICON_SIZES = [48, 96]
RAW_SIZE = 512
COMFYUI_POLL_INTERVAL = 2
COMFYUI_TIMEOUT = 300

UNIT_PROMPTS = {
    "Warrior": "dark fantasy medieval warrior with sword and shield, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Archer": "dark fantasy medieval archer with bow and arrow, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Cavalry": "dark fantasy medieval cavalry on horseback with lance, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Settler": "dark fantasy medieval settler carrying supplies and tools, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Worker": "dark fantasy medieval worker with pickaxe and hammer, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Catapult": "dark fantasy medieval siege catapult with burning projectile, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Swordsman": "dark fantasy elite swordsman with longsword and plate armor, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Knight": "dark fantasy knight in full plate armor with heraldry, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Galley": "dark fantasy medieval war galley with oars and ram, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Spearman": "dark fantasy medieval spearman with long spear and small shield, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Militia": "dark fantasy medieval militia with crude weapon and leather armor, top-down 3/4 view, game icon, transparent background, painterly, detailed",
    "Scout": "dark fantasy medieval scout with cloak and dagger, top-down 3/4 view, game icon, transparent background, painterly, detailed",
}

NEGATIVE_PROMPT = "blurry, low quality, text, watermark, modern, white background"


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


def resize_variants(img: Image.Image, sizes: list) -> dict:
    """Resize image to multiple sizes. Returns {size: img}."""
    variants = {}
    for size in sizes:
        variants[size] = img.resize((size, size), Image.LANCZOS)
    return variants


def pack_atlas(tiles: dict, zoom: int, unit_names: list) -> tuple:
    """Pack icons into a horizontal strip atlas. Returns (Image, dict)."""
    if not tiles:
        return None, {}
    tile_img = next(iter(tiles.values()))
    tw, th = tile_img.size
    atlas_w = tw * len(unit_names)
    atlas_h = th
    atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))
    coords = {}
    for i, name in enumerate(unit_names):
        x = i * tw
        atlas.paste(tile_img, (x, 0))
        coords[f"{name}_{zoom}"] = {"x": x, "y": 0, "w": tw, "h": th}
    return atlas, coords


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate unit icon sprites via ComfyUI")
    parser.add_argument("--comfyui-url", default="http://127.0.0.1:8188", help="ComfyUI API URL")
    parser.add_argument("--output", default="assets/units", help="Output directory for unit icons")
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
        print("Continuing — icons will be generated if the API becomes available.")

    # Load workflow
    print(f"Loading workflow from {WORKFLOW_PATH}")
    workflow = load_json(WORKFLOW_PATH)

    unit_names = sorted(UNIT_PROMPTS.keys())

    raw_dir = output_dir / "raw"
    icons_dir = output_dir / "icons"
    atlas_dir = output_dir / "atlases"
    raw_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)
    atlas_dir.mkdir(parents=True, exist_ok=True)

    # ── Generate unit icons via ComfyUI ───────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Generating {len(unit_names)} unit icons via ComfyUI...")
    print(f"{'='*60}\n")

    generated = {}
    for i, unit in enumerate(unit_names, 1):
        print(f"[{i}/{len(unit_names)}] Generating {unit}...")
        seed = random.randint(0, 2**32 - 1)

        # Clone workflow and replace prompt + seed + filename
        wf = json.loads(json.dumps(workflow))

        # Node 2 = positive prompt, Node 5 = KSampler, Node 7 = SaveImage
        wf["2"]["inputs"]["text"] = UNIT_PROMPTS[unit]
        wf["3"]["inputs"]["text"] = NEGATIVE_PROMPT
        wf["4"]["inputs"]["width"] = RAW_SIZE
        wf["4"]["inputs"]["height"] = RAW_SIZE
        wf["5"]["inputs"]["seed"] = seed
        wf["7"]["inputs"]["filename_prefix"] = f"output/{unit}"

        try:
            prompt_id = post_prompt(url, wf)
            print(f"  Prompt submitted (id={prompt_id}, seed={seed})")

            history = wait_for_completion(url, prompt_id)
            outputs = history.get("outputs", {})

            # Find the SaveImage node output (node 7)
            if "7" not in outputs:
                print(f"  WARNING: No output from node 7 for {unit}")
                continue

            file_info = outputs["7"]["images"][0]
            filename = file_info["filename"]
            subfolder = file_info.get("subfolder", "")

            img_path = download_image(url, filename, raw_dir, subfolder, file_info.get("type", "output"))
            print(f"  Saved raw icon: {img_path}")

            generated[unit] = img_path

        except Exception as e:
            print(f"  ERROR generating {unit}: {e}")
            generated[unit] = None

    if not generated:
        print("ERROR: No icons were generated. Exiting.")
        sys.exit(1)

    # ── Post-processing: resize to icon sizes ─────────────────────────────
    print(f"\n{'='*60}")
    print(f"Post-processing icons to {len(ICON_SIZES)} sizes...")
    print(f"{'='*60}\n")

    all_variants = {}  # {unit: {size: Image}}
    for unit, img_path in generated.items():
        if img_path is None:
            continue
        print(f"Resizing {unit}...")
        img = Image.open(img_path).convert("RGBA")
        variants = resize_variants(img, ICON_SIZES)
        all_variants[unit] = variants
        for size in ICON_SIZES:
            out_path = icons_dir / f"{unit}_{size}.png"
            variants[size].save(out_path)
        print(f"  Saved {len(ICON_SIZES)} variants to {icons_dir}")

    # ── Pack sprite atlases ───────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Packing sprite atlases...")
    print(f"{'='*60}\n")

    for size in ICON_SIZES:
        tiles_for_size = {u: all_variants[u][size] for u in unit_names if u in all_variants}
        atlas_img, atlas_json = pack_atlas(tiles_for_size, size, unit_names)

        if atlas_img is None:
            print(f"  Skipping atlas_{size}.png (no icons available)")
            continue

        atlas_path = atlas_dir / f"atlas_{size}.png"
        atlas_meta_path = atlas_dir / f"atlas_{size}.json"

        atlas_img.save(atlas_path)
        save_json(atlas_json, atlas_meta_path)
        first = unit_names[0]
        tw = atlas_json.get(first, {}).get("w", 0)
        th = atlas_json.get(first, {}).get("h", 0)
        atlas_w = atlas_img.size[0]
        atlas_h = atlas_img.size[1]
        print(f"  Atlas {size}px: {atlas_path} ({atlas_w}x{atlas_h}, {tw}x{th} per tile)")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Done! Generated {len([u for u in unit_names if u in all_variants])} unit icons at {len(ICON_SIZES)} sizes.")
    print(f"  Raw icons:  {raw_dir}")
    print(f"  Individual: {icons_dir}")
    print(f"  Atlases:    {atlas_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
