"""WAVE I1 — Region, RegionState, RegionSet (headless)."""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from gilded.ui.widgets import Region, RegionState, RegionSet


def _rect(x=0, y=0, w=100, h=50):
    return pygame.Rect(x, y, w, h)


# 1. at() finds a region under the point
def test_at_finds_region():
    rs = RegionSet()
    rs.add(Region(rect=_rect(0, 0, 100, 50), action={"tap": True}))
    hit = rs.at((50, 25))
    assert hit is not None
    assert hit.rect is not None


# 2. at() returns None outside every rect
def test_at_returns_none_outside():
    rs = RegionSet()
    rs.add(Region(rect=_rect(0, 0, 100, 50), action={"tap": True}))
    assert rs.at((200, 200)) is None


# 3. Two OVERLAPPING regions: the LAST added wins
def test_at_last_added_wins_overlapping():
    rs = RegionSet()
    # Both rects cover (50, 25)
    rs.add(Region(rect=_rect(0, 0, 100, 50), action={"first": True}))
    rs.add(Region(rect=_rect(20, 10, 100, 50), action={"second": True}))
    hit = rs.at((50, 25))
    assert hit is not None
    assert hit.action == {"second": True}


# 4. at() returns a DISABLED region and its reason is readable
def test_at_returns_disabled_with_reason():
    rs = RegionSet()
    rs.add(Region(
        rect=_rect(0, 0, 100, 50),
        action=None,
        state=RegionState.DISABLED,
        reason="No attention left this turn.",
    ))
    hit = rs.at((50, 25))
    assert hit is not None
    assert hit.state is RegionState.DISABLED
    assert hit.reason == "No attention left this turn."


# 5. DISABLED Region with empty reason raises ValueError
def test_disabled_no_reason_raises():
    import pytest
    with pytest.raises(ValueError):
        Region(
            rect=_rect(),
            action=None,
            state=RegionState.DISABLED,
            reason="",
        )


# 6. ENABLED Region with action=None raises ValueError
def test_enabled_no_action_raises():
    import pytest
    with pytest.raises(ValueError):
        Region(
            rect=_rect(),
            action=None,
            state=RegionState.ENABLED,
        )


# 7. UNAVAILABLE Region needs neither reason nor action
def test_unavailable_needs_nothing():
    r = Region(
        rect=_rect(),
        action=None,
        state=RegionState.UNAVAILABLE,
    )
    assert r.state is RegionState.UNAVAILABLE
    assert r.reason == ""
    assert r.action is None


# 8. clear() empties the set
def test_clear():
    rs = RegionSet()
    rs.add(Region(rect=_rect(), action={"tap": True}))
    assert len(rs) == 1
    rs.clear()
    assert len(rs) == 0
    assert rs.at((0, 0)) is None


# 9. CHECK 0 — RegionState has FOUR DISTINCT members
def test_the_four_region_states_are_four_distinct_states():
    assert len(set(RegionState)) == 4
    assert RegionState.ACTIVE is not RegionState.ENABLED
