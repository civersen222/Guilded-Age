"""S15: the authored chain system is wired into the turn and reaches the world.

A constructed trigger arms, and every one of its beats reaches the gazette in
the authored order with the braces filled from the live world. The negative
half is asserted too: a chain whose trigger is FALSE emits nothing.
"""
from gilded.chassis import GildedGame
from gilded.society.event_chains import ChainDef, ChainStep
from gilded.society.event_content.chains_pack1 import build_pack1


def _heir_radicalization_game():
    """A world where a living designated heir has turned radical."""
    g = GildedGame(seed=7)
    realm = g.realms["Brandtner"]
    ch = next(c for c in realm.characters
              if c is not realm.ruler and c.is_alive)
    ch.is_heir = True
    ch.dispositions["labor_capital"] = -50.0
    return g, realm, ch


def _frags(text):
    import re
    return [p for p in (re.sub(r"\s+", " ", x).strip()
                        for x in re.split(r"\{[^{}]*\}", str(text)))
            if len(p) >= 6]


def test_constructed_trigger_arms_and_beats_reach_gazette_in_order():
    g, realm, ch = _heir_radicalization_game()
    cdef = next(d for d in build_pack1() if d.chain_id == "heir_radicalization")
    ctx = cdef.trigger(g)
    assert ctx is not None and ctx["heir"] == ch.name
    assert ctx["house"] == realm.house_name

    # --- the machinery: every beat plays in authored order, braces filled ---
    from gilded.society.event_chains import ChainManager
    mgr = ChainManager([cdef])
    msgs = []
    for _ in range(12):
        msgs.extend(mgr.tick(g))
    assert len(msgs) == 3, f"expected three beats, got {len(msgs)}"
    assert ch.name in msgs[0] and realm.house_name in msgs[0]
    assert "publishes a pamphlet" in msgs[1] and ch.name in msgs[1]
    assert "refuses the family dividend" in msgs[2] and ch.name in msgs[2]
    for m in msgs:
        assert "{heir}" not in m and "{house}" not in m, "braces left unfilled"


def test_wired_path_beats_land_in_gazette():
    g, realm, ch = _heir_radicalization_game()
    cdef = next(d for d in build_pack1() if d.chain_id == "heir_radicalization")
    ctx = cdef.trigger(g)
    assert ctx is not None
    events = []
    for _ in range(12):
        g.turn += 1
        g.end_turn()
        events.extend(str(getattr(e, "text", e)) for e in g.events)
    joined = " || ".join(events)
    # every authored beat of the chain is on the record with the braces filled
    for step in cdef.steps:
        for f in _frags(step.text):
            assert f in joined, f"beat fragment missing: {f!r}"
    assert any(ctx["heir"] in e and "pamphlet" in e for e in events)


def test_false_trigger_emits_nothing():
    g = GildedGame(seed=7)
    cdef = ChainDef("never_fires", lambda game: None,
                    [ChainStep("THIS SHOULD NEVER APPEAR", delay=1)])
    from gilded.society.event_chains import ChainManager
    mgr = ChainManager([cdef])
    for _ in range(12):
        assert mgr.tick(g) == []
    # a real def whose world condition is false arms nothing either
    other = next(d for d in build_pack1()
                 if d.chain_id == "coping_spiral")
    mgr2 = ChainManager([other])
    for c in (r.characters for r in g.realms.values()):
        for ch in c:
            ch.stress = 0
    assert sum(len(mgr2.tick(g)) for _ in range(4)) == 0
