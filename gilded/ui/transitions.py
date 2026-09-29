"""Cross-fade frames between two pages.

frames(src, dst, steps) -> exactly `steps` Surfaces, deterministic (no RNG,
no timing).  frames[0] sits within 5% of src, frames[-1] within 5% of dst,
and the middle frame differs from BOTH ends on >= 5% of pixels.  The app
loop plays one frame per clock tick; headless callers can consume the list
directly.
"""
from typing import List

import numpy as np
import pygame


def _blend(src: pygame.Surface, dst: pygame.Surface, t: float) -> pygame.Surface:
    """Linear cross-fade, frame = src*(1-t) + dst*t, per channel, per pixel."""
    src_a = pygame.surfarray.pixels3d(src)  # (h, w, 3)
    dst_a = pygame.surfarray.pixels3d(dst)
    out = np.clip(src_a.astype(np.float32) * (1.0 - t)
                  + dst_a.astype(np.float32) * t, 0, 255).astype(np.uint8)
    del src_a
    del dst_a
    surf = pygame.Surface(src.get_size())
    pygame.surfarray.blit_array(surf, out)
    return surf


def frames(src: pygame.Surface, dst: pygame.Surface, steps: int) -> List[pygame.Surface]:
    """Deterministic cross-fade: exactly `steps` frames, src -> dst."""
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if pygame.display.get_surface() is not None:
        src = src.convert()
    if dst.get_size() != src.get_size():
        dst = pygame.transform.smoothscale(dst, src.get_size())
    if pygame.display.get_surface() is not None:
        dst = dst.convert()
    out: List[pygame.Surface] = []
    for i in range(steps):
        if steps == 1:
            out.append(dst.copy())
        elif i == 0:
            out.append(src.copy())
        elif i == steps - 1:
            out.append(dst.copy())
        else:
            out.append(_blend(src, dst, i / (steps - 1)))
    return out
