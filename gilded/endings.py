"""Endings (mission G17): the age passes judgment.

Hard stops close the game - a dynasty extinguished, a house swept away by
revolution, a voluntary transformation, or simply the century running out.
judge() then weighs four axes (capital, standing, blood, world), names the
ending, and writes a four-paragraph epilogue that always states who paid."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from gilded.chassis import TURN_BUDGET, year_of
from gilded.enterprises import ENTERPRISE_TYPES, EXPAND_COST

AXES = ("capital", "standing", "blood", "world")
HEGEMON_CAPITAL = 99.0         # only the richest house stands here
HEGEMON_STANDING = 60.0
QUIET_STANDING = 60.0
QUIET_ATROCITIES = 3.0
ATROCITY_WEIGHT = 2.0          # world-axis cost per recorded atrocity
WELFARE_DIAL = 60.0            # dials held below this reward the world axis


@dataclass
class Epilogue:
    ending_key: str            # named ending
    axes: Dict[str, float]     # "capital", "standing", "blood", "world"
    text: str                  # four paragraphs, one per axis


def check_ending(game, house_name: str) -> Optional[str]:
    """Hard stops, checked every turn for the judged house."""
    realm = game.realms.get(house_name)
    if realm is not None and not any(
            c.is_alive for c in realm.dynasty.all_characters.values()):
        return "extinction"
    fate = getattr(game, "fallen", {}).get(house_name)
    if fate is not None:
        return fate            # "revolution" | "transformed"
    if game.turn > TURN_BUDGET:
        return "century"
    return None


# --- the four axes -----------------------------------------------------------

def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def _ent_value(ent) -> float:
    """What the works would cost to build today: charter plus expansions."""
    value = ENTERPRISE_TYPES[ent.kind][3]
    for tier in range(2, ent.tier + 1):
        value += EXPAND_COST[tier]
    return value


def _house_wealth(game, house_name: str) -> float:
    realm = game.realms.get(house_name)
    ids = {c.id for c in realm.characters} if realm is not None else set()
    wealth = game.houses[house_name].treasury
    for ent in game.enterprises:
        stake = sum(pct for cid, pct in ent.ledger.items() if cid in ids)
        wealth += _ent_value(ent) * stake / 100.0
    return wealth


def _axis_capital(game, house_name: str) -> float:
    """Wealth against the world's best: the richest house scores 100."""
    wealth = {h: _house_wealth(game, h) for h in game.houses}
    best = max(wealth.values())
    if best <= 0.0:
        return 0.0
    return _clamp(100.0 * wealth[house_name] / best)


def _axis_standing(game, house_name: str) -> float:
    house = game.houses[house_name]
    rel = list(house.relations.values())
    mean_rel = sum(rel) / len(rel) if rel else 0.0
    return _clamp(0.5 * game.legitimacy.get(house_name, 0.0)
                  + 0.25 * (50.0 + house.prestige / 4.0)
                  + 0.25 * (50.0 + mean_rel / 2.0))


def _axis_blood(game, house_name: str) -> Tuple[float, List, int]:
    realm = game.realms.get(house_name)
    if realm is None:
        return 0.0, [], 0
    members = list(realm.dynasty.all_characters.values())
    living = [c for c in members if c.is_alive]
    burden = (sum(c.stress for c in living) / len(living)) if living else 100.0
    axis = _clamp(30.0 * len(living) + 5.0 * (len(members) - len(living))
                  - burden / 2.0)
    return axis, living, len(members)


def _axis_world(game, house_name: str) -> Tuple[float, float]:
    provs = game.provinces_of(house_name)
    unrest = (sum(p.unrest for p in provs) / len(provs)) if provs else 0.0
    ents = [e for e in game.enterprises if e.house == house_name]
    welfare = (sum(max(0.0, WELFARE_DIAL - e.extraction_dial) for e in ents)
               / len(ents)) if ents else 0.0
    axis = _clamp(100.0 - game.tide.level
                  - ATROCITY_WEIGHT * game.tide.atrocities
                  - unrest + welfare / 4.0)
    return axis, unrest


# --- judgment ----------------------------------------------------------------

def judge(game, house_name: str) -> Epilogue:
    fate = check_ending(game, house_name)
    capital = _axis_capital(game, house_name)
    standing = _axis_standing(game, house_name)
    blood, living, ever = _axis_blood(game, house_name)
    world, _unrest = _axis_world(game, house_name)
    axes = {"capital": capital, "standing": standing,
            "blood": blood, "world": world}
    if fate == "transformed":
        key = "People's Chairman"
    elif fate in ("extinction", "revolution"):
        key = "A House of Ash"
    elif capital >= HEGEMON_CAPITAL and standing >= HEGEMON_STANDING:
        key = "Hegemon of the Age"
    elif standing >= QUIET_STANDING and game.tide.atrocities <= QUIET_ATROCITIES:
        key = "The Quiet Throne"
    else:
        key = "The Long Ledger"
    return Epilogue(key, axes, _epilogue_text(game, house_name, key, axes,
                                              living, ever))


def _saga_coda(game) -> str:
    """The Director's closing lines: the final age, the rival's fate, and any
    thread the century left open. Empty when no Director has observed a turn."""
    d = getattr(game, "director", None)
    if d is None:
        return ""
    from gilded.saga.content.eras import ERAS
    parts = []
    if 0 <= d.age_idx < len(ERAS):
        parts.append(f"The age closed in {ERAS[d.age_idx].title}.")
    if d.rival:
        rival_beats = [b for b in d.beats.values() if b.source == "rival"]
        reached = [b for b in rival_beats if b.state == "complete"]
        if reached:
            parts.append(f"House {d.rival}, the great rival, "
                         f"{reached[-1].title.lower()} before the end.")
        else:
            parts.append(f"House {d.rival} was the rival that never quite rose.")
    open_threads = [b for b in d.beats.values()
                    if b.source == "chronicle" and b.state == "active"]
    if open_threads:
        parts.append("Left unresolved: "
                     + "; ".join(sorted(b.title for b in open_threads)) + ".")
    return " ".join(parts)


def _epilogue_text(game, house_name: str, key: str, axes: Dict[str, float],
                   living: List, ever: int) -> str:
    year = year_of(game.turn)
    house = game.houses[house_name]
    ents = sorted((e for e in game.enterprises if e.house == house_name),
                  key=lambda e: (-_ent_value(e), e.eid))
    provs = game.provinces_of(house_name)
    paid = max(provs, key=lambda p: (p.unrest, p.pid)) if provs else None

    p1 = (f"{key}. In {year} the ledgers of House {house_name} close on "
          f"{house.treasury:.0f} gold in the vault"
          + (f" and {ents[0].name} still turning at tier {ents[0].tier}"
             if ents else " and not one enterprise left turning")
          + f" - a capital standing of {axes['capital']:.0f}.")
    p2 = (f"Standing: {axes['standing']:.0f}. The mandate rests at "
          f"{game.legitimacy.get(house_name, 0.0):.0f}, prestige at "
          f"{house.prestige:.0f}, in a world whose temper has turned "
          f"{game.tide.phase()}.")
    if living:
        eldest = max(living, key=lambda c: (c.age, c.name))
        p3 = (f"Blood: {axes['blood']:.0f}. {len(living)} of the line still "
              f"draw breath of the {ever} the century saw; {eldest.name}, "
              f"{eldest.age}, carries the name onward.")
    else:
        p3 = (f"Blood: {axes['blood']:.0f}. Of the {ever} the century saw, "
              f"none remain - the name is spoken only by strangers.")
    if paid is not None:
        p4 = (f"World: {axes['world']:.0f}. The bill was paid in "
              f"{paid.name}, where unrest stands at {paid.unrest:.0f} and "
              f"the tide has counted {game.tide.atrocities:.0f} atrocities; "
              f"the workers paid, as they always do.")
    else:
        p4 = (f"World: {axes['world']:.0f}. The House holds no province at "
              f"the close; whoever paid the century's bill, it was not them "
              f"- it never is.")
    coda = _saga_coda(game)
    paragraphs = [p1, p2, p3, p4] + ([coda] if coda else [])
    return "\n\n".join(paragraphs)
