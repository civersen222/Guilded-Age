"""Mission C4 — the Banknote ink system.

Every UI draw routes through these pinned inks. Lowercase hex, exactly
as the spec pins them. RIVER is reserved: no other constant here (and no
province fill elsewhere) may share its hex.

Accent law: VERMILLION marks consequence only (no more than ~5 marks per
screen); GOLD marks the player only.
"""

from __future__ import annotations

PAPER = "#f5f0e1"
FIELD = "#ece5d0"
CARD = "#fbf8ec"
INK = "#1f2d26"
INK2 = "#44513f"
DIM = "#84876f"
VERMILLION = "#c23a22"
VERMILLION_DARK = "#8e2917"
GOLD = "#a8842c"
SAGE = "#ccd6bd"
WHEAT = "#e3d7ae"
SLATE = "#bccad2"
RIVER = "#6f93ad"


def rgb(hexstr: str) -> tuple[int, int, int]:
    """Convert a pinned hex ink to an RGB tuple for pygame drawing."""
    h = hexstr.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
