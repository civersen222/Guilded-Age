"""Wave 0b – HUD geometry measured by reading drawn pixels, single-source year."""

import pygame

from gilded.chassis import GildedGame, TURN_BUDGET, year_of
from gilded.ui.broadsheet import TAB_H, HUD_LINES, _font, _hud_height, PAPER_BG, HUD_INK


def _init_fonts():
    if not pygame.font.get_init():
        pygame.font.init()


def test_hud_height_covers_all_lines():
    """No HUD ink lies below the derived band height.

    Measure the drawing: fill a Surface with PAPER_BG, call _draw_hud only,
    then bounding-box every non-PAPER_BG pixel and assert its bottom <=
    TAB_H + _hud_height().
    """
    _init_fonts()
    pygame.init()
    g = GildedGame(42)
    g.end_turn()
    from gilded.ui.broadsheet import BroadsheetView
    v = BroadsheetView(g, sorted(g.houses)[0])
    surf = pygame.Surface((1280, 900))
    surf.fill(PAPER_BG)
    v._draw_hud(surf)
    hud_h = _hud_height()
    band_bottom = TAB_H + hud_h
    bottom = 0
    for y in range(TAB_H, surf.get_height()):
        for x in range(surf.get_width()):
            if surf.get_at((x, y)) != PAPER_BG:
                bottom = max(bottom, y + 1)
                break
    assert bottom <= band_bottom, (
        f"HUD draws {bottom - band_bottom}px below its band (band bottom {band_bottom}, ink bottom {bottom})")


def test_hud_draws_five_lines():
    """All five HUD rows render text (the fifth is the rival's design).

    Count rows of rendered ink: walk scanlines in the band, mark each
    containing HUD_INK, count runs of marked scanlines, assert 5.
    """
    _init_fonts()
    pygame.init()
    g = GildedGame(42)
    g.end_turn()
    from gilded.ui.broadsheet import BroadsheetView
    v = BroadsheetView(g, sorted(g.houses)[0])
    surf = pygame.Surface((1280, 900))
    surf.fill(PAPER_BG)
    v._draw_hud(surf)
    hud_h = _hud_height()
    band_top = TAB_H
    band_bottom = TAB_H + hud_h
    # Walk scanlines, mark rows with HUD_INK ink
    ink_rows = []
    for y in range(band_top, band_bottom):
        row_has_ink = False
        for x in range(16, surf.get_width() - 16):
            pixel = surf.get_at((x, y))
            if pixel == HUD_INK:
                row_has_ink = True
                break
        ink_rows.append(row_has_ink)
    # Count runs of consecutive ink rows
    runs = 0
    in_run = False
    for has_ink in ink_rows:
        if has_ink and not in_run:
            runs += 1
            in_run = True
        elif not has_ink:
            in_run = False
    assert runs == 5, f"Expected 5 runs of HUD ink, found {runs}"


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
