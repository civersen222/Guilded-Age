"""Generate hex outline/filled masks for ComfyUI ControlNet."""

from PIL import Image, ImageDraw
import math

def hex_vertices(cx, cy, r):
    """Compute flat-topped hex vertices (6 sides, angle=pi/3*i)."""
    verts = []
    for i in range(6):
        angle = math.pi / 3 * i
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        verts.append((x, y))
    return verts

def generate_canny_mask(size=1024, radius_pct=0.45):
    """White hex outline on black background for Canny input."""
    img = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size / 2, size / 2
    r = size * radius_pct
    verts = hex_vertices(cx, cy, r)
    draw.polygon(verts, outline=(255, 255, 255), width=8)
    return img

def generate_clip_mask(size=256, radius_pct=0.45):
    """Filled hex with alpha channel for clipping mask."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size / 2, size / 2
    r = size * radius_pct
    verts = hex_vertices(cx, cy, r)
    draw.polygon(verts, fill=(255, 255, 255, 255))
    return img

if __name__ == "__main__":
    import os
    tools_dir = os.path.dirname(os.path.abspath(__file__))

    canny = generate_canny_mask()
    canny_path = os.path.join(tools_dir, "hex_mask_canny.png")
    canny.save(canny_path)
    print(f"Saved {canny_path} ({canny.size})")

    clip = generate_clip_mask()
    clip_path = os.path.join(tools_dir, "hex_clip_mask.png")
    clip.save(clip_path)
    print(f"Saved {clip_path} ({clip.size})")
