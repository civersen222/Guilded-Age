"""Shares: house enterprises and shareholding ledgers (deep-systems spec, Wave DC M43).

Every Great House (a realm's ruling dynasty) is founded holding Enterprises over
its cities. Each Enterprise has a ledger of shareholdings (char_id -> pct,
always summing to 100.0) and pays its base_yield in gold to holders'
gold_reserve every turn during the gold step. Succession partition of shares
lands in M44; share dowries in M45.
"""

import random
from typing import Dict, List

from simulation import modify_opinion

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


def partition_shares(realm, old_ruler, new_ruler, law) -> List[str]:
    """Succession 2.0 (M44): the dead ruler's stakes partition among heirs.

    Title follows law (handled by the caller). Shares follow testament
    weighting: the new ruler inherits half of every stake and living adult
    dynasty kin split the other half evenly; GAVELKIND splits every stake
    evenly among the new ruler and kin alike. A ruler with no adult kin
    passes the full portfolio to the successor.

    Non-inheriting kin resent the settlement: -40 opinion of the new ruler,
    pushing them past the rival threshold that plot logic feeds on.
    """
    events: List[str] = []
    kin = [c for c in realm.dynasty.all_characters.values()
           if c.is_alive and c.age >= 16 and c.id not in (old_ruler.id, new_ruler.id)]
    moved = 0.0
    for ent in realm.enterprises:
        stake = ent.ledger.pop(old_ruler.id, 0.0)
        if stake <= 0:
            continue
        moved += stake
        if not kin:
            ent.assign_share(new_ruler.id, stake)
        elif law == 'GAVELKIND':
            share = stake / (len(kin) + 1)
            ent.assign_share(new_ruler.id, share)
            for k in kin:
                ent.assign_share(k.id, share)
        else:
            ent.assign_share(new_ruler.id, stake / 2)
            share = (stake / 2) / len(kin)
            for k in kin:
                ent.assign_share(k.id, share)
    if moved > 0 and kin:
        for k in kin:
            modify_opinion(k, new_ruler, -40, "denied the throne")
        events.append(f"{old_ruler.name}'s shares are partitioned; {len(kin)} kin become shareholder rivals of {new_ruler.name}")
    elif moved > 0:
        events.append(f"{new_ruler.name} inherits {old_ruler.name}'s full portfolio")
    return events


def transfer_shares(ent, from_id: str, to_id: str, pct: float) -> float:
    """Move up to pct of an enterprise from one holder to another (M45).

    Returns the amount actually moved. The ledger keeps summing to 100.
    """
    held = ent.ledger.get(from_id, 0.0)
    amt = min(pct, held)
    if amt <= 0:
        return 0.0
    if held - amt <= 1e-9:
        ent.ledger.pop(from_id, None)
    else:
        ent.ledger[from_id] = held - amt
    ent.assign_share(to_id, amt)
    return amt
