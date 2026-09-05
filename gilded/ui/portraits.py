"""C8.2 - engraved portraits, deterministically assigned per character.

``portrait_for(character)`` returns the absolute path of the engraving for
the character, chosen from the man_*/woman_* pools by the character's
gender (when the model has one) and the stable character id - never
game.rng.  Loaded Surfaces are cached so redraws blit the exact same
pixels.
"""

from __future__ import annotations

import os
import zlib
from typing import Any, Dict, Optional

import pygame

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "assets", "portraits")

_MEN = [f"man_{i:02d}.jpg" for i in range(1, 25)]
_WOMEN = [f"woman_{i:02d}.jpg" for i in range(1, 13)]

_cache: Dict[str, pygame.Surface] = {}


def _pool_for(character) -> list:
    gender = getattr(character, "gender", None)
    if gender is None:
        inner = getattr(character, "character", None)
        gender = getattr(inner, "gender", None)
    if gender is not None and str(gender).lower().startswith("f"):
        return _WOMEN
    return _MEN


def _char_key(character) -> str:
    return str(getattr(character, "id", None) or getattr(character, "name", ""))


def portrait_for(character) -> str:
    """The absolute path of the character's engraving (stable per id)."""
    key = _char_key(character)
    pool = _pool_for(character)
    idx = zlib.crc32(key.encode("utf-8")) % len(pool)
    return os.path.join(_DIR, pool[idx])


def load(character) -> pygame.Surface:
    """The cached loaded Surface for the character's engraving."""
    path = portrait_for(character)
    if path not in _cache:
        img = pygame.image.load(path)
        try:
            img = img.convert_alpha()
        except pygame.error:
            pass  # headless: blit the raw surface; pixels are identical
        _cache[path] = img
    return _cache[path]


def blit_fitted(surface: pygame.Surface, character,
                dest: pygame.Rect) -> Optional[pygame.Rect]:
    """Scale the engraving to fit *dest*, blit it centred, and return the
    blitted rect (None when the character has no usable identity)."""
    if not _char_key(character):
        return None
    img = load(character)
    scale = min(dest.width / img.get_width(),
                dest.height / img.get_height())
    w, h = max(1, int(img.get_width() * scale)), max(1, int(img.get_height() * scale))
    if w < img.get_width() or h < img.get_height():
        img = pygame.transform.smoothscale(img, (w, h))
    rect = img.get_rect(center=(dest.centerx, dest.centery))
    surface.blit(img, rect)
    return rect
