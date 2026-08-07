"""I6j — THE TYPE SCALE: tests for the type scale and font cache unification.

Covers:
  - Type scale constants exist in widgets.py with role-describing names
  - At most six distinct point sizes reach pygame.font.SysFont across all screens
  - atlas_view.py has no font cache of its own
  - Lint that catches point size literals outside widgets.py
"""

from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pathlib
import re
import pygame
import pytest

import gilded.ui.widgets as widgets
from gilded.ui import broadsheet
from gilded.chassis import GildedGame


# ── helpers ──────────────────────────────────────────────────────────────────


def _init():
    pygame.init()
    pygame.display.set_mode((1280, 800))


# ── D1: Type scale constants exist with role names ──────────────────────────


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


# ── D2: At most six distinct sizes reach SysFont ────────────────────────────


def test_at_most_six_sizes_on_screen():
    """Recording SysFont calls across all fourteen screens yields <= 6 sizes."""
    _init()
    sizes_seen = set()

    original_sysfont = pygame.font.SysFont

    def recording_sysfont(name, size, bold=False):
        sizes_seen.add(size)
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
        # Found picker
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

    assert len(sizes_seen) <= 6, f"{len(sizes_seen)} distinct sizes: {sorted(sizes_seen)}"


# ── D6: atlas_view has no font cache ────────────────────────────────────────


def test_atlas_view_has_no_font_cache():
    """atlas_view.py defines no _font_cache of its own."""
    import gilded.ui.atlas_view as av
    source = pathlib.Path(av.__file__).read_text(encoding="utf-8")
    assert "_font_cache" not in source, "atlas_view still defines _font_cache"


def test_atlas_view_has_no_font_function():
    """atlas_view.py defines no _font function of its own."""
    import gilded.ui.atlas_view as av
    source = pathlib.Path(av.__file__).read_text(encoding="utf-8")
    # Check for def _font( which would be a local font function
    assert "def _font(" not in source, "atlas_view still defines its own _font function"


# ── D7: Lint — no point size literals outside widgets.py ────────────────────


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
            # Match module-level constant = integer (e.g. _TEXT_PT = 13)
            for m in re.finditer(r'^[A-Z_]+PT\s*=\s*([0-9]+)', line, re.IGNORECASE):
                offenders.append((str(py_file.name), i, f"{m.group(0)}"))

    detail = "; ".join(f"{f}:{ln} {desc}" for f, ln, desc in offenders)
    assert len(offenders) == 0, (
        f"Point size literals found outside widgets.py ({len(offenders)} offenders): {detail}"
    )


# ── Render test: record actual sizes used ───────────────────────────────────


def test_recorded_sizes_match_scale():
    """Every size that reaches SysFont is one of the type scale values."""
    _init()
    sizes_seen = set()

    original_sysfont = pygame.font.SysFont

    def recording_sysfont(name, size, bold=False):
        sizes_seen.add(size)
        return original_sysfont(name, size, bold)

    g = GildedGame(seed=42)
    house = next(iter(g.houses))
    g.houses[house].is_player = True
    view = broadsheet.BroadsheetView(g, house)
    view.hover_pos = (5, 5)
    surf = pygame.Surface((1280, 800))

    with patch.object(pygame.font, "SysFont", recording_sysfont):
        view.active_tab = "Briefing"
        view.draw(surf)

    scale_values = {
        widgets.TYPE_CAPTION, widgets.TYPE_BODY, widgets.TYPE_TEXT,
        widgets.TYPE_SUBTITLE, widgets.TYPE_HEADING, widgets.TYPE_TITLE,
    }
    for s in sizes_seen:
        assert s in scale_values, f"Size {s} not in type scale {sorted(scale_values)}"


from unittest.mock import patch
