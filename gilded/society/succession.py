"""Succession — a single pure implementation of the line of succession.

Both house_ai.tick_realm and the peerage read-model call this module.
"""

from typing import Dict, List, Optional

from gilded.society.characters import Character


def _designated_heir(realm) -> Optional[Character]:
    """Return the designated heir if one is alive, else None.

    Scans dynasty members first, then realm-wide characters.
    Only a living character with `is_heir` set qualifies.
    """
    ruler = realm.ruler
    ruler_id = ruler.id if ruler else None

    # Check dynasty members first
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != ruler_id and getattr(c, "is_heir", False):
            return c

    # Check all realm characters
    for c in realm.characters:
        if c.is_alive and c.id != ruler_id and getattr(c, "is_heir", False):
            return c

    return None


def succession_order(realm) -> List[Character]:
    """Return candidates in succession priority order.

    The game's rule (house_ai.py:43-64), expressed as a pure ordering
    with no rng, no mutation, no character creation.

    A living designated heir (is_heir flag) stands FIRST, ahead of all tiers.
    Behind the designated heir, the three-tier ordering is unchanged.

    Tiers (behind the designated heir):
      1. Living dynasty members ≥ 16, oldest first
      2. Living dynasty members < 16, oldest first
      3. Living adults in realm.characters (≥ 16) by highest effective statecraft
    """
    ruler = realm.ruler
    # Exclude the current ruler (may be dead, but still excluded)
    ruler_id = ruler.id if ruler else None

    # Find designated heir
    heir = _designated_heir(realm)
    heir_id = heir.id if heir else None

    # Tier 1: living dynasty adults (≥ 16), oldest first
    dynasty_adults = sorted(
        [c for c in realm.dynasty.all_characters.values()
         if c.is_alive and c.id != ruler_id and c.id != heir_id and c.age >= 16],
        key=lambda c: c.age,
        reverse=True,
    )

    # Tier 2: living dynasty minors (< 16), oldest first
    dynasty_minors = sorted(
        [c for c in realm.dynasty.all_characters.values()
         if c.is_alive and c.id != ruler_id and c.id != heir_id and c.age < 16],
        key=lambda c: c.age,
        reverse=True,
    )

    # Tier 3: living adults in realm.characters (≥ 16), highest statecraft first
    other_adults = sorted(
        [c for c in realm.characters
         if c.is_alive and c.id != ruler_id and c.id != heir_id and c.age >= 16],
        key=lambda c: c.get_effective_stat("statecraft"),
        reverse=True,
    )

    rest = dynasty_adults + dynasty_minors + other_adults
    if heir:
        return [heir] + rest
    return rest


def resolve_succession(realm) -> Optional[Character]:
    """Return the character who should succeed the ruler.

    Pure — no rng, no mutation.  Returns None if there is nobody
    eligible (the tick falls back to creating a character in that case).
    """
    order = succession_order(realm)
    return order[0] if order else None


def name_heir(realm) -> Optional[str]:
    """Designate this realm's heir if none is named, so that a living
    designated heir stands ahead of all tiers in the line of succession.

    The heir is the first dynasty member the three-tier order would pick
    (the oldest living adult, else the oldest minor) - i.e. exactly who
    the line names today, but named now, while the ruler still lives.
    Returns a message when a designation is made.
    """
    if _designated_heir(realm) is not None:
        return None
    ruler = realm.ruler
    ruler_id = ruler.id if ruler else None
    for c in realm.dynasty.all_characters.values():
        if getattr(c, "is_heir", False):
            c.is_heir = False
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != ruler_id and c.age >= 16:
            c.is_heir = True
            return f"{c.name} is named heir to the {realm.house_name} throne."
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != ruler_id and c.age < 16:
            c.is_heir = True
            return f"{c.name} is named heir to the {realm.house_name} throne."
    return None
