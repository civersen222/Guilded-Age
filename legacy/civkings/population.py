"""Tiered population simulation (character-society spec 3.1, M37).

Tier 0 (everyone, every turn, cheap): aging, mortality, fertility/births.
Tier 1 (the relevance set, full logic): schemes, opinions, stress, actions.
promote() pins any character into Tier 1; their state was maintained
cheaply the whole time, so promotion is seamless.
"""

import random
from typing import List, Set

from simulation import generate_child
from realms import MALE_NAMES, FEMALE_NAMES

MAX_REALM_POP = 150      # living characters per realm; births pause above this
BIRTH_CHANCE = 0.06      # per fertile woman per turn
FERTILE_LO = 16
FERTILE_HI = 45


def bulk_pass(realm, game, skip_ids: Set[str] = frozenset(),
              notable_ids: Set[str] = frozenset()) -> List[str]:
    """Tier-0 pass for one realm: age/kill everyone, then cheap fertility.

    skip_ids: characters aged elsewhere (the player ruler).
    notable_ids: characters whose life events deserve a log line.
    """
    msgs: List[str] = []
    for c in realm.characters:
        if not c.is_alive or c.id in skip_ids:
            continue
        event = c.age_up()
        if event and c.id in notable_ids:
            msgs.append(f"{c.name}: {event}")

    living = [c for c in realm.characters if c.is_alive]
    if len(living) >= MAX_REALM_POP:
        return msgs
    men = [c for c in living
           if c.gender == "Male" and FERTILE_LO <= c.age <= FERTILE_HI]
    if not men:
        return msgs
    game_chars = getattr(game, "characters", None)
    for mother in living:
        if mother.gender != "Female" or not (FERTILE_LO <= mother.age <= FERTILE_HI):
            continue
        if random.random() >= BIRTH_CHANCE:
            continue
        father = random.choice(men)
        child = generate_child(
            f"{random.choice(MALE_NAMES + FEMALE_NAMES)} of {realm.civ_name}",
            father, mother)
        child.age = 0
        child.age_progress.current_age = 0
        realm.characters.append(child)
        if game_chars is not None:
            game_chars.append(child)
    return msgs


def relevance_set(game, realm) -> Set[str]:
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
    sm = getattr(game, "scheme_manager", None)
    if sm is not None:
        for s in sm.schemes:
            rel.add(s.agent.id)
            rel.add(s.target.id)
            rel.update(ch.id for ch in s.participants)
    return rel


def promote(realm, char) -> None:
    """Wake a character into full Tier-1 simulation (spec 3.1: seamless -
    Tier-0 state carries over untouched)."""
    realm.promoted_ids.add(char.id)
