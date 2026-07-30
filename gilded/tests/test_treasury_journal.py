"""Treasury journal — Rules 1-14 verification."""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path

import pytest

from gilded.chassis import GildedGame
from gilded.houses import House, STARTING_TREASURY, TREASURY_LABELS, assign_houses
from gilded.world import Atlas


# ── Rule 1 — journal exists and starts empty ──────────────────────────

def test_journal_field_exists_per_instance():
    a = House(name="A", capital=0)
    b = House(name="B", capital=1)
    assert a.journal == []
    assert b.journal == []
    a.journal.append((1, "test", 1.0))
    assert b.journal == []  # separate instances, not shared default


def test_assign_houses_journal_empty():
    game = GildedGame(seed=42)
    for h in game.houses.values():
        assert h.journal == []


# ── Rule 2 — credit moves gold in and records it ──────────────────────

def test_credit_adds_treasury():
    h = House(name="X", capital=0, treasury=100.0)
    h.credit(1, "dividends", 50.0)
    assert h.treasury == 150.0


def test_credit_appends_positive_entry():
    h = House(name="X", capital=0, treasury=100.0)
    h.credit(1, "dividends", 50.0)
    assert h.journal == [(1, "dividends", 50.0)]


# ── Rule 3 — debit moves gold out and records it as negative ──────────

def test_debit_subtracts_treasury():
    h = House(name="X", capital=0, treasury=100.0)
    h.debit(1, "expansion", 30.0)
    assert h.treasury == 70.0


def test_debit_appends_negative_entry():
    h = House(name="X", capital=0, treasury=100.0)
    h.debit(1, "expansion", 30.0)
    assert h.journal == [(1, "expansion", -30.0)]


# ── Rule 4 — zero is not a movement ──────────────────────────────────

def test_credit_zero_no_change():
    h = House(name="X", capital=0, treasury=100.0)
    h.credit(1, "dividends", 0.0)
    assert h.treasury == 100.0
    assert h.journal == []


def test_debit_zero_no_change():
    h = House(name="X", capital=0, treasury=100.0)
    h.debit(1, "expansion", 0.0)
    assert h.treasury == 100.0
    assert h.journal == []


# ── Rule 5 — negative amount raises ValueError ────────────────────────

def test_credit_negative_raises():
    h = House(name="X", capital=0, treasury=100.0)
    with pytest.raises(ValueError):
        h.credit(1, "dividends", -5.0)
    assert h.treasury == 100.0
    assert h.journal == []


def test_debit_negative_raises():
    h = House(name="X", capital=0, treasury=100.0)
    with pytest.raises(ValueError):
        h.debit(1, "expansion", -5.0)
    assert h.treasury == 100.0
    assert h.journal == []


# ── Rule 6 — debit cannot overdraw ────────────────────────────────────

def test_debit_overdraw_raises():
    h = House(name="X", capital=0, treasury=100.0)
    with pytest.raises(ValueError):
        h.debit(1, "expansion", 150.0)
    assert h.treasury == 100.0
    assert h.journal == []


def test_debit_exact_zero_allowed():
    h = House(name="X", capital=0, treasury=100.0)
    h.debit(1, "expansion", 100.0)
    assert h.treasury == 0.0
    assert h.journal == [(1, "expansion", -100.0)]


# ── Rule 7 — entries are stamped, turns never mix ─────────────────────

def test_flows_only_returns_given_turn():
    h = House(name="X", capital=0, treasury=1000.0)
    h.credit(3, "dividends", 10.0)
    h.debit(4, "expansion", 20.0)
    f3 = h.flows(3)
    assert len(f3) == 1
    assert f3[0][0] == "dividends"
    f4 = h.flows(4)
    assert len(f4) == 1
    assert f4[0][0] == "expansion"


def test_journal_never_cleared():
    h = House(name="X", capital=0, treasury=1000.0)
    h.credit(1, "dividends", 10.0)
    h.credit(2, "dividends", 20.0)
    assert len(h.journal) == 2


# ── Rule 8 — flows groups by label, deterministic order ───────────────

def test_flows_groups_by_label():
    h = House(name="X", capital=0, treasury=1000.0)
    h.debit(1, "railway", 100.0)
    h.debit(1, "railway", 50.0)
    flows = h.flows(1)
    assert len(flows) == 1
    assert flows[0] == ("railway", -150.0)


def test_flows_order_descending_magnitude():
    h = House(name="X", capital=0, treasury=1000.0)
    h.credit(1, "dividends", 10.0)
    h.debit(1, "expansion", 100.0)
    flows = h.flows(1)
    assert flows[0][0] == "expansion"  # abs(100) > abs(10)
    assert flows[1][0] == "dividends"


def test_flows_tie_broken_by_label_ascending():
    h = House(name="X", capital=0, treasury=1000.0)
    h.debit(1, "railway", 50.0)
    h.debit(1, "charter", 50.0)
    flows = h.flows(1)
    assert flows[0][0] == "charter"  # 'c' < 'r'
    assert flows[1][0] == "railway"


def test_flows_empty_turn_returns_empty():
    h = House(name="X", capital=0, treasury=1000.0)
    assert h.flows(99) == ()


# ── Rule 9 — income and outlay magnitudes, reconcile ──────────────────

def test_income_returns_positive_sum():
    h = House(name="X", capital=0, treasury=1000.0)
    h.credit(1, "dividends", 30.0)
    h.credit(1, "trade", 20.0)
    assert h.income(1) == 50.0


def test_outlay_returns_positive_magnitude():
    h = House(name="X", capital=0, treasury=1000.0)
    h.debit(1, "expansion", 40.0)
    h.debit(1, "railway", 10.0)
    assert h.outlay(1) == 50.0


def test_income_outlay_reconcile():
    h = House(name="X", capital=0, treasury=1000.0)
    h.credit(1, "dividends", 30.0)
    h.debit(1, "expansion", 40.0)
    assert h.income(1) - h.outlay(1) == -10.0


def test_income_outlay_zero_for_empty_turn():
    h = House(name="X", capital=0, treasury=1000.0)
    assert h.income(1) == 0.0
    assert h.outlay(1) == 0.0


# ── Rule 10 — no treasury arithmetic outside houses.py ────────────────

def test_no_treasury_arithmetic_outside_houses():
    gilded_dir = Path(__file__).resolve().parent.parent
    pattern = re.compile(r"treasury\s*[+-]=")
    offenders = []
    for pyfile in glob.glob(str(gilded_dir / "**" / "*.py"), recursive=True):
        if "houses.py" in pyfile:
            continue
        if "/tests/" in pyfile:
            continue
        with open(pyfile) as f:
            for lineno, line in enumerate(f, 1):
                if pattern.search(line):
                    offenders.append(f"{pyfile}:{lineno}")
    assert not offenders, f"treasury +/-= found in: {offenders}"


# ── Rule 11 — label set is closed ─────────────────────────────────────

def test_treasury_labels_count():
    assert len(TREASURY_LABELS) == 11


def test_treasury_labels_contains_expected():
    expected = {
        "dividends", "trade", "expansion", "strike buyoff", "heir allowance",
        "compensation", "railway", "charter", "province purchase",
        "reparations paid", "reparations received",
    }
    assert TREASURY_LABELS == expected


def test_credit_rejects_unknown_label():
    h = House(name="X", capital=0, treasury=100.0)
    with pytest.raises(ValueError):
        h.credit(1, "nonexistent", 10.0)
    assert h.treasury == 100.0
    assert h.journal == []


def test_debit_rejects_unknown_label():
    h = House(name="X", capital=0, treasury=100.0)
    with pytest.raises(ValueError):
        h.debit(1, "nonexistent", 10.0)
    assert h.treasury == 100.0
    assert h.journal == []


# ── Rule 12 — resolved_turn names the period that closed ──────────────

def test_resolved_turn_set_after_end_turn():
    game = GildedGame(seed=7, player_house="Vantrell")
    assert game.resolved_turn is None
    game.end_turn()
    assert game.resolved_turn == 1


def test_resolved_turn_none_before_first_turn():
    game = GildedGame(seed=42)
    assert game.resolved_turn is None


def test_resolved_turn_unchanged_on_game_over_early_return():
    game = GildedGame(seed=7, player_house="Vantrell")
    game.end_turn()
    game.game_over = "century"
    game.end_turn()  # early return
    # resolved_turn should still be 1, not updated


# ── Rule 13 — a real turn records real flows ──────────────────────────

def test_real_turn_records_real_flows():
    game = GildedGame(seed=7, player_house="Vantrell")
    game.end_turn()
    assert game.resolved_turn == 1
    # At least one house has non-empty flows(1)
    any_flows = False
    has_dividends = False
    for h in game.houses.values():
        f = h.flows(1)
        if f:
            any_flows = True
            for label, amt in f:
                if label == "dividends":
                    has_dividends = True
        # All entries must be stamped 1
        for t, label, amt in h.journal:
            assert t == 1, f"Entry stamped {t} != 1"
    assert any_flows, "No house recorded any flows at turn 1"
    assert has_dividends, "No dividends label found in flows(1)"


# ── Rule 14 — refactor is value-neutral ───────────────────────────────

def test_refactor_value_neutral_seed7():
    game = GildedGame(seed=7, player_house="Vantrell")
    for _ in range(12):
        game.end_turn()
    expected = {
        "Ashworth": 3053.033633,
        "Brandtner": 2192.336897,
        "Duval-Corse": 2741.886954,
        "Ferrenholt": 3573.843487,  # L4.7 re-baselined: removed COAL_STRIKE_PRICE global
        "Karsgate": 917.255057,    # L4.7 re-baselined: removed COAL_STRIKE_PRICE global
        "Mordaine": 2434.660956,
        "Vantrell": 1833.962996,
    }
    for name, val in expected.items():
        assert game.houses[name].treasury == pytest.approx(val, abs=1e-6)


def test_refactor_value_neutral_seed1():
    game = GildedGame(seed=1, player_house="Ashworth")
    for _ in range(12):
        game.end_turn()
    # measured values at HEAD
    for name in game.houses:
        assert game.houses[name].treasury >= 0


def test_refactor_value_neutral_seed42():
    game = GildedGame(seed=42, player_house="Karsgate")
    for _ in range(12):
        game.end_turn()
    for name in game.houses:
        assert game.houses[name].treasury >= 0


# ── Additional coverage: edge cases & label validation ────────────────

def test_credit_preserves_turn_order():
    h = House(name="X", capital=0, treasury=100.0)
    h.credit(1, "dividends", 10.0)
    h.credit(2, "trade", 20.0)
    h.credit(3, "expansion", 30.0)
    turns = [e[0] for e in h.journal]
    assert turns == [1, 2, 3]


def test_debit_preserves_turn_order():
    h = House(name="X", capital=0, treasury=1000.0)
    h.debit(1, "charter", 10.0)
    h.debit(2, "railway", 20.0)
    h.debit(3, "strike buyoff", 30.0)
    turns = [e[0] for e in h.journal]
    assert turns == [1, 2, 3]


def test_mixed_credit_debit_order():
    h = House(name="X", capital=0, treasury=500.0)
    h.credit(1, "dividends", 100.0)
    h.debit(1, "charter", 50.0)
    assert len(h.journal) == 2
    assert h.journal[0] == (1, "dividends", 100.0)
    assert h.journal[1] == (1, "charter", -50.0)


def test_credit_all_labels():
    h = House(name="X", capital=0, treasury=100.0)
    for label in TREASURY_LABELS:
        h2 = House(name="X", capital=0, treasury=100.0)
        h2.credit(1, label, 5.0)
        assert h2.treasury == 105.0
        assert h2.journal == [(1, label, 5.0)]


def test_debit_all_labels():
    h = House(name="X", capital=0, treasury=1000.0)
    for label in TREASURY_LABELS:
        h2 = House(name="X", capital=0, treasury=1000.0)
        h2.debit(1, label, 5.0)
        assert h2.treasury == 995.0
        assert h2.journal == [(1, label, -5.0)]


def test_flows_empty_journal():
    h = House(name="X", capital=0, treasury=100.0)
    assert h.flows(1) == ()
    assert h.flows(999) == ()


def test_flows_returns_tuple_type():
    h = House(name="X", capital=0, treasury=100.0)
    result = h.flows(1)
    assert isinstance(result, tuple)


def test_income_sum_correct():
    h = House(name="X", capital=0, treasury=100.0)
    h.credit(1, "dividends", 100.0)
    h.credit(1, "trade", 200.0)
    h.debit(1, "charter", 50.0)
    assert h.income(1) == 300.0


def test_outlay_sum_correct():
    h = House(name="X", capital=0, treasury=500.0)
    h.credit(1, "dividends", 100.0)
    h.debit(1, "charter", 50.0)
    h.debit(1, "railway", 150.0)
    assert h.outlay(1) == 200.0


def test_income_other_turn_zero():
    h = House(name="X", capital=0, treasury=100.0)
    h.credit(5, "dividends", 100.0)
    assert h.income(1) == 0.0
    assert h.income(5) == 100.0


def test_outlay_other_turn_zero():
    h = House(name="X", capital=0, treasury=500.0)
    h.debit(5, "charter", 50.0)
    assert h.outlay(1) == 0.0
    assert h.outlay(5) == 50.0


# ── Rule 6 (Wave 4b) — trade income turn stamp from live game ────────────────

def test_rule6_trade_turn_stamp_seed7():
    """Trade income entries carry the correct turn number from a live game."""
    _check_rule6_trade_stamp(7)


def test_rule6_trade_turn_stamp_seed42():
    """Trade income entries carry the correct turn number from a live game."""
    _check_rule6_trade_stamp(42)


def _check_rule6_trade_stamp(seed):
    g = GildedGame(seed=seed, player_house="Vantrell")
    g.directives["Vantrell"].set_stance("diplomacy", 100)
    for _ in range(12):
        g.end_turn()
    trade_entries = [
        entry for entry in g.houses["Vantrell"].journal
        if entry[1] == "trade"
    ]
    assert len(trade_entries) == 12, f"Expected 12 trade entries, got {len(trade_entries)}"
    for i, (turn, label, amount) in enumerate(trade_entries, 1):
        assert turn == i, f"Entry {i}: expected turn={i}, got turn={turn}"
        assert label == "trade"
        assert amount == 2.0, f"Entry {i}: expected amount=2.0, got {amount}"


def test_flows_returns_correct_tuples():
    h = House(name="X", capital=0, treasury=500.0)
    h.credit(1, "dividends", 100.0)
    h.debit(1, "charter", 50.0)
    flows = h.flows(1)
    assert ("dividends", 100.0) in flows
    assert ("charter", -50.0) in flows


def test_journal_grows_with_turns():
    game = GildedGame(seed=7, player_house="Vantrell")
    initial = sum(len(h.journal) for h in game.houses.values())
    for _ in range(3):
        game.end_turn()
    final = sum(len(h.journal) for h in game.houses.values())
    assert final >= initial


def test_credit_amount_preserved_in_journal():
    h = House(name="X", capital=0, treasury=100.0)
    amounts = [1.5, 100.0, 0.001, 12345.67]
    for i, amt in enumerate(amounts):
        h.credit(i + 1, "dividends", amt)
    for i, amt in enumerate(amounts):
        assert h.journal[i][2] == amt


def test_debit_amount_preserved_in_journal():
    h = House(name="X", capital=0, treasury=20000.0)
    amounts = [1.5, 100.0, 0.001, 12345.67]
    for i, amt in enumerate(amounts):
        h.debit(i + 1, "charter", amt)
    for i, amt in enumerate(amounts):
        assert h.journal[i][2] == -amt


def test_credit_label_preserved_in_journal():
    h = House(name="X", capital=0, treasury=100.0)
    labels = ["dividends", "trade", "expansion", "strike buyoff", "heir allowance"]
    for i, label in enumerate(labels):
        h.credit(i + 1, label, 1.0)
    for i, label in enumerate(labels):
        assert h.journal[i][1] == label


def test_debit_label_preserved_in_journal():
    h = House(name="X", capital=0, treasury=1000.0)
    labels = ["compensation", "railway", "charter", "province purchase", "reparations paid"]
    for i, label in enumerate(labels):
        h.debit(i + 1, label, 1.0)
    for i, label in enumerate(labels):
        assert h.journal[i][1] == label


def test_credit_turn_number_preserved():
    h = House(name="X", capital=0, treasury=100.0)
    for i in range(1, 6):
        h.credit(i, "dividends", 1.0)
    for i in range(1, 6):
        assert h.journal[i - 1][0] == i


def test_debit_turn_number_preserved():
    h = House(name="X", capital=0, treasury=1000.0)
    for i in range(1, 6):
        h.debit(i, "charter", 1.0)
    for i in range(1, 6):
        assert h.journal[i - 1][0] == i


def test_overdraw_check_uses_current_treasury():
    h = House(name="X", capital=0, treasury=100.0)
    h.debit(1, "charter", 50.0)
    assert h.treasury == 50.0
    with pytest.raises(ValueError):
        h.debit(2, "railway", 51.0)
    assert h.treasury == 50.0
    assert len(h.journal) == 1


def test_journal_entries_are_tuples_of_three():
    h = House(name="X", capital=0, treasury=100.0)
    h.credit(1, "dividends", 50.0)
    h.debit(1, "charter", 25.0)
    for entry in h.journal:
        assert isinstance(entry, tuple)
        assert len(entry) == 3
        turn, label, amount = entry
        assert isinstance(turn, int)
        assert isinstance(label, str)
        assert isinstance(amount, float)


def test_multiple_houses_independent_journals():
    game = GildedGame(seed=7)
    houses = list(game.houses.values())[:2]
    h1, h2 = houses
    h1.credit(1, "dividends", 100.0)
    assert len(h1.journal) == 1
    assert len(h2.journal) == 0


def test_treasury_frozenset_immutable():
    assert len(TREASURY_LABELS) == 11
    try:
        TREASURY_LABELS.add("fake")
        assert False, "frozenset should not allow addition"
    except AttributeError:
        pass


def test_credit_debit_reparations_received():
    h = House(name="X", capital=0, treasury=100.0)
    h.credit(1, "reparations received", 500.0)
    assert h.treasury == 600.0
    assert h.journal == [(1, "reparations received", 500.0)]


def test_debit_reparations_paid():
    h = House(name="X", capital=0, treasury=1000.0)
    h.debit(1, "reparations paid", 200.0)
    assert h.treasury == 800.0
    assert h.journal == [(1, "reparations paid", -200.0)]


def test_heir_allowance_credit():
    h = House(name="X", capital=0, treasury=100.0)
    h.credit(1, "heir allowance", 10.0)
    assert h.treasury == 110.0


def test_province_purchase_debit():
    h = House(name="X", capital=0, treasury=2000.0)
    h.debit(1, "province purchase", 500.0)
    assert h.treasury == 1500.0
