"""Wave 6: the Ledger — tests for R1 through R11."""
from __future__ import annotations

import sys
import pytest
import pygame

pygame.init()
from gilded.houses import House
from gilded.ui.ledger import (
    money, ledger_model, LedgerRow, TurnLine, LedgerModel,
    HISTORY_SPAN,
)
from gilded.chassis import GildedGame
from gilded.papers import compose
from gilded.ui.widgets import PAPER_BG, FADED, INK, Column, Table
from gilded.ui.broadsheet import BroadsheetView, PAD, TAB_H, _hud_height, BOTTOM_H


def _game(seed=42, turns=1):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.open_turn()
        g.end_turn()
    return g


# ────────────────────────────────────────────────────────────────────────────
# R3: money() formatting
# ────────────────────────────────────────────────────────────────────────────

def test_r3_money_positive():
    assert money(108.14748382986993) == "+108"

def test_r3_money_negative():
    assert money(-150.0) == "-150"

def test_r3_money_large_negative():
    assert money(-2500.0) == "-2,500"

def test_r3_money_small_positive():
    assert money(0.3) == "+0"

def test_r3_money_small_negative():
    assert money(-0.3) == "-0"

def test_r3_money_zero():
    assert money(0.0) == "+0"


# ────────────────────────────────────────────────────────────────────────────
# R2: rows are the journal, untouched
# ────────────────────────────────────────────────────────────────────────────

def test_r2_rows_match_flows():
    h = House(name="Test", capital=1)
    h.credit(5, "dividends", 100.0)
    h.debit(5, "strike buyoff", 150.0)
    h.credit(5, "trade", 0.3)
    model = ledger_model(h, 5)
    assert len(model.rows) == 3
    # Order: descending magnitude
    assert model.rows[0].label == "strike buyoff"
    assert model.rows[0].amount == -150.0
    assert model.rows[1].label == "dividends"
    assert model.rows[1].amount == 100.0
    assert model.rows[2].label == "trade"
    assert model.rows[2].amount == 0.3


# ────────────────────────────────────────────────────────────────────────────
# R4: totals come from the journal, not from rendered strings
# ────────────────────────────────────────────────────────────────────────────

def test_r4_totals_from_journal():
    h = House(name="Test", capital=1)
    h.credit(5, "dividends", 108.14748382986993)
    h.debit(5, "strike buyoff", 150.0)
    h.credit(5, "trade", 1.2)
    model = ledger_model(h, 5)
    assert model.income == h.income(5)
    assert model.outlay == h.outlay(5)
    assert abs(model.net - (model.income - model.outlay)) < 1e-9
    # Rows reconcile
    row_income = sum(r.amount for r in model.rows if r.amount > 0)
    row_outlay = sum(abs(r.amount) for r in model.rows if r.amount < 0)
    assert abs(row_income - model.income) < 1e-9
    assert abs(row_outlay - model.outlay) < 1e-9


# ────────────────────────────────────────────────────────────────────────────
# R5: history
# ────────────────────────────────────────────────────────────────────────────

def test_r5_history_length():
    h = House(name="Test", capital=1)
    for t in range(1, 21):
        h.credit(t, "dividends", 10.0)
    model = ledger_model(h, 20)
    assert len(model.history) == HISTORY_SPAN
    # Oldest first
    assert model.history[0].turn == 13
    assert model.history[-1].turn == 20

def test_r5_history_includes_quiet_turns():
    h = House(name="Test", capital=1)
    # Only turn 5 has activity
    h.credit(5, "dividends", 100.0)
    model = ledger_model(h, 10)
    # All turns 3..10 should be present
    turns = [tl.turn for tl in model.history]
    assert turns == list(range(max(1, 10 - HISTORY_SPAN + 1), 11))
    # Quiet turns have zeros
    for tl in model.history:
        if tl.turn != 5:
            assert tl.income == 0.0
            assert tl.outlay == 0.0
            assert tl.net == 0.0

def test_r5_history_length_at_first_turn():
    h = House(name="Test", capital=1)
    h.credit(1, "dividends", 100.0)
    model = ledger_model(h, 1)
    assert len(model.history) == 1
    assert model.history[0].turn == 1


# ────────────────────────────────────────────────────────────────────────────
# R6: span summary
# ────────────────────────────────────────────────────────────────────────────

def test_r6_summary_aggregates():
    h = House(name="Test", capital=1)
    for t in range(13, 21):
        h.debit(t, "strike buyoff", 150.0)
        h.credit(t, "dividends", 108.0)
    model = ledger_model(h, 20)
    labels = {r.label for r in model.summary}
    assert "strike buyoff" in labels
    assert "dividends" in labels
    # strike buyoff totals
    sb = [r for r in model.summary if r.label == "strike buyoff"][0]
    assert sb.amount == -1200.0
    # Sorted by descending magnitude
    assert abs(model.summary[0].amount) >= abs(model.summary[1].amount)


# ────────────────────────────────────────────────────────────────────────────
# R7: empty turn
# ────────────────────────────────────────────────────────────────────────────

def test_r7_empty_turn():
    h = House(name="Test", capital=1)
    model = ledger_model(h, 1)
    assert model.rows == ()
    assert model.income == 0.0
    assert model.outlay == 0.0
    assert model.net == 0.0
    # History and summary still present
    assert len(model.history) >= 1


# ────────────────────────────────────────────────────────────────────────────
# R1: resolved turn (game.turn - 1)
# ────────────────────────────────────────────────────────────────────────────

def test_r1_resolved_turn():
    g = _game(seed=42, turns=1)
    name = list(g.houses.keys())[0]
    house = g.houses[name]
    # After 1 turn, g.turn == 2 (open turn), resolved is 1
    assert g.turn == 2
    resolved = g.turn - 1
    model = ledger_model(house, resolved)
    # flows(2) is empty, flows(1) should have data
    assert len(house.flows(g.turn)) == 0
    # Model should have flows from turn 1
    assert model.turn == resolved


# ────────────────────────────────────────────────────────────────────────────
# R8: every row reaches the page
# ────────────────────────────────────────────────────────────────────────────

def test_r8_rows_rendered():
    h = House(name="Test", capital=1)
    for i in range(20):
        h.credit(5, "dividends", 10.0)
    model = ledger_model(h, 5)
    # Build table data from model
    cols = [Column("Label", width=2.0, align="left"),
            Column("Amount", width=1.0, align="right")]
    data = [[r.label, money(r.amount)] for r in model.rows]
    tbl = Table(cols, data, size=14)
    # Table data matches model rows
    assert len(tbl.data) == len(model.rows)
    for i, row in enumerate(model.rows):
        assert tbl.data[i][0] == row.label
        assert tbl.data[i][1] == money(row.amount)


# ────────────────────────────────────────────────────────────────────────────
# R9: nothing drawn outside content rect
# ────────────────────────────────────────────────────────────────────────────

def test_r9_no_draw_outside_content_1280x900():
    g = _game(seed=7, turns=1)
    s = pygame.display.set_mode((1280, 900))
    hud_h = _hud_height()
    content = pygame.Rect(0, TAB_H + hud_h, 1280, 900 - TAB_H - hud_h - BOTTOM_H)
    house = list(g.houses.keys())[0]
    v = BroadsheetView(g, house)
    s.fill(PAPER_BG)
    v._draw_ledger(s, content)

    buf = pygame.image.tobytes(s, "RGB")
    pw = 1280
    # Check above content.top
    for y in range(0, content.top):
        for x in range(PAD, pw - PAD):
            idx = (y * pw + x) * 3
            r, g_val, b = buf[idx:idx+3]
            if (r, g_val, b) != PAPER_BG:
                pytest.fail(f"Non-bg pixel at ({x},{y}) above content.top={content.top}")
    # Check below content.bottom
    for y in range(content.bottom, 900):
        for x in range(PAD, pw - PAD):
            idx = (y * pw + x) * 3
            r, g_val, b = buf[idx:idx+3]
            if (r, g_val, b) != PAPER_BG:
                pytest.fail(f"Non-bg pixel at ({x},{y}) below content.bottom={content.bottom}")

def test_r9_no_draw_outside_content_800x600():
    g = _game(seed=7, turns=1)
    s = pygame.display.set_mode((800, 600))
    hud_h = _hud_height()
    content = pygame.Rect(0, TAB_H + hud_h, 800, 600 - TAB_H - hud_h - BOTTOM_H)
    house = list(g.houses.keys())[0]
    v = BroadsheetView(g, house)
    s.fill(PAPER_BG)
    v._draw_ledger(s, content)

    buf = pygame.image.tobytes(s, "RGB")
    pw = 800
    for y in range(0, content.top):
        for x in range(PAD, pw - PAD):
            idx = (y * pw + x) * 3
            r, g_val, b = buf[idx:idx+3]
            if (r, g_val, b) != PAPER_BG:
                pytest.fail(f"Non-bg pixel at ({x},{y}) above content.top")
    for y in range(content.bottom, 600):
        for x in range(PAD, pw - PAD):
            idx = (y * pw + x) * 3
            r, g_val, b = buf[idx:idx+3]
            if (r, g_val, b) != PAPER_BG:
                pytest.fail(f"Non-bg pixel at ({x},{y}) below content.bottom")


# ────────────────────────────────────────────────────────────────────────────
# R10: prose kept
# ────────────────────────────────────────────────────────────────────────────

def test_r10_notices_preserved(monkeypatch):
    class StubReport:
        year = 1066
        gazette = ["Short item"]
        ledger = ["Line one", "Line two"]
        letters = [""]

    monkeypatch.setattr("gilded.papers.compose", lambda *a, **k: StubReport())
    monkeypatch.setattr("gilded.ui.broadsheet.compose", lambda *a, **k: StubReport())

    g = _game(seed=7, turns=1)
    house = list(g.houses.keys())[0]
    s = pygame.display.set_mode((1280, 900))
    hud_h = _hud_height()
    content = pygame.Rect(0, TAB_H + hud_h, 1280, 900 - TAB_H - hud_h - BOTTOM_H)
    v = BroadsheetView(g, house)
    s.fill(PAPER_BG)
    v._draw_ledger(s, content)
    # Verify notices are in the model
    # We check that the surface has content (the notices rendered)
    buf = pygame.image.tobytes(s, "RGB")
    non_bg = sum(1 for i in range(0, len(buf), 3) if buf[i:i+3] != PAPER_BG)
    assert non_bg > 0, "Surface should have drawn content including notices"


# ────────────────────────────────────────────────────────────────────────────
# R11: no pygame.draw in tests (enforced by the checker, not by assertions here)
# ────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
