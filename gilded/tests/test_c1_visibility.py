"""Mission C1 - the sim becomes visible.

The public ladder ranks every House by the same composite the final
judgment weighs, and every axis value carries Causes that sum exactly to
it. Consequence beats name the moments the world bit back, with the rule
that fired and the Causes behind it. Seed 7 is the watched game: after a
dozen turns somebody is winning and everything that changed has a why.
"""

import pytest

from gilded.beats import Beat, beats, beats_for
from gilded.chassis import GildedGame
from gilded.ladder import leader, ladder


@pytest.fixture
def game():
    g = GildedGame(seed=7)
    for _ in range(12):
        if g.game_over is None:
            g.end_turn()
    return g


def test_ladder_ranks_every_house(game):
    rows = ladder(game)
    assert sorted(r.house for r in rows) == sorted(game.houses)
    assert [r.rank for r in rows] == list(range(1, len(rows) + 1))
    # ranks are composites in descending order
    assert all(a.composite >= b.composite
               for a, b in zip(rows, rows[1:]))


def test_ladder_composite_matches_scoreboard(game):
    from gilded.dashboard import _axes_for, _composite
    for row in ladder(game):
        assert row.composite == pytest.approx(
            _composite(_axes_for(game, row.house)))


def test_ladder_causes_sum_to_their_axis(game):
    for row in ladder(game):
        for name, attr in row.axes.items():
            assert attr.check(), (
                f"{row.house} {name}: causes do not sum to value "
                f"({[c.label for c in attr.causes]})")
            # every cause names the rule that produced it
            for c in attr.causes:
                assert c.source


def test_leader_is_the_winning_house(game):
    rows = ladder(game)
    assert leader(game).house == rows[0].house
    # the winner's causes explain the win - each axis has a named top cause
    for attr in leader(game).axes.values():
        assert attr.causes
        top = max(attr.causes, key=lambda c: abs(c.amount))
        assert top.label


def test_beats_carry_provenance(game):
    player = next(iter(game.houses))
    all_beats = [b for h in game.houses for b in beats_for(game, h)]
    # seed 7 after 12 turns: something happened somewhere - strikes, a
    # union, or dividends. At least the dividend ledger lines, if any,
    # carry Causes that sum to what landed in the treasury.
    divs = [b for b in all_beats if b.kind == "dividends"]
    for b in divs:
        assert b.source == "houses.House.credit"
        # the beat's Causes are the turn's named journal lines, so they
        # sum to the turn's net treasury effect for that house
        net = sum(amt for t, _label, amt in game.houses[b.house].journal
                  if t == b.turn)
        assert pytest.approx(net) == sum(c.amount for c in b.causes)
        assert b.causes
        assert any(c.label == "dividends" for c in b.causes)
    # every beat names the turn and the rule that produced it
    for b in all_beats:
        assert b.turn == game.resolved_turn
        assert b.source and b.text
        assert isinstance(b, Beat)


def test_beats_deterministic():
    a = GildedGame(seed=7)
    b = GildedGame(seed=7)
    for _ in range(12):
        a.end_turn()
        b.end_turn()
    for h in a.houses:
        assert beats(a, h) == beats(b, h)
        assert ladder(a) == ladder(b)


def test_beats_pure_no_mutation(game):
    before = ladder(game)
    player = next(iter(game.houses))
    beats(game, player)
    beats_for(game, player)
    assert ladder(game) == before
