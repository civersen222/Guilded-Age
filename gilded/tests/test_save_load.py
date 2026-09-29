"""Stage S13: the save survives.

A save is the game: round-tripping through a file in a fresh load must
continue the world identically, and every foreign or corrupt file must be
refused with a SaveError a player could read — never a leaked pickle crash.
"""
import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gilded.chassis import GildedGame
from gilded.save import SaveError, load_game, save_game


def _digest(g):
    h = hashlib.sha256()
    h.update(repr((g.turn,
                   {k: round(v.treasury, 6) for k, v in sorted(g.houses.items())},
                   sorted((c.name, c.age, round(getattr(c, "loyalty", -1.0), 4), c.is_alive)
                          for r in g.realms.values() for c in r.characters),
                   sorted((e.eid, e.tier, e.house, e.under_construction, e.target_tier)
                          for e in g.enterprises),
                   repr(g.rng.getstate()),
                   len(g.events))).encode())
    return h.hexdigest()


def test_round_trip_is_the_same_game(tmp_path):
    g = GildedGame(seed=7)
    for i in range(20):
        g.turn += 1
        g.end_turn()
        if i == 10:
            # the off-book mark: a mutation no seed replay could reproduce
            for j, h2 in enumerate(sorted(g.houses)[:2]):
                g.houses[h2].treasury += 12345.678 + j

    path = tmp_path / "s13.gsave"
    save_game(g, path)

    # the file is BYTES here — a fresh process cannot hide behind a cache
    with open(path, "rb") as f:
        raw = f.read()
    assert raw.startswith(b"GILDEDSAVE 1\n")

    # replay 10 turns on the continued game, then load from the same bytes
    for _ in range(10):
        g.turn += 1
        g.end_turn()

    raw_path = tmp_path / "s13_raw.gsave"
    raw_path.write_bytes(raw)
    g2 = load_game(str(raw_path))

    for _ in range(10):
        g2.turn += 1
        g2.end_turn()

    assert _digest(g2) == _digest(g)


def test_round_trip_at_more_seeds(tmp_path):
    for seed in (42, 61):
        g = GildedGame(seed=seed)
        for i in range(20):
            g.turn += 1
            g.end_turn()
        path = tmp_path / f"s13_{seed}.gsave"
        save_game(g, str(path))
        g2 = load_game(str(path))
        for _ in range(10):
            g.turn += 1
            g.end_turn()
        for _ in range(10):
            g2.turn += 1
            g2.end_turn()
        assert _digest(g2) == _digest(g)


def test_docket_rides_in_the_save(tmp_path):
    g = GildedGame(seed=7)
    for i in range(20):
        g.turn += 1
        g.end_turn()
    path = tmp_path / "s13_docket.gsave"
    save_game(g, str(path))
    g2 = load_game(str(path))
    assert g2.docket_by_house.keys() == g.docket_by_house.keys()
    for h in g.docket_by_house:
        assert len(g2.docket_by_house[h]) == len(g.docket_by_house[h])


def test_empty_file_raises_save_error(tmp_path):
    p = tmp_path / "empty.gsave"
    p.write_bytes(b"")
    with pytest.raises(SaveError) as ei:
        load_game(str(p))
    assert isinstance(ei.value, SaveError)
    assert str(ei.value)


def test_garbage_bytes_raise_save_error(tmp_path):
    p = tmp_path / "garbage.gsave"
    p.write_bytes(os.urandom(64))
    with pytest.raises(SaveError) as ei:
        load_game(str(p))
    assert isinstance(ei.value, SaveError)
    assert str(ei.value)


def test_truncated_valid_save_raises_save_error(tmp_path):
    g = GildedGame(seed=7)
    path = tmp_path / "s13_trunc.gsave"
    save_game(g, str(path))
    raw = path.read_bytes()
    trunc = tmp_path / "s13_trunc_cut.gsave"
    trunc.write_bytes(raw[:len(raw) // 2])
    with pytest.raises(SaveError) as ei:
        load_game(str(trunc))
    assert isinstance(ei.value, SaveError)
    assert str(ei.value)


def test_forged_version_refused_by_name(tmp_path):
    g = GildedGame(seed=7)
    path = tmp_path / "s13_forged.gsave"
    save_game(g, str(path))
    raw = path.read_bytes()
    assert raw.startswith(b"GILDEDSAVE 1\n")
    forged = tmp_path / "s13_forged9999.gsave"
    forged.write_bytes(b"GILDEDSAVE 9999\n" + raw[len(b"GILDEDSAVE 1\n"):])
    with pytest.raises(SaveError) as ei:
        load_game(str(forged))
    assert isinstance(ei.value, SaveError)
    assert "9999" in str(ei.value)


def test_legacy_raw_pickle_without_header_raises_save_error(tmp_path):
    import pickle
    g = GildedGame(seed=7)
    p = tmp_path / "legacy.pkl"
    p.write_bytes(pickle.dumps(g))
    with pytest.raises(SaveError) as ei:
        load_game(str(p))
    assert isinstance(ei.value, SaveError)
    assert str(ei.value)
