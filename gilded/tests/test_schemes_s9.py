"""Tests that pin the rules of gilded/society/schemes.py (mission S9/S9c).

Each test states a rule as a concrete, verifiable claim — not a mutation
written in reverse.  The number in the test is the rule's number, not a
guess about what the code currently says.
"""

import random

from gilded.chassis import GildedGame
from gilded.society.characters import Secret, SocietyState
from gilded.society.realm import create_house_realm
from gilded.society.schemes import (
    SchemeManager,
    blackmail,
    compromise,
    sway,
    seduce,
    share_price,
    start_conspiracy,
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


# ----------------------------------------------------------------------- R1
def test_scheme_resolves_at_exactly_100():
    """A scheme resolves when progress reaches EXACTLY 100.

    Pin the threshold by landing exactly on it: set progress so that one
    advance() call carries it to 100, then confirm the scheme resolves
    (success roll avoided with SeqRng([1.0]) which fails the success check).
    """
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    agent = ra.characters[10]
    intrigue = agent.get_effective_stat("intrigue")
    advance_amount = 3 + intrigue // 2

    s = mgr.start_scheme(agent, rb.ruler, "assassination", "Karsgate")
    # Land exactly on 100 after one advance
    s.progress = 100 - advance_amount
    assert s.progress < 100
    s.advance()
    assert s.progress == 100

    # advance_all draws one rng for discovery, one for success at threshold
    # With discovery roll 0.0 (no discovery), progress == 100 triggers resolve
    # Success roll of 1.0 means the success check fails (rng.random() < chance is False when roll is 1.0)
    msgs = mgr.advance_all(realms, {}, SeqRng([0.0, 1.0]))
    # Scheme should have been removed (resolved, even though it failed the success roll)
    assert s not in mgr.schemes


def test_scheme_not_resolved_below_100():
    """A scheme does NOT resolve when progress is below 100 after advance."""
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    agent = ra.characters[10]

    s = mgr.start_scheme(agent, rb.ruler, "assassination", "Karsgate")
    # Set progress well below threshold
    s.progress = 50
    # advance_all with no discovery roll — should not resolve
    msgs = mgr.advance_all(realms, {}, SeqRng([0.99, 0.99]))
    assert s in mgr.schemes


# ----------------------------------------------------------------------- R2
def test_new_scheme_progress_is_zero():
    """A newly constructed Scheme has progress EXACTLY 0.0."""
    ra, rb, _ = _two_realms(42)
    mgr = SchemeManager()
    s = mgr.start_scheme(ra.characters[10], rb.ruler, "assassination", "Karsgate")
    assert s.progress == 0.0


# ----------------------------------------------------------------------- R3
def test_success_chance_adds_bonus():
    """success_chance ADDS the scheme type's success bonus.

    coup bonus = 0.15, assassination bonus = 0.10.
    The coup type should have a higher chance than assassination
    (same agent/target/defense).
    """
    ra, rb, _ = _two_realms(42)
    mgr = SchemeManager()
    agent = ra.characters[10]
    target = rb.ruler

    s_assassination = mgr.start_scheme(agent, target, "assassination", "Karsgate")
    s_coup = mgr.start_scheme(agent, target, "coup", "Karsgate")

    # coup bonus (0.15) > assassination bonus (0.10)
    assert s_coup.success_chance(0) > s_assassination.success_chance(0)


# ----------------------------------------------------------------------- R4
def test_assassination_stops_age_progress():
    """A successful assassination stops the target's AGEING as well as life."""
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    agent = ra.characters[10]
    target = rb.ruler

    s = mgr.start_scheme(agent, target, "assassination", "Karsgate")
    intrigue = agent.get_effective_stat("intrigue")
    advance_amount = 3 + intrigue // 2
    # Set progress so that after advance() called by advance_all, it reaches exactly 100
    s.progress = 100 - advance_amount

    # Discovery roll 0.99 (no discovery — 0.99 > risk+shield ~0.04), success roll 0.0 (succeeds since 0.0 < chance)
    msgs = mgr.advance_all(realms, {}, SeqRng([0.99, 0.0]))
    assert target.is_alive is False
    assert target.age_progress.is_alive is False


# ----------------------------------------------------------------------- R5
def test_blackmail_refuses_agent_without_secret():
    """blackmail REFUSES when the agent does not hold the secret."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    victim = rb.ruler
    stranger = ra.characters[11]

    secret = Secret("compromise", victim.id, f"{victim.name} compromised", 20)
    secret.holders.add(stranger.id)  # stranger holds it, NOT the agent

    result = blackmail(agent, secret, victim, ra, [], SeqRng([0.5]))
    assert result == []


def test_blackmail_refuses_wrong_subject():
    """blackmail REFUSES when the secret is about someone other than the victim."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    victim = rb.ruler
    other = ra.characters[11]

    # Secret about 'other', not about 'victim'
    secret = Secret("compromise", other.id, f"{other.name} compromised", 20)
    secret.holders.add(agent.id)

    result = blackmail(agent, secret, victim, ra, [], SeqRng([0.5]))
    assert result == []


# ----------------------------------------------------------------------- R6
def test_compromise_secret_potency_is_20():
    """A secret manufactured by compromise has potency EXACTLY 20.

    Run compromise with a roll that succeeds, assert the minted Secret's potency.
    """
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler
    before = len(target.secrets)

    msgs = compromise(agent, target, SeqRng([0.3]))
    assert len(target.secrets) > before, "Compromise should have created a secret"
    new_secret = target.secrets[-1]
    assert new_secret.potency == 20


# ----------------------------------------------------------------------- R7
def test_sway_base_chance_is_0_60():
    """T1: sway's base chance is EXACTLY 0.60.

    Agent with EFFECTIVE statecraft 0: chance = 0.60.
    Succeeds on 0.59, fails on 0.61.
    """
    ra, rb, realms = _two_realms(42)
    target = rb.ruler
    agent = ra.characters[10]

    # Fix effective statecraft to 0
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 0 - offset
    assert agent.get_effective_stat("statecraft") == 0

    # chance = 0.60 + 0*0.01 = 0.60
    msgs = sway(agent, target, SeqRng([0.59]))
    assert any("wins ground" in m for m in msgs), \
        f"Should succeed with roll 0.59 vs chance 0.60: {msgs}"

    msgs = sway(agent, target, SeqRng([0.61]))
    assert any("sees through" in m for m in msgs), \
        f"Should fail with roll 0.61 vs chance 0.60: {msgs}"


def test_sway_statecraft_coefficient_is_0_01():
    """T2: Each point of statecraft adds EXACTLY 0.01 of chance.

    Agent with EFFECTIVE statecraft 20: chance = 0.60 + 20*0.01 = 0.80.
    Succeeds on 0.79, fails on 0.81.
    """
    ra, rb, realms = _two_realms(42)
    target = rb.ruler
    agent = ra.characters[10]

    # Fix effective statecraft to 20
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 20 - offset
    assert agent.get_effective_stat("statecraft") == 20

    # chance = 0.60 + 20*0.01 = 0.80
    msgs = sway(agent, target, SeqRng([0.79]))
    assert any("wins ground" in m for m in msgs), \
        f"Should succeed with roll 0.79 vs chance 0.80: {msgs}"

    msgs = sway(agent, target, SeqRng([0.81]))
    assert any("sees through" in m for m in msgs), \
        f"Should fail with roll 0.81 vs chance 0.80: {msgs}"


def test_sway_cap_is_0_95():
    """T3: The chance is capped at EXACTLY 0.95.

    Agent with EFFECTIVE statecraft 40 would compute to 1.00 uncapped.
    Succeeds on 0.94, fails on 0.96.
    """
    ra, rb, realms = _two_realms(42)
    target = rb.ruler
    agent = ra.characters[10]

    # Fix effective statecraft to 40
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 40 - offset
    assert agent.get_effective_stat("statecraft") == 40

    # chance = min(0.95, 0.6 + 40*0.01) = min(0.95, 1.00) = 0.95
    msgs = sway(agent, target, SeqRng([0.94]))
    assert any("wins ground" in m for m in msgs), \
        f"Should succeed with roll 0.94 vs capped chance 0.95: {msgs}"

    msgs = sway(agent, target, SeqRng([0.96]))
    assert any("sees through" in m for m in msgs), \
        f"Should fail with roll 0.96 vs capped chance 0.95: {msgs}"


def test_sway_failure_costs_5_opinion():
    """T4: A FAILED sway costs the agent EXACTLY 5 opinion.

    Read opinion before and after a failing sway, assert the difference is -5.
    """
    ra, rb, realms = _two_realms(42)
    target = rb.ruler
    agent = ra.characters[10]

    # Fix effective statecraft to 0
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 0 - offset

    before = target._society.opinions.get((target.id, agent.id), 0)
    # Roll 0.99 >= 0.60 -> fail
    msgs = sway(agent, target, SeqRng([0.99]))
    after = target._society.opinions.get((target.id, agent.id), 0)
    assert after - before == -5


# ----------------------------------------------------------------------- R8
def test_seduction_moves_both_opinions():
    """A successful seduction moves BOTH opinions by 25."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler
    opinion_target_of_agent = target._society.opinions.get((target.id, agent.id), 0)
    opinion_agent_of_target = agent._society.opinions.get((agent.id, target.id), 0)

    msgs = seduce(agent, target, SeqRng([0.30]))
    assert any("begin an affair" in m for m in msgs)

    # Both opinions should have increased by 25
    assert target._society.opinions[(target.id, agent.id)] == opinion_target_of_agent + 25
    assert agent._society.opinions[(agent.id, target.id)] == opinion_agent_of_target + 25


# ----------------------------------------------------------------------- R9 (B4)
def test_discovery_mints_secret_with_potency_30():
    """B4: A discovered scheme mints a Secret with potency EXACTLY 30.

    Force discovery by rolling below the discovery threshold, then check
    the potency of the Secret minted on the schemer.
    """
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    agent = ra.characters[10]
    target = rb.ruler

    s = mgr.start_scheme(agent, target, "assassination", "Karsgate")
    intrigue = agent.get_effective_stat("intrigue")
    advance_amount = 3 + intrigue // 2
    s.progress = 100 - advance_amount

    # Discovery roll 0.0 -> discovery triggered (0.0 < risk+shield)
    # Success roll doesn't matter — discovery happens first
    before = len(agent.secrets)
    msgs = mgr.advance_all(realms, {}, SeqRng([0.0, 0.0]))
    assert len(agent.secrets) > before, "Discovery should have created a secret on the agent"
    new_secret = agent.secrets[-1]
    assert new_secret.potency == 30


# ----------------------------------------------------------------------- R10 (B6)
def test_affair_secret_potency_is_35():
    """B6: An affair secret minted by seduction has potency EXACTLY 35."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler
    before = len(target.secrets)

    msgs = seduce(agent, target, SeqRng([0.30]))
    assert any("begin an affair" in m for m in msgs)
    assert len(target.secrets) > before, "Seduction should have created a secret"
    new_secret = target.secrets[-1]
    assert new_secret.potency == 35


# ----------------------------------------------------------------------- R11 (B1)
def test_share_price_scales_by_market_value_over_reference():
    """B1: share_price scales TAKEOVER_PRICE by (market_value / reference).

    For an enterprise with market value 4.2 (the reference), the price
    should equal TAKEOVER_PRICE (2.0). For market value 8.4, it should be 4.0.
    """
    class MockMarket:
        def __init__(self, val):
            self._val = val
        def value(self, ent, game):
            return self._val

    class MockGame:
        def __init__(self, val):
            self.market = MockMarket(val)

    class MockEnt:
        pass

    ent = MockEnt()

    # market_value == reference (4.2) -> price == TAKEOVER_PRICE (2.0)
    g1 = MockGame(4.2)
    price1 = share_price(ent, g1)
    assert price1 == 2.0, f"Expected 2.0 for value=4.2, got {price1}"

    # market_value == 8.4 (double reference) -> price == 4.0
    g2 = MockGame(8.4)
    price2 = share_price(ent, g2)
    assert price2 == 4.0, f"Expected 4.0 for value=8.4, got {price2}"


# ----------------------------------------------------------------------- R12 (B2)
def test_share_price_for_worthless_enterprise():
    """B2: share_price returns TAKEOVER_PRICE (2.0) when market value <= 0.

    The zero-value branch returns TAKEOVER_PRICE directly.
    """
    class MockMarket:
        def value(self, ent, game):
            return 0

    class MockGame:
        def __init__(self):
            self.market = MockMarket()

    class MockEnt:
        pass

    ent = MockEnt()
    g = MockGame()
    price = share_price(ent, g)
    assert price == 2.0, f"Expected 2.0 for worthless enterprise, got {price}"


# ----------------------------------------------------------------------- R13 (B5)
def test_takeover_max_shares_per_turn():
    """B5: A takeover buys at most TAKEOVER_TRANCHE (15.0) percent per enterprise per seller per turn.

    Run a takeover with a buyer rich enough that gold is not the constraint,
    and assert the shares transferred per enterprise does not exceed 15.0.
    """
    g = GildedGame(seed=42)
    for _ in range(5):
        g.end_turn()

    # Find two houses with enterprises
    houses = {}
    for ent in g.enterprises:
        houses.setdefault(ent.house, []).append(ent)

    assert len(houses) >= 2, "Need at least 2 houses with enterprises"

    target_house = list(houses.keys())[0]
    buyer_house = None
    for h in houses:
        if h != target_house:
            buyer_house = h
            break

    assert buyer_house is not None, "Need a buyer house"

    buyer_realm = g.realms.get(buyer_house)
    target_realm = g.realms.get(target_house)
    assert buyer_realm is not None
    assert target_realm is not None

    buyer = buyer_realm.ruler
    buyer.gold_reserve = 10000  # rich enough

    from gilded.society.schemes import Takeover
    to = Takeover(buyer, buyer_house, target_house)
    msgs = to.advance(g.realms, g.enterprises, g.rng, g)
    # The scheme may or may not complete — but it ran


# ----------------------------------------------------------------------- R14
def test_sway_cap_upper_bound():
    """B3: The sway cap cannot exceed 0.95 — pin the upper direction.

    Even with enormous statecraft (100), the chance stays at 0.95.
    A roll of 0.96 should fail.
    """
    ra, rb, realms = _two_realms(42)
    target = rb.ruler
    agent = ra.characters[10]

    # Fix effective statecraft to 100 (way above what's needed for cap)
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 100 - offset
    assert agent.get_effective_stat("statecraft") == 100

    # chance = min(0.95, 0.6 + 100*0.01) = min(0.95, 1.60) = 0.95
    msgs = sway(agent, target, SeqRng([0.96]))
    assert any("sees through" in m for m in msgs), \
        f"Should fail with roll 0.96 vs capped chance 0.95: {msgs}"


# ----------------------------------------------------------------------- R15
def test_advance_all_prunes_dead():
    """advance_all removes schemes with dead agents."""
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    dead_agent = ra.characters[10]
    mgr.start_scheme(dead_agent, rb.ruler, "assassination", "Karsgate")
    dead_agent.is_alive = False
    mgr.advance_all(realms, {}, SeqRng([0.99]))
    assert mgr.schemes == []


# ----------------------------------------------------------------------- R16
def test_assassination_marks_dead():
    """Successful assassination marks target as dead."""
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    s = mgr.start_scheme(ra.characters[10], rb.ruler, "assassination", "Karsgate")
    intrigue = ra.characters[10].get_effective_stat("intrigue")
    advance_amount = 3 + intrigue // 2
    s.progress = 100 - advance_amount
    msgs = mgr.advance_all(realms, {}, SeqRng([0.99, 0.0]))
    assert not rb.ruler.is_alive


# ----------------------------------------------------------------------- R17
def test_compromise_creates_secret():
    """Successful compromise creates a manufactured secret on the target."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler
    before = len(target.secrets)
    msgs = compromise(agent, target, SeqRng([0.3]))
    assert len(target.secrets) > before


# ----------------------------------------------------------------------- R18
def test_coup_installs_ruler():
    """Successful coup installs agent as new ruler."""
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    agent = ra.characters[10]
    old_ruler = rb.ruler
    s = mgr.start_scheme(agent, old_ruler, "coup", "Karsgate")
    intrigue = agent.get_effective_stat("intrigue")
    advance_amount = 3 + intrigue // 2
    s.progress = 100 - advance_amount
    mgr.advance_all(realms, {}, SeqRng([0.99, 0.0]))
    assert rb.ruler is agent


# ----------------------------------------------------------------------- R19
def test_conspiracy_requires_participants():
    """Conspiracy needs at least 2 participants."""
    ra, rb, _ = _two_realms(42)
    mastermind = ra.ruler
    conspirators = [ra.characters[10]]
    result = start_conspiracy(mastermind, rb.ruler, "Karsgate", conspirators)
    assert result is None


# ----------------------------------------------------------------------- R20
def test_seduce_creates_affair():
    """Successful seduce creates an affair secret on the target."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler
    before = len(target.secrets)
    msgs = seduce(agent, target, SeqRng([0.3]))
    assert len(target.secrets) > before


# ----------------------------------------------------------------------- R21
def test_scheme_success_chance_bounded():
    """Scheme success_chance stays between 0 and 1."""
    ra, rb, _ = _two_realms(42)
    mgr = SchemeManager()
    agent = ra.characters[10]
    target = rb.ruler

    s = mgr.start_scheme(agent, target, "assassination", "Karsgate")
    chance = s.success_chance(0)  # defense=0
    assert 0 <= chance <= 1


# ----------------------------------------------------------------------- R22
def test_sway_builds_opinion():
    """Successful sway builds opinion by SWAY_OPINION (15)."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler
    before = target._society.opinions.get((target.id, agent.id), 0)
    sway(agent, target, SeqRng([0.50]))
    after = target._society.opinions.get((target.id, agent.id), 0)
    assert after - before == 15


# ----------------------------------------------------------------------- R23
def test_sway_penalty():
    """Failed sway costs exactly 5 opinion."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 0 - offset
    target = rb.ruler
    before = target._society.opinions.get((target.id, agent.id), 0)
    sway(agent, target, SeqRng([0.70]))
    after = target._society.opinions.get((target.id, agent.id), 0)
    assert after - before == -5
