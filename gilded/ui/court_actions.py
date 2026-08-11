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

    if getattr(game, "court_verbs_used", 0) >= 1:
        return False, "You have already used your court action this turn."

    return True, ""


def _dismiss_seat_dispatch(game, house, view, action):
    if getattr(game, "court_verbs_used", 0) >= 1:
        return ["You have already used your court action this turn."]
    position_key = action["dismiss_seat"]
    realm = game.realms[house]
    position = _POSITION_KEYS[position_key]

    char = realm.court.dismiss(position)
    if char is None:
        return [f"{position.value} is already vacant."]

    standing_cost = _dismissal_standing(char.id, realm)
    game.attention[house] = game.attention.get(house, 0) - standing_cost
    game.court_verbs_used = 1
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

    if game.attention.get(house, 0) <= 0:
        return False, "You have no attention left this turn."

    return True, ""


def _open_appointment_picker_dispatch(game, house, view, action):
    """Open the appointment picker — sets view._court_picker so the picker is drawn."""
    if view is not None:
        pk = action.get("open_appointment_picker")
        view._court_picker = pk
    return []


# ── close appointment picker ──────────────────────────────────────────────────

def _close_appointment_picker_eligible(game, house, action):
    return True, ""


def _close_appointment_picker_dispatch(game, house, view, action):
    """Close the appointment picker — clears view._court_picker."""
    if view is not None:
        view._court_picker = None
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

    if getattr(game, "court_verbs_used", 0) >= 1:
        return False, "You have already used your court action this turn."

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

    game.attention[house] = game.attention.get(house, 0) - 1
    game.court_verbs_used = 1
    realm.court.appoint(position, char, game.turn)
    modify_opinion(char, realm.ruler, 5, f"Appointed to {position.value}")

    return [f"{char.name} appointed to {position.value}."]


# ── designate heir verb ───────────────────────────────────────────────────────

def _designate_heir_eligible(game, house, action):
    char_id = action.get("char_id")
    if char_id is None:
        return False, "No character selected."

    realm = game.realms[house]

    # Find the character
    char = None
    for c in realm.dynasty.all_characters.values():
        if c.id == char_id:
            char = c
            break
    if char is None:
        for c in realm.characters:
            if c.id == char_id:
                char = c
                break
    if char is None or not char.is_alive:
        return False, "That person cannot be designated heir."

    if char.id == realm.ruler.id:
        return False, "The ruler cannot be designated heir."

    if game.attention.get(house, 0) <= 0:
        return False, "You have no attention left this turn."

    if getattr(game, "court_verbs_used", 0) >= 1:
        return False, "You have already used your court action this turn."

    return True, ""


def _designate_heir_dispatch(game, house, view, action):
    char_id = action["char_id"]

    realm = game.realms[house]

    # Find the character
    char = None
    for c in realm.dynasty.all_characters.values():
        if c.id == char_id:
            char = c
            break
    if char is None:
        for c in realm.characters:
            if c.id == char_id:
                char = c
                break

    # Clear any existing heir designation
    for c in realm.dynasty.all_characters.values():
        if hasattr(c, "is_heir"):
            c.is_heir = False
    for c in realm.characters:
        if hasattr(c, "is_heir"):
            c.is_heir = False

    # Set the new heir
    char.is_heir = True

    game.attention[house] = game.attention.get(house, 0) - 1
    game.court_verbs_used = 1

    return [f"{char.name} designated as heir."]


# ── Clear heir designation (clear_heir verb) ────────────────────────────────

def _clear_heir_eligible(game, house, action):
    realm = game.realms[house]

    # Check if there's an heir to clear
    has_heir = False
    for c in realm.dynasty.all_characters.values():
        if getattr(c, "is_heir", False):
            has_heir = True
            break
    if not has_heir:
        for c in realm.characters:
            if getattr(c, "is_heir", False):
                has_heir = True
                break
    if not has_heir:
        return False, "No heir currently designated."

    if game.attention.get(house, 0) <= 0:
        return False, "You have no attention left this turn."

    if getattr(game, "court_verbs_used", 0) >= 1:
        return False, "You have already used your court action this turn."

    return True, ""


def _clear_heir_dispatch(game, house, view, action):
    realm = game.realms[house]

    # Clear any existing heir designation
    for c in realm.dynasty.all_characters.values():
        if hasattr(c, "is_heir"):
            c.is_heir = False
    for c in realm.characters:
        if hasattr(c, "is_heir"):
            c.is_heir = False

    game.attention[house] = game.attention.get(house, 0) - 1
    game.court_verbs_used = 1

    return ["Heir designation cleared."]


# ── candidate pool helper ─────────────────────────────────────────────────────

def court_appointment_candidates(game, house, position_key):
    """Return eligible characters who could take the given court seat."""
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
