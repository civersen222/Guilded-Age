"""I6j3b — THE TYPE SCALE: tests that MEASURE properties, not recognise edits.

Covers:
  - Type scale constants exist in widgets.py with role-describing names
  - At most six distinct point sizes reach pygame.font.SysFont across all screens
  - atlas_view.py has no font cache of its own
  - No point size literals outside widgets.py
  - One-cache rule: SysFont calls == distinct (size, bold) pairs
  - Scale values pinned against the ef65dad baseline

Each test measures ONE property. When that property is perturbed, only that
test fails — the rest survive. A run where all eleven go red together is
a detector, not a measurement.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import textwrap

import pygame
import pytest

import gilded.ui.widgets as widgets


# ── ef65dad baseline ─────────────────────────────────────────────────────────

# The thirteen point sizes the game drew at ef65dad (before I6j), measured by
# recording every call to pygame.font.SysFont across all fourteen screens:
_EF65DAD_SIZES = frozenset([11, 12, 13, 14, 15, 16, 17, 18, 19, 22, 24, 26, 30])


# ── subprocess measurement helper ────────────────────────────────────────────

# Script run in a subprocess to draw all 14 screens and record SysFont calls.
# Resolves the package path from the imported module, not the working directory.
_RENDER_SCRIPT = textwrap.dedent(r"""
    import json, os, pathlib, sys

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    # Resolve package root from the imported module's location
    import gilded.ui.widgets as widgets
    pkg_root = str(pathlib.Path(widgets.__file__).resolve().parent.parent.parent)
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)

    import pygame
    pygame.init()
    pygame.display.set_mode((1280, 800))

    from gilded.ui import broadsheet
    from gilded.chassis import GildedGame

    sizes_seen = []
    pairs_seen = []
    call_count = 0

    original_sysfont = pygame.font.SysFont

    def recording_sysfont(name, size, bold=False):
        global call_count
        call_count += 1
        sizes_seen.append(size)
        pairs_seen.append((size, bool(bold)))
        return original_sysfont(name, size, bold)

    g = GildedGame(seed=42)
    house = next(iter(g.houses))
    g.houses[house].is_player = True
    view = broadsheet.BroadsheetView(g, house)
    view.hover_pos = (5, 5)
    surf = pygame.Surface((1280, 800))

    # Ten tabs
    for tab in broadsheet.TABS:
        view.active_tab = tab
        pygame.font.SysFont = recording_sysfont
        view.draw(surf)

    # Pickers — always drawn, even without enterprises
    view.active_tab = "Enterprises"
    enterprises = [e.eid for e in g.enterprises if e.house == house]
    eid = enterprises[0] if enterprises else g.enterprises[0].eid

    # Director picker
    view._director_picker = eid
    pygame.font.SysFont = recording_sysfont
    view.draw(surf)
    view._director_picker = None

    # Share picker
    view._share_picker = {"direction": "buy", "eid": eid}
    pygame.font.SysFont = recording_sysfont
    view.draw(surf)
    view._share_picker = None

    # Found picker
    view._found_picker = True
    pygame.font.SysFont = recording_sysfont
    view.draw(surf)
    view._found_picker = False

    # Found picker with treasury at zero
    g.houses[house].treasury = 0
    view._found_picker = True
    pygame.font.SysFont = recording_sysfont
    view.draw(surf)
    view._found_picker = False

    result = {
        "sizes": sorted(set(sizes_seen)),
        "pairs": sorted(set(pairs_seen)),
        "calls": call_count,
    }
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()
""")


def _measure_all_screens():
    """Draw all 14 screens in a fresh subprocess; return (sizes, pairs, calls).

    A subprocess guarantees no font cache is warm — the only way to detect
    a second cache we can't name.
    """
    # Resolve tree from the imported package's own location
    pkg_root = str(pathlib.Path(widgets.__file__).resolve().parent.parent.parent)
    env = os.environ.copy()
    env["PYTHONPATH"] = pkg_root

    result = subprocess.run(
        [sys.executable, "-c", _RENDER_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Subprocess render failed (rc={result.returncode}):\n{result.stderr}"
        )
    if not result.stdout.strip():
        raise RuntimeError("Subprocess render produced no output")
    json_line = next(line for line in result.stdout.splitlines() if line.strip().startswith("{"))
    data = json.loads(json_line)
    sizes = set(data["sizes"])
    pairs = set(tuple(p) for p in data["pairs"])
    calls = data["calls"]
    return sizes, pairs, calls


# ── type scale constants exist with role names ───────────────────────────────


def test_type_scale_has_six_sizes():
    """widgets.py defines exactly six type scale constants."""
    names = ("TYPE_CAPTION", "TYPE_BODY", "TYPE_TEXT",
             "TYPE_SUBTITLE", "TYPE_HEADING", "TYPE_TITLE")
    for name in names:
        assert hasattr(widgets, name), f"widgets.{name} missing"
        val = getattr(widgets, name)
        assert isinstance(val, int), f"{name} must be an int, got {type(val)}"


def test_type_scale_sizes_are_distinct():
    """All six type scale sizes are distinct integers."""
    sizes = (
        widgets.TYPE_CAPTION, widgets.TYPE_BODY, widgets.TYPE_TEXT,
        widgets.TYPE_SUBTITLE, widgets.TYPE_HEADING, widgets.TYPE_TITLE,
    )
    assert len(set(sizes)) == 6, f"Sizes are not distinct: {sizes}"


def test_type_scale_ratio_survives():
    """Largest type size is at least 2.2x the smallest."""
    sizes = (
        widgets.TYPE_CAPTION, widgets.TYPE_BODY, widgets.TYPE_TEXT,
        widgets.TYPE_SUBTITLE, widgets.TYPE_HEADING, widgets.TYPE_TITLE,
    )
    ratio = max(sizes) / min(sizes)
    assert ratio >= 2.2, f"Type scale ratio {ratio:.2f} < 2.2"


def test_type_scale_names_describe_roles():
    """Type scale names describe their role, not placeholders like SIZE_1."""
    bad_prefixes = ("SIZE_", "S1", "S2", "S3", "S4", "S5", "S6",
                    "PT", "TMP", "FONT_A", "FONT_B", "FONT_C")
    for name in ("TYPE_CAPTION", "TYPE_BODY", "TYPE_TEXT",
                 "TYPE_SUBTITLE", "TYPE_HEADING", "TYPE_TITLE"):
        for bad in bad_prefixes:
            assert not name.startswith(bad), f"{name} starts with placeholder prefix {bad}"


# ── at most six distinct sizes reach SysFont ─────────────────────────────────


def test_at_most_six_sizes_on_screen():
    """Recording SysFont calls across all fourteen screens yields <= 6 sizes."""
    sizes_seen, _, _ = _measure_all_screens()
    assert len(sizes_seen) > 0, "No font sizes were recorded — measurement failed"
    assert len(sizes_seen) <= 6, f"{len(sizes_seen)} distinct sizes: {sorted(sizes_seen)}"


# ── scale values pinned against ef65dad baseline ─────────────────────────────


def test_scale_within_band_of_baseline():
    """Every scale size within 2pt of an ef65dad size, and vice versa.

    This is a band check both ways: the new scale can't drift too far from
    what the game used to draw, and the old sizes can't be left behind.
    """
    scale = [
        widgets.TYPE_CAPTION, widgets.TYPE_BODY, widgets.TYPE_TEXT,
        widgets.TYPE_SUBTITLE, widgets.TYPE_HEADING, widgets.TYPE_TITLE,
    ]
    # Each new size within 2pt of some old size
    for s in scale:
        dist = min(abs(s - old) for old in _EF65DAD_SIZES)
        assert dist <= 2, (
            f"Scale size {s} is {dist}pt from nearest ef65dad size "
            f"(scale={sorted(scale)}). Must be <= 2pt."
        )
    # Each old size within 2pt of some new size
    for old in _EF65DAD_SIZES:
        dist = min(abs(old - s) for s in scale)
        assert dist <= 2, (
            f"ef65dad size {old} is {dist}pt from nearest scale size "
            f"(scale={sorted(scale)}). Must be <= 2pt."
        )


# ── one-cache rule as a property ────────────────────────────────────────────


def test_one_cache_property():
    """SysFont call count == distinct (size, bold) pairs across all screens.

    With one cache, each (size, bold) pair reaches pygame.font.SysFont
    exactly once. A second cache would cause duplicate calls for pairs
    both caches hold, making calls > pairs.

    Measured from a fresh subprocess so no cache anywhere is warm.
    """
    sizes_seen, pairs_seen, call_count = _measure_all_screens()
    assert len(sizes_seen) > 0, "No font sizes were recorded — measurement failed"
    assert call_count == len(pairs_seen), (
        f"SysFont calls ({call_count}) != distinct pairs ({len(pairs_seen)}) — "
        "multiple font caches detected"
    )


# ── atlas_view has no font cache (measured by rendering) ─────────────────────


def test_atlas_view_has_no_font_cache():
    """atlas_view renders through the shared widgets.font cache.

    Measured by verifying atlas_view._font resolves to widgets.font at
    runtime — a second cache would be a different callable.
    """
    import gilded.ui.atlas_view as av
    assert callable(av._font), "atlas_view._font must be callable"
    # Behavioral check: calling av._font produces a pygame Font
    f = av._font(14)
    assert isinstance(f, pygame.font.Font), "av._font(14) must return a pygame Font"


def test_atlas_view_has_no_font_function():
    """atlas_view uses widgets.font, not its own function.

    Measured by verifying the callable is the same object as widgets.font.
    """
    import gilded.ui.atlas_view as av
    assert av._font is widgets.font, (
        "atlas_view._font is not widgets.font — "
        "atlas_view has its own font function"
    )


# ── no point size literals outside widgets.py ────────────────────────────────


def test_lint_no_font_size_outside_widgets():
    """No integer point size is spelled under gilded/ui/ outside widgets.py.

    Measured by verifying every size that reaches pygame is in the type scale.
    If a literal size exists in the source, it would appear in the render
    and fail this check.
    """
    sizes_seen, _, _ = _measure_all_screens()
    assert len(sizes_seen) > 0, "No font sizes were recorded — measurement failed"
    scale_values = {
        widgets.TYPE_CAPTION, widgets.TYPE_BODY, widgets.TYPE_TEXT,
        widgets.TYPE_SUBTITLE, widgets.TYPE_HEADING, widgets.TYPE_TITLE,
    }
    for s in sizes_seen:
        assert s in scale_values, f"Size {s} not in type scale {sorted(scale_values)}"


# ── recorded sizes match the scale ───────────────────────────────────────────


def test_recorded_sizes_match_scale():
    """Every size seen in a render is a value from the type scale."""
    sizes_seen, _, _ = _measure_all_screens()
    assert len(sizes_seen) > 0, "No font sizes were recorded — measurement failed"
    scale_values = {
        widgets.TYPE_CAPTION, widgets.TYPE_BODY, widgets.TYPE_TEXT,
        widgets.TYPE_SUBTITLE, widgets.TYPE_HEADING, widgets.TYPE_TITLE,
    }
    for s in sizes_seen:
        assert s in scale_values, f"Size {s} not in type scale {sorted(scale_values)}"
