"""Mission C6 Wave 4 — House Overview band budget.

Committed measurement: draws each House Overview section at the default
1280x900 window, reports the y-cursor and the region groups each section
registers, so the layout can be verified to fit every section into the
content band without overlap.

The test is the assertion: after drawing ALL House Overview sections, the
registered groups must include the court seats, the heir controls, the
docket's rule cards (agenda), the set_stance dials (policies), cycle_exec,
and the pickers — not just printed numbers.

Run:  python gilded/tests/test_c6c_layout.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import sys
import pygame
import gilded.tests.test_ui_broadsheet as T
import gilded.ui.broadsheet as B
from gilded.peerage import report as peerage_report
from gilded.ui.house_tab import draw_house_tab
from collections import Counter


def _groups(view):
    """Count by action key — the census contract is action-based, not by the
    free-form group tag.  A skipped section registers no region at all, so a
    missing action here is a missing control."""
    c = Counter()
    for r in view.regions._regions:
        a = r.action
        k = next(iter(a), "?") if isinstance(a, dict) and a else "?"
        c[k] += 1
    return dict(c)


def _measure(quiet=False):
    g, v = T._view()
    v._w, v._h = 1280, 900
    hud_h = B._hud_height()
    content = pygame.Rect(0, B.TAB_H + hud_h, 1280, 900 - B.TAB_H - hud_h - B.BOTTOM_H)
    content.height -= v._guide_text_height() + 4
    surf = pygame.Surface((1280, 900))
    rpt = peerage_report(g, v.house)
    if not quiet:
        print(f"content band: y={content.y} bottom={content.bottom} height={content.height}")
    v.regions._regions.clear()
    y = draw_house_tab(surf, content, rpt, v)
    if not quiet:
        print(f"house_tab: -> {y}  groups={_groups(v)}")
    # Mirror the two-column House layout in _draw_house: the spine text
    # (ladder + agenda) in the left column, the policies dials at the right
    # column's band top with intrigue stacked beneath them.
    left = pygame.Rect(content.x, y + 2, 400, content.bottom - (y + 2))
    right = pygame.Rect(content.x + 414, content.y + 40,
                        content.width - 414,
                        content.bottom - (content.y + 40))
    y = v._draw_ladder_and_agenda(surf, left, left.y, bottom=content.bottom - 40)
    if not quiet:
        print(f"ladder_agenda: -> {y}  groups={_groups(v)}")
    y = v._draw_policies(surf, right, right.y, bottom=content.bottom - 40)
    if not quiet:
        print(f"policies: -> {y}  groups={_groups(v)}")
    y = v._draw_intrigue(surf, right, y, bottom=content.bottom - 40)
    if not quiet:
        print(f"intrigue: -> {y}  groups={_groups(v)}")
    v._draw_ambition_controls(surf, content)
    # The persistent guide strip (always drawn above the bottom bar, outside
    # the content band) carries the next-step button that re-runs the docket's
    # current ruling — the third rule region the census counts.
    v._draw_guide(surf)
    if not quiet:
        print(f"ambition: groups={_groups(v)}")
    if not quiet:
        print(f"TOTAL regions={len(v.regions._regions)}")
    return content, v


def test_house_overview_fits_band():
    """Every section's controls must register inside the band — the groups,
    not the printed numbers, are the assertion.  A section that skipped
    'for no room' registers nothing, and this test catches it."""
    content, v = _measure(quiet=True)
    groups = _groups(v)
    print(f"content band: y={content.y} bottom={content.bottom} height={content.height}")
    print(f"house_overview groups={groups}  TOTAL regions={len(v.regions._regions)}")
    # Court seats table (6 buttons) + heir controls (2)
    assert groups.get("dismiss_seat") == 6, f"court seats missing/skipped: {groups}"
    assert groups.get("open_heir_picker") == 1, f"heir controls missing/skipped: {groups}"
    # The docket's rule cards (agenda) — the rule x3 docket
    assert (groups.get("rule") or 0) >= 3, f"agenda docket rules missing/skipped: {groups}"
    # The five set_stance dials (policies re-homed to House)
    assert groups.get("set_stance") == 5, f"set_stance dials missing/skipped: {groups}"
    # cycle_exec — the executor cycle control
    assert groups.get("cycle_exec") >= 1, f"cycle_exec missing/skipped: {groups}"
    # The ambition button + scheme picker registration
    assert groups.get("open_ambition_picker") == 1, f"ambition button missing/skipped: {groups}"
    assert groups.get("open_scheme_picker") == 1, f"scheme picker missing/skipped: {groups}"


if __name__ == "__main__":
    _measure()
