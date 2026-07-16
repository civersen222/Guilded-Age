from pathlib import Path
from pygame_app.audio.turn_audio import AudioBundle, on_turn


class FakeSound:
    def __init__(self):
        self.played = []

    def play(self, category, name, volume=0.7):
        self.played.append((category, name))


class FakeMusic:
    def __init__(self):
        self.eras = []

    def update_era(self, name):
        self.eras.append(name)


class FakeAudio:
    def __init__(self, path=None):
        self._path = path
        self.events = []

    def narrate_event(self, event, **kw):
        self.events.append(event)
        return self._path


class FakeEra:
    name = "MEDIEVAL"


class FakeCiv:
    current_era = FakeEra()


class FakeState:
    def __init__(self, pending=None, game_over=False):
        self.pending_ck_event = pending
        self.game_over = game_over


class FakeGame:
    def __init__(self, pending=None, game_over=False):
        self.player_civ = FakeCiv()
        self.state = FakeState(pending, game_over)


def test_updates_era_music():
    music = FakeMusic()
    on_turn(FakeGame(), AudioBundle(music=music))
    assert music.eras == ["MEDIEVAL"]


def test_narrates_and_plays_pending_event():
    played = []
    audio = FakeAudio(path=Path("v.wav"))
    sound = FakeSound()
    bundle = AudioBundle(sound=sound, audio=audio,
                         play_voice=lambda p: played.append(p))
    on_turn(FakeGame(pending={"id": "e1", "title": "War"}), bundle)
    assert audio.events == [{"id": "e1", "title": "War"}]
    assert played == [Path("v.wav")]
    assert ("events", "era_advance.wav") in sound.played


def test_no_event_no_narration():
    audio = FakeAudio(path=Path("v.wav"))
    on_turn(FakeGame(pending=None), AudioBundle(audio=audio))
    assert audio.events == []


def test_game_over_plays_defeat():
    sound = FakeSound()
    on_turn(FakeGame(game_over=True), AudioBundle(sound=sound))
    assert ("events", "defeat.wav") in sound.played


def test_missing_managers_never_raise():
    on_turn(FakeGame(pending={"id": "x"}, game_over=True), AudioBundle())
