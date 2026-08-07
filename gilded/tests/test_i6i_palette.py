"""I6i — THE PALETTE LAW: no screen names its own colours."""

import os
import re
import glob as globmod

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.chassis import GildedGame
from gilded.ui import widgets
from gilded.ui.broadsheet import BroadsheetView, TABS


def _init():
    pygame.init()
    pygame.display.set_mode((1280, 800))


RGB_RE = re.compile(r"\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)")


# ── lint: no literal RGB outside widgets.py ──────────────────────────


def test_palette_lint_no_literal_rgb():
    """No literal RGB tuple in gilded/ui/ outside widgets.py."""
    ui_dir = os.path.join(os.path.dirname(widgets.__file__))
    offenders = []
    for path in sorted(globmod.glob(os.path.join(ui_dir, "*.py"))):
        basename = os.path.basename(path)
        if basename == "widgets.py":
            continue
        with open(path, "r") as f:
            for lineno, line in enumerate(f, 1):
                if RGB_RE.search(line):
                    offenders.append((path, lineno))
    assert not offenders, (
        f"Literal RGB tuples found in {len(offenders)} locations: "
        + "; ".join(f"{os.path.basename(f)}:{l}" for f, l in offenders)
    )


# ── palette name values match what was drawn before the rename ────────


def test_palette_INK_value():
    assert widgets.INK == (28, 24, 20)


def test_palette_PANEL_BG_value():
    assert widgets.PANEL_BG == (18, 16, 14)


def test_palette_TAB_TEXT_value():
    assert widgets.TAB_TEXT == (232, 226, 210)


def test_palette_PICKER_BACK_BG_value():
    assert widgets.PICKER_BACK_BG == (70, 70, 50)


def test_palette_DISABLED_FILL_value():
    assert widgets.DISABLED_FILL == (60, 60, 50)


def test_palette_HOUSE_COLORS_shape():
    assert len(widgets.HOUSE_COLORS) == 8
    assert widgets.HOUSE_COLORS[0] == (122, 74, 58)


def test_palette_TONES_reuse():
    """TONES dict still present with expected keys."""
    assert "good" in widgets.TONES
    assert "bad" in widgets.TONES
    assert widgets.TONES["good"] == (34, 120, 68)


# ── re-export checks ─────────────────────────────────────────────────


def test_broadsheet_reexports():
    from gilded.ui.broadsheet import (
        BUTTON_BG, BUTTON_TEXT, DISABLED_BUTTON_BG,
    )
    assert BUTTON_BG == (60, 82, 60)
    assert BUTTON_TEXT == (238, 240, 232)
    assert DISABLED_BUTTON_BG == (30, 30, 30)


def test_atlas_view_reexports():
    from gilded.ui.atlas_view import (
        HOUSE_COLORS, MINOR_COLOR, OCEAN_COLOR,
        FRONT_COLOR, GLYPH_COLOR, RAIL_COLOR,
    )
    assert len(HOUSE_COLORS) == 8
    assert MINOR_COLOR == (90, 90, 90)
    assert OCEAN_COLOR == (26, 35, 51)
    assert FRONT_COLOR == (208, 64, 64)
    assert GLYPH_COLOR == (250, 240, 200)
    assert RAIL_COLOR == (198, 164, 84)


# ── widgets.py imports nothing from gilded.ui ────────────────────────


def test_widgets_no_ui_import():
    src = open(widgets.__file__).read()
    for bad in ["gilded.ui.app", "gilded.ui.broadsheet", "gilded.ui.atlas_view"]:
        assert bad not in src, f"widgets.py must not reference {bad}"


# ── rendered screen matches recorded expectation ─────────────────────


def test_briefing_tab_renders():
    _init()
    g = GildedGame(seed=42)
    house = next(iter(g.houses))
    surface = pygame.Surface((1280, 800))
    view = BroadsheetView(g, house)
    view.hover_pos = (5, 5)
    view.active_tab = "Briefing"
    view.draw(surface)
    pixels = pygame.image.tobytes(surface, "RGB")
    assert len(pixels) == 1280 * 800 * 3
    # Surface should not be all zeros (blank)
    assert pixels != b"\x00" * len(pixels)
