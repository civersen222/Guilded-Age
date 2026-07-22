"""Cross-civ marriages bind realms together (Phase B4)."""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from simulation import modify_opinion, generate_child
from realms import MALE_NAMES, FEMALE_NAMES
from dispositions import PAIRS
from shares import transfer_shares

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


@dataclass
class MarriageContract:
    """Marriage as merger (M45): the terms two houses agree on.

    board_seat is stored for the org chart to consume (Wave OC); the full
    courtship verbs that haggle these terms land in Wave IN.
    """
    alliance: bool = False
    dowry_gold: float = 0.0
    dowry_shares_pct: float = 0.0
    matrilineal: bool = False   # children register to the mother's House
    board_seat: bool = False


# (char_a_id, char_b_id) -> MarriageContract; marriages arranged elsewhere
# (e.g. the realm popup) have no entry and fall back to a default contract.
_contracts: Dict[tuple, MarriageContract] = {}

_BLOODLINE_KEYS = tuple(k for k, p in PAIRS.items() if p.family == "bloodline")


def bloodline_quality(char) -> float:
    """Desirable bloodline labels sit on the NEGATIVE side of each pair."""
    disp = getattr(char, "dispositions", None) or {}
    return sum(max(0.0, -disp.get(k, 0.0)) for k in _BLOODLINE_KEYS)


def house_power(realm) -> float:
    return float(sum(ent.base_yield for ent in realm.enterprises))


SCANDAL_KEYS = ("honest_deceitful", "temperate_hedonist")


def scandal_discount(char) -> float:
    """Courtship pressure (M64, spec 4.3): what society BELIEVES about a
    person is what the market prices - an exposé craters the persona and
    with it the asking price."""
    persona = getattr(char, "persona", None) or {}
    return sum(max(0.0, persona.get(k, 0.0)) for k in SCANDAL_KEYS) * 0.15


def asking_price(char, realm) -> float:
    """AI valuation: what this hand in marriage costs the other house."""
    return max(1.0, 10.0 + bloodline_quality(char) * 0.5 + house_power(realm)
               - scandal_discount(char))


def _negotiate_contract(ra, rb, a, b) -> MarriageContract:
    """ra's house receives spouse b from rb's house and pays the bride price
    in gold if its ruler can afford it, topping up with shares if not."""
    price = asking_price(b, rb)
    contract = MarriageContract(alliance=True)
    contract.matrilineal = random.random() < 0.25
    contract.board_seat = random.random() < 0.25
    payer = ra.ruler
    if payer.gold_reserve >= price:
        contract.dowry_gold = price
    else:
        contract.dowry_gold = payer.gold_reserve * 0.5
        contract.dowry_shares_pct = min(15.0, max(5.0, (price - contract.dowry_gold) * 0.25))
    return contract


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
            # Marriage as merger (M45): negotiate and apply the contract.
            contract = _negotiate_contract(ra, rb, a, b)
            if contract.dowry_gold > 0:
                ra.ruler.gold_reserve -= contract.dowry_gold
                rb.ruler.gold_reserve += contract.dowry_gold
            if contract.dowry_shares_pct > 0 and ra.enterprises:
                transfer_shares(random.choice(ra.enterprises), ra.ruler.id,
                                rb.ruler.id, contract.dowry_shares_pct)
            _marriages.append((a.id, civ_a, b.id, civ_b))
            _contracts[(a.id, b.id)] = contract
            _married_ids.update((a.id, b.id))
            wedding_count += 1
            dm.modify_relation(civ_a, civ_b,
                               MARRIAGE_RELATION_BONUS + (10 if contract.alliance else 0))
            return f"{a.name} weds {b.name} - {civ_a} and {civ_b} are bound by marriage"
    return None


def arrange_match_between(game, civ_a: str, civ_b: str) -> Optional[str]:
    """A deliberate match between two named Houses (M76): the AI binds a
    friend the way the ambient tick does, but on purpose - kin preferred,
    best bloodline first, the same merger contract."""
    global wedding_count
    realms = getattr(game, "realms", None) or {}
    ra, rb = realms.get(civ_a), realms.get(civ_b)
    if ra is None or rb is None:
        return None
    dm = game.diplomacy_manager
    if dm.is_at_war(civ_a, civ_b):
        return None
    kin_a = [c for c in _eligible(ra) if c.id in ra.dynasty.all_characters]
    cand_a = kin_a or _eligible(ra)
    if not cand_a:
        return None
    a = max(cand_a, key=bloodline_quality)
    want = "Female" if a.gender == "Male" else "Male"
    cand_b = _eligible(rb, want)
    if not cand_b:
        return None
    b = max(cand_b, key=bloodline_quality)
    if b in rb.characters:
        rb.characters.remove(b)
    ra.characters.append(b)
    ra.dynasty.all_characters.setdefault(b.id, b)
    for pos, ch in rb.court.positions.items():
        if ch and ch.id == b.id:
            rb.court.positions[pos] = None
    modify_opinion(a, b, 40, "marriage")
    modify_opinion(b, a, 40, "marriage")
    contract = _negotiate_contract(ra, rb, a, b)
    if contract.dowry_gold > 0:
        ra.ruler.gold_reserve -= contract.dowry_gold
        rb.ruler.gold_reserve += contract.dowry_gold
    if contract.dowry_shares_pct > 0 and ra.enterprises:
        transfer_shares(random.choice(ra.enterprises), ra.ruler.id,
                        rb.ruler.id, contract.dowry_shares_pct)
    _marriages.append((a.id, civ_a, b.id, civ_b))
    _contracts[(a.id, b.id)] = contract
    _married_ids.update((a.id, b.id))
    wedding_count += 1
    dm.modify_relation(civ_a, civ_b,
                       MARRIAGE_RELATION_BONUS + (10 if contract.alliance else 0))
    return f"{a.name} weds {b.name} - {civ_a} and {civ_b} are bound by marriage"


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
            _contracts.pop((id_a, id_b), None)
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
            # Children of the union register to the contract's House (M45).
            contract = _contracts.get((id_a, id_b)) or MarriageContract()
            mother = a if a.gender == "Female" else b
            father = b if mother is a else a
            if mother.age <= 45 and random.random() < 0.25:
                parent = mother if contract.matrilineal else father
                house_civ = (civ_a if parent is a else civ_b)
                home = realms.get(house_civ)
                if home is not None:
                    child = generate_child(
                        f"{random.choice(MALE_NAMES + FEMALE_NAMES)} of {house_civ}",
                        father, mother)
                    child.age = 0
                    child.age_progress.current_age = 0
                    home.dynasty.add_member(child, parent.id)
                    home.characters.append(child)
                    game.characters.append(child)
                    msgs.append(f"A child of the union, {child.name}, is born into House {house_civ}")
    return msgs


def get_state() -> dict:
    """Snapshot the module-level marriage registries (M78)."""
    return {"marriages": list(_marriages), "contracts": dict(_contracts),
            "married_ids": set(_married_ids), "wedding_count": wedding_count}


def set_state(state: dict) -> None:
    """Restore the module-level marriage registries (M78)."""
    global wedding_count
    _marriages[:] = state.get("marriages", [])
    _contracts.clear()
    _contracts.update(state.get("contracts", {}))
    _married_ids.clear()
    _married_ids.update(state.get("married_ids", set()))
    wedding_count = state.get("wedding_count", 0)