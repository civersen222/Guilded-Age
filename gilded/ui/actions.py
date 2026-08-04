"""Player action registry — one entry per emitted key.

Every action key the UI emits has exactly one entry here.  `eligible` decides
whether the player may act; `dispatch` performs the verb and returns narration
lines.  Neither imports the UI modules that call them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


# ── dataclass ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlayerAction:
    key: str
    label: str
    domain: str
    attention_cost: int
    gold_cost: int
    eligible: Callable  # (game, house, action) -> (bool, reason)
    dispatch: Callable  # (game, house, view, action) -> list[str]


# ── helpers (shared across game verbs) ───────────────────────────────────────

def _no_attention(game, house):
    """Return True if the house has no attention left."""
    return game.attention.get(house, 0) <= 0


def _attention_reason():
    return "You have no attention left this turn."


# ── game verbs (moved from app.py) ───────────────────────────────────────────

def _end_turn_eligible(game, house, action):
    if game.game_over is not None:
        return False, "The game is over."
    return True, ""


def _end_turn_dispatch(game, house, view, action):
    from gilded.dashboard import scoreboard
    pre = scoreboard(game, house)
    game.end_turn()
    view.prev_board = pre
    view.active_tab = "Briefing"
    return []


def _place_informant_eligible(game, house, action):
    target = action.get("place_informant")
    if target is None:
        return False, "No target selected."
    if target not in game.houses or target == house:
        return False, "You cannot place an informant there."
    if _no_attention(game, house):
        return False, _attention_reason()
    return True, ""


def _place_informant_dispatch(game, house, view, action):
    from gilded.docket import initiative
    target = action["place_informant"]
    realm = game.realms[house]
    executor = _executor_for(game, realm, "diplomacy")
    game.attention[house] -= 1
    initiative(game, house, "establish_informant", executor, target_house=target)
    return []


# Cache for _executor_for import — lazy to avoid circular deps
_executor_for = None

def _get_executor_for():
    global _executor_for
    if _executor_for is None:
        from gilded.ai import _executor_for as _ef
        _executor_for = _ef
    return _executor_for


# Override the above — use the imported function directly
def _place_informant_dispatch(game, house, view, action):
    from gilded.docket import initiative
    from gilded.ai import _executor_for
    target = action["place_informant"]
    realm = game.realms[house]
    executor = _executor_for(game, realm, "diplomacy")
    game.attention[house] -= 1
    initiative(game, house, "establish_informant", executor, target_house=target)
    return []


def _set_stance_eligible(game, house, action):
    return True, ""


def _set_stance_dispatch(game, house, view, action):
    key, value = action["set_stance"]
    game.directives[house].set_stance(key, value)
    return []


def _rule_eligible(game, house, action):
    if _no_attention(game, house):
        return False, _attention_reason()
    pid = action.get("rule")
    if pid is None:
        return False, "No petition selected."
    petition = next((p for p in game.docket_by_house.get(house, [])
                     if p.pid == pid[0]), None)
    if petition is None:
        return False, "The petition is no longer on your docket."
    return True, ""


def _rule_dispatch(game, house, view, action):
    from gilded.docket import rule as docket_rule
    pid, option_key, exec_id = action["rule"]
    petition = next(p for p in game.docket_by_house.get(house, [])
                    if p.pid == pid)
    # Reconstruct executor from exec_id (same as _executor_by_id)
    realm = game.realms[house]
    if exec_id is not None:
        from gilded.ai import _executor_for
        executor = next(
            (c for c in realm.characters if c.is_alive and c.id == exec_id),
            _executor_for(game, realm, petition.domain)
        )
    else:
        from gilded.ai import _executor_for
        executor = _executor_for(game, realm, petition.domain)
    game.attention[house] -= 1
    docket_rule(game, petition, option_key, executor)
    game.docket_by_house[house].remove(petition)
    return []


def _expand_enterprise_eligible(game, house, action):
    if _no_attention(game, house):
        return False, _attention_reason()
    eid = action.get("expand_enterprise")
    if eid is None:
        return False, "No enterprise selected."
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return False, "The enterprise no longer exists."
    if ent.house != house:
        return False, "You do not own this enterprise."
    return True, ""


def _expand_enterprise_dispatch(game, house, view, action):
    from gilded.docket import INITIATIVES, initiative
    from gilded.ai import _executor_for
    from gilded.chassis import TurnEvent
    eid = action["expand_enterprise"]
    venture = next(e for e in game.enterprises if e.eid == eid and e.house == house)
    domain = INITIATIVES["expand_enterprise"][0]
    realm = game.realms[house]
    executor = _executor_for(game, realm, domain)
    game.attention[house] -= 1
    lines = initiative(game, house, "expand_enterprise", executor, eid=eid)
    for line in lines:
        game.events.append(TurnEvent(line, "ledger", house))
    return lines


def _appoint_director_eligible(game, house, action):
    if _no_attention(game, house):
        return False, _attention_reason()
    eid = action.get("appoint_director")
    if eid is None:
        return False, "No enterprise selected."
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return False, "The enterprise no longer exists."
    char_id = action.get("char_id")
    if char_id is None:
        return False, "No character selected."
    realm = game.realms[house]
    char = next((c for c in realm.characters if c.is_alive and c.id == char_id), None)
    if char is None:
        return False, "The character is not available."
    return True, ""


def _appoint_director_dispatch(game, house, view, action):
    from gilded.docket import INITIATIVES, initiative
    from gilded.ai import _executor_for
    from gilded.chassis import TurnEvent
    eid = action["appoint_director"]
    char_id = action["char_id"]
    try:
        venture = next(e for e in game.enterprises if e.eid == eid and e.house == house)
    except StopIteration:
        return []
    domain = INITIATIVES["appoint_director"][0]
    realm = game.realms[house]
    executor = _executor_for(game, realm, domain)
    game.attention[house] -= 1
    lines = initiative(game, house, "appoint_director", executor, eid=eid, char_id=char_id)
    for line in lines:
        game.events.append(TurnEvent(line, "ledger", house))
    view._director_picker = None
    view._director_picker_hits.clear()
    return lines


# ── view verbs ────────────────────────────────────────────────────────────────

def _toggle_narrate_eligible(game, house, action):
    return True, ""


def _toggle_narrate_dispatch(game, house, view, action):
    view.narrate_on = not view.narrate_on
    return []


def _close_director_picker_eligible(game, house, action):
    return True, ""


def _close_director_picker_dispatch(game, house, view, action):
    view._director_picker = None
    view._director_picker_hits.clear()
    return []


# ── view-local keys (click already mutated the view) ─────────────────────────

def _noop_eligible(game, house, action):
    return True, ""


def _noop_dispatch(game, house, view, action):
    return []


# ── registry ─────────────────────────────────────────────────────────────────

ACTIONS: dict[str, PlayerAction] = {
    # game verbs
    "end_turn": PlayerAction(
        key="end_turn", label="End Turn", domain="view",
        attention_cost=0, gold_cost=0,
        eligible=_end_turn_eligible, dispatch=_end_turn_dispatch,
    ),
    "place_informant": PlayerAction(
        key="place_informant", label="Place Informant", domain="diplomacy",
        attention_cost=1, gold_cost=0,
        eligible=_place_informant_eligible, dispatch=_place_informant_dispatch,
    ),
    "set_stance": PlayerAction(
        key="set_stance", label="Set Stance", domain="policies",
        attention_cost=0, gold_cost=0,
        eligible=_set_stance_eligible, dispatch=_set_stance_dispatch,
    ),
    "rule": PlayerAction(
        key="rule", label="Rule Petition", domain="statecraft",
        attention_cost=1, gold_cost=0,
        eligible=_rule_eligible, dispatch=_rule_dispatch,
    ),
    "expand_enterprise": PlayerAction(
        key="expand_enterprise", label="Expand Enterprise", domain="commerce",
        attention_cost=1, gold_cost=0,
        eligible=_expand_enterprise_eligible, dispatch=_expand_enterprise_dispatch,
    ),
    "appoint_director": PlayerAction(
        key="appoint_director", label="Appoint Director", domain="commerce",
        attention_cost=1, gold_cost=0,
        eligible=_appoint_director_eligible, dispatch=_appoint_director_dispatch,
    ),
    # view verbs
    "toggle_narrate": PlayerAction(
        key="toggle_narrate", label="Toggle Narration", domain="view",
        attention_cost=0, gold_cost=0,
        eligible=_toggle_narrate_eligible, dispatch=_toggle_narrate_dispatch,
    ),
    "close_director_picker": PlayerAction(
        key="close_director_picker", label="Close Director Picker", domain="view",
        attention_cost=0, gold_cost=0,
        eligible=_close_director_picker_eligible, dispatch=_close_director_picker_dispatch,
    ),
    # view-local keys
    "tab": PlayerAction(
        key="tab", label="Switch Tab", domain="view",
        attention_cost=0, gold_cost=0,
        eligible=_noop_eligible, dispatch=_noop_dispatch,
    ),
    "select_province": PlayerAction(
        key="select_province", label="Select Province", domain="view",
        attention_cost=0, gold_cost=0,
        eligible=_noop_eligible, dispatch=_noop_dispatch,
    ),
    "open_director_picker": PlayerAction(
        key="open_director_picker", label="Open Director Picker", domain="view",
        attention_cost=0, gold_cost=0,
        eligible=_noop_eligible, dispatch=_noop_dispatch,
    ),
    "cycle_exec": PlayerAction(
        key="cycle_exec", label="Choose Executor", domain="view",
        attention_cost=0, gold_cost=0,
        eligible=_noop_eligible, dispatch=_noop_dispatch,
    ),
}
