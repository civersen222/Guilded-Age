"""Probe: what docket data does the c6c fixture have, and which sections get
dropped by the band in the sequential layout."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import gilded.tests.test_ui_broadsheet as T
import gilded.ui.broadsheet as B
from gilded.ui.house_tab import draw_house_tab

g, v = T._view()
v._w, v._h = 1280, 900
hud_h = B._hud_height()
content = pygame.Rect(0, B.TAB_H + hud_h, 1280, 900 - B.TAB_H - hud_h - B.BOTTOM_H)
content.height -= v._guide_text_height() + 4
surf = pygame.Surface((1280, 900))

print("== docket data for", v.house, "==")
docket = v.game.docket_by_house.get(v.house, [])
for p in docket:
    print(f"pid={p.pid} kind={p.kind} domain={p.domain} "
          f"options={[o.key for o in p.options]}")

print("== band ==", content)
y0 = content.y
v.regions._regions.clear()
y = draw_house_tab(surf, content, None, v)
print(f"house_tab: -> {y}")
y = v._draw_ladder_and_agenda(surf, content, y + 8, bottom=content.bottom - 40)
print(f"ladder_agenda: -> {y}")
y = v._draw_intrigue(surf, content, y, bottom=content.bottom - 40)
print(f"intrigue: -> {y}")
y = v._draw_policies(surf, content, y, bottom=content.bottom - 40)
print(f"policies: -> {y}")
