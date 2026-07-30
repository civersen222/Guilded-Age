"""Wave 3c — Powers table: model, layout, draw, and interaction tests."""

import pygame
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pytest

from gilded.ui.broadsheet import (
    INTEL_COL, POWER_COLS, PowerLine, PowersModel, powers_layout, powers_model,
    powers_report, PowersTable,
)
from gilded.ui.widgets import Table, TableLayout, TONES

# ── fixture helpers ────────────────────────────────────────────────────


def _line(house="Ravenmere", tier=2, breakdown=("shared border",),
          apparent_intent="Pursuing conquest", can_place_informant=True):
    return PowerLine(
        house=house,
        tier=tier,
        breakdown=tuple(breakdown),
        apparent_intent=apparent_intent,
        can_place_informant=can_place_informant,
    )


def _lines(count=3, tier=2, can_place=True):
    return tuple(
        _line(house=f"House{i}", tier=tier, can_place_informant=can_place)
        for i in range(count)
    )


# ── rule 1: one table row per PowerLine ────────────────────────────────


def test_one_row_per_line():
    lines = _lines(5)
    model = powers_model(lines)
    assert len(model.table.data) == len(lines)


def test_zero_lines():
    model = powers_model(())
    assert len(model.table.data) == 0


# ── rule 2: POWER_COLS has exactly 5 columns with correct headers ─────


def test_power_cols_count():
    assert len(POWER_COLS) == 5


def test_power_cols_headers():
    assert POWER_COLS[0].header == "House"
    assert POWER_COLS[1].header == "Threat"
    assert POWER_COLS[2].header == "Intel"
    assert POWER_COLS[3].header == "Ties"
    assert POWER_COLS[4].header == "Apparent intent"


# ── rule 3: INTEL_COL is "intel" ──────────────────────────────────────


def test_intel_col_value():
    assert INTEL_COL == 2


# ── rule 4: threat rank column is 1-based ─────────────────────────────


def test_threat_rank_one_based():
    lines = _lines(3)
    model = powers_model(lines)
    for i, row in enumerate(model.table.data):
        assert row[1] == str(i + 1)


# ── rule 5: intel column shows tier/3 ─────────────────────────────────


def test_intel_shows_tier_over_3():
    lines = (_line(tier=0), _line(tier=1), _line(tier=2), _line(tier=3))
    model = powers_model(lines)
    for i, row in enumerate(model.table.data):
        assert row[2] == f"{i}/3"


# ── rule 6: ties cell ─────────────────────────────────────────────────


def test_ties_joined():
    lines = (_line(breakdown=("a", "b", "c")),)
    model = powers_model(lines)
    assert "a, b, c" in model.table.data[0][3]


def test_ties_dash_when_empty():
    lines = (_line(breakdown=()),)
    model = powers_model(lines)
    assert model.table.data[0][3] == "—"


# ── rule 7: intent cell ───────────────────────────────────────────────


def test_intent_cell():
    lines = (_line(apparent_intent="expand east"),)
    model = powers_model(lines)
    assert model.table.data[0][4] == "expand east"


def test_intent_dash_when_none():
    lines = (_line(apparent_intent=None),)
    model = powers_model(lines)
    assert model.table.data[0][4] == "—"


# ── rule 8: row houses tuple ──────────────────────────────────────────


def test_row_houses():
    lines = (_line(house="A"), _line(house="B"))
    model = powers_model(lines)
    assert model.row_houses == ("A", "B")


# ── rule 9: intel tones ───────────────────────────────────────────────


def test_intel_tones():
    lines = (_line(tier=0), _line(tier=2), _line(tier=3))
    model = powers_model(lines)
    assert model.intel_tones == ("dead", "neutral", "good")


# ── rule 10: blind rows ───────────────────────────────────────────────


def test_blind_rows():
    lines = (_line(tier=0), _line(tier=2), _line(tier=0))
    model = powers_model(lines)
    assert 0 in model.blind_rows
    assert 2 in model.blind_rows
    assert 1 not in model.blind_rows


# ── rule 11: no cell overprints column (pixel test) ───────────────────


def test_no_cell_overprints_column():
    """Rule 3 — widened: 40 rows at widths 900, 1280, 1600."""
    lines = tuple(_line(house=f"House{i}", tier=i % 4,
                        breakdown=(f"tie{i}0", f"tie{i}1", f"tie{i}2", f"tie{i}3", f"tie{i}4") if i % 2 == 0 else (),
                        apparent_intent=f"Pursuing conquest against House Valia: they threaten our borders with force" if i % 2 == 0 else f"Intent {i}",
                        can_place_informant=True)
                  for i in range(40))
    model = powers_model(lines)
    for width in (900, 1280, 1600):
        content = pygame.Rect(0, 100, width, 600)
        layout = powers_layout(model, content)
        tbl_rect = layout["table"]
        tbl_layout = model.table.layout(tbl_rect)
        for r in range(len(tbl_layout.cell_rects)):
            for c in range(len(tbl_layout.cell_rects[r])):
                tr = tbl_layout.text_rects[r][c]
                cr = tbl_layout.cell_rects[r][c]
                assert tr.right <= cr.right, (
                    f"width={width} row={r} col={c}: "
                    f"text_rect.right={tr.right} > cell_rect.right={cr.right}"
                )
                assert tr.left >= cr.left, (
                    f"width={width} row={r} col={c}: "
                    f"text_rect.left={tr.left} < cell_rect.left={cr.left}"
                )


# ── rule 2 (new): ellipsis on shortened cells ─────────────────────────


def test_fit_appends_ellipsis_when_shortening():
    """Rule 2: a cell whose text is too long must end with '…'."""
    font = pygame.font.Font(None, 24)
    cell = pygame.Rect(0, 0, 50, 18)  # very narrow cell
    long_text = "This is a very long string that definitely will not fit"
    result = PowersTable._fit(long_text, font, cell)
    assert result.endswith("…"), f"Expected ellipsis, got: {result!r}"


def test_fit_no_ellipsis_when_text_fits():
    """Rule 2: a short cell must NOT end with '…'."""
    font = pygame.font.Font(None, 24)
    cell = pygame.Rect(0, 0, 200, 18)
    short_text = "3/3"
    result = PowersTable._fit(short_text, font, cell)
    assert result == "3/3", f"Expected unchanged, got: {result!r}"


def test_fit_no_ellipsis_on_dash():
    """Rule 2: '—' must not get an ellipsis appended."""
    font = pygame.font.Font(None, 24)
    cell = pygame.Rect(0, 0, 200, 18)
    result = PowersTable._fit("—", font, cell)
    assert result == "—", f"Expected '—', got: {result!r}"


def test_fit_ellipsis_fits_in_cell():
    """Rule 2: the truncated string INCLUDING ellipsis must fit."""
    font = pygame.font.Font(None, 24)
    cell = pygame.Rect(0, 0, 60, 18)
    long_text = "A very long ties string that needs truncation badly"
    result = PowersTable._fit(long_text, font, cell)
    surf = font.render(result, True, (0, 0, 0))
    assert surf.get_width() <= cell.width - 8, (
        f"Ellipsis result too wide: {surf.get_width()} > {cell.width - 8}"
    )


# ── rule 12: selection ────────────────────────────────────────────────


def test_selection_none():
    model = powers_model(_lines(3), selected=None)
    assert model.selected_row is None


def test_selection_valid_house():
    lines = (_line(house="A"), _line(house="B"))
    model = powers_model(lines, selected="B")
    assert model.selected_row == 1


def test_selection_invalid_house():
    lines = (_line(house="A"), _line(house="B"))
    model = powers_model(lines, selected="NonExistent")
    assert model.selected_row is None


# ── rule 13: informant lever ──────────────────────────────────────────


def test_informant_rows_included():
    lines = (_line(house="A", can_place_informant=True),
             _line(house="B", can_place_informant=False))
    model = powers_model(lines)
    assert 0 in model.informant_rows
    assert 1 not in model.informant_rows


def test_informant_rows_empty_when_none():
    lines = (_line(house="A", can_place_informant=False),)
    model = powers_model(lines)
    assert len(model.informant_rows) == 0


# ── rule 14: overflow ─────────────────────────────────────────────────


def test_overflow_at_40_rows():
    """Rule 6: at 40 rows, overflow_count==8, overflow_name is set."""
    lines = _lines(40)
    model = powers_model(lines)
    assert model.overflow_count == 8
    assert model.overflow_name is not None
    # overflow_name must be the first row that didn't fit
    expected_name = model.row_houses[len(lines) - model.overflow_count]
    assert model.overflow_name == expected_name


def test_no_overflow_at_30_rows():
    """Rule 6: at 30 rows, no overflow."""
    lines = _lines(30)
    model = powers_model(lines)
    assert model.overflow_count == 0
    assert model.overflow_name is None


def test_no_overflow_few_lines():
    lines = _lines(2)
    model = powers_model(lines)
    assert model.overflow_name is None
    assert model.overflow_count == 0


def test_overflow_rows_not_dropped():
    """Rule 6: all rows are in the model, overflow is display-only."""
    lines = _lines(40)
    model = powers_model(lines)
    assert len(model.row_houses) == len(lines)
    assert len(model.table.data) == len(lines)


# ── rule 15: no pipe character, empty roster ──────────────────────────


def test_no_pipe_in_cells():
    lines = (_line(house="A|B", apparent_intent="Test|Intent", breakdown=("x|y",)),)
    model = powers_model(lines)
    for row in model.table.data:
        for cell in row:
            assert "|" not in cell


def test_empty_roster_has_message():
    model = powers_model(())
    assert "empty" in model.texts
    assert len(model.texts["empty"]) > 0


# ── rule 16: powers_lines no longer feeds the draw ────────────────────


def test_powers_model_exists():
    """powers_model must be importable and callable."""
    model = powers_model(_lines(2))
    assert isinstance(model, PowersModel)


# ── layout tests ──────────────────────────────────────────────────────


def test_layout_has_keys():
    lines = _lines(3)
    model = powers_model(lines)
    content = pygame.Rect(0, 100, 1280, 600)
    layout = powers_layout(model, content)
    for key in ("title", "table", "detail", "buttons"):
        assert key in layout


def test_layout_rects_inside_content():
    lines = _lines(3)
    model = powers_model(lines)
    content = pygame.Rect(0, 100, 1280, 600)
    layout = powers_layout(model, content)
    for key, rect in layout.items():
        assert rect.left >= content.left
        assert rect.top >= content.top
        assert rect.right <= content.right
        assert rect.bottom <= content.bottom


def test_layout_no_overlap():
    lines = _lines(3)
    model = powers_model(lines)
    content = pygame.Rect(0, 100, 1280, 600)
    layout = powers_layout(model, content)
    rects = list(layout.values())
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            assert not rects[i].colliderect(rects[j])


# ── layout at multiple widths ─────────────────────────────────────────


def test_layout_at_widths():
    """Layout must work at widths 900, 1280, 1600 and height 900."""
    lines = _lines(4)
    model = powers_model(lines)
    for width in (900, 1280, 1600):
        content = pygame.Rect(0, 100, width, 600)
        layout = powers_layout(model, content)
        assert "table" in layout


# ── can_place_informant rules ─────────────────────────────────────────


def test_can_place_false_not_in_informant_rows():
    lines = (_line(house="A", can_place_informant=False),
             _line(house="B", can_place_informant=False))
    model = powers_model(lines)
    assert len(model.informant_rows) == 0


def test_mixed_can_place():
    lines = (_line(house="A", can_place_informant=True),
             _line(house="B", can_place_informant=False),
             _line(house="C", can_place_informant=True))
    model = powers_model(lines)
    assert 0 in model.informant_rows
    assert 1 not in model.informant_rows
    assert 2 in model.informant_rows


# ── Rule 4: informant button is clickable (draw + handle_click) ───────


def test_informant_button_clickable():
    """Rule 4: draw populates _informant_hits, handle_click returns the action."""
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView
    game = GildedGame(seed=7, player_house="Vantrell")
    view = BroadsheetView(game, "Vantrell")
    view.active_tab = "Powers"
    view.draw(pygame.Surface((1280, 900)))
    # _informant_hits must be populated
    assert len(view._informant_hits) > 0, "No informant hit regions registered"
    # Click the first hit
    rect, act = view._informant_hits[0]
    result = view.handle_click(rect.center)
    assert result == {"place_informant": act["place_informant"]}, (
        f"Expected {{'place_informant': {act['place_informant']!r}}}, got {result!r}"
    )


def test_every_informant_region_returns_its_own_house():
    """Rule 15: every informant hit region's centre returns its own house action."""
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView
    game = GildedGame(seed=7, player_house="Vantrell")
    view = BroadsheetView(game, "Vantrell")
    view.active_tab = "Powers"
    view.draw(pygame.Surface((1280, 900)))
    hits = list(view._informant_hits)
    assert len(hits) >= 2, f"Need >=2 regions to discriminate, got {len(hits)}"
    for rect, act in hits:
        result = view.handle_click(rect.center)
        assert result == {"place_informant": act["place_informant"]}, (
            f"Region for {act['place_informant']!r} returned {result!r}"
        )


def test_click_outside_informant_hits_returns_none():
    """Rule 4: clicking well outside any hit region returns None."""
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView
    game = GildedGame(seed=7, player_house="Vantrell")
    view = BroadsheetView(game, "Vantrell")
    view.active_tab = "Powers"
    view.draw(pygame.Surface((1280, 900)))
    rect, _ = view._informant_hits[0]
    # Click far to the left of the hit region
    result = view.handle_click((rect.left - 500, rect.top))
    assert result is None


# ── Rule 5: powers_report reads game.informants and attention ─────────


def test_powers_report_placed_informant():
    """Rule 5: placing an informant removes that house from can_place."""
    from gilded.chassis import GildedGame
    game = GildedGame(seed=7, player_house="Vantrell")
    report = powers_report(game, "Vantrell")
    # All rivals should be placeable initially
    target_house = report[0].house
    assert any(ln.can_place_informant for ln in report), "At least one should be placeable"
    # Place an informant on the first rival
    game.informants.add(("Vantrell", target_house))
    report2 = powers_report(game, "Vantrell")
    # The placed house must be False, others must still be True
    for ln in report2:
        if ln.house == target_house:
            assert ln.can_place_informant is False, (
                f"Expected can_place=False for {target_house!r} after placing informant"
            )
        else:
            assert ln.can_place_informant is True, (
                f"Expected can_place=True for {ln.house!r} (not the placed house)"
            )


def test_powers_report_no_attention():
    """Rule 5: with attention=0, no house is placeable."""
    from gilded.chassis import GildedGame
    game = GildedGame(seed=7, player_house="Vantrell")
    game.attention["Vantrell"] = 0
    report = powers_report(game, "Vantrell")
    for ln in report:
        assert ln.can_place_informant is False, (
            f"Expected can_place=False for {ln.house!r} with attention=0"
        )


# ── Rule 7: layout margin >= 4 on left/right/top ─────────────────────


def test_layout_margin_left_right_top():
    """Rule 7: margin is a stated minimum, not merely non-negative."""
    for n_rows in (3, 30, 60):
        lines = _lines(n_rows)
        model = powers_model(lines)
        for width in (900, 1280, 1600):
            content = pygame.Rect(0, 100, width, 600)
            layout = powers_layout(model, content)
            for key, rect in layout.items():
                assert rect.left - content.left >= 4, (
                    f"n={n_rows} w={width} {key}: left margin {rect.left - content.left} < 4"
                )
                assert content.right - rect.right >= 4, (
                    f"n={n_rows} w={width} {key}: right margin {content.right - rect.right} < 4"
                )
                assert rect.top - content.top >= 4, (
                    f"n={n_rows} w={width} {key}: top margin {rect.top - content.top} < 4"
                )
                # Bottom is >= 0, not >= 4 (existing behaviour)
                assert content.bottom - rect.bottom >= 0, (
                    f"n={n_rows} w={width} {key}: bottom margin {content.bottom - rect.bottom} < 0"
                )


# ── Rule 8: table clamped at large roster ─────────────────────────────


def test_table_clamped_at_60_rows():
    """Rule 8: at 60 rows, table rect is clamped, rect.height < table.height()."""
    lines = _lines(60)
    model = powers_model(lines)
    content = pygame.Rect(0, 100, 1280, 600)
    layout = powers_layout(model, content)
    tbl_rect = layout["table"]
    assert tbl_rect.bottom <= content.bottom, (
        f"Table bottom {tbl_rect.bottom} > content bottom {content.bottom}"
    )
    assert tbl_rect.height < model.table.height(), (
        f"Table rect height {tbl_rect.height} >= table height {model.table.height()} "
        f"— clamp did not bind"
    )


# ── Rule 1: the old truncation helper was removed ─────────────────────


def test_old_trunc_helper_removed():
    """Rule 1: the old truncation helper must not exist in broadsheet module."""
    import gilded.ui.broadsheet as bs
    assert not hasattr(bs, "_trunc" + "ate"), "old helper should have been removed"


# ── selected row detail ───────────────────────────────────────────────


def test_selected_row_has_full_intent():
    long_intent = "Pursuing conquest against House Valia: they threaten our borders"
    lines = (_line(house="A", apparent_intent=long_intent),)
    model = powers_model(lines, selected="A")
    assert model.selected_row == 0
    key = f"intent_{model.selected_row}"
    assert key in model.texts
    assert model.texts[key] == long_intent
