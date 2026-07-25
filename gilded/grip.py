"""Stage 4 L2 - Grip on the House: a PURE read-model over the portfolio.

Mirrors gilded/intel.py: report() derives everything from existing state and
never mutates the game, never touches game.rng, and runs no new simulation.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from gilded.enterprises import output_gold
from gilded.market import PRODUCES, tech_mod_for
from gilded.society.labor import dividend_multiplier
from gilded.society.realm import disloyal_shareholders
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


def band_for(controlling_stake: float) -> str:
    margin = controlling_stake - TAKEOVER_THRESHOLD
    if margin >= GRIP_BAND_MARGIN:
        return BAND_IRON_GRIP
    if margin >= 0.0:
        return BAND_CONTESTED
    if margin >= -GRIP_BAND_MARGIN:
        return BAND_IMPERILED
    return BAND_SEIZED


def _get_province(game, ent):
    return game.atlas.provinces[ent.province]


def _get_character(game, char_id):
    for realm in game.realms.values():
        for ch in realm.characters:
            if ch.id == char_id:
                return ch
    return None


def _holder_name(game, char_id):
    ch = _get_character(game, char_id)
    return ch.name if ch else char_id


def report(game, house: str) -> GripReport:
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
            band=band_for(0.0),
        )

    # Build loyal bloc: ruler + living realm characters who hold shares and are NOT disloyal
    disloyal = set(c.id for c in disloyal_shareholders(realm, house_ents))
    loyal_ids = set()

    # Ruler is only in bloc if they hold shares
    if any(ruler.id in ent.ledger for ent in house_ents):
        loyal_ids.add(ruler.id)

    for ch in realm.characters:
        if not ch.is_alive or ch.id == ruler.id:
            continue
        if ch.id in disloyal:
            continue
        if any(ch.id in ent.ledger for ent in house_ents):
            loyal_ids.add(ch.id)

    # Compute controlling stake (sum of house_stake for each loyal member)
    controlling_stake = sum(house_stake(house_ents, cid) for cid in loyal_ids)

    # Build loyal bloc Holder list
    loyal_bloc = tuple(
        Holder(id=cid, name=_holder_name(game, cid),
               stake=house_stake(house_ents, cid))
        for cid in sorted(loyal_ids)
    )

    # Find top predator: strongest non-loyal LIVING holder by portfolio-wide stake
    all_holders = set()
    for ent in house_ents:
        all_holders.update(ent.ledger.keys())
    outside_ids = all_holders - loyal_ids
    # Filter to living holders only
    outside_ids = {
        cid for cid in outside_ids
        if _get_character(game, cid) is None or _get_character(game, cid).is_alive
    }
    top_predator = None
    if outside_ids:
        best_id = max(outside_ids, key=lambda cid: house_stake(house_ents, cid))
        best_stake = house_stake(house_ents, best_id)
        if best_stake > 0:
            top_predator = Holder(id=best_id, name=_holder_name(game, best_id), stake=best_stake)

    margin = controlling_stake - TAKEOVER_THRESHOLD
    band = band_for(controlling_stake)

    # Build enterprise lines
    enterprises = []
    for ent in house_ents:
        province = _get_province(game, ent)
        director_ch = _get_character(game, ent.director_id) if ent.director_id else None

        # Dividend calculation
        tech_mod = tech_mod_for(province)
        output = output_gold(ent, province, director_ch, tech_mod)
        # Apply market price for the commodity
        commodity = PRODUCES.get(ent.kind)
        if commodity:
            price = game.market.prices.get(commodity, 1.0)
            output = output * price
        div = output * dividend_multiplier(ent.extraction_dial)

        # Director info
        director = None
        if director_ch is not None and director_ch.is_alive:
            director = Director(
                id=director_ch.id,
                name=director_ch.name,
                industry=director_ch.get_effective_stat("industry"),
                disloyal=director_ch.id in disloyal,
            )

        # Your stake (ruler's stake in this enterprise)
        your_stake = ent.ledger.get(ruler.id, 0.0)

        # Top outside holder for this enterprise (non-loyal, living)
        top_outside = None
        for cid in sorted(ent.ledger.keys(), key=lambda c: ent.ledger[c], reverse=True):
            if cid in loyal_ids:
                continue
            ch = _get_character(game, cid)
            if ch is not None and not ch.is_alive:
                continue
            top_outside = (cid, ent.ledger[cid])
            break

        sector = PRODUCES.get(ent.kind) or "bank"
        enterprises.append(EnterpriseLine(
            eid=ent.eid,
            name=ent.name,
            sector=sector,
            tier=ent.tier,
            dividend=div,
            director=director,
            your_stake=your_stake,
            top_outside=top_outside,
        ))

    return GripReport(
        house=house,
        enterprises=tuple(enterprises),
        loyal_bloc=loyal_bloc,
        controlling_stake=controlling_stake,
        top_predator=top_predator,
        threshold=TAKEOVER_THRESHOLD,
        margin=margin,
        band=band,
    )
