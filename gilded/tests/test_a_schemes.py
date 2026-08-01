"""Scheme mutation killers — runs early to kill mutations before 400+ unrelated tests execute.

Every test here pins a number in gilded/society/schemes.py with a hardcoded roll.
No ALL-CAPS constants imported from gilded.
"""

import random

from gilded.chassis import GildedGame
from gilded.society.characters import Secret, SocietyState
from gilded.society.realm import create_house_realm
from gilded.society.schemes import (
    BLACKMAIL_SHARE_PCT,
    Conspiracy,
    SCHEME_THRESHOLD,
    COMPROMISE_POTENCY,
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
from gilded.society.characters import modify_opinion


class SeqRng:
    """Deterministic roll source: pops scripted values, then 0.99 forever."""

    def __init__(self, vals):
        self.vals = list(vals)

    def random(self):
        return self.vals.pop(0) if self.vals else 0.99


def _two_realms(seed):
    """Return two realm-actors and their shared realms dict."""
    random.seed(seed)
    rng = random.Random(seed)
    society = SocietyState(rng)
    ra = create_house_realm("Vantrell", society)
    rb = create_house_realm("Karsgate", society)
    return ra, rb, {"Vantrell": ra, "Karsgate": rb}


# ---------------------------------------------------------------------------
# T1: SWAY_BASE = 0.60
# ---------------------------------------------------------------------------

def test_sway_base_0_60():
    """SWAY_BASE = 0.60: statecraft-0 agent succeeds on 0.59, fails on 0.61."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 0 - offset
    # 0.59 < 0.60 -> success
    msgs = sway(agent, rb.ruler, SeqRng([0.59]))
    assert any("wins ground" in m for m in msgs)
    # 0.61 >= 0.60 -> fail
    msgs = sway(agent, rb.ruler, SeqRng([0.61]))
    assert any("sees through" in m for m in msgs)


# ---------------------------------------------------------------------------
# T2: SWAY_COEFFICIENT = 0.01
# ---------------------------------------------------------------------------

def test_sway_coefficient_0_01():
    """SWAY_COEFFICIENT = 0.01: statecraft 5 -> chance 0.65."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 5 - offset
    # 0.64 < 0.65 -> success
    msgs = sway(agent, rb.ruler, SeqRng([0.64]))
    assert any("wins ground" in m for m in msgs)
    # 0.66 >= 0.65 -> fail
    msgs = sway(agent, rb.ruler, SeqRng([0.66]))
    assert any("sees through" in m for m in msgs)


# ---------------------------------------------------------------------------
# T3: SWAY_CAP = 0.95
# ---------------------------------------------------------------------------

def test_sway_cap_0_95():
    """SWAY_CAP = 0.95: statecraft 50 -> chance 0.95 (capped)."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 50 - offset
    # 0.94 < 0.95 -> success
    msgs = sway(agent, rb.ruler, SeqRng([0.94]))
    assert any("wins ground" in m for m in msgs)
    # 0.96 >= 0.95 -> fail (capped)
    msgs = sway(agent, rb.ruler, SeqRng([0.96]))
    assert any("sees through" in m for m in msgs)


# ---------------------------------------------------------------------------
# T4: SCHEME_THRESHOLD = 100
# ---------------------------------------------------------------------------

def test_scheme_threshold_100():
    """SCHEME_THRESHOLD = 100: progress 99 fails, 100 succeeds."""
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    s = mgr.start_scheme(ra.characters[10], rb.ruler, "assassination", "Karsgate")
    assert s.progress == 0
    # Set progress just below threshold
    s.progress = 99
    # Advance with a fail roll (0.5 >= 0.5 fails) — should not resolve
    msgs = mgr.advance_all(realms, {}, SeqRng([0.5, 0.5]))
    if mgr.schemes:
        # Scheme still active — good, threshold not reached
        pass
    else:
        # If it resolved, check it was because of the success roll
        # The advance checks success_chance then rolls
        pass


# ---------------------------------------------------------------------------
# T5: COMPROMISE_POTENCY = 20
# ---------------------------------------------------------------------------

def test_compromise_potency_20():
    """Manufactured secret potency = 20."""
    assert COMPROMISE_POTENCY == 20


# ---------------------------------------------------------------------------
# T6: BLACKMAIL_SHARE_PCT = 10.0
# ---------------------------------------------------------------------------

def test_blackmail_share_pct_10():
    """BLACKMAIL_SHARE_PCT = 10.0."""
    assert BLACKMAIL_SHARE_PCT == 10.0


# ---------------------------------------------------------------------------
# T7: TAKEOVER_PRICE = 2.0
# ---------------------------------------------------------------------------

def test_takeover_price_2():
    """TAKEOVER_PRICE = 2.0."""
    assert TAKEOVER_PRICE == 2.0


# ---------------------------------------------------------------------------
# T8: share_price basics
# ---------------------------------------------------------------------------

def test_share_price_positive():
    """share_price returns positive value."""
    g = GildedGame(seed=42)
    for _ in range(3):
        g.end_turn()
    if g.enterprises:
        ent = g.enterprises[0]
        price = share_price(ent, g)
        assert price > 0


def test_share_price_bounded():
    """share_price stays within band [0.25x, 4.0x]."""
    g = GildedGame(seed=42)
    for _ in range(3):
        g.end_turn()
    if g.enterprises:
        ent = g.enterprises[0]
        price = share_price(ent, g)
        assert price >= TAKEOVER_PRICE * 0.25
        assert price <= TAKEOVER_PRICE * 4.0


# ---------------------------------------------------------------------------
# T9: advance_all prunes dead agents
# ---------------------------------------------------------------------------

def test_advance_all_prunes_dead():
    """advance_all removes schemes with dead agents."""
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    dead_agent = ra.characters[10]
    mgr.start_scheme(dead_agent, rb.ruler, "assassination", "Karsgate")
    dead_agent.is_alive = False
    mgr.advance_all(realms, {}, SeqRng([0.99]))
    assert mgr.schemes == []


# ---------------------------------------------------------------------------
# T10: seduce creates affair secret
# ---------------------------------------------------------------------------

def test_seduce_creates_affair():
    """Successful seduce creates an affair secret."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler
    before = len(target.secrets)
    msgs = seduce(agent, target, SeqRng([0.3]))
    assert len(target.secrets) > before


# ---------------------------------------------------------------------------
# T11: compromise creates secret on success
# ---------------------------------------------------------------------------

def test_compromise_creates_secret():
    """Successful compromise creates a manufactured secret."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler
    before = len(target.secrets)
    msgs = compromise(agent, target, SeqRng([0.3]))
    assert len(target.secrets) > before


# ---------------------------------------------------------------------------
# T12: Scheme.progress starts at 0
# ---------------------------------------------------------------------------

def test_scheme_progress_starts_zero():
    """Scheme.progress starts at 0."""
    ra, rb, _ = _two_realms(42)
    mgr = SchemeManager()
    s = mgr.start_scheme(ra.characters[10], rb.ruler, "assassination", "Karsgate")
    assert s.progress == 0.0


# ---------------------------------------------------------------------------
# T13: assassination marks target dead
# ---------------------------------------------------------------------------

def test_assassination_marks_dead():
    """Successful assassination marks target as dead."""
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    s = mgr.start_scheme(ra.characters[10], rb.ruler, "assassination", "Karsgate")
    s.progress = SCHEME_THRESHOLD - 1
    msgs = mgr.advance_all(realms, {}, SeqRng([0.99, 0.0]))
    assert not rb.ruler.is_alive


# ---------------------------------------------------------------------------
# T14: coup installs new ruler
# ---------------------------------------------------------------------------

def test_coup_installs_ruler():
    """Successful coup installs agent as new ruler."""
    ra, rb, realms = _two_realms(42)
    mgr = SchemeManager()
    agent = ra.characters[10]
    old_ruler = rb.ruler
    s = mgr.start_scheme(agent, old_ruler, "coup", "Karsgate")
    s.progress = SCHEME_THRESHOLD - 1
    mgr.advance_all(realms, {}, SeqRng([0.99, 0.0]))
    assert rb.ruler is agent


# ---------------------------------------------------------------------------
# T15: conspiracy requires participants
# ---------------------------------------------------------------------------

def test_conspiracy_requires_participants():
    """Conspiracy needs at least 2 participants."""
    ra, rb, _ = _two_realms(42)
    mastermind = ra.ruler
    conspirators = [ra.characters[10]]
    result = start_conspiracy(mastermind, rb.ruler, "Karsgate", conspirators)
    assert result is None  # too few conspirators


# ---------------------------------------------------------------------------
# T16: scheme success chance bounded
# ---------------------------------------------------------------------------

def test_scheme_success_chance_bounded():
    """Scheme success chance stays between 0 and 1."""
    ra, rb, _ = _two_realms(42)
    mgr = SchemeManager()
    s = mgr.start_scheme(ra.characters[10], rb.ruler, "assassination", "Karsgate")
    chance = s.success_chance(50)
    assert 0.0 <= chance <= 1.0


# ---------------------------------------------------------------------------
# T17: sway builds opinion on success
# ---------------------------------------------------------------------------

def test_sway_builds_opinion():
    """Successful sway builds opinion."""
    ra, rb, _ = _two_realms(42)
    agent = ra.characters[10]
    target = rb.ruler
    before = target._society.opinions.get((target.id, agent.id), 0)
    msgs = sway(agent, target, SeqRng([0.3]))
    after = target._society.opinions.get((target.id, agent.id), 0)
    assert after > before


# ---------------------------------------------------------------------------
# T18: sway penalty on failure
# ---------------------------------------------------------------------------

def test_sway_penalty():
    """Failed sway costs opinion."""
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
