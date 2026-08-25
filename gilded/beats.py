"""Mission C1 - the sim becomes visible: consequence beats.

`beats(game, house)` turns the chassis event log of the last resolved turn
into named consequence beats - the moments where the world bit back: a
strike opens, a strike stands down, a union is born, dividends land in
the treasury. Every beat carries its provenance: the turn it fired, the
rule that produced it (`source`), and the Causes that explain its effect
(`causes`), so a player watching can say *why* anything changed.

Pure and deterministic: no RNG, no mutation, no pygame. It reads the same
state the papers read, so the beats and the broadsheet never disagree.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from gilded.provenance import Cause

_STRIKE_MARKER = "STRIKE in "
_STRIKE_ENDS_MARKER = "stands down"
_UNION_MARKER = "organize"
_DIVIDENDS_MARKER = "Dividends: "


@dataclass(frozen=True)
class Beat:
    turn: int
    kind: str              # "strike" | "strike_ends" | "union" | "dividends"
    house: str
    text: str
    source: str            # the rule that fired, as a dotted path
    causes: tuple          # Causes explaining the beat's effect


def _province_of(game, text: str):
    """Find the province named in an event line: longest name that
    appears, so 'Harlow' doesn't win over 'Harlow Fells'."""
    names = sorted((p.name for p in game.atlas.provinces.values()),
                   key=len, reverse=True)
    for name in names:
        if name in text:
            return next(p for p in game.atlas.provinces.values()
                        if p.name == name)
    return None


def _owner_of(game, province, house: str) -> str:
    """The House whose enterprise is squeezed in that province; the
    province's owner when no enterprise sits there."""
    for e in game.enterprises:
        if e.province == province.pid and e.house == house:
            return e.house
    for e in game.enterprises:
        if e.province == province.pid:
            return e.house
    return province.owner


def _journal_causes(game, house: str, turn: int) -> tuple:
    """The treasury journal's named entries for the turn: each line is a
    Cause, so the beat's effect sums exactly to what landed."""
    entries = [(label, amt) for t, label, amt in
               game.houses[house].journal if t == turn]
    return tuple(Cause(label, amt, "houses.House.journal")
                 for label, amt in entries)


def beats(game, house: str, turn: Optional[int] = None) -> List[Beat]:
    """The consequence beats for one House.

    `turn=None` means the last resolved turn (the events currently in the
    chassis log). The house argument scopes the ledger beats; gazette beats
    name the House whose enterprise or province was hit, so a strike in a
    rival's province is visible to you but attributed to them.
    """
    if turn is None:
        turn = game.resolved_turn
    out: List[Beat] = []
    for e in game.events:
        if e.register == "gazette":
            if e.text.startswith(_STRIKE_MARKER):
                prov = _province_of(game, e.text)
                if prov is None:
                    continue
                owner = _owner_of(game, prov, house)
                out.append(Beat(
                    turn, "strike", owner, e.text,
                    "society.labor.tick_movement",
                    (Cause(f"{prov.name} strikes", 0.0,
                           "society.labor.Movement.state"),)))
            elif _STRIKE_ENDS_MARKER in e.text:
                prov = _province_of(game, e.text)
                owner = _owner_of(game, prov, house) if prov else ""
                out.append(Beat(
                    turn, "strike_ends", owner, e.text,
                    "society.labor.tick_movement",
                    (Cause(f"{prov.name} stands down", 0.0,
                           "society.labor.Movement.state"),)
                    if prov else ()))
            elif _UNION_MARKER in e.text:
                prov = _province_of(game, e.text)
                owner = _owner_of(game, prov, house) if prov else ""
                out.append(Beat(
                    turn, "union", owner, e.text,
                    "society.labor.tick_movement",
                    (Cause(f"{prov.name} organizes", 0.0,
                           "society.labor.Movement.state"),)
                    if prov else ()))
        if e.register == "ledger" and e.house == house \
                and e.text.startswith(_DIVIDENDS_MARKER):
            out.append(Beat(
                turn, "dividends", house, e.text,
                "houses.House.credit",
                _journal_causes(game, house, turn)))
    return out


def beats_for(game, house: str) -> List[Beat]:
    """Alias for `beats` on the last resolved turn - the player's view."""
    return beats(game, house)
