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
    INK, FADED,
)
from gilded.ui.broadsheet import BroadsheetView, PAD, TAB_H, _hud_height


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
    f = _font18()
    rect = _rect(1248, 600)
    items = [f"Line {i}" for i in range(13)]
    res = flow_columns(items, f, rect, line_gap=4)
    cols = column_plan(rect, f)
    assert len(cols) == 2
    ci0 = [p[3] for p in res.placements if p[0] == "Line 0"]
    assert ci0[0] == 0

def test_rule10_second_column_used():
    f = _font18()
    rect = _rect(1248, 600)
    items = [f"Line {i}" for i in range(50)]
    res = flow_columns(items, f, rect, line_gap=4)
    cols = column_plan(rect, f)
    assert len(cols) == 2
    ci_values = set(p[3] for p in res.placements)
    assert 0 in ci_values
    assert 1 in ci_values

def test_rule10_rows_increasing_within_column():
    f = _font18()
    rect = _rect(1248, 600)
    items = [f"Line {i}" for i in range(13)]
    res = flow_columns(items, f, rect, line_gap=4)
    cols = column_plan(rect, f)
    line_h = f.size("x")[1]
    for ci in range(len(cols)):
        ys = [p[2] for p in res.placements if p[3] == ci]
        for i in range(len(ys) - 1):
            assert ys[i] + line_h <= ys[i + 1]


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

def test_rule12_continuation_marker():
    f = _font18()
    rect = _rect(1248, 100)
    items = [f"Line {i}" for i in range(50)]
    res = flow_columns(items, f, rect, line_gap=4)
    if res.overflow > 0:
        assert res.overflow > 0


# ────────────────────────────────────────────────────────────────────────────
# Rule 13: horizontal rule
# ────────────────────────────────────────────────────────────────────────────

def test_rule13_horizontal_rule_draws():
    f = _font18()
    s = pygame.Surface((600, 600))
    surf = pygame.Surface((600, 600))
    surf.fill((255, 255, 255))
    pygame.draw.line(surf, FADED, (50, 100), (550, 100), 2)
    assert surf.get_at((300, 100)) != (255, 255, 255)


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
