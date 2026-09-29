"""The Four Orders (mission C3 - the world pushes back).

The realm is not just Houses. Four institutions stand alongside the seven
great Houses and push back with the SAME anatomy: a real head (a Character
with the full 30-key disposition set, traits, a private want) and a live
GOAL (an agenda.Goal) that is held across a commit window, rotates through
the Order's OWN goal families, and that stands in the way of a House whose
ambition crosses it (see ambitions._order_clash).

  Combine - labor:   Organize, Recognition, General Strike, Purge Scabs
  Bank    - capital: Solvency, Expansion, Receivership, King-making
  Church  - faith:   Endowment, Crusade of Morals, Sanctuary, Schism
  Gazette - press:   Circulation War, Expose, Respectability, Patronage

Each Order's REACH is a SET - the provinces it presses on (labor presence,
parishes, literate readership) or, for the Bank, the houses in its debt
book. A House that HOLDS an Order's seat is spared the Order's pressure and
gets its honest lever (better loan terms, spared strikes, softer exposes).

Deterministic: goal selection is a pure function of (seed, state) - the
family rotates by turn and the target cycles through the non-seated houses,
so a given seed always yields the same four heads, the same aims, and the
same levers.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from gilded.agenda import COMMIT_TURNS, Goal
from gilded.ambitions import (
    FAMILY_DISPOSITION,
    STANCE_BACKS_AT,
    STANCE_OPPOSES_AT,
    WANT_TEXT,
)
from gilded.beats import Beat, Cause
from gilded.society.characters import Character

# name -> the Order's OWN goal families (the ticker rotates through them),
#         the head's given name, and the head's disposition bent.
_ORDER_SPECS = {
    "Combine": {
        "families": ["Organize", "Recognition",
                     "General Strike", "Purge Scabs"],
        "given": "Halden",
    },
    "Bank": {
        "families": ["Solvency", "Expansion",
                     "Receivership", "King-making"],
        "given": "Maren",
    },
    "Church": {
        "families": ["Endowment", "Crusade of Morals",
                     "Sanctuary", "Schism"],
        "given": "Seraphine",
    },
    "Gazette": {
        "families": ["Circulation War", "Expose",
                     "Respectability", "Patronage"],
        "given": "Corbin",
    },
}

# head disposition profile per Order - a stable, legible bent on the line
# its institution lives on (the base 30-key set comes from the seeded
# society, so a head carries the SAME keys as any House adult).
_ORDER_BIAS = {
    "Combine": {"bold_craven": 30.0, "ambitious_content": 25.0},
    "Bank":    {"generous_greedy": 35.0, "trusting_paranoid": -20.0},
    "Church":  {"honest_deceitful": -30.0, "pious_secular": 30.0},
    "Gazette": {"bold_craven": 25.0, "traditionalist_modernist": 30.0},
}

ORDER_NAMES = tuple(_ORDER_SPECS)

# wave 2 levers - each Order presses a real, deterministic world quantity.
_BANK_DEBT = 50.0          # the Bank extends a loan to the house it aims at
_BANK_SEAT_LOAN = 25.0     # the seat holder's better terms, per tick
_CHURCH_EYES = 0.25        # the eyes of the Church: unrest on the target's capital
_CHURCH_SEAT_RELIEF = 5.0  # the seat holder's tithe relief, per tick
_GAZETTE_EYES = 0.25       # the press: unrest from a hard expose, per province
_GAZETTE_SEAT_PRESTIGE = 0.5  # the seat holder's softer exposes, per tick
_COMBINE_STRIKE = 0.5      # the Combine stirs the mills: unrest per province
_COMBINE_SEAT_PRESTIGE = 0.5  # the seat holder's spared strikes, per tick


def _head_stats(name: str) -> Dict[str, int]:
    base = {"statecraft": 7, "command": 7, "industry": 7,
            "intrigue": 7, "science": 7, "resolve": 7}
    if name == "Combine":
        base["command"] += 3
    elif name == "Bank":
        base["industry"] += 3
    elif name == "Church":
        base["intrigue"] += 3
    elif name == "Gazette":
        base["science"] += 3
    return base


class Order:
    """A first-class institution: a real head with a private want, a live
    goal, a treasury it draws from, and the realm it reaches."""

    def __init__(self, name: str, head: Character, goal: Goal,
                 reach: set) -> None:
        self.name = name
        self.head = head
        self.goal = goal
        self.treasury: float = 0.0
        self.reach: set = reach
        self.journal: List[tuple] = []          # (turn, label, amount)

    def wants(self, family: str) -> List[dict]:
        """The head's private want on `family`, computed exactly as a house
        courtier's is: stance from the head's own disposition on the
        family's line, want text by name, and the disposition it came from.
        Mirrors ambitions.wants so the head has the SAME anatomy as a House
        adult - a model that carries its own .want."""
        key, polarity = FAMILY_DISPOSITION[family]
        value = float(self.head.dispositions.get(key, 0.0)) * polarity
        if value > STANCE_BACKS_AT:
            stance = "backs"
        elif value < STANCE_OPPOSES_AT:
            stance = "opposes"
        else:
            stance = "wary"
        text = f"{self.head.name} {WANT_TEXT[stance][family]}"
        self.head.want = {"text": text, "disposition": key, "stance": stance}
        return [{
            "id": self.head.id,
            "name": self.head.name,
            "age": self.head.age,
            "traits": list(self.head.traits),
            "stance": stance,
            "disposition": key,
            "value": value,
            "text": text,
        }]

    def credit(self, turn: int, label: str, amount: float) -> None:
        if amount < 0:
            raise ValueError("amount must be non-negative")
        self.treasury = self.treasury + amount
        self.journal.append((turn, label, amount))


def _player_of(game) -> Optional[str]:
    return next((h for h in game.houses if game.houses[h].is_player), None)


def _strongest_house(game) -> Optional[str]:
    best, best_val = None, None
    for h in sorted(game.houses):
        val = sum(p.population for p in game.provinces_of(h)) + \
            game.houses[h].treasury
        if best_val is None or val > best_val:
            best, best_val = h, val
    return best


def _richest_house(game) -> Optional[str]:
    best, best_val = None, None
    for h in sorted(game.houses):
        val = game.houses[h].treasury
        if best_val is None or val > best_val:
            best, best_val = h, val
    return best


def _non_seat_houses(game, name: str) -> List[str]:
    """The houses the Order presses on: every house but the seat holder."""
    seat = getattr(game, "order_seats", {}).get(name)
    return [h for h in sorted(game.houses)
            if h != seat and h != _player_of(game)]


def _target_for(game, name: str, family: str) -> Optional[str]:
    """Deterministic target for the Order's goal:
    - Bank's Receivership -> richest house (the debts are where the gold is)
    - Church's Sanctuary  -> the player (the faithful at home)
    - everything else     -> the strongest house.
    A seat-holder house is never a target."""
    seat = getattr(game, "order_seats", {}).get(name)
    if name == "Bank":
        richest = _richest_house(game)
        return None if richest == seat else richest
    if name == "Church":
        player = _player_of(game)
        if player is not None and player != seat:
            return player
        return _strongest_house(game)
    strongest = _strongest_house(game)
    return None if strongest == seat else strongest


def _why(name: str, family: str, target: Optional[str]) -> str:
    return {
        "Organize": f"the laborers of {target} must stand together",
        "Recognition": f"House {target}'s mills must be recognized",
        "General Strike": f"House {target}'s mills will stand still",
        "Purge Scabs": f"the scabs of {target} must be swept out",
        "Solvency": f"the books of {target} must balance",
        "Expansion": f"the Bank's reach must press {target}",
        "Receivership": f"House {target}'s debts are the Bank's to hold",
        "King-making": f"House {target}'s name must buy its crown",
        "Endowment": f"the parishes of {target} want a roof",
        "Crusade of Morals": f"the vices of {target} must be named",
        "Sanctuary": f"House {target}'s fugitives must be sheltered",
        "Schism": f"the faith of {target} is split down the middle",
        "Circulation War": f"the presses of {target} must sell",
        "Expose": f"House {target}'s secrets are for the pages",
        "Respectability": f"the tone of {target} must be corrected",
        "Patronage": f"House {target}'s patrons must be courted",
    }[family]


def _refresh_wants(order: Order) -> None:
    if order.goal is not None:
        order.wants(order.goal.family)


def _refresh_reach(game, orders: Dict[str, "Order"]) -> None:
    """Reach is a SET: the provinces each Order presses on (or the Bank's
    debt-book houses)."""
    for name, order in orders.items():
        if name == "Bank":
            order.reach = {h for h in sorted(game.houses)
                           if h != getattr(game, "order_seats", {}).get(name)
                           and game.houses[h].treasury > 0.0}
        elif name == "Church":
            order.reach = {p.pid for p in game.atlas.provinces.values()}
        else:
            order.reach = {p.pid for p in game.atlas.provinces.values()}


def _press(game, order: Order) -> None:
    """The Order acts: its lever moves a real, deterministic world quantity
    on the House it aims at. A House that HOLDS the Order's seat is spared
    the pressure and receives the Order's honest lever instead - the seat
    moves the world through the lever, never by a direct grant."""
    target = order.goal.target
    if target is None or target not in game.houses:
        return

    def journal(why: str, amount: float, facet: str, amt: float,
                face: Optional[str] = None) -> None:
        if amt <= 0.0:
            return
        game.beats.append(Beat(
            turn=game.turn, kind="signature", house=target,
            text=why, source="orders._press",
            causes=(Cause(why, amt, "orders._press"),),
            face=face if face is not None else order.head.name,
            facet=facet,
        ))

    seat = getattr(game, "order_seats", {}).get(order.name)
    name = order.name
    if name == "Bank":
        amount = min(_BANK_DEBT, max(0.0, game.houses[target].treasury))
        if amount > 0.0:
            order.credit(game.turn, "loan extended", amount)
            journal(f"The Bank extends a loan to {target}",
                    amount, "loan", amount)
        if seat is not None:
            # the seat holder's better loan terms: the Bank lends them
            # on easy terms - a small, recurring, honest infusion
            game.houses[seat].credit(game.turn, "trade",
                                     _BANK_SEAT_LOAN)
            journal(f"The Bank extends the {seat} seat-holder better "
                    f"terms - {_BANK_SEAT_LOAN:.0f} gold to House {seat}",
                    _BANK_SEAT_LOAN, "loan", _BANK_SEAT_LOAN,
                    face=order.head.name)
        return
    # the ordinary press - the Order acts on its target
    if name == "Combine":
        moved = 0.0
        for p in game.provinces_of(target):
            p.unrest = p.unrest + _COMBINE_STRIKE
            moved += _COMBINE_STRIKE
        journal(f"The Combine stirs the mills of {target}",
                moved, "strike", moved)
    elif name == "Church":
        capital = next((p for p in game.provinces_of(target)
                        if p.pid == game.houses[target].capital), None)
        if capital is not None:
            capital.unrest = capital.unrest + _CHURCH_EYES
            journal(f"The Church opens its eyes on {target}",
                    _CHURCH_EYES, "unrest", _CHURCH_EYES)
    elif name == "Gazette":
        moved = 0.0
        for p in game.provinces_of(target):
            p.unrest = p.unrest + _GAZETTE_EYES
            moved += _GAZETTE_EYES
        journal(f"The Gazette runs a hard expose on {target}",
                moved, "expose", moved)
    # the seat holder receives the Order's honest lever instead of its
    # pressure: spared strikes, tithe relief, softer exposés - the seat
    # moves the world through the lever, never by a direct grant
    if seat is not None and seat != target and seat in game.houses:
        if name == "Combine":
            game.houses[seat].prestige += _COMBINE_SEAT_PRESTIGE
            journal(f"The Combine spares the {seat} seat-holder's mills",
                    _COMBINE_SEAT_PRESTIGE, "strike", _COMBINE_SEAT_PRESTIGE)
        elif name == "Church":
            amt = min(_CHURCH_SEAT_RELIEF, max(0.0,
                                               5000.0 - game.houses[seat].treasury))
            if amt > 0.0:
                game.houses[seat].credit(game.turn, "compensation", amt)
            journal(f"The Church grants the {seat} seat-holder tithe relief",
                    amt, "tithe", amt)
        elif name == "Gazette":
            game.houses[seat].prestige += _GAZETTE_SEAT_PRESTIGE
            journal(f"The Gazette softens its exposés on the "
                    f"{seat} seat-holder",
                    _GAZETTE_SEAT_PRESTIGE, "expose", _GAZETTE_SEAT_PRESTIGE)


def init_orders(game) -> None:
    """Create the four Orders on the game. Heads are real Characters built
    from the seeded society (so a seed yields the same four heads); each
    Order opens with a deterministic goal on a house it aims at."""
    orders: Dict[str, Order] = {}
    saved = game.society.rng.getstate()
    for name in ORDER_NAMES:
        spec = _ORDER_SPECS[name]
        head = Character(f"{spec['given']} {name}", _head_stats(name),
                         [], age=40, gender="Male", society=game.society)
        # a legible, stable bent on the line the institution lives on
        for k, v in _ORDER_BIAS[name].items():
            head.dispositions[k] = v
        head.traits = []
        family = spec["families"][0]
        target = _target_for(game, name, family)
        goal = Goal(family=family, target=target,
                    opened_turn=game.turn, commit_turns=COMMIT_TURNS,
                    why=_why(name, family, target))
        order = Order(name, head, goal, set())
        _refresh_wants(order)
        orders[name] = order
    game.society.rng.setstate(saved)
    game.orders = orders
    game.order_seats = {name: None for name in ORDER_NAMES}
    _refresh_reach(game, orders)


def tick_orders(game) -> None:
    """Each turn the Orders push back: their reach tracks the realm, their
    goal rotates through the Order's own families (a deterministic function
    of the turn) and re-targets when the target vanishes, and a head's
    private want follows its institution's line."""
    orders = game.orders
    _refresh_reach(game, orders)
    for name in ORDER_NAMES:
        order = orders[name]
        families = _ORDER_SPECS[name]["families"]
        goal = order.goal
        if goal is None:
            continue
        # rotate the family by the resolved turn - deterministic per seed
        t = game.resolved_turn if game.resolved_turn is not None else 0
        desired = families[t % len(families)]
        target_gone = (goal.target is not None
                       and goal.target not in game.houses)
        if goal.family != desired or target_gone:
            new_target = _target_for(game, name, desired)
            new_why = _why(name, desired, new_target)
            order.goal = Goal(family=desired, target=new_target,
                              opened_turn=game.turn,
                              commit_turns=COMMIT_TURNS, why=new_why)
            game.beats.append(Beat(
                turn=game.turn, kind="signature", house=name,
                text=f"The {name} turns its aim: {new_why}",
                source="orders.tick_orders", causes=(),
                face=order.head.name, facet="ambition",
            ))
        _press(game, order)
        _refresh_wants(order)
