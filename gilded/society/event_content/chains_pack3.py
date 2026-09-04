"""Chain pack 3 (C7, content depth): eleven more chains, all >= 3 steps.

Triggers read the live world - a marriage, a death, a war front, a tide,
an heir's stress, a House's legitimacy - never a turn number. Deterministic:
no RNG anywhere in this module.
"""

from typing import Any, Dict, List, Optional

from gilded.society.event_chains import ChainDef, ChainStep
from gilded.society.event_content.chains_pack1 import (
    _cities_of, _drain_legitimacy, _provinces)


def _by_id(game: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for realm in (getattr(game, "realms", None) or {}).values():
        for ch in realm.characters:
            out[ch.id] = ch
    return out


# --- 7. The marriage of convenience ------------------------------------------

def _trig_marriage_bargain(game: Any) -> Optional[Dict[str, Any]]:
    reg = getattr(game, "marriages", None)
    if reg is None or not reg.marriages:
        return None
    by_id = _by_id(game)
    a_id, house_a, b_id, house_b = reg.marriages[-1]
    a, b = by_id.get(a_id), by_id.get(b_id)
    if a is None or b is None or not (a.is_alive and b.is_alive):
        return None
    return {"bride": a.name, "groom": b.name, "house_a": house_a,
            "house_b": house_b, "_a": a, "_b": b}


def _bargain_dowry(game: Any, ctx: Dict[str, Any]) -> List[str]:
    treasury = getattr(game, "treasury", None)
    if treasury is not None:
        treasury.gold += 20
    return []


def _bargain_alliance(game: Any, ctx: Dict[str, Any]) -> List[str]:
    houses = getattr(game, "houses", None) or {}
    if ctx["house_a"] in houses:
        houses[ctx["house_a"]].relations[ctx["house_b"]] = max(
            houses[ctx["house_a"]].relations.get(ctx["house_b"], 0), 55)
    return []


def _bargain_rivals(game: Any, ctx: Dict[str, Any]) -> List[str]:
    from gilded.society.characters import modify_opinion
    a, b = ctx["_a"], ctx["_b"]
    modify_opinion(a, b, 8, "the marriage holds")
    return _drain_legitimacy(game, ctx["house_a"], 1.0)


# --- 8. The funeral of a ruler ----------------------------------------------

def _trig_ruler_funeral(game: Any) -> Optional[Dict[str, Any]]:
    # Live state only: a death has actually happened and kin survive to
    # mourn. Deterministic order: realms sorted, characters by id.
    for realm in sorted((getattr(game, "realms", None) or {}).values(),
                        key=lambda r: r.house_name):
        for ch in sorted(realm.characters, key=lambda c: c.id):
            if ch.is_alive:
                continue
            kin = [c for c in realm.characters
                   if c.is_alive and (c.id in ch.parent_ids
                                      or ch.id in c.parent_ids)]
            if kin:
                return {"ruler": ch.name, "house": realm.house_name,
                        "kin": kin[0].name, "_realm": realm, "_kin": kin[0]}
    return None


def _funeral_mourners(game: Any, ctx: Dict[str, Any]) -> List[str]:
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        legit[ctx["house"]] = min(100.0, legit.get(ctx["house"], 70.0) + 5.0)
    return []


def _funeral_procession(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for ch in getattr(ctx["_realm"], "characters", []):
        if ch.is_alive:
            ch.stress = max(0, ch.stress - 4)
    return []


def _funeral_ledger(game: Any, ctx: Dict[str, Any]) -> List[str]:
    treasury = getattr(game, "treasury", None)
    if treasury is not None:
        treasury.gold -= 25
    return _drain_legitimacy(game, ctx["house"], 1.0)


# --- 9. The war's price ------------------------------------------------------

def _trig_war_price(game: Any) -> Optional[Dict[str, Any]]:
    for war in (getattr(game, "wars", None) or []):
        if (len(war.fronts) >= 1
                and getattr(war, "started_turn", 0) and
                getattr(game, "turn", 0) - war.started_turn >= 8):
            return {"aggressor": war.aggressor, "defender": war.defender,
                    "_war": war}
    return None


def _war_tolls(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for ch in _by_id(game).values():
        if ch.is_alive:
            ch.stress = min(300, ch.stress + 3)
    return []


def _war_reparations(game: Any, ctx: Dict[str, Any]) -> List[str]:
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        legit[ctx["aggressor"]] = max(0.0, legit.get(ctx["aggressor"], 70.0) - 4.0)
        legit[ctx["defender"]] = min(100.0, legit.get(ctx["defender"], 70.0) + 2.0)
    return []


def _war_truce(game: Any, ctx: Dict[str, Any]) -> List[str]:
    tide = getattr(game, "tide", None)
    if tide is not None:
        tide.level = max(0.0, tide.level - 3.0)
    return []


# --- 10. The tide turns ------------------------------------------------------

def _trig_tide_turns(game: Any) -> Optional[Dict[str, Any]]:
    tide = getattr(game, "tide", None)
    if tide is None:
        return None
    phase = tide.phase()
    if phase == "reformist":
        return {"phase": phase, "house": ""}
    return None


def _tide_pamphlets(game: Any, ctx: Dict[str, Any]) -> List[str]:
    tide = getattr(game, "tide", None)
    if tide is not None:
        tide.level = min(200.0, tide.level + 2.0)
    return []


def _tide_reading_circles(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for ch in _by_id(game).values():
        if ch.is_alive and getattr(ch, "is_heir", False):
            ch.stress = min(300, ch.stress + 5)
            break
    return []


def _tide_police(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for p in _provinces(game):
        p.unrest = max(0.0, p.unrest - 3.0)
    return []


# --- 11. The heir's break ----------------------------------------------------

def _trig_heir_break(game: Any) -> Optional[Dict[str, Any]]:
    for realm in (getattr(game, "realms", None) or {}).values():
        for ch in realm.characters:
            if (ch.is_alive and getattr(ch, "is_heir", False)
                    and ch.stress >= 90):
                return {"heir": ch.name, "house": realm.house_name,
                        "_char": ch}
    return None


def _heir_absence(game: Any, ctx: Dict[str, Any]) -> List[str]:
    _char = ctx["_char"]
    _char.stress = min(300, _char.stress + 6)
    return []


def _heir_letter(game: Any, ctx: Dict[str, Any]) -> List[str]:
    from gilded.society.characters import Secret
    _char = ctx["_char"]
    _char.secrets.append(Secret(
        "ambition", _char.id,
        f"{_char.name} writes a letter to a house that will not be read", 20))
    return []


def _heir_recalled(game: Any, ctx: Dict[str, Any]) -> List[str]:
    _char = ctx["_char"]
    _char.stress = max(0, _char.stress - 20)
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        legit[ctx["house"]] = min(100.0, legit.get(ctx["house"], 70.0) + 2.0)
    return []


# --- 12. The ledger scandal --------------------------------------------------

def _trig_ledger_scandal(game: Any) -> Optional[Dict[str, Any]]:
    for house, legit in (getattr(game, "legitimacy", None) or {}).items():
        if legit < 35.0 and house not in (getattr(game, "fallen", None) or {}):
            return {"house": house}
    return None


def _ledger_sheets(game: Any, ctx: Dict[str, Any]) -> List[str]:
    return _drain_legitimacy(game, ctx["house"], 2.0)


def _ledger_trial(game: Any, ctx: Dict[str, Any]) -> List[str]:
    treasury = getattr(game, "treasury", None)
    if treasury is not None:
        treasury.gold -= 35
    return []


def _ledger_settlement(game: Any, ctx: Dict[str, Any]) -> List[str]:
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        legit[ctx["house"]] = min(100.0, legit.get(ctx["house"], 70.0) + 3.0)
    for p in _provinces(game):
        if p.owner == ctx["house"]:
            p.unrest = max(0.0, p.unrest - 4.0)
    return []


# --- 13. The pamphlet wave ----------------------------------------------------

def _trig_pamphlet_wave(game: Any) -> Optional[Dict[str, Any]]:
    tide = getattr(game, "tide", None)
    if tide is not None and tide.level >= 32.0:
        return {"house": "", "level": round(tide.level, 1)}
    return None


def _pamphlet_street(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for p in _provinces(game):
        p.unrest = min(100.0, p.unrest + 3.0)
    return []


def _pamphlet_courts(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for ch in _by_id(game).values():
        if ch.is_alive:
            ch.stress = min(300, ch.stress + 2)
    return []


def _pamphlet_ban(game: Any, ctx: Dict[str, Any]) -> List[str]:
    tide = getattr(game, "tide", None)
    if tide is not None:
        tide.level = max(0.0, tide.level - 5.0)
    return []


# --- 14. The high tide's crest ------------------------------------------------

def _trig_tide_crest(game: Any) -> Optional[Dict[str, Any]]:
    tide = getattr(game, "tide", None)
    if tide is not None and tide.level >= 40.0:
        return {"house": "", "level": round(tide.level, 1)}
    return None


def _crest_marches(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for p in _provinces(game):
        p.unrest = min(100.0, p.unrest + 4.0)
    return []


def _crest_deputations(game: Any, ctx: Dict[str, Any]) -> List[str]:
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        for house in legit:
            legit[house] = max(0.0, legit[house] - 1.0)
    return []


def _crest_settles(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for ch in _by_id(game).values():
        if ch.is_alive:
            ch.stress = max(0, ch.stress - 3)
    return []


# --- 15. The strain of the houses -------------------------------------------

def _trig_strain(game: Any) -> Optional[Dict[str, Any]]:
    # Live state only: some character is running at the edge of collapse.
    # Deterministic order: realms sorted, characters by id; the first at the
    # highest stress is the one named.
    best = None
    best_stress = 0.0
    for realm in sorted((getattr(game, "realms", None) or {}).values(),
                        key=lambda r: r.house_name):
        for ch in sorted(realm.characters, key=lambda c: c.id):
            if ch.is_alive and ch.stress > best_stress:
                best_stress = ch.stress
                best = ch
    if best is not None and best_stress >= 170.0:
        return {"subject": best.name, "house": "", "_char": best}
    return None


def _strain_doctors(game: Any, ctx: Dict[str, Any]) -> List[str]:
    _char = ctx["_char"]
    _char.stress = max(0, _char.stress - 30)
    return []


def _strain_ledger(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for p in _provinces(game):
        p.unrest = max(0.0, p.unrest - 2.0)
    return []


# --- 16. The great tide -------------------------------------------------------

def _trig_great_tide(game: Any) -> Optional[Dict[str, Any]]:
    tide = getattr(game, "tide", None)
    if tide is not None and tide.level >= 45.0:
        return {"house": "", "level": round(tide.level, 1)}
    return None


def _great_tide_squares(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for p in _provinces(game):
        p.unrest = min(100.0, p.unrest + 5.0)
    return []


def _great_tide_parliaments(game: Any, ctx: Dict[str, Any]) -> List[str]:
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        for house in legit:
            legit[house] = max(0.0, legit[house] - 2.0)
    return []


def _great_tide_recalls(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for ch in _by_id(game).values():
        if ch.is_alive and getattr(ch, "is_heir", False):
            ch.stress = max(0, ch.stress - 15)
            break
    return []


# --- 17. The rolls of the dead -------------------------------------------------

def _trig_mourners_roll(game: Any) -> Optional[Dict[str, Any]]:
    # Live state only: a real tally of the dead, counting what has actually
    # died in the realms. Deterministic order: realms sorted, characters by id.
    dead = 0
    for realm in sorted((getattr(game, "realms", None) or {}).values(),
                        key=lambda r: r.house_name):
        for ch in sorted(realm.characters, key=lambda c: c.id):
            if not ch.is_alive:
                dead += 1
    if dead >= 280:
        return {"house": "", "count": dead}
    return None


def _roll_printed(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for p in _provinces(game):
        p.unrest = max(0.0, p.unrest - 2.0)
    return []


def _roll_silence(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for ch in _by_id(game).values():
        if ch.is_alive:
            ch.stress = max(0, ch.stress - 4)
    return []


def _roll_register(game: Any, ctx: Dict[str, Any]) -> List[str]:
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        for house in legit:
            legit[house] = max(0.0, legit[house] + 1.0)
    return []


def build_pack3() -> List[ChainDef]:
    """Eleven chains that read the live world (C7 content depth)."""
    return [
        ChainDef("marriage_bargain", _trig_marriage_bargain, [
            ChainStep("House {house_a} and House {house_b} sign the marriage of {bride} and {groom} - the dowry is a number, the alliance a door", delay=1),
            ChainStep("The dowry lands in House {house_a}'s treasury; the bankers of both Houses shake hands", apply=_bargain_dowry, delay=2),
            ChainStep("The alliance holds: the two Houses seat a shared director on the {house_b} board", apply=_bargain_alliance, delay=2),
            ChainStep("The {groom}'s rivals note the new tie and price their own bids accordingly", apply=_bargain_rivals, delay=2)]),
        ChainDef("ruler_funeral", _trig_ruler_funeral, [
            ChainStep("The bells of House {house} ring for {ruler}; the flags come down half-mast", delay=1),
            ChainStep("The procession of {ruler} passes the works of {house}; the workers stand still an hour", apply=_funeral_mourners, delay=2),
            ChainStep("The {house} ledger closes the old account; the new line of the house is written in the register", apply=_funeral_ledger, delay=2),
            ChainStep("The household of {house} exhales: the mourners go home and the staff keep the ledger clean", apply=_funeral_procession, delay=2)]),
        ChainDef("war_price", _trig_war_price, [
            ChainStep("The war between House {aggressor} and House {defender} enters its second month; the field hospitals fill", delay=1),
            ChainStep("The rolls of the war read longer than the muster lists; the families of {defender} keep the candles lit", apply=_war_tolls, delay=2),
            ChainStep("The {aggressor} presses for reparations at the negotiating table; the {defender} counts the cost", apply=_war_reparations, delay=2),
            ChainStep("A truce is signed at the border of the two Houses; the tide of the movement drops with the guns", apply=_war_truce, delay=2)]),
        ChainDef("tide_turns", _trig_tide_turns, [
            ChainStep("The tide is {phase}: the pamphlet presses of the city print through the night", delay=1),
            ChainStep("Reading circles open in the cellars of the city; the police note the names", apply=_tide_reading_circles, delay=2),
            ChainStep("The police raid two circles; the movement's papers reprint the names as proof", apply=_tide_police, delay=2),
            ChainStep("The pamphlets reach the reading rooms of the Houses themselves", apply=_tide_pamphlets, delay=2)]),
        ChainDef("heir_break", _trig_heir_break, [
            ChainStep("{heir} of House {house} is absent from the board; the staff say nothing, and everyone says everything", delay=1),
            ChainStep("A letter from {heir} reaches a House that will not be read; the seal is unbroken", apply=_heir_letter, delay=2),
            ChainStep("House {house} recalls {heir} from wherever the absence has gone", apply=_heir_recalled, delay=2),
            ChainStep("The absence ends: {heir} is seen at the {house} gate, and the staff are told to say nothing", apply=_heir_absence, delay=2)]),
        ChainDef("ledger_scandal", _trig_ledger_scandal, [
            ChainStep("Sheets from the books of House {house} turn up at a rival's press - LEDGER SCANDAL", delay=1),
            ChainStep("The {house} ledger is read aloud at a rival's dinner; the numbers do not add to the published account", apply=_ledger_sheets, delay=2),
            ChainStep("House {house} stands the books before the court of inquiry; the treasury pays the fees", apply=_ledger_trial, delay=2),
            ChainStep("The settlement is printed: the {house} books are restated, and the works of the house open again", apply=_ledger_settlement, delay=2)]),
        ChainDef("pamphlet_wave", _trig_pamphlet_wave, [
            ChainStep("The pamphlet wave breaks on the streets: the tide is {level} and the presses do not stop", apply=_pamphlet_street, delay=1),
            ChainStep("Courts and works are flooded with the new literature; the clerks copy what they cannot read", apply=_pamphlet_courts, delay=2),
            ChainStep("The police burn the open stock of the pamphlets; the tide falls a little", apply=_pamphlet_ban, delay=2)]),
        ChainDef("tide_crest", _trig_tide_crest, [
            ChainStep("The tide crests at {level}: the banners come out and the squares fill by night", apply=_crest_marches, delay=1),
            ChainStep("Deputations come to every House; each ledger of the realm is read aloud at a meeting", apply=_crest_deputations, delay=2),
            ChainStep("The crest passes: the banners go back into the stores and the staff count the damage", apply=_crest_settles, delay=2)]),
        ChainDef("house_strain", _trig_strain, [
            ChainStep("{subject} is carried from the works; the strain of the houses is written on the face of the family", delay=1),
            ChainStep("The doctors of the house take over the care of {subject}; the household keeps the doors shut", apply=_strain_doctors, delay=2),
            ChainStep("The strain passes: the ledger of the house is set to rights and the works open again", apply=_strain_ledger, delay=2)]),
        ChainDef("great_tide", _trig_great_tide, [
            ChainStep("The great tide is at {level}: the squares are full and the banners of the Houses stand in the streets", apply=_great_tide_squares, delay=1),
            ChainStep("The parliaments of the Houses are called to answer the tide; every ledger is read against it", apply=_great_tide_parliaments, delay=2),
            ChainStep("The heirs are recalled from the streets; the tide is set down on the record of the realm", apply=_great_tide_recalls, delay=2)]),
        ChainDef("mourners_roll", _trig_mourners_roll, [
            ChainStep("The rolls of the dead are printed: {count} names stand against the works of the realm", apply=_roll_printed, delay=1),
            ChainStep("A silence passes the streets at the hour of the roll; the clerks read the names in a low voice", apply=_roll_silence, delay=2),
            ChainStep("The register is closed: the names are set into the ledger of the house and the works open again", apply=_roll_register, delay=2)]),
    ]
