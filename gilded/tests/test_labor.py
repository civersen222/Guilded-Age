"""Tests for gilded.society.labor (mission G6)."""

import random

from gilded.enterprises import Enterprise
from gilded.society import labor
from gilded.society.characters import Character, SocietyState
from gilded.world import generate_atlas


class StubTide:
    def __init__(self):
        self.atrocities = []

    def movement_multiplier(self):
        return 1.0

    def drift_multiplier(self):
        return 1.0

    def record_atrocity(self, kind, house):
        self.atrocities.append((kind, house))


class FakeRealm:
    def __init__(self, characters=None, ruler=None, society=None):
        self.characters = characters or []
        self.ruler = ruler
        self.civ_name = "Vantrell"
        self.society = society


def _prov(atlas=None):
    atlas = atlas or generate_atlas(42)
    return next(iter(atlas.provinces.values()))


def _ent(pid, dial=50.0):
    e = Enterprise(eid=1, kind="colliery", name="Test Colliery",
                   house="Vantrell", province=pid)
    e.extraction_dial = dial
    return e


def test_formula_shapes():
    assert labor.production_multiplier(0) == 0.75
    assert labor.production_multiplier(100) == 1.25
    assert labor.dividend_multiplier(100) > labor.dividend_multiplier(0)
    assert labor.unrest_gain(90) > labor.unrest_gain(30) * 8
    assert labor.accident_chance(40) == 0.0
    assert labor.accident_chance(95) > 0.0
    assert labor.clamp_dial(300) == 100.0 and labor.clamp_dial(-5) == 0.0


def test_dial_from_ruler():
    random.seed(20)
    assert labor.dial_from_ruler(None) == labor.DIAL_DEFAULT
    society = SocietyState(random.Random(20))
    r = Character(name="Baron", stats={}, traits=[], age=50, gender="Male", society=society)
    r.dispositions["labor_capital"] = 90.0
    r.dispositions["preservationist_extractionist"] = 60.0
    assert labor.dial_from_ruler(r) > labor.DIAL_DEFAULT


def test_extraction_accrues_unrest():
    society = SocietyState(random.Random(3))
    prov = _prov()
    ent = _ent(prov.pid, dial=95.0)
    realm = FakeRealm(society=society)
    rng = random.Random(3)
    u0 = prov.unrest
    for _ in range(10):
        labor.tick_extraction(ent, prov, realm, rng, StubTide())
    assert prov.unrest > u0


def test_accident_kills_and_records():
    random.seed(21)
    society = SocietyState(random.Random(21))
    prov = _prov()
    pop0 = prov.population
    director = Character(name="Dir", stats={}, traits=[], age=40, gender="Male", society=society)
    ruler = Character(name="Rul", stats={}, traits=[], age=50, gender="Male", society=society)
    realm = FakeRealm([director, ruler], ruler, society=society)
    ent = _ent(prov.pid, dial=95.0)
    ent.director_id = director.id
    tide = StubTide()
    events = labor.resolve_accident(ent, prov, realm, random.Random(4), tide)
    assert prov.population == pop0 - 1
    assert events
    assert tide.atrocities == [("accident", "Vantrell")]


def test_union_forms_then_strikes_then_stands_down():
    random.seed(22)
    society = SocietyState(random.Random(22))
    prov = _prov()
    prov.movement = None
    prov.unrest = 60.0
    realm = FakeRealm([Character(name="W", stats={}, traits=[], age=30, gender="Male", society=society)], society=society)
    rng = random.Random(5)
    msgs = labor.tick_movement(prov, realm, rng)
    assert prov.movement is not None and "union is born" in " ".join(msgs)
    assert prov.movement.leader is not None
    msgs = labor.tick_movement(prov, realm, rng)
    assert prov.movement.state == "striking"
    while prov.movement.state == "striking":
        labor.tick_movement(prov, realm, rng)
    assert prov.unrest <= labor.STRIKE_END


def test_martyr_spreads_to_sister_province():
    random.seed(23)
    atlas = generate_atlas(42)
    provs = sorted(atlas.provinces.values(), key=lambda p: p.pid)
    a, b = provs[0], provs[1]
    a.owner = b.owner = "Vantrell"
    a.movement = None
    b.movement = None
    society = SocietyState(random.Random(23))
    realm = FakeRealm([Character(name="W", stats={}, traits=[], age=30, gender="Male", society=society)], society=society)
    rng = random.Random(6)
    a.unrest = 60.0
    labor.tick_movement(a, realm, rng)
    mv = a.movement
    tide = StubTide()
    events = labor.martyr_leader(mv, a, provs, realm, rng, tide)
    assert mv.martyr is not None and mv.militancy >= labor.MARTYR_MILITANCY
    assert ("martyrdom", "Vantrell") in tide.atrocities
    assert any(getattr(p, "movement", None) is not None and p is not a
               for p in provs if p.owner == "Vantrell")
    assert any("spreads" in e for e in events)


def test_buy_off_dissolves_cold_movement():
    random.seed(24)
    prov = _prov()
    prov.movement = None
    prov.unrest = 30.0
    society = SocietyState(random.Random(24))
    realm = FakeRealm([Character(name="W", stats={}, traits=[], age=30, gender="Male", society=society)], society=society)
    rng = random.Random(7)
    labor.tick_movement(prov, realm, rng)
    mv = prov.movement
    mv.militancy = 30.0
    events = labor.buy_off_leader(mv, prov)
    assert mv.leader is None
    assert prov.movement is None
    assert any("dissolves" in e for e in events)


def test_cover_up_relieves_unrest_and_stresses_ruler():
    random.seed(25)
    society = SocietyState(random.Random(25))
    prov = _prov()
    prov.unrest = 50.0
    ruler = Character(name="Rul", stats={}, traits=[], age=50, gender="Male", society=society)
    tide = StubTide()
    events = labor.cover_up(ruler, prov, tide)
    assert prov.unrest < 50.0
    assert ruler.stress >= labor.COVERUP_STRESS
    assert ("cover_up", prov.owner) in tide.atrocities
    assert events