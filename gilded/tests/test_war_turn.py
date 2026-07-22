"""G16 war-in-the-turn tests: peace terms, the war council, and the wiring."""

import random

from gilded.chassis import GildedGame
from gilded.docket import generate_petitions, initiative, rule
from gilded.fronts import (TRUCE_TURNS, PeaceTerms, WarGoal, ai_acceptable,
                           allocate, declare_war, negotiate_peace,
                           raise_regiments)

SEED = 42


class ZeroRng(random.Random):
    """random() is always 0.0: rulings never fumble, dice roll their floor."""

    def random(self):
        return 0.0


def _game() -> GildedGame:
    return GildedGame(SEED)


def _adjacent_pair(g: GildedGame):
    for a in sorted(g.houses):
        for p in g.provinces_of(a):
            for n in sorted(p.neighbors):
                o = g.atlas.provinces[n].owner
                if o and o != a and o in g.houses:
                    return a, o
    raise AssertionError("seed grew no contested borders")


def _war(g: GildedGame):
    a, d = _adjacent_pair(g)
    return declare_war(g, a, d, WarGoal(kind="humble"))


# --- signing the peace -------------------------------------------------------

def test_peace_cedes_land_pays_gold_and_binds_a_truce():
    g = _game()
    war = _war(g)
    a, d = war.aggressor, war.defender
    war.war_score = 50.0
    target = min(pid for f in war.fronts for pair in f.border for pid in pair
                 if g.atlas.provinces[pid].owner == d)
    ta0, td0 = g.houses[a].treasury, g.houses[d].treasury
    msgs = negotiate_peace(g, war, PeaceTerms(provinces=[target], gold=200.0))
    assert g.atlas.provinces[target].owner == a
    assert g.houses[a].treasury == ta0 + 200.0
    assert g.houses[d].treasury == td0 - 200.0
    assert war not in g.wars
    assert d not in g.houses[a].at_war_with and a not in g.houses[d].at_war_with
    assert g.houses[a].truces[d] == g.turn + TRUCE_TURNS
    assert g.houses[d].truces[a] == g.turn + TRUCE_TURNS
    assert any("truce holds" in m for m in msgs)


def test_a_negative_score_reads_for_the_defender():
    g = _game()
    war = _war(g)
    a, d = war.aggressor, war.defender
    war.war_score = -50.0
    target = min(pid for f in war.fronts for pair in f.border for pid in pair
                 if g.atlas.provinces[pid].owner == a)
    negotiate_peace(g, war, PeaceTerms(provinces=[target]))
    assert g.atlas.provinces[target].owner == d


def test_full_shares_seize_reregisters_the_spoils():
    g = _game()
    war = _war(g)
    a, d = war.aggressor, war.defender
    war.war_score = 60.0
    ent = sorted((e for e in g.enterprises if e.house == d),
                 key=lambda e: e.eid)[0]
    assert g.atlas.provinces[ent.province].owner == d
    msgs = negotiate_peace(g, war, PeaceTerms(provinces=[ent.province],
                                              shares_pct=100.0))
    assert ent.house == a
    assert any("re-register" in m for m in msgs)


def test_partial_shares_flow_to_the_winners_ruler():
    g = _game()
    war = _war(g)
    a, d = war.aggressor, war.defender
    war.war_score = 60.0
    ent = sorted((e for e in g.enterprises if e.house == d),
                 key=lambda e: e.eid)[0]
    negotiate_peace(g, war, PeaceTerms(provinces=[ent.province],
                                       shares_pct=40.0))
    ruler = g.realms[a].ruler
    assert abs(ent.ledger.get(ruler.id, 0.0) - 40.0) < 1e-6
    assert abs(sum(ent.ledger.values()) - 100.0) < 1e-6
    assert ent.house == d                      # the works keep their colors


def test_ai_signs_only_beaten_and_only_a_fair_bill():
    g = _game()
    war = _war(g)
    d = war.defender
    war.war_score = 39.0
    assert not ai_acceptable(g, war, PeaceTerms(), d)
    war.war_score = 40.0
    assert ai_acceptable(g, war, PeaceTerms(), d)
    heavy = PeaceTerms(provinces=[1, 2, 3], gold=500.0)   # cost 55 > 40
    assert not ai_acceptable(g, war, heavy, d)


# --- the war council ---------------------------------------------------------

def test_war_council_convenes_on_a_hot_front():
    g = _game()
    war = _war(g)
    war.fronts[0].line = 0.5
    pets = [p for p in generate_petitions(g, war.aggressor)
            if p.kind == "war_council"]
    assert pets and pets[0].actors["war"] is war
    assert war.defender in pets[0].text
    assert [o.key for o in pets[0].options] == ["reinforce", "hold",
                                                "seek_terms"]


def test_war_council_convenes_on_a_score_swing_then_quiets():
    g = _game()
    war = _war(g)
    war.war_score = 25.0
    first = [p for p in generate_petitions(g, war.aggressor)
             if p.kind == "war_council"]
    assert first
    again = [p for p in generate_petitions(g, war.aggressor)
             if p.kind == "war_council"]
    assert not again                           # the swing has been minuted


def test_reinforce_raises_and_marches_to_the_front():
    g = _game()
    g.rng = ZeroRng()
    war = _war(g)
    front = war.fronts[0]
    front.line = 0.5
    pet = [p for p in generate_petitions(g, war.aggressor)
           if p.kind == "war_council"][0]
    msgs = rule(g, pet, "reinforce", g.realms[war.aggressor].ruler)
    assert front.attacker_regiments == 3
    assert any("fresh regiments march to front" in m for m in msgs)


def test_hold_deepens_the_houses_own_trench():
    g = _game()
    g.rng = ZeroRng()
    war = _war(g)
    front = war.fronts[0]
    front.line = 0.5
    pet = [p for p in generate_petitions(g, war.aggressor)
           if p.kind == "war_council"][0]
    msgs = rule(g, pet, "hold", g.realms[war.aggressor].ruler)
    assert front.entrenchment_a == 1 and front.entrenchment_d == 0
    assert any("lines deepen" in m for m in msgs)


def test_seek_terms_ends_a_lopsided_war():
    g = _game()
    g.rng = ZeroRng()
    war = _war(g)
    war.war_score = 60.0
    pet = [p for p in generate_petitions(g, war.aggressor)
           if p.kind == "war_council"][0]
    msgs = rule(g, pet, "seek_terms", g.realms[war.aggressor].ruler)
    assert war not in g.wars
    assert any("Peace is signed" in m for m in msgs)


def test_seek_terms_refused_while_the_score_is_level():
    g = _game()
    g.rng = ZeroRng()
    war = _war(g)
    war.fronts[0].line = 0.5
    pet = [p for p in generate_petitions(g, war.aggressor)
           if p.kind == "war_council"][0]
    msgs = rule(g, pet, "seek_terms", g.realms[war.aggressor].ruler)
    assert war in g.wars
    assert any("will not yield" in m for m in msgs)


# --- initiatives -------------------------------------------------------------

def test_declare_war_initiative_and_the_binding_truce():
    g = _game()
    g.rng = ZeroRng()
    a, d = _adjacent_pair(g)
    msgs = initiative(g, a, "declare_war", g.realms[a].ruler, target_house=d)
    assert any("declares war" in m for m in msgs)
    assert len(g.wars) == 1 and d in g.houses[a].at_war_with
    g2 = _game()
    g2.rng = ZeroRng()
    a2, d2 = _adjacent_pair(g2)
    g2.houses[a2].truces[d2] = g2.turn + 4
    refused = initiative(g2, a2, "declare_war", g2.realms[a2].ruler,
                         target_house=d2)
    assert any("truce" in m for m in refused)
    assert not g2.wars


def test_negotiate_peace_initiative():
    g = _game()
    g.rng = ZeroRng()
    a, d = _adjacent_pair(g)
    nothing = initiative(g, a, "negotiate_peace", g.realms[a].ruler,
                         target_house=d)
    assert any("no war" in m for m in nothing)
    war = declare_war(g, a, d, WarGoal(kind="humble"))
    war.war_score = 60.0
    msgs = initiative(g, a, "negotiate_peace", g.realms[a].ruler,
                      target_house=d)
    assert war not in g.wars
    assert any("Peace is signed" in m for m in msgs)


# --- the turn ----------------------------------------------------------------

def test_end_turn_grinds_the_fronts_into_the_gazette():
    g = _game()
    war = _war(g)
    a = war.aggressor
    prov = g.provinces_of(a)[0]
    raised = raise_regiments(g, a, prov.pid, 5)
    assert raised > 0
    allocate(war, war.fronts[0], a, raised)
    events = g.end_turn()
    assert any(ev.register == "gazette" and "Front" in ev.text
               for ev in events)
