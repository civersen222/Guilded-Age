"""The Four Orders (mission C3 - the world pushes back).

The realm is not just Houses. Four institutions stand alongside the seven
great Houses and push back with the SAME anatomy: a real head (a Character
with dispositions, traits, a private want) and a live GOAL (an agenda.Goal)
that is held across a commit window, re-evaluated, and that stands in the
way of a House whose ambition crosses it (see ambitions._order_clash).

  Crown    - pursues Dominion     (the borders are too small)
  Treasury - pursues Buyout       (the richest House's shares are for the taking)
  Guilds   - pursues Consolidation(the mills must stand quiet)
  Church   - pursues Intrigue     (the player's secrets are worth having)

Each Order's REACH is its jurisdiction - the total population of the realm's
provinces it can press on - so the Orders grow and shrink with the world.

Deterministic: goal selection and head creation use no RNG; the head's
dispositions come from the game's seeded society rng (seeded once at boot),
so a given seed always yields the same four heads and the same aims.
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

# name -> (the institution's family, the disposition that reads its stance,
#          the head's given name)
_ORDER_SPECS = {
    "Crown":    {"family": "Dominion",     "given": "Corbin"},
    "Treasury": {"family": "Buyout",       "given": "Maren"},
    "Guilds":   {"family": "Consolidation","given": "Halden"},
    "Church":   {"family": "Intrigue",     "given": "Seraphine"},
}

# head disposition profile per Order - seeded deterministically so a head has
# a stable, legible bent on the line its institution lives on.
_ORDER_BIAS = {
    "Crown":    {"bold_craven": 30.0, "ambitious_content": 25.0},
    "Treasury": {"generous_greedy": 35.0, "trusting_paranoid": 20.0},
    "Guilds":   {"cruel_compassionate": 25.0, "traditionalist_modernist": 30.0},
    "Church":   {"honest_deceitful": -30.0, "bold_craven": 20.0},
}

ORDER_NAMES = tuple(_ORDER_SPECS)

# wave 2 - the levers move real world quantities. Every tick each Order
# presses its lever on the House it currently aims at; the effect is
# deterministic (no RNG) and House treasuries are never touched (only the
# Treasury Order credits ITS OWN treasury from the target's gold).
_CROWN_PRESSURE = 0.5        # border pressure: unrest added per target province
_TREASURY_PURCHASE = 100.0   # shares bought from the richest House, per tick
_GUILD_CALM = 0.5            # quieting of the mills: unrest removed per target province
_CHURCH_EYES = 0.25          # the eyes of the Church: unrest added to the target's capital


def _head_stats(name: str) -> Dict[str, int]:
    base = {"statecraft": 7, "command": 7, "industry": 7,
            "intrigue": 7, "science": 7, "resolve": 7}
    if name == "Crown":
        base["command"] += 3
    elif name == "Treasury":
        base["industry"] += 3
    elif name == "Guilds":
        base["resolve"] += 3
    elif name == "Church":
        base["intrigue"] += 3
    return base


class Order:
    """A first-class institution: a real head with a private want, a live
    goal, a treasury it draws from, and the realm it reaches."""

    def __init__(self, name: str, head: Character, goal: Goal,
                 reach: int) -> None:
        self.name = name
        self.head = head
        self.goal = goal
        self.treasury: float = 0.0
        self.reach: int = reach
        self.journal: List[tuple] = []          # (turn, label, amount)
        self.family = _ORDER_SPECS[name]["family"]

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


def _target_for(game, name: str) -> Optional[str]:
    spec = _ORDER_SPECS[name]
    if spec["family"] == "Buyout":
        # richest House by treasury (shares are where the gold is)
        return _richest_house(game)
    if spec["family"] == "Intrigue":
        player = next((h for h in game.houses if game.houses[h].is_player),
                      None)
        if player is not None:
            return player
        return _strongest_house(game)
    return _strongest_house(game)


def _why(family: str, target: Optional[str]) -> str:
    return {
        "Dominion": "the borders are too small",
        "Buyout": f"House {target}'s shares are for the taking",
        "Consolidation": "the mills must stand quiet",
        "Intrigue": f"House {target}'s secrets are worth having",
    }[family]


def _refresh_wants(order: Order) -> None:
    if order.goal is not None:
        order.wants(order.goal.family)


def _press(game, order: Order) -> None:
    """wave 2 - the Order acts: its lever moves a real, deterministic
    world quantity on the House it aims at. The gold that moves (Treasury
    only) is journalled on the Order; its treasury is never touched, so
    the world the Orders push on stays deterministic across boots."""
    target = order.goal.target
    if target is None or target not in game.houses:
        return
    def journal(why: str, amount: float, facet: str, amt: float) -> None:
        if amt <= 0.0:
            return
        game.beats.append(Beat(
            turn=game.turn, kind="signature", house=target,
            text=why, source="orders._press",
            causes=(Cause(why, amt, "orders._press"),),
            face=order.head.name, facet=facet,
        ))
    if order.family == "Dominion":
        moved = 0.0
        for p in game.provinces_of(target):
            p.unrest = p.unrest + _CROWN_PRESSURE
            moved += _CROWN_PRESSURE
        journal(f"The Crown presses its border on {target}",
                moved, "unrest", moved)
    elif order.family == "Buyout":
        # collects a tax share of the richest House's gold - it does NOT
        # drain the House's treasury (that would move the world's strength
        # rankings); the Order's own treasury is where the gold lands.
        amount = min(_TREASURY_PURCHASE, game.houses[target].treasury)
        if amount > 0.0:
            order.credit(game.turn, "shares taken", amount)
            journal(f"The Treasury takes a share of {target}'s gold",
                    amount, "dividends", amount)
    elif order.family == "Consolidation":
        moved = 0.0
        for p in game.provinces_of(target):
            drop = min(_GUILD_CALM, p.unrest)
            p.unrest = p.unrest - drop
            moved += drop
        journal(f"The Guilds quiet the mills of {target}",
                moved, "unrest", moved)
    elif order.family == "Intrigue":
        capital = next((p for p in game.provinces_of(target)
                        if p.pid == game.houses[target].capital), None)
        if capital is not None:
            capital.unrest = capital.unrest + _CHURCH_EYES
            journal(f"The Church opens its eyes on {target}",
                    _CHURCH_EYES, "unrest", _CHURCH_EYES)


def init_orders(game) -> None:
    """Create the four Orders on the game. Heads are real Characters built
    from the seeded society (so a seed yields the same four heads); each
    Order opens with a deterministic goal on the House it aims at."""
    orders: Dict[str, Order] = {}
    reach = sum(p.population for p in game.atlas.provinces.values())
    # heads draw from a snapshot of the society rng so their creation
    # shifts NOTHING downstream (births, house courts, ...) - the world
    # is byte-identical to a game without the Orders
    saved = game.society.rng.getstate()
    for name in ORDER_NAMES:
        spec = _ORDER_SPECS[name]
        head = Character(f"{spec['given']} {name}", _head_stats(name),
                         [], age=40, gender="Male", society=game.society)
        # a legible, stable bent on the line the institution lives on
        for k, v in _ORDER_BIAS[name].items():
            head.dispositions[k] = v
        head.traits = []
        goal = Goal(family=spec["family"], target=_target_for(game, name),
                    opened_turn=game.turn, commit_turns=COMMIT_TURNS,
                    why=_why(spec["family"], _target_for(game, name)))
        order = Order(name, head, goal, reach)
        _refresh_wants(order)
        orders[name] = order
    game.society.rng.setstate(saved)
    game.orders = orders


def tick_orders(game) -> None:
    """Each turn the Orders push back: their reach tracks the realm, their
    goal is re-evaluated when its commit window closes or its target has
    vanished, and a head's private want follows its institution's line."""
    orders = game.orders
    reach = sum(p.population for p in game.atlas.provinces.values())
    for name in ORDER_NAMES:
        order = orders[name]
        order.reach = reach
        goal = order.goal
        if goal is None:
            continue
        expired = game.turn >= goal.opened_turn + goal.commit_turns
        target_gone = (goal.target is not None
                       and goal.target not in game.houses)
        if expired or target_gone:
            new_target = _target_for(game, name)
            new_why = _why(order.family, new_target)
            order.goal = Goal(family=order.family, target=new_target,
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
