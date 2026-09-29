"""S15: AI houses name their own heirs while the ruler still lives.

name_heir designates the first dynasty member the three-tier order would
pick today, so the documented designated-heir rule at succession.py:39
finally executes in AI play: an heir named before its ruler dies actually
inherits.
"""
from gilded.chassis import GildedGame
from gilded.society.succession import name_heir, resolve_succession, _designated_heir
from gilded.society.house_ai import tick_realm


def _ai_realm(g):
    return next(r for h, r in g.realms.items() if not g.houses[h].is_player)


def test_name_heir_designates_who_the_line_would_pick():
    g = GildedGame(seed=7)
    realm = _ai_realm(g)
    expected = resolve_succession(realm)
    msg = name_heir(realm)
    assert msg is not None and "is named heir" in msg
    heir = _designated_heir(realm)
    assert heir is not None and heir.is_alive
    assert heir.id == expected.id          # exactly the line's pick today
    assert heir is not realm.ruler
    assert heir.is_heir is True
    # already designated -> nothing to do
    assert name_heir(realm) is None


def test_ai_houses_have_living_designated_heirs_by_turn_12():
    g = GildedGame(seed=7)
    ai_houses = [h for h in g.houses if not g.houses[h].is_player]
    assert ai_houses
    for _ in range(12):
        g.end_turn()
    for h in ai_houses:
        heir = _designated_heir(g.realms[h])
        assert heir is not None and heir.is_alive, f"{h} has no living heir"


def test_named_heir_inherits_when_ruler_dies():
    g = GildedGame(seed=7)
    realm = _ai_realm(g)
    name_heir(realm)
    heir = _designated_heir(realm)
    old_ruler = realm.ruler
    old_ruler.is_alive = False
    msgs, _born = tick_realm(realm, g.turn + 1, g.rng, g.tide)
    assert realm.ruler is heir
    assert realm.court.ruler is heir
    assert heir.id in realm.dynasty.all_characters
    assert any(old_ruler.name in m and heir.name in m and "died" in m
               for m in msgs)
