"""UI7g: own the family, not the field — every Scoreboard/Delta field pinned, plus tripwires."""

from __future__ import annotations

import dataclasses
from gilded.chassis import GildedGame, year_of, TURN_BUDGET
from gilded.dashboard import Scoreboard, Delta, MetricDelta, scoreboard, delta, _md, SIGNIFICANCE
from gilded.dashboard import ERAS, AXIS_NAMES


# ── helpers ──────────────────────────────────────────────────────────────────

def _game():
    """Return (game, player_house) with a fresh game at seed 42."""
    g = GildedGame(seed=42)
    h = sorted(g.houses)[0]
    g.houses[h].is_player = True
    return g, h


# ═══════════════════════════════════════════════════════════════════════════════
# SCOREBOARD FIELD PINNINGS — the remainder after Wave 7f
# ═══════════════════════════════════════════════════════════════════════════════


def test_scoreboard_year_is_year_of_turn():
    """year field must be year_of(game.turn), not game.turn or a constant."""
    g, h = _game()
    g.turn = 80
    b = scoreboard(g, h)
    expected_year = year_of(g.turn)
    assert b.year == expected_year, f"year should be {expected_year}, got {b.year}"
    # Mutation check: if year were bound to turn directly, they'd be equal.
    # year_of(80) != 80, so this catches it.
    assert b.year != g.turn, "year should not equal turn directly"


def test_scoreboard_century_pct_is_turn_over_budget():
    """century_pct must be game.turn / TURN_BUDGET, clamped [0, 1]."""
    g, h = _game()
    g.turn = TURN_BUDGET // 4  # 25% of the way through
    b = scoreboard(g, h)
    expected = g.turn / TURN_BUDGET
    assert abs(b.century_pct - expected) < 1e-9, \
        f"century_pct should be {expected}, got {b.century_pct}"


def test_scoreboard_era_title_matches_era_idx():
    """era_title must be the title for the current era_idx, not a constant."""
    g, h = _game()
    # Force into a known era by setting age_idx
    g.director.age_idx = 1  # second era
    b = scoreboard(g, h)
    assert b.era_idx == 1
    # Title must match ERAS[1].title, not ERAS[0].title
    expected_title = ERAS[1].title
    assert b.era_title == expected_title, \
        f"era_title should be '{expected_title}', got '{b.era_title}'"


def test_scoreboard_next_era_computed_from_idx():
    """next_era must describe the era after the current idx, not a constant."""
    g, h = _game()
    g.director.age_idx = 1
    b = scoreboard(g, h)
    nxt = g.director.age_idx + 1
    if 0 <= nxt < len(ERAS):
        e = ERAS[nxt]
        expected_hint = f"Next: {e.title} at tide {e.tide:.0f} or turn {e.turn}"
    else:
        expected_hint = "the final age"
    assert b.next_era == expected_hint, \
        f"next_era should be '{expected_hint}', got '{b.next_era}'"


def test_scoreboard_tide_phase_computed_from_level():
    """tide_phase must come from game.tide.phase(), which varies with tide level.

    phase() thresholds: >=66.67 → revolutionary, >=33.33 → socialist, else reformist.
    Mutation: tide_phase = "reformist" (constant) would fail at level 50.
    """
    g, h = _game()
    g.tide.level = 50.0  # 100/3=33.33, 200/3=66.67 → level 50 is "socialist"
    b = scoreboard(g, h)
    # Expected value is a literal computed from the phase() thresholds, not from g.tide.phase()
    assert b.tide_phase == "socialist", \
        f"tide_phase should be 'socialist' at level 50, got '{b.tide_phase}'"


# ═══════════════════════════════════════════════════════════════════════════════
# SCOREBOARD TRIPWIRE — fails when a new field appears without a test
# ═══════════════════════════════════════════════════════════════════════════════


def test_scoreboard_field_roster_complete():
    """Scoreboard must have exactly these fields — adding a new one breaks the suite."""
    actual_fields = {f.name for f in dataclasses.fields(Scoreboard)}
    expected_fields = {
        "year", "turn", "century_pct", "era_idx", "era_title", "next_era",
        "axes", "legitimacy", "prestige", "treasury", "tide_level", "tide_phase",
        "atrocities", "rival_name", "rival_axes", "rank", "unrest_avg",
    }
    missing = expected_fields - actual_fields
    extra = actual_fields - expected_fields
    if missing:
        assert False, f"Scoreboard missing fields: {missing}"
    if extra:
        assert False, f"Scoreboard has extra fields not in roster: {extra}"


# ═══════════════════════════════════════════════════════════════════════════════
# DELTA TRIPWIRE — fails when a new field appears without a test
# ═══════════════════════════════════════════════════════════════════════════════


def test_delta_field_roster_complete():
    """Delta must have exactly these fields — adding a new one breaks the suite."""
    actual_fields = {f.name for f in dataclasses.fields(Delta)}
    expected_fields = {
        "first_session", "axes", "legitimacy", "treasury",
        "tide_level", "unrest_avg", "rank",
    }
    missing = expected_fields - actual_fields
    extra = actual_fields - expected_fields
    if missing:
        assert False, f"Delta missing fields: {missing}"
    if extra:
        assert False, f"Delta has extra fields not in roster: {extra}"


# ═══════════════════════════════════════════════════════════════════════════════
# DELTA FIELD PINNINGS — verify all 7 fields are covered by existing tests
# This test confirms the wiring explicitly for completeness.
# ═══════════════════════════════════════════════════════════════════════════════


def test_delta_first_session_false_when_prev_exists():
    """Delta.first_session must be False when prev is not None."""
    g, h = _game()
    b = scoreboard(g, h)
    d = delta(b, b)
    assert d.first_session is False, "first_session should be False when prev exists"


def test_delta_axes_keys_match_axis_names():
    """Delta.axes must have keys matching AXIS_NAMES, each a MetricDelta."""
    g, h = _game()
    b = scoreboard(g, h)
    d = delta(b, b)
    assert set(d.axes.keys()) == set(AXIS_NAMES), \
        f"Delta.axes keys should be {set(AXIS_NAMES)}, got {set(d.axes.keys())}"
