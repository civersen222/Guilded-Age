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
from typing import Dict, List, Optional

from gilded.provenance import Attributed, Cause

_STRIKE_MARKER = "STRIKE in "
_STRIKE_ENDS_MARKER = "stands down"
_UNION_MARKER = "organize"
_DIVIDENDS_MARKER = "Dividends: "


@dataclass(frozen=True)
class Beat:
    turn: int
    kind: str              # "signature" | "season" | "inquiry" | "deflection"
    house: str
    text: str
    source: str            # the rule that fired, as a dotted path
    causes: tuple          # Causes explaining the beat's effect
    face: Optional[str] = None          # a person, when the world bit back
    provenance: Optional[Attributed] = None
    facet: str = ""             # the domain word (dividends/strike/union/...)


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


def _owner_of(game, province, house: Optional[str]) -> str:
    """The House whose enterprise is squeezed in that province; the
    province's owner when no enterprise sits there. When `house` is None
    (the public view) the first enterprise in the province wins."""
    for e in game.enterprises:
        if e.province == province.pid and (house is None or e.house == house):
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


def beats(game, house: Optional[str] = None, turn: Optional[int] = None,
          ) -> List[Beat]:
    """The consequence beats for one House, or for every House when
    `house` is None - the public view.

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
                    turn, "season", owner, e.text,
                    "society.labor.tick_movement",
                    (Cause(f"{prov.name} strikes", 0.0,
                           "society.labor.Movement.state"),),
                    facet="strike"))
            elif _STRIKE_ENDS_MARKER in e.text:
                prov = _province_of(game, e.text)
                owner = _owner_of(game, prov, house) if prov else ""
                out.append(Beat(
                    turn, "season", owner, e.text,
                    "society.labor.tick_movement",
                    (Cause(f"{prov.name} stands down", 0.0,
                           "society.labor.Movement.state"),)
                    if prov else (),
                    facet="strike_ends"))
            elif _UNION_MARKER in e.text:
                prov = _province_of(game, e.text)
                owner = _owner_of(game, prov, house) if prov else ""
                out.append(Beat(
                    turn, "season", owner, e.text,
                    "society.labor.tick_movement",
                    (Cause(f"{prov.name} organizes", 0.0,
                           "society.labor.Movement.state"),)
                    if prov else (),
                    facet="union"))
        if e.register == "ledger" and (house is None or e.house == house) \
                and e.text.startswith(_DIVIDENDS_MARKER):
            out.append(Beat(
                turn, "season", e.house, e.text,
                "houses.House.credit",
                _journal_causes(game, e.house, turn),
                facet="dividends"))
    return out


def beats_for(game, house: str) -> List[Beat]:
    """Alias for `beats` on the last resolved turn - the player's view."""
    return beats(game, house)


def _treasury_delta(game, house: str, turn: int) -> tuple:
    """The house's treasury delta for `turn` as an Attributed whose named
    journal lines are the Causes - so `check()` holds by construction."""
    house_obj = game.houses[house]
    lines = [(label, amt) for t, label, amt in house_obj.journal if t == turn]
    if not lines:
        return None
    value = sum(amt for _label, amt in lines)
    causes = tuple(Cause(label, amt, "houses.House.journal")
                   for label, amt in lines)
    return (f"{house}.treasury",
            Attributed(value=value, previous=0.0, causes=causes))


def turn_deltas(game, turn: int) -> List[tuple]:
    """EVERY player-visible numeric delta for `turn`, labelled: one
    (label, Attributed) pair per House with journal activity that turn."""
    out: List[tuple] = []
    for house in sorted(game.houses):
        pair = _treasury_delta(game, house, turn)
        if pair is not None:
            out.append(pair)
    return out


# --- C6: onboarding - the cold-open player learns the verbs in prose ----
# facet -> (prose, dotted source). Each names its verb and what it is for.
_ONBOARDING = {
    "win": ("You rule the {house} House for a budgeted century. The world "
            "closes on you when the last turn is spent or your mandate ends - "
            "win by outlasting the century with a prosperous, loyal House; "
            "the Epilogue judges your standing on four axes.",
            "endings.check_ending"),
    "orders": ("Four Orders rule the realm - Bank, Church, Gazette, Combine - "
               "each with a head who holds a private want. Hold an Order's "
               "seat with hold_seat() and its honest lever plays in your "
               "House's favour; leave it unheld and it presses against you.",
            "orders.tick_orders"),
    "ambitions": ("Declare your House's stake with set_ambition(): a target "
                  "and a family's private wants. The banner's clock then "
                  "counts the turns you have to commit it.",
            "ambitions.AmbitionsFacade.status"),
    "war": ("Houses wage war over borders. A front between your provinces "
            "bleeds garrisons and gold every turn it stands; negotiate peace "
            "when the score swings your way. The Atlas shows every front.",
            "fronts.War"),
    "turn": ("Each press of end_turn() advances the world a season: "
             "dividends credit, the Orders re-aim, the rival Houses read the "
             "morning paper. The century is budgeted - spend the turns on "
             "intention, not waiting.",
            "chassis.end_turn"),
}

_ONBOARD_ORDER = ("win", "orders", "ambitions", "war", "turn")


def _player_house(game):
    return next((h for h in game.houses if game.houses[h].is_player), None)


# --- C6: the three long chains, one per act ------------------------------
# Each watches real state and lands three beats - the situation arrives,
# escalates, and resolves with a measured consequence the Epilogue can name.
def _province_stats(game, player):
    provs = game.provinces_of(player)
    unrest = [p.unrest for p in provs]
    worst = max(provs, key=lambda p: (p.unrest, -p.pid)) if provs else None
    garrison = sum(p.garrison for p in provs)
    return provs, (sum(unrest) / len(unrest) if unrest else 0.0), worst, garrison


def _enterprise_lines(game, base, house, stage):
    ents = [e for e in game.enterprises if e.house == house]
    provs, _, _, _ = _province_stats(game, house)
    if stage == 1:
        base["gold"] = house.treasury
        text = (f"Your {len(ents)} enterprises open their ledgers across "
                f"{len(provs)} provinces; the treasury stands at "
                f"{house.treasury:.0f} gold.")
        source = "treasury.treasury"
    elif stage == 2:
        delta = house.treasury - base["gold"]
        text = (f"The dividends compound: {delta:+.0f} gold since the ledgers "
                f"opened, the treasury at {house.treasury:.0f}.")
        source = "treasury.dividends"
    else:
        text = (f"Your enterprises stand at {len(ents)} houses in "
                f"{len(provs)} provinces; {house.treasury:.0f} gold in hand "
                f"for the quarter's reckoning.")
        source = "treasury.treasury"
    return text, source


def _labor_lines(game, base, house, stage):
    provs, avg, worst, _ = _province_stats(game, house)
    movements = [mv for mv in getattr(game, "movements", []) or []
                 if getattr(mv, "state", "") == "striking"]
    if stage == 1:
        base["unrest"] = avg
        text = (f"Your {len(provs)} provinces rest at {avg:.2f} unrest; "
                f"{len(movements)} movement(s) are striking.")
        source = "society.labor.Movement.state"
    elif stage == 2:
        text = (f"The labour mood has moved {avg - base['unrest']:+.2f} "
                f"since your provinces first settled; {len(movements)} "
                f"movement(s) strike.")
        source = "society.labor.tick_movement"
    else:
        worst_name = worst.name if worst is not None else "no province"
        text = (f"The labour balance settles at {avg:.2f} unrest; the "
                f"Orders' eyes fall hardest on {worst_name}.")
        source = "society.labor.Movement.state"
    return text, source


def _war_lines(game, base, house, stage):
    wars = list(game.wars)
    fronts = sum(len(w.fronts) for w in wars)
    _, _, _, garrison = _province_stats(game, house)
    score = sum(w.war_score for w in wars) / len(wars) if wars else 0.0
    if stage == 1:
        base["wars"] = len(wars)
        text = (f"{len(wars)} war(s) rage across the realm; {fronts} front(s) "
                f"stand open.")
        source = "fronts.War"
    elif stage == 2:
        text = (f"The fronts stand at a mean score of {score:+.0f} against "
                f"your {garrison} garrisoned troops.")
        source = "fronts.War.war_score"
    else:
        text = (f"The century's wars close at a mean score of {score:+.0f}; "
                f"{len(wars)} war(s) still rage, {garrison} troops mustered.")
        source = "fronts.War"
    return text, source


# chain id -> (arrival, escalation, resolution, lines function)
_CHAIN_ACTS = (
    ("enterprise", 2, 12, 24, _enterprise_lines),
    ("labor", 26, 38, 49, _labor_lines),
    ("war", 51, 60, 69, _war_lines),
)


class BeatsFacade:
    """`game.beats` - the beat log as an object the UI and the gate consume
    directly.

    - `.log`: every beat so far (signature acts, season headlines, deflections)
    - `.deltas(turn)`: every named numeric delta for that turn
    - `.inquire(label, turn)`: the "why?" chain behind one delta
    - `.end_turn_close(game)`: called by the chassis at turn end - records the
      season headline beats and the world's deflections against the player
    - callable like the old `beats()` function: last turn's season beats
    """

    def __init__(self, game):
        self.game = game
        self.log: List[Beat] = []
        self._deltas: Dict[int, List[tuple]] = {}
        self._known_movements = set()
        self._chain_base: Dict[str, Dict[str, float]] = {}
        self._chain_stage: Dict[str, int] = {}

    # --- callable compatibility (game.beats(house) == beats_for(game, house))
    def __call__(self, house: Optional[str] = None,
                 turn: Optional[int] = None) -> List[Beat]:
        return beats(self.game, house, turn)

    def deltas(self, turn: int) -> List[tuple]:
        return list(self._deltas.get(turn, []))

    def inquire(self, label: str, turn: int) -> Attributed:
        """The "why?" chain: the Attributed behind a named delta."""
        for lbl, att in self._deltas.get(turn, []):
            if lbl == label:
                if att.causes:
                    return att
                return Attributed(value=att.value, previous=att.previous,
                                  causes=(Cause(label, att.value,
                                                "houses.House.journal"),))
        # no recorded delta (e.g. a turn before close): materialize it now
        for house in sorted(self.game.houses):
            if label.startswith(f"{house}.treasury"):
                pair = _treasury_delta(self.game, house, turn)
                if pair is not None:
                    self._deltas.setdefault(turn, []).append(pair)
                    return pair[1]
        raise KeyError(f"no delta {label!r} on turn {turn}")

    def append(self, beat: Beat) -> None:
        self.log.append(beat)

    def end_turn_close(self) -> None:
        """Record the just-resolved turn: season headlines, deltas, and the
        deflections - the world thwarting the player, always with a face."""
        game = self.game
        turn = game.resolved_turn
        if turn is None:
            return
        for b in beats(game, None, turn):
            self.append(b)
        self._deltas[turn] = turn_deltas(game, turn)
        # the "why?" answers: every materialised delta answers with Causes
        for label, att in self._deltas[turn]:
            self.append(Beat(
                turn, "inquiry", "",
                f"why {label}: {sum(c.amount for c in att.causes):.0f}",
                "beats.turn_deltas",
                att.causes, None, att))
        self._scan_deflections(turn)
        # C6: the cold-open player is taught, and the world's long chains run
        self._emit_onboarding(game, turn)
        self._emit_chains(game, turn)

    # --- C6: onboarding, then the three long chains -----------------------
    def _emit_onboarding(self, game, turn: int) -> None:
        """The first five turns each teach one verb, in a stranger's prose.
        Each facet fires once, on the turn it is due, from the player's
        own state."""
        if turn > 5:
            return
        player = _player_house(game)
        if player is None:
            return
        facet = _ONBOARD_ORDER[turn - 1]
        if any(b.kind == "onboarding" and b.facet == facet for b in self.log):
            return
        text, source = _ONBOARDING[facet]
        text = text.format(house=game.houses[player].name if hasattr(game.houses[player], "name") else player)
        self.append(Beat(
            turn, "onboarding", player, text, source,
            (Cause(f"teaching the {facet} verb", 0.0, source),),
            None, None, facet=facet))

    def _emit_chains(self, game, turn: int) -> None:
        """Three chains, one per act: a situation arrives, escalates, and
        resolves - each a real measurement of the player's own House, so the
        Epilogue can name the consequence. A stage fires once at its turn."""
        player = _player_house(game)
        if player is None:
            return
        house = game.houses[player]
        for chain_id, t1, t2, t3, lines_fn in _CHAIN_ACTS:
            if turn == t1:
                stage = 1
            elif turn == t2:
                stage = 2
            elif turn == t3:
                stage = 3
            else:
                continue
            if self._chain_stage.get(chain_id) == stage:
                continue
            self._chain_stage[chain_id] = stage
            base = self._chain_base.setdefault(chain_id, {})
            text, source = lines_fn(game, base, house, stage)
            self.append(Beat(
                turn, "chain", player, text, source,
                (Cause(f"{chain_id} chain, {stage} of 3", 0.0, source),),
                None, None, facet=chain_id))

    # --- deflections: the world thwarts the player, never silently --------
    def _scan_deflections(self, turn: int) -> None:
        game = self.game
        player = next((h for h in game.houses if game.houses[h].is_player),
                      None)
        if player is None:
            return
        for ent in game.enterprises:
            if ent.house != player:
                continue
            prov = game.atlas.provinces.get(ent.province)
            if prov is None:
                continue
            mv = getattr(prov, "movement", None)
            if mv is None or mv.leader is None:
                continue
            leader = mv.leader
            leader_name = getattr(leader, "name", leader)
            if prov.pid not in self._known_movements:
                self._known_movements.add(prov.pid)
                self.append(Beat(
                    turn=turn, kind="deflection", house=player,
                    text=(f"{leader_name} organizes the {prov.name} workers "
                          f"against your squeeze of {ent.name}"),
                    source="society.labor.Movement",
                    causes=(Cause(f"{prov.name} movement formed", 0.0,
                                  "society.labor.Movement.state"),),
                    face=leader_name,
                    provenance=Attributed(
                        value=0.0, previous=0.0,
                        causes=(Cause(f"{prov.name} movement formed", 0.0,
                                      "society.labor.Movement.state"),)),
                ))
            elif mv.state == "striking":
                self.append(Beat(
                    turn=turn, kind="deflection", house=player,
                    text=(f"Your extraction at {ent.name} is halted by the "
                          f"{prov.name} strike under {leader_name}"),
                    source="society.labor.Movement.state",
                    causes=(Cause(f"{prov.name} strike", 0.0,
                                  "society.labor.Movement.state"),),
                    face=leader_name,
                    provenance=Attributed(
                        value=0.0, previous=0.0,
                        causes=(Cause(f"{prov.name} strike", 0.0,
                                      "society.labor.Movement.state"),)),
                ))
