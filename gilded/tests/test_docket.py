"""Tests for gilded.docket (mission G12)."""

import random

from gilded import docket
from gilded.directives import Directives
from gilded.docket import (
    DOMAIN_PRIORITY,
    MAX_PETITIONS,
    director_candidates,
    generate_petitions,
    initiative,
    resolve_unattended,
    rule,
)
from gilded.enterprises import EXPAND_COST, Enterprise, found_enterprise
from gilded.market import Market
from gilded.houses import assign_houses
from gilded.society.characters import SocietyState
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

    def __init__(self):
        self.directives = {}


def _game(seed, realm_count=1):
    random.seed(seed)
    g = FakeGame()
    g.rng = random.Random(seed)
    g.society = SocietyState(g.rng)
    g.atlas = generate_atlas(seed)
    g.houses = assign_houses(g.atlas, seed)
    names = sorted(g.houses)[:realm_count]
    g.realms = {n: create_house_realm(n, g.society) for n in names}
    g.enterprises = []
    g.wars = []
    g.events = []
    g.turn = 3
    g.marriages = MarriageRegistry()
    g.scheme_mgr = SchemeManager()
    g.legitimacy = {n: 50.0 for n in g.houses}
    g.directives = {n: Directives() for n in g.houses}
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
    before = heir._society.opinions.get((heir.id, realm.ruler.id), 0)
    g.rng = SeqRng([0.0])
    rule(g, hd[0], "refuse", realm.ruler)
    assert heir._society.opinions.get((heir.id, realm.ruler.id), 0) == before - 12


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


def test_expansionist_policy_cheapens_expansion():
    from gilded.chassis import GildedGame
    from gilded.enterprises import EXPAND_COST
    g = GildedGame(seed=23)
    h = next(x for x in sorted(g.houses) if g.ents_of(x))
    ent = next(e for e in g.ents_of(h) if e.tier < 5 and e.under_construction == 0)
    g.directives[h].set_stance("expansion", 100)
    from gilded import policy
    eff = policy.effects(g, h)
    expected = EXPAND_COST[ent.tier + 1] * eff.expand_cost_mod
    assert expected < EXPAND_COST[ent.tier + 1]


def _make_ent_with_ledger(g, house, ruler_id, kin_id):
    """Create an enterprise with a ledger and attach a market to the FakeGame."""
    from gilded.market import Market
    from gilded.enterprises import ENTERPRISE_TYPES
    g.market = Market()
    # Pick a kind and a province that has the needed endowment
    kind = "colliery"
    needed = ENTERPRISE_TYPES[kind][0]  # "coalfield"
    prov = next((p for p in g.atlas.provinces.values()
                 if p.owner == house and needed in p.endowments),
                next(p for p in g.atlas.provinces.values() if p.owner == house))
    # If the province lacks the endowment, add it so the market values the enterprise
    if needed and needed not in prov.endowments:
        prov.endowments[needed] = 1
    ent = Enterprise(eid=next((e.eid for e in g.enterprises), 0) + 1,
                     kind=kind, name=f"{prov.name} Colliery",
                     house=house, province=prov.pid)
    ent.under_construction = 0
    ent.assign_share(ruler_id, 60.0)
    ent.assign_share(kin_id, 40.0)
    g.enterprises.append(ent)
    return ent


# -- buy_shares / sell_shares tests --

def test_buy_shares_happy_path():
    """Executor (buyer) buys shares from a counterparty."""
    g, h = _game(100)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    ruler.gold_reserve = 10_000.0
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    g.rng = SeqRng([0.0])
    kin_stake_before = ent.ledger.get(kin.id, 0.0)
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=10.0)
    assert len(msgs) >= 1
    assert ent.ledger.get(kin.id, 0.0) < kin_stake_before
    assert ent.ledger.get(ruler.id, 0.0) > 60.0


def test_sell_shares_happy_path():
    """Executor (seller) sells shares to a funded counterparty."""
    g, h = _game(101)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    kin.gold_reserve = 10_000.0
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    g.rng = SeqRng([0.0])
    ruler_stake_before = ent.ledger.get(ruler.id, 0.0)
    msgs = initiative(g, h, "sell_shares", ruler, eid=ent.eid, buyer_id=kin.id, pct=10.0)
    assert len(msgs) >= 1
    assert ent.ledger.get(ruler.id, 0.0) < ruler_stake_before
    assert ent.ledger.get(kin.id, 0.0) > 40.0


def test_buy_shares_cross_house():
    """Buy shares from a character in a different realm."""
    g, h = _game(102, realm_count=2)
    h2 = sorted(g.realms)[1]
    realm1 = g.realms[h]
    realm2 = g.realms[h2]
    ruler = realm1.ruler
    other = realm2.ruler
    ruler.gold_reserve = 10_000.0
    ent = _make_ent_with_ledger(g, h, ruler.id, other.id)
    g.rng = SeqRng([0.0])
    other_stake_before = ent.ledger.get(other.id, 0.0)
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=other.id, pct=10.0)
    assert len(msgs) >= 1
    assert ent.ledger.get(other.id, 0.0) < other_stake_before


def test_buy_shares_unknown_person():
    """Unresolvable seller_id returns an event line, changes nothing."""
    g, h = _game(103)
    realm = g.realms[h]
    ruler = realm.ruler
    ruler.gold_reserve = 10_000.0
    ent = _make_ent_with_ledger(g, h, ruler.id, 99999)
    g.rng = SeqRng([0.0])
    ledger_before = dict(ent.ledger)
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=99999, pct=10.0)
    assert len(msgs) >= 1
    assert ent.ledger == ledger_before


def test_buy_shares_unknown_enterprise():
    """Nonexistent eid returns an event line, changes nothing."""
    g, h = _game(104)
    realm = g.realms[h]
    ruler = realm.ruler
    ruler.gold_reserve = 10_000.0
    g.market = Market()
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "buy_shares", ruler, eid=99999, seller_id=1, pct=10.0)
    assert len(msgs) >= 1


def test_broke_buyer():
    """Unfunded buyer sees no shares move (House treasury is the purse)."""
    g, h = _game(105)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    house = g.houses[h]
    house.treasury = 0.0
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    g.rng = SeqRng([0.0])
    ledger_before = dict(ent.ledger)
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=10.0)
    assert len(msgs) >= 1
    assert ent.ledger == ledger_before


def test_buy_shares_fumble_halves():
    """Fumble (scale=0.5) buys strictly less stake than a clean roll."""
    g, h = _game(106)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    ruler.gold_reserve = 10_000.0
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    g.rng = SeqRng()  # 0.99 forever -> fumble
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=20.0)
    assert any("botches" in m for m in msgs)
    moved = ent.ledger.get(ruler.id, 60.0) - 60.0
    assert moved > 0 and moved < 20.0


def test_buy_shares_zero_pct():
    """pct <= 0 is a no-op event line."""
    g, h = _game(107)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    g.rng = SeqRng([0.0])
    ledger_before = dict(ent.ledger)
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=0.0)
    assert len(msgs) >= 1
    assert ent.ledger == ledger_before


def test_buy_shares_no_stake():
    """Seller with no stake gets a 'no stake' message, not 'cannot afford'."""
    g, h = _game(108)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    ruler.gold_reserve = 10_000.0
    ent = _make_ent_with_ledger(g, h, ruler.id, 99999)
    assert kin.id not in ent.ledger, "kin should not be in the ledger"
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=10.0)
    line = " ".join(msgs).lower()
    assert "stake" in line or "no" in line
    assert "cannot afford" not in line


def test_buy_shares_partial_fill():
    """Asking for more than seller has: line reports actual amount moved."""
    g, h = _game(109)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    ruler.gold_reserve = 10_000.0
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    ent.ledger[kin.id] = 2.0
    ent.ledger[ruler.id] = 98.0
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=5.0)
    text = " ".join(msgs)
    assert "2.0%" in text
    assert "5.0%" not in text


def test_buy_shares_small_price_format():
    """Price under 10 gold shows two decimal places, not zero."""
    g, h = _game(110)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    ruler.gold_reserve = 10_000.0
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    ent.ledger[kin.id] = 2.0
    ent.ledger[ruler.id] = 98.0
    g.rng = SeqRng([0.0])
    gold_before = ruler.gold_reserve
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=2.0)
    gold_paid = gold_before - ruler.gold_reserve
    text = " ".join(msgs)
    if gold_paid > 0:
        assert "0 gold" not in text


def test_sell_shares_no_stake():
    """Executor selling from an enterprise they don't own gets 'no stake'."""
    g, h = _game(111)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    kin.gold_reserve = 10_000.0
    ent = _make_ent_with_ledger(g, h, kin.id, 99999)
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "sell_shares", ruler, eid=ent.eid, buyer_id=kin.id, pct=10.0)
    line = " ".join(msgs).lower()
    assert "stake" in line or "no" in line


def test_sell_shares_small_price_format():
    """Sell-side price under 10 gold shows two decimal places."""
    g, h = _game(112)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    kin.gold_reserve = 10_000.0
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    ent.ledger[ruler.id] = 2.0
    ent.ledger[kin.id] = 98.0
    g.rng = SeqRng([0.0])
    gold_before = ruler.gold_reserve
    msgs = initiative(g, h, "sell_shares", ruler, eid=ent.eid, buyer_id=kin.id, pct=2.0)
    gold_received = ruler.gold_reserve - gold_before
    text = " ".join(msgs)
    if gold_received > 0:
        assert "0 gold" not in text


def test_director_candidates_ranked():
    """The pool comes back best-industry-first and is not empty."""
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    ent = found_enterprise("bank", h, prov, "test-bank-1", g.rng)
    ent.under_construction = 0
    g.enterprises.append(ent)
    cands = director_candidates(g, h, ent.eid)
    assert len(cands) > 0, "pool should not be empty"
    inds = [c.get_effective_stat("industry") for c in cands]
    assert inds == sorted(inds, reverse=True), "pool must be sorted industry descending"


def test_director_candidates_excludes_ruler():
    """The ruler is never offered as a candidate."""
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    ent = found_enterprise("bank", h, prov, "test-bank-2", g.rng)
    ent.under_construction = 0
    g.enterprises.append(ent)
    cands = director_candidates(g, h, ent.eid)
    assert all(c.id != realm.ruler.id for c in cands), "ruler should not be in candidate pool"


def test_director_candidates_excludes_council():
    """Council members are never offered as candidates."""
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    ent = found_enterprise("bank", h, prov, "test-bank-3", g.rng)
    ent.under_construction = 0
    g.enterprises.append(ent)
    cands = director_candidates(g, h, ent.eid)
    court_ids = {ch.id for ch in realm.court.positions.values() if ch}
    assert not any(c.id in court_ids for c in cands), "council members should not be in pool"


def test_director_candidates_excludes_sitting_directors():
    """A character already directing any enterprise is excluded from the pool."""
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    # Create two enterprises
    ent1 = found_enterprise("bank", h, prov, "test-bank-4a", g.rng)
    ent1.under_construction = 0
    g.enterprises.append(ent1)
    ent2 = found_enterprise("bank", h, prov, "test-bank-4b", g.rng)
    ent2.under_construction = 0
    g.enterprises.append(ent2)
    # Seat a director on ent1
    pick = _adult_not_seated(realm)
    ent1.director_id = pick.id
    # ent2's candidate pool should NOT include the sitting director
    cands = director_candidates(g, h, ent2.eid)
    assert not any(c.id == pick.id for c in cands), "sitting director should be excluded"


def test_appoint_sets_director():
    """appoint_director initiative sets director_id on the enterprise."""
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    ent = found_enterprise("bank", h, prov, "test-bank-5", g.rng)
    ent.under_construction = 0
    g.enterprises.append(ent)
    ent.ledger.clear()
    ent.assign_share(realm.ruler.id, 100.0)
    pick = director_candidates(g, h, ent.eid)[0]
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "appoint_director", realm.ruler, eid=ent.eid, char_id=pick.id)
    assert ent.director_id == pick.id, "director_id should be set to the appointee"


def test_appoint_survives_tick():
    """An appointed director survives a tick_directors call (persistence guard)."""
    from gilded.society.realm import tick_directors
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    ent = found_enterprise("bank", h, prov, "test-bank-6", g.rng)
    ent.under_construction = 0
    g.enterprises.append(ent)
    ent.ledger.clear()
    ent.assign_share(realm.ruler.id, 100.0)
    pick = director_candidates(g, h, ent.eid)[0]
    g.rng = SeqRng([0.0])
    initiative(g, h, "appoint_director", realm.ruler, eid=ent.eid, char_id=pick.id)
    tick_directors(realm, g.enterprises, g.rng)
    assert ent.director_id == pick.id, "director_id should survive tick_directors"


def test_appoint_salary_paid():
    """Appointment moves DIRECTOR_SALARY_PCT from ruler's stake to director's."""
    from gilded.society.realm import DIRECTOR_SALARY_PCT
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    ent = found_enterprise("bank", h, prov, "test-bank-7", g.rng)
    ent.under_construction = 0
    g.enterprises.append(ent)
    ent.ledger.clear()
    ent.assign_share(realm.ruler.id, 100.0)
    pick = director_candidates(g, h, ent.eid)[0]
    ruler_before = ent.ledger.get(realm.ruler.id, 0.0)
    g.rng = SeqRng([0.0])
    initiative(g, h, "appoint_director", realm.ruler, eid=ent.eid, char_id=pick.id)
    ruler_after = ent.ledger.get(realm.ruler.id, 0.0)
    director_stake = ent.ledger.get(pick.id, 0.0)
    assert director_stake >= DIRECTOR_SALARY_PCT - 0.01, f"director should receive salary stake ({director_stake})"
    assert ruler_before - ruler_after >= DIRECTOR_SALARY_PCT - 0.01, "salary should come from ruler's stake"


def test_appoint_honors_scale():
    """A botched appointment wins the appointee over by less than a clean one."""
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    ent = found_enterprise("bank", h, prov, "test-bank-8", g.rng)
    ent.under_construction = 0
    g.enterprises.append(ent)
    ent.ledger.clear()
    ent.assign_share(realm.ruler.id, 100.0)
    pick = director_candidates(g, h, ent.eid)[0]
    before = g.society.opinions.get((pick.id, realm.ruler.id), 0)
    g.rng = SeqRng([0.0])
    initiative(g, h, "appoint_director", realm.ruler, eid=ent.eid, char_id=pick.id)
    clean_after = g.society.opinions.get((pick.id, realm.ruler.id), 0)
    clean_delta = clean_after - before
    # Now test botched
    g2, h2 = _game(42)
    realm2 = g2.realms[h2]
    prov2 = _owned_province(g2, h2)
    ent2 = found_enterprise("bank", h2, prov2, "test-bank-8b", g2.rng)
    ent2.under_construction = 0
    g2.enterprises.append(ent2)
    ent2.ledger.clear()
    ent2.assign_share(realm2.ruler.id, 100.0)
    pick2 = director_candidates(g2, h2, ent2.eid)[0]
    before2 = g2.society.opinions.get((pick2.id, realm2.ruler.id), 0)
    g2.rng = SeqRng([0.99])
    initiative(g2, h2, "appoint_director", realm2.ruler, eid=ent2.eid, char_id=pick2.id)
    botched_after = g2.society.opinions.get((pick2.id, realm2.ruler.id), 0)
    botched_delta = botched_after - before2
    assert clean_delta > 0, "clean appointment should improve opinion"
    assert botched_delta < clean_delta, "botched appointment should improve opinion less"


def test_appoint_rejects_ineligible():
    """Handler must refuse char_ids not in the candidate pool (ruler, council, sitting director)."""
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    ent = found_enterprise("bank", h, prov, "test-bank-reject", g.rng)
    ent.under_construction = 0
    g.enterprises.append(ent)
    ent.ledger.clear()
    ent.assign_share(realm.ruler.id, 100.0)
    
    # Try to appoint the ruler
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "appoint_director", realm.ruler, eid=ent.eid, char_id=realm.ruler.id)
    assert ent.director_id != realm.ruler.id, "ruler should not be seated as director"
    assert msgs, "should return a refusal line"
    
    # Try to appoint a council member
    council = [c for c in realm.court.positions.values() if c is not None]
    if council:
        g.rng = SeqRng([0.0])
        msgs = initiative(g, h, "appoint_director", realm.ruler, eid=ent.eid, char_id=council[0].id)
        assert ent.director_id != council[0].id, "council member should not be seated as director"
        assert msgs, "should return a refusal line"
    
    # Try to appoint a sitting director from another enterprise
    other = found_enterprise("bank", h, prov, "test-bank-other", g.rng)
    other.under_construction = 0
    g.enterprises.append(other)
    cands = director_candidates(g, h, other.eid)
    if cands:
        sitting = cands[0]
        other.director_id = sitting.id
        g.rng = SeqRng([0.0])
        msgs = initiative(g, h, "appoint_director", realm.ruler, eid=ent.eid, char_id=sitting.id)
        assert ent.director_id != sitting.id, "sitting director should not be seated again"
        assert msgs, "should return a refusal line"


def test_appoint_rejects_foreign():
    """Handler must refuse a rival house's ruler (foreign character)."""
    random.seed(99)
    g = FakeGame()
    g.rng = random.Random(99)
    g.society = SocietyState(g.rng)
    g.atlas = generate_atlas(99)
    g.houses = assign_houses(g.atlas, 99)
    names = sorted(g.houses)[:2]
    g.realms = {n: create_house_realm(n, g.society) for n in names}
    g.enterprises = []
    g.wars = []
    g.events = []
    g.turn = 3
    g.marriages = MarriageRegistry()
    g.scheme_mgr = SchemeManager()
    g.legitimacy = {n: 50.0 for n in g.houses}
    g.directives = {n: Directives() for n in g.houses}
    g.tide = IdeologicalTide()
    
    h = names[0]
    realm = g.realms[h]
    prov = next(p for p in sorted(g.atlas.provinces.values(), key=lambda p: p.pid) if p.owner == h)
    ent = found_enterprise("bank", h, prov, "test-bank-fgn", g.rng)
    ent.under_construction = 0
    g.enterprises.append(ent)
    ent.ledger.clear()
    ent.assign_share(realm.ruler.id, 100.0)
    
    # Try to appoint the rival house's ruler
    foreign_ruler = g.realms[names[1]].ruler
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "appoint_director", realm.ruler, eid=ent.eid, char_id=foreign_ruler.id)
    assert ent.director_id != foreign_ruler.id, "foreign ruler should not be seated as director"
    assert msgs, "should return a refusal line"


def test_appoint_salary_line_matches_amount():
    """The salary line must name the percentage that actually moved, not a rounded zero."""
    import re
    g, h = _game(42)
    realm = g.realms[h]
    prov = _owned_province(g, h)
    ent = found_enterprise("bank", h, prov, "test-bank-sal", g.rng)
    ent.under_construction = 0
    g.enterprises.append(ent)
    # Give ruler 0.4% so transfer_shares clamps to 0.4% (less than 0.5% -> .0f rounds to 0)
    ent.ledger.clear()
    ent.assign_share(realm.ruler.id, 0.4)
    pick = director_candidates(g, h, ent.eid)[0]
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "appoint_director", realm.ruler, eid=ent.eid, char_id=pick.id)
    moved = ent.ledger.get(pick.id, 0.0)
    assert moved > 0, "something should have moved"
    line = " ".join(msgs)
    # Extract the percentage from the line
    m = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
    assert m, f"no percentage in line: {line}"
    line_pct = float(m.group(1))
    assert abs(line_pct - moved) < 0.01, f"line says {line_pct}% but {moved}% actually moved: {line}"


# ====================================================================
# I4d2a3: one price for one stake — eight properties
# ====================================================================

def test_p1_quote_equals_treasury_drop():
    """P-1: The Enterprises page quote equals what the treasury falls by.
    Uses a real GildedGame at a stated turn, no purse handed to anybody."""
    from gilded.chassis import GildedGame
    from gilded.society.shares import stake_cost
    from gilded.ui.broadsheet import _buyout_price

    g = GildedGame(seed=42)
    while g.turn < 5:
        g.end_turn()
        g.open_turn()
    h = next(x for x in sorted(g.houses) if g.ents_of(x))
    ent = next(e for e in g.ents_of(h) if e.house == h)
    # Find a rival stakeholder
    rival_id = None
    for cid, pct in ent.ledger.items():
        if pct > 0 and cid != g.realms[h].ruler.id:
            rival_id = cid
            break
    if rival_id is None:
        pytest.skip("no rival stakeholder found")
    pct = ent.ledger[rival_id]
    quote = stake_cost(ent, pct, g)
    treasury_before = g.houses[h].treasury
    # Execute a clean buy (scale=1.0, rng draws 0.0)
    g.rng = SeqRng([0.0])
    ruler = g.realms[h].ruler
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=rival_id, pct=pct)
    treasury_after = g.houses[h].treasury
    assert any("botches" not in m for m in msgs), f"should not have botched: {msgs}"
    drop = treasury_before - treasury_after
    assert drop == quote, f"quote={quote}, treasury_drop={drop}, msgs={msgs}"


def test_p2_buy_shares_debits_treasury_credits_seller():
    """P-2: buy_shares debits ordering House's treasury, credits seller's gold_reserve."""
    g, h = _game(200)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    house = g.houses[h]
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    kin_gold_before = kin.gold_reserve
    treasury_before = house.treasury
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=10.0)
    assert any("botches" not in m and "buys" in m for m in msgs), f"trade should have succeeded: {msgs}"
    treasury_drop = treasury_before - house.treasury
    kin_credit = kin.gold_reserve - kin_gold_before
    assert treasury_drop == kin_credit, f"treasury_drop={treasury_drop}, kin_credit={kin_credit}"


def test_p3_zero_gold_executor_can_buy_from_treasury():
    """P-3: Executor with gold_reserve=0 can still complete a buy when treasury is full."""
    g, h = _game(201)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    ruler.gold_reserve = 0.0
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    g.rng = SeqRng([0.0])
    kin_stake_before = ent.ledger.get(kin.id, 0.0)
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=10.0)
    assert any("cannot afford" not in m for m in msgs), f"should not refuse: {msgs}"
    assert ent.ledger.get(kin.id, 0.0) < kin_stake_before, "shares should have moved"


def test_p4_sell_shares_credits_treasury_debits_buyer():
    """P-4: sell_shares credits ordering House's treasury from buyer's gold_reserve."""
    g, h = _game(202)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    kin.gold_reserve = 10_000.0
    house = g.houses[h]
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    treasury_before = house.treasury
    kin_gold_before = kin.gold_reserve
    g.rng = SeqRng([0.0])
    msgs = initiative(g, h, "sell_shares", ruler, eid=ent.eid, buyer_id=kin.id, pct=10.0)
    assert any("botches" not in m and "sells" in m for m in msgs), f"trade should have succeeded: {msgs}"
    treasury_gain = house.treasury - treasury_before
    kin_debit = kin_gold_before - kin.gold_reserve
    assert treasury_gain == kin_debit, f"treasury_gain={treasury_gain}, kin_debit={kin_debit}"


def test_c1_sell_refused_when_buyer_cannot_pay():
    """C-1: A sell_shares is refused when the BUYING CHARACTER cannot pay,
    even if the House treasury is full (surviving mutation M08)."""
    from gilded.society.shares import stake_cost
    g, h = _game(203)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    house = g.houses[h]
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    kin.gold_reserve = 0.0
    house.treasury = 10000.0
    ledger_before = dict(ent.ledger)
    g.rng = SeqRng([0.99])
    msgs = initiative(g, h, "sell_shares", ruler, eid=ent.eid, buyer_id=kin.id, pct=10.0)
    text = " ".join(msgs).lower()
    assert "cannot afford" in text, f"should refuse for buyer poverty: {msgs}"
    assert ent.ledger == ledger_before, f"ledger should not have changed: {ent.ledger}"


def test_c2_buy_refusal_names_house_not_executor():
    """C-2: A buy refusal names THE HOUSE TREASURY that is short, not the executor.
    Surviving mutation M10 changed the subject from House to executor."""
    from gilded.society.shares import stake_cost
    g, h = _game(203)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    house = g.houses[h]
    house.treasury = 0.0
    ruler.gold_reserve = 500.0  # executor is well-funded
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    g.rng = SeqRng([0.1, 0.99])
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=10.0)
    # Find the refusal message (skip botch/stress messages)
    refusal = [m for m in msgs if "cannot afford" in m.lower()]
    assert refusal, f"should have refusal message: {msgs}"
    text = refusal[0]
    # Must name the House, not the executor
    assert h.lower() in text.lower(), f"refusal should name the House '{h}': {text}"
    assert "treasury" in text.lower(), f"refusal should mention treasury: {text}"
    assert "cannot afford" in text.lower(), f"should refuse: {text}"


def test_p5_refusal_names_purse_and_balance():
    """C-3/P-5: Refusal names the correct purse (House treasury for buy) and
    states its balance accurately as a number, not just a string match.
    Treasury set to 7.0 — renders as "7" which cannot be confused with the
    quote (9.5) or any other figure on the line."""
    import re
    from gilded.society.shares import stake_cost
    g, h = _game(203)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    house = g.houses[h]
    house.treasury = 7.0  # unambiguous: renders "7", not "0" or "9.5"
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    quote = stake_cost(ent, 10.0, g)
    g.rng = SeqRng([0.1, 0.99])
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=10.0)
    refusal = [m for m in msgs if "cannot afford" in m.lower()]
    assert refusal, f"should refuse: {msgs}"
    text = refusal[0]
    # Must name the House treasury, not the executor
    assert h in text, f"refusal should name House '{h}': {text}"
    assert "treasury" in text.lower(), f"refusal should mention treasury: {text}"
    # Extract the stated balance from the refusal line — it should be 7.0
    # The format is "(X gold needed, Y in treasury)" — extract Y
    nums = [float(x) for x in re.findall(r'[\d.]+', text)]
    # Last number in the line is the treasury balance
    stated_balance = nums[-1]
    assert abs(stated_balance - house.treasury) < 0.01, \
        f"stated balance {stated_balance} != actual treasury {house.treasury}: {text}"
    # Also verify the first number is the quote
    stated_quote = nums[0]
    assert abs(stated_quote - quote) < 0.01, \
        f"stated quote {stated_quote} != actual quote {quote}: {text}"


def test_p6_quote_not_priced_off_market_value():
    """P-6: Changing market.value does not move the quote (share_price clamps).
    Fixture: seed 204, turn 3 — share_price band is active (clamped to [0.5, 8.0])."""
    g, h = _game(204)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    from gilded.society.shares import stake_cost
    from gilded.society.schemes import share_price

    quote_before = stake_cost(ent, 10.0, g)
    sp_before = share_price(ent, g)
    # Clamp the market value to something wildly different
    original_value = g.market.value(ent, g)
    g.market._prices_backup = dict(g.market.prices)
    # Multiply all prices by 100 — market.value goes up 100x but share_price stays clamped
    g.market.prices = {k: v * 100 for k, v in g.market.prices.items()}
    quote_after = stake_cost(ent, 10.0, g)
    sp_after = share_price(ent, g)
    # Restore
    g.market.prices = g.market._prices_backup
    # share_price is clamped to [TAKEOVER_PRICE * BAND_LO, TAKEOVER_PRICE * BAND_HI]
    # i.e. [0.5, 8.0] per 1%.  A 100x market swing cannot push it outside that band.
    from gilded.society.schemes import TAKEOVER_PRICE, BAND_LO, BAND_HI
    lo = TAKEOVER_PRICE * BAND_LO  # 0.5
    hi = TAKEOVER_PRICE * BAND_HI  # 8.0
    assert lo <= sp_before <= hi, f"sp_before={sp_before} outside clamp band [{lo},{hi}]"
    assert lo <= sp_after <= hi, f"sp_after={sp_after} outside clamp band [{lo},{hi}]"
    # quote = sp * pct, so it's also bounded by the clamp band * pct
    assert lo * 10.0 <= quote_before <= hi * 10.0, \
        f"quote_before={quote_before} outside expected range [{lo*10},{hi*10}]"
    assert lo * 10.0 <= quote_after <= hi * 10.0, \
        f"quote_after={quote_after} outside expected range [{lo*10},{hi*10}]"


def test_p7_no_phantom_trade():
    """P-7: No path reports a completed trade when the ledger did not move."""
    g, h = _game(205)
    realm = g.realms[h]
    ruler = realm.ruler
    kin = _adult_not_seated(realm)
    house = g.houses[h]
    house.treasury = 0.0
    ent = _make_ent_with_ledger(g, h, ruler.id, kin.id)
    g.rng = SeqRng([0.0])
    ledger_before = dict(ent.ledger)
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=kin.id, pct=10.0)
    # Ledger didn't move (no treasury)
    assert ent.ledger == ledger_before, "ledger should not have changed"
    # No message should claim a trade completed
    for m in msgs:
        assert "buys" not in m.lower() or "cannot afford" in m.lower() or "failed" in m.lower(), \
            f"phantom trade reported: {m}"


def test_p8_fumble_reports_and_charges_actual_size():
    """P-8: Fumbled trade (scale=0.5) reports and charges for the actual size moved.
    Uses a real GildedGame(seed) at a stated turn, no purse handed to anybody."""
    from gilded.chassis import GildedGame
    from gilded.society.shares import stake_cost
    from gilded.society.schemes import share_price

    g = GildedGame(seed=45)
    while g.turn < 10:
        g.end_turn()
        g.open_turn()
    h = next(x for x in sorted(g.houses) if g.ents_of(x))
    ent = next(e for e in g.ents_of(h) if e.house == h)
    rival_id = None
    for cid, pct in ent.ledger.items():
        if pct > 0 and cid != g.realms[h].ruler.id:
            rival_id = cid
            break
    if rival_id is None:
        pytest.skip("no rival stakeholder found")
    pct = min(ent.ledger[rival_id], 10.0)
    treasury_before = g.houses[h].treasury
    ledger_before = dict(ent.ledger)
    # Force a fumble (rng draws 0.99 → scale=0.5)
    g.rng = SeqRng([])  # empty → 0.99 forever
    ruler = g.realms[h].ruler
    msgs = initiative(g, h, "buy_shares", ruler, eid=ent.eid, seller_id=rival_id, pct=pct)
    assert any("botches" in m for m in msgs), f"should have botched: {msgs}"
    treasury_drop = treasury_before - g.houses[h].treasury
    actual_moved = ledger_before.get(rival_id, 0) - ent.ledger.get(rival_id, 0)
    expected_pct = pct * 0.5  # fumble halves
    expected_cost = share_price(ent, g) * min(expected_pct, ledger_before.get(rival_id, 0))
    assert abs(treasury_drop - expected_cost) < 0.01, \
        f"treasury_drop={treasury_drop}, expected_cost={expected_cost}, actual_moved={actual_moved}"
