"""Character AI: every living character acts each turn (Phase B2)."""

import random
from typing import List, Optional

from simulation import generate_child, modify_opinion, ATTRIBUTES
from realms import MALE_NAMES, FEMALE_NAMES, _make_character

FEAST_INTERVAL = 12
CHILD_INTERVAL = 8
MAX_LIVING_DYNASTY = 8
MAX_MESSAGES_PER_TURN = 6


def tick_realms(game) -> List[str]:
    """Advance every realm one turn: aging, succession, births, actions."""
    messages: List[str] = []
    realms = getattr(game, "realms", None) or {}
    turn = game.state.turn
    for civ_name, realm in realms.items():
        messages.extend(_tick_realm(game, realm, turn))
    if len(messages) > MAX_MESSAGES_PER_TURN:
        messages = random.sample(messages, MAX_MESSAGES_PER_TURN)
    return messages


def _tick_realm(game, realm, turn) -> List[str]:
    msgs: List[str] = []
    pname = game.player_civ.name
    is_player = realm.civ_name == pname
    if is_player:
        realm.ruler = game.rulers.get(pname, realm.ruler)

    # --- aging (the player ruler is aged by the dynasty block in process_turn) ---
    court_ids = {c.id for c in realm.court.positions.values() if c}
    for c in realm.characters:
        if not c.is_alive or (is_player and c.id == realm.ruler.id):
            continue
        event = c.age_up()
        if event and (c.id == realm.ruler.id or c.id in court_ids):
            msgs.append(f"{c.name}: {event}")

    # --- succession (AI realms; player succession is handled in process_turn) ---
    ruler = realm.ruler
    if not ruler.is_alive and not is_player:
        kin = [c for c in realm.dynasty.all_characters.values() if c.is_alive and c.id != ruler.id]
        adults = [c for c in kin if c.age >= 16]
        heir = max(adults, key=lambda c: c.age) if adults else (max(kin, key=lambda c: c.age) if kin else None)
        if heir is None:
            living = [c for c in realm.characters if c.is_alive and c.age >= 16]
            heir = max(living, key=lambda c: c.get_effective_stat("diplomacy")) if living else None
        if heir is None:
            heir = _make_character(realm.civ_name, ruler.base_stats, [], 20, 35)
            realm.characters.append(heir)
            game.characters.append(heir)
        for pos, ch in realm.court.positions.items():
            if ch and ch.id == heir.id:
                realm.court.positions[pos] = None
        realm.ruler = heir
        realm.court.ruler = heir
        game.rulers[realm.civ_name] = heir
        if heir.id not in realm.dynasty.all_characters:
            realm.dynasty.all_characters[heir.id] = heir
        msgs.append(f"{ruler.name} has died - {heir.name} now rules {realm.civ_name}")
        ruler = heir

    # --- births ---
    living_kin = sum(1 for c in realm.dynasty.all_characters.values() if c.is_alive)
    if ruler.is_alive and not is_player and turn % CHILD_INTERVAL == 0 and 16 <= ruler.age < 55 and living_kin < MAX_LIVING_DYNASTY:
        partner = next((c for c in realm.characters if c.is_alive and c.gender != ruler.gender and c.age >= 16 and c.id != ruler.id), None)
        if partner:
            child = generate_child(f"{random.choice(MALE_NAMES + FEMALE_NAMES)} of {realm.civ_name}", ruler, partner)
            child.age = 0
            child.age_progress.current_age = 0
            realm.dynasty.add_member(child, ruler.id)
            realm.characters.append(child)
            game.characters.append(child)
            msgs.append(f"A child, {child.name}, is born to {ruler.name}")

    # --- court replenishment: fill vacant positions, new blood if the realm runs dry ---
    if not is_player:
        for pos, ch in list(realm.court.positions.items()):
            if ch is not None and ch.is_alive:
                continue
            candidates = [c for c in realm.characters
                          if c.is_alive and c.age >= 16 and c.id != realm.ruler.id
                          and all(o is None or o.id != c.id for o in realm.court.positions.values())]
            pick = realm.court.get_best_candidate(candidates, pos)
            if pick is None:
                pick = _make_character(realm.civ_name, realm.ruler.base_stats, [], 18, 35)
                realm.characters.append(pick)
                game.characters.append(pick)
            realm.court.positions[pos] = None
            realm.court.appoint(pos, pick, turn)

    # --- actions: one per living adult ---
    for c in realm.characters:
        if not c.is_alive or c.age < 16:
            continue
        c.decay_stress()
        if c.id == realm.ruler.id:
            if not is_player:
                m = _ruler_action(game, realm, c, turn)
                if m:
                    msgs.append(m)
        else:
            m = _courtier_action(realm, c, c.id in court_ids)
            if m:
                msgs.append(m)
    return msgs


def _ruler_action(game, realm, ruler, turn) -> Optional[str]:
    others = [c for c in realm.characters if c.is_alive and c.id != ruler.id and c.age >= 16]
    cunning = "Cunning" in ruler.traits or "Opportunistic" in ruler.traits
    social = "Charismatic" in ruler.traits or "Diplomat" in ruler.traits
    if turn % FEAST_INTERVAL == 0 and others:
        ruler.reduce_stress(15)
        for c in others:
            modify_opinion(c, ruler, random.randint(3, 8), "feast")
        return f"{ruler.name} hosts a great feast in {realm.civ_name}"
    rivals = [r for n, r in game.rulers.items() if n != realm.civ_name and r.is_alive]
    if cunning and rivals and random.random() < 0.25:
        target = random.choice(rivals)
        modify_opinion(target, ruler, -random.randint(4, 10), "scheme")
        ruler.add_stress(5)
        return f"{ruler.name} schemes against {target.name}"
    if social and others and random.random() < 0.3:
        modify_opinion(random.choice(others), ruler, random.randint(2, 6), "royal favor")
        return None
    ruler.reduce_stress(3)  # govern quietly
    return None


def _courtier_action(realm, char, in_court: bool) -> Optional[str]:
    others = [c for c in realm.characters if c.is_alive and c.id != char.id and c.age >= 16]
    if in_court and ("Cunning" in char.traits or "Opportunistic" in char.traits) and random.random() < 0.2:
        rivals = [c for c in realm.court.positions.values() if c and c.is_alive and c.id != char.id]
        if rivals:
            rival = random.choice(rivals)
            modify_opinion(rival, char, -random.randint(3, 8), "court intrigue")
            char.add_stress(4)
            return f"{char.name} plots against {rival.name}"
    if others and random.random() < 0.4:
        modify_opinion(random.choice(others), char, random.randint(1, 5), "friendship")
    elif random.random() < 0.15:
        stat = random.choice(ATTRIBUTES)
        char.base_stats[stat] = min(20, char.base_stats.get(stat, 8) + 1)
    return None
