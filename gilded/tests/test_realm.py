"""Tests for gilded.society.realm and gilded.society.population (mission G8)."""

import random

from gilded.enterprises import Enterprise
from gilded.society.characters import opinion_matrix
from gilded.society.court import CourtPosition
from gilded.society.population import bulk_pass, promote, relevance_set
from gilded.society.realm import (
    DISLOYAL_LOYALTY,
    Realm,
    create_house_realm,
    disloyal_shareholders,
    tick_directors,
    tick_loyalty,
)


def test_create_house_realm_basics():
    random.seed(80)
    rng = random.Random(11)
    realm = create_house_realm("Vantrell", rng)
    assert realm.house_name == "Vantrell"
    assert realm.ruler.is_alive and 28 <= realm.ruler.age <= 45
    assert realm.ruler.name.endswith("Vantrell")
    spouse = realm.characters[1]
    assert spouse.gender != realm.ruler.gender
    assert 43 <= len(realm.characters) <= 64
    assert sum(1 for p in CourtPosition if realm.court.positions[p]) == 6
    seated_ids = {ch.id for ch in realm.court.positions.values() if ch}
    assert realm.ruler.id not in seated_ids


def test_create_house_realm_dynasty_children():
    random.seed(81)
    realm = create_house_realm("Karsgate", random.Random(3))
    kids = [c for c in realm.characters if c.parent_ids]
    assert 1 <= len(kids) <= 2
    for kid in kids:
        assert kid.age == 0
        assert kid.id in realm.dynasty.all_characters
        assert kid.id in realm.ruler.children_ids


def test_create_house_realm_rng_determinism():
    random.seed(82)
    a = create_house_realm("Vantrell", random.Random(11))
    b = create_house_realm("Vantrell", random.Random(11))
    assert a.ruler.name == b.ruler.name
    assert a.ruler.age == b.ruler.age
    assert len(a.characters) == len(b.characters)
    assert [c.name for c in a.characters] == [c.name for c in b.characters]


def test_tick_directors_appoints_and_pays():
    random.seed(83)
    rng = random.Random(4)
    realm = create_house_realm("Vantrell", rng)
    paid = Enterprise(eid=1, kind="bank", name="Vantrell Trust",
                      house="Vantrell", province=0)
    paid.ledger = {realm.ruler.id: 100.0}
    free = Enterprise(eid=2, kind="mill", name="Ash Mill",
                      house="Vantrell", province=1)
    other = Enterprise(eid=3, kind="bank", name="Rival Bank",
                       house="Karsgate", province=2)
    events = tick_directors(realm, [paid, free, other], rng)
    assert paid.director_id and free.director_id
    assert paid.director_id != free.director_id
    assert other.director_id == ""                     # other houses untouched
    seated_ids = {ch.id for ch in realm.court.positions.values() if ch}
    assert paid.director_id not in seated_ids
    assert paid.director_id != realm.ruler.id
    assert paid.ledger[paid.director_id] == 10.0
    assert paid.ledger[realm.ruler.id] == 90.0
    assert any("enfeoffed" in e for e in events)
    assert any("appointed" in e for e in events)


def test_tick_directors_replaces_dead_and_focus():
    random.seed(84)
    rng = random.Random(5)
    realm = create_house_realm("Vantrell", rng)
    ent = Enterprise(eid=1, kind="bank", name="Vantrell Trust",
                     house="Vantrell", province=0)
    tick_directors(realm, [ent], rng)
    first = ent.director_id
    by_id = {ch.id: ch for ch in realm.characters}
    director = by_id[first]
    assert director.focus.attribute == "industry"
    assert director.focus.progress == 1
    director.is_alive = False
    tick_directors(realm, [ent], rng)
    assert ent.director_id and ent.director_id != first


def test_tick_loyalty_targets_and_disloyalty():
    random.seed(85)
    rng = random.Random(6)
    realm = create_house_realm("Vantrell", rng)
    ch = next(c for c in realm.court.positions.values() if c is not None)
    ch.dispositions["labor_capital"] = 0.0
    realm.ruler.dispositions["labor_capital"] = 0.0
    opinion_matrix[(ch.id, realm.ruler.id)] = -60
    events1 = tick_loyalty(realm, [], rng)
    assert abs(ch.loyalty - 44.0) < 1e-6               # 50 + (20-50)*0.2
    events2 = tick_loyalty(realm, [], rng)
    assert ch.loyalty < DISLOYAL_LOYALTY
    assert any(ch.name in e for e in events1 + events2)


def test_tick_loyalty_pay_helps():
    random.seed(86)
    rng = random.Random(7)
    realm = create_house_realm("Vantrell", rng)
    seated = [c for c in realm.court.positions.values() if c is not None]
    a, b = seated[0], seated[1]
    for c in (a, b):
        c.dispositions["labor_capital"] = 0.0
        opinion_matrix[(c.id, realm.ruler.id)] = 0
    realm.ruler.dispositions["labor_capital"] = 0.0
    ent = Enterprise(eid=1, kind="bank", name="Vantrell Trust",
                     house="Vantrell", province=0)
    ent.ledger = {a.id: 5.0}
    tick_loyalty(realm, [ent], rng)
    assert a.loyalty > b.loyalty


def test_disloyal_shareholders():
    random.seed(87)
    rng = random.Random(8)
    realm = create_house_realm("Vantrell", rng)
    holder = realm.characters[10]
    holder.loyalty = 30.0
    ruler = realm.ruler
    ruler.loyalty = 0.0
    ent = Enterprise(eid=1, kind="bank", name="Vantrell Trust",
                     house="Vantrell", province=0)
    ent.ledger = {holder.id: 5.0, ruler.id: 60.0}
    out = disloyal_shareholders(realm, [ent])
    assert holder in out
    assert ruler not in out                            # ruler never sells out
    loyal_broke = realm.characters[11]
    loyal_broke.loyalty = 10.0
    assert loyal_broke not in out                      # no stake, no listing


def test_bulk_pass_ages_births_and_skips():
    random.seed(88)
    rng = random.Random(9)
    realm = create_house_realm("Vantrell", rng)
    elder = realm.characters[10]
    elder.age = 79
    elder.age_progress.current_age = 79
    ruler_age = realm.ruler.age
    born_total = []
    msgs_total = []
    for turn in range(30):
        msgs, born = bulk_pass(realm, turn, rng,
                               skip_ids={realm.ruler.id},
                               notable_ids={elder.id})
        born_total.extend(born)
        msgs_total.extend(msgs)
    assert realm.ruler.age == ruler_age                # skipped
    assert not elder.is_alive
    assert any(elder.name in m for m in msgs_total)
    assert born_total                                  # someone was born
    child = born_total[0]
    assert child in realm.characters
    assert child.age <= 30 and child.name.endswith("Vantrell")


def test_relevance_set_and_promote():
    random.seed(89)
    rng = random.Random(10)
    realm = create_house_realm("Vantrell", rng)
    rs = relevance_set(realm, {"agent-x"})
    assert realm.ruler.id in rs
    assert "agent-x" in rs
    for ch in realm.court.positions.values():
        assert ch.id in rs
    outsider = next(c for c in realm.characters
                    if c.id not in rs)
    promote(realm, outsider)
    assert outsider.id in relevance_set(realm, set())

