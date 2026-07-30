from tools.audio_foundry import config


def test_asset_dirs_under_repo():
    assert config.VOICE_DIR.name == "voice"
    assert config.SFX_DIR.parent == config.ASSET_ROOT


def test_engine_config_defaults():
    ec = config.EngineConfig()
    assert ec.openmoss_cli
    assert ec.thinksound_cli
