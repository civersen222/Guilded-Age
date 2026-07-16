from tools.audio_foundry.flavor import author_line
from tools.audio_foundry.lemonade import LemonadeHost


def test_returns_none_when_host_down():
    down = LemonadeHost(base_url="http://127.0.0.1:1", timeout=0.2)
    assert author_line("A plague spreads", host=down) is None


def test_returns_none_on_empty_input():
    down = LemonadeHost(base_url="http://127.0.0.1:1", timeout=0.2)
    assert author_line("   ", host=down) is None


def test_uses_host_result_first_line():
    class FakeHost:
        def generate_text(self, prompt, **kw):
            return "  The banners fell as winter came.\nextra line\n"

    line = author_line("Defeat in the north", host=FakeHost())
    assert line == "The banners fell as winter came."
