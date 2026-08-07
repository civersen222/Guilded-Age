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
    pygame.quit()


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
    original_region = regions[0]

    # A single word with no spaces — long enough to exceed TOOLTIP_MAX_WIDTH
    long_word = "a" * 96
    target = Region(
        rect=original_region.rect,
        action=original_region.action,
        state=original_region.state,
        reason=original_region.reason,
        hint=long_word,
        group=original_region.group,
    )
    v.regions._regions[0] = target

    # Draw without hover first
    v.hover_pos = None
    v.hovered = None
    v.draw(surf)

    # Hover to produce the tooltip — set hovered directly so the replaced
    # region's hint is used (at() iterates in reverse and may pick a different
    # region whose rect overlaps)
    v.hover_pos = target.rect.center
    v.hovered = target
    v.draw(surf)

    tr = v.tooltip_rect
    assert tr is not None, "Long word produced no tooltip"

    cap = TOOLTIP_MAX_WIDTH + 8  # max_w + 2*pad (pad=4)
    assert tr.width < cap, (
        f"tooltip panel width {tr.width} >= cap {cap} — the over-wide word "
        f"was NOT truncated (panel fills to the cap instead of shrinking)")

    v.regions._regions[0] = original_region
