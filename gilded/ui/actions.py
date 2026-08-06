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


def _defend_buyout_eligible(game, house, action):
    if _no_attention(game, house):
        return False, _attention_reason()
    payload = action.get("defend_buyout")
    if not isinstance(payload, (list, tuple)) or len(payload) < 2:
        return False, "No buyout target specified."
    eid, outside_id = payload[0], payload[1]
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return False, "The enterprise no longer exists."
    from gilded.society.shares import stake_cost
    by_id = {c.id: c for r in game.realms.values() for c in r.characters}
    seller = by_id.get(outside_id)
    if seller is None:
        return False, "The stakeholder is not found."
    pct = ent.ledger.get(outside_id, 0.0)
    if pct <= 0:
        return False, f"{seller.name} has no stake in {ent.name}."
    from gilded.houses import House
    house_obj: House = game.houses[house]
    from gilded.docket import _fmt_gold
    quote = stake_cost(ent, pct, game)
    if house_obj.treasury < quote:
        return False, f"House {house} cannot afford the buyout ({_fmt_gold(quote)} gold needed, {_fmt_gold(house_obj.treasury)} in treasury)"
    return True, ""


def _defend_buyout_dispatch(game, house, view, action):
    from gilded.docket import INITIATIVES, initiative
    from gilded.ai import _executor_for
    from gilded.chassis import TurnEvent
    payload = action["defend_buyout"]
    eid, outside_id = payload[0], payload[1]
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return []
    pct = ent.ledger.get(outside_id, 0.0)
    domain = INITIATIVES["buy_shares"][0]
    realm = game.realms[house]
    executor = _executor_for(game, realm, domain)
    game.attention[house] -= 1
    lines = initiative(game, house, "buy_shares", executor, eid=eid, seller_id=outside_id, pct=pct)
    for line in lines:
        game.events.append(TurnEvent(line, "ledger", house))
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


def _close_found_picker_eligible(game, house, action):
    return True, ""


def _close_found_picker_dispatch(game, house, view, action):
    view._found_picker = None
    view._found_picker_hits.clear()
    return []


def _close_share_picker_eligible(game, house, action):
    return True, ""


def _close_share_picker_dispatch(game, house, view, action):
    view._share_picker = None
    view._share_picker_hits.clear()
    return []


def _takeover_reach(game, target_house):
    """How much of `target_house` is genuinely for sale.

    The combined average stake its disloyal kin hold across its enterprises.
    This is the campaign's ceiling, and `house_stake` scores progress on the
    same scale, so the two numbers can honestly be shown side by side.
    """
    from gilded.society.realm import disloyal_shareholders
    ents = [e for e in game.enterprises if e.house == target_house]
    if not ents:
        return 0.0
    sellers = disloyal_shareholders(game.realms[target_house], game.enterprises)
    return sum(sum(e.ledger.get(s.id, 0.0) for e in ents)
               for s in sellers) / len(ents)


def _running_takeover(game, house, target_house):
    """The player's unfinished campaign against `target_house`, or None."""
    return next((t for t in game.takeovers
                 if t.buyer_house == house and t.target_house == target_house
                 and not t.complete), None)


def _attack_takeover_eligible(game, house, action):
    target = action.get("attack_takeover")
    if target not in game.houses or target == house:
        return False, "There is no such House to buy into."
    if _running_takeover(game, house, target) is not None:
        return False, (f"A quiet buying campaign against House {target} is "
                       f"already under way.")
    if _no_attention(game, house):
        return False, _attention_reason()
    if _takeover_reach(game, target) <= 0.0:
        return False, (f"No one in House {target} is disloyal enough to sell "
                       f"you a share.")
    return True, ""


def _attack_takeover_dispatch(game, house, view, action):
    from gilded.docket import INITIATIVES, initiative
    from gilded.ai import _executor_for
    from gilded.chassis import TurnEvent
    target = action["attack_takeover"]
    realm = game.realms[house]
    executor = _executor_for(game, realm, INITIATIVES["start_takeover"][0])
    game.attention[house] -= 1
    lines = initiative(game, house, "start_takeover", executor,
                       target_house=target)
    for line in lines:
        game.events.append(TurnEvent(line, "ledger", house))
    return lines


# ── buy shares ───────────────────────────────────────────────────────────────

def _buy_shares_eligible(game, house, action):
    payload = action.get("buy_shares")
    # OPEN form — bare int (chooser click)
    if isinstance(payload, int):
        return True, ""
    # DECIDE form — (eid, char_id, pct) tuple
    if not isinstance(payload, (list, tuple)) or len(payload) < 3:
        return False, "Malformed buy_shares action."
    eid, char_id, pct = payload[0], payload[1], payload[2]
    if pct <= 0:
        return False, "Percentage must be positive."
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return False, "The enterprise no longer exists."
    if _no_attention(game, house):
        return False, _attention_reason()
    # Counterparty check
    counterparties = buy_share_counterparties(game, house, eid)
    cp_ids = {c["id"] for c in counterparties}
    if char_id not in cp_ids:
        return False, f"{char_id} is not a valid seller for this enterprise."
    # Size ladder check
    seller_entry = next((c for c in counterparties if c["id"] == char_id), None)
    if seller_entry is None:
        return False, "Seller not found."
    ladder = share_size_ladder(game, house, eid, char_id)
    offerable_rungs = [r for r in ladder if r["offerable"]]
    offerable_pcts = {r["pct"] for r in offerable_rungs}
    if pct not in offerable_pcts:
        # Find the reason from the non-offerable rung
        blocked = next((r for r in ladder if r["pct"] == pct), None)
        if blocked and blocked.get("reason"):
            return False, blocked["reason"]
        return False, f"That size is not offerable."
    # Affordability
    from gilded.society.shares import stake_cost
    from gilded.houses import House
    from gilded.docket import _fmt_gold
    house_obj = game.houses[house]
    quote = stake_cost(ent, pct, game)
    if house_obj.treasury < quote:
        return False, f"Cannot afford ({_fmt_gold(quote)} needed, {_fmt_gold(house_obj.treasury)} in treasury)"
    return True, ""


def _buy_shares_dispatch(game, house, view, action):
    from gilded.docket import INITIATIVES, initiative
    from gilded.ai import _executor_for
    from gilded.chassis import TurnEvent
    payload = action["buy_shares"]
    # OPEN form — bare int: pure, record on view, do nothing else
    if isinstance(payload, int):
        view._share_picker = {"direction": "buy", "eid": payload}
        return []
    # DECIDE form — (eid, char_id, pct)
    eid, char_id, pct = payload[0], payload[1], payload[2]
    ok, why = _buy_shares_eligible(game, house, action)
    if not ok:
        return [f"Refused: {why}"]
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return []
    domain = INITIATIVES["buy_shares"][0]
    realm = game.realms[house]
    executor = _executor_for(game, realm, domain)
    game.attention[house] -= 1
    lines = initiative(game, house, "buy_shares", executor, eid=eid, seller_id=char_id, pct=pct)
    for line in lines:
        game.events.append(TurnEvent(line, "ledger", house))
    return lines


# ── sell shares ──────────────────────────────────────────────────────────────

def _sell_shares_eligible(game, house, action):
    payload = action.get("sell_shares")
    # OPEN form — bare int (chooser click)
    if isinstance(payload, int):
        return True, ""
    # DECIDE form — (eid, char_id, pct) tuple
    if not isinstance(payload, (list, tuple)) or len(payload) < 3:
        return False, "Malformed sell_shares action."
    eid, char_id, pct = payload[0], payload[1], payload[2]
    if pct <= 0:
        return False, "Percentage must be positive."
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return False, "The enterprise no longer exists."
    if _no_attention(game, house):
        return False, _attention_reason()
    realm = game.realms[house]
    # Counterparty check
    counterparties = sell_share_counterparties(game, house, eid)
    cp_ids = {c["id"] for c in counterparties}
    if char_id not in cp_ids:
        return False, f"{char_id} is not a valid buyer for this enterprise."
    # Size ladder check
    buyer_entry = next((c for c in counterparties if c["id"] == char_id), None)
    if buyer_entry is None:
        return False, "Buyer not found."
    ladder = share_size_ladder(game, house, eid, realm.ruler.id, char_id)
    offerable_rungs = [r for r in ladder if r["offerable"]]
    offerable_pcts = {r["pct"] for r in offerable_rungs}
    if pct not in offerable_pcts:
        blocked = next((r for r in ladder if r["pct"] == pct), None)
        if blocked and blocked.get("reason"):
            return False, blocked["reason"]
        return False, f"That size is not offerable."
    return True, ""


def _sell_shares_dispatch(game, house, view, action):
    from gilded.docket import INITIATIVES, initiative
    from gilded.ai import _executor_for
    from gilded.chassis import TurnEvent
    payload = action["sell_shares"]
    # OPEN form — bare int: pure, record on view, do nothing else
    if isinstance(payload, int):
        view._share_picker = {"direction": "sell", "eid": payload}
        return []
    # DECIDE form — (eid, char_id, pct)
    eid, char_id, pct = payload[0], payload[1], payload[2]
    ok, why = _sell_shares_eligible(game, house, action)
    if not ok:
        return [f"Refused: {why}"]
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return []
    domain = INITIATIVES["sell_shares"][0]
    realm = game.realms[house]
    executor = _executor_for(game, realm, domain)
    game.attention[house] -= 1
    lines = initiative(game, house, "sell_shares", executor, eid=eid, buyer_id=char_id, pct=pct)
    for line in lines:
        game.events.append(TurnEvent(line, "ledger", house))
    return lines


# ── found enterprise ─────────────────────────────────────────────────────────

def _get_available_charters(game, house):
    """Return list of (kind, province_pid, province_name, cost) for charters available to house."""
    from gilded.enterprises import ENTERPRISE_TYPES
    from gilded.ai import ENDOWMENT_KIND
    existing = {(e.kind, e.province) for e in game.enterprises}
    owned_pids = {p.pid for p in game.provinces_of(house)}
    charters = []
    for kind, etype in ENTERPRISE_TYPES.items():
        endow_needed = etype[0]  # needs-endowment
        cost = etype[3]          # found_cost
        for pid in owned_pids:
            if (kind, pid) in existing:
                continue
            prov = game.atlas.provinces.get(pid)
            if prov is None:
                continue
            if endow_needed is None:
                # bank needs no endowment — available in every owned province
                charters.append((kind, pid, prov.name, cost))
            elif endow_needed in prov.endowments:
                charters.append((kind, pid, prov.name, cost))
    charters.sort(key=lambda c: (c[3], c[2], c[0]))  # sort by cost, then name, then kind
    return charters


def _found_enterprise_eligible(game, house, action):
    if _no_attention(game, house):
        return False, _attention_reason()
    charters = _get_available_charters(game, house)
    if not charters:
        return False, "There are no charters available."
    house_obj = game.houses.get(house)
    if house_obj is None:
        return False, "House not found."
    # If a specific charter is targeted, check its cost
    val = action.get("found_enterprise")
    if isinstance(val, tuple):
        kind, pid = val
        target = None
        for c in charters:
            if c[0] == kind and c[1] == pid:
                target = c
                break
        if target is None:
            return False, "That charter is not available."
        if house_obj.treasury < target[3]:
            return False, f"The House cannot afford this charter ({int(target[3])} gold)."
    else:
        cheapest = min(c[3] for c in charters)
        if house_obj.treasury < cheapest:
            return False, f"The House cannot afford the cheapest charter ({int(cheapest)} gold)."
    return True, ""


def _found_enterprise_dispatch(game, house, view, action):
    """Dispatch for the Found Enterprise button or a charter row click.

    If the action carries a (kind, pid) tuple, actually found the enterprise.
    If it carries just True, open the chooser.
    """
    val = action["found_enterprise"]
    if isinstance(val, tuple):
        # Row click — actually found the enterprise
        kind, pid = val
        # Guard: check affordability before proceeding
        ok, why = _found_enterprise_eligible(game, house, action)
        if not ok:
            return [f"Refused: {why}"]
        from gilded.docket import INITIATIVES, initiative
        from gilded.ai import _executor_for
        from gilded.chassis import TurnEvent
        realm = game.realms[house]
        executor = _executor_for(game, realm, INITIATIVES["found_enterprise"][0])
        game.attention[house] -= 1
        lines = initiative(game, house, "found_enterprise", executor,
                           kind=kind, province_pid=pid)
        for line in lines:
            game.events.append(TurnEvent(line, "ledger", house))
        view._found_picker = None
        view._found_picker_hits.clear()
        return lines
    else:
        # Button click — open the chooser
        view._found_picker = True
        return []


# ── view-local keys (click already mutated the view) ─────────────────────────

def _noop_eligible(game, house, action):
    return True, ""


def _noop_dispatch(game, house, view, action):
    return []


# ── registry ─────────────────────────────────────────────────────────────────

# ── share trade helpers (I4d2b1) ──────────────────────────────────────────────

def buy_share_counterparties(game, house, eid):
    """Return people the House could buy shares FROM in enterprise *eid*.

    Returns list of dicts with keys: id, name, stake_pct, cost.
    Excludes the realm's ruler.  Built from the ledger, resolved across all realms.
    """
    from gilded.society.shares import stake_cost
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return []
    realm = game.realms[house]
    ruler_id = realm.ruler.id
    by_id = {c.id: c for r in game.realms.values() for c in r.characters}
    options = []
    for char_id, pct in ent.ledger.items():
        if pct <= 0:
            continue
        if char_id == ruler_id:
            continue
        char = by_id.get(char_id)
        if char is None:
            continue
        cost = stake_cost(ent, pct, game)
        options.append({"id": char_id, "name": char.name, "stake_pct": pct, "cost": cost})
    options.sort(key=lambda o: (-o["stake_pct"], o["name"]))
    return options


def sell_share_counterparties(game, house, eid):
    """Return people the House's ruler could sell shares TO in enterprise *eid*.

    Returns list of dicts with keys: id, name, gold.
    Excludes the ruler.  Candidates must be alive, adult, and hold enough gold
    to buy at least 1.00% of the enterprise.  Sorted richest first.
    """
    from gilded.society.shares import stake_cost
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return []
    realm = game.realms[house]
    ruler_id = realm.ruler.id
    min_cost = stake_cost(ent, 1.0, game)
    by_id = {c.id: c for r in game.realms.values() for c in r.characters}
    options = []
    for char in by_id.values():
        if char.id == ruler_id:
            continue
        if not char.is_alive:
            continue
        if char.age < 16:
            continue
        if char.gold_reserve < min_cost:
            continue
        options.append({"id": char.id, "name": char.name, "gold": char.gold_reserve})
    options.sort(key=lambda o: (-o["gold"], o["name"]))
    return options


def share_size_ladder(game, house, eid, seller_id, buyer_id=None):
    """Return slice sizes that can be transacted for a share trade.

    *seller_id* is the id of the person selling.
    *buyer_id* is the id of the person buying (for a sell action).
    When *buyer_id* is None, the trade is treated as a BUY (house treasury pays).

    Returns list of dicts with keys: pct, cost, offerable, reason.
    Canonical sizes: 1, 5, 10, 25, 35, 50, 75, 100.
    The seller's whole stake is always included so any holder can be bought out.
    """
    from gilded.society.shares import stake_cost
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return []
    realm = game.realms[house]
    house_obj = game.houses[house]
    available = ent.ledger.get(seller_id, 0.0)
    canonical = [1, 5, 10, 25, 35, 50, 75, 100]
    # R-2: add the seller's whole stake as a rung so any holder can be bought out
    # but a stake of zero is not a slice anyone can trade
    rungs = sorted(set(canonical + [available] if available > 0 else canonical))
    is_buy = buyer_id is None
    if is_buy:
        purse = house_obj.treasury
    else:
        by_id = {c.id: c for r in game.realms.values() for c in r.characters}
        buyer = by_id.get(buyer_id)
        purse = buyer.gold_reserve if buyer else 0.0
    options = []
    for pct in rungs:
        cost = stake_cost(ent, pct, game)
        if pct > available:
            options.append({"pct": pct, "cost": cost, "offerable": False,
                           "reason": f"Seller only holds {available:.1f}%"})
        elif cost > purse:
            purse_name = "House treasury" if is_buy else "buyer"
            options.append({"pct": pct, "cost": cost, "offerable": False,
                           "reason": f"{purse_name} cannot afford {cost:.2f} gold (has {purse:.2f})"})
        else:
            options.append({"pct": pct, "cost": cost, "offerable": True, "reason": ""})
    # Fully-refused ladder: state the fact once, not once per rung
    if not any(o["offerable"] for o in options):
        reasons = [o["reason"] for o in options if o["reason"]]
        if reasons and len(set(reasons)) == 1:
            # All refused for the same reason — say it on the first rung only
            for o in options:
                if not o["offerable"]:
                    o["reason"] = ""
            options[0]["reason"] = reasons[0]
    return options


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
    "defend_buyout": PlayerAction(
        key="defend_buyout", label="Defend Buyout", domain="commerce",
        attention_cost=1, gold_cost=0,
        eligible=_defend_buyout_eligible, dispatch=_defend_buyout_dispatch,
    ),
    "attack_takeover": PlayerAction(
        key="attack_takeover", label="Hostile Takeover", domain="capital",
        attention_cost=1, gold_cost=0,
        eligible=_attack_takeover_eligible, dispatch=_attack_takeover_dispatch,
    ),
    "buy_shares": PlayerAction(
        key="buy_shares", label="Buy Shares", domain="capital",
        attention_cost=1, gold_cost=0,
        eligible=_buy_shares_eligible, dispatch=_buy_shares_dispatch,
    ),
    "sell_shares": PlayerAction(
        key="sell_shares", label="Sell Shares", domain="capital",
        attention_cost=1, gold_cost=0,
        eligible=_sell_shares_eligible, dispatch=_sell_shares_dispatch,
    ),
    "found_enterprise": PlayerAction(
        key="found_enterprise", label="Found Enterprise", domain="capital",
        attention_cost=1, gold_cost=0,
        eligible=_found_enterprise_eligible, dispatch=_found_enterprise_dispatch,
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
    "close_found_picker": PlayerAction(
        key="close_found_picker", label="Close Found Picker", domain="view",
        attention_cost=0, gold_cost=0,
        eligible=_close_found_picker_eligible, dispatch=_close_found_picker_dispatch,
    ),
    "close_share_picker": PlayerAction(
        key="close_share_picker", label="Close Share Picker", domain="view",
        attention_cost=0, gold_cost=0,
        eligible=_close_share_picker_eligible, dispatch=_close_share_picker_dispatch,
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
