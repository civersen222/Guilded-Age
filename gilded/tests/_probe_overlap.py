"""Probe: find the colliding text rows in test_no_text_overlap (House tab).
Run: python gilded/tests/_probe_overlap.py"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import tempfile
os.chdir(tempfile.mkdtemp())
from gilded.ui.app import new_app_state

SEED = 42
s = new_app_state(seed=SEED)
for stop in (0, 10):
    while s.game.turn < stop:
        s.game.end_turn()
    s.view.active_tab = "House"
    s.view.draw(s.screen)
    rows = s.view.text_rows
    print(f"--- stop={stop} House: {len(rows)} rows")
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if rows[i][0].colliderect(rows[j][0]):
                print(f"  COLLIDE {i},{j}: {rows[i][0]} {rows[i][1][:50]!r}  vs  {rows[j][0]} {rows[j][1][:50]!r}")
