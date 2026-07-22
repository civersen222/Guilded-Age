"""Tests for gilded.houses (mission G2)."""

from gilded.houses import GREAT_HOUSE_COUNT, HOUSE_NAMES, House, assign_houses
from gilded.world import MINOR_OWNER, generate_atlas


def _bfs_owned(atlas, start, owned):
    seen = {start}
    queue = [start]
    while queue:
        cur = queue.pop(0)
        for n in atlas.provinces[cur].neighbors:
            if n in owned and n not in seen:
                seen.add(n)
                queue.append(n)
    return seen


def test_house_count_and_names():
    atlas = generate_atlas(42)
    houses = assign_houses(atlas, 42)
    assert len(houses) == GREAT_HOUSE_COUNT
    assert set(houses) == set(HOUSE_NAMES[:GREAT_HOUSE_COUNT])
    for name, house in houses.items():
        assert isinstance(house, House)
        assert house.name == name
        assert house.treasury == 2000.0
        assert not house.is_player


def test_cluster_sizes_and_capitals():
    atlas = generate_atlas(42)
    houses = assign_houses(atlas, 42)
    for house in houses.values():
        owned = {p.pid for p in atlas.provinces.values() if p.owner == house.name}
        assert 5 <= len(owned) <= 7
        assert house.capital in owned
        assert atlas.provinces[house.capital].garrison == 2


def test_clusters_contiguous():
    atlas = generate_atlas(42)
    houses = assign_houses(atlas, 42)
    for house in houses.values():
        owned = {p.pid for p in atlas.provinces.values() if p.owner == house.name}
        assert _bfs_owned(atlas, house.capital, owned) == owned


def test_minors_remain():
    atlas = generate_atlas(42)
    houses = assign_houses(atlas, 42)
    minors = [p for p in atlas.provinces.values() if p.owner == MINOR_OWNER]
    assert len(minors) >= 5
    assert all(p.garrison == 1 for p in minors)


def test_relations_initialised():
    atlas = generate_atlas(42)
    houses = assign_houses(atlas, 42)
    for a in houses:
        others = set(houses) - {a}
        assert set(houses[a].relations) == others
        assert all(v == 0 for v in houses[a].relations.values())
        assert houses[a].at_war_with == set()
        assert houses[a].truces == {}


def test_deterministic():
    h1 = assign_houses(generate_atlas(42), 42)
    h2 = assign_houses(generate_atlas(42), 42)
    assert {h.capital for h in h1.values()} == {h.capital for h in h2.values()}
    assert {n: h.capital for n, h in h1.items()} == {n: h.capital for n, h in h2.items()}


def test_multiple_seeds():
    for seed in (1, 7, 2026):
        atlas = generate_atlas(seed)
        houses = assign_houses(atlas, seed)
        assert len(houses) == GREAT_HOUSE_COUNT
        for house in houses.values():
            owned = [p for p in atlas.provinces.values() if p.owner == house.name]
            assert 5 <= len(owned) <= 7

