"""Mission C1 - the sim becomes visible: the public ladder.

`ladder(game)` ranks every House by the same composite of the four judgment
axes that `dashboard.scoreboard` and `endings.judge` weigh, so the ladder is
the mid-game number the final judgment reports. Every axis value ships with
its provenance: one Cause per named contribution (treasury, enterprise
stakes, legitimacy, court strain, tide, unrest, welfare...), and a residual
scale/clamp cause so the Causes always sum exactly to the value
(`Attributed.check()` holds by construction). The rank-1 House is the one
winning; the causes say why.

Pure and deterministic: no RNG, no mutation, no pygame. The UI and the
papers consume it exactly as they consume `dashboard.scoreboard`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List

from gilded.endings import (
    AXES, _axis_blood, _axis_capital, _axis_standing, _axis_world,
    _house_wealth, WELFARE_DIAL)
from gilded.provenance import Attributed, Cause


def _capital(game, house_name: str) -> Attributed:
    value = _axis_capital(game, house_name)
    wealth = _house_wealth(game, house_name)
    treasury = game.houses[house_name].treasury
    causes = [
        Cause(f"treasury {treasury:.0f} gold", treasury,
              "houses.House.treasury"),
        Cause(f"enterprise stakes {wealth - treasury:.0f}",
              wealth - treasury, "endings._house_wealth"),
        Cause("scaled to the world's best",
              value - treasury - (wealth - treasury),
              "endings._axis_capital"),
    ]
    return Attributed(value, 0.0, tuple(causes))


def _standing(game, house_name: str) -> Attributed:
    value = _axis_standing(game, house_name)
    house = game.houses[house_name]
    rel = list(house.relations.values())
    mean_rel = sum(rel) / len(rel) if rel else 0.0
    legit = 0.5 * game.legitimacy.get(house_name, 0.0)
    prest = 0.25 * (50.0 + house.prestige / 4.0)
    relation = 0.25 * (50.0 + mean_rel / 2.0)
    causes = [
        Cause(f"legitimacy {legit:.1f}", legit,
              "chassis.GildedGame.legitimacy"),
        Cause(f"prestige {prest:.1f}", prest, "houses.House.prestige"),
        Cause(f"relations {relation:.1f}", relation,
              "houses.House.relations"),
        Cause("clamped to the scale", value - legit - prest - relation,
              "endings._axis_standing"),
    ]
    return Attributed(value, 0.0, tuple(causes))


def _blood(game, house_name: str) -> Attributed:
    axis, living, _members, burden, heir = _axis_blood(game, house_name)
    if not living:
        causes = (Cause("no living members", 0.0, "endings._axis_blood"),)
    else:
        line = 8.0 * len(living)
        strain = -burden / 4.0
        successor = 15.0 if heir else 0.0
        causes = (
            Cause(f"{len(living)} living members", line,
                  "endings._axis_blood"),
            Cause(f"court strain {strain:.1f}", strain,
                  "endings._axis_blood"),
        )
        if heir:
            causes = causes + (Cause("an heir stands behind the ruler",
                                     successor, "endings._axis_blood"),)
        causes = causes + (
            Cause("clamped to the scale",
                  axis - line - strain - successor,
                  "endings._axis_blood"),)
    return Attributed(axis, 0.0, causes)


def _world(game, house_name: str) -> Attributed:
    value, _unrest = _axis_world(game, house_name)
    provs = game.provinces_of(house_name)
    unrest = (sum(p.unrest for p in provs) / len(provs)) if provs else 0.0
    ents = [e for e in game.enterprises if e.house == house_name]
    welfare = (sum(max(0.0, WELFARE_DIAL - e.extraction_dial) for e in ents)
               / len(ents)) if ents else 0.0
    tide_cost = -game.tide.level
    atrocity_cost = -2.0 * game.tide.house_atrocities.get(house_name, 0.0)
    causes = [
        Cause("a clean world", 100.0, "endings._axis_world"),
        Cause(f"the tide at {game.tide.level:.1f}", tide_cost,
              "chassis.GildedGame.tide"),
        Cause(f"atrocities {game.tide.house_atrocities.get(house_name, 0.0):.0f}",
              atrocity_cost, "ideology.IdeologicalTide.record_atrocity"),
        Cause(f"unrest {unrest:.1f}", -unrest, "society.labor.unrest_gain"),
        Cause(f"welfare {welfare / 4.0:.1f}", welfare / 4.0,
              "enterprises.ExtractionDial"),
        Cause("clamped to the scale",
              value - (100.0 + tide_cost + atrocity_cost - unrest
                       + welfare / 4.0), "endings._axis_world"),
    ]
    return Attributed(value, 0.0, tuple(causes))


_AXIS_BUILDERS = {
    "capital": _capital,
    "standing": _standing,
    "blood": _blood,
    "world": _world,
}


@dataclass(frozen=True)
class LadderRow:
    rank: int
    house: str
    composite: float
    axes: Dict[str, Attributed]

    def causes(self, axis: str) -> tuple:
        return self.axes[axis].causes


def ladder(game) -> List[LadderRow]:
    """Every House ranked by composite of the four judgment axes.

    Rank 1 is the House winning the age. Ties break by name ascending,
    exactly as `dashboard.scoreboard` ranks them, so the public ladder and
    the private scoreboard never disagree.
    """
    rows: List[LadderRow] = []
    for h in game.houses:
        axes = {name: _AXIS_BUILDERS[name](game, h) for name in AXES}
        composite = sum(a.value for a in axes.values()) / len(axes)
        rows.append(LadderRow(0, h, composite, axes))
    rows.sort(key=lambda r: (-r.composite, r.house))
    return [replace(r, rank=i + 1) for i, r in enumerate(rows)]


def leader(game) -> LadderRow:
    """The House winning the age right now, with the causes that say why."""
    return ladder(game)[0]


class LadderFacade:
    """`game.ladder` - callable like `ladder(game)` (full LadderRows with
    Attributed axes) and also exposing `.standings()`, the plain public
    view: one (house, rank, axes-as-plain-floats) row per House, 1..N."""

    def __init__(self, game):
        self.game = game

    def __call__(self):
        return ladder(self.game)

    def standings(self) -> List[tuple]:
        rows = ladder(self.game)
        return [(r.house, r.rank, {k: ax.value for k, ax in r.axes.items()})
                for r in rows]
