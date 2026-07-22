from gilded.saga.facts import WorldFact, FactStore, facts_from_turn


def test_store_add_and_exists():
    s = FactStore()
    s.add(WorldFact(3, "house", "Karsgate", "went_to_war", object="Vantrell"))
    assert s.exists("went_to_war")
    assert s.exists("went_to_war", subject=("house", "Karsgate"))
    assert s.exists("went_to_war", subject=("house", "Karsgate"), object="Vantrell")
    assert not s.exists("went_to_war", subject=("house", "Vantrell"))
    assert not s.exists("made_peace")


def test_store_count_and_since_turn():
    s = FactStore()
    s.add(WorldFact(1, "house", "K", "committed_atrocity", magnitude=2.0))
    s.add(WorldFact(4, "house", "K", "committed_atrocity", magnitude=1.0))
    s.add(WorldFact(4, "house", "V", "committed_atrocity"))
    assert s.count("committed_atrocity") == 3
    assert s.count("committed_atrocity", subject=("house", "K")) == 2
    assert s.count("committed_atrocity", subject=("house", "K"), since_turn=2) == 1


class _Stub:
    """Minimal duck-typed game for facts_from_turn."""
    def __init__(self):
        self.turn = 5
        self.events = []
        self.houses = {}          # name -> obj with .at_war_with (set)
        self.fallen = {}
        self.realms = {}          # name -> obj with .ruler (id via .id)

        class _Tide:
            level = 40.0
            house_atrocities = {}

            def phase(self):
                return "socialist"
        self.tide = _Tide()


def _house(war=None):
    class H:
        pass
    h = H()
    h.at_war_with = set(war or [])
    return h


def test_facts_from_turn_detects_new_war():
    g = _Stub()
    g.houses = {"K": _house({"V"}), "V": _house()}
    prev = {"war": {"K": set(), "V": set()}, "atrocity": {}, "fallen": {},
            "ruler": {}, "phase": "reformist"}
    facts, snap = facts_from_turn(g, prev)
    assert any(f.predicate == "went_to_war" and f.subject_id == "K"
               and f.object == "V" for f in facts)
    assert snap["war"]["K"] == {"V"}


def test_facts_from_turn_detects_tide_phase_change():
    g = _Stub()
    g.houses = {"K": _house()}
    prev = {"war": {"K": set()}, "atrocity": {}, "fallen": {},
            "ruler": {}, "phase": "reformist"}
    facts, snap = facts_from_turn(g, prev)
    assert any(f.predicate == "reached_tide_phase" and f.object == "socialist"
               for f in facts)
    # idempotent: same phase next call yields no new phase fact
    facts2, _ = facts_from_turn(g, snap)
    assert not any(f.predicate == "reached_tide_phase" for f in facts2)