from gilded.saga.director import Director


class _Tide:
    def __init__(self, level):
        self.level = level
        self.house_atrocities = {}

    def phase(self):
        return "reformist"


class _Game:
    def __init__(self, turn, level):
        self.turn = turn
        self.events = []
        self.houses = {}
        self.fallen = {}
        self.realms = {}
        self.tide = _Tide(level)


def test_age_opens_first_era_on_turn_one():
    d = Director(seed=1)
    ev = d._tick_age(_Game(turn=1, level=0.0))
    assert d.age_idx == 0
    assert any("Gilded Peace" in e.text for e in ev)


def test_age_advances_by_tide_or_turn_once_each():
    d = Director(seed=1)
    d._tick_age(_Game(turn=1, level=0.0))       # era 0
    # jump the tide past the Red Decade threshold; skips straight to idx 2
    ev = d._tick_age(_Game(turn=20, level=70.0))
    assert d.age_idx == 2
    assert any("Red Decade" in e.text for e in ev)
    # no re-fire at the same level
    ev2 = d._tick_age(_Game(turn=21, level=70.0))
    assert ev2 == []


def _real_game(seed=2026):
    from gilded.chassis import GildedGame
    return GildedGame(seed=seed)


def test_rival_is_bound_deterministically():
    a = _real_game()
    b = _real_game()
    ra = a.director._pick_rival(a)
    rb = b.director._pick_rival(b)
    assert ra is not None and ra == rb
    assert ra in a.houses


def test_rival_arc_opens_and_tracks_real_deeds():
    g = _real_game()
    d = g.director
    d._tick_rival(g)                       # binds rival, opens first arc beat
    assert d.rival is not None
    # a rival war fact should satisfy the first beat's completion predicate
    from gilded.saga.facts import WorldFact
    d.facts.add(WorldFact(g.turn, "house", d.rival, "went_to_war", object="X"))
    ev = d._advance(g)
    assert len(ev) == 1
    assert d.rival in ev[0].text
    assert d.beats["rival_first_blood"].state == "complete"


def test_chronicle_promotes_and_resolves_a_scandal_thread():
    from gilded.chassis import GildedGame
    from gilded.saga.facts import WorldFact
    g = GildedGame(seed=5)
    d = g.director
    h = sorted(g.houses)[0]
    for t in (1, 2):
        d.facts.add(WorldFact(t, "house", h, "committed_atrocity"))
    d._tick_chronicle(g)
    bid = f"thread_scandal_{h}"
    assert bid in d.beats and d.beats[bid].state == "active"
    # resolution
    d.facts.add(WorldFact(g.turn, "house", h, "suffered_revolution"))
    ev = d._advance(g)
    assert d.beats[bid].state == "complete"
