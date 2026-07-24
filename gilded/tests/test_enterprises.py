"""Tests for gilded.enterprises and gilded.society.shares (mission G4)."""

import random

from gilded.enterprises import (
    ENTERPRISE_TYPES,
    Enterprise,
    capacity_out,
    found_enterprise,
    output_gold,
    tick_construction,
)
from gilded.society import shares
from gilded.society.characters import Character, Dynasty, SocietyState, generate_child
from gilded.world import generate_atlas


class FakeRealm:
    def __init__(self, ruler, characters, society=None):
        self.ruler = ruler
        self.characters = characters
        self.dynasty = Dynasty(ruler, {c.id: c for c in characters})
        self.society = society


def _coal_province(atlas):
    return next(p for p in atlas.provinces.values() if "coalfield" in p.endowments)


def _bare_province(atlas):
    return next(p for p in atlas.provinces.values() if "coalfield" not in p.endowments)


def _built(kind, province, eid=1):
    ent = found_enterprise(kind, "Vantrell", province, eid, random.Random(1))
    while not tick_construction(ent):
        pass
    return ent


def test_found_requires_endowment():
    atlas = generate_atlas(42)
    assert found_enterprise("colliery", "V", _bare_province(atlas), 1, random.Random(1)) is None
    ent = found_enterprise("colliery", "V", _coal_province(atlas), 1, random.Random(1))
    assert ent is not None and ent.under_construction > 0 and ent.tier == 1


def test_bank_needs_no_endowment():
    atlas = generate_atlas(42)
    ent = found_enterprise("bank", "V", _bare_province(atlas), 1, random.Random(1))
    assert ent is not None


def test_construction_ticks_to_completion():
    atlas = generate_atlas(42)
    prov = _coal_province(atlas)
    ent = found_enterprise("colliery", "V", prov, 1, random.Random(1))
    assert output_gold(ent, prov, None) == 0.0
    turns = 0
    while not tick_construction(ent):
        turns += 1
    assert ent.under_construction == 0
    assert output_gold(ent, prov, None) > 0.0


def test_output_scales_with_dial_and_director():
    random.seed(2)
    atlas = generate_atlas(42)
    prov = _coal_province(atlas)
    ent = _built("colliery", prov)
    base = output_gold(ent, prov, None)
    ent.extraction_dial = 100.0
    assert output_gold(ent, prov, None) > base
    ent.extraction_dial = 50.0
    society = SocietyState(random.Random(2))
    director = Character(name="D", stats={"industry": 16}, traits=[], age=40, gender="Male", society=society)
    assert output_gold(ent, prov, director) > base
    assert output_gold(ent, prov, None, tech_mod=1.5) > base


def test_capacity_out():
    atlas = generate_atlas(42)
    prov = _coal_province(atlas)
    ent = _built("colliery", prov)
    kind, amt = capacity_out(ent, prov)
    assert kind == "coal" and amt >= 1.0
    bare = _bare_province(atlas)
    bank = _built("bank", bare, eid=2)
    assert capacity_out(bank, bare) == (None, 0.0)


def test_initial_ledger_and_dividends():
    random.seed(3)
    atlas = generate_atlas(42)
    prov = _coal_province(atlas)
    society = SocietyState(random.Random(3))
    ruler = Character(name="R", stats={}, traits=[], age=45, gender="Male", society=society)
    consort = Character(name="C", stats={}, traits=[], age=40, gender="Female", society=society)
    kid = generate_child("K", ruler, consort, society.rng)
    kid.age = 20
    realm = FakeRealm(ruler, [ruler, consort, kid], society=society)
    realm.dynasty.add_member(kid, ruler.id)
    ent = _built("colliery", prov)
    shares.initial_ledger(ent, realm)
    assert abs(ent.ledger_total() - 100.0) < 1e-6
    assert ent.ledger[ruler.id] == 60.0
    take, _events = shares.pay_dividends(realm, [ent], atlas.provinces)
    assert take > 0 and ruler.gold_reserve > 0 and kid.gold_reserve > 0


def test_transfer_and_extort_and_stake():
    ent = Enterprise(eid=1, kind="bank", name="B", house="V", province=0)
    ent.ledger = {"a": 60.0, "b": 40.0}
    moved = shares.transfer_shares(ent, "a", "b", 10.0)
    assert abs(moved - 10.0) < 1e-6
    assert abs(ent.ledger["a"] - 50.0) < 1e-6
    assert abs(ent.ledger_total() - 100.0) < 1e-6
    ent2 = Enterprise(eid=2, kind="bank", name="B2", house="V", province=0)
    ent2.ledger = {"a": 100.0}
    total = shares.extort_shares([ent, ent2], "a", "b", 25.0)
    assert abs(total - 50.0) < 1e-6
    assert shares.house_stake([ent, ent2], "b") > 0.0


def test_partition_shares_primogeniture():
    random.seed(4)
    society = SocietyState(random.Random(4))
    old = Character(name="Old", stats={}, traits=[], age=70, gender="Male", society=society)
    heir = Character(name="Heir", stats={}, traits=[], age=30, gender="Male", society=society)
    spare = Character(name="Spare", stats={}, traits=[], age=25, gender="Male", society=society)
    realm = FakeRealm(old, [old, heir, spare], society=society)
    realm.dynasty.all_characters = {c.id: c for c in (old, heir, spare)}
    ent = Enterprise(eid=1, kind="bank", name="B", house="V", province=0)
    ent.ledger = {old.id: 100.0}
    events = shares.partition_shares(realm, [ent], old, heir, "PRIMOGENITURE")
    assert old.id not in ent.ledger
    assert abs(ent.ledger[heir.id] - 50.0) < 1e-6
    assert abs(ent.ledger[spare.id] - 50.0) < 1e-6
    assert events


def test_seize_enterprises():
    random.seed(5)
    society = SocietyState(random.Random(5))
    victor = Character(name="Victor", stats={}, traits=[], age=40, gender="Male", society=society)
    realm = FakeRealm(victor, [victor], society=society)
    ent = Enterprise(eid=1, kind="bank", name="B", house="Loser", province=0)
    ent.ledger = {"ghost": 100.0}
    other = Enterprise(eid=2, kind="bank", name="B2", house="Third", province=0)
    n = shares.seize_enterprises([ent, other], "Loser", "Victor", realm)
    assert n == 1
    assert ent.house == "Victor" and ent.ledger == {victor.id: 100.0}
    assert other.house == "Third"
