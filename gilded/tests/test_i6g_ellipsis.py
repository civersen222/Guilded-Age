"""I6g — the ellipsis truncation is measurable.

A single over-wide word (no spaces) must produce a tooltip panel whose
content width is strictly less than the cap, proving the truncation loop
actually shortened the word rather than just clipping it.
"""

import pygame
import pytest

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView, TOOLTIP_MAX_WIDTH
from gilded.ui.widgets import Region


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield


def _game_view(seed=42, turns=3):
    g = GildedGame(seed=seed)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for _ in range(turns):
        g.end_turn()
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    return g, v


def test_overwide_word_truncates_panel_width():
    """A single word wider than TOOLTIP_MAX_WIDTH is truncated with ellipsis,
    producing a panel whose content width is strictly less than the cap.

    Without truncation the word would fill to max_w + 2*pad (308 px).
    With truncation the shortened word is shorter, so content_w < max_w
    and panel_w = content_w + 2*pad < max_w + 2*pad.

    This goes RED when the truncation loop (lines 906-908) is removed,
    because the untruncated word then fills to the cap.
    """
    g, v = _game_view()
    surf = pygame.Surface((1200, 800))
    v.draw(surf)

    regions = v.regions._regions
    assert regions, "No regions found"

    # Pick a region with a non-overlapping rect for hovering.
    # The last region (End Turn button) has a unique rect position.
    orig = regions[-1]

    # A single word with no spaces — long enough to exceed TOOLTIP_MAX_WIDTH
    long_word = "a" * 96
    target = Region(
        rect=orig.rect,
        action=orig.action,
        state=orig.state,
        reason=orig.reason,
        hint=long_word,
        group=orig.group,
    )

    # Draw without hover first
    v.hover_pos = None
    v.hovered = None
    v.draw(surf)

    # Monkeypatch regions.at() to always return target, regardless of
    # what position is passed. This ensures the tooltip is drawn for our
    # over-wide word, not some other region's hint.
    orig_at = v.regions.at
    v.regions.at = lambda pos: target

    v.hover_pos = target.rect.center
    v.draw(surf)

    tr = v.tooltip_rect
    assert tr is not None, "Long word produced no tooltip"

    # Assert the tooltip the view ACTUALLY drew is the over-wide text,
    # not some other region's hint that got picked instead.
    assert v.tooltip_text is not None, "No tooltip text produced"
    assert "aaaa" in v.tooltip_text, (
        f"tooltip_text is '{v.tooltip_text}' — the over-wide word was not "
        f"the text the view drew; the hover hit the wrong region")

    cap = TOOLTIP_MAX_WIDTH + 8  # max_w + 2*pad (pad=4)
    assert tr.width < cap, (
        f"tooltip panel width {tr.width} >= cap {cap} — the over-wide word "
        f"was NOT truncated (panel fills to the cap instead of shrinking)")
