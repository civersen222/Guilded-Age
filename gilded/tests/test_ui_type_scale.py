"""I6j2 — THE TYPE SCALE: tests for the type scale and font cache unification.

Covers:
  - Type scale constants exist in widgets.py with role-describing names
  - At most six distinct point sizes reach pygame.font.SysFont across all screens
  - atlas_view.py has no font cache of its own
  - Lint that catches point size literals outside widgets.py
  - One-cache rule: SysFont calls == distinct (size, bold) pairs
  - Scale values pinned against the ef65dad baseline
"""

from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pathlib
import re
from unittest.mock import patch

import pygame
import pytest

import gilded.ui.widgets as widgets
from gilded.ui import broadsheet
from gilded.chassis import GildedGame


# ── helpers ──────────────────────────────────────────────────────────────────


def _init():
    pygame.init()
    pygame.display.set_mode((1280, 800))


def _draw_all_screens():
    """Draw all fourteen screens with a warm cache, returning (sizes, pairs, calls) recorded.

    Clears widgets._font_cache before drawing so the results are the same
    whether or not any screen has already been drawn in this process.
    Returns:
        sizes_seen: set of distinct point sizes
        pairs_seen: set of distinct (size, bold) pairs
        call_count: total number of SysFont calls
    """
    _init()
    widgets._font_cache.clear()

    sizes_seen: set[int] = set()
    pairs_seen: set[tuple[int, bool]] = set()
    call_count = 0

    original_sysfont = pygame.font.SysFont

    def recording_sysfont(name, size, bold=False):
        nonlocal call_count
        call_count += 1
        sizes_seen.add(size)
        pairs_seen.add((size, bool(bold)))
        return original_sysfont(name, size, bold)

    g = GildedGame(seed=42)
    house = next(iter(g.houses))
    g.houses[house].is_player = True
    view = broadsheet.BroadsheetView(g, house)
    view.hover_pos = (5, 5)
    surf = pygame.Surface((1280, 800))

    tabs = broadsheet.TABS
    for tab in tabs:
        view.active_tab = tab
        with patch.object(pygame.font, "SysFont", recording_sysfont):
            view.draw(surf)

    # Pickers
    view.active_tab = "Enterprises"
    enterprises = [e.eid for e in g.enterprises if e.house == house]
    if enterprises:
        eid = enterprises[0]
        # Found picker (treasury = 0)
        g.houses[house].treasury = 0.0
        view._found_picker = True
        with patch.object(pygame.font, "SysFont", recording_sysfont):
            view.draw(surf)
        view._found_picker = False
        # Director picker
        view._director_picker = eid
        with patch.object(pygame.font, "SysFont", recording_sysfont):
            view.draw(surf)
        view._director_picker = None
        # Share picker
        view._share_picker = {"direction": "buy", "eid": eid}
        with patch.object(pygame.font, "SysFont", recording_sysfont):
            view.draw(surf)
        view._share_picker = None

    return sizes_seen, pairs_seen, call_count


# ── ef65dad baseline ─────────────────────────────────────────────────────────

# The thirteen point sizes the game drew at ef65dad (before I6j), measured by
# recording every call to pygame.font.SysFont across all fourteen screens:
_EF65DAD_SIZES = frozenset([11, 12, 13, 14, 15, 16, 17, 18, 19, 22, 24, 26, 30])


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
    sizes_seen, _, _ = _draw_all_screens()
    assert len(sizes_seen) > 0, "No font sizes were recorded — measurement failed"
    assert len(sizes_seen) <= 6, f"{len(sizes_seen)} distinct sizes: {sorted(sizes_seen)}"


# ── scale values pinned against ef65dad baseline ────────────────────────────


def test_scale_within_band_of_baseline():
    """Every scale size is within 2pt of an ef65dad size, and vice versa.

    Pins the six numbers: moving TYPE_TITLE from 29 to 33 fails because
    33 is more than 2pt from any ef65dad size (closest is 30, dist=3).
    """
    scale = set(widgets.TYPE_SIZES)
    baseline = _EF65DAD_SIZES

    for s in scale:
        min_dist = min(abs(s - b) for b in baseline)
        assert min_dist <= 2, (
            f"Scale size {s} is {min_dist}pt from nearest baseline size "
            f"(baseline={sorted(baseline)}). Must be <= 2pt."
        )

    for b in baseline:
        min_dist = min(abs(b - s) for s in scale)
        assert min_dist <= 2, (
            f"Baseline size {b} is {min_dist}pt from nearest scale size "
            f"(scale={sorted(scale)}). Must be <= 2pt."
        )


# ── one-cache rule as a property ────────────────────────────────────────────


def test_one_cache_property():
    """SysFont call count == distinct (size, bold) pairs across all screens.

    With one cache, each (size, bold) pair reaches pygame.font.SysFont
    exactly once. A second cache would cause duplicate calls for pairs
    already cached by the shared cache, making calls > pairs.
    """
    sizes_seen, pairs_seen, call_count = _draw_all_screens()
    assert len(sizes_seen) > 0, "No font sizes were recorded — measurement failed"
    assert call_count == len(pairs_seen), (
        f"SysFont calls ({call_count}) != distinct pairs ({len(pairs_seen)}) — "
        "multiple font caches detected"
    )


# ── atlas_view has no font cache ────────────────────────────────────────────


def test_atlas_view_has_no_font_cache():
    """atlas_view.py defines no _font_cache of its own."""
    import gilded.ui.atlas_view as av
    source = pathlib.Path(av.__file__).read_text(encoding="utf-8")
    assert "_font_cache" not in source, "atlas_view still defines _font_cache"


def test_atlas_view_has_no_font_function():
    """atlas_view.py defines no _font function of its own."""
    import gilded.ui.atlas_view as av
    source = pathlib.Path(av.__file__).read_text(encoding="utf-8")
    assert "def _font(" not in source, "atlas_view still defines its own _font function"


# ── lint — no point size literals outside widgets.py ─────────────────────────


def test_lint_no_font_size_outside_widgets():
    """No integer point size is spelled under gilded/ui/ outside widgets.py."""
    ui_dir = pathlib.Path(widgets.__file__).parent
    offenders: list[tuple[str, int, str]] = []

    for py_file in ui_dir.glob("*.py"):
        if py_file.name == "widgets.py":
            continue
        if py_file.name.startswith("__"):
            continue
        text = py_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Match _font(N) where N is an integer literal
            for m in re.finditer(r'_font\(\s*([0-9]+)', line):
                offenders.append((str(py_file.name), i, f"_font({m.group(1)})"))
            # Match _font(..., N) or _font(..., N, ...) — second positional int
            for m in re.finditer(r'_font\([^,]+,\s*([0-9]+)', line):
                if not re.search(r'_font\(\s*[0-9]+', line[:m.start()]):
                    offenders.append((str(py_file.name), i, f"_font(..., {m.group(1)})"))
            # Match size=N or pt=N keyword with integer literal
            for m in re.finditer(r'(?:size|pt)\s*=\s*([0-9]+)', line):
                offenders.append((str(py_file.name), i, f"{m.group(0)}"))

    detail = "; ".join(f"{f}:{ln} {desc}" for f, ln, desc in offenders)
    assert len(offenders) == 0, (
        f"Point size literals found outside widgets.py ({len(offenders)} offenders): {detail}"
    )


# ── recorded sizes match the scale ───────────────────────────────────────────


def test_recorded_sizes_match_scale():
    """Every size that reaches SysFont is one of the type scale values."""
    sizes_seen, _, _ = _draw_all_screens()
    assert len(sizes_seen) > 0, "No font sizes were recorded — measurement failed"
    scale_values = {
        widgets.TYPE_CAPTION, widgets.TYPE_BODY, widgets.TYPE_TEXT,
        widgets.TYPE_SUBTITLE, widgets.TYPE_HEADING, widgets.TYPE_TITLE,
    }
    for s in sizes_seen:
        assert s in scale_values, f"Size {s} not in type scale {sorted(scale_values)}"
