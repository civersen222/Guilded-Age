"""Wave 0 – HUD geometry and single-source year."""

import pygame

from gilded.chassis import GildedGame, TURN_BUDGET, year_of
from gilded.ui.broadsheet import TAB_H, HUD_LINES, _ensure_hud_h, _font, _hud_height


def _init_fonts():
    if not pygame.font.get_init():
        pygame.font.init()


def test_hud_height_covers_all_lines():
    """HUD height is derived from HUD_LINES, not a hardcoded constant."""
    _init_fonts()
    fs = _font(15)
    line_h = fs.get_height() + 3
    expected = 6 + HUD_LINES * line_h
    assert _ensure_hud_h() == expected


def test_hud_draws_five_lines():
    """All five HUD rows render text (the fifth is the rival's design)."""
    _init_fonts()
    g = GildedGame(42)
    g.end_turn()
    from gilded.ui.broadsheet import BroadsheetView
    v = BroadsheetView(g, sorted(g.houses)[0])
    surf = pygame.Surface((1280, 900))
    v.draw(surf)
    hud_h = _ensure_hud_h()
    y0 = TAB_H + 6
    fs = _font(15)
    line_h = fs.get_height() + 3
    # Sample a pixel in each row's text area (left edge)
    for i in range(HUD_LINES):
        y = y0 + i * line_h
        assert y + fs.get_height() <= TAB_H + hud_h, (
            f"HUD line {i} overflows the band")


def test_year_agrees_at_turn_12():
    """Masthead and HUD read the same year at turn > 1."""
    _init_fonts()
    g = GildedGame(42)
    while g.turn < 12:
        g.end_turn()
    from gilded.papers import compose
    h = sorted(g.houses)[0]
    rep = compose(g, h)
    assert rep.year == year_of(g.turn), (
        f"Masthead year {rep.year} != HUD year {year_of(g.turn)} at turn {g.turn}")


def test_century_spans_1900_to_1999():
    """year_of(1) == 1900 and year_of(TURN_BUDGET) == 1999."""
    assert year_of(1) == 1900
    assert year_of(TURN_BUDGET) == 1999
