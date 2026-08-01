
"""Tests for gilded.society.schemes (mission G9)."""

import random

from gilded.enterprises import Enterprise
from gilded.chassis import GildedGame
from gilded.society.characters import Secret, SocietyState
from gilded.society.ideology import IdeologicalTide
from gilded.society.realm import create_house_realm
from gilded.society.schemes import (
    Conspiracy,
    SchemeManager,
    Takeover,
    share_price,
    blackmail,
    compromise,
    expose_secret,
    sabotage,
    seduce,
    start_conspiracy,
    sway,
)


class SeqRng:
    """Deterministic roll source: pops scripted values, then 0.99 forever."""

    def __init__(self, vals):
        self.vals = list(vals)

    def random(self):
        return self.vals.pop(0) if self.vals else 0.99


def _two_realms(seed):
    random.seed(seed)
    rng = random.Random(seed)
    society = SocietyState(rng)
    ra = create_house_realm("Vantrell", society)
    rb = create_house_realm("Karsgate", society)
    return ra, rb, {"Vantrell": ra, "Karsgate": rb}


def test_scheme_mechanics():
    ra, rb, realms = _two_realms(90)
    mgr = SchemeManager()
    agent = ra.characters[10]
    s = mgr.start_scheme(agent, rb.ruler, "assassination", "Karsgate")
    assert mgr.scheming(agent) and not mgr.scheming(rb.ruler)
    before = s.progress
    s.advance()
    assert s.progress == before + 3 + agent.get_effective_stat("intrigue") // 2
    s.add_participant(ra.characters[11])
    s.add_participant(ra.characters[11])            # dedupe
    s.add_participant(agent)                        # never the agent
    assert len(s.participants) == 1
    assert 0.0 <= s.success_chance(50) <= 0.9


def test_advance_all_prunes_moot_schemes():
    ra, rb, realms = _two_realms(91)
    mgr = SchemeManager()
    dead_agent = ra.characters[10]
    mgr.start_scheme(dead_agent, rb.ruler, "assassination", "Karsgate")
    dead_agent.is_alive = False
    not_ruler = rb.characters[12]
    mgr.start_scheme(ra.characters[11], not_ruler, "coup", "Karsgate")
    mgr.advance_all(realms, {}, SeqRng([0.99, 0.99]))
    assert mgr.schemes == []


def test_assassination_success_marks_succession():
    ra, rb, realms = _two_realms(92)
    mgr = SchemeManager()
    s = mgr.start_scheme(ra.characters[10], rb.ruler, "assassination", "Karsgate")
    s.progress = 99
    msgs = mgr.advance_all(realms, {}, SeqRng([0.99, 0.0]))
    assert not rb.ruler.is_alive
    assert ("ruler_dead", "Karsgate") in mgr.pending_successions
    assert msgs and mgr.schemes == []


def test_coup_success_seats_the_agent():
    ra, rb, realms = _two_realms(93)
    mgr = SchemeManager()
    old_ruler = rb.ruler
    agent = next(ch for ch in rb.court.positions.values() if ch is not None)
    s = mgr.start_scheme(agent, old_ruler, "coup", "Karsgate")
    s.progress = 99
    mgr.advance_all(realms, {}, SeqRng([0.99, 0.0]))
    assert rb.ruler is agent and rb.court.ruler is agent
    assert agent not in rb.court.positions.values()
    assert agent.id in rb.dynasty.all_characters
    assert mgr.pending_successions == []            # coup is its own succession


def test_discovery_shames_the_house():
    ra, rb, realms = _two_realms(94)
    mgr = SchemeManager()
    agent = ra.characters[10]
    mgr.start_scheme(agent, rb.ruler, "assassination", "Karsgate")
    legit = {"Vantrell": 50.0}
    msgs = mgr.advance_all(realms, legit, SeqRng([0.0]))
    assert legit["Vantrell"] < 50.0
    assert any(sec.kind == "scheme" for sec in agent.secrets)
    assert rb.ruler._society.opinions[(rb.ruler.id, agent.id)] <= -40
    assert agent.is_alive                           # cross-house: no execution
    assert msgs


def test_expose_secret_spends_the_leverage():
    ra, rb, realms = _two_realms(95)
    publisher, subject = ra.ruler, rb.ruler
    secret = Secret("affair", subject.id, f"{subject.name} hides an affair", 30)
    secret.holders.add(publisher.id)
    subject.secrets.append(secret)
    legit = {"Karsgate": 60.0}
    msgs = expose_secret(publisher, secret, subject, "Karsgate", legit)
    assert msgs and msgs[0].startswith("EXPOSED")
    assert legit["Karsgate"] < 60.0
    assert secret not in subject.secrets
    stranger = ra.characters[10]
    assert expose_secret(stranger, secret, subject, "Karsgate", legit) == []


def test_blackmail_extorts_shares():
    ra, rb, realms = _two_realms(96)
    agent, victim = ra.ruler, rb.ruler
    secret = Secret("compromise", victim.id, f"{victim.name} was compromised", 20)
    secret.holders.add(agent.id)
    ent = Enterprise(eid=1, kind="bank", name="K Bank", house="Karsgate", province=0)
    ent.ledger = {victim.id: 40.0}
    msgs = blackmail(agent, secret, victim, rb, [ent], SeqRng([0.99]))
    assert ent.ledger[agent.id] == 10.0
    assert ent.ledger[victim.id] == 30.0
    assert any("turns the screw" in m for m in msgs)
    bluff = blackmail(agent, secret, victim, rb, [ent], SeqRng([0.0]))
    assert any("calls the bluff" in m for m in bluff)


def test_sabotage_hits_the_rival_works():
    ra, rb, realms = _two_realms(97)

    class Province:
        name = "Karsholm"
        population = 50
        unrest = 0.0

    ent = Enterprise(eid=1, kind="mill", name="K Mill", house="Karsgate", province=0)
    tide = IdeologicalTide()
    msgs = sabotage(ra.ruler, ent, Province(), rb, SeqRng([0.0]), tide)
    assert any("mysterious accident" in m for m in msgs)
    assert tide.house_atrocities.get("Karsgate", 0.0) > 0
    assert any(sec.kind == "sabotage" for sec in ra.ruler.secrets)


def test_leverage_verbs():
    ra, rb, realms = _two_realms(98)
    a, t = ra.ruler, rb.ruler
    sway(a, t, SeqRng([0.0]))
    assert a._society.opinions[(t.id, a.id)] >= 15
    seduce(a, t, SeqRng([0.0]))
    assert any(sec.kind == "affair" for sec in t.secrets)
    compromise(a, t, SeqRng([0.0]))
    assert any(sec.kind == "compromise" for sec in t.secrets)
    legit = {"Vantrell": 50.0}
    msgs = compromise(a, t, SeqRng([0.99]), legitimacy=legit, agent_house="Vantrell")
    assert legit["Vantrell"] < 50.0 and any("fabricating" in m for m in msgs)


def test_takeover_buys_the_house_out():
    game = GildedGame(seed=99)
    for _ in range(3):
        game.end_turn()
    ra = game.realms["Vantrell"]
    rb = game.realms["Karsgate"]
    realms = game.realms
    buyer = ra.ruler
    buyer.gold_reserve = 1000.0
    seller = rb.characters[10]
    seller.loyalty = 10.0
    ent = Enterprise(eid=1, kind="bank", name="K Bank", house="Karsgate", province=0)
    ent.ledger = {seller.id: 80.0}
    tk = Takeover(buyer, "Vantrell", "Karsgate")
    ents = [ent]
    for _ in range(6):
        msgs = tk.advance(realms, ents, SeqRng([]), game)
        if tk.complete:
            break
    assert tk.complete
    assert ent.house == "Vantrell"
    assert ra.ruler.id in ent.ledger                # ledger re-carved for the buyer
    assert seller.gold_reserve > 0
    assert any("HOSTILE TAKEOVER" in m for m in msgs)
    assert tk.advance(realms, ents, SeqRng([]), game) == []


def test_conspiracy_staged_accident():
    ra, rb, realms = _two_realms(100)
    m = ra.ruler
    m.gold_reserve = 200.0
    assert start_conspiracy(m, rb.ruler, "Karsgate", ra.characters[5:6]) is None
    c = start_conspiracy(m, rb.ruler, "Karsgate", ra.characters[5:8])
    assert isinstance(c, Conspiracy) and m.gold_reserve == 100.0
    assert c.advance(realms, SeqRng([0.99] * 3)) == []
    assert c.advance(realms, SeqRng([0.99] * 3)) == []
    msgs = c.advance(realms, SeqRng([0.99, 0.99, 0.99, 0.5]))
    assert c.done and not c.exposed
    assert not rb.ruler.is_alive
    assert msgs


def test_conspiracy_exposure_is_nuclear():
    ra, rb, realms = _two_realms(101)
    m = ra.ruler
    m.gold_reserve = 200.0
    c = start_conspiracy(m, rb.ruler, "Karsgate", ra.characters[5:8])
    tide = IdeologicalTide()
    legit = {"Vantrell": 70.0}
    msgs = c.advance(realms, SeqRng([0.0, 0.0]), tide, legit)
    assert c.exposed and c.done
    assert legit["Vantrell"] < 70.0
    assert tide.house_atrocities.get("Vantrell", 0.0) > 0
    assert rb.ruler._society.opinions[(rb.ruler.id, m.id)] <= -60
    assert not m.is_alive                           # execution roll came up
    assert any("loses their nerve" in m_ for m_ in msgs)
# --- L3.5: share_price tests ---

def test_share_price_positive_floor():
    """An enterprise the market values at 0 still costs > 0 per percent."""
    game = GildedGame(seed=42)
    for _ in range(3):
        game.end_turn()
    worthless = [e for e in game.enterprises if game.market.value(e, game) == 0.0][0]
    p = share_price(worthless, game)
    assert p > 0.0

def test_share_price_rises_in_boom():
    """Raising the commodity price raises the share price."""
    game = GildedGame(seed=42)
    for _ in range(3):
        game.end_turn()
    from gilded.market import PRODUCES
    e = max([e for e in game.enterprises if game.market.value(e, game) > 0],
            key=lambda e: game.market.value(e, game))
    commodity = PRODUCES.get(e.kind)
    game.market.prices[commodity] = 0.5
    cheap = share_price(e, game)
    game.market.prices[commodity] = 4.0
    dear = share_price(e, game)
    assert dear > cheap

def test_share_price_bounded():
    """share_price stays within [TAKEOVER_PRICE * 0.25, TAKEOVER_PRICE * 4.0]."""
    game = GildedGame(seed=42)
    for _ in range(3):
        game.end_turn()
    lo = 0.5
    hi = 8.0
    prices = [share_price(e, game) for e in game.enterprises]
    assert all(lo - 1e-9 <= p <= hi + 1e-9 for p in prices)

def test_share_price_both_sides_of_base():
    """Some ventures price above 2.0, some below, in a normal market."""
    game = GildedGame(seed=42)
    for _ in range(3):
        game.end_turn()
    prices = [share_price(e, game) for e in game.enterprises]
    above = [p for p in prices if p > 2.0 + 1e-9]
    below = [p for p in prices if p < 2.0 - 1e-9]
    assert above, "no venture prices above the base rate"
    assert below, "no venture prices below the base rate"

def test_advance_uses_game_not_flat_rate():
    """advance() requires a game argument and charges the priced rate."""
    game = GildedGame(seed=42)
    for _ in range(4):
        game.end_turn()
    target_house = sorted(game.houses)[0]
    buyer_house = sorted(game.houses)[1]
    buyer = game.realms[buyer_house].ruler
    buyer.gold_reserve = 1000.0
    gold_before = buyer.gold_reserve
    tk = Takeover(buyer, buyer_house, target_house)
    target_ents = [e for e in game.enterprises if e.house == target_house]
    assert len(target_ents) >= 1, f"Expected at least one enterprise for {target_house}"
    tk.advance(game.realms, target_ents, SeqRng([]), game)
    # advance charges the priced rate — buyer should have spent gold
    assert buyer.gold_reserve < gold_before, \
        f"Buyer gold unchanged ({gold_before}): advance should charge the priced rate"


def test_sway_base_chance():
    """sway base chance = 0.60: statecraft 0 agent succeeds on roll 0.59, fails on roll 0.61."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 0 - offset
    # roll 0.59 < 0.60 base → must succeed (catches SWAY_BASE→0.5)
    msgs = sway(agent, rb.ruler, SeqRng([0.59]))
    assert not any("sees through" in m for m in msgs)
    # roll 0.61 > 0.60 base → must fail
    msgs = sway(agent, rb.ruler, SeqRng([0.61]))
    assert any("sees through" in m for m in msgs)


def test_sway_coefficient():
    """sway coefficient = 0.01 per statecraft: statecraft 20 chance=0.80 succeeds on roll 0.75, fails on 0.81."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 20 - offset
    # roll 0.75 < 0.80 (0.60 + 20*0.01) → must succeed
    # If coeff→0.005: chance=0.60+20*0.005=0.70, roll 0.75>0.70 → fails (caught)
    # If coeff→0.02: chance=0.60+20*0.02=1.00→capped 0.95, roll 0.75<0.95 → succeeds (not caught here)
    msgs = sway(agent, rb.ruler, SeqRng([0.75]))
    assert not any("sees through" in m for m in msgs)
    # roll 0.81 > 0.80 → must fail
    # If coeff→0.02: chance=1.00→capped 0.95, roll 0.81<0.95 → succeeds (caught)
    msgs = sway(agent, rb.ruler, SeqRng([0.81]))
    assert any("sees through" in m for m in msgs)


def test_sway_cap():
    """sway cap = 0.95: statecraft 40 chance=0.95 succeeds on roll 0.94."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 40 - offset
    # roll 0.94 < 0.95 cap → must succeed (catches CAP→0.90)
    msgs = sway(agent, rb.ruler, SeqRng([0.94]))
    assert not any("sees through" in m for m in msgs)
    # roll 0.96 > 0.95 cap → must fail
    msgs = sway(agent, rb.ruler, SeqRng([0.96]))
    assert any("sees through" in m for m in msgs)


def test_sway_penalty():
    """failed sway costs exactly 5 opinion."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 0 - offset
    target = rb.ruler
    before = target._society.opinions.get((target.id, agent.id), 0)
    sway(agent, target, SeqRng([0.70]))
    after = target._society.opinions.get((target.id, agent.id), 0)
    assert after - before == -5
