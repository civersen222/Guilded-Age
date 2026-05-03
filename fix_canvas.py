#!/usr/bin/env python3
"""Fix the canvas block in gui.py."""

with open('gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines 349-356 (0-indexed 348-355) need to be replaced
# Replace with MapCanvas creation
new_lines = [
    "        self.map_canvas = MapCanvas(self.map_frame, game_state=self.game)\n",
    "        self.map_canvas.pack(fill=tk.BOTH, expand=True)\n",
    "        self.game.on_tile_selected = self._on_map_click\n",
    "        self.game.on_city_double_click = self._on_city_double_click\n",
]

lines[348:356] = new_lines

with open('gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Canvas block replaced')
