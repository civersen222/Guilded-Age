"""Instrument house_tab internal y-breakdown."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pygame
import gilded.tests.test_ui_broadsheet as T
import gilded.ui.broadsheet as B
from gilded.peerage import report as peerage_report
import gilded.ui.house_tab as H

g, v = T._view()
v._w, v._h = 1280, 900
hud_h = B._hud_height()
content = pygame.Rect(0, B.TAB_H + hud_h, 1280, 900 - B.TAB_H - hud_h - B.BOTTOM_H)
content.height -= v._guide_text_height() + 4
surf = pygame.Surface((1280, 900))
rpt = peerage_report(g, v.house)

# monkeypatch blit to log y positions with tags
import gilded.ui.house_tab as HT
real = HT.blit_text
rows = []
def spy(surface, font, text, pos, color=None):
    rows.append((pos[1], text[:44]))
    return real(surface, font, text, pos, color)
HT.blit_text = spy
y = H.draw_house_tab(surf, content, rpt, v)
HT.blit_text = real
print(f"house ends y={y} (band top 160, want ~430)")
rows.sort()
for yy, t in rows:
    print(f"  y={yy:4d}  {t}")
