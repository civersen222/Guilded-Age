"""Regenerate tile atlases from individual tile PNGs."""
import os
import json
from PIL import Image

TILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "tiles", "tiles")
ATLASES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "tiles", "atlases")

TERRAINS = sorted(["DESERT", "FOREST", "GRASSLAND", "HILLS", "MOUNTAIN", "OCEAN", "PLAINS", "TUNDRA", "WATER_COAST"])
SIZES = [64, 96, 128, 192, 256]


def rebuild_atlas(size: int) -> None:
    """Build one atlas for the given tile size."""
    tile_surfaces = []
    json_data = {}

    for i, terrain in enumerate(TERRAINS):
        path = os.path.join(TILES_DIR, f"{terrain}_{size}.png")
        if not os.path.exists(path):
            print(f"  WARNING: {path} not found, skipping")
            continue
        img = Image.open(path).convert("RGBA")
        tile_surfaces.append(img)
        json_data[f"{terrain}_{size}"] = {"x": i * size, "y": 0, "w": size, "h": size}

    if not tile_surfaces:
        print(f"  ERROR: No tiles found for size {size}, skipping")
        return

    # Pack horizontally
    total_width = len(tile_surfaces) * size
    height = size
    atlas = Image.new("RGBA", (total_width, height))

    for i, tile in enumerate(tile_surfaces):
        atlas.paste(tile, (i * size, 0))

    # Save PNG
    atlas_path = os.path.join(ATLASES_DIR, f"atlas_z{size:03d}.png")
    atlas.save(atlas_path, "PNG")

    # Save JSON
    json_path = os.path.join(ATLASES_DIR, f"atlas_z{size:03d}.json")
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"  Atlas z{size:03d}: {len(tile_surfaces)} tiles, {total_width}x{height}")


def verify_atlas(size: int) -> None:
    """Verify each terrain slot in the atlas has a different center pixel."""
    atlas_path = os.path.join(ATLASES_DIR, f"atlas_z{size:03d}.png")
    if not os.path.exists(atlas_path):
        print(f"  SKIP: {atlas_path} not found")
        return

    img = Image.open(atlas_path)
    colors = []
    for i, terrain in enumerate(TERRAINS):
        cx = i * size + size // 2
        cy = size // 2
        px = img.getpixel((cx, cy))[:3]
        colors.append((terrain, px))

    unique = len(set(colors))
    print(f"  Verify z{size:03d}: {unique}/{len(colors)} unique center pixels")
    for name, px in colors:
        print(f"    {name}: {px}")


def main():
    os.makedirs(ATLASES_DIR, exist_ok=True)

    for size in SIZES:
        print(f"Building atlas z{size:03d}...")
        rebuild_atlas(size)

    print("\nVerifying atlases...")
    for size in SIZES:
        verify_atlas(size)


if __name__ == "__main__":
    main()
