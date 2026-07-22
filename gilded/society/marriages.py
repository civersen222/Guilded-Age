
"""Cross-house marriages bind the great houses together (mission G10).

Ported from root marriages.py with the module-level registries wrapped in
MarriageRegistry and the diplomacy manager replaced by House relations and
war sets. All randomness comes through an explicit rng."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from gilded.enterprises import ENTERPRISE_TYPES
from gilded.society.characters import generate_child, modify_opinion
from gilded.society.dispositions import PAIRS
from gilded.society.realm import FEMALE_NAMES, MALE_NAMES
from gilded.society.shares import transfer_shares

MARRIAGE_CHANCE = 0.04
BLOOD_TIE_INTERVAL = 8
BLOOD_TIE_BONUS = 3
MARRIAGE_RELATION_BONUS = 15
ALLIANCE_AT = 50
MAX_MESSAGES = 3


@dataclass
class MarriageContract:
    """Marriage as merger (spec 4.3): the terms two houses agree on.

    board_seat is stored for the org chart to consume; the full courtship
    verbs that haggle these terms come with the deliberate AI matches."""
    alliance: bool = False
    dowry_gold: float = 0.0
    dowry_shares_pct: float = 0.0
    matrilineal: bool = False   # children register to the mother's House
    board_seat: bool = False


_BLOODLINE_KEYS = tuple(k for k, p in PAIRS.items() if p.family == "bloodline")


def bloodline_quality(char) -> float:
    """Desirable bloodline labels sit on the NEGATIVE side of each pair."""
    disp = getattr(char, "dispositions", None) or {}
    return sum(max(0.0, -disp.get(k, 0.0)) for k in _BLOODLINE_KEYS)


def house_power(enterprises: List) -> float:
    return float(sum(ENTERPRISE_TYPES[ent.kind][2] * ent.tier
                     for ent in enterprises))


SCANDAL_KEYS = ("honest_deceitful", "temperate_hedonist")


def scandal_discount(char) -> float:
    """Courtship pressure (spec 4.3): what society BELIEVES about a person
    is what the market prices - an expose craters the persona and with it
    the asking price."""
    persona = getattr(char, "persona", None) or {}
    return sum(max(0.0, persona.get(k, 0.0)) for k in SCANDAL_KEYS) * 0.15


def asking_price(char, enterprises: List) -> float:
    """AI valuation: what this hand in marriage costs the other house."""
    return max(1.0, 10.0 + bloodline_quality(char) * 0.5
               + house_power(enterprises) - scandal_discount(char))


def _at_war(houses, a: str, b: str) -> bool:
    ha = houses.get(a)
    return ha is not None and b in getattr(ha, "at_war_with", set())


def _relation(houses, a: str, b: str) -> int:
    ha = houses.get(a)
    if ha is None:
        return 0
    return ha.relations.get(b, 0)


def _modify_relation(houses, a: str, b: str, delta: int) -> None:
    ha, hb = houses.get(a), houses.get(b)
    if ha is not None:
        ha.relations[b] = ha.relations.get(b, 0) + delta
    if hb is not None:
        hb.relations[a] = hb.relations.get(a, 0) + delta


class MarriageRegistry:
    """Owns every cross-house marriage, its contract, and the blood ties
    that slowly pull the houses together."""

    def __init__(self):
        # (char_a_id, house_a, char_b_id, house_b)
        self.marriages: List[tuple] = []
        # (char_a_id, char_b_id) -> MarriageContract
        self.contracts: Dict[tuple, MarriageContract] = {}
        self.married_ids: set = set()
        self.wedding_count = 0
        self.turns = 0   # internal clock for the blood-tie interval

    def _eligible(self, realm, gender: Optional[str] = None) -> List:
        out = []
        for c in realm.characters:
            if not c.is_alive or c.age < 16 or c.age > 50 or c.id in self.married_ids:
                continue
            if c.id == realm.ruler.id:
                continue
            if gender and c.gender != gender:
                continue
            out.append(c)
        return out

    def _negotiate_contract(self, ra, b, ents_b, rng) -> MarriageContract:
        """ra's house receives spouse b and pays the bride price in gold if
        its ruler can afford it, topping up with shares if not."""
        price = asking_price(b, ents_b)
        contract = MarriageContract(alliance=True)
        contract.matrilineal = rng.random() < 0.25
        contract.board_seat = rng.random() < 0.25
        payer = ra.ruler
        if payer.gold_reserve >= price:
            contract.dowry_gold = price
        else:
            contract.dowry_gold = payer.gold_reserve * 0.5
            contract.dowry_shares_pct = min(15.0, max(5.0, (price - contract.dowry_gold) * 0.25))
        return contract

    def _wed(self, house_a, house_b, ra, rb, a, b, houses,
             enterprises_by_house, rng) -> str:
        """The match itself: b joins a's realm and house, the merger
        contract is negotiated and applied, relations warm."""
        if b in rb.characters:
            rb.characters.remove(b)
        ra.characters.append(b)
        ra.dynasty.all_characters.setdefault(b.id, b)
        for pos, ch in rb.court.positions.items():
            if ch and ch.id == b.id:
                rb.court.positions[pos] = None
        modify_opinion(a, b, 40, "marriage")
        modify_opinion(b, a, 40, "marriage")
        ents_a = enterprises_by_house.get(house_a, [])
        ents_b = enterprises_by_house.get(house_b, [])
        contract = self._negotiate_contract(ra, b, ents_b, rng)
        if contract.dowry_gold > 0:
            ra.ruler.gold_reserve -= contract.dowry_gold
            rb.ruler.gold_reserve += contract.dowry_gold
        if contract.dowry_shares_pct > 0 and ents_a:
            transfer_shares(rng.choice(ents_a), ra.ruler.id,
                            rb.ruler.id, contract.dowry_shares_pct)
        self.marriages.append((a.id, house_a, b.id, house_b))
        self.contracts[(a.id, b.id)] = contract
        self.married_ids.update((a.id, b.id))
        self.wedding_count += 1
        if _relation(houses, house_a, house_b) < 60:
            _modify_relation(houses, house_a, house_b,
                             MARRIAGE_RELATION_BONUS + (10 if contract.alliance else 0))
        return f"{a.name} weds {b.name} - {house_a} and {house_b} are bound by marriage"

    def _maybe_arrange_match(self, realms, houses, enterprises_by_house,
                             rng) -> Optional[str]:
        if rng.random() >= MARRIAGE_CHANCE:
            return None
        names = list(realms)
        rng.shuffle(names)
        for i, house_a in enumerate(names):
            for house_b in names[i + 1:]:
                if _at_war(houses, house_a, house_b):
                    continue
                ra, rb = realms[house_a], realms[house_b]
                # Prefer marrying off dynasty kin - that is what binds the houses.
                kin_a = [c for c in self._eligible(ra) if c.id in ra.dynasty.all_characters]
                cand_a = kin_a or self._eligible(ra)
                if not cand_a:
                    continue
                a = rng.choice(cand_a)
                want = "Female" if a.gender == "Male" else "Male"
                cand_b = self._eligible(rb, want)
                if not cand_b:
                    continue
                b = rng.choice(cand_b)
                return self._wed(house_a, house_b, ra, rb, a, b, houses,
                                 enterprises_by_house, rng)
        return None

    def arrange_match_between(self, house_a: str, house_b: str, realms, houses,
                              enterprises_by_house, rng) -> Optional[str]:
        """A deliberate match between two named Houses: the AI binds a
        friend the way the ambient tick does, but on purpose - kin
        preferred, best bloodline first, the same merger contract."""
        ra, rb = realms.get(house_a), realms.get(house_b)
        if ra is None or rb is None:
            return None
        if _at_war(houses, house_a, house_b):
            return None
        kin_a = [c for c in self._eligible(ra) if c.id in ra.dynasty.all_characters]
        cand_a = kin_a or self._eligible(ra)
        if not cand_a:
            return None
        a = max(cand_a, key=bloodline_quality)
        want = "Female" if a.gender == "Male" else "Male"
        cand_b = self._eligible(rb, want)
        if not cand_b:
            return None
        b = max(cand_b, key=bloodline_quality)
        return self._wed(house_a, house_b, ra, rb, a, b, houses,
                         enterprises_by_house, rng)

    def _blood_ties(self, realms, houses, rng) -> List[str]:
        """Living cross-house couples slowly pull their houses together."""
        msgs = []
        chars = {c.id: c for realm in realms.values() for c in realm.characters}
        for rec in list(self.marriages):
            id_a, house_a, id_b, house_b = rec
            a, b = chars.get(id_a), chars.get(id_b)
            if not a or not b or not a.is_alive or not b.is_alive:
                self.marriages.remove(rec)
                self.contracts.pop((id_a, id_b), None)
                self.married_ids.discard(id_a)
                self.married_ids.discard(id_b)
                continue
            if _at_war(houses, house_a, house_b):
                continue
            if self.turns % BLOOD_TIE_INTERVAL == 0:
                before = _relation(houses, house_a, house_b)
                _modify_relation(houses, house_a, house_b, BLOOD_TIE_BONUS)
                after = _relation(houses, house_a, house_b)
                if before < ALLIANCE_AT <= after:
                    msgs.append(f"Blood ties seal an ALLIANCE between {house_a} and {house_b}")
                # Children of the union register to the contract's House.
                contract = self.contracts.get((id_a, id_b)) or MarriageContract()
                mother = a if a.gender == "Female" else b
                father = b if mother is a else a
                if mother.age <= 45 and rng.random() < 0.25:
                    parent = mother if contract.matrilineal else father
                    house_name = (house_a if parent is a else house_b)
                    home = realms.get(house_name)
                    if home is not None:
                        child = generate_child(
                            f"{rng.choice(MALE_NAMES + FEMALE_NAMES)} {house_name}",
                            father, mother)
                        child.age = 0
                        child.age_progress.current_age = 0
                        home.dynasty.add_member(child, parent.id)
                        home.characters.append(child)
                        msgs.append(f"A child of the union, {child.name}, is born into House {house_name}")
        return msgs

    def tick(self, realms, houses, enterprises_by_house, rng) -> List[str]:
        """Arrange cross-house matches, then let existing ones pull the
        houses together."""
        self.turns += 1
        msgs: List[str] = []
        if len(realms) >= 2:
            m = self._maybe_arrange_match(realms, houses, enterprises_by_house, rng)
            if m:
                msgs.append(m)
        msgs.extend(self._blood_ties(realms, houses, rng))
        if len(msgs) > MAX_MESSAGES:
            msgs = rng.sample(msgs, MAX_MESSAGES)
        return msgs
