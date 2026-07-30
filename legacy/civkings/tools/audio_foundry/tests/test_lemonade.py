from tools.audio_foundry.lemonade import LemonadeHost


def test_unreachable_host_is_unavailable():
    host = LemonadeHost(base_url="http://127.0.0.1:1", timeout=0.2)
    assert host.available() is False


def test_generate_text_returns_none_when_down():
    host = LemonadeHost(base_url="http://127.0.0.1:1", timeout=0.2)
    assert host.generate_text("hello") is None


def test_never_raises_on_bad_url():
    host = LemonadeHost(base_url="not-a-url", timeout=0.2)
    assert host.available() is False
    assert host.generate_text("x") is None
