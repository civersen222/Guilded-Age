"""W10 probe: where do 'Start Scheme' and 'Attention' land at turn 10?"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from gilded.ui.app import new_app_state

s = new_app_state(seed=42, start="menu")
s.view.draw(s.screen)
menu = {r.action.get("menu"): r for r in s.view.regions._regions
        if getattr(r, "group", "") == "menu" and isinstance(r.action, dict)}
from gilded.ui.app import _apply_action
_apply_action(s, s.view.handle_click(menu["new_game"].rect.center))

for t in range(10):
    s.game.end_turn()

s.view.active_tab = "House"
s.view.draw(s.screen)
print(f"screen={s.screen.get_size()}")
for rect, text in s.view.text_rows:
    if rect.y > 830:
        print(f"  {text[:40]!r}  {rect}")
