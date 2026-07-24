
"""Tests for gilded.society.marriages (mission G10)."""

import random

from gilded.enterprises import Enterprise
from gilded.houses import House
from gilded.society.characters import Character, SocietyState
from gilded.society.marriages import (
    ALLIANCE_AT,
    BLOOD_TIE_INTERVAL,
    MarriageContract,
    MarriageRegistry,
    asking_price,
    bloodline_quality,
    house_power,
    scandal_discount,
)
from gilded.society.realm import create_house_realm


class FixedRng:
    """Constant-roll rng: keeps ambient weddings and births controllable."""

    def __init__(self, r=0.9):
        self.r = r

    def random(self):
        return self.r

    def randint(self, a, b):
        return a

    def choice(self, seq):
        return seq[0]

    def shuffle(self, seq):
        pass

    def sample(self, seq, k):
        return seq[:k]

    def gauss(self, mu, sigma):
        return mu


def _setup(seed):
    random.seed(seed)
    rng = random.Random(seed)
    society = SocietyState(rng)
    realms = {"Vantrell": create_house_realm("Vantrell", society),
              "Karsgate": create_house_realm("Karsgate", society)}
    houses = {"Vantrell": House(name="Vantrell", capital=0),
              "Karsgate": House(name="Karsgate", capital=1)}
    ents = {"Vantrell": [], "Karsgate": []}
    return realms, houses, ents, society


def test_valuation_formulas():
    random.seed(110)
    society = SocietyState(random.Random(110))
    c = Character(name="Vera Vantrell", stats={}, traits=[], age=25, gender="Female", society=society)
    c.dispositions = {k: 0.0 for k in c.dispositions}
    c.dispositions["brilliant_dull"] = -50.0
    c.dispositions["comely_plain"] = -30.0
    c.persona = {k: 0.0 for k in c.persona}
    assert bloodline_quality(c) == 80.0
    ent = Enterprise(eid=1, kind="bank", name="B", house="Vantrell", province=0)
    ent.tier = 2
    assert house_power([ent]) == 100.0
    c.persona["honest_deceitful"] = 40.0
    assert scandal_discount(c) == 6.0
    assert asking_price(c, [ent]) == 10.0 + 40.0 + 100.0 - 6.0
    assert asking_price(c, []) >= 1.0


def test_eligible_filters():
    realms, houses, ents, rng = _setup(111)
    ra = realms["Vantrell"]
    reg = MarriageRegistry()
    pool = reg._eligible(ra)
    assert all(16 <= c.age <= 50 and c.is_alive for c in pool)
    assert all(c.id != ra.ruler.id for c in pool)
    reg.married_ids.add(pool[0].id)
    assert pool[0] not in reg._eligible(ra)
    women = reg._eligible(ra, "Female")
    assert all(c.gender == "Female" for c in women)


def test_arrange_match_between():
    realms, houses, ents, rng = _setup(112)
    ra, rb = realms["Vantrell"], realms["Karsgate"]
    reg = MarriageRegistry()
    n_before = len(rb.characters)
    msg = reg.arrange_match_between("Vantrell", "Karsgate", realms, houses,
                                    ents, FixedRng(0.9))
    assert msg and "weds" in msg
    assert reg.wedding_count == 1 and len(reg.married_ids) == 2
    assert len(reg.marriages) == 1 and len(reg.contracts) == 1
    id_a, house_a, id_b, house_b = reg.marriages[0]
    assert (house_a, house_b) == ("Vantrell", "Karsgate")
    assert any(c.id == id_b for c in ra.characters)     # spouse moved in
    assert not any(c.id == id_b for c in rb.characters)
    assert len(rb.characters) == n_before - 1
    assert id_b in ra.dynasty.all_characters
    assert houses["Vantrell"].relations["Karsgate"] == 25
    assert houses["Karsgate"].relations["Vantrell"] == 25


def test_war_blocks_matches():
    realms, houses, ents, rng = _setup(113)
    houses["Vantrell"].at_war_with.add("Karsgate")
    houses["Karsgate"].at_war_with.add("Vantrell")
    reg = MarriageRegistry()
    assert reg.arrange_match_between("Vantrell", "Karsgate", realms, houses,
                                     ents, FixedRng(0.9)) is None
    assert reg.wedding_count == 0


def test_dowry_changes_hands():
    realms, houses, ents, rng = _setup(114)
    ra, rb = realms["Vantrell"], realms["Karsgate"]
    ra.ruler.gold_reserve = 500.0
    reg = MarriageRegistry()
    msg = reg.arrange_match_between("Vantrell", "Karsgate", realms, houses,
                                    ents, FixedRng(0.9))
    assert msg
    contract = next(iter(reg.contracts.values()))
    assert contract.alliance and contract.dowry_gold > 0
    assert not contract.matrilineal and not contract.board_seat   # 0.9 rolls
    assert ra.ruler.gold_reserve == 500.0 - contract.dowry_gold
    assert rb.ruler.gold_reserve == contract.dowry_gold


def test_blood_ties_alliance_once():
    realms, houses, ents, rng = _setup(115)
    reg = MarriageRegistry()
    assert reg.arrange_match_between("Vantrell", "Karsgate", realms, houses,
                                     ents, FixedRng(0.9))
    houses["Vantrell"].relations["Karsgate"] = ALLIANCE_AT - 2
    houses["Karsgate"].relations["Vantrell"] = ALLIANCE_AT - 2
    seals = []
    for _ in range(BLOOD_TIE_INTERVAL * 2):
        seals.extend(m for m in reg.tick(realms, houses, ents, FixedRng(0.9))
                     if "ALLIANCE" in m)
    assert len(seals) == 1
    assert houses["Vantrell"].relations["Karsgate"] >= ALLIANCE_AT


def test_blood_ties_children():
    realms, houses, ents, rng = _setup(116)
    reg = MarriageRegistry()
    assert reg.arrange_match_between("Vantrell", "Karsgate", realms, houses,
                                     ents, FixedRng(0.9))
    key = next(iter(reg.contracts))
    reg.contracts[key] = MarriageContract(matrilineal=False)
    id_a, _, id_b, _ = reg.marriages[0]
    everyone = [c for r in realms.values() for c in r.characters]
    for c in everyone:
        if c.id in (id_a, id_b):
            c.age = 30                                 # keep the union fertile
    total = sum(len(r.characters) for r in realms.values())
    births = []
    for _ in range(BLOOD_TIE_INTERVAL):
        births.extend(m for m in reg.tick(realms, houses, ents, FixedRng(0.1))
                      if "child of the union" in m)
    assert births
    assert sum(len(r.characters) for r in realms.values()) == total + len(births)


def test_widowed_marriages_dissolve():
    realms, houses, ents, rng = _setup(117)
    ra = realms["Vantrell"]
    reg = MarriageRegistry()
    assert reg.arrange_match_between("Vantrell", "Karsgate", realms, houses,
                                     ents, FixedRng(0.9))
    id_a, _, id_b, _ = reg.marriages[0]
    spouse = next(c for c in ra.characters if c.id == id_b)
    spouse.is_alive = False
    reg.tick(realms, houses, ents, FixedRng(0.9))
    assert reg.marriages == [] and reg.contracts == {}
    assert reg.married_ids == set()
