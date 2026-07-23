"""Stage 1 read-model: the scoreboard and its turn-over-turn delta."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from gilded.chassis import GildedGame, TURN_BUDGET
from gilded.dashboard import Delta, Scoreboard, delta, scoreboard
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
    ranks = {n: scoreboard(g, n).rank for n in g.houses}
    assert sorted(ranks.values()) == list(range(1, len(g.houses) + 1))


def test_era_before_the_age_on_fresh_game():
    # The Director only observes inside end_turn, so a fresh game is pre-Age.
    g, h = _game()
    b = scoreboard(g, h)
    assert b.era_idx == -1
    assert b.era_title == "Before the Age"


def test_delta_first_session_is_zero():
    g, h = _game()
    b = scoreboard(g, h)
    d = delta(None, b)
    assert isinstance(d, Delta)
    assert d.first_session
    assert d.legitimacy.change == 0.0 and d.legitimacy.direction == 0
    for k in ("capital", "standing", "blood", "world"):
        assert d.axes[k].change == 0.0 and d.axes[k].direction == 0


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