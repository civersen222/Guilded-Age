from tools.audio_foundry.integration import AudioService, AudioRuntimeSettings


def test_default_flag_is_off():
    assert AudioRuntimeSettings().audio_runtime_enabled is False


def test_flag_off_uses_prebaked_only(tmp_path):
    fb = tmp_path / "baked.wav"
    fb.write_bytes(b"RIFFxxxx")
    svc = AudioService(AudioRuntimeSettings(audio_runtime_enabled=False,
                                            cache_dir=tmp_path / "c"))
    out = svc.narrate_event({"id": "e1", "title": "War"}, fallback=fb)
    assert out == fb                     # pure Mode-A
    assert not (tmp_path / "c").exists()  # no live generation happened


def test_flag_off_no_fallback_returns_none(tmp_path):
    svc = AudioService(AudioRuntimeSettings(audio_runtime_enabled=False,
                                            cache_dir=tmp_path / "c"))
    assert svc.narrate_event({"id": "e2"}) is None


def test_flag_on_generates(tmp_path):
    svc = AudioService(AudioRuntimeSettings(audio_runtime_enabled=True,
                                            cache_dir=tmp_path / "c"))
    out = svc.narrate_event({"id": "e3", "title": "Peace"}, dry_run=True)
    assert out is not None and out.exists()
    assert out.parent == tmp_path / "c"


def test_chronicle_flag_off_uses_fallback(tmp_path):
    fb = tmp_path / "chr.wav"
    fb.write_bytes(b"x")
    svc = AudioService(AudioRuntimeSettings(audio_runtime_enabled=False,
                                            cache_dir=tmp_path / "c"))
    assert svc.narrate_chronicle("Rome", "text", fallback=fb) == fb
