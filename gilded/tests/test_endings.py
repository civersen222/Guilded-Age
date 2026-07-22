"""G17 endings tests: hard stops, the four axes, and the epilogue."""

from gilded.chassis import TURN_BUDGET, GildedGame, year_of
from gilded.endings import AXES, Epilogue, check_ending, judge

SEED = 42


def _game(**kw) -> GildedGame:
    return GildedGame(SEED, **kw)


def _first(g: GildedGame) -> str:
    return sorted(g.houses)[0]


# --- the calendar ------------------------------------------------------------

def test_the_century_runs_1900_to_2000():
    assert year_of(1) == 1900
    assert year_of(TURN_BUDGET + 1) == 2000


# --- hard stops --------------------------------------------------------------

def test_no_ending_at_the_start():
    g = _game()
    assert check_ending(g, _first(g)) is None


def test_extinction_when_the_line_dies():
    g = _game()
    h = _first(g)
    for c in g.realms[h].dynasty.all_characters.values():
        c.is_alive = False
    assert check_ending(g, h) == "extinction"


def test_recorded_fates_are_returned():
    g = _game()
    h = _first(g)
    g.fallen[h] = "revolution"
    assert check_ending(g, h) == "revolution"
    g.fallen[h] = "transformed"
    assert check_ending(g, h) == "transformed"


def test_the_century_closes_the_book():
    g = _game()
    g.turn = TURN_BUDGET + 1
    assert check_ending(g, _first(g)) == "century"


def test_game_over_freezes_further_turns():
    g = _game()
    g.game_over = "century"
    turn0 = g.turn
    g.end_turn()
    assert g.turn == turn0


def test_ai_century_sets_game_over():
    g = _game()
    g.turn = TURN_BUDGET
    events = g.end_turn()
    assert g.turn == TURN_BUDGET + 1
    assert g.game_over == "century"
    assert any("THE AGE CLOSES" in e.text for e in events)


def test_player_fall_ends_the_game():
    g = GildedGame(SEED, player_house=None)
    h = _first(g)
    g.houses[h].is_player = True
    g.fallen[h] = "revolution"
    g.end_turn()
    assert g.game_over == "revolution"


# --- judgment ----------------------------------------------------------------

def test_axes_complete_and_bounded():
    g = _game()
    ep = judge(g, _first(g))
    assert isinstance(ep, Epilogue)
    assert set(ep.axes) == set(AXES)
    assert all(0.0 <= v <= 100.0 for v in ep.axes.values())


def test_epilogue_is_four_paragraphs_and_states_who_paid():
    g = _game()
    ep = judge(g, _first(g))
    assert len(ep.text) > 200
    assert ep.text.count("\n\n") == 3
    assert "paid" in ep.text


def test_hegemon_profile():
    g = _game()
    h = _first(g)
    g.houses[h].treasury = 10 ** 6
    g.legitimacy[h] = 90.0
    g.houses[h].prestige = 50.0
    ep = judge(g, h)
    assert ep.ending_key == "Hegemon of the Age"


def test_quiet_throne_profile():
    g = _game()
    hs = sorted(g.houses)
    h, rich = hs[0], hs[1]
    g.houses[rich].treasury = 10 ** 6      # someone else tops the exchange
    g.legitimacy[h] = 95.0
    g.houses[h].prestige = 40.0
    g.tide.atrocities = 0.0
    ep = judge(g, h)
    assert ep.ending_key == "The Quiet Throne"


def test_ash_and_chairman_profiles():
    g = _game()
    h = _first(g)
    g.fallen[h] = "revolution"
    assert judge(g, h).ending_key == "A House of Ash"
    g.fallen[h] = "transformed"
    assert judge(g, h).ending_key == "People's Chairman"


def test_long_ledger_is_the_default_verdict():
    g = _game()
    h = _first(g)
    g.legitimacy[h] = 10.0
    g.tide.atrocities = 10.0
    hs = sorted(g.houses)
    g.houses[hs[1]].treasury = 10 ** 6
    ep = judge(g, h)
    assert ep.ending_key == "The Long Ledger"


def test_epilogue_names_the_age_and_rival():
    from gilded.chassis import GildedGame, TURN_BUDGET
    from gilded.endings import judge
    g = GildedGame(seed=2026)
    for _ in range(TURN_BUDGET + 1):
        g.end_turn()
        if g.game_over:
            break
    ep = judge(g, next(iter(g.houses)))
    # the coda names the final era and the bound rival
    from gilded.saga.content.eras import ERAS
    assert any(era.title in ep.text for era in ERAS[:g.director.age_idx + 1])
    assert g.director.rival in ep.text
