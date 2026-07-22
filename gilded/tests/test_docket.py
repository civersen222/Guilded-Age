"""Tests for gilded.docket (mission G12)."""

import random

from gilded import docket
from gilded.docket import (
    DOMAIN_PRIORITY,
    MAX_PETITIONS,
    generate_petitions,
    initiative,
    resolve_unattended,
    rule,
)
from gilded.enterprises import EXPAND_COST, found_enterprise
from gilded.houses import assign_houses
from gilded.society.characters import opinion_matrix
from gilded.society.court import CourtPosition
from gilded.society.ideology import IdeologicalTide
from gilded.society.labor import Movement
from gilded.society.marriages import MarriageRegistry
from gilded.society.realm import create_house_realm
from gilded.society.schemes import SchemeManager
from gilded.world import MINOR_OWNER, generate_atlas


class SeqRng:
    """Pops scripted .random() values, then 0.99 forever; other draws fixed."""

    def __init__(self, vals=()):
        self.vals = list(vals)

    def random(self):
        return self.vals.pop(0) if self.vals else 0.99

    def randint(self, a, b):
        return a

    def choice(self, seq):
        return seq[0]

    def shuffle(self, seq):
        pass

    def sample(self, seq, k):
        return list(seq)[:k]


class FakeGame:
    pass


def _game(seed, realm_count=1):
    random.seed(seed)
    g = FakeGame()
    g.rng = random.Random(seed)
    g.atlas = generate_atlas(seed)
    g.houses = assign_houses(g.atlas, seed)
    names = sorted(g.houses)[:realm_count]
    g.realms = {n: create_house_realm(n, g.rng) for n in names}
    g.enterprises = []
    g.wars = []
    g.events = []
    g.turn = 3
    g.marriages = MarriageRegistry()
    g.scheme_mgr = SchemeManager()
    g.legitimacy = {n: 50.0 for n in g.houses}
    g.tide = IdeologicalTide()
    return g, names[0]


def _owned_province(g, house):
    return next(p for p in sorted(g.atlas.provinces.values(), key=lambda p: p.pid)
                if p.owner == house)


def _adult_not_seated(realm):
    seated = {c.id for c in realm.court.positions.values() if c is not None}
    return next(c for c in realm.characters
                if c.is_alive and c.age >= 16 and c.id != realm.ruler.id
                and c.id not in seated)


def test_capital_request_grant_funds_expansion():
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    ent = found_enterprise("bank", h, prov, 1, g.rng)
    ent.under_construction = 0
    director = _adult_not_seated(realm)
    ent.director_id = director.id
    g.enterprises.append(ent)
    pets = generate_petitions(g, h)
    cap = [p for p in pets if p.kind == "capital_request"]
    assert cap and cap[0].domain == "capital"
    g.rng = SeqRng([0.0])                      # clean success
    before = g.houses[h].treasury
    msgs = rule(g, cap[0], "grant", realm.ruler)
    assert g.houses[h].treasury == before - EXPAND_COST[2]
    assert ent.under_construction > 0 and ent.target_tier == 2
    assert any("breaks ground" in m for m in msgs)


def test_seat_vacancy_petition_appoints():
    g, h = _game(43)
    realm = g.realms[h]
    realm.court.positions[CourtPosition.MARSHAL] = None
    pets = generate_petitions(g, h)
    vac = [p for p in pets if p.kind == "seat_vacancy"]
    assert vac and vac[0].domain == "war"
    assert 1 <= len(vac[0].options) <= 3
    g.rng = SeqRng([0.0])
    msgs = rule(g, vac[0], "appoint_1", realm.ruler)
    holder = realm.court.positions[CourtPosition.MARSHAL]
    assert holder is not None and holder.is_alive
    assert any("sworn in as Marshal" in m for m in msgs)


def test_union_ultimatum_buy_off_costs_gold():
    g, h = _game(44)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    leader = _adult_not_seated(realm)
    mv = Movement(prov.pid, leader)
    mv.state = "striking"
    mv.militancy = 60.0
    prov.movement = mv
    pets = generate_petitions(g, h)
    ult = [p for p in pets if p.kind == "union_ultimatum"]
    assert ult and ult[0].domain == "labor"
    g.rng = SeqRng([0.0])
    before = g.houses[h].treasury
    rule(g, ult[0], "buy_off", realm.ruler)
    assert g.houses[h].treasury == before - docket.BUYOFF_COST
    assert mv.leader is None


def test_union_ultimatum_break_martyrs_the_leader():
    g, h = _game(45)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    leader = _adult_not_seated(realm)
    mv = Movement(prov.pid, leader)
    mv.state = "striking"
    prov.movement = mv
    pets = generate_petitions(g, h)
    ult = [p for p in pets if p.kind == "union_ultimatum"]
    assert ult
    g.rng = SeqRng([0.0])
    rule(g, ult[0], "break", realm.ruler)
    assert not leader.is_alive and mv.martyr == leader.name
    assert g.tide.house_atrocities.get(h, 0) > 0


def test_betrothal_offer_accept_weds_the_houses():
    g, h = _game(46, realm_count=2)
    g.rng = SeqRng([0.0])                      # the betrothal roll fires
    pets = generate_petitions(g, h)
    bet = [p for p in pets if p.kind == "betrothal_offer"]
    assert bet and bet[0].domain == "diplomacy"
    g.rng = SeqRng([0.0])
    msgs = rule(g, bet[0], "accept", g.realms[h].ruler)
    assert len(g.marriages.marriages) == 1
    assert msgs


def test_heir_demand_refusal_wounds():
    g, h = _game(47)
    realm = g.realms[h]
    heir = _adult_not_seated(realm)
    realm.dynasty.all_characters[heir.id] = heir
    g.rng = SeqRng([0.0])                      # the heir-demand roll fires
    pets = generate_petitions(g, h)
    hd = [p for p in pets if p.kind == "heir_demand"]
    assert hd and hd[0].domain == "family"
    before = opinion_matrix.get((heir.id, realm.ruler.id), 0)
    g.rng = SeqRng([0.0])
    rule(g, hd[0], "refuse", realm.ruler)
    assert opinion_matrix.get((heir.id, realm.ruler.id), 0) == before - 12


def test_disaster_inquiry_compensation():
    g, h = _game(48)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    prov.unrest = 20.0
    ent = found_enterprise("bank", h, prov, 1, g.rng)
    ent.director_id = _adult_not_seated(realm).id
    g.enterprises.append(ent)
    g.last_accidents = [(ent, prov)]
    pets = generate_petitions(g, h)
    di = [p for p in pets if p.kind == "disaster_inquiry"]
    assert di and di[0].domain == "press"
    g.rng = SeqRng([0.0])
    before = g.houses[h].treasury
    rule(g, di[0], "compensate", realm.ruler)
    assert g.houses[h].treasury == before - docket.COMPENSATE_COST
    assert prov.unrest == 12.0


def test_rail_proposal_fund_lays_track():
    g, h = _game(49)
    realm = g.realms[h]
    pets = generate_petitions(g, h)
    rp = [p for p in pets if p.kind == "rail_proposal"]
    assert rp and rp[0].domain == "expansion"
    link = rp[0].actors["link"]
    assert not link.rail
    g.rng = SeqRng([0.0])
    before = g.houses[h].treasury
    rule(g, rp[0], "fund", realm.ruler)
    assert link.rail
    assert g.houses[h].treasury == before - docket.RAIL_COST


def test_docket_caps_at_six_most_urgent_first():
    g, h = _game(50)
    realm = g.realms[h]
    for seat in CourtPosition:
        realm.court.positions[seat] = None
    prov = _owned_province(g, h)
    mv = Movement(prov.pid, _adult_not_seated(realm))
    mv.state = "striking"
    prov.movement = mv
    pets = generate_petitions(g, h)
    assert len(pets) == MAX_PETITIONS
    priorities = [DOMAIN_PRIORITY[p.domain] for p in pets]
    assert priorities == sorted(priorities)
    assert pets[0].domain == "war"


def test_resolve_unattended_seated_minister_rules():
    g, h = _game(51)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    mv = Movement(prov.pid, _adult_not_seated(realm))
    mv.state = "striking"
    prov.movement = mv
    pets = [p for p in generate_petitions(g, h) if p.kind == "union_ultimatum"]
    assert pets
    g.rng = SeqRng([0.0])
    out = resolve_unattended(g, h, pets)
    assert any("unprompted" in m for m in out)
    assert pets[0].turns_waiting == 0 and not pets[0].escalated


def test_resolve_unattended_family_matters_fester():
    g, h = _game(52)
    realm = g.realms[h]
    heir = _adult_not_seated(realm)
    realm.dynasty.all_characters[heir.id] = heir
    g.rng = SeqRng([0.0])
    pets = [p for p in generate_petitions(g, h) if p.kind == "heir_demand"]
    assert pets
    g.rng = SeqRng([0.0])
    out1 = resolve_unattended(g, h, pets)
    assert out1 == [] and pets[0].turns_waiting == 1 and not pets[0].escalated
    out2 = resolve_unattended(g, h, pets)
    assert pets[0].escalated
    assert any("fester" in m.lower() for m in out2)


def test_initiative_found_enterprise():
    g, h = _game(53)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    g.rng = SeqRng([0.0])
    before = g.houses[h].treasury
    msgs = initiative(g, h, "found_enterprise", realm.ruler,
                      kind="bank", province_pid=prov.pid)
    assert len(g.enterprises) == 1 and g.enterprises[0].kind == "bank"
    assert g.houses[h].treasury == before - 800.0
    assert abs(sum(g.enterprises[0].ledger.values()) - 100.0) < 1e-6
    assert any("chartered" in m for m in msgs)


def test_initiative_acquire_minor_flips_owner():
    g, h = _game(54)
    realm = g.realms[h]
    owned = {p.pid for p in g.atlas.provinces.values() if p.owner == h}
    minor = next(p for p in sorted(g.atlas.provinces.values(), key=lambda p: p.pid)
                 if p.owner == MINOR_OWNER and p.neighbors & owned)
    cost = 300.0 * minor.development + 100.0 * sum(minor.endowments.values())
    g.houses[h].treasury = cost + 50.0
    g.rng = SeqRng([0.0])
    initiative(g, h, "acquire_minor", realm.ruler, province_pid=minor.pid)
    assert minor.owner == h
    assert abs(g.houses[h].treasury - 50.0) < 1e-6


def test_initiative_fumble_halves_the_effect():
    g, h = _game(55)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    prov.unrest = 20.0
    g.rng = SeqRng()                           # 0.99 forever -> fumble
    msgs = initiative(g, h, "tour_province", realm.ruler, province_pid=prov.pid)
    assert any("botches" in m for m in msgs)
    assert prov.unrest == 15.0                 # half of the 10-point relief


def test_initiative_guardrails():
    g, h = _game(56)
    realm = g.realms[h]
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "adjust_garrison", realm.ruler)
    assert any("G16" in m for m in msgs)
    assert initiative(g, h, "nonsense", realm.ruler) == ["No such initiative 'nonsense'"]
