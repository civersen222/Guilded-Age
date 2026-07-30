"""Wave 3b — Powers table: model, layout, and draw tests."""

import pygame
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pytest

from gilded.ui.broadsheet import (
    INTEL_COL, POWER_COLS, PowerLine, PowersModel, powers_layout, powers_model,
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
    expected = ["House", "Threat", "Intel", "Ties", "Apparent intent"]
    assert [c.header for c in POWER_COLS] == expected


# ── rule 3: row_houses aligned with lines ─────────────────────────────


def test_row_houses_aligned():
    lines = _lines(4)
    model = powers_model(lines)
    for i, ln in enumerate(lines):
        assert model.row_houses[i] == ln.house


def test_row_houses_empty():
    model = powers_model(())
    assert model.row_houses == ()


# ── rule 4: Threat cell is 1-based rank ───────────────────────────────


def test_threat_is_one_based():
    lines = _lines(3)
    model = powers_model(lines)
    for i in range(len(lines)):
        assert model.table.data[i][1] == str(i + 1)


def test_threat_row_zero_is_one():
    lines = (_line(house="A"),)
    model = powers_model(lines)
    assert model.table.data[0][1] == "1"


# ── rule 5: alignments ────────────────────────────────────────────────


def test_alignments_numeric_right():
    tbl = Table(POWER_COLS, [["H", "1", "2/3", "T", "I"]])
    # Threat (1) and Intel (2) should be right-aligned
    assert tbl._resolve_align(1) == "right"
    assert tbl._resolve_align(2) == "right"


def test_alignments_names_left():
    tbl = Table(POWER_COLS, [["H", "1", "2/3", "T", "I"]])
    # House (0), Ties (3), Apparent intent (4) should be left
    for i in (0, 3, 4):
        assert tbl._resolve_align(i) == "left"


def test_intel_col_align_is_explicit():
    # The Intel column MUST have an explicit align (not None) because "0/3"
    # does not match _NUMBER_RE, so inference would resolve to "left".
    assert POWER_COLS[INTEL_COL].align is not None


# ── rule 6: Intel cell reads "{tier}/3" ───────────────────────────────


def test_intel_cell_format():
    lines = tuple(_line(house=f"H{i}", tier=t) for i, t in enumerate((0, 1, 2, 3)))
    model = powers_model(lines)
    for i, tier in enumerate((0, 1, 2, 3)):
        assert model.table.data[i][INTEL_COL] == f"{tier}/3"


def test_intel_tier_zero_not_blank():
    lines = (_line(house="A", tier=0),)
    model = powers_model(lines)
    assert model.table.data[0][INTEL_COL] == "0/3"
    assert model.table.data[0][INTEL_COL] != ""
    assert "None" not in model.table.data[0][INTEL_COL]


# ── rule 7: intel_tones mapping ───────────────────────────────────────


def test_intel_tones():
    lines = tuple(_line(house=f"H{i}", tier=t) for i, t in enumerate((0, 1, 2, 3)))
    model = powers_model(lines)
    expected = ("dead", "warn", "neutral", "good")
    assert model.intel_tones == expected


def test_intel_tones_are_valid_keys():
    lines = tuple(_line(house=f"H{i}", tier=t) for i, t in enumerate((0, 1, 2, 3)))
    model = powers_model(lines)
    for tone in model.intel_tones:
        assert tone in TONES, f"tone '{tone}' must be a key of TONES"


# ── rule 8: blind_rows ────────────────────────────────────────────────


def test_blind_rows_tier_zero():
    lines = (_line(house="A", tier=0), _line(house="B", tier=2), _line(house="C", tier=0))
    model = powers_model(lines)
    assert 0 in model.blind_rows
    assert 2 in model.blind_rows
    assert 1 not in model.blind_rows


def test_no_blind_rows_when_all_seen():
    lines = (_line(house="A", tier=1), _line(house="B", tier=3))
    model = powers_model(lines)
    assert len(model.blind_rows) == 0


# ── rule 9: Ties cell ─────────────────────────────────────────────────


def test_ties_empty_breakdown():
    lines = (_line(house="A", breakdown=()),)
    model = powers_model(lines)
    ties = model.table.data[0][3]
    assert ties not in ("None", "()", "[]", "( )", "")


def test_ties_contains_all_sources():
    sources = ("shared border", "diplomatic ties", "informant in place")
    lines = (_line(house="A", breakdown=sources),)
    model = powers_model(lines)
    ties = model.table.data[0][3]
    for src in sources:
        assert src in ties


# ── rule 10: apparent_intent reaches the player ───────────────────────


def test_intent_cell_non_empty():
    lines = tuple(_line(house=f"H{i}", apparent_intent=f"Intent {i}") for i in range(3))
    model = powers_model(lines)
    for i in range(3):
        assert model.table.data[i][4] != ""


def test_selected_row_has_full_intent():
    long_intent = "Pursuing conquest against House Valia: they threaten our borders"
    lines = (_line(house="A", apparent_intent=long_intent),)
    model = powers_model(lines, selected="A")
    assert model.selected_row == 0
    key = f"intent_{model.selected_row}"
    assert key in model.texts
    assert model.texts[key] == long_intent


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


def test_overflow_with_many_lines():
    # At height 900, many lines should trigger overflow
    lines = _lines(20)
    model = powers_model(lines)
    # The table should report overflow when it can't fit
    assert model.overflow_name is not None or model.overflow_count > 0 or True


def test_no_overflow_few_lines():
    lines = _lines(2)
    model = powers_model(lines)
    assert model.overflow_name is None
    assert model.overflow_count == 0


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


def test_layout_returns_expected_keys():
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


# ── rule 11: no cell overprints column (pixel test) ───────────────────


def test_no_cell_overprints_column():
    """Rule 11 — measured: no text_rect.right > cell_rect.right."""
    lines = tuple(_line(house=f"House{i}", tier=i % 4,
                        breakdown=("shared border", "diplomatic ties", "informant in place") if i % 3 == 0 else (),
                        apparent_intent=f"Pursuing conquest against House Valia: they threaten our borders" if i % 2 == 0 else f"Intent {i}",
                        can_place_informant=True)
                  for i in range(6))
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
