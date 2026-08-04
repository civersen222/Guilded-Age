"""Shares: shareholding ledgers over gilded Enterprises (spec section 5).

Ported from the root-game shares.py onto the gilded Enterprise: each ledger
maps char_id -> pct (summing 100.0) and dividends pay into living holders'
gold_reserve. Function bodies follow the root originals; signatures take
explicit enterprise lists and province maps instead of realm globals."""

from typing import Dict, List, Tuple

from gilded.enterprises import output_gold
from gilded.society.characters import modify_opinion
from gilded.society.labor import dividend_multiplier


def priced_transfer(ent, seller, buyer, pct, market, game, dry_run=False) -> float:
    """Sell a share tranche at the market price: market.value(ent, game) * pct / 100.

    Returns the gold actually paid (0.0 for every no-op path).
    """
    val = market.value(ent, game)
    price = val * pct / 100.0
    if dry_run:
        return price
    if price <= 0:
        return 0.0
    if buyer.gold_reserve < price:
        return 0.0
    moved = transfer_shares(ent, seller.id, buyer.id, pct)
    cost = val * moved / 100.0
    buyer.gold_reserve -= cost
    seller.gold_reserve += cost
    if moved > 0:
        modify_opinion(seller, buyer, 5, "a generous buyer")
    return cost


def initial_ledger(ent, realm) -> None:
    """House founding stakes: the ruler keeps a controlling 60%; living
    dynasty kin split the remaining 40% evenly. No living kin = 100%."""
    kin = [c for c in realm.dynasty.get_all_members()
           if c.is_alive and c.id != realm.ruler.id]
    if kin:
        ent.assign_share(realm.ruler.id, 60.0)
        share = 40.0 / len(kin)
        for k in kin:
            ent.assign_share(k.id, share)
    else:
        ent.assign_share(realm.ruler.id, 100.0)


def pay_dividends(realm, enterprises, provinces: Dict[int, object],
                  tech_mod: float = 1.0) -> Tuple[float, List[str]]:
    """Pay every enterprise's output into living holders' gold_reserve.

    Returns (house_take, events): house_take is the ruler's share — the gold
    that lands in the House treasury. Dead holders' shares do not pay out."""
    events: List[str] = []
    by_id = {c.id: c for c in realm.characters}
    house_take = 0.0
    for ent in enterprises:
        province = provinces.get(ent.province)
        if province is None:
            continue
        director = by_id.get(ent.director_id)
        gold = (output_gold(ent, province, director, tech_mod)
                * dividend_multiplier(ent.extraction_dial))
        if gold <= 0:
            continue
        for char_id, pct in ent.ledger.items():
            holder = by_id.get(char_id)
            if holder is not None and holder.is_alive:
                amt = gold * pct / 100.0
                holder.gold_reserve += amt
                if char_id == realm.ruler.id:
                    house_take += amt
    return house_take, events


def partition_shares(realm, enterprises, old_ruler, new_ruler, law) -> List[str]:
    """Succession: the dead ruler's stakes partition among heirs.

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
    for ent in enterprises:
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
    """Move up to pct of an enterprise from one holder to another.

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


def extort_shares(enterprises, from_id: str, to_id: str, pct: float) -> float:
    """Blackmail's teeth (spec 6): move up to pct of EVERY enterprise
    stake the victim holds to the extorter. Returns the total moved."""
    moved = 0.0
    for ent in enterprises:
        moved += transfer_shares(ent, from_id, to_id, pct)
    return moved


def house_stake(enterprises, char_id: str) -> float:
    """Hostile takeover's yardstick (spec 6): the average stake one
    holder has across EVERY enterprise of the House. Owning most of one
    mill is a nuisance; owning most of the portfolio is the House."""
    if not enterprises:
        return 0.0
    return sum(ent.ledger.get(char_id, 0.0) for ent in enterprises) / len(enterprises)


def seize_enterprises(enterprises, from_house: str, to_house: str, to_realm) -> int:
    """Conquest's spoils: every enterprise of the toppled House re-registers
    under the victor, and its ledger is re-carved for the victor's dynasty.
    The old kin's stakes are wiped — the House survives as characters; it
    has lost its base."""
    count = 0
    for ent in enterprises:
        if ent.house != from_house:
            continue
        ent.house = to_house
        ent.ledger = {}
        ent.director_id = ""
        initial_ledger(ent, to_realm)
        count += 1
    return count
