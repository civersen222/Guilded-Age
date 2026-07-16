from tools.audio_foundry.runtime import voice_event, voice_chronicle
from tools.audio_foundry.lemonade import LemonadeHost

DOWN = LemonadeHost(base_url="http://127.0.0.1:1", timeout=0.05)


def test_generate_returns_fresh_clip(tmp_path):
    p = voice_event({"id": "e1", "title": "War", "desc": "It begins"},
                    tmp_path, generate=True, dry_run=True, host=DOWN)
    assert p is not None and p.exists()


def test_no_generate_uses_fallback(tmp_path):
    fb = tmp_path / "prebaked.wav"
    fb.write_bytes(b"RIFFfake")
    p = voice_event({"id": "e2"}, tmp_path, generate=False, fallback=fb)
    assert p == fb


def test_no_generate_no_fallback_returns_none(tmp_path):
    p = voice_event({"id": "e3"}, tmp_path, generate=False)
    assert p is None


def test_chronicle_generates(tmp_path):
    p = voice_chronicle("Rome", "The empire endures", tmp_path,
                        generate=True, dry_run=True, host=DOWN)
    assert p is not None and p.exists()


def test_chronicle_falls_back_when_not_generating(tmp_path):
    fb = tmp_path / "chr.wav"
    fb.write_bytes(b"x")
    p = voice_chronicle("Rome", "text", tmp_path, generate=False, fallback=fb)
    assert p == fb