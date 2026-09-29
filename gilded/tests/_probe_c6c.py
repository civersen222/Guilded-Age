"""Probe: House Overview band budget — section bottoms and region groups.
Mirrors test_c6c_layout._measure (real peerage_report, two-column
left/right rects) so the probe matches the committed measurement.
Run:  python gilded/tests/_probe_c6c.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from collections import Counter
import pygame
import gilded.tests.test_ui_broadsheet as T
import gilded.ui.broadsheet as B
from gilded.peerage import report as peerage_report
from gilded.ui.house_tab import draw_house_tab


def _groups(view):
    c = Counter()
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
    print(f"content band: y={content.y} bottom={content.bottom} height={content.height}")
    v.regions._regions.clear()
    y = draw_house_tab(surf, content, rpt, v)
    print(f"house_tab: -> {y}  groups={_groups(v)}")
    left = pygame.Rect(content.x, y + 2, 400, content.bottom - (y + 2))
    right = pygame.Rect(content.x + 414, content.y + 40,
                        content.width - 414,
                        content.bottom - (content.y + 40))
    y = v._draw_ladder_and_agenda(surf, left, left.y, bottom=content.bottom - 40)
    print(f"ladder_agenda: -> {y}  groups={_groups(v)}")
    y = v._draw_policies(surf, right, right.y, bottom=content.bottom - 40)
    print(f"policies: -> {y}  groups={_groups(v)}")
    y = v._draw_intrigue(surf, right, y, bottom=content.bottom - 40)
    print(f"intrigue: -> {y}  groups={_groups(v)}")
    v._draw_guide(surf)
    print(f"ambition: groups={_groups(v)}")
    print(f"TOTAL regions={len(v.regions._regions)}")


if __name__ == "__main__":
    main()
