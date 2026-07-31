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
    """Rank change sign: falling 2->5 gives +3, climbing 5->2 gives -3."""
    prev_fall = Scoreboard(0, 5, 0.5, 0, "Era", "Next", {"capital": 50.0, "standing": 50.0, "blood": 50.0, "world": 50.0}, 50.0, 0.0, 500.0, 0.0, "reformist", 0.0, None, None, 2, 0.0)
    curr_fall = Scoreboard(0, 6, 0.5, 0, "Era", "Next", {"capital": 50.0, "standing": 50.0, "blood": 50.0, "world": 50.0}, 50.0, 0.0, 500.0, 0.0, "reformist", 0.0, None, None, 5, 0.0)
    result_fall = delta(prev_fall, curr_fall)
    assert result_fall.rank.direction == 1, (
        f"Fall 2->5 should have positive direction, got {result_fall.rank.direction}")
    assert result_fall.rank.change == 3.0, (
        f"Fall 2->5 change must be 3.0, got {result_fall.rank.change}")

    prev_climb = Scoreboard(0, 5, 0.5, 0, "Era", "Next", {"capital": 50.0, "standing": 50.0, "blood": 50.0, "world": 50.0}, 50.0, 0.0, 500.0, 0.0, "reformist", 0.0, None, None, 5, 0.0)
    curr_climb = Scoreboard(0, 6, 0.5, 0, "Era", "Next", {"capital": 50.0, "standing": 50.0, "blood": 50.0, "world": 50.0}, 50.0, 0.0, 500.0, 0.0, "reformist", 0.0, None, None, 2, 0.0)
    result_climb = delta(prev_climb, curr_climb)
    assert result_climb.rank.change < 0, (
        f"Climb 5->2 should have negative change, got {result_climb.rank.change}")
    assert result_climb.rank.change == -3.0, (
        f"Climb 5->2 change must be -3.0, got {result_climb.rank.change}")


# ────────────────────────────────────────────────────────────────────────────
# UI7f: scoreboard scalar bindings, delta field wiring, composite, unrest_avg,
#       rival_axes, rank, quiet-turn sentence
# ────────────────────────────────────────────────────────────────────────────


def test_scoreboard_scalars_bound_to_game_values():
    """Each scalar field on the Scoreboard must come from its own game source.

    Sets DISTINCT, recognisable values on the game and asserts each field
    equals the literal it was given.  Mutation: treasury=house.prestige would
    make b.treasury == 17.0, failing the 4321.0 assertion.
    """
    g, h = _game()
    # All distinct, none 0.0 or 50.0
    g.houses[h].treasury = 4321.0
    g.houses[h].prestige = 17.0
    g.legitimacy[h] = 63.0
    g.tide.level = 8.0
    g.tide.atrocities = 3.0

    b = scoreboard(g, h)
    assert b.treasury == 4321.0, f"treasury should be 4321.0, got {b.treasury}"
    assert b.prestige == 17.0, f"prestige should be 17.0, got {b.prestige}"
    assert b.legitimacy == 63.0, f"legitimacy should be 63.0, got {b.legitimacy}"
    assert b.tide_level == 8.0, f"tide_level should be 8.0, got {b.tide_level}"
    assert b.atrocities == 3.0, f"atrocities should be 3.0, got {b.atrocities}"


def test_delta_fields_wired_to_own_change():
    """Each Delta field must carry its own change, not another's.

    Builds two Scoreboards where legitimacy, treasury, tide_level and
    unrest_avg each move by a DIFFERENT amount.  Mutation: wiring
    Delta.unrest_avg to legitimacy would give unrest_avg.change == 1.0,
    failing the 7.0 assertion.
    """
    from dataclasses import replace

    prev = Scoreboard(
        year=1837, turn=1, century_pct=0.04, era_idx=0, era_title="Era",
        next_era="Next", axes={"capital": 50.0, "standing": 50.0,
                               "blood": 50.0, "world": 50.0},
        legitimacy=50.0, prestige=10.0, treasury=100.0,
        tide_level=5.0, tide_phase="reformist", atrocities=0.0,
        rival_name=None, rival_axes=None, rank=1, unrest_avg=5.0)
    curr = replace(prev,
                   legitimacy=51.0,       # +1.0
                   treasury=140.0,        # +40.0
                   tide_level=5.5,        # +0.5
                   unrest_avg=12.0)       # +7.0

    d = delta(prev, curr)
    assert d.legitimacy.change == 1.0, f"legitimacy change should be 1.0, got {d.legitimacy.change}"
    assert d.treasury.change == 40.0, f"treasury change should be 40.0, got {d.treasury.change}"
    assert d.tide_level.change == 0.5, f"tide_level change should be 0.5, got {d.tide_level.change}"
    assert d.unrest_avg.change == 7.0, f"unrest_avg change should be 7.0, got {d.unrest_avg.change}"


def test_delta_axes_change_direction():
    """delta() must compute axis changes as curr - prev (not reversed).

    Rising axis: prev capital 40, curr 55 -> change +15, direction +1.
    Falling axis: prev standing 60, curr 40 -> change -20, direction -1.
    Mutation: _md(curr.axes[k], prev.axes[k]) would invert both signs.
    """
    prev = Scoreboard(
        year=1837, turn=1, century_pct=0.04, era_idx=0, era_title="Era",
        next_era="Next",
        axes={"capital": 40.0, "standing": 60.0, "blood": 30.0, "world": 70.0},
        legitimacy=50.0, prestige=10.0, treasury=100.0,
        tide_level=5.0, tide_phase="reformist", atrocities=0.0,
        rival_name=None, rival_axes=None, rank=1, unrest_avg=5.0)
    curr = Scoreboard(
        year=1837, turn=2, century_pct=0.08, era_idx=0, era_title="Era",
        next_era="Next",
        axes={"capital": 55.0, "standing": 40.0, "blood": 45.0, "world": 50.0},
        legitimacy=50.0, prestige=10.0, treasury=100.0,
        tide_level=5.0, tide_phase="reformist", atrocities=0.0,
        rival_name=None, rival_axes=None, rank=1, unrest_avg=5.0)

    d = delta(prev, curr)
    # Rising axes
    assert d.axes["capital"].change == 15.0, f"capital change should be 15.0, got {d.axes['capital'].change}"
    assert d.axes["capital"].direction == 1
    assert d.axes["blood"].change == 15.0, f"blood change should be 15.0, got {d.axes['blood'].change}"
    assert d.axes["blood"].direction == 1
    # Falling axes
    assert d.axes["standing"].change == -20.0, f"standing change should be -20.0, got {d.axes['standing'].change}"
    assert d.axes["standing"].direction == -1
    assert d.axes["world"].change == -20.0, f"world change should be -20.0, got {d.axes['world'].change}"
    assert d.axes["world"].direction == -1


def test_rival_axes_is_rivals_not_players():
    """scoreboard().rival_axes must be the rival house's axes, not the player's.

    Mutation: rival_axes = _axes_for(game, house_name) would make both
    equal, so the != assertion fails.  Also pins rival_name and the None case.
    """
    g, h = _game()
    houses = sorted(g.houses)
    rival = houses[1] if len(houses) > 1 else houses[0]
    g.director.rival = rival

    # Make rival measurably different from player
    g.houses[rival].treasury = 9999.0
    g.houses[h].treasury = 100.0

    b = scoreboard(g, h)
    assert b.rival_name == rival
    assert b.rival_axes is not None
    # Under the mutation, rival_axes == axes, so this catches it
    assert b.rival_axes["capital"] != b.axes["capital"] or \
           b.rival_axes["standing"] != b.axes["standing"] or \
           b.rival_axes["blood"] != b.axes["blood"] or \
           b.rival_axes["world"] != b.axes["world"], \
           "rival_axes must differ from player axes"

    # None case: with no rival bound, rival_axes must be None
    g.director.rival = None
    b_none = scoreboard(g, h)
    assert b_none.rival_axes is None


def test_rank_is_one_based_and_descending():
    """Strongest house must rank #1; rank must be 1-based, not 0-based.

    Makes one house enormously strong (treasury 1e9) and another very weak
    (treasury -1e9), then asserts the strong house ranks 1 and strictly
    better than the weak one.
    Mutation: rank = order.index(house_name) (no +1) gives rank 0.
    Mutation: sort ascending instead of descending gives the weak house rank 1.
    """
    g, h = _game()
    houses = sorted(g.houses)
    weak = houses[1] if len(houses) > 1 else houses[0]

    # Make player unambiguously strongest, other unambiguously weakest
    g.houses[h].treasury = 1e9
    g.houses[weak].treasury = -1e9

    b_strong = scoreboard(g, h)
    b_weak = scoreboard(g, weak)

    # Fixture bites: strong house has higher capital axis
    assert b_strong.axes["capital"] > b_weak.axes["capital"], \
        f"fixture: strong capital {b_strong.axes['capital']} should exceed weak {b_weak.axes['capital']}"

    assert b_strong.rank == 1, f"strongest house should be rank 1, got {b_strong.rank}"
    assert b_strong.rank < b_weak.rank, \
        f"strong rank {b_strong.rank} should be < weak rank {b_weak.rank}"


def test_composite_counts_all_four_axes():
    """_composite must average all four axes equally.

    One axis at 100.0, others at 0.0 -> 25.0 for each axis in turn.
    Mutation: dropping world gives 0.0 for the world-only case.
    Mutation: double-counting an axis gives 50.0.
    """
    from gilded.dashboard import _composite, AXIS_NAMES

    for name in AXIS_NAMES:
        axes = {k: 0.0 for k in AXIS_NAMES}
        axes[name] = 100.0
        result = _composite(axes)
        assert result == 25.0, f"_composite with only {name}=100 should be 25.0, got {result}"

    # Four different values: 100, 60, 20, 0 -> mean 45.0
    axes_diff = {"capital": 100.0, "standing": 60.0, "blood": 20.0, "world": 0.0}
    result_diff = _composite(axes_diff)
    assert result_diff == 45.0, f"_composite(100,60,20,0) should be 45.0, got {result_diff}"


def test_unrest_avg_is_mean_of_players_provinces():
    """unrest_avg must be the arithmetic mean of the player's provinces only.

    Sets six provinces to 10,10,20,20,30,90 -> mean 30.0.
    Mean differs from max(90), min(10), median(20), sum(180).
    Other houses' provinces set to 99.0 to catch "mean of everything" bug.
    Mutation: max(p.unrest) would give 90.0, not 30.0.
    """
    g, h = _game()
    provs = g.provinces_of(h)
    assert len(provs) == 6, f"player should own 6 provinces, got {len(provs)}"

    # Set player's provinces to known unequal values: mean=30.0, max=90, min=10, median=20
    unrest_values = [10.0, 10.0, 20.0, 20.0, 30.0, 90.0]
    for p, v in zip(provs, unrest_values):
        p.unrest = v

    # Contaminate other houses' provinces
    for other_h in g.houses:
        if other_h != h:
            for p in g.provinces_of(other_h):
                p.unrest = 99.0

    b = scoreboard(g, h)
    assert b.unrest_avg == 30.0, f"unrest_avg should be 30.0 (mean of 10,10,20,20,30,90), got {b.unrest_avg}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
