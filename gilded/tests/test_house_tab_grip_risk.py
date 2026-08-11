"""Stage 5B — R-F: Shareholder who holds House stock and hates ruler is named.

This is the Grip shortfall's cause.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

import pygame

from gilded.chassis import GildedGame
from gilded.society.relationships import modify_opinion
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import report as peerage_report


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_grip_risk_shown():
    """R-F: A shareholder with negative opinion is named on the tab."""
    g, v = _view()
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = peerage_report(g, v.house)
    # Find a kin with shares
    shareholders = [k for k in rpt.kin if k.shares_pct > 0 and k.is_alive]
    if not shareholders:
        pytest.skip("No shareholders")

    target = shareholders[0]
    target_char = None
    for ch in realm.characters:
        if ch.id == target.char_id:
            target_char = ch
            break
    if target_char is None:
        pytest.skip("Target character not found")

    # Make the shareholder hate the ruler
    modify_opinion(target_char, realm.ruler, -20, "sell signal")

    lines = v.house_lines()
    text = "\n".join(lines)

    assert target.name in text, \
        f"Shareholder '{target.name}' should appear on tab: {text}"
    assert "GRIP" in text or "shares" in text, \
        f"Share info should appear: {text}"


def test_grip_risk_pixel_change():
    """R-F pixel check: making a shareholder disloyal changes pixels."""
    g, v = _view()
    v.active_tab = "House"
    realm = g.realms.get(v.house)
    if realm is None or realm.ruler is None:
        pytest.skip("No realm or ruler")

    rpt = peerage_report(g, v.house)
    shareholders = [k for k in rpt.kin if k.shares_pct > 0 and k.is_alive]
    if not shareholders:
        pytest.skip("No shareholders")

    target = shareholders[0]
    target_char = None
    for ch in realm.characters:
        if ch.id == target.char_id:
            target_char = ch
            break
    if target_char is None:
        pytest.skip("Target character not found")

    surf1 = pygame.Surface((1280, 900))
    v.draw(surf1)
    pixels1 = pygame.image.tobytes(surf1, "RGBA")

    modify_opinion(target_char, realm.ruler, -20, "grip risk")

    surf2 = pygame.Surface((1280, 900))
    v.draw(surf2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    assert pixels1 != pixels2, "Pixels should change when shareholder becomes disloyal"
