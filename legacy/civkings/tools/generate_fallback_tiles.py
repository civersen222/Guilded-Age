"""Generate colored hex tile PNGs as fallback when ComfyUI assets don't exist."""
import os
import sys
import math
import json
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game_data import TerrainType

# Same palette as constants.py but as RGB tuples
TERRAIN_COLORS = {
    'PLAINS':      (61, 77, 61),
    'GRASSLAND':   (74, 93, 74),
    'FOREST':      (45, 74, 45),
    'HILLS':       (90, 90, 61),
    'MOUNTAIN':    (74, 74, 74),
    'DESERT':      (106, 90, 58),
    'TUNDRA':      (180, 190, 200),
    'WATER_COAST': (40, 80, 120),
    'OCEAN':       (26, 58, 90),
}

ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.5, 2.0]
BASE_SIZE = 128  # pixels at zoom 1.0


def hex_points(cx, cy, radius):
    """Generate flat-top hex vertices."""
    points = []
    for i in range(6):
        angle = math.pi / 3 * i
        px = cx + radius * math.cos(angle)
        py = cy + radius * math.sin(angle)
        points.append((px, py))
    return points


def generate_tile(color, size):
    """Create a single hex tile PNG with transparency."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = size * 0.48  # slightly smaller than half to leave border
    pts = hex_points(size / 2, size / 2, r)
    draw.polygon(pts, fill=color + (255,), outline=(18, 18, 18, 255))
    return img


def generate_all(output_dir):
    """Generate all terrain tiles at all zoom levels and pack into atlases."""
    os.makedirs(output_dir, exist_ok=True)

    for zoom in ZOOM_LEVELS:
        size = int(BASE_SIZE * zoom)
        atlas_tiles = {}
        images = []

        for terrain_name, color in TERRAIN_COLORS.items():
            tile_img = generate_tile(color, size)
            images.append((terrain_name, tile_img))

        # Pack into atlas (simple horizontal strip)
        cols = len(images)
        atlas_w = cols * size
        atlas_h = size
        atlas = Image.new('RGBA', (atlas_w, atlas_h), (0, 0, 0, 0))

        for i, (name, img) in enumerate(images):
            x = i * size
            atlas.paste(img, (x, 0))
            atlas_tiles[f"{name}_0"] = {"x": x, "y": 0, "w": size, "h": size}

        zoom_tag = f"z{zoom:.1f}".replace('.', '_')
        atlas_path = os.path.join(output_dir, f"atlas_{zoom_tag}.png")
        json_path = os.path.join(output_dir, f"atlas_{zoom_tag}.json")

        atlas.save(atlas_path)
        with open(json_path, 'w') as f:
            json.dump(atlas_tiles, f, indent=2)

        print(f"Generated {atlas_path} ({atlas_w}x{atlas_h}, {len(images)} tiles)")

    print("Done. Fallback tiles generated.")


if __name__ == '__main__':
    output = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'tiles')
    generate_all(output)
