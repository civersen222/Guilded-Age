"""Measure real downstream section heights at FULL room, and the picker's
natural row height. Run:  python gilded/tests/_measure_c6c.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import gilded.tests.test_ui_broadsheet as T
import gilded.ui.broadsheet as B
from gilded.peerage import report as peerage_report
from gilded.ui.house_tab import draw_house_tab
from collections import Counter


def _groups(view):
    c = Counter()
    for r in view.regions._regions:
        a = r.action
        k = next(iter(a), "?") if isinstance(a, dict) and a else "?"
        c[k] += 1
    return dict(c)


def measure_full_room():
    """Draw each downstream section with UNLIMITED bottom so we see its
    natural height. Then we know how much band they truly need."""
    g, v = T._view()
    v._w, v._h = 1280, 900
    hud_h = B._hud_height()
    content = pygame.Rect(0, B.TAB_H + hud_h, 1280, 900 - B.TAB_H - hud_h - B.BOTTOM_H)
    content.height -= v._guide_text_height() + 4
    surf = pygame.Surface((1280, 900))
    rpt = peerage_report(g, v.house)
    big = content.bottom + 500  # unlimited room

    v.regions._regions.clear()
    y = draw_house_tab(surf, content, rpt, v)
    print(f"[full-room] house_tab -> {y}  groups={_groups(v)}")
    v.regions._regions.clear()

    y2 = v._draw_ladder_and_agenda(surf, content, y + 8, bottom=big)
    print(f"[full-room] ladder_agenda {y+8} -> {y2}  (consumed {y2-(y+8)})  groups={_groups(v)}")
    y3 = v._draw_intrigue(surf, content, y2, bottom=big)
    print(f"[full-room] intrigue {y2} -> {y3}  (consumed {y3-y2})  groups={_groups(v)}")
    y4 = v._draw_policies(surf, content, y3, bottom=big)
    print(f"[full-room] policies {y3} -> {y4}  (consumed {y4-y3})  groups={_groups(v)}")
    v._draw_ambition_controls(surf, content)
    print(f"[full-room] TOTAL groups={_groups(v)} regions={len(v.regions._regions)}")


def measure_picker_row():
    """The heir picker's natural row height (the committed 8-rows/480px)."""
    g, v = T._view()
    v._w, v._h = 1280, 900
    v._heir_picker = True
    v.regions._regions.clear()
    hud_h = B._hud_height()
    content = pygame.Rect(0, B.TAB_H + hud_h, 1280, 900 - B.TAB_H - hud_h - B.BOTTOM_H)
    content.height -= v._guide_text_height() + 4
    surf = pygame.Surface((1280, 900))
    rpt = peerage_report(g, v.house)
    y = draw_house_tab(surf, content, rpt, v)
    print(f"[picker-open] house_tab -> {y}  groups={_groups(v)}")


if __name__ == "__main__":
    measure_full_room()
    print("-" * 40)
    measure_picker_row()
