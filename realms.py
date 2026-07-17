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
