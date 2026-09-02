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
    # where does the bottom bar (Attention) draw its text?
    import re, io
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "broadsheet.py")).read()
    m = re.search(r"attn_label = f\"Attention: \{attn\}\"(.*?)y = ", src, re.S)
    print("attn draw context:\n", m.group(0)[:600] if m else "not found")
    print(f"pinned SetAmbition top ~ {content.bottom - 30}  (content.bottom-30)")
    print(f"pinned Attention bar top = {900 - B.BOTTOM_H}")

    y3 = draw_house_tab(surf, content, rpt, v)
    print(f"[house]      {content.y} -> {y3}  ({y3 - content.y})")
    y = v._draw_ladder_and_agenda(surf, content, y3 + 8)
    print(f"[ladder]     {y3 + 8} -> {y}  ({y - y3 - 8})")
    rows = [(r.top, t) for r, t in v.text_rows]
    y2 = v._draw_intrigue(surf, content, y)
    print(f"[intrigue]   {y} -> {y2}  ({y2 - y})")
    y4 = v._draw_policies(surf, content, y2)
    print(f"[policies]   {y2} -> {y4}  ({y4 - y2})")

    print("--- ladder text rows ---")
    for yy, t in rows:
        if yy >= y3 + 8:
            print(f"  y={yy:4d}  {t}")
    print(f"TOTAL regions={len(v.regions._regions)}")
    print(f"groups={_groups(v)}")
    print("--- region rects (label-ish) ---")
    for r in sorted(v.regions._regions, key=lambda r: r.rect.top):
        a = r.action
        k = next(iter(a), "?") if isinstance(a, dict) and a else "?"
        print(f"  y={r.rect.top:4d}..{r.rect.bottom:4d} {k}")


if __name__ == "__main__":
    main()
