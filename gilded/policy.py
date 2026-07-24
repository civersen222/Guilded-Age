"""Stage 3 read-model (Policy Dials): the standing consequence of one House's
five directive stances. `effects(game, house)` maps the -100..+100 stances on
capital/labor/expansion/diplomacy/war to a frozen PolicyEffects the turn loop
applies and the Policies tab displays. Pure and deterministic: it never mutates
the game and never touches game.rng. The labor dial is realized as a house-wide
extraction level written into each enterprise's existing dial, so all the
society.labor curves (and the endings blood axis) keep working unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from gilded.directives import DIRECTIVE_KEYS


@dataclass(frozen=True)
class PolicyEffects:
    extraction_level: int
    output_mod: float
    build_speed_mod: float
    expand_cost_mod: float
    strength_mod: float
    happiness_mod: float
    legitimacy_mod: float
    relations_drift: float
    trade_income: float
    unrest_add: float


NEUTRAL = PolicyEffects(
    extraction_level=50, output_mod=1.0, build_speed_mod=1.0,
    expand_cost_mod=1.0, strength_mod=1.0, happiness_mod=0.0,
    legitimacy_mod=0.0, relations_drift=0.0, trade_income=0.0, unrest_add=0.0)


def _t(stances, key: str) -> float:
    return max(-100, min(100, int(stances.get(key, 0)))) / 100.0


def effects(game, house_name: str) -> PolicyEffects:
    """Pure: the standing effects of `house_name`'s current dial stances."""
    directives = game.directives.get(house_name)
    if directives is None:
        return NEUTRAL
    st = directives.stances
    tl = _t(st, "labor")
    tc = _t(st, "capital")
    te = _t(st, "expansion")
    tw = _t(st, "war")
    td = _t(st, "diplomacy")
    extraction_level = max(0, min(100, round(50 + 50 * tl)))
    happiness_mod = -5.0 * tw + (3.0 * (-td) if td < 0 else 0.0)
    legitimacy_mod = 1.5 * (-td) if td < 0 else 0.0
    unrest_add = 1.0 * te + (-0.5 * (-tc) if tc < 0 else 0.0)
    return PolicyEffects(
        extraction_level=extraction_level,
        output_mod=1.0 + 0.15 * tc,
        build_speed_mod=1.0 + 0.3 * tc,
        expand_cost_mod=1.0 - 0.2 * te,
        strength_mod=1.0 + 0.25 * tw,
        happiness_mod=happiness_mod,
        legitimacy_mod=legitimacy_mod,
        relations_drift=2.0 * td,
        trade_income=2.0 * td if td > 0 else 0.0,
        unrest_add=unrest_add,
    )
