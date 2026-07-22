from gilded.chassis import GildedGame
from gilded.papers import compose
from gilded.saga.narrator import NarratorTemplated


def test_templated_narrator_is_identity():
    g = GildedGame(seed=42)
    g.end_turn()
    h = sorted(g.houses)[0]
    rep = compose(g, h)
    out = NarratorTemplated().render(rep, g.director, g)
    assert out.gazette == rep.gazette
    assert out.ledger == rep.ledger
    assert out.letters == rep.letters
    assert out.turn == rep.turn and out.year == rep.year


def test_llm_narrator_falls_back_on_unreachable_model(monkeypatch):
    import gilded.saga.narrator as nar
    g = GildedGame(seed=42)
    g.end_turn()
    rep = compose(g, sorted(g.houses)[0])

    def boom(*a, **k):
        raise OSError("no model")
    monkeypatch.setattr(nar, "_post_chat", boom)
    n = nar.NarratorLLM(check=False)            # skip constructor probe
    out = n.render(rep, g.director, g)
    assert out.gazette == rep.gazette           # unchanged on failure


def test_select_narrator_honours_disable(monkeypatch):
    import gilded.saga.narrator as nar
    monkeypatch.setenv("GILDED_NARRATE", "0")
    assert isinstance(nar.select_narrator(), nar.NarratorTemplated)
