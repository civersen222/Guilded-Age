"""Enterprises: the House economy (spec section 5).

An Enterprise is a named venture seated in a province, owned by a House,
run by a Director, and carved into shareholdings. Output flows from the
province's endowment richness, the enterprise tier, the extraction dial
and the Director's industry."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from gilded.society.labor import production_multiplier

ENTERPRISE_TYPES = {
    #  type        needs-endowment  capacity  base_gold  found_cost
    "colliery":   ("coalfield",     "coal",    30.0,      400.0),
    "ironworks":  ("iron",          "steel",   40.0,      600.0),
    "mill":       ("timber",        "freight", 25.0,      300.0),
    "estate":     ("farmland",      None,      20.0,      250.0),
    "rail_co":    ("harbor",        "freight", 35.0,      500.0),
    "bank":       (None,            None,      50.0,      800.0),
}
KIND_TITLES = {
    "colliery": "Colliery", "ironworks": "Ironworks", "mill": "Mill",
    "estate": "Estate", "rail_co": "Rail Co.", "bank": "Bank",
}
WORKFORCE_PER_TIER = 10          # thousands employed per capital tier
TIER_MAX = 5
EXPAND_COST = {2: 300.0, 3: 500.0, 4: 800.0, 5: 1200.0}   # gold to reach tier
EXPAND_TURNS = {2: 2, 3: 2, 4: 3, 5: 3}


@dataclass
class Enterprise:
    eid: int
    kind: str                      # key of ENTERPRISE_TYPES
    name: str                      # e.g. "Karvess Colliery"
    house: str
    province: int                  # pid
    tier: int = 1
    extraction_dial: float = 50.0  # society.labor dial, 0..100
    director_id: str = ""          # Character.id
    ledger: Dict[str, float] = field(default_factory=dict)  # char_id -> pct, sums 100
    under_construction: int = 0    # turns remaining (founding or expansion)
    target_tier: int = 1
    _last_dividend: float = 0.0    # dividend paid during last end_turn

    def workforce(self) -> int:
        return self.tier * WORKFORCE_PER_TIER

    def assign_share(self, char_id: str, pct: float) -> None:
        self.ledger[char_id] = self.ledger.get(char_id, 0.0) + pct

    def ledger_total(self) -> float:
        return sum(self.ledger.values())


def _richness(ent: Enterprise, province) -> float:
    needed = ENTERPRISE_TYPES[ent.kind][0]
    if needed is None:
        return 1.0
    return float(province.endowments.get(needed, 0))


def output_gold(ent: Enterprise, province, director, tech_mod: float = 1.0) -> float:
    """Gold produced this turn (before dividend split)."""
    if ent.under_construction > 0:
        return 0.0
    richness = _richness(ent, province)
    if richness <= 0:
        return 0.0
    base_gold = ENTERPRISE_TYPES[ent.kind][2]
    staffing = min(1.0, province.population / max(1, ent.workforce()))
    director_mod = 1.0
    if director is not None and getattr(director, "is_alive", False):
        director_mod = 1.0 + director.get_effective_stat("industry") / 40.0
    return (base_gold * richness * ent.tier * staffing
            * production_multiplier(ent.extraction_dial) * director_mod * tech_mod)


def capacity_out(ent: Enterprise, province) -> Tuple[Optional[str], float]:
    """Strategic capacity (coal/steel/freight) the enterprise adds this turn."""
    kind = ENTERPRISE_TYPES[ent.kind][1]
    if kind is None or ent.under_construction > 0:
        return None, 0.0
    richness = _richness(ent, province)
    if richness <= 0:
        return None, 0.0
    return kind, ent.tier * richness


def found_enterprise(kind: str, house: str, province, eid: int,
                     rng: random.Random) -> Optional[Enterprise]:
    """Charter a new venture; None if the province lacks the endowment."""
    needed = ENTERPRISE_TYPES[kind][0]
    if needed is not None and needed not in province.endowments:
        return None
    ent = Enterprise(eid=eid, kind=kind,
                     name=f"{province.name} {KIND_TITLES[kind]}",
                     house=house, province=province.pid)
    ent.under_construction = EXPAND_TURNS[2]
    ent.target_tier = 1
    return ent


def tick_construction(ent: Enterprise) -> bool:
    """Advance scaffolding one turn; True the turn work completes."""
    if ent.under_construction <= 0:
        return False
    ent.under_construction -= 1
    if ent.under_construction == 0:
        ent.tier = max(ent.tier, ent.target_tier)
        return True
    return False


DIRECTOR_SKIM_PCT = 0.15  # fraction of dividend a disloyal Director diverts


def director_skim(take: float, director, ruler) -> float:
    """Gold the Director diverts from one enterprise's dividend.

    Zero when the seat is empty, the Director is loyal, or the take is
    non-positive.  Otherwise a fixed fraction of ``take``.
    """
    if director is None:
        return 0.0
    from gilded.society.realm import director_is_disloyal
    if not director_is_disloyal(director, ruler):
        return 0.0
    if take <= 0:
        return 0.0
    return take * DIRECTOR_SKIM_PCT
