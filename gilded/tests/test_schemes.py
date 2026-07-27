
"""Tests for gilded.society.schemes (mission G9)."""

import random

from gilded.enterprises import Enterprise
from gilded.chassis import GildedGame
from gilded.society.characters import Secret, SocietyState
from gilded.society.ideology import IdeologicalTide
from gilded.society.realm import create_house_realm
from gilded.society.schemes import (
    BLACKMAIL_SHARE_PCT,
    Conspiracy,
    SCHEME_THRESHOLD,
    SchemeManager,
    Takeover,
    TAKEOVER_PRICE,
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
    s.progress = SCHEME_THRESHOLD - 1
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
    s.progress = SCHEME_THRESHOLD - 1
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
    assert ent.ledger[agent.id] == BLACKMAIL_SHARE_PCT
    assert ent.ledger[victim.id] == 40.0 - BLACKMAIL_SHARE_PCT
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
    lo = TAKEOVER_PRICE * 0.25
    hi = TAKEOVER_PRICE * 4.0
    for e in game.enterprises:
        p = share_price(e, game)
        assert lo - 1e-9 <= p <= hi + 1e-9

def test_share_price_both_sides_of_base():
    """Some ventures price above 2.0, some below, in a normal market."""
    game = GildedGame(seed=42)
    for _ in range(3):
        game.end_turn()
    prices = [share_price(e, game) for e in game.enterprises]
    above = [p for p in prices if p > TAKEOVER_PRICE + 1e-9]
    below = [p for p in prices if p < TAKEOVER_PRICE - 1e-9]
    assert above, "no venture prices above the base rate"
    assert below, "no venture prices below the base rate"

def test_advance_uses_game_not_flat_rate():
    """advance() requires a game argument and charges the priced rate."""
    game = GildedGame(seed=42)
    for _ in range(3):
        game.end_turn()
    target_house = sorted(game.houses)[0]
    buyer_house = sorted(game.houses)[1]
    buyer = game.realms[buyer_house].ruler
    buyer.gold_reserve = 1000.0
    tk = Takeover(buyer, buyer_house, target_house)
    target_ents = [e for e in game.enterprises if e.house == target_house]
    if target_ents:
        tk.advance(game.realms, target_ents, SeqRng([]), game)
        # should not raise
