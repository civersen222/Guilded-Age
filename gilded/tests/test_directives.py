"""Tests for gilded.directives (mission G5)."""

import random

from gilded.directives import (
    DIRECTIVE_CONVICTION,
    DIRECTIVE_KEYS,
    FRICTION_STRESS,
    FRICTION_THRESHOLD,
    RESIGN_FRICTION_TURNS,
    Directives,
    friction,
    tick_friction,
)
from gilded.society.characters import Character, SocietyState


def _char(name="Sec"):
    random.seed(11)
    rng = random.Random(11)
    society = SocietyState(rng)
    return Character(name=name, stats={}, traits=[], age=45, gender="Male", society=society)


def test_default_stances_zero():
    d = Directives()
    assert set(d.stances) == set(DIRECTIVE_KEYS)
    assert all(v == 0 for v in d.stances.values())
    assert set(DIRECTIVE_CONVICTION) == set(DIRECTIVE_KEYS)


def test_set_stance_clamps_and_resets_friction():
    d = Directives()
    d.friction_turns["war"] = 3
    d.set_stance("war", 250)
    assert d.stances["war"] == 100
    assert d.friction_turns["war"] == 0
    d.set_stance("war", -999)
    assert d.stances["war"] == -100


def test_friction_formula():
    assert friction(100, -80.0) == 100 + 80 - FRICTION_THRESHOLD
    assert friction(0, -80.0) == 80 - FRICTION_THRESHOLD
    assert friction(-60, -80.0) == 0.0
    assert friction(0, 0.0) == 0.0


def test_tick_friction_stresses_conflicted_executor():
    d = Directives()
    d.set_stance("labor", 100)
    c = _char()
    c.dispositions["labor_capital"] = -80.0
    before = c.stress
    events = tick_friction(d, {"labor": c}, random.Random(1))
    assert c.stress == before + FRICTION_STRESS
    assert events == [("labor", "stress")]
    assert d.friction_turns["labor"] == 1


def test_tick_friction_ignores_aligned_and_empty_seats():
    d = Directives()
    c = _char()
    c.dispositions["labor_capital"] = 0.0
    events = tick_friction(d, {"labor": c, "war": None}, random.Random(1))
    assert events == []
    assert c.stress == 0
    assert d.friction_turns["labor"] == 0


def test_resignation_after_sustained_friction():
    d = Directives()
    d.set_stance("war", 100)
    c = _char()
    c.dispositions["militarist_pacifist"] = -90.0
    rng = random.Random(3)
    seen = []
    for _ in range(40):
        for key, what in tick_friction(d, {"war": c}, rng):
            seen.append(what)
            if what == "resigned":
                break
        if "resigned" in seen:
            break
    assert "resigned" in seen
    assert seen.count("stress") >= RESIGN_FRICTION_TURNS - 1
    assert d.friction_turns["war"] == 0
