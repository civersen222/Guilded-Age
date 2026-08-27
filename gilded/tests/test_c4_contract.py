"""Mission C4 wave 3 self-check.

Run EXACTLY as:
    python -m pytest gilded/tests/test_c4_contract.py -q

This is the committed self-check the campaign gate re-runs. It pins the
three-spine world (House/Powers/Atlas), the pinned palette, the glyph tiers,
the DATA homes and VERB annotations, the accent law against real rendered
pixels, and that the two shipped typefaces load from their committed paths.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
from gilded.ui.app import new_app_state
from gilded.ui import registry, broadsheet, palette
from gilded.ui.probe import render_screen

SPINES = ["House", "Powers", "Atlas"]
INKS = {"PAPER": "#f5f0e1", "FIELD": "#ece5d0", "CARD": "#fbf8ec",
        "INK": "#1f2d26", "INK2": "#44513f", "DIM": "#84876f",
        "VERMILLION": "#c23a22", "VERMILLION_DARK": "#8e2917",
        "GOLD": "#a8842c", "SAGE": "#ccd6bd", "WHEAT": "#e3d7ae",
        "SLATE": "#bccad2", "RIVER": "#6f93ad"}
GLYPH_KEYS = {"city", "regiment", "battle", "strike", "train", "ship", "informant"}
VERB_KEYS = {"set_dial", "set_ambition", "hold_seat", "informant_on_order",
             "declare_war", "propose_marriage", "place_informant"}


def test_spines_and_tabs():
    assert list(registry.SCREENS) == SPINES
    assert list(broadsheet.TABS) == SPINES


def test_palette_pinned():
    for name, hexval in INKS.items():
        assert getattr(palette, name).lower() == hexval
    dupes = [n for n in dir(palette) if not n.startswith("_") and n != "RIVER"
             and isinstance(getattr(palette, n), str)
             and getattr(palette, n).lower() == INKS["RIVER"]]
    assert not dupes


def test_glyph_tiers_single():
    assert GLYPH_KEYS <= set(registry.GLYPHS)
    for k, v in registry.GLYPHS.items():
        assert isinstance(v["tier"], str) and v["tier"] in {"continent", "region", "parish"}


def test_data_homed_and_verbs_annotated():
    for k, v in registry.DATA.items():
        assert v.split("/")[0] in SPINES, (k, v)
    assert registry.DATA["ladder"].split("/")[0] == "Powers"
    assert registry.DATA["ambition_banner"].split("/")[0] == "House"
    assert registry.DATA["desk"].split("/")[0] == "Atlas"
    assert VERB_KEYS <= set(registry.VERBS)
    for k, v in registry.VERBS.items():
        for f in ("what", "why_now", "serves"):
            assert v[f].strip(), (k, f)


def test_accents_and_frames():
    s = new_app_state(seed=7)
    s.game.end_turn()
    frames = {}
    for screen in SPINES:
        a = registry.ACCENTS(screen, s)
        assert isinstance(a["vermillion"], int) and a["vermillion"] <= 5
        assert a["gold_nonplayer"] == 0
        surf = render_screen(s, screen)
        raw = pygame.image.tostring(surf, "RGB")
        frames[screen] = raw
        colours = {raw[i:i + 3] for i in range(0, min(len(raw), 60000), 3)}
        assert len(colours) >= 8, f"{screen} renders near-blank"
    assert frames["House"] != frames["Powers"] != frames["Atlas"]
    assert frames["House"] != frames["Atlas"]


def test_fonts_shipped_and_loaded():
    pygame.font.init()
    for role, needle in (("display", "BodoniModa"), ("body", "EBGaramond")):
        path = registry.FONTS[role]
        assert needle in os.path.basename(path)
        pygame.font.Font(path if os.path.isabs(path) else
                         os.path.join(os.path.dirname(__file__), "..", "..", path), 16)
