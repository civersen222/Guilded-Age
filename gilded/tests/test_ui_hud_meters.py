"""Gilded UI Wave 2 — HUD meter test suite.

Rules 1-14 from the spec, plus rule 15 (widget fmt).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pygame
import pytest

from gilded.dashboard import Delta, MetricDelta, Scoreboard, AXIS_NAMES
from gilded.ui.broadsheet import (
    LEGIT_DANGER,
    TIDE_DANGER,
    BroadsheetView,
    HudModel,
    _hud_height,
    hud_layout,
    hud_model,
)
from gilded.ui.widgets import Chip, Meter, TONES


# ────────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────────

def _board(
    axes: Optional[Dict[str, float]] = None,
    legitimacy: float = 55.0,
    treasury: float = 100.0,
    tide_level: float = 30.0,
    tide_phase: str = "calm",
    atrocities: float = 0.0,
    rival_name: Optional[str] = "House Blackwood",
    rival_axes: Optional[Dict[str, float]] = None,
    rank: int = 3,
    year: int = 1920,
    turn: int = 20,
    century_pct: float = 20.0,
    era_idx: int = 0,
    era_title: str = "The Age of Steam",
    next_era: str = "The Age of Steel",
    prestige: float = 50.0,
    unrest_avg: float = 20.0,
    brewing_turns: int = 0,
    revolution_explanation: str = "",
) -> Scoreboard:
    if axes is None:
        axes = {"capital": 50.0, "standing": 60.0, "blood": 40.0, "world": 70.0}
    if rival_axes is None and rival_name is not None:
        rival_axes = {"capital": 30.0, "standing": 45.0, "blood": 55.0, "world": 35.0}
    return Scoreboard(
        year=year,
        turn=turn,
        century_pct=century_pct,
        era_idx=era_idx,
        era_title=era_title,
        next_era=next_era,
        axes=axes,
        legitimacy=legitimacy,
        prestige=prestige,
        treasury=treasury,
        tide_level=tide_level,
        tide_phase=tide_phase,
        atrocities=atrocities,
        rival_name=rival_name,
        rival_axes=rival_axes,
        rank=rank,
        unrest_avg=unrest_avg,
        brewing_turns=brewing_turns,
        revolution_explanation=revolution_explanation,
    )


def _delta(
    axes_changes: Optional[Dict[str, float]] = None,
    legitimacy_change: float = 2.0,
    treasury_change: float = 10.0,
    tide_change: float = 3.0,
    unrest_change: float = -1.0,
    rank_change: float = 0.0,
    first_session: bool = False,
) -> Delta:
    if axes_changes is None:
        axes_changes = {"capital": 5.0, "standing": -2.0, "blood": 3.0, "world": -1.0}
    axes_md: Dict[str, MetricDelta] = {}
    for name, change in axes_changes.items():
        direction = 0 if change == 0 else (1 if change > 0 else -1)
        axes_md[name] = MetricDelta(change=change, direction=direction)
    return Delta(
        first_session=first_session,
        axes=axes_md,
        legitimacy=MetricDelta(change=legitimacy_change, direction=0 if legitimacy_change == 0 else (1 if legitimacy_change > 0 else -1)),
        treasury=MetricDelta(change=treasury_change, direction=0 if treasury_change == 0 else (1 if treasury_change > 0 else -1)),
        tide_level=MetricDelta(change=tide_change, direction=0 if tide_change == 0 else (1 if tide_change > 0 else -1)),
        unrest_avg=MetricDelta(change=unrest_change, direction=0 if unrest_change == 0 else (1 if unrest_change > 0 else -1)),
        rank=MetricDelta(change=rank_change, direction=0 if rank_change == 0 else (1 if rank_change > 0 else -1)),
    )


# ────────────────────────────────────────────────────────────────────────────
# Rule 1: Each axis is a Meter with lo=0, hi=100, value == board.axes[name]
# ────────────────────────────────────────────────────────────────────────────

# Each axis is a Meter with lo=0, hi=100, value == board.axes[name].

def test_all_four_axes_are_meters():
    b = _board(axes={"capital": 80.0, "standing": 45.0, "blood": 25.0, "world": 90.0})
    d = _delta()
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        assert name in m.meters, f"{name} missing from meters"
        mt = m.meters[name]
        assert isinstance(mt, Meter), f"{name} is not a Meter"

def test_axis_lo_is_zero():
    b = _board()
    d = _delta()
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        assert m.meters[name].lo == 0, f"{name}.lo should be 0, got {m.meters[name].lo}"

def test_axis_hi_is_100():
    b = _board()
    d = _delta()
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        assert m.meters[name].hi == 100, f"{name}.hi should be 100, got {m.meters[name].hi}"

def test_axis_values_match_board():
    axes = {"capital": 80.0, "standing": 45.0, "blood": 25.0, "world": 90.0}
    b = _board(axes=axes)
    d = _delta()
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        assert m.meters[name].value == axes[name], \
            f"{name} value {m.meters[name].value} != board {axes[name]}"


# ────────────────────────────────────────────────────────────────────────────
# Rule 2: Axis meters carry CHANGE as delta
# ────────────────────────────────────────────────────────────────────────────

# Axis meters carry the CHANGE as their delta.

def test_axis_delta_equals_change():
    changes = {"capital": 5.0, "standing": -2.0, "blood": 3.0, "world": -1.0}
    b = _board()
    d = _delta(axes_changes=changes)
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        assert m.meters[name].delta == changes[name], \
            f"{name} delta {m.meters[name].delta} != change {changes[name]}"

def test_axis_delta_is_change_not_direction():
    """Using direction instead of change must fail."""
    b = _board()
    d = _delta(axes_changes={"capital": 5.0, "standing": 3.0, "blood": -2.0, "world": 7.0})
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        md = d.axes[name]
        if abs(md.change) != 1:
            assert m.meters[name].delta != md.direction, \
                f"{name} delta should be change ({md.change}), not direction ({md.direction})"


# ────────────────────────────────────────────────────────────────────────────
# Rule 3: First session — every axis meter has delta is None
# ────────────────────────────────────────────────────────────────────────────

# On first session every axis meter has delta is None.

def test_first_session_no_delta():
    b = _board()
    d = _delta(first_session=True)
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        assert m.meters[name].delta is None, \
            f"{name} should have delta=None on first session"

def test_first_session_arrow_empty():
    b = _board()
    d = _delta(first_session=True)
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        assert m.meters[name].arrow() == "", \
            f"{name} arrow should be empty on first session"


# ────────────────────────────────────────────────────────────────────────────
# Rule 4: Rival axes are their own meters
# ────────────────────────────────────────────────────────────────────────────

# Rival axes are separate meters built from rival_axes.

def test_rival_axes_are_meters():
    axes = {"capital": 80.0, "standing": 45.0, "blood": 25.0, "world": 90.0}
    rival_axes = {"capital": 30.0, "standing": 45.0, "blood": 55.0, "world": 35.0}
    b = _board(axes=axes, rival_axes=rival_axes)
    d = _delta()
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        key = f"rival:{name}"
        assert key in m.meters, f"{key} missing from meters"
        mt = m.meters[key]
        assert isinstance(mt, Meter)
        assert mt.lo == 0
        assert mt.hi == 100

def test_rival_values_from_rival_axes_not_axes():
    axes = {"capital": 80.0, "standing": 65.0, "blood": 25.0, "world": 90.0}
    rival_axes = {"capital": 30.0, "standing": 45.0, "blood": 55.0, "world": 35.0}
    b = _board(axes=axes, rival_axes=rival_axes)
    d = _delta()
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        key = f"rival:{name}"
        assert m.meters[key].value == rival_axes[name], \
            f"{key} value {m.meters[key].value} != rival_axes {rival_axes[name]}"
        assert m.meters[key].value != axes[name], \
            f"{key} value matches axes[{name}] — rival_axes must differ"

def test_rival_delta_is_none():
    b = _board(rival_axes={"capital": 30.0, "standing": 45.0, "blood": 55.0, "world": 35.0})
    d = _delta()
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        key = f"rival:{name}"
        assert m.meters[key].delta is None, \
            f"{key} should have delta=None (no rival history)"


# ────────────────────────────────────────────────────────────────────────────
# Rule 5: No rival_axes — no rival:* keys, texts["rival"] non-empty
# ────────────────────────────────────────────────────────────────────────────

# When rival_axes is None, no rival:* keys, texts['rival'] non-empty.

def test_no_rival_keys_when_none():
    b = _board(rival_axes=None, rival_name=None)
    d = _delta()
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        key = f"rival:{name}"
        assert key not in m.meters, f"{key} should not exist when rival_axes is None"

def test_rival_text_non_empty_when_none():
    b = _board(rival_axes=None, rival_name=None)
    d = _delta()
    m = hud_model(b, d)
    assert "rival" in m.texts
    assert m.texts["rival"], "texts['rival'] should be non-empty when no rival"

def test_hud_model_does_not_raise_with_no_rival():
    b = _board(rival_axes=None, rival_name=None)
    d = _delta()
    m = hud_model(b, d)
    assert isinstance(m, HudModel)


# ────────────────────────────────────────────────────────────────────────────
# Rule 6: Legitimacy danger
# ────────────────────────────────────────────────────────────────────────────

# Legitimacy meter has danger=('below', LEGIT_DANGER).

def test_legitimacy_meter_has_danger():
    b = _board()
    d = _delta()
    m = hud_model(b, d)
    legit = m.meters["legitimacy"]
    assert legit.danger is not None, "legitimacy should have danger set"
    assert legit.danger[0] == "below", "legitimacy danger direction should be 'below'"
    assert legit.danger[1] == LEGIT_DANGER, \
        f"legitimacy danger threshold should be LEGIT_DANGER ({LEGIT_DANGER})"

def test_legitimacy_at_danger_tones_bad():
    b = _board(legitimacy=LEGIT_DANGER)
    d = _delta()
    m = hud_model(b, d)
    legit = m.meters["legitimacy"]
    assert legit.tone() == "bad", \
        f"legitimacy at LEGIT_DANGER ({LEGIT_DANGER}) should tone 'bad', got '{legit.tone()}'"

def test_legitimacy_above_danger_does_not_tone_bad():
    b = _board(legitimacy=LEGIT_DANGER + 10)
    d = _delta()
    m = hud_model(b, d)
    legit = m.meters["legitimacy"]
    assert legit.tone() != "bad", \
        f"legitimacy at {LEGIT_DANGER + 10} should NOT tone 'bad', got '{legit.tone()}'"


# ────────────────────────────────────────────────────────────────────────────
# Rule 7: Tide invert + danger
# ────────────────────────────────────────────────────────────────────────────

# Tide meter has invert=True and danger=('above', TIDE_DANGER).

def test_tide_meter_has_invert():
    b = _board()
    d = _delta()
    m = hud_model(b, d)
    tide = m.meters["tide"]
    assert tide.invert, "tide meter should have invert=True"

def test_tide_meter_has_danger_above():
    b = _board()
    d = _delta()
    m = hud_model(b, d)
    tide = m.meters["tide"]
    assert tide.danger is not None, "tide should have danger set"
    assert tide.danger[0] == "above", "tide danger direction should be 'above'"
    assert tide.danger[1] == TIDE_DANGER

def test_rising_tide_tones_bad():
    b = _board(tide_level=60.0)
    d = _delta(tide_change=5.0)
    m = hud_model(b, d)
    tide = m.meters["tide"]
    assert tide.delta_tone() == "bad", \
        f"rising tide should tone 'bad' (invert), got '{tide.delta_tone()}'"

def test_falling_tide_tones_good():
    b = _board(tide_level=60.0)
    d = _delta(tide_change=-5.0)
    m = hud_model(b, d)
    tide = m.meters["tide"]
    assert tide.delta_tone() == "good", \
        f"falling tide should tone 'good' (invert), got '{tide.delta_tone()}'"


# ────────────────────────────────────────────────────────────────────────────
# Rule 8: Atrocities chip tone
# ────────────────────────────────────────────────────────────────────────────

# Atrocities chip tones 'bad' when > 0, 'neutral' when 0.

def test_atrocities_positive_tones_bad():
    b = _board(atrocities=5.0)
    d = _delta()
    m = hud_model(b, d)
    chip = m.chips["atrocities"]
    assert chip.tone == "bad", f"atrocities=5.0 should tone 'bad', got '{chip.tone}'"

def test_atrocities_zero_tones_neutral():
    b = _board(atrocities=0.0)
    d = _delta()
    m = hud_model(b, d)
    chip = m.chips["atrocities"]
    assert chip.tone == "neutral", f"atrocities=0.0 should tone 'neutral', got '{chip.tone}'"


# ────────────────────────────────────────────────────────────────────────────
# Rule 9: Treasury chip tone from delta direction
# ────────────────────────────────────────────────────────────────────────────

# Treasury chip tones from delta direction.

def test_treasury_rising_tones_good():
    b = _board(treasury=110.0)
    d = _delta(treasury_change=10.0)
    m = hud_model(b, d)
    chip = m.chips["treasury"]
    assert chip.tone == "good", f"treasury rising should tone 'good', got '{chip.tone}'"

def test_treasury_falling_tones_bad():
    b = _board(treasury=90.0)
    d = _delta(treasury_change=-10.0)
    m = hud_model(b, d)
    chip = m.chips["treasury"]
    assert chip.tone == "bad", f"treasury falling should tone 'bad', got '{chip.tone}'"

def test_treasury_flat_tones_neutral():
    b = _board(treasury=100.0)
    d = _delta(treasury_change=0.0)
    m = hud_model(b, d)
    chip = m.chips["treasury"]
    assert chip.tone == "neutral", f"treasury flat should tone 'neutral', got '{chip.tone}'"

def test_treasury_first_session_tones_neutral():
    b = _board()
    d = _delta(first_session=True)
    m = hud_model(b, d)
    chip = m.chips["treasury"]
    assert chip.tone == "neutral", f"first session treasury should tone 'neutral', got '{chip.tone}'"


# ────────────────────────────────────────────────────────────────────────────
# Rule 10: hud_layout returns rect for every key, set equality
# ────────────────────────────────────────────────────────────────────────────

# hud_layout returns a rect for every key the model declares.

def test_layout_coverage_with_rival():
    b = _board()
    d = _delta()
    m = hud_model(b, d)
    band = pygame.Rect(0, 40, 1280, 200)
    layout = hud_layout(m, band)
    expected_keys = set(m.meters.keys()) | set(m.chips.keys()) | set(m.texts.keys())
    actual_keys = set(layout.keys())
    assert actual_keys == expected_keys, \
        f"Layout keys {actual_keys} != expected {expected_keys}"

def test_layout_coverage_no_rival():
    b = _board(rival_axes=None, rival_name=None)
    d = _delta()
    m = hud_model(b, d)
    band = pygame.Rect(0, 40, 1280, 200)
    layout = hud_layout(m, band)
    expected_keys = set(m.meters.keys()) | set(m.chips.keys()) | set(m.texts.keys())
    actual_keys = set(layout.keys())
    assert actual_keys == expected_keys


# ────────────────────────────────────────────────────────────────────────────
# Rule 11: Every rect inside band with 4px clearance
# ────────────────────────────────────────────────────────────────────────────

# Every rect lies inside the band with at least 4px clearance.

@pytest.mark.parametrize("band_width", [900, 1280, 1600])
def test_clearance_at_width(band_width):
    b = _board()
    d = _delta()
    m = hud_model(b, d)
    band = pygame.Rect(0, 40, band_width, 200)
    layout = hud_layout(m, band)
    clearance = 4
    for key, rect in layout.items():
        assert rect.left >= band.left + clearance, \
            f"{key} left {rect.left} < band.left+{clearance} ({band.left + clearance})"
        assert rect.right <= band.right - clearance, \
            f"{key} right {rect.right} > band.right-{clearance} ({band.right - clearance})"
        assert rect.top >= band.top + clearance, \
            f"{key} top {rect.top} < band.top+{clearance} ({band.top + clearance})"
        assert rect.bottom <= band.bottom - clearance, \
            f"{key} bottom {rect.bottom} > band.bottom-{clearance} ({band.bottom - clearance})"


# ────────────────────────────────────────────────────────────────────────────
# Rule 12: No two rects overlap
# ────────────────────────────────────────────────────────────────────────────

# No two rects returned by hud_layout overlap.

def test_no_overlap():
    b = _board()
    d = _delta()
    m = hud_model(b, d)
    band = pygame.Rect(0, 40, 1280, 200)
    layout = hud_layout(m, band)
    keys = list(layout.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            r1 = layout[keys[i]]
            r2 = layout[keys[j]]
            assert not r1.colliderect(r2), \
                f"Rects '{keys[i]}' {r1} and '{keys[j]}' {r2} overlap"


# ────────────────────────────────────────────────────────────────────────────
# Rule 13: _hud_height leaves room — lowest rect bottom >= 4px above limit
# ────────────────────────────────────────────────────────────────────────────

# Lowest rect bottom is at least 4px above TAB_H + _hud_height().

@pytest.mark.parametrize("band_width", [900, 1280, 1600])
def test_height_fits(band_width):
    b = _board()
    d = _delta()
    m = hud_model(b, d)
    hud_h = _hud_height()
    band = pygame.Rect(0, 40, band_width, hud_h + 50)
    layout = hud_layout(m, band)
    limit = 40 + hud_h
    max_bottom = max(r.bottom for r in layout.values())
    assert max_bottom <= limit - 4, \
        f"At width {band_width}: max bottom {max_bottom} > limit-{4} ({limit - 4})"


# ────────────────────────────────────────────────────────────────────────────
# Rule 14: Band height does not change when rival appears
# ────────────────────────────────────────────────────────────────────────────

# _hud_height() returns the same value regardless of rival presence.

def test_layout_extent_same_with_and_without_rival():
    b_rival = _board()
    b_no_rival = _board(rival_axes=None, rival_name=None)
    d = _delta()
    m_rival = hud_model(b_rival, d)
    m_no_rival = hud_model(b_no_rival, d)
    band = pygame.Rect(0, 40, 1280, 200)
    layout_rival = hud_layout(m_rival, band)
    layout_no_rival = hud_layout(m_no_rival, band)
    rival_bottom = max(r.bottom for r in layout_rival.values())
    no_rival_bottom = max(r.bottom for r in layout_no_rival.values())
    assert rival_bottom == no_rival_bottom, \
        f"Layout extent differs: rival={rival_bottom}, no_rival={no_rival_bottom}"
    # Prove the layouts are not trivially identical
    rival_keys = set(layout_rival.keys())
    no_rival_keys = set(layout_no_rival.keys())
    assert any(k.startswith("rival:") for k in rival_keys), \
        "Rival layout should contain rival:* keys"
    assert not any(k.startswith("rival:") for k in no_rival_keys), \
        "No-rival layout should NOT contain rival:* keys"
    assert rival_keys != no_rival_keys, \
        "Rival and no-rival layouts should have different keys"

def test_height_is_constant_value():
    h = _hud_height()
    assert h > 0, "_hud_height() should be positive"
    assert isinstance(h, int), "_hud_height() should return int"


# ────────────────────────────────────────────────────────────────────────────
# Rule 15: Widget fmt — axis meter value_text shows "80" not "80.0"
# ────────────────────────────────────────────────────────────────────────────

# Axis meter whose value is 80.0 has value_text() == '80'.

def test_value_text_format():
    mt = Meter(label="test", value=80.0, lo=0, hi=100, fmt="{:.0f}")
    assert mt.value_text() == "80", f"value_text() = '{mt.value_text()}', expected '80'"

def test_axis_meters_use_fmt():
    b = _board(axes={"capital": 80.0, "standing": 45.0, "blood": 25.0, "world": 90.0})
    d = _delta()
    m = hud_model(b, d)
    for name in AXIS_NAMES:
        mt = m.meters[name]
        expected = str(int(mt.value))
        assert mt.value_text() == expected, \
            f"{name} value_text() = '{mt.value_text()}', expected '{expected}'"


# ────────────────────────────────────────────────────────────────────────────
# Rule I5a: Revolution countdown chip
# ────────────────────────────────────────────────────────────────────────────

def test_revolution_chip_absent_when_zero():
    b = _board(brewing_turns=0)
    d = _delta()
    m = hud_model(b, d)
    assert "revolution" not in m.chips


def test_revolution_chip_present_when_brewing():
    b = _board(brewing_turns=2)
    d = _delta()
    m = hud_model(b, d)
    assert "revolution" in m.chips
    chip = m.chips["revolution"]
    assert chip.tone == "bad"
    assert "2" in chip.text
    assert "3" in chip.text


def test_revolution_chip_shows_count():
    b = _board(brewing_turns=1)
    d = _delta()
    m = hud_model(b, d)
    assert "revolution" in m.chips
    assert "1" in m.chips["revolution"].text


def test_revolution_chip_includes_explanation():
    """When revolution_explanation is set, the chip text includes it."""
    b = _board(brewing_turns=2, revolution_explanation="mandate collapsed; Yorkshire striking")
    d = _delta()
    m = hud_model(b, d)
    chip = m.chips["revolution"]
    assert "mandate collapsed" in chip.text, \
        f"Expected 'mandate collapsed' in chip text, got '{chip.text}'"
    assert "Yorkshire striking" in chip.text, \
        f"Expected 'Yorkshire striking' in chip text, got '{chip.text}'"


def test_revolution_chip_without_explanation():
    """When revolution_explanation is empty, the chip shows only the count."""
    b = _board(brewing_turns=2, revolution_explanation="")
    d = _delta()
    m = hud_model(b, d)
    chip = m.chips["revolution"]
    assert "2" in chip.text
    assert "3" in chip.text
    assert "—" not in chip.text, \
        f"Expected no separator when explanation is empty, got '{chip.text}'"