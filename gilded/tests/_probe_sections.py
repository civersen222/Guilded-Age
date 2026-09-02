"""Trace y through BroadSheetView sections at a given stop."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gilded.ui.app import new_app_state

stop = int(sys.argv[1]) if len(sys.argv) > 1 else 10
s = new_app_state(seed=42)
while s.game.turn < stop:
    s.game.end_turn()
v = s.view
v.active_tab = "House"

import gilded.ui.house_tab as HT

orig_dht = HT.draw_house_tab
def dht(surf, content, rpt, view=None):
    r = orig_dht(surf, content, rpt, view)
    print(f"house_tab -> {r}")
    return r
HT.draw_house_tab = dht

def trace(name, orig):
    def w(surface, content, y=None, bottom=None, **k):
        r = orig(surface, content, y, bottom=bottom, **k)
        print(f"{name}: {y} -> {r}")
        return r
    return w
v._draw_ladder_and_agenda = trace("ladder", v._draw_ladder_and_agenda)
v._draw_intrigue = trace("intrigue", v._draw_intrigue)
v._draw_policies = trace("policies", v._draw_policies)

v.draw(s.screen)
