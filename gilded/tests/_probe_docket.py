"""Probe: full draw on House — which regions carry a 'rule' action?"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import gilded.tests.test_ui_broadsheet as T

g, v = T._view()
v._w, v._h = 1280, 900
v.active_tab = "House"
surf = pygame.Surface((1280, 900))
v.draw(surf)
print("docket for", v.house, ":",
      [(p.pid, p.kind, [o.key for o in p.options])
       for p in g.docket_by_house.get(v.house, [])])
n = 0
for r in v.regions._regions:
    if isinstance(r.action, dict) and "rule" in r.action:
        n += 1
        print(f"RULE region: rect={r.rect} action={r.action} group={r.group}")
print("total rule regions:", n)
print("total regions:", len(v.regions._regions))
