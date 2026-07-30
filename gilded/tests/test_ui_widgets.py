"""Wave 1b – in-repo tests for gilded/ui/widgets.py.

Geometric, never pixel-comparing (except the chip contrast rule which IS about
colour and is stated as a luminance inequality).  Headless via dummy driver.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pathlib
import pygame
import pytest

import gilded.ui.widgets as widgets
from gilded.ui import broadsheet


# ── helpers ──────────────────────────────────────────────────────────────────

def _init():
    if not pygame.font.get_init():
        pygame.font.init()
    pygame.init()


def _surf(w, h):
    return pygame.Surface((w, h))


def _lum(rgb):
    """Rec.709 luminance."""
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


# ── columns / rows ───────────────────────────────────────────────────────────

def test_columns_three_no_overlap():
    _init()
    r = pygame.Rect(0, 0, 300, 100)
    cols = widgets.columns(r, 3, 0)
    assert len(cols) == 3
    assert cols[0].left == r.left
    assert cols[-1].right == r.right
    for i in range(len(cols) - 1):
        assert cols[i].right <= cols[i + 1].left


def test_columns_gap():
    _init()
    gap = 10
    r = pygame.Rect(0, 0, 300, 100)
    cols = widgets.columns(r, 3, gap)
    for i in range(len(cols) - 1):
        assert cols[i + 1].left - cols[i].right == gap


def test_columns_first_left_last_right():
    _init()
    r = pygame.Rect(10, 20, 200, 80)
    cols = widgets.columns(r, 3, 0)
    assert cols[0].left == r.left
    assert cols[-1].right == r.right


def test_rows_ratio_1_to_3():
    _init()
    r = pygame.Rect(0, 0, 200, 400)
    rows = widgets.rows(r, (1, 3), 0)
    assert len(rows) == 2
    ratio = rows[0].height / rows[1].height
    assert abs(ratio - 1 / 3) < 0.05, f"Expected ~1:3 ratio, got {ratio}"


def test_rows_last_bottom():
    _init()
    r = pygame.Rect(0, 0, 200, 400)
    rows = widgets.rows(r, (1, 3), 0)
    assert rows[-1].bottom == r.bottom


def test_rows_last_bottom_non_divisible():
    """rows with weights (1,1,1) on height 10 — 10/3 is not an integer.

    Without the last-row override: int(1*3.333)=3 for each row,
    bottom = 9 != 10.  With the override: last row gets height 4,
    bottom = 10.  Total heights sum to rect.height with no leftover.
    """
    _init()
    r = pygame.Rect(0, 0, 200, 10)
    rows = widgets.rows(r, (1, 1, 1), 0)
    assert rows[-1].bottom == r.bottom
    assert sum(row.height for row in rows) == r.height


def test_rows_last_bottom_with_gap():
    """rows with weights (1,2) on height 100, gap=5.

    available = 95, base = 31.667.  Naive: row0=31, row1=63 → 31+63+5=99.
    Override: row1 = 100 - (31+5) = 64 → 31+64+5=100.
    """
    _init()
    gap = 5
    r = pygame.Rect(0, 0, 200, 100)
    rows = widgets.rows(r, (1, 2), gap)
    assert rows[-1].bottom == r.bottom
    total = sum(row.height for row in rows) + gap * (len(rows) - 1)
    assert total == r.height


def test_rows_gap_heights():
    _init()
    gap = 10
    r = pygame.Rect(0, 0, 200, 400)
    rows = widgets.rows(r, (1, 1), gap)
    total_h = rows[0].height + rows[1].height
    assert total_h == r.height - gap


def test_font_caching():
    """font(size, bold) returns the same instance on repeated calls."""
    _init()
    f1 = widgets.font(14)
    f2 = widgets.font(14)
    assert f1 is f2
    f3 = widgets.font(14, bold=True)
    assert f3 is not f1


def test_wrap_returns_lines():
    """wrap splits text into lines that fit within the given width."""
    _init()
    f = widgets.font(14)
    text = "one two three four five"
    lines = widgets.wrap(text, f, 100)
    assert len(lines) >= 1
    for line in lines:
        assert f.size(line)[0] <= 100


# ── Table ────────────────────────────────────────────────────────────────────

def test_table_header_width_ratios():
    _init()
    cols = [
        widgets.Column("A", width=1.0),
        widgets.Column("B", width=2.0),
        widgets.Column("C", width=1.0),
    ]
    data = [["a", "b", "c"]]
    tbl = widgets.Table(cols, data)
    lay = tbl.layout(pygame.Rect(0, 0, 400, 100))
    # Column B (weight 2) should be widest
    assert lay.header_rects[1].width > lay.header_rects[0].width
    assert lay.header_rects[1].width > lay.header_rects[2].width


def test_table_headers_tile_full_width():
    _init()
    cols = [
        widgets.Column("A", width=1.0),
        widgets.Column("B", width=1.0),
    ]
    data = [["a", "b"]]
    tbl = widgets.Table(cols, data)
    rect = pygame.Rect(0, 0, 200, 100)
    lay = tbl.layout(rect)
    assert lay.header_rects[0].left == rect.left
    assert lay.header_rects[-1].right == rect.right


def test_table_cells_inside_columns_and_rows():
    _init()
    cols = [
        widgets.Column("X", width=1.0),
        widgets.Column("Y", width=1.0),
    ]
    data = [["1", "2"], ["3", "4"]]
    tbl = widgets.Table(cols, data)
    lay = tbl.layout(pygame.Rect(0, 0, 200, 120))
    for i, col_rect in enumerate(lay.header_rects):
        for row_cells in lay.cell_rects:
            cell = row_cells[i]
            assert cell.left >= col_rect.left
            assert cell.right <= col_rect.right


def test_table_row_rects_no_overlap():
    _init()
    cols = [widgets.Column("A", width=1.0), widgets.Column("B", width=1.0)]
    data = [["1", "2"], ["3", "4"], ["5", "6"]]
    tbl = widgets.Table(cols, data)
    lay = tbl.layout(pygame.Rect(0, 0, 200, 150))
    for i in range(len(lay.row_rects) - 1):
        assert lay.row_rects[i].bottom <= lay.row_rects[i + 1].top


def test_table_numeric_right_align():
    _init()
    cols = [
        widgets.Column("Name", width=1.0),
        widgets.Column("Score", width=1.0),
    ]
    data = [
        ["Alice", "100"],
        ["Bob", "2000"],
        ["Charlie", "30"],
    ]
    tbl = widgets.Table(cols, data)
    lay = tbl.layout(pygame.Rect(0, 0, 300, 150))
    # Numeric column text_rects should share one right edge
    num_col_idx = 1
    right_edges = [lay.text_rects[r][num_col_idx].right for r in range(len(lay.text_rects))]
    assert len(set(right_edges)) == 1, f"Right edges not uniform: {right_edges}"


def test_table_text_left_align():
    _init()
    cols = [widgets.Column("Name", width=1.0)]
    data = [["Alice"], ["Bob"], ["Charlie"]]
    tbl = widgets.Table(cols, data)
    lay = tbl.layout(pygame.Rect(0, 0, 200, 150))
    left_edges = [lay.text_rects[r][0].left for r in range(len(lay.text_rects))]
    assert len(set(left_edges)) == 1, f"Left edges not uniform: {left_edges}"


def test_table_numeric_right_past_center():
    _init()
    cols = [widgets.Column("Score", width=1.0)]
    data = [["100"], ["2000"], ["30"]]
    tbl = widgets.Table(cols, data)
    lay = tbl.layout(pygame.Rect(0, 0, 200, 150))
    col_span = lay.header_rects[0]
    center = col_span.left + col_span.width / 2
    for tr in lay.text_rects:
        assert tr[0].left > center, "Numeric text should be right-aligned past center"


def test_table_explicit_align_left_beats_numeric():
    _init()
    cols = [widgets.Column("Score", width=1.0, align="left")]
    data = [["100"], ["2000"], ["30"]]
    tbl = widgets.Table(cols, data)
    lay = tbl.layout(pygame.Rect(0, 0, 200, 150))
    left_edges = [lay.text_rects[r][0].left for r in range(len(lay.text_rects))]
    assert len(set(left_edges)) == 1, "Explicit left-align should make all left edges equal"


def test_table_rule_y_between_header_and_data():
    _init()
    cols = [widgets.Column("A", width=1.0)]
    data = [["1"], ["2"]]
    tbl = widgets.Table(cols, data, row_rule=True)
    lay = tbl.layout(pygame.Rect(0, 0, 200, 150))
    header_bottom = lay.header_rects[0].bottom
    first_row_top = lay.row_rects[0].top
    assert header_bottom < lay.rule_y < first_row_top


def test_table_row_rects_full_width():
    _init()
    cols = [widgets.Column("A", width=1.0), widgets.Column("B", width=1.0)]
    data = [["1", "2"]]
    tbl = widgets.Table(cols, data)
    rect = pygame.Rect(0, 0, 200, 100)
    lay = tbl.layout(rect)
    for rr in lay.row_rects:
        assert rr.left == rect.left
        assert rr.right == rect.right


def test_table_row_contains_cells():
    _init()
    cols = [widgets.Column("A", width=1.0), widgets.Column("B", width=1.0)]
    data = [["1", "2"], ["3", "4"]]
    tbl = widgets.Table(cols, data)
    lay = tbl.layout(pygame.Rect(0, 0, 200, 150))
    for row_rect, cells in zip(lay.row_rects, lay.cell_rects):
        for cell in cells:
            assert cell.top >= row_rect.top
            assert cell.bottom <= row_rect.bottom


def test_table_height_more_rows_taller():
    _init()
    cols = [widgets.Column("A", width=1.0)]
    tbl2 = widgets.Table(cols, [["1"], ["2"]])
    tbl5 = widgets.Table(cols, [["1"], ["2"], ["3"], ["4"], ["5"]])
    assert tbl5.height() > tbl2.height()


def test_table_empty_data():
    _init()
    cols = [widgets.Column("A", width=1.0), widgets.Column("B", width=1.0)]
    tbl = widgets.Table(cols, [])
    rect = pygame.Rect(0, 0, 200, 100)
    lay = tbl.layout(rect)
    tbl.draw(_surf(200, 100), rect)


# ── Meter ────────────────────────────────────────────────────────────────────

def test_meter_full_bar():
    _init()
    m = widgets.Meter("Fuel", 100, 0, 100)
    lay = m.layout(pygame.Rect(0, 0, 200, 40))
    assert lay.fill_rect.width == lay.bar_rect.width


def test_meter_empty_bar():
    _init()
    m = widgets.Meter("Fuel", 0, 0, 100)
    lay = m.layout(pygame.Rect(0, 0, 200, 40))
    assert lay.fill_rect.width == 0


def test_meter_quarter_fill():
    _init()
    m = widgets.Meter("Fuel", 25, 0, 100)
    lay = m.layout(pygame.Rect(0, 0, 200, 40))
    expected = lay.bar_rect.width / 4
    assert abs(lay.fill_rect.width - expected) <= 2


def test_meter_clamp_above():
    _init()
    m = widgets.Meter("Over", 500, 0, 100)
    lay = m.layout(pygame.Rect(0, 0, 200, 40))
    assert 0 <= lay.fill_rect.width <= lay.bar_rect.width
    assert lay.fill_rect.left >= lay.bar_rect.left
    assert lay.fill_rect.right <= lay.bar_rect.right


def test_meter_clamp_below():
    _init()
    m = widgets.Meter("Under", -70, 0, 100)
    lay = m.layout(pygame.Rect(0, 0, 200, 40))
    assert 0 <= lay.fill_rect.width <= lay.bar_rect.width
    assert lay.fill_rect.left >= lay.bar_rect.left
    assert lay.fill_rect.right <= lay.bar_rect.right


def test_meter_parts_no_overlap():
    _init()
    m = widgets.Meter("Temp", 50, 0, 100)
    lay = m.layout(pygame.Rect(0, 0, 300, 50))
    parts = [lay.label_rect, lay.bar_rect, lay.value_rect]
    if lay.arrow_rect is not None:
        parts.append(lay.arrow_rect)
    for i, a in enumerate(parts):
        for j, b in enumerate(parts):
            if i != j:
                assert not a.colliderect(b), f"{i} and {j} overlap"


def test_meter_parts_inside_rect():
    _init()
    m = widgets.Meter("Temp", 50, 0, 100)
    rect = pygame.Rect(10, 10, 300, 50)
    lay = m.layout(rect)
    for part in [lay.label_rect, lay.bar_rect, lay.value_rect]:
        assert part.top >= rect.top
        assert part.bottom <= rect.bottom
        assert part.left >= rect.left
        assert part.right <= rect.right


def test_meter_danger_below():
    _init()
    m = widgets.Meter("Low", 30, 0, 100, danger=("below", 40))
    assert m.tone() == "bad"
    m2 = widgets.Meter("Ok", 70, 0, 100, danger=("below", 40))
    assert m2.tone() != "bad"


def test_meter_danger_below_at_boundary():
    _init()
    m = widgets.Meter("At", 40, 0, 100, danger=("below", 40))
    assert m.tone() == "bad"


def test_meter_danger_above():
    _init()
    m = widgets.Meter("High", 70, 0, 100, danger=("above", 60))
    assert m.tone() == "bad"
    m2 = widgets.Meter("Safe", 30, 0, 100, danger=("above", 60))
    assert m2.tone() != "bad"


def test_meter_danger_above_at_boundary():
    _init()
    m = widgets.Meter("At", 60, 0, 100, danger=("above", 60))
    assert m.tone() == "bad"


def test_meter_delta_tones_different():
    _init()
    m_up = widgets.Meter("Up", 50, 0, 100, delta=10)
    m_down = widgets.Meter("Down", 50, 0, 100, delta=-10)
    m_flat = widgets.Meter("Flat", 50, 0, 100, delta=0)
    tones = [m_up.delta_tone(), m_down.delta_tone(), m_flat.delta_tone()]
    assert len(set(tones)) == 3, f"Delta tones should be different: {tones}"


def test_meter_delta_arrows_different():
    _init()
    m_up = widgets.Meter("Up", 50, 0, 100, delta=10)
    m_down = widgets.Meter("Down", 50, 0, 100, delta=-10)
    m_flat = widgets.Meter("Flat", 50, 0, 100, delta=0)
    arrows = [m_up.arrow(), m_down.arrow(), m_flat.arrow()]
    assert len(set(arrows)) == 3, f"Arrow glyphs should be different: {arrows}"


def test_meter_invert_swaps_tones():
    _init()
    m_normal = widgets.Meter("N", 50, 0, 100, delta=10)
    m_inv = widgets.Meter("I", 50, 0, 100, delta=10, invert=True)
    assert m_normal.delta_tone() != m_inv.delta_tone()


def test_meter_lo_eq_hi():
    _init()
    m = widgets.Meter("Same", 5, 5, 5)
    f = m.fraction()
    lay = m.layout(pygame.Rect(0, 0, 200, 40))


# ── Chip ─────────────────────────────────────────────────────────────────────

def test_chip_pads_text():
    _init()
    c = widgets.Chip("hello")
    f = widgets.font(c.pt)
    tw, _ = f.size("hello")
    assert c.size()[0] > tw


def test_chip_longer_wider():
    _init()
    c1 = widgets.Chip("hi")
    c2 = widgets.Chip("a much longer label")
    assert c2.size()[0] > c1.size()[0]


def test_chip_contrast_all_tones():
    _init()
    for tone_name in widgets.TONES:
        c = widgets.Chip("test", tone=tone_name)
        lum_bg = _lum(c.bg())
        lum_ink = _lum(c.ink())
        diff = abs(lum_ink - lum_bg)
        assert diff >= 90, f"Contrast too low for tone '{tone_name}': {diff:.1f}"


def test_chip_draw_returns_correct_rect():
    _init()
    c = widgets.Chip("hello")
    surf = _surf(200, 200)
    pos = (37, 51)
    ret = c.draw(surf, pos)
    assert ret.topleft == pos
    assert ret.size == c.size()


def test_chip_invalid_tone_raises():
    _init()
    with pytest.raises((ValueError, KeyError)):
        widgets.Chip("x", tone="chartreuse")


# ── Panel ────────────────────────────────────────────────────────────────────

def test_panel_inner_strictly_inside():
    _init()
    p = widgets.Panel(pygame.Rect(0, 0, 200, 100))
    inner = p.inner()
    assert inner.left > p.rect.left
    assert inner.top > p.rect.top
    assert inner.right < p.rect.right
    assert inner.bottom < p.rect.bottom


def test_panel_inner_minimum_clearance():
    """Content must have real clearance from the border, not merely nonzero.

    Asserts each side has at least 4 px of clearance.  This catches the
    case where _PANEL_PAD is set to 0 (border alone gives only 1 px).
    """
    _init()
    p = widgets.Panel(pygame.Rect(0, 0, 200, 100))
    inner = p.inner()
    left_clear = inner.left - p.rect.left
    right_clear = p.rect.right - inner.right
    top_clear = inner.top - p.rect.top
    bottom_clear = p.rect.bottom - inner.bottom
    for name, val in [("left", left_clear), ("right", right_clear),
                      ("top", top_clear), ("bottom", bottom_clear)]:
        assert val >= 4, f"Panel {name} clearance is {val}, expected >= 4"


def test_panel_titled_inner_lower():
    _init()
    rect = pygame.Rect(0, 0, 200, 100)
    p_titled = widgets.Panel(rect, title="Ledger")
    p_untitled = widgets.Panel(rect)
    assert p_titled.inner().top > p_untitled.inner().top
    assert p_titled.inner().height < p_untitled.inner().height


def test_panel_small_no_negative():
    _init()
    p = widgets.Panel(pygame.Rect(0, 0, 30, 12), title="Ledger")
    inner = p.inner()
    assert inner.width >= 0
    assert inner.height >= 0


# ── Boundaries ───────────────────────────────────────────────────────────────

def test_widgets_no_broadsheet_import():
    source = pathlib.Path(widgets.__file__).read_text(encoding="utf-8")
    assert "broadsheet" not in source
    assert "atlas_view" not in source
    assert "gilded.ui.app" not in source


def test_broadsheet_uses_widgets_palette():
    assert broadsheet._font is widgets.font
    assert broadsheet.INK == widgets.INK
