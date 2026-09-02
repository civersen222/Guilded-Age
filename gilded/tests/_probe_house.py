import os, sys
os.environ.setdefault('SDL_VIDEODRIVER','dummy'); os.environ.setdefault('SDL_AUDIODRIVER','dummy')
_out = open('C:/tmp/w10_house.txt','w',encoding='utf-8')
def print(*a): _out.write(' '.join(str(x) for x in a)+'\n')
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
print('content', content, 'bottom', content.bottom)
surf = pygame.Surface((1280, 900))
rpt = peerage_report(g, v.house)
# monkeypatch to trace y
orig_heir = HT._draw_heir_controls
def trace_heir(s, c, y, *a):
    print('before heir_controls y=', y)
    r = orig_heir(s, c, y, *a)
    print('after heir_controls y=', r)
    return r
HT._draw_heir_controls = trace_heir
y = HT.draw_house_tab(surf, content, rpt, v)
print('house_tab ->', y)
print('seats rows=', len(rpt.seats), 'lines=', len([l for l in HT._house_tab_lines(rpt) if l.strip()]))
_out.close()
