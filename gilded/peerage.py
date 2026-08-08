"""Stage 5A — The Peerage read-model: the men who will betray you, with numbers.

Pure read-model over the court and dynasty.  report() derives everything from
existing state and never mutates the game, never touches game.rng, and runs no
new simulation.  Built without a UI consumer (wave 5B).
"""

from dataclasses import dataclass, is_dataclass
from typing import Dict, List, Optional, Tuple

from gilded.society.court import CourtPosition
from gilded.society.realm import DISLOYAL_LOYALTY, DISLOYAL_OPINION, disloyal_shareholders
from gilded.society.shares import house_stake
from gilded.society.succession import succession_order


# ── Bands ────────────────────────────────────────────────────────────────────

BAND_TRUSTED = "TRUSTED"
BAND_LOYAL = "LOYAL"
BAND_DUBIOUS = "DUBIOUS"
BAND_DISLOYAL = "DISLOYAL"

BANDS = (BAND_DISLOYAL, BAND_DUBIOUS, BAND_LOYAL, BAND_TRUSTED)  # weakest-first


def band_for(loyalty: float) -> str:
    """Return the loyalty band for a value in 0..100.

    The edge between DUBIOUS and DISLOYAL sits exactly on DISLOYAL_LOYALTY
    so that it moves when the constant moves.
    """
    if loyalty < DISLOYAL_LOYALTY:
        return BAND_DISLOYAL
    elif loyalty < DISLOYAL_LOYALTY + 20:
        return BAND_DUBIOUS
    elif loyalty < 80:
        return BAND_LOYAL
    else:
        return BAND_TRUSTED


# ── Frozen records ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CourtSeat:
    position: str
    holder_name: Optional[str]
    holder_id: Optional[str]
    stat: str
    bonus: int
    loyalty: Optional[float]
    band: Optional[str]
    vacant: bool


@dataclass(frozen=True)
class Kin:
    char_id: str
    name: str
    age: int
    is_alive: bool
    is_heir: bool
    succession_rank: Optional[int]
    opinion_of_ruler: int
    loyalty: float
    shares_pct: float
    is_disloyal: bool
    grievances: Tuple[str, ...]


@dataclass(frozen=True)
class CourtReport:
    house: str
    ruler_name: Optional[str]
    ruler_age: Optional[int]
    seats: Tuple[CourtSeat, ...]
    kin: Tuple[Kin, ...]
    heir_designated: Optional[str]
    heir_if_ruler_died_now: Optional[str]
    aggrieved_if_that_happened: Tuple[str, ...]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _empty_report(house: str) -> CourtReport:
    return CourtReport(
        house=house,
        ruler_name=None,
        ruler_age=None,
        seats=(),
        kin=(),
        heir_designated=None,
        heir_if_ruler_died_now=None,
        aggrieved_if_that_happened=(),
    )


def _get_loyalty(ch) -> float:
    """Safe loyalty accessor — falls back to LOYALTY_START when absent."""
    from gilded.society.realm import LOYALTY_START
    return getattr(ch, "loyalty", LOYALTY_START)


# ── Public API ───────────────────────────────────────────────────────────────

def report(game, house: str) -> CourtReport:
    """Build a CourtReport for *house* without mutating game state.

    Returns an empty report when *house* is not in game.houses.
    """
    if house not in game.houses:
        return _empty_report(house)

    realm = game.realms[house]
    ruler = realm.ruler
    house_ents = list(game.ents_of(house))

    # ── Court seats ────────────────────────────────────────────────────────
    seats: List[CourtSeat] = []
    for pos in CourtPosition:
        holder = realm.court.positions.get(pos)
        if holder and holder.is_alive:
            loyalty = _get_loyalty(holder)
            seats.append(CourtSeat(
                position=pos.value,
                holder_name=holder.name,
                holder_id=holder.id,
                stat=realm.court.POSITION_STATS.get(pos, ""),
                bonus=realm.court.get_bonus(pos) if hasattr(realm.court, 'get_bonus') else 0,
                loyalty=loyalty,
                band=band_for(loyalty),
                vacant=False,
            ))
        else:
            seats.append(CourtSeat(
                position=pos.value,
                holder_name=None,
                holder_id=None,
                stat=realm.court.POSITION_STATS.get(pos, ""),
                bonus=0,
                loyalty=None,
                band=None,
                vacant=True,
            ))

    # ── Kin set — every living non-ruler character disloyal_shareholders can
    #     name, plus every living dynasty member, ruler excluded ────────────
    kin_set: Dict[str, object] = {}  # char_id -> Character

    # Living dynasty members (excl ruler)
    ruler_id = ruler.id if ruler else None
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.id != ruler_id:
            kin_set[c.id] = c

    # All characters disloyal_shareholders can name (excl ruler)
    ds_list = disloyal_shareholders(realm, house_ents, house_only=True)
    for c in ds_list:
        if c.is_alive and c.id != ruler_id:
            kin_set[c.id] = c

    # Also include ALL living characters in realm (disloyal_shareholders iterates realm.characters)
    for c in realm.characters:
        if c.is_alive and c.id != ruler_id:
            kin_set[c.id] = c

    # ── Succession order ───────────────────────────────────────────────────
    succ_order = succession_order(realm)
    succ_rank_map: Dict[str, int] = {}
    for idx, ch in enumerate(succ_order, 1):
        if ch.id not in succ_rank_map:
            succ_rank_map[ch.id] = idx

    # Heir if ruler died now
    heir_if_died = succ_order[0].id if succ_order else None

    # Aggrieved if ruler died now — living dynasty adults ≥ 16 who are not the heir
    aggrieved: List[str] = []
    for c in succ_order:
        if c.is_alive and c.id != heir_if_died and c.age >= 16:
            if c.id in {ch.id for ch in realm.dynasty.all_characters.values()}:
                aggrieved.append(c.name)

    # ── Build kin list ─────────────────────────────────────────────────────
    kin_list: List[Kin] = []
    society = realm.society if hasattr(realm, 'society') else ruler._society

    for ch in sorted(kin_set.values(), key=lambda c: c.name):
        opinion = society.opinions.get((ch.id, ruler_id), 0) if ruler_id else 0
        loyalty = _get_loyalty(ch)
        shares = house_stake(house_ents, ch.id)

        # Disloyal flag — match disloyal_shareholders rule exactly
        is_disloyal = loyalty < DISLOYAL_LOYALTY or opinion <= DISLOYAL_OPINION

        # Grievances — opinion history of THIS character OF THE RULER
        hist_key = (ch.id, ruler_id)
        entries = society.opinion_history.get(hist_key, [])
        grievances = tuple(e.reason for e in entries if e.reason)

        kin_list.append(Kin(
            char_id=ch.id,
            name=ch.name,
            age=ch.age,
            is_alive=ch.is_alive,
            is_heir=ch.is_heir if hasattr(ch, 'is_heir') else False,
            succession_rank=succ_rank_map.get(ch.id),
            opinion_of_ruler=opinion,
            loyalty=loyalty,
            shares_pct=shares,
            is_disloyal=is_disloyal,
            grievances=grievances,
        ))

    # ── Heir designated ────────────────────────────────────────────────────
    heir_designated = None
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c.is_heir:
            heir_designated = c.name
            break

    return CourtReport(
        house=house,
        ruler_name=ruler.name if ruler else None,
        ruler_age=ruler.age if ruler else None,
        seats=tuple(seats),
        kin=tuple(kin_list),
        heir_designated=heir_designated,
        heir_if_ruler_died_now=heir_if_died,
        aggrieved_if_that_happened=tuple(aggrieved),
    )
