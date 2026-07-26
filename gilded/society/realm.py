"""Realms: every great house gets a ruler, dynasty, and court (mission G8).

Ported from root realms.py onto houses and enterprise lists - no game or
civ objects. All randomness is threaded through an explicit rng.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random

from gilded.society.characters import (
    Character,
    Dynasty,
    generate_child,
    SocietyState,
)
from gilded.society.court import Court, CourtPosition
from gilded.society.shares import transfer_shares

MALE_NAMES = ["Marcus", "Alexios", "Sargon", "Ramses", "Cyrus", "Wei", "Temujin", "Ragnar", "Ashoka", "Aurelius", "Leonidas", "Darius", "Hammurabi", "Khufu", "Kublai", "Bjorn"]
FEMALE_NAMES = ["Livia", "Helena", "Ishtar", "Nefertiti", "Roxana", "Mei", "Borte", "Freydis", "Mira", "Octavia", "Thea", "Atossa", "Semiramis", "Cleopatra", "Tomyris", "Astrid"]

# Baseline attribute block for house-born characters; rng jitter spreads it.
HOUSE_BASE_STATS = {"statecraft": 8, "command": 8, "industry": 8,
                    "intrigue": 8, "science": 8, "resolve": 8}


@dataclass
class Realm:
    house_name: str
    ruler: Character
    dynasty: Dynasty
    court: Court
    characters: List[Character] = field(default_factory=list)
    promoted_ids: set = field(default_factory=set)  # Tier-1 pins (population.promote)


def _jitter_stats(base: Dict[str, int], rng: random.Random, spread: int = 3) -> Dict[str, int]:
    return {k: max(1, v + rng.randint(-spread, spread)) for k, v in base.items()}


def _make_character(house_name: str, base_stats: Dict[str, int], traits: List[str], age_lo: int, age_hi: int, rng: random.Random, society: SocietyState, gender: str = None) -> Character:
    gender = gender or rng.choice(["Male", "Female"])
    pool = MALE_NAMES if gender == "Male" else FEMALE_NAMES
    name = f"{rng.choice(pool)} {house_name}"
    return Character(name=name, stats=_jitter_stats(base_stats, rng), traits=list(traits), age=rng.randint(age_lo, age_hi), gender=gender, society=society)


def create_house_realm(house_name: str, society: SocietyState) -> Realm:
    """Build ruler, spouse, children, courtiers, dynasty, and court for one house."""
    rng = society.rng
    ruler = _make_character(house_name, HOUSE_BASE_STATS, [], 28, 45, rng, society)
    spouse = _make_character(house_name, HOUSE_BASE_STATS, [], 22, 40, rng, society, gender="Female" if ruler.gender == "Male" else "Male")
    dynasty = Dynasty(ruler, {ruler.id: ruler})
    characters = [ruler, spouse]
    for _ in range(rng.randint(1, 2)):
        child = generate_child(f"{rng.choice(MALE_NAMES + FEMALE_NAMES)} {house_name}", ruler, spouse, rng)
        dynasty.add_member(child, ruler.id)
        characters.append(child)
    court = Court(ruler)
    courtiers = [_make_character(house_name, HOUSE_BASE_STATS, [], 20, 55, rng, society) for _ in range(rng.randint(40, 60))]
    characters.extend(courtiers)
    unassigned = list(courtiers)
    for position in CourtPosition:
        best = court.get_best_candidate(unassigned, position)
        if best and court.appoint(position, best, 0):
            unassigned.remove(best)
    realm = Realm(house_name, ruler, dynasty, court, characters)
    realm.society = society
    return realm


DIRECTOR_SALARY_PCT = 10.0  # shares salary from the ruler's stake (spec 4.4)


def tick_directors(realm: Realm, enterprises: List, rng: random.Random) -> List[str]:
    """Enfeoffment (spec 4.4): every house enterprise gets a Director drawn
    from the realm's characters (best industry, adult, not the ruler, not on
    the council, not already a Director), paid a 10% shares salary from the
    ruler's stake. Sitting Directors gain Focus progress along industry."""
    events: List[str] = []
    house_ents = [e for e in enterprises if e.house == realm.house_name]
    by_id = {ch.id: ch for ch in realm.characters}
    court_ids = {ch.id for ch in realm.court.positions.values() if ch}
    taken = set()
    for ent in house_ents:
        d = by_id.get(ent.director_id)
        if d is not None and d.is_alive:
            taken.add(d.id)
        else:
            ent.director_id = ""
    for ent in house_ents:
        if ent.director_id:
            continue
        pool = [ch for ch in realm.characters
                if ch.is_alive and ch.age >= 16 and ch.id != realm.ruler.id
                and ch.id not in taken and ch.id not in court_ids]
        if not pool:
            continue
        director = max(pool, key=lambda ch: ch.get_effective_stat("industry"))
        ent.director_id = director.id
        taken.add(director.id)
        moved = transfer_shares(ent, realm.ruler.id, director.id, DIRECTOR_SALARY_PCT)
        if moved > 0:
            events.append(f"{director.name} is enfeoffed as Director of {ent.name} ({moved:.0f}% shares salary)")
        else:
            events.append(f"{director.name} is appointed Director of {ent.name}")
    for ent in house_ents:
        d = by_id.get(ent.director_id)
        if d is not None and d.is_alive:
            if d.focus.attribute is None:
                d.focus.set("industry")
            line = d.tick_focus()
            if line:
                events.append(line)
    return events


LOYALTY_START = 50.0


def tick_loyalty(realm: Realm, enterprises: List, rng: random.Random) -> List[str]:
    """Loyalty (spec 4.4): council members and Directors hold loyalty 0-100
    rebuilt each turn from opinion of the ruler, treatment (a shares salary),
    and Conviction alignment (Labor/Capital axis). Returns a message when a
    posted character first slips into disloyalty."""
    events: List[str] = []
    ruler = realm.ruler
    if ruler is None or not ruler.is_alive:
        return events
    house_ents = [e for e in enterprises if e.house == realm.house_name]
    by_id = {ch.id: ch for ch in realm.characters}
    posted: Dict[str, Character] = {}
    for ch in realm.court.positions.values():
        if ch is not None and ch.is_alive:
            posted[ch.id] = ch
    for ent in house_ents:
        d = by_id.get(ent.director_id)
        if d is not None and d.is_alive:
            posted[d.id] = d
    for ch in posted.values():
        if ch.id == ruler.id:
            continue
        opinion = ch._society.opinions.get((ch.id, ruler.id), 0)
        # Treatment: check not just ledger presence but actual dividends received
        # An enterprise with _last_dividend > 0 is productive and rewarding
        productive = [ent for ent in house_ents
                      if ch.id in ent.ledger and getattr(ent, '_last_dividend', 0) >= 0]
        paid = len(productive) > 0
        treatment = 10.0 if paid else -10.0
        align = 10.0 - abs(ch.dispositions.get("labor_capital", 0.0)
                           - ruler.dispositions.get("labor_capital", 0.0)) / 10.0
        target = max(0.0, min(100.0, 50.0 + opinion * 0.5 + treatment + align))
        old = getattr(ch, "loyalty", 50.0)
        ch.loyalty = old + (target - old) * 0.2
        if old >= DISLOYAL_LOYALTY and ch.loyalty < DISLOYAL_LOYALTY:
            events.append(f"{ch.name} has become disloyal to {ruler.name}")
    return events


DISLOYAL_LOYALTY = 40.0   # sellers: loyalty below this...
DISLOYAL_OPINION = -20    # ...or opinion of the ruler at or below this


def disloyal_shareholders(realm: Realm, enterprises: List,
                          house_only: bool = True) -> List[Character]:
    """Hostile takeover's door (spec 6): the siblings, widows and denied
    heirs who hold House shares but no love for the House. Low loyalty or
    a grudge against the ruler marks them ready to sell. The ruler is
    never on this list - selling the House out from under yourself is a
    different verb.

    When *house_only* is True (default) the shareholder test is restricted
    to enterprises whose .house matches the realm.  When False the check
    spans every enterprise in *enterprises*, allowing a caller to judge
    disloyalty across the full portfolio (e.g. grip.py read-model).
    """
    ruler = realm.ruler
    if house_only:
        check_ents = [e for e in enterprises if e.house == realm.house_name]
    else:
        check_ents = list(enterprises)
    out: List[Character] = []
    for ch in realm.characters:
        if not ch.is_alive or ch.id == ruler.id:
            continue
        if not any(ch.id in ent.ledger for ent in check_ents):
            continue
        opinion = ch._society.opinions.get((ch.id, ruler.id), 0)
        loyalty = getattr(ch, "loyalty", None)
        if (loyalty is not None and loyalty < DISLOYAL_LOYALTY
                or opinion <= DISLOYAL_OPINION):
            out.append(ch)
    return out