"""C8.4 - the ambient bed per act: three distinct minute-plus beds on disk,
sha256-distinct, the act bands pick the right bed, and mute still rules."""

import hashlib
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gilded import audio
from gilded.audio import ambient_event_for


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def test_three_beds_on_disk_distinct():
    paths = [audio.resolve(e) for e in ("ambient_act1", "ambient_act2", "ambient_act3")]
    for p in paths:
        assert os.path.isfile(p), p
    hashes = {_sha(p) for p in paths}
    assert len(hashes) == 3


def test_beds_are_minute_plus():
    pygame.mixer.init()
    for e in ("ambient_act1", "ambient_act2", "ambient_act3"):
        s = pygame.mixer.Sound(audio.resolve(e))
        assert s.get_length() >= 60.0, (e, s.get_length())


def test_band_picks():
    class G:
        def __init__(self, t):
            self.turn = t
    assert ambient_event_for(G(5)) == "ambient_act1"
    assert ambient_event_for(G(25)) == "ambient_act1"
    assert ambient_event_for(G(30)) == "ambient_act2"
    assert ambient_event_for(G(50)) == "ambient_act2"
    assert ambient_event_for(G(60)) == "ambient_act3"


def test_mute_returns_false():
    class S:
        mute = True
    assert audio.play("ambient_act1", S()) is False


def test_licenses_name_the_beds():
    lic = open(os.path.join(os.path.dirname(os.path.abspath(audio.__file__)),
                            "assets", "audio", "LICENSES.md"),
               encoding="utf-8").read()
    for name in ("act1_calm.flac", "act2_tense.flac", "act3_grand.flac"):
        assert name in lic, name
