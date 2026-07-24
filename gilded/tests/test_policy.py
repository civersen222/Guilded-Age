"""Stage 3: policy.effects is a pure read-model over the five dials."""

from gilded.chassis import GildedGame
from gilded import policy
from gilded.society import labor


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
    assert e.expand_cost_mod < 1.0     # expansionist is cheaper to grow
    assert e.strength_mod > 1.0        # militarist is stronger
    assert e.relations_drift > 0.0     # cosmopolitan warms neighbours
    assert e.trade_income > 0.0        # cosmopolitan earns trade
    assert e.happiness_mod < 0.0       # war footing costs contentment


def test_nationalist_diplomacy_returns_home_standing():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, diplomacy=-100)
    e = policy.effects(g, h)
    assert e.happiness_mod > 0.0
    assert e.legitimacy_mod > 0.0
    assert e.relations_drift < 0.0
    assert e.trade_income == 0.0


def test_effects_is_pure():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, labor=80, war=40)
    before = GildedGame(seed=1).rng.random()
    policy.effects(g, h)
    policy.effects(g, h)
    assert before == GildedGame(seed=1).rng.random()  # no rng consumed anywhere
    assert g.directives[h].stances["labor"] == 80      # no mutation of stances


def test_labor_display_matches_curves():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, labor=100)
    lvl = policy.effects(g, h).extraction_level
    # The UI derives the labor line from the same curves at extraction_level.
    assert labor.dividend_multiplier(lvl) == labor.dividend_multiplier(100)
    assert labor.production_multiplier(lvl) == labor.production_multiplier(100)


def test_set_policy_is_deterministic_and_rng_free():
    from gilded.ai import set_policy
    g1 = GildedGame(seed=5)
    g2 = GildedGame(seed=5)
    h = next(x for x in sorted(g1.houses) if not g1.houses[x].is_player)
    before = GildedGame(seed=5).rng.random()
    set_policy(g1, h)
    set_policy(g2, h)
    assert g1.directives[h].stances == g2.directives[h].stances
    assert before == GildedGame(seed=5).rng.random()


def test_set_policy_drifts_toward_target_in_bounded_steps():
    from gilded.ai import set_policy, POLICY_STEP
    g = GildedGame(seed=5)
    h = next(x for x in sorted(g.houses) if not g.houses[x].is_player)
    for k in ("capital", "labor", "expansion", "diplomacy", "war"):
        g.directives[h].set_stance(k, 0)
    set_policy(g, h)
    for k, v in g.directives[h].stances.items():
        assert abs(v) <= POLICY_STEP  # a single step from 0, never a jump


def test_converged_dial_stops_being_reset():
    from gilded.ai import set_policy, _policy_targets, DEAD_BAND
    g = GildedGame(seed=5)
    h = next(x for x in sorted(g.houses) if not g.houses[x].is_player)
    targets = _policy_targets(g, h)
    # Park every dial exactly on target: set_policy must NOT call set_stance
    # (which would reset friction_turns), so a pre-loaded counter survives.
    for k, tgt in targets.items():
        g.directives[h].set_stance(k, tgt)
        g.directives[h].friction_turns[k] = 3
    set_policy(g, h)
    assert all(g.directives[h].friction_turns[k] == 3 for k in targets)
