"""Realms: every civilization gets a ruler, dynasty, and court (Phase B1)."""

from dataclasses import dataclass, field
from typing import Dict, List
import random

from simulation import Character, Dynasty, generate_child
from court import Court, CourtPosition

MALE_NAMES = ["Marcus", "Alexios", "Sargon", "Ramses", "Cyrus", "Wei", "Temujin", "Ragnar", "Ashoka", "Aurelius", "Leonidas", "Darius", "Hammurabi", "Khufu", "Kublai", "Bjorn"]
FEMALE_NAMES = ["Livia", "Helena", "Ishtar", "Nefertiti", "Roxana", "Mei", "Borte", "Freydis", "Mira", "Octavia", "Thea", "Atossa", "Semiramis", "Cleopatra", "Tomyris", "Astrid"]


@dataclass
class Realm:
    civ_name: str
    ruler: Character
    dynasty: Dynasty
    court: Court
    characters: List[Character] = field(default_factory=list)
    promoted_ids: set = field(default_factory=set)  # Tier-1 pins (population.promote)
    enterprises: List = field(default_factory=list)  # house Enterprises (shares.py, M43)


def _jitter_stats(base: Dict[str, int], spread: int = 3) -> Dict[str, int]:
    return {k: max(1, v + random.randint(-spread, spread)) for k, v in base.items()}


def _make_character(civ_name: str, base_stats: Dict[str, int], traits: List[str], age_lo: int, age_hi: int, gender: str = None) -> Character:
    gender = gender or random.choice(["Male", "Female"])
    pool = MALE_NAMES if gender == "Male" else FEMALE_NAMES
    name = f"{random.choice(pool)} of {civ_name}"
    return Character(name=name, stats=_jitter_stats(base_stats), traits=list(traits), age=random.randint(age_lo, age_hi), gender=gender)


def create_realm(civ, turn: int = 0) -> Realm:
    """Build ruler, spouse, children, courtiers, dynasty, and court for one civ."""
    ruler = _make_character(civ.name, civ.starting_stats, civ.starting_traits, 28, 45)
    spouse = _make_character(civ.name, civ.starting_stats, [], 22, 40, gender="Female" if ruler.gender == "Male" else "Male")
    dynasty = Dynasty(ruler, {ruler.id: ruler})
    characters = [ruler, spouse]
    for _ in range(random.randint(1, 2)):
        child = generate_child(f"{random.choice(MALE_NAMES + FEMALE_NAMES)} of {civ.name}", ruler, spouse)
        dynasty.add_member(child, ruler.id)
        characters.append(child)
    court = Court(ruler)
    # Spec-scale pool (spec 3.1): hundreds of living characters per game.
    courtiers = [_make_character(civ.name, civ.starting_stats, [], 20, 55) for _ in range(random.randint(40, 60))]
    characters.extend(courtiers)
    unassigned = list(courtiers)
    for position in CourtPosition:
        best = court.get_best_candidate(unassigned, position)
        if best and court.appoint(position, best, turn):
            unassigned.remove(best)
    return Realm(civ.name, ruler, dynasty, court, characters)


def create_realms(game) -> Dict[str, Realm]:
    """Give every civ a realm; the player's existing ruler/dynasty/court alias into theirs."""
    realms: Dict[str, Realm] = {}
    pname = game.player_civ.name
    if game.rulers.get(pname):
        realms[pname] = Realm(pname, game.rulers[pname], game.dynasty, game.court, list(game.characters))
    for civ_name, civ in game.civilizations.items():
        if civ_name == pname:
            continue
        realm = create_realm(civ)
        realms[civ_name] = realm
        game.rulers[civ_name] = realm.ruler
        game.succession_laws[civ_name] = 'PRIMOGENITURE'
        game.characters.extend(realm.characters)
    return realms


DOMAIN_CAP = 4  # personal domain (spec 2): cities beyond this need a Director


def tick_directors(game) -> List[str]:
    """Enfeoffment (M47, spec 4.4): every city beyond a realm's domain cap
    gets a Director drawn from the realm's characters (best industry, adult,
    not the ruler, not on the council, not already a Director), paid a 10%
    shares salary from the ruler's stake in the city's enterprise."""
    from shares import transfer_shares
    events: List[str] = []
    realms = getattr(game, "realms", None) or {}
    for civ_name, realm in realms.items():
        cities = [c for c in game.cities.values() if c.owner == civ_name]
        taken = {c.director.id for c in cities
                 if c.director is not None and c.director.is_alive}
        court_ids = {ch.id for ch in realm.court.positions.values() if ch}
        for city in cities[DOMAIN_CAP:]:
            if city.director is not None and city.director.is_alive:
                continue
            pool = [ch for ch in realm.characters
                    if ch.is_alive and ch.age >= 16 and ch.id != realm.ruler.id
                    and ch.id not in taken and ch.id not in court_ids]
            if not pool:
                continue
            director = max(pool, key=lambda ch: ch.get_effective_stat("industry"))
            city.director = director
            taken.add(director.id)
            for ent in realm.enterprises:
                if ent.city_name == city.name:
                    moved = transfer_shares(ent, realm.ruler.id, director.id, 10.0)
                    if moved > 0:
                        events.append(f"{director.name} is enfeoffed as Director of {city.name} ({moved:.0f}% shares salary)")
                    else:
                        events.append(f"{director.name} is appointed Director of {city.name}")
                    break
            else:
                events.append(f"{director.name} is appointed Director of {city.name}")
    return events


LOYALTY_START = 50.0


def tick_loyalty(game) -> List[str]:
    """Loyalty (M49, spec 4.4): council members and Directors hold loyalty
    0-100 rebuilt each turn from opinion of the ruler, treatment (a shares
    salary), and Conviction alignment (Labor/Capital axis). The disloyal
    embezzle now (shares.embezzle); defection and revolution hooks are
    consumed in Waves IN and PE."""
    from shares import embezzle
    from simulation import opinion_matrix
    events: List[str] = []
    realms = getattr(game, "realms", None) or {}
    for civ_name, realm in realms.items():
        ruler = realm.ruler
        if ruler is None or not ruler.is_alive:
            continue
        cities = [c for c in game.cities.values() if c.owner == civ_name]
        posted = {}
        for ch in realm.court.positions.values():
            if ch is not None and ch.is_alive:
                posted[ch.id] = ch
        for c in cities:
            d = c.director
            if d is not None and d.is_alive:
                posted[d.id] = d
        for ch in posted.values():
            if ch.id == ruler.id:
                continue
            opinion = opinion_matrix.get((ch.id, ruler.id), 0)
            paid = any(ch.id in ent.ledger for ent in realm.enterprises)
            treatment = 10.0 if paid else -10.0
            align = 10.0 - abs(ch.dispositions.get("labor_capital", 0.0)
                               - ruler.dispositions.get("labor_capital", 0.0)) / 10.0
            target = max(0.0, min(100.0, 50.0 + opinion / 2.0 + treatment + align))
            cur = getattr(ch, "loyalty", LOYALTY_START)
            ch.loyalty = cur + (target - cur) * 0.2
        events.extend(embezzle(game, realm, cities))
    return events


DISLOYAL_LOYALTY = 40.0   # sellers: loyalty below this...
DISLOYAL_OPINION = -20    # ...or opinion of the ruler at or below this


def disloyal_shareholders(realm) -> List[Character]:
    """Hostile takeover's door (M65, spec 6): the siblings, widows and
    denied heirs who hold House shares but no love for the House. Low
    loyalty or a grudge against the ruler marks them ready to sell.
    The ruler is never on this list - selling the House out from under
    yourself is a different verb."""
    from simulation import opinion_matrix
    ruler = realm.ruler
    out: List[Character] = []
    for ch in realm.characters:
        if not ch.is_alive or ch.id == ruler.id:
            continue
        if not any(ch.id in ent.ledger for ent in realm.enterprises):
            continue
        opinion = opinion_matrix.get((ch.id, ruler.id), 0)
        if (getattr(ch, "loyalty", LOYALTY_START) < DISLOYAL_LOYALTY
                or opinion <= DISLOYAL_OPINION):
            out.append(ch)
    return out
