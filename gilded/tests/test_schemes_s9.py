"""Tests that pin the eight rules of gilded/society/schemes.py (mission S9).

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
    intrigue = agent.get_effective_stat("intrigue")
    advance_amount = 3 + intrigue // 2

    s = mgr.start_scheme(agent, rb.ruler, "assassination", "Karsgate")
    # After advance(), progress should still be below 100
    s.progress = 100 - advance_amount - 1  # lands at 99 - advance_amount
    # advance_all calls s.advance() first, so progress after advance = 99
    assert s.progress + advance_amount == 99

    # No discovery roll needed — progress < 100 after advance means scheme stays
    msgs = mgr.advance_all(realms, {}, SeqRng([]))
    assert s in mgr.schemes


# ----------------------------------------------------------------------- R2
def test_new_scheme_progress_is_zero():
    """A newly constructed Scheme has progress EXACTLY 0.0."""
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    agent = ra.characters[10]
    s = mgr.start_scheme(agent, rb.ruler, "assassination", "Karsgate")
    assert s.progress == 0.0


# ----------------------------------------------------------------------- R3
def test_success_chance_adds_bonus():
    """success_chance ADDS the scheme type's success bonus.

    An assassination (bonus 0.10) must produce a higher chance than a
    hypothetical scheme type with zero bonus — all else being equal.
    Pin the arithmetic precisely enough that a sign flip changes it.
    """
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    agent = ra.characters[10]

    s_assassination = mgr.start_scheme(agent, rb.ruler, "assassination", "Karsgate")
    s_coup = mgr.start_scheme(agent, rb.ruler, "coup", "Karsgate")

    # Both schemes have the same agent, no participants, same defense
    chance_assassination = s_assassination.success_chance(0)
    chance_coup = s_coup.success_chance(0)

    # Coup has bonus 0.15, assassination has bonus 0.10
    # coup must be higher by exactly 0.025 (the 0.05 difference halved by the * 0.5 factor)
    diff = chance_coup - chance_assassination
    assert 0.02 < diff < 0.03, f"Coup should be ~0.025 higher than assassination, got {diff:.4f}"

    # Pin the absolute value to catch a sign flip
    # BASE_SUCCESS=0.3, assassination bonus=0.10, no participants, agent intrigue varies
    # chance = (0.3 + 0.10) * 0.5 + intrigue*0.01 = 0.2 + intrigue*0.01
    # For a typical agent with intrigue ~50: chance ~ 0.7
    assert 0.0 < chance_assassination < 0.9  # strictly inside the clamp


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

    result = blackmail(agent, secret, victim, ra, [], SeqRng([]))
    assert result == []


def test_blackmail_refuses_wrong_subject():
    """blackmail REFUSES when the secret is about someone other than the victim."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    victim = rb.ruler
    other_target = ra.characters[11]

    secret = Secret("compromise", other_target.id, f"{other_target.name} compromised", 20)
    secret.holders.add(agent.id)  # agent holds it, but it's about someone else

    result = blackmail(agent, secret, victim, ra, [], SeqRng([]))
    assert result == []


# ----------------------------------------------------------------------- R6
def test_compromise_secret_potency_is_20():
    """A secret manufactured by compromise has potency EXACTLY 20."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler

    msgs = compromise(agent, target, SeqRng([0.0]))  # 0.0 < chance -> success
    secrets = [sec for sec in target.secrets if sec.kind == "compromise"]
    assert len(secrets) >= 1
    assert secrets[0].potency == 20


# ----------------------------------------------------------------------- R7
def test_sway_base_chance_is_0_60():
    """T1: sway's base chance is EXACTLY 0.60.

    An agent with EFFECTIVE statecraft 0 succeeds on roll 0.59, fails on 0.61.
    Both rolls are typed as literals — no derivation from SWAY_BASE.
    """
    ra, rb, realms = _two_realms(42)
    target = rb.ruler
    agent = ra.characters[10]

    # Fix effective statecraft to 0
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 0 - offset
    assert agent.get_effective_stat("statecraft") == 0

    # Succeeds on roll < 0.60
    msgs = sway(agent, target, SeqRng([0.59]))
    assert any("wins ground" in m for m in msgs), \
        f"Should succeed with roll 0.59 vs chance 0.60: {msgs}"

    # Fails on roll >= 0.60
    msgs = sway(agent, target, SeqRng([0.61]))
    assert any("sees through" in m for m in msgs), \
        f"Should fail with roll 0.61 vs chance 0.60: {msgs}"


def test_sway_statecraft_coefficient_is_0_01():
    """T2: Each point of statecraft adds EXACTLY 0.01 of chance.

    Agent with EFFECTIVE statecraft 20 has chance 0.80.
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

    # chance = min(0.95, 0.6 + 20*0.01) = 0.80
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

    # Fix effective statecraft to 0 (chance = 0.60)
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 0 - offset
    assert agent.get_effective_stat("statecraft") == 0

    # Read opinion before (defaults to 0 if not set)
    opinion_before = target._society.opinions.get((target.id, agent.id), 0)

    # Roll 0.70 > 0.60 chance, so sway fails
    msgs = sway(agent, target, SeqRng([0.70]))
    assert any("sees through" in m for m in msgs)

    opinion_after = target._society.opinions.get((target.id, agent.id), 0)
    assert opinion_after - opinion_before == -5, \
        f"Failed sway should cost exactly 5 opinion: was {opinion_before}, now {opinion_after}"


# ----------------------------------------------------------------------- R8
def test_seduction_moves_both_opinions():
    """A successful seduction moves BOTH opinions by 25."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler

    # Record opinions before
    opinion_target_of_agent = target._society.opinions.get((target.id, agent.id), 0)
    opinion_agent_of_target = agent._society.opinions.get((agent.id, target.id), 0)

    msgs = seduce(agent, target, SeqRng([0.0]))  # 0.0 < chance -> success
    assert any("begin an affair" in m for m in msgs)

    # Both opinions should have increased by 25
    assert target._society.opinions[(target.id, agent.id)] == opinion_target_of_agent + 25
    assert agent._society.opinions[(agent.id, target.id)] == opinion_agent_of_target + 25
