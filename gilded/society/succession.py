"""Succession — a single pure implementation of the line of succession.

Both house_ai.tick_realm and the peerage read-model call this module.
"""

from typing import Dict, List, Optional

from gilded.society.characters import Character


def succession_order(realm) -> List[Character]:
    """Return candidates in succession priority order.

    The game's rule (house_ai.py:43-64), expressed as a pure ordering
    with no rng, no mutation, no character creation.

    Tiers:
      1. Living dynasty members ≥ 16, oldest first
      2. Living dynasty members < 16, oldest first
      3. Living adults in realm.characters (≥ 16) by highest effective statecraft
    """
    ruler = realm.ruler
    # Exclude the current ruler (may be dead, but still excluded)
    ruler_id = ruler.id if ruler else None

    # Tier 1: living dynasty adults (≥ 16), oldest first
    dynasty_adults = sorted(
        [c for c in realm.dynasty.all_characters.values()
         if c.is_alive and c.id != ruler_id and c.age >= 16],
        key=lambda c: c.age,
        reverse=True,
    )

    # Tier 2: living dynasty minors (< 16), oldest first
    dynasty_minors = sorted(
        [c for c in realm.dynasty.all_characters.values()
         if c.is_alive and c.id != ruler_id and c.age < 16],
        key=lambda c: c.age,
        reverse=True,
    )

    # Tier 3: living adults in realm (≥ 16), highest statecraft first
    realm_adults = sorted(
        [c for c in realm.characters
         if c.is_alive and c.id != ruler_id and c.age >= 16],
        key=lambda c: c.get_effective_stat("statecraft"),
        reverse=True,
    )

    return dynasty_adults + dynasty_minors + realm_adults


def resolve_succession(realm) -> Optional[Character]:
    """Return the character who should succeed the ruler.

    Pure — no rng, no mutation.  Returns None if there is nobody
    eligible (the tick falls back to creating a character in that case).
    """
    order = succession_order(realm)
    return order[0] if order else None
