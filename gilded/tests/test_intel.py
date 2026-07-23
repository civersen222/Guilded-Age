import copy

from gilded.chassis import GildedGame
from gilded import agenda, intel
from gilded.intel import IntelReport, report, threat_rank


def _two_houses(g):
    hs = sorted(g.houses)
    return hs[0], hs[1]


def test_report_shape_and_bounds():
    g = GildedGame(seed=3)
    a, b = _two_houses(g)
    r = report(g, a, b)
    assert isinstance(r, IntelReport)
    assert 0 <= r.tier <= 3
    assert isinstance(r.breakdown, list)
    assert isinstance(r.apparent_intent, str)
    assert r.tier == min(3, len(r.breakdown))


def test_informant_raises_tier_and_lists_source():
    g = GildedGame(seed=3)
    a, b = _two_houses(g)
    base = report(g, a, b).tier
    g.informants.add((a, b))
    r = report(g, a, b)
    assert r.tier >= base
    assert "informant in place" in r.breakdown


def test_report_is_pure_no_mutation():
    g = GildedGame(seed=8)
    a, b = _two_houses(g)
    agenda.ensure_agenda(g, b)
    before = copy.deepcopy(g.agendas)
    report(g, a, b)
    report(g, a, b)
    assert g.agendas == before
    assert (a, b) not in g.informants


def test_tier0_hides_intent():
    g = GildedGame(seed=8)
    a, b = _two_houses(g)
    r = report(g, a, b)
    if r.tier == 0:
        assert "unknown" in r.apparent_intent.lower()


def test_threat_rank_orders_player_targeter_first():
    g = GildedGame(seed=4)
    player = sorted(g.houses)[0]
    g.houses[player].is_player = True
    other = sorted(h for h in g.houses if h != player)[0]
    g.agendas[other] = agenda.Goal("Conquest", player, g.turn, 10, "war")
    ranked = threat_rank(g)
    assert ranked[0] == other
    assert player not in ranked


def test_intent_gating_is_exact(monkeypatch):
    """Tier 2 names only the family; tier 3 adds the target House and the why."""
    g = GildedGame(seed=8)
    a, b = _two_houses(g)
    g.agendas[b] = agenda.Goal("Buyout", a, g.turn, 10, "buying in")
    g.informants.discard((a, b))
    monkeypatch.setattr(intel, "_shares_border", lambda *_: True)
    monkeypatch.setattr(intel, "_diplomatic_visibility", lambda *_: True)
    monkeypatch.setattr(intel, "_depth_visibility", lambda *_: False)
    r2 = report(g, a, b)
    assert r2.tier == 2
    assert "Buyout" in r2.apparent_intent
    assert f"House {a}" not in r2.apparent_intent      # target hidden at tier 2
    monkeypatch.setattr(intel, "_depth_visibility", lambda *_: True)
    r3 = report(g, a, b)
    assert r3.tier == 3
    assert f"House {a}" in r3.apparent_intent           # target revealed at tier 3
    assert "buying in" in r3.apparent_intent


def test_threat_rank_no_player_lists_all_houses():
    """With no player set, threat_rank still deterministically orders every House."""
    g = GildedGame(seed=4)
    for h in g.houses.values():
        h.is_player = False
    ranked = threat_rank(g)
    assert set(ranked) == set(g.houses)
    assert ranked == threat_rank(g)          # deterministic, no crash on player=None
