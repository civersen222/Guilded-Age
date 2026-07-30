"""Wave 3 — Enterprises table: model, layout, and draw tests."""

import pygame
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import pytest

from gilded.grip import (
    BAND_CONTESTED, BAND_IMPERILED, BAND_IRON_GRIP, BAND_SEIZED,
    Director, EnterpriseLine, GripReport, Holder,
)
from gilded.ui.broadsheet import (
    DELTA_COL, ENT_COLS, EnterprisesModel, enterprises_layout, enterprises_model,
)
from gilded.ui.widgets import Table, TableLayout, TONES

# ── fixture helpers ────────────────────────────────────────────────────

def _line(eid=1, name="Test Mill", sector="freight", tier=1,
          dividend=100.0, dividend_delta=9.6, director=None,
          your_stake=50.0, top_outside=("Rival", 10.0)):
    return EnterpriseLine(
        eid=eid, name=name, sector=sector, tier=tier,
        dividend=dividend, dividend_delta=dividend_delta,
        director=director, your_stake=your_stake,
        top_outside=top_outside,
    )


def _report(enterprises=(), controlling_stake=50.0, threshold=50.0,
            margin=0.0, band=BAND_CONTESTED, top_predator=None,
            loyal_bloc=(), house="Valia"):
    return GripReport(
        house=house,
        enterprises=tuple(enterprises),
        loyal_bloc=tuple(loyal_bloc),
        controlling_stake=controlling_stake,
        top_predator=top_predator,
        threshold=threshold,
        margin=margin,
        band=band,
    )


# ── rule 1: one row per enterprise ─────────────────────────────────────

def test_row_count_matches_enterprises():
    lines = [_line(eid=i, name=f"Mill {i}") for i in range(1, 6)]
    model = enterprises_model(_report(enterprises=lines))
    assert len(model.table.data) == len(lines)


def test_zero_enterprises():
    model = enterprises_model(_report(enterprises=()))
    assert len(model.table.data) == 0


# ── rule 2: ENT_COLS has exactly 8 columns with correct headers ────────

def test_ent_cols_count():
    assert len(ENT_COLS) == 8


def test_ent_cols_headers():
    expected = ["Venture", "Sector", "Tier", "Dividend", "Δ",
                "Director", "Stake", "Top outside"]
    assert [c.header for c in ENT_COLS] == expected


# ── rule 3: row_eids aligned with enterprises ──────────────────────────

def test_row_eids_aligned():
    eids = [10, 20, 30]
    lines = [_line(eid=e, name=f"V{i}") for i, e in enumerate(eids, 1)]
    model = enterprises_model(_report(enterprises=lines))
    assert model.row_eids == (10, 20, 30)


# ── rule 4: column alignments ──────────────────────────────────────────

def test_column_alignments():
    tbl = Table(ENT_COLS, [()])
    # Left: Venture(0), Sector(1), Director(5), Top outside(7)
    for i in (0, 1, 5, 7):
        assert tbl._resolve_align(i) == "left", f"col {i} should be left"
    # Right: Tier(2), Dividend(3), Δ(4), Stake(6)
    for i in (2, 3, 4, 6):
        assert tbl._resolve_align(i) == "right", f"col {i} should be right"


# ── rule 5: None delta → empty cell, neutral tone ──────────────────────

def test_none_delta_empty_cell_neutral_tone():
    line = _line(dividend_delta=None)
    model = enterprises_model(_report(enterprises=[line]))
    assert model.table.data[0][DELTA_COL] == ""
    assert model.delta_tones[0] == "neutral"


# ── rule 6: delta sign → tone mapping ──────────────────────────────────

def test_positive_delta_tone_good():
    model = enterprises_model(_report(enterprises=[_line(dividend_delta=5.0)]))
    assert model.delta_tones[0] == "good"


def test_negative_delta_tone_bad():
    model = enterprises_model(_report(enterprises=[_line(dividend_delta=-5.0)]))
    assert model.delta_tones[0] == "bad"


def test_zero_delta_tone_neutral():
    model = enterprises_model(_report(enterprises=[_line(dividend_delta=0.0)]))
    assert model.delta_tones[0] == "neutral"


# ── rule 7: delta cell carries explicit sign and one decimal ───────────

def test_delta_cell_signed_plus():
    model = enterprises_model(_report(enterprises=[_line(dividend_delta=9.6)]))
    assert model.table.data[0][DELTA_COL] == "+9.6"


def test_delta_cell_signed_minus():
    model = enterprises_model(_report(enterprises=[_line(dividend_delta=-9.6)]))
    assert model.table.data[0][DELTA_COL] == "-9.6"


def test_delta_cell_signed_zero():
    model = enterprises_model(_report(enterprises=[_line(dividend_delta=0.0)]))
    assert model.table.data[0][DELTA_COL] == "+0.0"


# ── rule 8: None director → "Vacant", not "None" ──────────────────────

def test_none_director_vacant():
    model = enterprises_model(_report(enterprises=[_line(director=None)]))
    dir_cell = model.table.data[0][5]  # Director column
    assert dir_cell != "None"
    assert dir_cell == "Vacant"


def test_no_none_string_in_any_cell():
    lines = [_line(director=None, top_outside=None)]
    model = enterprises_model(_report(enterprises=lines))
    for row in model.table.data:
        for cell in row:
            assert "None" not in cell


# ── rule 9: disloyal director → skim_rows ──────────────────────────────

def test_disloyal_director_in_skim_rows():
    disloyal_dir = Director(id="d1", name="Bad Director", industry=5, disloyal=True)
    model = enterprises_model(_report(enterprises=[_line(director=disloyal_dir)]))
    assert 0 in model.skim_rows


def test_loyal_director_not_in_skim_rows():
    loyal_dir = Director(id="d2", name="Good Director", industry=5, disloyal=False)
    model = enterprises_model(_report(enterprises=[_line(director=loyal_dir)]))
    assert 0 not in model.skim_rows


def test_skim_rows_with_multiple_directors():
    disloyal_dir = Director(id="d1", name="Bad", industry=5, disloyal=True)
    loyal_dir = Director(id="d2", name="Good", industry=5, disloyal=False)
    lines = [
        _line(eid=1, director=loyal_dir),
        _line(eid=2, director=disloyal_dir),
        _line(eid=3, director=None),
    ]
    model = enterprises_model(_report(enterprises=lines))
    assert 0 not in model.skim_rows
    assert 1 in model.skim_rows
    assert 2 not in model.skim_rows


# ── rule 10: top_outside formatting ────────────────────────────────────

def test_none_top_outside_not_none_string():
    model = enterprises_model(_report(enterprises=[_line(top_outside=None)]))
    cell = model.table.data[0][7]
    assert cell != "None"
    assert cell != ""


def test_top_outside_formatted():
    model = enterprises_model(_report(enterprises=[_line(top_outside=("Rival", 10.0))]))
    cell = model.table.data[0][7]
    assert "Rival" in cell
    assert "10.0%" in cell


# ── rule 11: band_chip text and tone ───────────────────────────────────

def test_band_chip_no_underscore():
    for band in (BAND_SEIZED, BAND_IMPERILED, BAND_CONTESTED, BAND_IRON_GRIP):
        model = enterprises_model(_report(band=band))
        assert "_" not in model.band_chip.text, f"band {band} has underscore in chip text"


def test_band_chip_tone_seized():
    model = enterprises_model(_report(band=BAND_SEIZED))
    assert model.band_chip.tone == "bad"


def test_band_chip_tone_imperiled():
    model = enterprises_model(_report(band=BAND_IMPERILED))
    assert model.band_chip.tone == "bad"


def test_band_chip_tone_contested():
    model = enterprises_model(_report(band=BAND_CONTESTED))
    assert model.band_chip.tone == "warn"


def test_band_chip_tone_iron_grip():
    model = enterprises_model(_report(band=BAND_IRON_GRIP))
    assert model.band_chip.tone == "good"


# ── rule 12: margin_meter ──────────────────────────────────────────────

def test_margin_meter_value():
    model = enterprises_model(_report(margin=12.5))
    assert model.margin_meter.value == 12.5


def test_margin_meter_negative():
    model = enterprises_model(_report(margin=-5.0))
    assert model.margin_meter.value == -5.0


def test_margin_meter_danger_when_at_or_below_zero():
    model = enterprises_model(_report(margin=0.0))
    assert model.margin_meter.tone() == "bad"
    model2 = enterprises_model(_report(margin=-3.0))
    assert model2.margin_meter.tone() == "bad"


# ── rule 13: overflow detection ────────────────────────────────────────

def test_overflow_with_many_ventures():
    lines = [_line(eid=i, name=f"Mill {i}") for i in range(1, 51)]
    model = enterprises_model(_report(enterprises=lines))
    assert model.overflow_name is not None
    assert model.overflow_count > 0


def test_no_overflow_with_few_ventures():
    lines = [_line(eid=i, name=f"Mill {i}") for i in range(1, 4)]
    model = enterprises_model(_report(enterprises=lines))
    assert model.overflow_name is None
    assert model.overflow_count == 0


# ── rule 14: no pipe character in cells ────────────────────────────────

def test_no_pipe_in_cells():
    lines = [_line(name="A|B", sector="x|y")]
    model = enterprises_model(_report(enterprises=lines))
    for row in model.table.data:
        for cell in row:
            assert "|" not in cell


# ── rule 15: enterprises_lines not used ────────────────────────────────

def test_draw_enterprises_not_using_enterprises_lines():
    import inspect
    from gilded.ui.broadsheet import BroadsheetView
    src = inspect.getsource(BroadsheetView._draw_enterprises)
    assert "enterprises_lines" not in src


# ── layout tests ───────────────────────────────────────────────────────

def test_layout_rects_inside_content():
    lines = [_line(eid=i, name=f"Mill {i}") for i in range(1, 6)]
    model = enterprises_model(_report(enterprises=lines))
    content = pygame.Rect(0, 0, 1280, 900)
    layout = enterprises_layout(model, content)
    for name, rect in layout.items():
        assert rect.left >= content.left
        assert rect.top >= content.top
        assert rect.right <= content.right
        assert rect.bottom <= content.bottom


def test_layout_clearance():
    lines = [_line(eid=i, name=f"Mill {i}") for i in range(1, 6)]
    model = enterprises_model(_report(enterprises=lines))
    content = pygame.Rect(0, 0, 1280, 900)
    layout = enterprises_layout(model, content)
    for name, rect in layout.items():
        assert rect.left - content.left >= 4
        assert rect.top - content.top >= 4
        assert content.right - rect.right >= 4
        assert content.bottom - rect.bottom >= 4


def test_layout_no_overlap():
    lines = [_line(eid=i, name=f"Mill {i}") for i in range(1, 6)]
    model = enterprises_model(_report(enterprises=lines))
    content = pygame.Rect(0, 0, 1280, 900)
    layout = enterprises_layout(model, content)
    rects = list(layout.items())
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            n1, r1 = rects[i]
            n2, r2 = rects[j]
            assert not r1.colliderect(r2), f"{n1} overlaps {n2}"


def test_layout_returns_action_area():
    lines = [_line(eid=1)]
    model = enterprises_model(_report(enterprises=lines))
    content = pygame.Rect(0, 0, 1280, 900)
    layout = enterprises_layout(model, content)
    assert "action" in layout


@pytest.mark.parametrize("width", [900, 1280, 1600])
def test_layout_clearance_at_widths(width):
    lines = [_line(eid=i, name=f"Mill {i}") for i in range(1, 4)]
    model = enterprises_model(_report(enterprises=lines))
    content = pygame.Rect(0, 0, width, 900)
    layout = enterprises_layout(model, content)
    for name, rect in layout.items():
        assert rect.left - content.left >= 4
        assert rect.top - content.top >= 4
        assert content.right - rect.right >= 4
        assert content.bottom - rect.bottom >= 4


# ── enterprises_model returns EnterprisesModel ─────────────────────────

def test_model_type():
    model = enterprises_model(_report())
    assert isinstance(model, EnterprisesModel)


# ── DELTA_COL index ────────────────────────────────────────────────────

def test_delta_col_index():
    assert DELTA_COL == 4
    assert ENT_COLS[DELTA_COL].header == "Δ"
