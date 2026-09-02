"""Probe: full text-row map on House at stop=0 and stop=10, seed 42 (gate seed)."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gilded.ui.app import new_app_state

SEED = 42
stop = int(sys.argv[1]) if len(sys.argv) > 1 else 10

s = new_app_state(seed=SEED)
while s.game.turn < stop:
    s.game.end_turn()
v = s.view
v.active_tab = "House"
v.draw(s.screen)
rows = v.text_rows
print(f"stop={stop} rows={len(rows)}")
coll = 0
for i in range(len(rows)):
    for j in range(i + 1, len(rows)):
        if rows[i][0].colliderect(rows[j][0]):
            coll += 1
            print(f"  OVERLAP: {rows[i][1]!r} {rows[i][0]}  vs  {rows[j][1]!r} {rows[j][0]}")
print("collisions:", coll)
for r, t in sorted(rows, key=lambda x: (x[0].top, x[0].left)):
    if r.top >= 160 and r.top < 840:
        print(f"  y={r.top:3d} x={r.left:3d} h={r.height:2d} {t!r}")
