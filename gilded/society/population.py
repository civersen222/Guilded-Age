"""Tiered population simulation for great houses (mission G8).

Tier 0 (everyone, every turn, cheap): aging, mortality, fertility/births.
Tier 1 (the relevance set, full logic): schemes, opinions, stress, actions.
promote() pins any character into Tier 1; their state was maintained
cheaply the whole time, so promotion is seamless.
"""

import random
from typing import List, Set, Tuple

from gilded.society.characters import Character, generate_child
from gilded.society.realm import MALE_NAMES, FEMALE_NAMES

MAX_REALM_POP = 150      # living characters per realm; births pause above this
BIRTH_CHANCE = 0.06      # per fertile woman per turn
FERTILE_LO = 16
FERTILE_HI = 45


def bulk_pass(realm, turn: int, rng: random.Random,
              skip_ids: Set[str] = frozenset(),
              notable_ids: Set[str] = frozenset()) -> Tuple[List[str], List[Character]]:
    """Tier-0 pass for one realm: age/kill everyone, then cheap fertility.

    skip_ids: characters aged elsewhere (the player ruler).
    notable_ids: characters whose life events deserve a log line.
    Returns (messages, new_children); the caller owns registering the
    children with any global roster.
    """
    msgs: List[str] = []
    born: List[Character] = []
    for c in realm.characters:
        if not c.is_alive or c.id in skip_ids:
            continue
        event = c.age_up()
        if event and c.id in notable_ids:
            msgs.append(f"{c.name}: {event}")

    living = [c for c in realm.characters if c.is_alive]
    if len(living) >= MAX_REALM_POP:
        return msgs, born
    men = [c for c in living
           if c.gender == "Male" and FERTILE_LO <= c.age <= FERTILE_HI]
    if not men:
        return msgs, born
    for mother in living:
        if mother.gender != "Female" or not (FERTILE_LO <= mother.age <= FERTILE_HI):
            continue
        if rng.random() >= BIRTH_CHANCE:
            continue
        father = rng.choice(men)
        child = generate_child(
            f"{rng.choice(MALE_NAMES + FEMALE_NAMES)} {realm.house_name}",
            father, mother, rng)
        child.age = 0
        child.age_progress.current_age = 0
        realm.characters.append(child)
        born.append(child)
    return msgs, born


def relevance_set(realm, scheme_agent_ids: Set[str]) -> Set[str]:
    """Tier-1 ids for one realm: ruler, living dynasty kin, seated court,
    scheme participants, plus anyone pinned via promote()."""
    rel: Set[str] = set(realm.promoted_ids)
    if realm.ruler is not None:
        rel.add(realm.ruler.id)
    for c in realm.dynasty.all_characters.values():
        if c.is_alive:
            rel.add(c.id)
    for c in realm.court.positions.values():
        if c is not None:
            rel.add(c.id)
    rel.update(scheme_agent_ids)
    return rel


def promote(realm, char) -> None:
    """Wake a character into full Tier-1 simulation (spec 3.1: seamless -
    Tier-0 state carries over untouched)."""
    realm.promoted_ids.add(char.id)
