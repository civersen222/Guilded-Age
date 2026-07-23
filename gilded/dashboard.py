"""Stage 1 read-model (the Frame): the live scoreboard for one House.

`scoreboard(game, house)` computes the four judgment axes, the Tide, the era,
the treasury/legitimacy, and where the House ranks — all by *reading* the game,
never mutating it. It reuses `endings._axis_*` so the mid-game meters are the
exact numbers the final judgment reports. `delta(prev, curr)` diffs two boards
for the "Since last session" feed. Pure and deterministic: no RNG, no pygame,
no game mutation. The UI consumes it exactly as it consumes `papers.compose`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from gilded.chassis import TURN_BUDGET, year_of
from gilded.endings import (
    _axis_blood, _axis_capital, _axis_standing, _axis_world)
from gilded.saga.content.eras import ERAS

AXIS_NAMES = ("capital", "standing", "blood", "world")


@dataclass(frozen=True)
class Scoreboard:
    year: int
    turn: int
    century_pct: float
    era_idx: int
    era_title: str
    next_era: str
    axes: Dict[str, float]
    legitimacy: float
    prestige: float
    treasury: float
    tide_level: float
    tide_phase: str
    atrocities: float
    rival_name: Optional[str]
    rival_axes: Optional[Dict[str, float]]
    rank: int
    unrest_avg: float


def _axes_for(game, house_name: str) -> Dict[str, float]:
    return {
        "capital": _axis_capital(game, house_name),
        "standing": _axis_standing(game, house_name),
        "blood": _axis_blood(game, house_name)[0],
        "world": _axis_world(game, house_name)[0],
    }


def _composite(axes: Dict[str, float]) -> float:
    return sum(axes[k] for k in AXIS_NAMES) / len(AXIS_NAMES)


def _era_fields(game):
    idx = game.director.age_idx
    if idx < 0:
        title = "Before the Age"
    elif idx < len(ERAS):
        title = ERAS[idx].title
    else:
        title = ERAS[-1].title
    nxt = idx + 1
    if 0 <= nxt < len(ERAS):
        e = ERAS[nxt]
        hint = f"Next: {e.title} at tide {e.tide:.0f} or turn {e.turn}"
    else:
        hint = "the final age"
    return idx, title, hint


def scoreboard(game, house_name: str) -> Scoreboard:
    axes = _axes_for(game, house_name)

    # Rank all houses by composite (descending), ties broken by name ascending.
    order = [
        h for _neg, h in sorted(
            ((-_composite(_axes_for(game, h)), h) for h in game.houses),
            key=lambda t: (t[0], t[1]))
    ]
    rank = order.index(house_name) + 1

    rival = game.director.rival
    rival_axes = _axes_for(game, rival) if rival else None

    provs = game.provinces_of(house_name)
    unrest_avg = (sum(p.unrest for p in provs) / len(provs)) if provs else 0.0

    era_idx, era_title, next_era = _era_fields(game)
    house = game.houses[house_name]
    return Scoreboard(
        year=year_of(game.turn),
        turn=game.turn,
        century_pct=max(0.0, min(1.0, game.turn / TURN_BUDGET)),
        era_idx=era_idx,
        era_title=era_title,
        next_era=next_era,
        axes=axes,
        legitimacy=game.legitimacy.get(house_name, 0.0),
        prestige=house.prestige,
        treasury=house.treasury,
        tide_level=game.tide.level,
        tide_phase=game.tide.phase(),
        atrocities=game.tide.atrocities,
        rival_name=rival,
        rival_axes=rival_axes,
        rank=rank,
        unrest_avg=unrest_avg,
    )


@dataclass(frozen=True)
class MetricDelta:
    change: float
    direction: int   # -1 fell, 0 flat, +1 rose


@dataclass(frozen=True)
class Delta:
    first_session: bool
    axes: Dict[str, MetricDelta]
    legitimacy: MetricDelta
    treasury: MetricDelta
    tide_level: MetricDelta
    unrest_avg: MetricDelta
    rank: MetricDelta


def _md(prev: float, curr: float) -> MetricDelta:
    change = curr - prev
    direction = (change > 0) - (change < 0)
    return MetricDelta(change, direction)


def delta(prev: Optional[Scoreboard], curr: Scoreboard) -> Delta:
    if prev is None:
        zero = MetricDelta(0.0, 0)
        return Delta(True, {k: zero for k in AXIS_NAMES},
                     zero, zero, zero, zero, zero)
    return Delta(
        False,
        {k: _md(prev.axes[k], curr.axes[k]) for k in AXIS_NAMES},
        _md(prev.legitimacy, curr.legitimacy),
        _md(prev.treasury, curr.treasury),
        _md(prev.tide_level, curr.tide_level),
        _md(prev.unrest_avg, curr.unrest_avg),
        # rank is 1 = best; a negative change means standing improved.
        _md(float(prev.rank), float(curr.rank)),
    )