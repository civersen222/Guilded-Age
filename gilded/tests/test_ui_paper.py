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

def test_rule12_continuation_marker():
    """When there is overflow, _draw_paper must render a continuation marker.

    Uses a tall game (10 turns) for more content, and a surface short enough
    that the body area is only 30px, forcing overflow.  Then probes for
    non-background pixels in the marker region (which would not be there if
    the `if result.overflow > 0:` block were deleted).
    """
    g = _game(seed=7, turns=10)
    hud_h = _hud_height()
    body_font = _font18()
    head_font = _font(30, bold=True)
    house = list(g.houses.keys())[0]

    # Compute where the body area starts
    head = head_font.render("THE GAZETTE - 1066", True, INK)
    rule_y = TAB_H + hud_h + 6 + head.get_height() + 4
    body_top = rule_y + 6

    # Surface height gives body area of 30px (fits ~1 line, forcing overflow)
    body_h = 30
    short_h = body_top + body_h + BOTTOM_H
    s = pygame.display.set_mode((1280, short_h))

    v = BroadsheetView(g, house)
    v.active_tab = "Gazette"
    v.draw(s)

    # content.bottom = TAB_H + hud_h + (short_h - TAB_H - hud_h - BOTTOM_H) = short_h - BOTTOM_H
    content_bottom = short_h - BOTTOM_H

    # The marker is placed at content.bottom - marker_height - 8
    marker_h = body_font.size("+ 6 more")[1]
    marker_y = content_bottom - marker_h - 8

    # Probe for non-PAPER_BG pixels in the marker region
    from gilded.ui.widgets import PAPER_BG
    non_bg = 0
    for y in range(marker_y - 2, content_bottom):
        for x in range(PAD + 5, min(PAD + 150, 1200)):
            if s.get_at((x, y)) != PAPER_BG:
                non_bg += 1
    assert non_bg > 20, (
        f"No continuation marker found: only {non_bg} non-bg pixels "
        f"near y={marker_y}-{content_bottom}"
    )


# ────────────────────────────────────────────────────────────────────────────
# Rule 13: horizontal rule
# ────────────────────────────────────────────────────────────────────────────

def test_rule13_horizontal_rule_draws():
    """_draw_paper must draw a horizontal rule (pygame.draw.line) under the head.

    Renders the broadsheet and probes for a dark horizontal line just below
    the head text.  The rule colour is INK (28, 24, 20).
    """
    g = _game(seed=7, turns=1)
    s = pygame.display.set_mode((1280, 900))
    house = list(g.houses.keys())[0]
    v = BroadsheetView(g, house)
    v.active_tab = "Gazette"
    v.draw(s)
    head_font = _font(30, bold=True)
    head_text = head_font.render(f"THE GAZETTE - 1066", True, INK)
    # _draw_paper: rule_y = content.y + 6 + head_height + 4, where content.y = TAB_H + hud_h
    hud_h = _hud_height()
    rule_y = TAB_H + hud_h + 6 + head_text.get_height() + 4
    # Probe for INK-colored pixels on the rule line
    ink_pixels = 0
    for x in range(PAD + 10, min(PAD + 300, 1280 - PAD)):
        col = s.get_at((x, rule_y))
        if col == INK:
            ink_pixels += 1
    assert ink_pixels > 50, f"Horizontal rule not found: only {ink_pixels} ink pixels at y={rule_y}"


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
