from game_data import Era
from pygame_app.audio.music_manager import MusicManager
from tools.audio_foundry.game_paths import (
    era_music_filename,
    era_music_path,
    sfx_target,
)


def test_era_filenames_match_music_manager():
    for era in Era:
        assert era_music_filename(era) == MusicManager.ERA_FILES[era.name]


def test_era_music_path_under_music_dir():
    p = str(era_music_path(Era.MODERN)).replace("\\", "/")
    assert p == "assets/music/modern.ogg"


def test_sfx_target_shape():
    cat, name, path = sfx_target("battle_clash")
    assert cat == "events"
    assert name == "battle_clash.wav"
    assert str(path).replace("\\", "/") == "assets/sounds/events/battle_clash.wav"
