"""Temporary measurement probe (committed self-check). Run:
python gilded/tests/_probe_c6c.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pygame
import gilded.tests.test_ui_broadsheet as T
import gilded.ui.broadsheet as B
from gilded.peerage import report as peerage_report
from gilded.ui.house_tab import draw_house_tab

g, v = T._view()
v._w, v._h = 1280, 900
hud_h = B._hud_height()
content = pygame.Rect(0, B.TAB_H + hud_h, 1280, 900 - B.TAB_H - hud_h - B.BOTTOM_H)
content.height -= v._guide_text_height() + 4
surf = pygame.Surface((1280, 900))
rpt = peerage_report(g, v.house)
print(f"content band: y={content.y} bottom={content.bottom} height={content.height}")

v.regions._regions.clear()
y1 = draw_house_tab(surf, content, rpt, v)
print(f"house_tab: -> {y1}  (band ends {content.bottom})")
y2 = v._draw_ladder_and_agenda(surf, content, y1 + 8, bottom=content.bottom - 40)
print(f"ladder_agenda: -> {y2}")
y3 = v._draw_intrigue(surf, content, y2, bottom=content.bottom - 40)
print(f"intrigue: -> {y3}")
y4 = v._draw_policies(surf, content, y3, bottom=content.bottom - 40)
print(f"policies: -> {y4}")
v._draw_ambition_controls(surf, content)
n = len(v.regions._regions)
print(f"TOTAL regions={n}")
from collections import Counter
c = Counter()
for r in v.regions._regions:
    a = r.action
    k = next(iter(a), "?") if isinstance(a, dict) and a else "?"
    c[k] += 1
print(f"groups={dict(c)}")
