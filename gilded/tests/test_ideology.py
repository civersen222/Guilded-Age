"""Tests for gilded.society.ideology (mission G7)."""

import random

from gilded.enterprises import Enterprise
from gilded.houses import assign_houses
from gilded.society.ideology import (
    COLLECTIVE_ID,
    IdeologicalTide,
    LEGITIMACY_START,
    REVOLUTION_OWNER,
    TRANSFORM_LEGITIMACY,
    can_transform,
    record_scandal,
    revolution_brewing,
    tick_legitimacy,
    transform_house,
    trigger_revolution,
)
from gilded.society.labor import DIAL_DEFAULT, Movement
from gilded.society.characters import Character
from gilded.world import generate_atlas


def test_tide_rises_and_phases():
    tide = IdeologicalTide()
    assert tide.phase() == "reformist"
    for _ in range(10):
        tide.tick()
    assert 0 < tide.level <= 100.0
    tide.level = 50.0
    assert tide.phase() == "socialist"
    tide.level = 90.0
    assert tide.phase() == "revolutionary"


def test_atrocities_feed_tide_and_stain_house():
    tide = IdeologicalTide()
    w = tide.record_atrocity("martyrdom", "Vantrell")
    assert w == 4.0 and tide.level > 0
    assert tide.house_atrocities["Vantrell"] == 4.0
    assert tide.consume_fresh("Vantrell") == 4.0
    assert tide.consume_fresh("Vantrell") == 0.0
    assert tide.movement_multiplier() >= 1.0
    assert tide.drift_multiplier() >= 1.0


def test_legitimacy_recovers_and_drains():
    up = tick_legitimacy(50.0, 20)
    assert up > 50.0
    down = tick_legitimacy(50.0, -30)
    assert down < 50.0
    tide = IdeologicalTide()
    tide.level = 100.0
    drained = tick_legitimacy(50.0, 0, tide, fresh_atrocities=2.0)
    assert drained < 50.0
    assert tick_legitimacy(0.0, -100) == 0.0
    assert tick_legitimacy(100.0, 20) == 100.0


def test_record_scandal():
    legit = {"Vantrell": 60.0}
    events = []
    loss = record_scandal(legit, "Vantrell", severity=2.0, events=events)
    assert loss == 16.0 and legit["Vantrell"] == 44.0
    assert events and "Scandal" in events[0]
    record_scandal(legit, "Unknown")
    assert legit["Unknown"] == LEGITIMACY_START - 8.0


def test_revolution_brewing_conditions():
    atlas = generate_atlas(42)
    houses = assign_houses(atlas, 42)
    hname = next(iter(houses))
    owned = [p for p in atlas.provinces.values() if p.owner == hname]
    assert not revolution_brewing(80.0, owned)
    assert not revolution_brewing(0.0, owned)          # no movement yet
    mv = Movement(province_pid=owned[0].pid, leader=None)
    mv.militancy = 90.0
    owned[0].movement = mv
    assert not revolution_brewing(0.0, owned)          # union, not striking
    mv.state = "striking"
    assert revolution_brewing(0.0, owned)


def test_trigger_revolution_flips_and_clears():
    atlas = generate_atlas(42)
    houses = assign_houses(atlas, 42)
    hname = next(iter(houses))
    owned = [p for p in atlas.provinces.values() if p.owner == hname]
    mv = Movement(province_pid=owned[0].pid, leader=None)
    mv.state = "striking"
    mv.militancy = 90.0
    owned[0].movement = mv
    ent = Enterprise(eid=1, kind="bank", name="B", house=hname,
                     province=owned[0].pid)
    ent.ledger = {"a": 100.0}
    ent.extraction_dial = 95.0
    msgs, flipped = trigger_revolution(hname, owned, [ent])
    assert owned[0].pid in flipped
    assert owned[0].owner == REVOLUTION_OWNER
    assert owned[0].movement is None and owned[0].unrest == 0.0
    assert ent.ledger == {} and ent.extraction_dial == DIAL_DEFAULT
    assert any("REVOLUTION" in m for m in msgs)
    assert owned[1].owner == hname                     # unorganized stays


def test_can_transform_checks_true_conviction():
    random.seed(30)
    r = Character(name="Chairman", stats={}, traits=[], age=50, gender="Male")
    r.dispositions["labor_capital"] = -60.0
    r.persona["labor_capital"] = 50.0                  # persona does not fool it
    assert can_transform(r)
    r.dispositions["labor_capital"] = 0.0
    assert not can_transform(r)
    assert not can_transform(None)


def test_transform_house_concedes_everything():
    random.seed(31)
    atlas = generate_atlas(42)
    houses = assign_houses(atlas, 42)
    hname = next(iter(houses))
    owned = [p for p in atlas.provinces.values() if p.owner == hname]
    owned[0].unrest = 40.0
    owned[0].movement = Movement(province_pid=owned[0].pid, leader=None)
    ent = Enterprise(eid=1, kind="bank", name="B", house=hname,
                     province=owned[0].pid)
    ent.ledger = {"a": 100.0}
    ent.extraction_dial = 90.0
    other = Enterprise(eid=2, kind="bank", name="O", house="Other", province=0)
    other.ledger = {"b": 100.0}
    ruler = Character(name="Chairman", stats={}, traits=[], age=50, gender="Male")
    msgs, new_legit = transform_house(hname, ruler, owned, [ent, other],
                                      None, 10.0)
    assert new_legit == TRANSFORM_LEGITIMACY
    assert ent.ledger == {COLLECTIVE_ID: 100.0}
    assert ent.extraction_dial == DIAL_DEFAULT
    assert other.ledger == {"b": 100.0}                # other houses untouched
    assert owned[0].unrest == 0.0 and owned[0].movement is None
    assert any("transforms" in m for m in msgs)
