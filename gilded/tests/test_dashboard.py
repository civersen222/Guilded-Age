"""Stage 1 read-model: the scoreboard and its turn-over-turn delta.

UI7 additions: significance floor tests.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from gilded.chassis import GildedGame, TURN_BUDGET
from gilded.dashboard import Delta, Scoreboard, delta, scoreboard, SIGNIFICANCE, _md
from gilded.endings import judge


def _game():
    g = GildedGame(seed=42)
    h = sorted(g.houses)[0]
    g.houses[h].is_player = True
    return g, h


def test_scoreboard_fields_in_range():
    g, h = _game()
    b = scoreboard(g, h)
    assert isinstance(b, Scoreboard)
    for k in ("capital", "standing", "blood", "world"):
        assert 0.0 <= b.axes[k] <= 100.0
    assert 0.0 <= b.century_pct <= 1.0
    assert b.turn == g.turn
    assert 1 <= b.rank <= len(g.houses)
    assert b.tide_phase in ("reformist", "socialist", "revolutionary")


def test_axes_match_judgment_numbers():
    # The mid-game meters must be the *same numbers* the final judgment uses.
    g, h = _game()
    g.turn = TURN_BUDGET + 1
    ep = judge(g, h)
    b = scoreboard(g, h)
    for k in ("capital", "standing", "blood", "world"):
        assert abs(b.axes[k] - ep.axes[k]) < 1e-9


def test_scoreboard_does_not_mutate_game():
    g, h = _game()
    before = (g.turn, g.tide.level, g.tide.atrocities,
              dict(g.legitimacy),
              {n: g.houses[n].treasury for n in g.houses})
    scoreboard(g, h)
    after = (g.turn, g.tide.level, g.tide.atrocities,
             dict(g.legitimacy),
             {n: g.houses[n].treasury for n in g.houses})
    assert before == after


def test_rank_is_a_stable_permutation():
    g, h = _game()
    for _ in range(5):
        g.end_turn()
    b = scoreboard(g, h)
    assert 1 <= b.rank <= len(g.houses)


def test_era_before_the_age_on_fresh_game():
    g, h = _game()
    b = scoreboard(g, h)
    assert b.era_idx == -1  # "Before the Age" is index -1


def test_delta_first_session_is_zero():
    g, h = _game()
    b = scoreboard(g, h)
    d = delta(None, b)
    assert d.first_session
    assert d.axes["capital"].change == 0.0
    assert d.axes["capital"].direction == 0


def test_delta_reports_signed_change():
    g, h = _game()
    b0 = scoreboard(g, h)
    g.end_turn()
    b1 = scoreboard(g, h)
    d = delta(b0, b1)
    assert not d.first_session
    assert abs(d.tide_level.change - (b1.tide_level - b0.tide_level)) < 1e-9
    expect = (b1.treasury > b0.treasury) - (b1.treasury < b0.treasury)
    assert d.treasury.direction == expect


# ────────────────────────────────────────────────────────────────────────────
# UI7: significance floor tests
# ────────────────────────────────────────────────────────────────────────────

def test_significance_constant_range():
    """SIGNIFICANCE is > 0 and <= 0.1."""
    assert 0 < SIGNIFICANCE <= 0.1


def test_float_epsilon_is_not_news():
    """A change of 1e-9 is below SIGNIFICANCE (0.05) -> direction 0."""
    md = _md(1.0, 1.0 + 1e-9)
    assert md.direction == 0
    assert abs(md.change - 1e-9) < 1e-15


def test_0_01_is_not_news():
    """A change of 0.01 is below SIGNIFICANCE (0.05) -> direction 0."""
    md = _md(1.0, 1.01)
    assert md.direction == 0
    assert abs(md.change - 0.01) < 1e-9


def test_0_05_boundary_is_news():
    """A change of exactly 0.05 is NOT below SIGNIFICANCE -> direction nonzero."""
    md = _md(1.0, 1.05)
    assert md.direction != 0
    assert md.direction == 1


def test_0_25_is_news():
    """A change of 0.25 is reported as a direction."""
    md = _md(1.0, 1.25)
    assert md.direction == 1


def test_0_4_is_news():
    """A change of 0.4 is reported as a direction."""
    md = _md(1.0, 1.4)
    assert md.direction == 1


def test_negative_change_is_news():
    """A sign-reversed change of SIGNIFICANCE is reported."""
    md = _md(1.0, 1.0 - SIGNIFICANCE)
    assert md.direction == -1


def test_suppressed_change_carries_true_size():
    """A suppressed change still reports its true magnitude."""
    md = _md(1.0, 1.0 + 0.01)
    assert md.direction == 0
    assert abs(md.change - 0.01) < 1e-9


# ────────────────────────────────────────────────────────────────────────────
# ITEM 4 (UI7b): SIGNIFICANCE boundary — exact-arithmetic discipline
#
# The probe must use values where the subtraction is EXACT in binary FP.
# 0.05 - 0.0 == 0.05 exactly.  1.05 - 1.0 == 0.0500...04 (not exact).
# Therefore we start from 0.0, not 1.0, so the test can distinguish < from <=.
# ────────────────────────────────────────────────────────────────────────────

def test_significance_boundary_exact_positive():
    """A change of EXACTLY SIGNIFICANCE (0.05) IS news — direction == 1.

    Uses 0.0 -> 0.05 because 0.05 - 0.0 == 0.05 exactly in binary FP.
    Hard-coded 0.05, not derived from SIGNIFICANCE, so a test that computes
    its expectation from the constant it guards CANNOT pass vacuously.
    """
    md = _md(0.0, 0.05)
    assert md.direction == 1, f"Change of exactly 0.05 must be news, got direction {md.direction}"


def test_significance_boundary_exact_negative():
    """A change of EXACTLY -SIGNIFICANCE (-0.05) IS news — direction == -1.

    Uses 0.0 -> -0.05 because -0.05 - 0.0 == -0.05 exactly in binary FP.
    """
    md = _md(0.0, -0.05)
    assert md.direction == -1, f"Change of exactly -0.05 must be news, got direction {md.direction}"


def test_largest_non_news_change():
    """A change just below SIGNIFICANCE (0.04) is NOT news — direction == 0.

    Uses 0.0 -> 0.04 because 0.04 - 0.0 == 0.04 exactly in binary FP.
    """
    md = _md(0.0, 0.04)
    assert md.direction == 0, f"Change of 0.04 must be suppressed, got direction {md.direction}"


def test_figure_surviving_changes_not_zero():
    """figure() of each surviving change does not read as zero."""
    from gilded.ui.figures import figure
    for val in [SIGNIFICANCE, 0.25, 0.4, 1.0]:
        result = figure(val)
        assert result != "0", f"figure({val}) = '{result}' must not read as zero"


def test_md_preserves_sign_of_change():
    """Item 4 (UI7d): _md() must preserve the sign of the change value.

    Mutation R20: returning MetricDelta(abs(change), direction) strips the
    sign from .change while keeping direction intact — every call site that
    reads the sign off the change is dead."""
    # Falling: prev=5.0, curr=3.0 => change=-2.0, direction=-1
    md_fall = _md(5.0, 3.0)
    assert md_fall.change == -2.0, f"_md(5.0, 3.0).change must be -2.0, got {md_fall.change}"
    assert md_fall.direction == -1, f"_md(5.0, 3.0).direction must be -1, got {md_fall.direction}"

    # Rising: prev=3.0, curr=5.0 => change=+2.0, direction=+1
    md_rise = _md(3.0, 5.0)
    assert md_rise.change == 2.0, f"_md(3.0, 5.0).change must be 2.0, got {md_rise.change}"
    assert md_rise.direction == 1, f"_md(3.0, 5.0).direction must be 1, got {md_rise.direction}"


def test_delta_rank_change_direction():
    """Item 4 (UI7e): delta() must compute rank change in the right direction.

    Rank 1 is best; a climb (prev=5 -> curr=2) produces a negative change.
    A fall (prev=2 -> curr=5) produces a positive change."""
    from gilded.dashboard import Scoreboard, delta, MetricDelta

    flat_axes = {"capital": 50.0, "standing": 50.0,
                 "blood": 50.0, "world": 50.0}

    # Climb: rank 5 -> 2 (improvement)
    prev_climb = Scoreboard(
        year=1837, turn=1, century_pct=0.01, era_idx=0,
        era_title="Age of Reform", next_era="hint",
        axes=flat_axes, legitimacy=50.0, prestige=0.0,
        treasury=100.0, tide_level=1.0, tide_phase="reformist",
        atrocities=0.0, rival_name=None, rival_axes=None,
        rank=5, unrest_avg=10.0,
    )
    curr_climb = Scoreboard(
        year=1837, turn=2, century_pct=0.02, era_idx=0,
        era_title="Age of Reform", next_era="hint",
        axes=flat_axes, legitimacy=50.0, prestige=0.0,
        treasury=100.0, tide_level=1.0, tide_phase="reformist",
        atrocities=0.0, rival_name=None, rival_axes=None,
        rank=2, unrest_avg=10.0,
    )
    result_climb = delta(prev_climb, curr_climb)
    assert result_climb.rank.change < 0, (
        f"Climb 5->2 should have negative change, got {result_climb.rank.change}")
    assert result_climb.rank.change == -3.0, (
        f"Climb 5->2 change must be -3.0, got {result_climb.rank.change}")

    # Fall: rank 2 -> 5 (worsening)
    prev_fall = Scoreboard(
        year=1837, turn=1, century_pct=0.01, era_idx=0,
        era_title="Age of Reform", next_era="hint",
        axes=flat_axes, legitimacy=50.0, prestige=0.0,
        treasury=100.0, tide_level=1.0, tide_phase="reformist",
        atrocities=0.0, rival_name=None, rival_axes=None,
        rank=2, unrest_avg=10.0,
    )
    curr_fall = Scoreboard(
        year=1837, turn=2, century_pct=0.02, era_idx=0,
        era_title="Age of Reform", next_era="hint",
        axes=flat_axes, legitimacy=50.0, prestige=0.0,
        treasury=100.0, tide_level=1.0, tide_phase="reformist",
        atrocities=0.0, rival_name=None, rival_axes=None,
        rank=5, unrest_avg=10.0,
    )
    result_fall = delta(prev_fall, curr_fall)
    assert result_fall.rank.change > 0, (
        f"Fall 2->5 should have positive change, got {result_fall.rank.change}")
    assert result_fall.rank.change == 3.0, (
        f"Fall 2->5 change must be 3.0, got {result_fall.rank.change}")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
