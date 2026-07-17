"""Shares: house enterprises and shareholding ledgers (deep-systems spec, Wave DC M43).

Every Great House (a realm's ruling dynasty) is founded holding Enterprises over
its cities. Each Enterprise has a ledger of shareholdings (char_id -> pct,
always summing to 100.0) and pays its base_yield in gold to holders'
gold_reserve every turn during the gold step. Succession partition of shares
lands in M44; share dowries in M45.
"""

import random
from typing import Dict, List

SECTORS = ("grain", "timber", "ore", "wool", "wine", "salt")


class Enterprise:
    def __init__(self, name: str, house: str, sector: str, city_name: str, base_yield: int):
        self.name = name
        self.house = house            # civ_name of the founding Great House
        self.sector = sector
        self.city_name = city_name
        self.base_yield = base_yield  # gold per turn, split by the ledger
        self.ledger: Dict[str, float] = {}   # char_id -> pct, sums to 100.0

    def assign_share(self, char_id: str, pct: float):
        self.ledger[char_id] = self.ledger.get(char_id, 0.0) + pct

    def ledger_total(self) -> float:
        return sum(self.ledger.values())


def found_enterprises(realm, cities) -> List["Enterprise"]:
    """House founding: one enterprise per city the realm owns.

    The ruler keeps a controlling 60% stake; living dynasty kin split the
    remaining 40% evenly. A ruler with no living kin holds 100%.
    """
    out: List[Enterprise] = []
    kin = [c for c in realm.dynasty.get_all_members()
           if c.is_alive and c.id != realm.ruler.id]
    for city in cities:
        if city.owner != realm.civ_name:
            continue
        sector = random.choice(SECTORS)
        ent = Enterprise(f"{city.name} {sector} ventures", realm.civ_name, sector,
                         city.name, base_yield=random.randint(3, 6))
        if kin:
            ent.assign_share(realm.ruler.id, 60.0)
            share = 40.0 / len(kin)
            for k in kin:
                ent.assign_share(k.id, share)
        else:
            ent.assign_share(realm.ruler.id, 100.0)
        out.append(ent)
    return out


def pay_dividends(realm) -> float:
    """Pay every enterprise's yield into living holders' gold_reserve.

    Returns the house's total payout this turn. Dead holders' shares simply
    do not pay out (succession partition reassigns them in M44).
    """
    by_id = {c.id: c for c in realm.characters}
    total = 0.0
    for ent in realm.enterprises:
        for char_id, pct in ent.ledger.items():
            holder = by_id.get(char_id)
            if holder is not None and holder.is_alive:
                amt = ent.base_yield * pct / 100.0
                holder.gold_reserve += amt
                total += amt
    return total
