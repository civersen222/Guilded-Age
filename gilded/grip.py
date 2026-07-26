"""Stage 4 L2 - Grip on the House: a PURE read-model over the portfolio.

Mirrors gilded/intel.py: report() derives everything from existing state and
never mutates the game, never touches game.rng, and runs no new simulation.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from gilded.enterprises import output_gold
from gilded.market import PRODUCES, tech_mod_for
from gilded.society.labor import dividend_multiplier
from gilded.society.realm import DISLOYAL_LOYALTY, DISLOYAL_OPINION, disloyal_shareholders
from gilded.society.schemes import TAKEOVER_THRESHOLD
from gilded.society.shares import house_stake

BAND_SEIZED = "SEIZED"
BAND_IMPERILED = "IMPERILED"
BAND_CONTESTED = "CONTESTED"
BAND_IRON_GRIP = "IRON_GRIP"
BANDS = (BAND_SEIZED, BAND_IMPERILED, BAND_CONTESTED, BAND_IRON_GRIP)

GRIP_BAND_MARGIN = 15.0    # one TAKEOVER_TRANCHE either side of the threshold


@dataclass(frozen=True)
class Holder:
    id: str
    name: str
    stake: float


@dataclass(frozen=True)
class Director:
    id: str
    name: str
    industry: int
    disloyal: bool


@dataclass(frozen=True)
class EnterpriseLine:
    eid: int
    name: str
    sector: str
    tier: int
    dividend: float
    director: Optional[Director]
    your_stake: float
    top_outside: Optional[Tuple[str, float]]


@dataclass(frozen=True)
class GripReport:
    house: str
    enterprises: Tuple[EnterpriseLine, ...]
    loyal_bloc: Tuple[Holder, ...]
    controlling_stake: float
    top_predator: Optional[Holder]
    threshold: float
    margin: float
    band: str


def band_for(stake: float) -> str:
    if stake < 35:
        return BAND_SEIZED
    if stake < 50:
        return BAND_IMPERILED
    if stake < 65:
        return BAND_CONTESTED
    return BAND_IRON_GRIP


def _name_for(game, char_id: str) -> str:
    for realm in game.realms.values():
        for ch in realm.characters:
            if ch.id == char_id:
                return ch.name
    return char_id


def _director(ent, province, game, disloyal: set) -> Optional[Director]:
    if not ent.director_id:
        return None
    ch = None
    for realm in game.realms.values():
        for c in realm.characters:
            if c.id == ent.director_id:
                ch = c
                break
        if ch:
            break
    if ch is None or not ch.is_alive:
        return None
    industry = ch.get_effective_stat("industry")
    return Director(
        id=ch.id,
        name=ch.name,
        industry=industry,
        disloyal=ch.id in disloyal,
    )


def _enterprise_dividend(ent, province, game) -> float:
    """Derive dividend through the same path the chassis uses.

    The chassis builds a composite modifier:
        coal strike price * strike output multiplier * policy output_mod
        * market.output_mod(ent) * tech_mod
    and passes it to pay_dividends which calls output_gold * dividend_multiplier.

    We reconstruct the same modifier (read-only) and compute the dividend.
    """
    if province is None:
        return 0.0
    if ent.under_construction > 0:
        return 0.0

    # Build the composite modifier the same way chassis does
    mod = 1.0

    # Coal strike price modifier
    from gilded.chassis import COAL_STRIKE_PRICE
    striking = sum(
        1 for p in game.atlas.provinces.values()
        if getattr(p, "movement", None) is not None
        and p.movement.state == "striking"
    )
    coal_price = 1.0 + COAL_STRIKE_PRICE * striking
    mod *= coal_price if ent.kind == "colliery" else 1.0

    # Strike output multiplier
    from gilded.chassis import STRIKE_OUTPUT_MULT
    mv = getattr(province, "movement", None)
    if mv is not None and mv.state == "striking":
        mod *= STRIKE_OUTPUT_MULT

    # Policy output_mod (may not exist before first end_turn)
    game_policy = getattr(game, 'policy', None)
    if game_policy is not None:
        house_policy = game_policy.get(ent.house)
        if house_policy is not None:
            mod *= house_policy.output_mod

    # Market output_mod
    mod *= game.market.output_mod(ent)

    # Tech mod
    mod *= tech_mod_for(province)

    # Now compute: output_gold * dividend_multiplier * ruler's stake
    realm = game.realms.get(ent.house)
    if realm is None:
        return 0.0
    by_id = {c.id: c for c in realm.characters}
    director = by_id.get(ent.director_id)

    gold = output_gold(ent, province, director, mod) * dividend_multiplier(ent.extraction_dial)
    # Return the ruler's share
    ruler_stake = ent.ledger.get(realm.ruler.id, 0.0)
    return gold * ruler_stake / 100.0


def _top_outside_holder(ent, loyal_ids: set, dead_ids: set) -> Optional[Tuple[str, float]]:
    best_id = None
    best_pct = 0.0
    for char_id, pct in ent.ledger.items():
        if char_id in loyal_ids:
            continue
        if char_id in dead_ids:
            continue
        if pct > best_pct:
            best_pct = pct
            best_id = char_id
    if best_id is None:
        return None
    return (best_id, best_pct)


def report(game, house: str) -> GripReport:
    """Build a GripReport for *house* without mutating the game state."""
    band = band_for(0.0)
    if not house in game.houses:
        return GripReport(
            house=house,
            enterprises=tuple(),
            loyal_bloc=tuple(),
            controlling_stake=0.0,
            top_predator=None,
            threshold=TAKEOVER_THRESHOLD,
            margin=-TAKEOVER_THRESHOLD,
            band=band,
        )
    realm = game.realms[house]
    ruler = realm.ruler
    house_ents = list(game.ents_of(house))

    if not house_ents:
        return GripReport(
            house=house,
            enterprises=tuple(),
            loyal_bloc=tuple(),
            controlling_stake=0.0,
            top_predator=None,
            threshold=TAKEOVER_THRESHOLD,
            margin=-TAKEOVER_THRESHOLD,
            band=band,
        )

    # Build loyal bloc: ruler + living realm characters who hold shares and are NOT disloyal
    # Disloyalty is judged across ALL enterprises, not just house ones
    disloyal_chs = disloyal_shareholders(realm, game.enterprises, house_only=False)
    disloyal = {ch.id for ch in disloyal_chs}
    loyal_ids = set()

    # Collect all alive character ids for filtering dead holders
    all_alive_ids = set()
    dead_ids = set()
    for r in game.realms.values():
        for ch in r.characters:
            if ch.is_alive:
                all_alive_ids.add(ch.id)
            else:
                dead_ids.add(ch.id)

    # Ruler is always in the bloc while alive — they command the House
    if ruler.is_alive:
        loyal_ids.add(ruler.id)

    for ch in realm.characters:
        if not ch.is_alive or ch.id == ruler.id:
            continue
        if ch.id in disloyal:
            continue
        if not any(ch.id in ent.ledger for ent in house_ents):
            continue
        loyal_ids.add(ch.id)

    # Build enterprise lines
    enterprises = []
    all_ledger_ids: Dict[int, set] = {ent.eid: set(ent.ledger.keys()) for ent in house_ents}
    all_ids = set()
    for s in all_ledger_ids.values():
        all_ids.update(s)

    for ent in house_ents:
        province = game.atlas.provinces.get(ent.province)
        director = _director(ent, province, game, disloyal)
        dividend = _enterprise_dividend(ent, province, game)
        your_stake = ent.ledger.get(ruler.id, 0.0)

        # Top outside holder
        top_outside = _top_outside_holder(ent, loyal_ids, dead_ids)

        enterprises.append(EnterpriseLine(
            eid=ent.eid,
            name=ent.name,
            sector=PRODUCES.get(ent.kind) or "bank",
            tier=ent.tier,
            dividend=dividend,
            director=director,
            your_stake=your_stake,
            top_outside=top_outside,
        ))

    # Controlling stake: sum of house_stake for each loyal member
    loyal_bloc = []
    controlling_stake = 0.0
    for char_id in sorted(loyal_ids):
        stake = house_stake(house_ents, char_id)
        # Ruler is always in the bloc even without shares
        if stake > 0 or char_id == ruler.id:
            controlling_stake += stake
            loyal_bloc.append(Holder(
                id=char_id,
                name=_name_for(game, char_id),
                stake=stake,
            ))

    # Top predator: strongest non-bloc holder (skip dead holders)
    top_predator = None
    for char_id in sorted(all_ids):
        if char_id in loyal_ids:
            continue
        if char_id in dead_ids:
            continue
        stake = house_stake(house_ents, char_id)
        if stake > 0:
            if top_predator is None or stake > top_predator.stake:
                top_predator = Holder(
                    id=char_id,
                    name=_name_for(game, char_id),
                    stake=stake,
                )

    margin = controlling_stake - TAKEOVER_THRESHOLD
    band = band_for(controlling_stake)

    return GripReport(
        house=house,
        enterprises=tuple(enterprises),
        loyal_bloc=tuple(loyal_bloc),
        controlling_stake=controlling_stake,
        top_predator=top_predator,
        threshold=TAKEOVER_THRESHOLD,
        margin=margin,
        band=band,
    )
