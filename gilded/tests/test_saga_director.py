from gilded.chassis import TurnEvent
from gilded.saga.director import Director
from gilded.saga.beats import Beat, Predicate


class _Tide:
    level = 0.0
    house_atrocities = {}

    def phase(self):
        return "reformist"


class _Game:
    def __init__(self):
        self.turn = 4
        self.events = []
        self.houses = {}
        self.fallen = {}
        self.realms = {}
        self.tide = _Tide()


def test_observe_is_deterministic_and_advances_a_beat():
    g = _Game()
    d = Director(seed=1)
    b = Beat(bid="b1", source="chronicle", title="A Test Thread",
             load_bearing=True,
             completion=Predicate(kind="turn_reached", turn=4),
             payoff="The thread pays off.")
    d.register(b, g)
    assert "b1" in d.active
    events = d.observe(g)
    assert any(isinstance(e, TurnEvent) and e.text == "The thread pays off."
               for e in events)
    assert d.beats["b1"].state == "complete"
    assert "b1" not in d.active


def test_open_successor_on_completion():
    g = _Game()
    d = Director(seed=1)
    first = Beat(bid="a", source="rival", title="First", load_bearing=True,
                 completion=Predicate(kind="turn_reached", turn=4),
                 next_bids=["b"])
    second = Beat(bid="b", source="rival", title="Second", load_bearing=True,
                  completion=Predicate(kind="turn_reached", turn=99))
    d.register(first, g)
    d.register(second, g)          # has a predecessor -> stays pending
    assert d.beats["b"].state == "pending"
    d.observe(g)
    assert d.beats["b"].state == "active"