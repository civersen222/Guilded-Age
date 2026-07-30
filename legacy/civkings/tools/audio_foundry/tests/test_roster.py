from game_data import CIVILIZATIONS
from tools.audio_foundry.roster import ROSTER, profile_for


def test_roster_covers_exactly_the_civilizations():
    assert set(ROSTER) == set(CIVILIZATIONS)


def test_voice_refs_are_unique():
    refs = [p.voice_ref for p in ROSTER.values()]
    assert len(refs) == len(set(refs))


def test_unknown_civ_falls_back():
    p = profile_for("Atlantis")
    assert p.civ_id == "unknown"
    assert p.voice_ref == "voice_default"
