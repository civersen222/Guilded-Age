"""Chain pack 1 (M72, spec 7): six signature chains over the live state."""

from typing import Any, Dict, Iterator, List, Optional, Tuple

from gilded.society.event_chains import ChainDef, ChainStep
from gilded.society.characters import Secret, modify_opinion


def _drain_legitimacy(game: Any, house: str, amount: float) -> List[str]:
    # A fallen House's mandate is settled, not draining.
    if house in (getattr(game, "fallen", None) or {}):
        return []
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        legit[house] = max(0.0, legit.get(house, 70.0) - amount)
    return []


def _provinces(game: Any) -> List[Any]:
    atlas = getattr(game, "atlas", None)
    return list((getattr(atlas, "provinces", None) or {}).values())


def _dial_for(game: Any, province: Any) -> float:
    """The extraction dial on a place is carried by its enterprises."""
    dials = [float(getattr(ent, "extraction_dial", 50.0))
             for ent in (getattr(game, "enterprises", None) or [])
             if ent.province == province.pid]
    return max(dials) if dials else 50.0


def _cities_of(game: Any, civ: str) -> List[Any]:
    return [p for p in _provinces(game) if p.owner == civ]


def _characters(game: Any) -> Iterator[Tuple[Any, Any]]:
    for realm in (getattr(game, "realms", None) or {}).values():
        for ch in realm.characters:
            yield realm, ch


# --- 1. The mine-disaster inquiry ------------------------------------------

def _trig_mine_inquiry(game: Any) -> Optional[Dict[str, Any]]:
    for province in _provinces(game):
        if (province.unrest >= 35.0
                and _dial_for(game, province) >= 60.0):
            return {"city": province.name, "house": province.owner,
                    "_city": province}
    return None


def _mine_testimony(game: Any, ctx: Dict[str, Any]) -> List[str]:
    return _drain_legitimacy(game, ctx["house"], 2.0)


def _mine_verdict(game: Any, ctx: Dict[str, Any]) -> List[str]:
    ctx["_city"].unrest += 6.0
    return []


# --- 2. Heir radicalization ------------------------------------------------

def _trig_heir_radicalization(game: Any) -> Optional[Dict[str, Any]]:
    for realm, ch in _characters(game):
        if (ch.is_alive and getattr(ch, "is_heir", False)
                and ch.dispositions.get("labor_capital", 0.0) <= -30.0):
            return {"heir": ch.name, "house": realm.house_name, "_char": ch}
    return None


def _heir_pamphlet(game: Any, ctx: Dict[str, Any]) -> List[str]:
    ch = ctx["_char"]
    lc = ch.dispositions.get("labor_capital", 0.0)
    ch.dispositions["labor_capital"] = max(-100.0, lc - 10.0)
    return _drain_legitimacy(game, ctx["house"], 1.0)


def _heir_refusal(game: Any, ctx: Dict[str, Any]) -> List[str]:
    note = ctx["_char"].add_stress(10)
    return [note] if note else []


# --- 3. The tabloid war ----------------------------------------------------

def _trig_tabloid_war(game: Any) -> Optional[Dict[str, Any]]:
    realms = list((getattr(game, "realms", None) or {}).values())
    for i, ra in enumerate(realms):
        for rb in realms[i + 1:]:
            a = getattr(ra, "ruler", None)
            b = getattr(rb, "ruler", None)
            if a is None or b is None:
                continue
            if (a._society.opinions.get((a.id, b.id), 0) <= -40
                    and b._society.opinions.get((b.id, a.id), 0) <= -40):
                return {"house_a": ra.house_name, "house_b": rb.house_name,
                        "a": a.name, "b": b.name}
    return None


def _tabloid_bleed(game: Any, ctx: Dict[str, Any]) -> List[str]:
    _drain_legitimacy(game, ctx["house_a"], 2.0)
    _drain_legitimacy(game, ctx["house_b"], 2.0)
    return []


def _tabloid_tired(game: Any, ctx: Dict[str, Any]) -> List[str]:
    tide = getattr(game, "tide", None)
    if tide is not None:
        tide.level = min(100.0, tide.level + 1.0)
    return []


# --- 4. The revolution's ultimatum -----------------------------------------

def _trig_revolution_ultimatum(game: Any) -> Optional[Dict[str, Any]]:
    tide = getattr(game, "tide", None)
    if tide is None or tide.phase() != "revolutionary":
        return None
    for house, legit in (getattr(game, "legitimacy", None) or {}).items():
        if legit < 30.0:
            return {"house": house}
    return None


def _revolution_rifles(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for city in _cities_of(game, ctx["house"]):
        city.unrest += 4.0
    return []


# --- 5. Succession vultures ------------------------------------------------

def _trig_succession_vultures(game: Any) -> Optional[Dict[str, Any]]:
    for realm in (getattr(game, "realms", None) or {}).values():
        ruler = getattr(realm, "ruler", None)
        if ruler is None or not ruler.is_alive or ruler.age < 65:
            continue
        kin = [c for c in realm.characters
               if c.is_alive and c is not ruler and c.age >= 16]
        if len(kin) >= 2:
            return {"ruler": ruler.name, "house": realm.house_name,
                    "_kin": (kin[0], kin[1])}
    return None


def _vultures_bedside(game: Any, ctx: Dict[str, Any]) -> List[str]:
    a, b = ctx["_kin"]
    modify_opinion(a, b, -10, "circling the same will")
    modify_opinion(b, a, -10, "circling the same will")
    return []


# --- 6. The coping spiral --------------------------------------------------

def _trig_coping_spiral(game: Any) -> Optional[Dict[str, Any]]:
    for _realm, ch in _characters(game):
        if ch.is_alive and ch.stress >= 80:
            return {"subject": ch.name, "_char": ch}
    return None


def _coping_chemist(game: Any, ctx: Dict[str, Any]) -> List[str]:
    ch = ctx["_char"]
    ch.stress = max(0, ch.stress - 15)
    ch.secrets.append(Secret(
        "vice", ch.id, f"{ch.name} depends on the chemist's droppers", 20))
    return []


def _coping_ledger(game: Any, ctx: Dict[str, Any]) -> List[str]:
    ch = ctx["_char"]
    ch.stress = max(0, ch.stress - 10)
    ch.secrets.append(Secret(
        "vice", ch.id, f"{ch.name}'s chemist's ledger reached the household", 20))
    return []


def _ultimatum_council(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for city in _cities_of(game, ctx["house"]):
        city.unrest = max(0.0, city.unrest - 8.0)
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        legit[ctx["house"]] = min(100.0, legit.get(ctx["house"], 70.0) + 4.0)
    return []


def _vultures_settle(game: Any, ctx: Dict[str, Any]) -> List[str]:
    a, b = ctx["_kin"]
    modify_opinion(a, b, 5, "the will is sealed")
    modify_opinion(b, a, 5, "the will is sealed")
    treasury = getattr(game, "treasury", None)
    if treasury is not None:
        treasury.gold += 20
    return []


def build_pack1() -> List[ChainDef]:
    """The six signature chains, in priority order (spec 7)."""
    return [
        ChainDef("mine_inquiry", _trig_mine_inquiry, [
            ChainStep("The {city} Gazette demands a public inquiry into conditions at the {city} works", delay=1),
            ChainStep("Witnesses testify in the {city} inquiry - House {house}'s name is spoken with contempt", apply=_mine_testimony, delay=2),
            ChainStep("The {city} inquiry publishes: negligence, unpunished - the workers remember", apply=_mine_verdict, delay=2)]),
        ChainDef("heir_radicalization", _trig_heir_radicalization, [
            ChainStep("Whispers at court: {heir} of House {house} attends a workers' reading circle", delay=1),
            ChainStep("{heir} publishes a pamphlet under a thin pseudonym - everyone knows", apply=_heir_pamphlet, delay=2),
            ChainStep("{heir} refuses the family dividend in front of the whole board", apply=_heir_refusal, delay=2)]),
        ChainDef("tabloid_war", _trig_tabloid_war, [
            ChainStep("The presses of House {house_a} and House {house_b} turn on each other - TABLOID WAR", delay=1),
            ChainStep("Forged letters, bought witnesses: {a} and {b} bleed credibility by the column inch", apply=_tabloid_bleed, delay=2),
            ChainStep("The public tires of both Houses - and the movement's papers look honest by comparison", apply=_tabloid_tired, delay=2)]),
        ChainDef("revolution_ultimatum", _trig_revolution_ultimatum, [
            ChainStep("An ultimatum is nailed to the gates of House {house}: reform, abdicate, or fall", delay=1),
            ChainStep("House {house} hesitates; in the tenements, the committees count rifles", apply=_revolution_rifles, delay=2),
            ChainStep("House {house} opens the gates: a council of bread and work, chaired by the city itself", apply=_ultimatum_council, delay=2)]),
        ChainDef("succession_vultures", _trig_succession_vultures, [
            ChainStep("{ruler} of House {house} grows old; the vultures begin to circle the will", delay=1),
            ChainStep("Kin arrive 'to help' at {ruler}'s bedside; the shares ledger is read aloud at night", apply=_vultures_bedside, delay=2),
            ChainStep("{ruler} signs the will before the vultures can read it; the shares ledger stays in the house", apply=_vultures_settle, delay=2)]),
        ChainDef("coping_spiral", _trig_coping_spiral, [
            ChainStep("{subject} is not sleeping; the household staff have begun to whisper", delay=1),
            ChainStep("{subject} finds a chemist who asks no questions", apply=_coping_chemist, delay=2),
            ChainStep("The ledger of the chemist's shop surfaces in the {subject} household", apply=_coping_ledger, delay=2)]),
    ]
