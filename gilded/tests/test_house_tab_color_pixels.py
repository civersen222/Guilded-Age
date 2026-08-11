"""Pixel-level colour assertions for the House tab.

Each test renders the tab to an off-screen surface and verifies that
specific regions contain the expected colour values.  These cases are
designed to go RED when the corresponding UI constants are perturbed
by the perturbation harness.

Uses HARDCODED expected colours so that when house_tab constants are
perturbed, the rendered pixels no longer match and the test fails.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

import pygame

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import report as peerage_report
from gilded.ui.house_tab import draw_house_tab

# Hardcoded expected colours (the canonical values from widgets.TONES / widgets.INK)
_EXPECTED_INK = (28, 24, 20)
_EXPECTED_BAD = (180, 50, 40)
_EXPECTED_GOOD = (34, 120, 68)
_EXPECTED_WARN = (200, 150, 30)


def _color_distance(c1, c2):
    """Euclidean distance between two RGB colours."""
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2) ** 0.5


def _count_nearby(surf, target, threshold=60):
    """Count pixels within *threshold* colour distance of *target*."""
    count = 0
    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            c = surf.get_at((x, y))[:3]
            if _color_distance(c, target) < threshold:
                count += 1
    return count


def _make():
    """Return (game, view) for the default house."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def _draw():
    """Draw the house tab and return the surface."""
    g, v = _make()
    rpt = peerage_report(g, v.house)
    surf = pygame.Surface((640, 480))
    rect = pygame.Rect(0, 0, 640, 480)
    draw_house_tab(surf, rect, rpt)
    return surf


def test_pixel_ink_title():
    """The title text renders with the INK colour."""
    surf = _draw()
    count = _count_nearby(surf, _EXPECTED_INK, threshold=40)
    assert count > 500, f"Expected >500 INK pixels, got {count}"


def test_pixel_tone_good():
    """The succession section uses the 'good' tone for the heir marker."""
    surf = _draw()
    count = _count_nearby(surf, _EXPECTED_GOOD, threshold=60)
    assert count > 100, f"Expected >100 GOOD tone pixels, got {count}"


def _draw_disloyal():
    """Draw a tab with a disloyal shareholder to produce bad-tone pixels."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    realm = g.realms.get(house_name)
    rpt = peerage_report(g, house_name)
    for k in rpt.kin:
        if k.shares_pct > 0 and k.is_alive:
            ch = realm.dynasty.all_characters.get(k.char_id)
            if ch:
                ch.loyalty = 10.0
                break
    rpt = peerage_report(g, house_name)
    surf = pygame.Surface((640, 800))
    rect = pygame.Rect(0, 0, 640, 800)
    draw_house_tab(surf, rect, rpt)
    return surf


def test_pixel_tone_bad():
    """Disloyal kin render with the 'bad' tone colour."""
    surf = _draw_disloyal()
    count = _count_nearby(surf, _EXPECTED_BAD, threshold=80)
    assert count > 100, f"Expected >100 BAD tone pixels, got {count}"


def _draw_warn():
    """Draw a tab with a dubious (low-loyalty, no shares) kin to produce warn-tone pixels."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    realm = g.realms.get(house_name)
    # Set loyalty on Octavia (char id 00000002) who has no shares
    for ch in realm.characters:
        if ch.id == '00000002':
            ch.loyalty = 25.0
            break
    rpt = peerage_report(g, house_name)
    surf = pygame.Surface((640, 800))
    rect = pygame.Rect(0, 0, 640, 800)
    draw_house_tab(surf, rect, rpt)
    return surf


def test_pixel_tone_warn():
    """Dubious kin render with the 'warn' tone colour."""
    surf = _draw_warn()
    count = _count_nearby(surf, _EXPECTED_WARN, threshold=80)
    assert count > 100, f"Expected >100 WARN tone pixels, got {count}"


def test_pixel_type_title_size():
    """Title font is TYPE_TITLE (22pt) — title text should be taller than 15px."""
    from gilded.ui.house_tab import _font, TYPE_TITLE, INK
    bold_font = _font(TYPE_TITLE, bold=True)
    title_surf = bold_font.render("HOUSE VANTRELL", True, INK)
    # At TYPE_TITLE=22 the bold title text is ~20px tall; at 12pt it's ~12px
    assert title_surf.get_height() > 15, (
        f"Title text height {title_surf.get_height()} should be > 15 (TYPE_TITLE={TYPE_TITLE})"
    )
