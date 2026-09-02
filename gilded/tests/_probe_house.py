"""Instrument house_tab's internal y-budget component by component so the
wave-10 shrink can target the exact gaps. Writes to C:/tmp/w10_house.txt."""
import os, sys
os.environ.setdefault('SDL_VIDEODRIVER','dummy'); os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0, 'C:/Users/civer/civkings')
import pygame
import gilded.tests.test_ui_broadsheet as T
import gilded.ui.broadsheet as B
from gilded.peerage import report as peerage_report
import gilded.ui.house_tab as HT

g, v = T._view()
v._w, v._h = 1280, 900
hud_h = B._hud_height()
content = pygame.Rect(0, B.TAB_H + hud_h, 1280, 900 - B.TAB_H - hud_h - B.BOTTOM_H)
content.height -= v._guide_text_height() + 4
surf = pygame.Surface((1280, 900))
rpt = peerage_report(g, v.house)

# Trace each internal stage by monkeypatching the section helpers.
import gilded.ui.house_tab as M
orig_heir = M._draw_heir_controls
stages = {}
def trace_heir(s, c, y, *a, **kw):
    stages['before_heir'] = y
    r = orig_heir(s, c, y, *a, **kw)
    stages['after_heir'] = r
    return r
M._draw_heir_controls = trace_heir

# Also capture the title bottom and seat-grid end by wrapping draw_house_tab's
# building blocks: replicate the y-math from the source.
from gilded.ui.widgets import font
from gilded.ui.house_tab import _house_tab_lines
body = font(M.TYPE_TEXT)
small = font(M.TYPE_CAPTION)
title = font(M.TYPE_TITLE, bold=True)

PAD = 12
t = title.render(f"HOUSE {rpt.house.upper()}", True, (20,20,20))
title_bottom = content.y + 6 + t.get_height()
lines = _house_tab_lines(rpt)
non_blank = [l for l in lines if l.strip()]
body_h = body.get_height()
btn_h = body_h + 8
seat_h = body_h + 2
cols = 3
seat_rows = -(-len(rpt.seats) // cols)
seat_end = title_bottom + 1 + seat_rows * (btn_h + 2) + 8
cols_d = 8
per = 9
if len(non_blank) > cols_d * per:
    per = max(per, -(-len(non_blank) // cols_d))
line_h = small.get_height()
pitch = line_h + 1
dossier_rows = -(-len(non_blank) // cols_d)
dossier_bottom = seat_end + dossier_rows * pitch

print(f"content.y={content.y} content.bottom={content.bottom}")
print(f"title_bottom={title_bottom}  (title h={t.get_height()})")
print(f"body_h={body_h} btn_h={btn_h} seat_h={seat_h} line_h={line_h} pitch={pitch}")
print(f"seats={len(rpt.seats)} seat_rows={seat_rows} seat_end={seat_end}")
print(f"non_blank={len(non_blank)} per={per} dossier_rows={dossier_rows} dossier_bottom={dossier_bottom}")
print(f"stages={stages}")
print(f"FINAL y (returned) = ?")
y = M.draw_house_tab(surf, content, rpt, v)
print(f"returned y={y}  (want <= 430)")
