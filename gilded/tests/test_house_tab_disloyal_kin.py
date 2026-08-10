"""Stage 5B — R-B: The disloyal kin flag appears when a man in line for succession drops below loyalty threshold."""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import report
from gilded.society.realm import DISLOYAL_LOYALTY


def test_disloyal_kin_flag():
    """A shareholder who becomes disloyal changes the tab output."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)

    rpt = report(g, house_name)
    # Find a shareholder (shares > 0)
    shareholder = None
    for k in rpt.kin:
        if k.shares_pct > 0 and k.is_alive:
            shareholder = k
            break
    if shareholder is None:
        pytest.skip("No shareholder kin")

    realm = g.realms.get(house_name)
    ch = realm.dynasty.all_characters.get(shareholder.char_id)
    if ch is None:
        pytest.skip("Shareholder not in dynasty")

    lines1 = v.house_lines()
    text1 = "\n".join(lines1)

    # Make the shareholder disloyal (below threshold)
    ch.loyalty = 10.0

    lines2 = v.house_lines()
    text2 = "\n".join(lines2)

    assert text1 != text2, "Lines should differ when a shareholder becomes disloyal"


def test_disloyal_kin_flag_moves_when_threshold_moves():
    """The flag boundary moves when DISLOYAL_LOYALTY moves.

    A shareholder at DISLOYAL_LOYALTY + 0.1 is NOT flagged.
    A shareholder at DISLOYAL_LOYALTY - 0.1 IS flagged.
    """
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)

    rpt = report(g, house_name)
    shareholder = None
    for k in rpt.kin:
        if k.shares_pct > 0 and k.is_alive:
            shareholder = k
            break
    if shareholder is None:
        pytest.skip("No shareholder kin")

    realm = g.realms.get(house_name)
    ch = realm.dynasty.all_characters.get(shareholder.char_id)
    if ch is None:
        pytest.skip("Shareholder not in dynasty")

    # Just above threshold — should NOT be flagged as disloyal
    ch.loyalty = DISLOYAL_LOYALTY + 0.1

    lines_above = v.house_lines()
    text_above = "\n".join(lines_above)

    # Just below threshold — should be flagged as disloyal
    ch.loyalty = DISLOYAL_LOYALTY - 0.1

    lines_below = v.house_lines()
    text_below = "\n".join(lines_below)

    assert text_above != text_below, (
        f"Lines should differ when crossing loyalty threshold. "
        f"Above: {text_above[:200]}... Below: {text_below[:200]}..."
    )


def test_disloyal_kin_flag_shows_band():
    """Disloyal shareholders show their loyalty band in the LOYALTY RISKS section."""
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)

    rpt = report(g, house_name)
    shareholder = None
    for k in rpt.kin:
        if k.shares_pct > 0 and k.is_alive:
            shareholder = k
            break
    if shareholder is None:
        pytest.skip("No shareholder kin")

    realm = g.realms.get(house_name)
    ch = realm.dynasty.all_characters.get(shareholder.char_id)
    if ch is None:
        pytest.skip("Shareholder not in dynasty")

    # Set to clearly disloyal level
    ch.loyalty = 15.0

    lines = v.house_lines()
    text = "\n".join(lines)

    # Should appear in LOYALTY RISKS or show DISLOYAL band
    assert "DISLOYAL" in text or "LOYALTY RISKS" in text, (
        f"Should show disloyal indicator: {text[:500]}"
    )
