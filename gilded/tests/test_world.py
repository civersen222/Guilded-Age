"""G1: the atlas generator is deterministic, bounded, and well-formed."""

from gilded.world import (
    ENDOWMENT_MINIMUMS, PROVINCE_MAX, PROVINCE_MIN, TERRAINS, generate_atlas,
)

ATLAS = generate_atlas(42)


def test_deterministic_same_seed():
    again = generate_atlas(42)
    assert [p.name for p in ATLAS.provinces.values()] == [p.name for p in again.provinces.values()]
    assert [p.terrain for p in ATLAS.provinces.values()] == [p.terrain for p in again.provinces.values()]


def test_different_seed_differs():
    other = generate_atlas(7)
    assert [p.name for p in other.provinces.values()] != [p.name for p in ATLAS.provinces.values()]


def test_province_count_bounds():
    assert PROVINCE_MIN <= len(ATLAS.provinces) <= PROVINCE_MAX


def test_provinces_well_formed():
    for p in ATLAS.provinces.values():
        assert p.terrain in TERRAINS
        assert p.population > 0
        assert p.cells and p.center
        for kind, richness in p.endowments.items():
            assert 1 <= richness <= 3
        for n in p.neighbors:
            assert p.pid in ATLAS.provinces[n].neighbors


def test_endowment_minimums():
    kinds = [k for p in ATLAS.provinces.values() for k in p.endowments]
    for kind, need in ENDOWMENT_MINIMUMS.items():
        assert kinds.count(kind) >= need, kind


def test_links_and_distance():
    for (a, b), ln in ATLAS.links.items():
        assert a < b and not ln.rail
        assert b in ATLAS.provinces[a].neighbors
    d = ATLAS.distance(min(ATLAS.provinces), max(ATLAS.provinces))
    assert d > 0
