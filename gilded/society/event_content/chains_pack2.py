"""Chain pack 2 (M72b, spec 7): the strike wave, the martyr's ballad, the panic."""

from typing import Any, Dict, List, Optional

from gilded.society.event_chains import ChainDef, ChainStep
from gilded.society.event_content.chains_pack1 import (
    _cities_of, _dial_for, _provinces)


def _drain_legitimacy(game: Any, house: str, amount: float) -> List[str]:
    # A fallen House's mandate is settled, not draining.
    if house in (getattr(game, "fallen", None) or {}):
        return []
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        legit[house] = max(0.0, legit.get(house, 70.0) - amount)
    return []


# --- 1. The general strike -------------------------------------------------

def _trig_general_strike(game: Any) -> Optional[Dict[str, Any]]:
    for province in _provinces(game):
        mv = getattr(province, "movement", None)
        if (mv is not None and mv.state == "striking"
                and mv.militancy >= 60.0):
            return {"city": province.name, "house": province.owner,
                    "_city": province}
    return None


def _strike_spreads(game: Any, ctx: Dict[str, Any]) -> List[str]:
    for c in _cities_of(game, ctx["house"]):
        if c is not ctx["_city"]:
            c.unrest += 2.0
    return _drain_legitimacy(game, ctx["house"], 2.0)


# --- 2. The martyr's ballad ------------------------------------------------

def _trig_martyr_ballad(game: Any) -> Optional[Dict[str, Any]]:
    for province in _provinces(game):
        mv = getattr(province, "movement", None)
        if mv is not None and mv.martyr:
            return {"city": province.name, "martyr": mv.martyr, "_mv": mv}
    return None


def _ballad_banner(game: Any, ctx: Dict[str, Any]) -> List[str]:
    mv = ctx["_mv"]
    mv.militancy = min(100.0, mv.militancy + 10.0)
    tide = getattr(game, "tide", None)
    if tide is not None:
        tide.level = min(100.0, tide.level + 1.0)
    return []


# --- 3. Strikebreakers -----------------------------------------------------

def _trig_strikebreakers(game: Any) -> Optional[Dict[str, Any]]:
    for province in _provinces(game):
        if (_dial_for(game, province) >= 80.0
                and province.unrest >= 25.0):
            return {"city": province.name, "house": province.owner,
                    "_city": province}
    return None


def _skulls_photographed(game: Any, ctx: Dict[str, Any]) -> List[str]:
    ctx["_city"].unrest += 5.0
    return _drain_legitimacy(game, ctx["house"], 3.0)


# --- 4. The company paradise -----------------------------------------------

def _trig_company_paradise(game: Any) -> Optional[Dict[str, Any]]:
    for province in _provinces(game):
        if (_dial_for(game, province) <= 30.0
                and province.unrest <= 10.0):
            return {"city": province.name, "house": province.owner}
    return None


def _paradise_pamphlets(game: Any, ctx: Dict[str, Any]) -> List[str]:
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        legit[ctx["house"]] = min(100.0, legit.get(ctx["house"], 70.0) + 2.0)
    return []


# --- 5. The exchange panic -------------------------------------------------

def _trig_exchange_panic(game: Any) -> Optional[Dict[str, Any]]:
    tide = getattr(game, "tide", None)
    if tide is None or tide.level < 50.0:
        return None
    for house, legit in (getattr(game, "legitimacy", None) or {}).items():
        if legit < 40.0:
            return {"house": house}
    return None


def _widows_not_whole(game: Any, ctx: Dict[str, Any]) -> List[str]:
    return _drain_legitimacy(game, ctx["house"], 2.0)


# --- 6. A conspiracy of equals ---------------------------------------------

def _trig_conspiracy_of_equals(game: Any) -> Optional[Dict[str, Any]]:
    mgr = getattr(game, "scheme_mgr", None)
    for s in (getattr(mgr, "schemes", None) or []):
        if len(s.participants) >= 2:
            return {"target": s.target.name, "_target": s.target}
    return None


def _tasted_cups(game: Any, ctx: Dict[str, Any]) -> List[str]:
    note = ctx["_target"].add_stress(10)
    return [note] if note else []


def _strike_arbitrated(game: Any, ctx: Dict[str, Any]) -> List[str]:
    ctx["_city"].unrest = max(0.0, ctx["_city"].unrest - 12.0)
    return []


def _ballad_committee(game: Any, ctx: Dict[str, Any]) -> List[str]:
    mv = ctx["_mv"]
    mv.militancy = min(100.0, mv.militancy + 5.0)
    return []


def _skulls_quieted(game: Any, ctx: Dict[str, Any]) -> List[str]:
    treasury = getattr(game, "treasury", None)
    if treasury is not None:
        treasury.gold -= 30
    return _drain_legitimacy(game, ctx["house"], 1.0)


def _paradise_copied(game: Any, ctx: Dict[str, Any]) -> List[str]:
    legit = getattr(game, "legitimacy", None)
    if legit is not None:
        legit[ctx["house"]] = min(100.0, legit.get(ctx["house"], 70.0) + 3.0)
    return []


def _widows_written_down(game: Any, ctx: Dict[str, Any]) -> List[str]:
    treasury = getattr(game, "treasury", None)
    if treasury is not None:
        treasury.gold += 25
    return []


def _circle_burns(game: Any, ctx: Dict[str, Any]) -> List[str]:
    note = ctx["_target"].add_stress(5)
    return [note] if note else []


def build_pack2() -> List[ChainDef]:
    """Six more signature chains, in priority order (spec 7)."""
    return [
        ChainDef("general_strike", _trig_general_strike, [
            ChainStep("The {city} strike hardens: pickets at every gate, and the trains stand still", delay=1),
            ChainStep("Sympathy walkouts ripple outward from {city} - House {house}'s ledgers bleed", apply=_strike_spreads, delay=2),
            ChainStep("The {city} strike ends in an arbitration board: bread prices fixed, the gates half-open", apply=_strike_arbitrated, delay=2)]),
        ChainDef("martyr_ballad", _trig_martyr_ballad, [
            ChainStep("A ballad of {martyr} is sung in the taverns of {city}; the police tear down the broadsheets", delay=1),
            ChainStep("{martyr}'s name becomes a banner: the {city} movement swears it will not be bought", apply=_ballad_banner, delay=2),
            ChainStep("The {city} movement names its committee after {martyr}; the police learn the names", apply=_ballad_committee, delay=2)]),
        ChainDef("strikebreakers", _trig_strikebreakers, [
            ChainStep("House {house} quietly hires strikebreakers for the {city} works", delay=1),
            ChainStep("Cracked skulls on the picket line at {city}; the newspapers print the photographs", apply=_skulls_photographed, delay=2),
            ChainStep("The photographs reach the {city} court of inquiry; House {house} buys the strikebreakers' silence", apply=_skulls_quieted, delay=2)]),
        ChainDef("company_paradise", _trig_company_paradise, [
            ChainStep("Visitors marvel at the model tenements of {city}: schools, clinics, gardens", delay=1),
            ChainStep("Pamphlets across the world cite {city} as proof the Houses can be humane", apply=_paradise_pamphlets, delay=2),
            ChainStep("The {city} model is copied by two rival Houses; the gardens become a matter of statecraft", apply=_paradise_copied, delay=2)]),
        ChainDef("exchange_panic", _trig_exchange_panic, [
            ChainStep("Rumors of default: the exchange dumps House {house} paper by the crate", delay=1),
            ChainStep("House {house} pledges assets to steady its price; the widows' funds are not made whole", apply=_widows_not_whole, delay=2),
            ChainStep("The exchange prints a notice: House {house} paper stands; the widows' fund is written down, not repaid", apply=_widows_written_down, delay=2)]),
        ChainDef("conspiracy_of_equals", _trig_conspiracy_of_equals, [
            ChainStep("Too many candles burn late: something moves against {target}, and the servants know it", delay=1),
            ChainStep("{target} doubles the guard and trusts no cup not tasted first", apply=_tasted_cups, delay=2),
            ChainStep("One of the conspirators buys passage abroad; the rest of the circle learns to burn letters", apply=_circle_burns, delay=2)]),
    ]
