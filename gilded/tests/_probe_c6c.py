"""Probe: measure the House-tab chain section by section, and log every
text row's y in the ladder/agenda region so the shrink can target exact
gaps. Also logs the pinned controls' positions."""
import os
import sys
import collections

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pygame
import gilded.tests.test_ui_broadsheet as T
import gilded.ui.broadsheet as B
from gilded.peerage import report as peerage_report
from gilded.ui.house_tab import draw_house_tab


def _groups(view):
    c = collections.Counter()
    for r in view.regions._regions:
        a = r.action
        k = next(iter(a), "?") if isinstance(a, dict) and a else "?"
        c[k] += 1
    return dict(c)


def main():
    g, v = T._view()
    v._w, v._h = 1280, 900
    hud_h = B._hud_height()
    content = pygame.Rect(0, B.TAB_H + hud_h, 1280, 900 - B.TAB_H - hud_h - B.BOTTOM_H)
    content.height -= v._guide_text_height() + 4
    surf = pygame.Surface((1280, 900))
    rpt = peerage_report(g, v.house)
    v.regions._regions.clear()

    print(f"BOTTOM_H={B.BOTTOM_H} band: y={content.y} bottom={content.bottom} h={content.height}")
    print(f"pinned SetAmbition top ~ {content.bottom - 30}  (content.bottom-30)")
    print(f"pinned Attention bar top = {v._h - B.BOTTOM_H}")

    y = draw_house_tab(surf, content, rpt, v)
    print(f"[house]      {content.y} -> {y}  ({y - content.y})")

    # instrument: log every text row's y in ladder/agenda
    rows = []
    real_blit = B.blit_text
    def spy_blit(surface, font, text, pos, color=None):
        rows.append((pos[1], text[:40]))
        return real_blit(surface, font, text, pos, color)
    B.blit_text = spy_blit
    try:
        y2 = v._draw_ladder_and_agenda(surf, content, y + 8, bottom=content.bottom - 40)
        y3 = v._draw_intrigue(surf, content, y2, bottom=content.bottom - 40)
        y4 = v._draw_policies(surf, content, y3, bottom=content.bottom - 40)
    finally:
        B.blit_text = real_blit
    print(f"[ladder]     {y + 8} -> {y2}  ({y2 - (y + 8)})")
    print(f"[intrigue]   {y2} -> {y3}  ({y3 - y2})")
    print(f"[policies]   {y3} -> {y4}  ({y4 - y3})")

    print("--- ladder text rows ---")
    for yy, t in rows:
        if yy >= y + 8:
            print(f"  y={yy:4d}  {t}")
    print(f"TOTAL regions={len(v.regions._regions)}")
    print(f"groups={_groups(v)}")


if __name__ == "__main__":
    main()
