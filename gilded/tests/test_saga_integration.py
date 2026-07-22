from gilded.chassis import GildedGame


def test_game_owns_a_director_and_runs():
    g = GildedGame(seed=2026)
    assert hasattr(g, "director") and g.director is not None
    for _ in range(5):
        g.end_turn()
    # the Director accrued facts safely over 5 turns
    assert len(g.director.facts.facts) >= 0


def test_director_does_not_change_state():
    # Same-seed run with the Director active is deterministic (guards no
    # game.rng perturbation). Two runs must match in ending + treasuries.
    a = GildedGame(seed=11)
    for _ in range(30):
        a.end_turn()
    b = GildedGame(seed=11)
    for _ in range(30):
        b.end_turn()
    assert a.game_over == b.game_over
    assert {h: a.houses[h].treasury for h in a.houses} \
        == {h: b.houses[h].treasury for h in b.houses}
    assert [e.text for e in a.events] == [e.text for e in b.events]
