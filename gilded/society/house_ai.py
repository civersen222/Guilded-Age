"""House AI: every living character in an AI house acts each turn (mission G11).

Ported from root character_ai.py onto a single realm and an explicit rng.
Every player-civ special case is gone - all houses run the same logic. The
chassis loops over realms, owns enterprises (so it calls partition_shares on
succession itself, using the returned messages' ruler change), and registers
the returned new characters wherever it keeps its global roster.

The root's cunning-ruler foreign-scheme branch is dropped: tick_realm sees a
single realm, and foreign intrigue now lives in relationships/schemes."""

import random
from typing import List, Optional, Tuple

from gilded.society.characters import Character, generate_child, modify_opinion, ATTRIBUTES
from gilded.society.realm import MALE_NAMES, FEMALE_NAMES, _make_character
from gilded.society.population import bulk_pass, relevance_set
from gilded.society.dispositions import apply_drift, guardian_rub_off
from gilded.society.succession import resolve_succession

FEAST_INTERVAL = 12
CHILD_INTERVAL = 8
MAX_LIVING_DYNASTY = 8


def tick_realm(realm, turn, rng: random.Random, tide=None,
               succession_law: str = "PRIMOGENITURE") -> Tuple[List[str], List[Character]]:
    """Advance one realm one turn: aging, succession, births, actions.

    Returns (messages, new_chars). new_chars are already in realm.characters;
    the chassis registers them in its global roster. succession_law is
    accepted for the chassis (which owns share partitions); it does not
    change who inherits here."""
    msgs: List[str] = []
    new_chars: List[Character] = []

    # --- Tier 0 bulk pass (spec 3.1): aging, mortality, fertility for ALL ---
    court_ids = {c.id for c in realm.court.positions.values() if c}
    notable_ids = court_ids | {realm.ruler.id}
    bulk_msgs, born = bulk_pass(realm, turn, rng, set(), notable_ids)
    msgs.extend(bulk_msgs)
    new_chars.extend(born)

    # --- succession: the oldest kin takes the chair the moment it empties ---
    ruler = realm.ruler
    if not ruler.is_alive:
        heir = resolve_succession(realm)
        if heir is None:
            heir = _make_character(realm.house_name, ruler.base_stats, [], 20, 35, rng, realm.society)
            realm.characters.append(heir)
            new_chars.append(heir)
        for pos, ch in realm.court.positions.items():
            if ch and ch.id == heir.id:
                realm.court.positions[pos] = None
        realm.ruler = heir
        realm.court.ruler = heir
        if heir.id not in realm.dynasty.all_characters:
            realm.dynasty.all_characters[heir.id] = heir
        msgs.append(f"{ruler.name} has died - {heir.name} now rules {realm.house_name}")
        ruler = heir

    # --- births ---
    living_kin = sum(1 for c in realm.dynasty.all_characters.values() if c.is_alive)
    if ruler.is_alive and turn % CHILD_INTERVAL == 0 and 16 <= ruler.age < 55 and living_kin < MAX_LIVING_DYNASTY:
        partner = next((c for c in realm.characters if c.is_alive and c.gender != ruler.gender and c.age >= 16 and c.id != ruler.id), None)
        if partner:
            child = generate_child(f"{rng.choice(MALE_NAMES + FEMALE_NAMES)} {realm.house_name}", ruler, partner, rng)
            child.age = 0
            child.age_progress.current_age = 0
            realm.dynasty.add_member(child, ruler.id)
            realm.characters.append(child)
            new_chars.append(child)
            msgs.append(f"A child, {child.name}, is born to {ruler.name}")

    # --- Guardians & education (spec 3.6): childhood shapes adults ---
    grown = [c for c in realm.characters if c.is_alive and c.age >= 16]
    for c in realm.characters:
        if not c.is_alive:
            continue
        if c.age < 16:
            g = c.guardian
            if g is None or not getattr(g, "is_alive", False):
                pool = [a for a in grown if a.id != c.id]
                c.guardian = rng.choice(pool) if pool else None
            if c.education_track is None:
                c.education_track = max(ATTRIBUTES, key=lambda a: c.base_stats.get(a, 0))
            if c.guardian is not None:
                msgs.extend(guardian_rub_off(c, c.guardian))
        else:
            m = c.graduate()
            if m:
                msgs.append(m)

    # --- court replenishment: fill vacant positions, new blood if the realm runs dry ---
    for pos, ch in list(realm.court.positions.items()):
        if ch is not None and ch.is_alive:
            continue
        candidates = [c for c in realm.characters
                      if c.is_alive and c.age >= 16 and c.id != realm.ruler.id
                      and all(o is None or o.id != c.id for o in realm.court.positions.values())]
        pick = realm.court.get_best_candidate(candidates, pos)
        if pick is None:
            pick = _make_character(realm.house_name, realm.ruler.base_stats, [], 18, 35, rng, realm.society)
            realm.characters.append(pick)
            new_chars.append(pick)
        realm.court.positions[pos] = None
        realm.court.appoint(pos, pick, turn)

    # --- actions: full Tier-1 logic only for the relevance set (spec 3.1) ---
    relevant = relevance_set(realm, set())
    for c in realm.characters:
        if not c.is_alive or c.age < 16 or c.id not in relevant:
            continue
        c.decay_stress()
        # Focus (spec 3.6): every adult holds one Focus line.
        if c.focus.attribute is None:
            c.focus.set(max(ATTRIBUTES, key=lambda a: c.base_stats.get(a, 0)))
        fm = c.tick_focus()
        if fm:
            msgs.append(fm)
        if c.id == realm.ruler.id:
            m = _ruler_action(realm, c, turn, rng)
            if m:
                msgs.append(m)
        else:
            m = _courtier_action(realm, c, c.id in court_ids, rng)
            if m:
                msgs.append(m)
    return msgs, new_chars


def _ruler_action(realm, ruler, turn, rng: random.Random) -> Optional[str]:
    others = [c for c in realm.characters if c.is_alive and c.id != ruler.id and c.age >= 16]
    social = "Charismatic" in ruler.traits or "Diplomat" in ruler.traits
    if turn % FEAST_INTERVAL == 0 and others:
        ruler.reduce_stress(15)
        for c in others:
            modify_opinion(c, ruler, rng.randint(3, 8), "feast")
        # A life of feasting shapes the host (spec 3.4 drift).
        drift = apply_drift(ruler, "gregarious_reclusive", -4.0, "hosting feasts")
        base = f"{ruler.name} hosts a great feast in {realm.house_name}"
        return f"{base} - {drift}" if drift else base
    if social and others and rng.random() < 0.3:
        modify_opinion(rng.choice(others), ruler, rng.randint(2, 6), "royal favor")
        return None
    ruler.reduce_stress(3)  # govern quietly
    return None


def _courtier_action(realm, char, in_court: bool, rng: random.Random) -> Optional[str]:
    others = [c for c in realm.characters if c.is_alive and c.id != char.id and c.age >= 16]
    if in_court and ("Cunning" in char.traits or "Opportunistic" in char.traits) and rng.random() < 0.2:
        rivals = [c for c in realm.court.positions.values() if c and c.is_alive and c.id != char.id]
        if rivals:
            rival = rng.choice(rivals)
            modify_opinion(rival, char, -rng.randint(3, 8), "court intrigue")
            char.add_stress(4)
            return f"{char.name} plots against {rival.name}"
    if others and rng.random() < 0.4:
        modify_opinion(rng.choice(others), char, rng.randint(1, 5), "friendship")
    elif rng.random() < 0.15:
        stat = rng.choice(ATTRIBUTES)
        char.base_stats[stat] = min(20, char.base_stats.get(stat, 8) + 1)
    return None