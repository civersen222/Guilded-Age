from game_data import Era
from tools.audio_foundry.content_sets import ERA_BEDS, SFX_SET, bed_for


def test_every_era_has_a_bed():
    assert set(ERA_BEDS) == set(Era)


def test_bed_refs_unique():
    refs = [b.bed_ref for b in ERA_BEDS.values()]
    assert len(refs) == len(set(refs))


def test_sfx_ids_consistent_and_unique():
    assert len(SFX_SET) >= 1
    for k, v in SFX_SET.items():
        assert k == v.sfx_id
    assert len(SFX_SET) == len({v.sfx_id for v in SFX_SET.values()})


def test_bed_for_returns_matching_era():
    assert bed_for(Era.MODERN).era is Era.MODERN
