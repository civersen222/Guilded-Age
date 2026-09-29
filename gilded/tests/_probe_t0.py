import os, sys
os.environ.setdefault('SDL_VIDEODRIVER','dummy'); os.environ.setdefault('SDL_AUDIODRIVER','dummy')
_out = open('C:/tmp/w10_t0.txt','w',encoding='utf-8')
def print(*a): _out.write(' '.join(str(x) for x in a)+'\n')
sys.path.insert(0, 'C:/Users/civer/civkings')
import gilded.ui.app as A
s = A.new_app_state(seed=42)
s.view.active_tab = 'House'
s.view.draw(s.screen)
rows = s.view.text_rows
for i in range(len(rows)):
    for j in range(i+1, len(rows)):
        if rows[i][0].colliderect(rows[j][0]):
            print('COLLIDE:', rows[i][1][:40], '||', rows[j][1][:40])
# every row sorted by y with text
for r, t in sorted(rows, key=lambda x: x[0].y):
    print(r.y, r.x, r.h, t[:56])
_out.close()
