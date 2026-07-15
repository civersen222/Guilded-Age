from tools.audio_foundry.adapters import openmoss, thinksound
from tools.audio_foundry.validate_audio import validate_file


def test_openmoss_dry_run(tmp_path):
    p = openmoss.generate("hail the king", tmp_path / "v.wav", dry_run=True)
    ok, msg = validate_file(p)
    assert ok, msg


def test_thinksound_dry_run(tmp_path):
    p = thinksound.generate("sword clash", tmp_path / "s.wav", dry_run=True)
    ok, _ = validate_file(p)
    assert ok
