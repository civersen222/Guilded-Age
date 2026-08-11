"""Court appointment and dismissal actions.

Handles the two verbs for the House tab: appoint a man to a court seat,
dismiss the man in a court seat.  Dismissal costs standing based on the
man's rank in the line of succession.
"""

from __future__ import annotations

from gilded.society.court import CourtPosition
from gilded.society.succession import succession_order
from gilded.society.characters import modify_opinion


# ── standing cost helpers ─────────────────────────────────────────────────────

def _dismissal_standing(char_id: str, realm) -> int:
    """Return the standing cost for dismissing a character from a court seat.

    Cost is based on rank in the line of succession: nearer the throne costs more.
    A man not in the line at all costs 1 (cheapest possible).
    """
    order = succession_order(realm)
    if not order:
        return 1
    for rank, candidate in enumerate(order):
        if isinstance(candidate, dict):
            cid = candidate["char_id"]
        else:
            cid = candidate.id
        if cid == char_id:
            cost = max(1, 7 - min(rank, 6))
            return cost
    return 1


_POSITION_KEYS = {p.value.lower().replace(" ", "_"): p for p in CourtPosition}


def _get_living_blood_relatives(char, realm):
    """Return living parents, children, and siblings of a character."""
    relatives = []
    all_chars = {cid: c for cid, c in realm.dynasty.all_characters.items() if c.is_alive}

    for pid in char.parent_ids:
        if pid in all_chars:
            relatives.append(all_chars[pid])

    for c in all_chars.values():
        if char.id in c.parent_ids:
            relatives.append(c)

    for pid in char.parent_ids:
        for c in all_chars.values():
            if c.id != char.id and pid in c.parent_ids:
                relatives.append(c)

    return relatives


# ── dismiss verb ──────────────────────────────────────────────────────────────

def _dismiss_seat_eligible(game, house, action):
    position_key = action.get("dismiss_seat")
    if position_key is None or position_key not in _POSITION_KEYS:
        return False, "Invalid court position."

    realm = game.realms[house]
    position = _POSITION_KEYS[position_key]
    existing = realm.court.positions.get(position)
    if existing is None:
        return False, f"{position.value} is vacant."

    if game.attention.get(house, 0) <= 0:
        return False, "You have no attention left this turn."

    return True, ""


def _dismiss_seat_dispatch(game, house, view, action):
    position_key = action["dismiss_seat"]
    realm = game.realms[house]
    position = _POSITION_KEYS[position_key]

    char = realm.court.dismiss(position)
    if char is None:
        return [f"{position.value} is already vacant."]

    standing_cost = _dismissal_standing(char.id, realm)
    modify_opinion(char, realm.ruler, -standing_cost,
                   f"Dismissed from {position.value}")

    relative_hit = max(1, standing_cost // 2)
    relatives = _get_living_blood_relatives(char, realm)
    for relative in relatives:
        modify_opinion(relative, realm.ruler, -relative_hit,
                       f"{char.name} dismissed from {position.value}")

    lines = [f"{char.name} dismissed from {position.value}."]
    if relatives:
        rel_names = ", ".join(r.name for r in relatives)
        lines.append(f"Relatives affected: {rel_names}.")
    return lines


# ── open appointment picker ───────────────────────────────────────────────────

def _open_appointment_picker_eligible(game, house, action):
    position_key = action.get("open_appointment_picker")
    if position_key is None or position_key not in _POSITION_KEYS:
        return False, "Invalid court position."

    realm = game.realms[house]
    position = _POSITION_KEYS[position_key]
    existing = realm.court.positions.get(position)
    if existing is not None:
        return False, f"{position.value} is already held by {existing.name}."

    return True, ""


def _open_appointment_picker_dispatch(game, house, view, action):
    return []


# ── close appointment picker ──────────────────────────────────────────────────

def _close_appointment_picker_eligible(game, house, action):
    return True, ""


def _close_appointment_picker_dispatch(game, house, view, action):
    return []


# ── appoint verb ──────────────────────────────────────────────────────────────

def _appoint_to_seat_eligible(game, house, action):
    position_key = action.get("appoint_to_seat")
    char_id = action.get("char_id")
    if position_key is None or position_key not in _POSITION_KEYS:
        return False, "Invalid court position."
    if char_id is None:
        return False, "No character selected."

    realm = game.realms[house]
    position = _POSITION_KEYS[position_key]

    existing = realm.court.positions.get(position)
    if existing is not None:
        return False, f"{position.value} is already held by {existing.name}."

    char = None
    for c in realm.dynasty.all_characters.values():
        if c.id == char_id:
            char = c
            break
    if char is None or not char.is_alive:
        return False, "That person cannot be appointed."

    if char.id == realm.ruler.id:
        return False, "The ruler cannot hold a court seat."

    for pos, holder in realm.court.positions.items():
        if holder and holder.id == char_id:
            return False, f"{char.name} already holds {pos.value}."

    if game.attention.get(house, 0) <= 0:
        return False, "You have no attention left this turn."

    return True, ""


def _appoint_to_seat_dispatch(game, house, view, action):
    position_key = action["appoint_to_seat"]
    char_id = action["char_id"]

    realm = game.realms[house]
    position = _POSITION_KEYS[position_key]

    char = None
    for c in realm.dynasty.all_characters.values():
        if c.id == char_id:
            char = c
            break

    realm.court.appoint(position, char, game.turn)
    return [f"{char.name} appointed {position.value}."]


# ── candidate pool helper ─────────────────────────────────────────────────────

def court_appointment_candidates(game, house, position_key):
    """Return eligible characters who could take the given court seat."""
    if position_key not in _POSITION_KEYS:
        return []
    realm = game.realms[house]
    court = realm.court
    court_ids = {ch.id for ch in court.positions.values() if ch}
    pool = [ch for ch in realm.dynasty.all_characters.values()
            if ch.is_alive and ch.id != realm.ruler.id
            and ch.id not in court_ids]
    pool.sort(key=lambda ch: ch.name)
    return pool


def _get_appointment_pool(realm):
    """Return living dynasty members eligible for court appointment."""
    court = realm.court
    court_ids = {ch.id for ch in court.positions.values() if ch}
    pool = [ch for ch in realm.dynasty.all_characters.values()
            if ch.is_alive and ch.id != realm.ruler.id
            and ch.id not in court_ids]
    pool.sort(key=lambda ch: ch.name)
    return pool
