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


def test_figure_surviving_changes_not_zero():
    """figure() of each surviving change does not read as zero."""
    from gilded.ui.figures import figure
    for val in [SIGNIFICANCE, 0.25, 0.4, 1.0]:
        result = figure(val)
        assert result != "0", f"figure({val}) = '{result}' must not read as zero"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
