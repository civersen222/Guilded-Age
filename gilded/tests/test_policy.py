"""Stage 3: policy.effects is a pure read-model over the five dials."""

from gilded.chassis import GildedGame
from gilded import policy


def _set(g, h, **stances):
    for k, v in stances.items():
        g.directives[h].set_stance(k, v)


def test_neutral_is_a_noop():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    e = policy.effects(g, h)
    assert e.extraction_level == 50
    assert e.output_mod == 1.0
    assert e.build_speed_mod == 1.0
    assert e.expand_cost_mod == 1.0
    assert e.strength_mod == 1.0
    assert e.happiness_mod == 0.0
    assert e.legitimacy_mod == 0.0
    assert e.relations_drift == 0.0
    assert e.trade_income == 0.0
    assert e.unrest_add == 0.0


def test_labor_sets_extraction_level_monotonically():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, labor=100)
    assert policy.effects(g, h).extraction_level == 100
    _set(g, h, labor=-100)
    assert policy.effects(g, h).extraction_level == 0
    _set(g, h, labor=50)
    assert policy.effects(g, h).extraction_level == 75


def test_dials_have_correct_signs():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, capital=100, expansion=100, war=100, diplomacy=100)
    e = policy.effects(g, h)
    assert e.output_mod > 1.0          # industrialist lifts output
    assert e.build_speed_mod > 1.0     # industrialist builds faster
    assert e.expand_cost_mod < 1.0     # expansionism lowers founding cost
    assert e.strength_mod > 1.0        # militarist boosts combat
    assert e.happiness_mod > 0.0       # cosmopolitan boosts happiness
    assert e.legitimacy_mod > 0.0      # cosmopolitan boosts legitimacy
    assert e.relations_drift > 0.0     # cosmopolitan improves relations
    assert e.trade_income > 0.0        # expansionism earns trade income
    assert e.unrest_add == 0.0         # labor=0 means no unrest add


def test_extractionist_labor_raises_unrest():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, labor=100)
    assert policy.effects(g, h).unrest_add > 0.0


def test_protective_lower_capital_reduces_output():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, capital=-100)
    e = policy.effects(g, h)
    assert e.output_mod < 1.0
    assert e.build_speed_mod < 1.0


def test_effects_is_pure_no_rng_consumed():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    state = g.rng.getstate()
    _set(g, h, capital=50, labor=30, expansion=-20, diplomacy=80, war=-60)
    e1 = policy.effects(g, h)
    assert g.rng.getstate() == state  # RNG state unchanged
    e2 = policy.effects(g, h)
    assert e1 == e2  # deterministic


def test_effects_is_frozen():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    e = policy.effects(g, h)
    try:
        e.output_mod = 2.0
        assert False, "PolicyEffects should be frozen"
    except Exception:
        pass
