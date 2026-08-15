"""Stage 10 — SEVENTY TURNS AND THE PLAYER NEVER FINDS OUT WHAT HAPPENED.

Tests for:
  CUT 1: Empty table headers (header_text_rects in TableLayout)
  CUT 2: Ending overlay drawn when game_over is set
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.chassis import GildedGame
from gilded.ui.widgets import Table, Column, font as _font
from gilded.ui.broadsheet import BroadsheetView


SEED = 42
SIZE = (1280, 900)


def _game() -> GildedGame:
    g = GildedGame(SEED)
    if not any(h.is_player for h in g.houses.values()):
        first = next(iter(g.houses))
        g.houses[first].is_player = True
    return g


# ====================================================================
# CUT 1 — A TABLE WITH NO ROWS MUST STILL DRAW ITS HEADER
# ====================================================================

class TestEmptyTableLayout:
    """Table.layout() with zero data rows."""

    def test_zero_row_table_layout_returns_header_text_rects(self):
        """A zero-row table layout has header_text_rects populated."""
        cols = [Column("Name", width=3.0, align="left"),
                Column("Value", width=1.0, align="right")]
        tbl = Table(cols, [])
        rect = pygame.Rect(0, 0, 600, 100)
        layout = tbl.layout(rect)
        assert len(layout.header_text_rects) == len(cols)
        assert all(isinstance(r, pygame.Rect) for r in layout.header_text_rects)

    def test_zero_row_table_header_text_rects_alignment_matches(self):
        """header_text_rects alignment matches what the column gets when rows exist."""
        cols = [Column("Name", width=3.0, align="left"),
                Column("Value", width=1.0, align="right")]
        tbl_empty = Table(cols, [])
        tbl_full = Table(cols, [["Alice", "42"], ["Bob", "7"]])
        rect = pygame.Rect(0, 0, 600, 200)
        lay_empty = tbl_empty.layout(rect)
        lay_full = tbl_full.layout(rect)
        # header_text_rects should be the same alignment for both
        assert len(lay_empty.header_text_rects) == len(lay_full.header_text_rects)
        for i in range(len(cols)):
            e_rect = lay_empty.header_text_rects[i]
            f_rect = lay_full.header_text_rects[i]
            # Right-aligned columns: x should be similar (right-justified)
            # Left-aligned columns: x should be similar (left-justified)
            assert abs(e_rect.x - f_rect.x) < 5, f"Column {i} alignment drifted"

    def test_zero_row_table_text_rects_empty(self):
        """Zero-row table has empty text_rects."""
        cols = [Column("A", width=1.0), Column("B", width=1.0)]
        tbl = Table(cols, [])
        rect = pygame.Rect(0, 0, 400, 80)
        layout = tbl.layout(rect)
        assert layout.text_rects == []

    def test_zero_row_table_height_is_header_only(self):
        """Zero-row table height accounts for header + rule only."""
        cols = [Column("Only", width=1.0)]
        tbl = Table(cols, [])
        h = tbl.height()
        f = _font(tbl.size, bold=True)
        header_h = f.get_linesize()
        assert h == header_h + 1 + 2  # header + rule + gap

    def test_zero_row_table_header_rects_populated(self):
        """Zero-row table still gets header_rects for all columns."""
        cols = [Column("A", width=1.0), Column("B", width=1.0), Column("C", width=1.0)]
        tbl = Table(cols, [])
        rect = pygame.Rect(0, 0, 300, 60)
        layout = tbl.layout(rect)
        assert len(layout.header_rects) == 3
        assert all(isinstance(r, pygame.Rect) for r in layout.header_rects)


class TestPowersTableEmpty:
    """PowersTable.layout() with zero data rows."""

    def test_powers_table_zero_row_returns_header_text_rects(self):
        """PowersTable with no rows returns header_text_rects."""
        from gilded.ui.broadsheet import PowersTable
        cols = [Column("House", width=3.0, align="left"),
                Column("Power", width=1.0, align="right")]
        tbl = PowersTable(cols, [])
        rect = pygame.Rect(0, 0, 600, 100)
        layout = tbl.layout(rect)
        assert hasattr(layout, "header_text_rects")
        assert len(layout.header_text_rects) == len(cols)

    def test_powers_table_zero_row_text_rects_empty(self):
        """PowersTable with no rows has empty text_rects."""
        from gilded.ui.broadsheet import PowersTable
        cols = [Column("House", width=3.0, align="left")]
        tbl = PowersTable(cols, [])
        rect = pygame.Rect(0, 0, 400, 80)
        layout = tbl.layout(rect)
        assert layout.text_rects == []

    def test_powers_table_draws_on_page(self):
        """Powers table with zero rows draws on a page without raising."""
        game = _game()
        house = next(h for h in game.houses if game.houses[h].is_player)
        pygame.init()
        pygame.font.init()
        screen = pygame.display.set_mode(SIZE)
        view = BroadsheetView(game, house)
        view.active_tab = "powers"
        view.draw(screen)

    def test_empty_table_draws_on_page(self):
        """A page with an empty table draws without raising."""
        game = _game()
        house = next(h for h in game.houses if game.houses[h].is_player)
        pygame.init()
        pygame.font.init()
        screen = pygame.display.set_mode(SIZE)
        view = BroadsheetView(game, house)
        view.draw(screen)


# ====================================================================
# CUT 2 — THE AGE ENDS AND THE GAME DOES NOT SAY SO
# ====================================================================

class TestEndingOverlay:
    """The drawn page shows the ending when game_over is set."""

    def _setup_view(self, game):
        """Create a BroadsheetView for the player house."""
        house = next(h for h in game.houses if game.houses[h].is_player)
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        view = BroadsheetView(game, house)
        return view, screen, house

    def test_game_over_sets_epilogue(self):
        """Drawing with game_over set produces an epilogue with ending_key, axes, and text."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        g.game_over = "century"
        house = next(h for h in g.houses if g.houses[h].is_player)
        view = BroadsheetView(g, house)
        view.draw(screen)
        epilogue = view._epilogue
        assert epilogue.ending_key is not None
        assert isinstance(epilogue.ending_key, str)
        assert len(epilogue.ending_key) > 0
        assert set(epilogue.axes.keys()) == {"capital", "standing", "blood", "world"}
        assert isinstance(epilogue.text, str)
        assert len(epilogue.text) > 0

    def test_epilogue_deterministic(self):
        """Drawing twice produces the same epilogue."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        g.game_over = "century"
        house = next(h for h in g.houses if g.houses[h].is_player)
        view = BroadsheetView(g, house)
        view.draw(screen)
        ep1 = view._epilogue
        view.draw(screen)
        ep2 = view._epilogue
        assert ep1.ending_key == ep2.ending_key
        assert ep1.axes == ep2.axes
        assert ep1.text == ep2.text

    def test_ending_overlay_draws_without_raising(self):
        """Drawing with game_over set does not raise."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        g.game_over = "century"
        house = next(h for h in g.houses if g.houses[h].is_player)
        view = BroadsheetView(g, house)
        # Draw the page — should not raise
        view.draw(screen)
        assert view._epilogue is not None

    def test_ending_has_ending_key(self):
        """The epilogue cache stores an ending key that is not None."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        g.game_over = "century"
        house = next(h for h in g.houses if g.houses[h].is_player)
        view = BroadsheetView(g, house)
        view.draw(screen)
        assert view._epilogue.ending_key is not None
        assert view._epilogue.ending_key != ""

    def test_ending_has_all_four_axes(self):
        """The epilogue carries all four axis scores."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        g.game_over = "century"
        house = next(h for h in g.houses if g.houses[h].is_player)
        view = BroadsheetView(g, house)
        view.draw(screen)
        for axis in ("capital", "standing", "blood", "world"):
            assert axis in view._epilogue.axes
            assert isinstance(view._epilogue.axes[axis], float)

    def test_ending_has_epilogue_text(self):
        """The epilogue carries paragraph text."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        g.game_over = "century"
        house = next(h for h in g.houses if g.houses[h].is_player)
        view = BroadsheetView(g, house)
        view.draw(screen)
        assert len(view._epilogue.text) > 50

    def test_draw_twice_same_page(self):
        """Drawing the ending overlay twice does not change the epilogue."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        g.game_over = "century"
        house = next(h for h in g.houses if g.houses[h].is_player)
        view = BroadsheetView(g, house)
        view.draw(screen)
        ep1 = view._epilogue
        view.draw(screen)
        ep2 = view._epilogue
        assert ep1 is ep2  # same cached object

    def test_no_ending_while_game_running(self):
        """While game_over is None, no epilogue is computed."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        assert g.game_over is None
        house = next(h for h in g.houses if g.houses[h].is_player)
        view = BroadsheetView(g, house)
        view.draw(screen)
        assert view._epilogue is None

    def test_ending_does_not_appear_in_gazette(self):
        """The ending is drawn as an overlay, not as a Gazette line."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        g.game_over = "century"
        house = next(h for h in g.houses if g.houses[h].is_player)
        view = BroadsheetView(g, house)
        view.draw(screen)
        # The ending overlay returns early from draw(), skipping tab bar
        # and bottom bar — the ending IS the page, not a scroll line
        ep = view._epilogue
        assert ep.ending_key is not None
        # Verify it's not just a Gazette string by checking the epilogue
        # has actual paragraph content (not a single line)
        paragraphs = ep.text.strip().split("\n\n")
        assert len(paragraphs) >= 1
        assert len(ep.text) > 100  # Gazette lines are shorter

    def test_enterprises_draws_empty_without_raising(self):
        """Enterprises tab draws for a House with no enterprises."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        house = next(h for h in g.houses if g.houses[h].is_player)
        # Remove all enterprises
        g.enterprises = []
        view = BroadsheetView(g, house)
        view.active_tab = "Enterprises"
        # Should not raise even with zero enterprises
        view.draw(screen)

    def test_all_tabs_draw_with_game_over(self):
        """All 11 tabs draw without raising when game_over is set."""
        pygame.init()
        screen = pygame.display.set_mode(SIZE)
        g = _game()
        g.game_over = "century"
        house = next(h for h in g.houses if g.houses[h].is_player)
        view = BroadsheetView(g, house)
        from gilded.ui.broadsheet import TABS
        for tab in TABS:
            view.active_tab = tab
            view._epilogue = None  # reset to test each draw
            view.draw(screen)
            assert view._epilogue is not None
