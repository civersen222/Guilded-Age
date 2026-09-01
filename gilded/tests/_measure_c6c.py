"""Measurement self-check for the C6 cut. Run: python gilded/tests/_measure_c6c.py"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import math
import pygame
import gilded.tests.test_ui_broadsheet as T
import gilded.ui.broadsheet as B
from gilded.peerage import report as peerage_report
import gilded.ui.house_tab as HT
from gilded.ui.widgets import font as _F, TYPE_TEXT, TYPE_BODY, TYPE_CAPTION, TYPE_TITLE, TYPE_SUBTITLE

g, v = T._view(); v._w, v._h = 1280, 900
hud = B._hud_height()
content = pygame.Rect(0, B.TAB_H + hud, 1280, 900 - B.TAB_H - hud - B.BOTTOM_H)
content.height -= v._guide_text_height() + 4
print("content", content, "width", content.width, "band bottom", content.bottom)
rpt = peerage_report(g, v.house)
lines = HT._house_tab_lines(rpt)
nb = [l for l in lines if l.strip()]
print("total", len(lines), "nonblank", len(nb))
PAD = 12
colw4 = (content.width - 2 * PAD) // 4
colw3 = (content.width - 2 * PAD) // 3
for name, size in [("TEXT", TYPE_TEXT), ("BODY", TYPE_BODY), ("CAP", TYPE_CAPTION)]:
    f = _F(size)
    w = max(f.size(l)[0] for l in nb)
    # how many lines per col at 4 cols, wrapping each line to colw4
    import functools
    total_lines = 0
    for l in nb:
        ww = f.size(l)[0]
        total_lines += max(1, -(-ww // colw4))
    rows4 = math.ceil(total_lines / 4)
    total3 = sum(max(1, -(-f.size(l)[0] // colw3)) for l in nb)
    rows3 = math.ceil(total3 / 3)
    print(f"{name}: maxw={w} h={f.get_height()} 4col_lines={total_lines} rows={rows4} block4={rows4*f.get_height()} 3col_lines={total3} rows={rows3} block3={rows3*f.get_height()}")
# title
t = _F(TYPE_TITLE, bold=True)
print("title height", t.get_height())
