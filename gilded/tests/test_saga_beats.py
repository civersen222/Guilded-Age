from gilded.saga.beats import Predicate, Beat, eval_predicate
from gilded.saga.facts import FactStore, WorldFact


class _G:
    turn = 10

    class tide:
        level = 55.0


def test_fact_exists_with_self_binding():
    s = FactStore()
    s.add(WorldFact(3, "house", "Karsgate", "went_to_war", object="V"))
    p = Predicate(kind="fact_exists", predicate="went_to_war",
                  subject_kind="house", subject_id="@self")
    assert eval_predicate(p, s, _G(), cast={"self": "Karsgate"})
    assert not eval_predicate(p, s, _G(), cast={"self": "Vantrell"})


def test_min_count():
    s = FactStore()
    for t in (2, 5, 8):
        s.add(WorldFact(t, "house", "K", "committed_atrocity"))
    p = Predicate(kind="fact_exists", predicate="committed_atrocity",
                  subject_kind="house", subject_id="K", min_count=3)
    assert eval_predicate(p, s, _G())
    p.min_count = 4
    assert not eval_predicate(p, s, _G())


def test_turn_and_tide_and_composites():
    s = FactStore()
    assert eval_predicate(Predicate(kind="turn_reached", turn=10), s, _G())
    assert not eval_predicate(Predicate(kind="turn_reached", turn=11), s, _G())
    assert eval_predicate(Predicate(kind="tide_reached", level=55.0), s, _G())
    both = Predicate(kind="all", parts=[
        Predicate(kind="turn_reached", turn=10),
        Predicate(kind="tide_reached", level=50.0)])
    assert eval_predicate(both, s, _G())
    either = Predicate(kind="any", parts=[
        Predicate(kind="turn_reached", turn=99),
        Predicate(kind="tide_reached", level=50.0)])
    assert eval_predicate(either, s, _G())


def test_beat_defaults():
    b = Beat(bid="x", source="age", title="T", load_bearing=False)
    assert b.state == "pending" and b.cast == {} and b.next_bids == []