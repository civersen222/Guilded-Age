"""Tests for gilded/provenance.py — the Cause/Attributed data model."""
import pytest
from gilded.provenance import Cause, Attributed


# --- delta property ---

def test_delta_computed():
    a = Attributed(value=15.0, previous=10.0, causes=(Cause("test", 5.0, "src"),))
    assert a.delta == 5.0


def test_delta_negative():
    a = Attributed(value=5.0, previous=10.0, causes=(Cause("test", -5.0, "src"),))
    assert a.delta == -5.0


# --- check() passing ---

def test_check_passes_exact():
    a = Attributed(
        value=13.0, previous=10.0,
        causes=(
            Cause("A", 2.0, "src.a"),
            Cause("B", 1.0, "src.b"),
        ))
    assert a.check() is True


def test_check_passes_within_tol():
    a = Attributed(
        value=13.0, previous=10.0,
        causes=(
            Cause("A", 2.0 + 0.5e-7, "src.a"),
            Cause("B", 1.0 - 0.5e-7, "src.b"),
        ))
    assert a.check() is True


# --- check() failing on incomplete causes ---

def test_check_fails_incomplete():
    a = Attributed(
        value=15.0, previous=10.0,
        causes=(Cause("A", 2.0, "src.a"),))
    assert a.check() is False


# --- 1e-6 boundary from both sides ---

def test_check_passes_just_inside_tol():
    # causes sum to delta + 0.9e-7 (within 1e-6)
    a = Attributed(
        value=11.0, previous=10.0,
        causes=(Cause("A", 1.0 + 0.9e-7, "src.a"),))
    assert a.check() is True


def test_check_fails_just_outside_tol():
    # causes sum to delta + 2e-6 (outside 1e-6)
    a = Attributed(
        value=11.0, previous=10.0,
        causes=(Cause("A", 1.0 + 2e-6, "src.a"),))
    assert a.check() is False


def test_check_fails_negative_just_outside_tol():
    # causes sum to delta - 2e-6 (outside 1e-6)
    a = Attributed(
        value=11.0, previous=10.0,
        causes=(Cause("A", 1.0 - 2e-6, "src.a"),))
    assert a.check() is False
