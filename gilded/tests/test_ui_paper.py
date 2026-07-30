"""UI Paper tests — rules 1-15 of Wave 5 (the papers get a measure).

Covers column_plan geometry, flow_columns placement, overflow handling,
continuation marker, horizontal rule, and multi-configuration rendering
at 1280x900, 800x600 x seeds 7, 42.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

pygame.init()
try:
    pygame.font.init()
finally:
    pass

from gilded.chassis import GildedGame
from gilded.papers import compose, WRAP_WIDTH
from gilded.ui.widgets import (
    MEASURE_CHARS, COLUMN_GAP,
    column_plan, flow_columns, FlowResult,
    columns, font as _font, wrap as _wrap,
    INK, FADED, PAPER_BG,
)
from gilded.ui.broadsheet import BroadsheetView, PAD, TAB_H, _hud_height, BOTTOM_H


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _game(seed=7, turns=1):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.open_turn()
        g.end_turn()
    return g


def _rect(w, h=600):
    return pygame.Rect(0, 0, w, h)


def _font18():
    return _font(18)


# ────────────────────────────────────────────────────────────────────────────
# Rule 1: constants exist, papers.py is untouched
# ────────────────────────────────────────────────────────────────────────────

def test_rule1_measure_chars_exists():
    assert MEASURE_CHARS == 66

def test_rule1_column_gap_exists():
    assert COLUMN_GAP == 24

def test_rule1_papers_wrap_width_unchanged():
    assert WRAP_WIDTH == 72


# ────────────────────────────────────────────────────────────────────────────
# Rule 2: column_plan exists, n >= 1 for all rect widths
# ────────────────────────────────────────────────────────────────────────────

def test_rule2_column_plan_returns_list():
    f = _font18()
    res = column_plan(_rect(1248), f)
    assert isinstance(res, list)

def test_rule2_column_plan_never_zero_columns():
    f = _font18()
    for w in range(200, 4001, 100):
        cols = column_plan(_rect(w), f)
        assert len(cols) >= 1, f"n=0 at width {w}"

def test_rule2_column_plan_no_division_by_zero():
    f = _font18()
    cols = column_plan(_rect(50), f)
    assert len(cols) >= 1


# ────────────────────────────────────────────────────────────────────────────
# Rule 3: every column width <= measure_px; exact 594 at 18pt
# ────────────────────────────────────────────────────────────────────────────

def test_rule3_col_width_at_640():
    f = _font18()
    cols = column_plan(_rect(608), f)
    assert all(c.width <= f.size("x" * 66)[0] for c in cols)

def test_rule3_col_width_at_800():
    f = _font18()
    cols = column_plan(_rect(768), f)
    assert all(c.width <= f.size("x" * 66)[0] for c in cols)

def test_rule3_col_width_at_1024():
    f = _font18()
    cols = column_plan(_rect(992), f)
    assert all(c.width <= f.size("x" * 66)[0] for c in cols)

def test_rule3_col_width_at_1280():
    f = _font18()
    cols = column_plan(_rect(1248), f)
    measure_px = f.size("x" * 66)[0]
    assert all(c.width == measure_px for c in cols)

def test_rule3_col_width_at_1600():
    f = _font18()
    cols = column_plan(_rect(1568), f)
    assert all(c.width <= f.size("x" * 66)[0] for c in cols)

def test_rule3_col_width_at_1920():
    f = _font18()
    cols = column_plan(_rect(1888), f)
    assert all(c.width <= f.size("x" * 66)[0] for c in cols)

def test_rule3_col_width_at_2560():
    f = _font18()
    cols = column_plan(_rect(2528), f)
    assert all(c.width <= f.size("x" * 66)[0] for c in cols)

def test_rule3_exact_594_at_18pt():
    f = _font18()
    cols = column_plan(_rect(1248), f)
    measure_px = f.size("x" * 66)[0]
    assert measure_px == 594
    assert all(c.width == 594 for c in cols)


# ────────────────────────────────────────────────────────────────────────────
# Rule 4: correct n at key widths
# ────────────────────────────────────────────────────────────────────────────

def test_rule4_n_formula():
    f = _font18()
    measure_px = f.size("x" * 66)[0]
    gap = COLUMN_GAP
    for w in [608, 768, 992, 1248, 1568, 1888, 2528]:
        cols = column_plan(_rect(w), f)
        expected_n = max(1, (w + gap) // (measure_px + gap))
        assert len(cols) == expected_n, f"n={len(cols)} != {expected_n} at w={w}"

def test_rule4_n_is_2_at_1248():
    f = _font18()
    cols = column_plan(_rect(1248), f)
    assert len(cols) == 2

def test_rule4_n_is_1_at_768():
    f = _font18()
    cols = column_plan(_rect(768), f)
    assert len(cols) == 1

def test_rule4_n_is_3_at_1888():
    f = _font18()
    cols = column_plan(_rect(1888), f)
    assert len(cols) == 3


# ────────────────────────────────────────────────────────────────────────────
# Rule 5: non-overlapping, ordered, inside rect, centred
# ────────────────────────────────────────────────────────────────────────────

def test_rule5_non_overlapping():
    f = _font18()
    rect = _rect(1248)
    cols = column_plan(rect, f)
    for i in range(len(cols) - 1):
        assert cols[i].right <= cols[i + 1].left

def test_rule5_ordered_left_to_right():
    f = _font18()
    rect = _rect(1248)
    cols = column_plan(rect, f)
    for i in range(len(cols) - 1):
        assert cols[i].x < cols[i + 1].x

def test_rule5_all_inside_rect():
    f = _font18()
    rect = _rect(1248)
    cols = column_plan(rect, f)
    for c in cols:
        assert c.left >= rect.left
        assert c.right <= rect.right

def test_rule5_centred_margins():
    f = _font18()
    rect = _rect(1248)
    cols = column_plan(rect, f)
    left_margin = cols[0].left - rect.left
    right_margin = rect.right - cols[-1].right
    assert abs(left_margin - right_margin) <= 1


# ────────────────────────────────────────────────────────────────────────────
# Rule 6: composes columns(), consistent gutter
# ────────────────────────────────────────────────────────────────────────────

def test_rule6_gutter_consistency():
    f = _font18()
    rect = _rect(1248)
    cols = column_plan(rect, f)
    for i in range(len(cols) - 1):
        gap_actual = cols[i + 1].left - cols[i].right
        assert gap_actual == COLUMN_GAP

def test_rule6_uses_columns():
    f = _font18()
    rect = _rect(1248)
    cols = column_plan(rect, f)
    n = len(cols)
    col_w = cols[0].width
    block = col_w * n + COLUMN_GAP * (n - 1)
    margin = (rect.width - block) // 2
    assert cols[0].x == margin


# ────────────────────────────────────────────────────────────────────────────
# Rule 7: flow_columns returns FlowResult
# ────────────────────────────────────────────────────────────────────────────

def test_rule7_flow_result_type():
    f = _font18()
    res = flow_columns(["hello"], f, _rect(600, 400), line_gap=4)
    assert isinstance(res, FlowResult)

def test_rule7_flow_result_has_placements():
    f = _font18()
    res = flow_columns(["hello"], f, _rect(600, 400), line_gap=4)
    assert hasattr(res, "placements")
    assert isinstance(res.placements, list)

def test_rule7_flow_result_has_overflow():
    f = _font18()
    res = flow_columns(["hello"], f, _rect(600, 400), line_gap=4)
    assert hasattr(res, "overflow")
    assert isinstance(res.overflow, int)


# ────────────────────────────────────────────────────────────────────────────
# Rule 8: every placement pixel width <= column width
# ────────────────────────────────────────────────────────────────────────────

def test_rule8_placement_width_seed7():
    g = _game(seed=7, turns=10)
    f = _font18()
    for attr in ("gazette", "ledger", "letters"):
        report = compose(g, list(g.houses.keys())[0])
        items = getattr(report, attr)
        if not items:
            continue
        rect = _rect(1248, 600)
        res = flow_columns(items, f, rect, line_gap=4)
        cols = column_plan(rect, f)
        for (text, x, y, ci) in res.placements:
            pw = f.size(text)[0]
            assert pw <= cols[ci].width

def test_rule8_placement_width_seed42():
    g = _game(seed=42, turns=10)
    f = _font18()
    for attr in ("gazette", "ledger", "letters"):
        report = compose(g, list(g.houses.keys())[0])
        items = getattr(report, attr)
        if not items:
            continue
        rect = _rect(1248, 600)
        res = flow_columns(items, f, rect, line_gap=4)
        cols = column_plan(rect, f)
        for (text, x, y, ci) in res.placements:
            pw = f.size(text)[0]
            assert pw <= cols[ci].width

def test_rule8_longest_line_under_100_chars():
    f = _font18()
    g = _game(seed=42, turns=40)
    for turns in range(1, 41):
        report = compose(g, list(g.houses.keys())[0])
        for attr in ("gazette", "ledger", "letters"):
            items = getattr(report, attr)
            if not items:
                continue
            rect = _rect(1248, 600)
            res = flow_columns(items, f, rect, line_gap=4)
            for (text, x, y, ci) in res.placements:
                assert len(text) < 100


# ────────────────────────────────────────────────────────────────────────────
# Rule 9: every placement bottom <= rect.bottom
# ────────────────────────────────────────────────────────────────────────────

def test_rule9_placement_inside_rect():
    f = _font18()
    rect = _rect(1248, 600)
    items = [f"Item {i}: this is a test line" for i in range(50)]
    res = flow_columns(items, f, rect, line_gap=4)
    line_h = f.size("x")[1]
    for (text, x, y, ci) in res.placements:
        assert y + line_h <= rect.bottom


# ────────────────────────────────────────────────────────────────────────────
# Rule 10: column-major fill
# ────────────────────────────────────────────────────────────────────────────

def test_rule10_column_major_fill():
    """Column-major fill: items fill col 0 completely before spilling to col 1.

    With 48 items and 24 capacity per column, col 0 gets items 0-23,
    col 1 gets items 24-47.  The last item of col 0 is 'Line 23'.
    A round-robin implementation would interleave items across columns,
    placing 'Line 23' in column 0 at a different row index.
    """
    f = _font18()
    rect = _rect(1248, 600)
    items = [f"Line {i}" for i in range(48)]
    res = flow_columns(items, f, rect, line_gap=4)
    cols = column_plan(rect, f)
    assert len(cols) == 2
    # Every item in col 0 must come before every item in col 1 in the
    # original items list.  The last col-0 item is the one with the
    # highest original index among col-0 placements.
    col0_items = [p for p in res.placements if p[3] == 0]
    col1_items = [p for p in res.placements if p[3] == 1]
    assert len(col0_items) == 24  # column capacity
    assert len(col1_items) == 24
    # In column-major order, the last item placed in col 0 is item 23
    # and the first item in col 1 is item 24.
    col0_texts = [p[0] for p in col0_items]
    col1_texts = [p[0] for p in col1_items]
    assert col0_texts[-1] == "Line 23"
    assert col1_texts[0] == "Line 24"

def test_rule10_second_column_used():
    """With 48 items, both columns are used, and col 0 is full before col 1 starts."""
    f = _font18()
    rect = _rect(1248, 600)
    items = [f"Line {i}" for i in range(48)]
    res = flow_columns(items, f, rect, line_gap=4)
    cols = column_plan(rect, f)
    assert len(cols) == 2
    ci_values = set(p[3] for p in res.placements)
    assert 0 in ci_values
    assert 1 in ci_values
    # Verify col 0 fills completely before col 1 — items 0-23 in col 0, 24-47 in col 1
    col0_indices = sorted([int(p[0].split()[-1]) for p in res.placements if p[3] == 0])
    col1_indices = sorted([int(p[0].split()[-1]) for p in res.placements if p[3] == 1])
    assert col0_indices == list(range(24))
    assert col1_indices == list(range(24, 48))

def test_rule10_rows_increasing_within_column():
    """Within each column, items appear in original order (item 0 before item 1, etc.).

    Uses 48 items so both columns are populated.  In each column the text
    labels must be in ascending index order — a round-robin fill would place
    them out of original order within a column.
    """
    f = _font18()
    rect = _rect(1248, 600)
    items = [f"Line {i}" for i in range(48)]
    res = flow_columns(items, f, rect, line_gap=4)
    cols = column_plan(rect, f)
    line_h = f.size("x")[1]
    for ci in range(len(cols)):
        placements = [p for p in res.placements if p[3] == ci]
        ys = [p[2] for p in placements]
        for i in range(len(ys) - 1):
            assert ys[i] + line_h <= ys[i + 1]
        # Items must appear in original order within the column
        texts = [p[0] for p in placements]
        indices = [int(t.split()[-1]) for t in texts]
        assert indices == sorted(indices)


# ────────────────────────────────────────────────────────────────────────────
# Rule 11: overflow count correct
# ────────────────────────────────────────────────────────────────────────────

def test_rule11_overflow_zero():
    f = _font18()
    rect = _rect(1248, 600)
    items = [f"Line {i}" for i in range(13)]
    res = flow_columns(items, f, rect, line_gap=4)
    assert res.overflow == 0

def test_rule11_overflow_positive():
    f = _font18()
    rect = _rect(1248, 100)
    items = [f"Line {i}" for i in range(50)]
    res = flow_columns(items, f, rect, line_gap=4)
    assert res.overflow > 0

def test_rule11_overflow_equals_unplaced():
    f = _font18()
    rect = _rect(1248, 100)
    items = [f"Line {i}" for i in range(50)]
    res = flow_columns(items, f, rect, line_gap=4)
    placed_lines = len(res.placements)
    assert res.overflow == len(items) - placed_lines


# ────────────────────────────────────────────────────────────────────────────
# Rule 12: continuation marker
# ────────────────────────────────────────────────────────────────────────────

def test_rule12_continuation_marker(monkeypatch):
    """When there is overflow, _draw_paper must render a continuation marker in FADED.

    Monkeypatch compose to return a stub report with 200 synthetic items so the
    body overflows.  Call _draw_paper directly on a 1280x900 surface.  Count
    pixels of EXACTLY FADED (96,88,78) in the content rect.  Production code
    uses FADED only for the continuation marker, so a zero-overflow page
    produces exactly 0 such pixels.
    """

    class StubReport:
        year = 1066
        gazette = [f"Overflow item {i}" for i in range(200)]
        ledger = [""]
        letters = [""]

    monkeypatch.setattr("gilded.papers.compose", lambda *a, **k: StubReport())
    monkeypatch.setattr("gilded.ui.broadsheet.compose", lambda *a, **k: StubReport())

    s = pygame.display.set_mode((1280, 900))
    hud_h = _hud_height()
    content = pygame.Rect(0, TAB_H + hud_h, 1280, 900 - TAB_H - hud_h - BOTTOM_H)

    g = _game(seed=7, turns=1)
    house = list(g.houses.keys())[0]
    v = BroadsheetView(g, house)
    v.active_tab = "Gazette"
    s.fill(PAPER_BG)
    v._draw_paper(s, content)

    buf = pygame.image.tobytes(s, "RGB")
    faded_r, faded_g, faded_b = FADED
    faded_count = 0
    pw = 1280
    for y in range(content.y, content.bottom):
        for x in range(content.x, content.right):
            idx = (y * pw + x) * 3
            if buf[idx] == faded_r and buf[idx + 1] == faded_g and buf[idx + 2] == faded_b:
                faded_count += 1
    assert faded_count > 0, (
        f"Continuation marker should produce FADED pixels when overflow > 0, but found {faded_count}"
    )


def test_rule4_no_marker_when_no_overflow(monkeypatch):
    """R4: a page with a single short item produces zero FADED pixels.

    If the marker were drawn unconditionally (every page, overflow or not),
    this test would fail because FADED pixels would appear even with no overflow.
    """

    class StubReport:
        year = 1066
        gazette = ["Short item"]
        ledger = [""]
        letters = [""]

    monkeypatch.setattr("gilded.papers.compose", lambda *a, **k: StubReport())
    monkeypatch.setattr("gilded.ui.broadsheet.compose", lambda *a, **k: StubReport())

    s = pygame.display.set_mode((1280, 900))
    hud_h = _hud_height()
    content = pygame.Rect(0, TAB_H + hud_h, 1280, 900 - TAB_H - hud_h - BOTTOM_H)

    g = _game(seed=7, turns=1)
    house = list(g.houses.keys())[0]
    v = BroadsheetView(g, house)
    v.active_tab = "Gazette"
    s.fill(PAPER_BG)
    v._draw_paper(s, content)

    buf = pygame.image.tobytes(s, "RGB")
    faded_r, faded_g, faded_b = FADED
    faded_count = 0
    pw = 1280
    for y in range(content.y, content.bottom):
        for x in range(content.x, content.right):
            idx = (y * pw + x) * 3
            if buf[idx] == faded_r and buf[idx + 1] == faded_g and buf[idx + 2] == faded_b:
                faded_count += 1
    assert faded_count == 0, (
        f"No marker when overflow == 0, but found {faded_count} FADED pixels"
    )


# ────────────────────────────────────────────────────────────────────────────
# Rule 13: horizontal rule
# ────────────────────────────────────────────────────────────────────────────

def test_rule13_horizontal_rule_draws(monkeypatch):
    """R5: _draw_paper draws a page-spanning horizontal rule under the head.

    The rule row carries >= 1000 non-background pixels across the full width.
    Search band is derived from the head font height so the test survives a font change.
    """

    class StubReport:
        year = 1066
        gazette = ["Short item"]
        ledger = [""]
        letters = [""]

    monkeypatch.setattr("gilded.papers.compose", lambda *a, **k: StubReport())
    monkeypatch.setattr("gilded.ui.broadsheet.compose", lambda *a, **k: StubReport())

    s = pygame.display.set_mode((1280, 900))
    hud_h = _hud_height()
    content = pygame.Rect(0, TAB_H + hud_h, 1280, 900 - TAB_H - hud_h - BOTTOM_H)

    head_font = _font(30, bold=True)
    head_h = head_font.size("Ag")[1]

    g = _game(seed=7, turns=1)
    house = list(g.houses.keys())[0]
    v = BroadsheetView(g, house)
    v.active_tab = "Gazette"
    s.fill(PAPER_BG)
    v._draw_paper(s, content)

    # Derive search band from head font height: rule_y = content.y + 6 + head_h + 4
    # Search a band of 20 pixels around that y
    expected_rule_y = content.y + 6 + head_h + 4
    search_start = expected_rule_y - 10
    search_end = expected_rule_y + 10

    buf = pygame.image.tobytes(s, "RGB")
    pw = 1280
    best_y = None
    best_count = 0
    for y in range(search_start, search_end):
        if y < 0 or y >= 900:
            continue
        row_ink = 0
        for x in range(content.x, content.right):
            idx = (y * pw + x) * 3
            r, g, b = buf[idx], buf[idx + 1], buf[idx + 2]
            if (r, g, b) != PAPER_BG:
                row_ink += 1
        if row_ink > best_count:
            best_count = row_ink
            best_y = y

    assert best_count >= 1000, (
        f"Horizontal rule row at y={best_y} has only {best_count} non-bg pixels (need >= 1000)"
    )


def test_rule6_horizontal_rule_thickness(monkeypatch):
    """R6: the horizontal rule is exactly 1 pixel thick.

    The rows immediately above and below the rule row carry zero non-background
    pixels in the horizontal span of the rule.
    """

    class StubReport:
        year = 1066
        gazette = ["Short item"]
        ledger = [""]
        letters = [""]

    monkeypatch.setattr("gilded.papers.compose", lambda *a, **k: StubReport())
    monkeypatch.setattr("gilded.ui.broadsheet.compose", lambda *a, **k: StubReport())

    s = pygame.display.set_mode((1280, 900))
    hud_h = _hud_height()
    content = pygame.Rect(0, TAB_H + hud_h, 1280, 900 - TAB_H - hud_h - BOTTOM_H)

    head_font = _font(30, bold=True)
    head_h = head_font.size("Ag")[1]

    g = _game(seed=7, turns=1)
    house = list(g.houses.keys())[0]
    v = BroadsheetView(g, house)
    v.active_tab = "Gazette"
    s.fill(PAPER_BG)
    v._draw_paper(s, content)

    buf = pygame.image.tobytes(s, "RGB")
    pw = 1280
    expected_rule_y = content.y + 6 + head_h + 4

    # Count non-bg pixels in the row above and below the rule
    for offset in (-1, 1):
        y = expected_rule_y + offset
        if y < 0 or y >= 900:
            continue
        row_ink = 0
        for x in range(PAD, content.right - PAD):
            idx = (y * pw + x) * 3
            r, g, b = buf[idx], buf[idx + 1], buf[idx + 2]
            if (r, g, b) != PAPER_BG:
                row_ink += 1
        assert row_ink == 0, (
            f"Row y={y} (offset {offset} from rule) has {row_ink} non-bg pixels — rule is too thick"
        )


# ────────────────────────────────────────────────────────────────────────────
# Rule 14: _draw_paper renders without error at 1280x900 and 800x600
# ────────────────────────────────────────────────────────────────────────────

def test_rule14_no_error_1280x900_seed7():
    g = _game(seed=7, turns=1)
    s = pygame.display.set_mode((1280, 900))
    v = BroadsheetView(g, list(g.houses.keys())[0])
    for tab in ("Gazette", "Ledger", "Letters"):
        v.active_tab = tab
        v.draw(s)

def test_rule14_no_error_800x600_seed7():
    g = _game(seed=7, turns=1)
    s = pygame.display.set_mode((800, 600))
    v = BroadsheetView(g, list(g.houses.keys())[0])
    for tab in ("Gazette", "Ledger", "Letters"):
        v.active_tab = tab
        v.draw(s)

def test_rule14_no_error_1280x900_seed42():
    g = _game(seed=42, turns=1)
    s = pygame.display.set_mode((1280, 900))
    v = BroadsheetView(g, list(g.houses.keys())[0])
    for tab in ("Gazette", "Ledger", "Letters"):
        v.active_tab = tab
        v.draw(s)

def test_rule14_no_error_800x600_seed42():
    g = _game(seed=42, turns=1)
    s = pygame.display.set_mode((800, 600))
    v = BroadsheetView(g, list(g.houses.keys())[0])
    for tab in ("Gazette", "Ledger", "Letters"):
        v.active_tab = tab
        v.draw(s)


# ────────────────────────────────────────────────────────────────────────────
# Rule 15: papers.py unchanged
# ────────────────────────────────────────────────────────────────────────────

def test_rule15_papers_wrap_width():
    assert WRAP_WIDTH == 72


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
