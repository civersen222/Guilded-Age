"""Cross-civ marriages bind realms together (Phase B4)."""

import random
from typing import List, Optional

from simulation import modify_opinion

MARRIAGE_CHANCE = 0.04
BLOOD_TIE_INTERVAL = 8
BLOOD_TIE_BONUS = 3
MARRIAGE_RELATION_BONUS = 15
ALLIANCE_AT = 50
MAX_MESSAGES = 3

# (char_a_id, civ_a, char_b_id, civ_b) — the two houses joined by each match
_marriages: List[tuple] = []
_married_ids = set()
wedding_count = 0


def tick_marriages(game) -> List[str]:
    """Arrange cross-civ matches, then let existing ones pull realms together."""
    msgs: List[str] = []
    realms = getattr(game, "realms", None) or {}
    if len(realms) >= 2:
        m = _maybe_arrange_match(game, realms)
        if m:
            msgs.append(m)
    msgs.extend(_blood_ties(game, realms))
    if len(msgs) > MAX_MESSAGES:
        msgs = random.sample(msgs, MAX_MESSAGES)
    return msgs


def _eligible(realm, gender: Optional[str] = None) -> List:
    out = []
    for c in realm.characters:
        if not c.is_alive or c.age < 16 or c.age > 50 or c.id in _married_ids:
            continue
        if c.id == realm.ruler.id:
            continue
        if gender and c.gender != gender:
            continue
        out.append(c)
    return out


def _maybe_arrange_match(game, realms) -> Optional[str]:
    global wedding_count
    if random.random() >= MARRIAGE_CHANCE:
        return None
    dm = game.diplomacy_manager
    names = list(realms)
    random.shuffle(names)
    for i, civ_a in enumerate(names):
        for civ_b in names[i + 1:]:
            if dm.is_at_war(civ_a, civ_b):
                continue
            ra, rb = realms[civ_a], realms[civ_b]
            # Prefer marrying off dynasty kin — that is what binds the houses.
            kin_a = [c for c in _eligible(ra) if c.id in ra.dynasty.all_characters]
            cand_a = kin_a or _eligible(ra)
            if not cand_a:
                continue
            a = random.choice(cand_a)
            want = "Female" if a.gender == "Male" else "Male"
            cand_b = _eligible(rb, want)
            if not cand_b:
                continue
            b = random.choice(cand_b)
            # The match: b joins a's realm and house.
            if b in rb.characters:
                rb.characters.remove(b)
            ra.characters.append(b)
            ra.dynasty.all_characters.setdefault(b.id, b)
            for pos, ch in rb.court.positions.items():
                if ch and ch.id == b.id:
                    rb.court.positions[pos] = None
            modify_opinion(a, b, 40, "marriage")
            modify_opinion(b, a, 40, "marriage")
            _marriages.append((a.id, civ_a, b.id, civ_b))
            _married_ids.update((a.id, b.id))
            wedding_count += 1
            dm.modify_relation(civ_a, civ_b, MARRIAGE_RELATION_BONUS)
            return f"{a.name} weds {b.name} - {civ_a} and {civ_b} are bound by marriage"
    return None


def _blood_ties(game, realms) -> List[str]:
    """Living cross-civ couples slowly pull their realms together."""
    msgs = []
    dm = game.diplomacy_manager
    chars = {c.id: c for realm in realms.values() for c in realm.characters}
    for rec in list(_marriages):
        id_a, civ_a, id_b, civ_b = rec
        a, b = chars.get(id_a), chars.get(id_b)
        if not a or not b or not a.is_alive or not b.is_alive:
            _marriages.remove(rec)
            _married_ids.discard(id_a)
            _married_ids.discard(id_b)
            continue
        if dm.is_at_war(civ_a, civ_b):
            continue
        if game.state.turn % BLOOD_TIE_INTERVAL == 0:
            dm.modify_relation(civ_a, civ_b, BLOOD_TIE_BONUS)
            if dm.get_relation(civ_a, civ_b) >= ALLIANCE_AT and not dm.is_allied(civ_a, civ_b):
                dm.make_pact(civ_a, civ_b, "alliance")
                msgs.append(f"Blood ties seal an ALLIANCE between {civ_a} and {civ_b}")
    return msgs