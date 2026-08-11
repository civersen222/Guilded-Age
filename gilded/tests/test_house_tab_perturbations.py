"""Perturbation tests for Stage 5B2 — R-1/R-2/R-3 second half.

Each perturbation changes one fact the player is entitled to see, leaving
the simulation, characters and render chassis untouched. For each
perturbation run THREE things must be true: the run is RED, at least one
case still PASSES, and at least one case that goes red is GREEN on the
unperturbed tree. No two perturbations may produce the same set of
newly-red cases.

KEY: The same test module objects are reused across baseline and perturbed
runs so that module-level perturbations persist.
"""
import importlib
import inspect
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_DIR = Path(__file__).resolve().parent

# Files that own the house-tab test cases (newer than the pre-5B tree).
_HOUSE_TAB_TEST_FILES = [
    "test_house_tab_grievances.py",
    "test_house_tab_disloyal_kin.py",
    "test_house_tab_grip_risk.py",
    "test_house_tab_heir.py",
    "test_house_tab_isolation.py",
    "test_house_tab_loyalty.py",
    "test_house_tab_succession_order.py",
    "test_house_opinion_ui.py",
    "test_house_tab_pixel_visual.py",
]


def _run_case(case_func):
    """Run a single test function. Returns True if it passes, False otherwise."""
    try:
        case_func()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Module-level cache for test cases (loaded once, reused across runs)
# ---------------------------------------------------------------------------

_CACHED_CASES = None


def _get_cached_cases():
    """Load test cases once and reuse the same function objects.

    This is critical: we need the same Python function objects across
    baseline and perturbed runs so that module-level state changes
    (e.g., house_tab.INK = (255,0,0)) are visible to the tests.
    """
    global _CACHED_CASES
    if _CACHED_CASES is not None:
        return _CACHED_CASES

    cases = {}
    for fname in _HOUSE_TAB_TEST_FILES:
        fpath = _TEST_DIR / fname
        if not fpath.exists():
            continue
        mod_name = f"gilded.tests.{fname[:-3]}"
        mod = importlib.import_module(mod_name)
        for name, obj in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("test_"):
                cases[name] = obj
    _CACHED_CASES = cases
    return cases


# ---------------------------------------------------------------------------
# Perturbation definitions
# ---------------------------------------------------------------------------
# Each perturbation changes a *fact* the player is entitled to see — a
# constant, a colour, a font size — not the simulation logic itself.
# ---------------------------------------------------------------------------


def _perturb_ink():
    """Replace the ink colour.  Every pixel test that renders text will
    produce different pixels."""
    import gilded.ui.house_tab as ht
    orig = ht.INK
    ht.INK = (255, 0, 0)
    return lambda: setattr(ht, "INK", orig)


def _perturb_tones_bad():
    """Replace the 'bad' tone colour."""
    import gilded.ui.house_tab as ht
    orig = ht.TONES["bad"]
    ht.TONES["bad"] = (0, 255, 0)
    return lambda: ht.TONES.__setitem__("bad", orig)


def _perturb_tones_good():
    """Replace the 'good' tone colour."""
    import gilded.ui.house_tab as ht
    orig = ht.TONES["good"]
    ht.TONES["good"] = (0, 0, 255)
    return lambda: ht.TONES.__setitem__("good", orig)


def _perturb_tones_warn():
    """Replace the 'warn' tone colour."""
    import gilded.ui.house_tab as ht
    orig = ht.TONES["warn"]
    ht.TONES["warn"] = (255, 0, 255)
    return lambda: ht.TONES.__setitem__("warn", orig)


def _perturb_type_text():
    """Replace the text font size."""
    import gilded.ui.house_tab as ht
    orig = ht.TYPE_TEXT
    ht.TYPE_TEXT = 8
    return lambda: setattr(ht, "TYPE_TEXT", orig)


def _perturb_type_title():
    """Replace the title font size."""
    import gilded.ui.house_tab as ht
    orig = ht.TYPE_TITLE
    ht.TYPE_TITLE = 12
    return lambda: setattr(ht, "TYPE_TITLE", orig)


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestPerturbations:
    """Each perturbation produces a unique signature of newly-red cases."""

    @pytest.fixture(autouse=True)
    def _baseline(self):
        """Compute the baseline (unperturbed) results once per class."""
        if not hasattr(self.__class__, "_baseline_results"):
            self.__class__._baseline_results = self._compute_baseline()
        return self.__class__._baseline_results

    @staticmethod
    def _compute_baseline():
        """Run all house-tab test cases unperturbed."""
        cases = _get_cached_cases()
        return {name: _run_case(func) for name, func in cases.items()}

    @pytest.fixture(autouse=True)
    def _perturbation_names(self):
        """Track which perturbations have run to ensure uniqueness."""
        if not hasattr(self.__class__, "_seen_signatures"):
            self.__class__._seen_signatures: dict = {}
        return self.__class__._seen_signatures

    def _run_perturbation(self, pname, pfactory, baseline_results, seen):
        """Run a single perturbation and assert the R-1/R-2/R-3 conditions."""
        cases = _get_cached_cases()
        setup = pfactory()
        try:
            results = {name: _run_case(func) for name, func in cases.items()}
        finally:
            setup()

        green_baseline = {n for n, p in baseline_results.items() if p}
        red_now = {n for n, p in results.items() if not p}
        newly_red = green_baseline & red_now
        still_passing = {n for n, p in results.items() if p}

        # R-1: the run is RED
        assert len(newly_red) > 0, (
            f"Perturbation '{pname}' produced no newly-red cases. "
            f"Baseline green: {len(green_baseline)}, "
            f"Red now: {red_now}, Newly red: {newly_red}"
        )

        # R-2: at least one case still PASSES
        assert len(still_passing) > 0, (
            f"Perturbation '{pname}' caused ALL cases to fail"
        )

        # Uniqueness
        sig = frozenset(newly_red)
        if sig in seen:
            prior = seen[sig]
            raise AssertionError(
                f"Perturbation '{pname}' produced the same newly-red set as "
                f"'{prior}': {newly_red}. Claims must be told apart."
            )
        seen[sig] = pname

        return newly_red

    # ---- Individual perturbation tests ----

    def test_perturb_ink(self, _baseline, _perturbation_names):
        newly_red = self._run_perturbation(
            "ink", _perturb_ink, _baseline, _perturbation_names)
        assert len(newly_red) >= 1

    def test_perturb_tones_bad(self, _baseline, _perturbation_names):
        newly_red = self._run_perturbation(
            "tones_bad", _perturb_tones_bad, _baseline, _perturbation_names)
        assert len(newly_red) >= 1

    def test_perturb_tones_good(self, _baseline, _perturbation_names):
        newly_red = self._run_perturbation(
            "tones_good", _perturb_tones_good, _baseline, _perturbation_names)
        assert len(newly_red) >= 1

    def test_perturb_tones_warn(self, _baseline, _perturbation_names):
        newly_red = self._run_perturbation(
            "tones_warn", _perturb_tones_warn, _baseline, _perturbation_names)
        assert len(newly_red) >= 1

    def test_perturb_type_text(self, _baseline, _perturbation_names):
        newly_red = self._run_perturbation(
            "type_text", _perturb_type_text, _baseline, _perturbation_names)
        assert len(newly_red) >= 1

    def test_perturb_type_title(self, _baseline, _perturbation_names):
        newly_red = self._run_perturbation(
            "type_title", _perturb_type_title, _baseline, _perturbation_names)
        assert len(newly_red) >= 1
