"""G14 papers tests: register scoping, the standing summary, press slant,
and the broadsheet's type."""

from gilded.chassis import GildedGame, TurnEvent
from gilded.papers import (MASTHEAD, SLANT_PREFIX, WRAP_WIDTH, TurnReport,
                           YEAR_ZERO, compose, format_broadsheet)
from gilded.society.court import CourtPosition

SEED = 42


def _game_after_turn() -> GildedGame:
    g = GildedGame(SEED)
    g.end_turn()
    return g


def _two_houses(g: GildedGame):
    names = sorted(g.houses)
    return names[0], names[1]


def _seat_press(g: GildedGame, h: str, intrigue: int):
    realm = g.realms[h]
    press = realm.ruler
    press.base_stats["intrigue"] = intrigue
    press.traits = []
    realm.court.positions[CourtPosition.MASTER_OF_PRESS] = press
    return press


# --- compose -----------------------------------------------------------------

def test_compose_dates_the_paper():
    g = _game_after_turn()
    h, _ = _two_houses(g)
    rep = compose(g, h)
    assert rep.turn == g.turn
    assert rep.year == YEAR_ZERO + g.turn >= 1900


def test_registers_scope_to_the_reading_house():
    g = _game_after_turn()
    mine, theirs = _two_houses(g)
    g.events = [
        TurnEvent("world news travels", "gazette", ""),
        TurnEvent("their public shame", "gazette", theirs),
        TurnEvent("my business", "ledger", mine),
        TurnEvent("their business", "ledger", theirs),
        TurnEvent("my private letter", "letters", mine),
        TurnEvent("their private letter", "letters", theirs),
    ]
    rep = compose(g, mine)
    assert "world news travels" in rep.gazette
    assert "their public shame" in rep.gazette
    assert "my business" in rep.ledger
    assert "their business" not in rep.ledger
    assert rep.letters == ["my private letter"]


def test_standing_summary_closes_the_ledger():
    g = _game_after_turn()
    h, _ = _two_houses(g)
    rep = compose(g, h)
    summary = rep.ledger[-1]
    assert summary.startswith("Standing: ")
    assert f"treasury {g.houses[h].treasury:.0f} gold" in summary
    assert f"{len(g.ents_of(h))} enterprises" in summary
    assert "strikes active" in summary


def test_summary_totals_the_dividends():
    g = _game_after_turn()
    h, _ = _two_houses(g)
    g.events = [TurnEvent("Dividends: 120 gold to the House treasury",
                          "ledger", h),
                TurnEvent("Dividends: 35 gold to the House treasury",
                          "ledger", h)]
    rep = compose(g, h)
    assert "dividends 155" in rep.ledger[-1]


# --- the press slant ---------------------------------------------------------

def test_sharp_press_softens_own_scandal():
    g = _game_after_turn()
    h, _ = _two_houses(g)
    _seat_press(g, h, 30)
    g.events = [TurnEvent(f"Scandal rocks {h}: legitimacy falls 8 to 42",
                          "gazette", h)]
    rep = compose(g, h)
    assert rep.gazette[0].startswith(SLANT_PREFIX)
    assert "scandal rocks" in rep.gazette[0]


def test_dull_press_prints_it_straight():
    g = _game_after_turn()
    h, _ = _two_houses(g)
    _seat_press(g, h, 0)
    text = f"Scandal rocks {h}: legitimacy falls 8 to 42"
    g.events = [TurnEvent(text, "gazette", h)]
    rep = compose(g, h)
    assert rep.gazette == [text]


def test_rival_scandal_is_never_softened():
    g = _game_after_turn()
    mine, theirs = _two_houses(g)
    _seat_press(g, mine, 30)
    text = f"Scandal rocks {theirs}: legitimacy falls 8 to 42"
    g.events = [TurnEvent(text, "gazette", theirs)]
    rep = compose(g, mine)
    assert rep.gazette == [text]


# --- the broadsheet ----------------------------------------------------------

def test_broadsheet_sets_the_masthead_and_sections():
    g = _game_after_turn()
    h, _ = _two_houses(g)
    rep = compose(g, h)
    sheet = format_broadsheet(rep)
    assert MASTHEAD in sheet and str(rep.year) in sheet
    for header in ("THE GAZETTE", "THE LEDGER", "LETTERS"):
        assert header in sheet


def test_broadsheet_wraps_and_fills_empty_sections():
    long_line = "a very long dispatch " * 10
    rep = TurnReport(3, 1902, [long_line.strip()], [], [])
    sheet = format_broadsheet(rep)
    assert all(len(line) <= WRAP_WIDTH for line in sheet.splitlines())
    assert "No business worth the ink." in sheet
    assert "The silver tray stands empty." in sheet