"""UI7: tests for the shared number formatter (gilded/ui/figures.py).

Owns the decimal threshold rule: DECIMAL_BELOW = 1.0
"""
from __future__ import annotations

from gilded.ui.figures import figure, signed, DECIMAL_BELOW


# ────────────────────────────────────────────────────────────────────────────
# figure() — magnitude formatting
# ────────────────────────────────────────────────────────────────────────────

def test_figure_zero():
    assert figure(0.0) == "0"


def test_figure_grouped_whole():
    assert figure(1200.0) == "1,200"


def test_figure_grouped_larger():
    assert figure(2500.4) == "2,500"


def test_figure_sub_unit_keeps_decimal():
    assert figure(0.22) == "0.2"


def test_figure_sub_unit_0_4():
    assert figure(0.4) == "0.4"


def test_figure_small_shows_less_than():
    assert figure(1e-9) == "<0.1"


def test_figure_0_02_shows_less_than():
    assert figure(0.02) == "<0.1"


def test_figure_0_049_shows_less_than():
    assert figure(0.049) == "<0.1"


def test_figure_0_05_boundary():
    assert figure(0.05) == "0.1"


def test_figure_0_1():
    assert figure(0.1) == "0.1"


def test_figure_0_949():
    assert figure(0.949) == "0.9"


def test_figure_0_99():
    assert figure(0.99) == "1.0"


def test_figure_1_0_boundary():
    assert figure(1.0) == "1"


def test_figure_1_4():
    assert figure(1.4) == "1"


def test_figure_negative_delegates_to_abs():
    assert figure(-1200.0) == "1,200"


# ────────────────────────────────────────────────────────────────────────────
# signed() — flow formatting
# ────────────────────────────────────────────────────────────────────────────

def test_signed_zero_no_sign():
    assert signed(0.0) == "0"


def test_signed_positive():
    assert signed(1200.0) == "+1,200"


def test_signed_negative():
    assert signed(-1200.0) == "-1,200"


def test_signed_small_positive():
    assert signed(0.22) == "+0.2"


def test_signed_small_negative():
    assert signed(-0.22) == "-0.2"


def test_signed_very_small_positive():
    assert signed(1e-9) == "+<0.1"


def test_signed_very_small_negative():
    assert signed(-1e-9) == "-<0.1"


def test_signed_negative_zero():
    assert signed(-0.0) == "0"


# ────────────────────────────────────────────────────────────────────────────
# Mutation guard: DECIMAL_BELOW must be exactly 1.0
# ────────────────────────────────────────────────────────────────────────────

def test_decimal_below_is_one():
    assert DECIMAL_BELOW == 1.0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
