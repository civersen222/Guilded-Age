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


def _player(game):
    """The player House, falling back to the first House for a headless
    game (the app always names one; the fixture game does not)."""
    return next((h for h in game.houses if game.houses[h].is_player),
                sorted(game.houses)[0])


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
    divs = [b for b in all_beats if b.facet == "dividends"]
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


def test_game_exposes_ladder_and_beats(game):
    # the public API lives on the game itself, next to the event log it
    # reads and the scoreboard it agrees with
    assert hasattr(game, "ladder") and hasattr(game, "beats")
    assert game.ladder() == ladder(game)
    assert game.beats(next(iter(game.houses))) == beats_for(game,
                                                            next(iter(game.houses)))


def test_beats_public_view_without_a_house(game):
    # the public view: no house argument, so every House's ledger beats
    # are visible, and every beat names a real House
    all_beats = beats(game)
    divs = {b.house for b in all_beats if b.facet == "dividends"}
    for h in game.houses:
        for b in beats_for(game, h):
            if b.facet == "dividends":
                assert b.house in divs
    assert all(b.house in game.houses for b in all_beats)
    assert game.beats() == all_beats


def test_beats_pure_no_mutation(game):
    before = ladder(game)
    player = next(iter(game.houses))
    beats(game, player)
    beats_for(game, player)
    assert ladder(game) == before


def test_briefing_shows_the_ladder(game):
    import pygame
    from gilded.ui.broadsheet import BroadsheetView
    pygame.init()
    player = next(iter(game.houses))
    v = BroadsheetView(game, player)
    v.active_tab = "Briefing"
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    assert v._ladder_rows is not None, "the briefing draws the public ladder"
    assert sorted(r.house for r in v._ladder_rows) == sorted(game.houses)
    # rank 1 is the house winning the age - the player can see who
    assert v._ladder_rows[0].rank == 1


# ---------------------------------------------------------------- wave 2 --
# the exact API surface: game.ladder.standings(), game.beats.{log,deltas,
# inquire}, game.acts.*, and the ui registry.


def test_ladder_facade_standings(game):
    rows = game.ladder.standings()
    assert [r for _h, r, _a in rows] == list(range(1, len(game.houses) + 1))
    # axes are plain floats here, the four endings axes
    for house, _rank, axes in rows:
        assert house in game.houses
        assert set(axes) == {"capital", "standing", "blood", "world"}
        assert all(isinstance(v, float) for v in axes.values())
    # agrees with the wave-1 ladder rows
    assert [(h, r) for h, r, _a in rows] == [
        (row.house, row.rank) for row in ladder(game)]


def test_beats_facade_shape(game):
    for b in game.beats.log:
        assert b.kind in {"signature", "season", "inquiry", "deflection", "gentry"}
        assert isinstance(b.turn, int)
        assert isinstance(b.text, str) and b.text
        assert b.face is None or isinstance(b.face, str)
    # the player's treasury delta has a materialised why?
    player = _player(game)
    t = game.resolved_turn
    deltas = game.beats.deltas(t)
    att = game.beats.inquire(f"{player}.treasury", t)
    assert att.causes and att.check(1e-6)
    assert any(label == f"{player}.treasury" for label, _a in deltas)


def test_acts_set_dial_emits_signature(game):
    player = _player(game)
    ent = next(e for e in game.enterprises if e.house == player)
    beat = game.acts.set_dial(ent.eid, 75.0)
    assert beat.kind == "signature"
    assert beat.face and beat.face in beat.text
    assert ent.extraction_dial == 75.0
    assert any(b.kind == "signature" for b in game.beats.log)
    # clamped to the 0-100 band
    beat = game.acts.set_dial(ent.eid, 150.0)
    assert ent.extraction_dial == 100.0


def test_ui_registry_shape():
    from gilded.ui import registry
    assert "set_dial" in registry.VERBS
    for verb_id, spec in registry.VERBS.items():
        assert spec["what"] and spec["why_now"] and spec["serves"]
    assert registry.DATA
    assert all(isinstance(v, str) and v for v in registry.DATA.values())


def test_all_four_kinds_in_seed7_20_turns():
    from gilded.ui.app import new_app_state
    s = new_app_state(seed=7)
    g = s.game
    mine = [e for e in g.enterprises if e.house == s.house]
    g.acts.set_dial(mine[0].eid, 75.0)
    assert any(b.kind == "signature" for b in g.beats.log)
    for t in range(20):
        g.end_turn()
        lad = g.ladder.standings()
        assert sorted(r for h, r, ax in lad) == list(range(1, len(lad) + 1))
        assert all(att.check(1e-6)
                   for _, att in g.beats.deltas(g.resolved_turn))
    kinds = {b.kind for b in g.beats.log}
    assert kinds >= {"signature", "season", "inquiry", "deflection"}, kinds
    lbl, _ = g.beats.deltas(g.resolved_turn)[0]
    att = g.beats.inquire(lbl, g.resolved_turn)
    assert att.causes and att.check(1e-6)
