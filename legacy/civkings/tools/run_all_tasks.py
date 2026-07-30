"""Run all remaining CivKings plan tasks through CynCo sequentially."""
import asyncio
import json
import sys
import time
import os

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TASKS = [
    # ── Task 3: theme.json ──
    {
        "id": 3,
        "name": "Create dark fantasy theme.json",
        "prompt": """Create pygame_app/theme.json with this exact JSON content for pygame_gui theming:

{
    "#defaults": {
        "colours": {
            "dark_bg": "#0a0b0d",
            "normal_bg": "#16181d",
            "hovered_bg": "#23262d",
            "selected_bg": "#33363d",
            "disabled_bg": "#111214",
            "normal_text": "#e0e0e0",
            "hovered_text": "#c5a059",
            "selected_text": "#c5a059",
            "disabled_text": "#555555",
            "normal_border": "#33363d",
            "hovered_border": "#c5a059",
            "focused_border": "#c5a059",
            "link_text": "#c5a059",
            "link_hover": "#d4b76a"
        },
        "font": {"name": "default", "size": "14"}
    },
    "button": {
        "colours": {
            "normal_bg": "#23262d",
            "hovered_bg": "#33363d",
            "active_bg": "#1a1c22",
            "normal_border": "#c5a059",
            "hovered_border": "#d4b76a"
        },
        "misc": {"border_width": "1", "shape_corner_radius": "3"}
    },
    "window": {
        "colours": {"dark_bg": "#0a0b0d", "normal_bg": "#16181d", "normal_border": "#c5a059"},
        "misc": {"border_width": "2", "title_bar_height": "28"}
    },
    "text_box": {
        "colours": {"dark_bg": "#0a0b0d", "normal_bg": "#16181d", "normal_border": "#33363d"}
    },
    "selection_list": {
        "colours": {"dark_bg": "#0a0b0d", "normal_bg": "#16181d", "selected_bg": "#33363d", "normal_border": "#33363d"}
    },
    "panel": {
        "colours": {"dark_bg": "#16181d", "normal_bg": "#16181d", "normal_border": "#33363d"}
    },
    "label": {
        "colours": {"dark_bg": "#16181d", "normal_text": "#e0e0e0"}
    },
    "horizontal_slider": {
        "colours": {"dark_bg": "#0a0b0d", "normal_bg": "#23262d", "hovered_bg": "#33363d", "selected_bg": "#c5a059"}
    }
}

After creating, commit: git add pygame_app/theme.json; git commit -m "feat: add dark fantasy pygame_gui theme"
""",
    },

    # ── Task 4: BaseScreen ──
    {
        "id": 4,
        "name": "Create BaseScreen class",
        "prompt": """Create pygame_app/screens/base.py with this content:

\"\"\"Base class for all game screens.\"\"\"
import pygame
import pygame_gui


class BaseScreen:
    \"\"\"Abstract base for screens (main menu, game, etc.).\"\"\"

    def __init__(self, app):
        self.app = app
        self.ui_manager = app.ui_manager

    def enter(self):
        pass

    def exit(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        pass

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        pass

After creating, commit: git add pygame_app/screens/base.py; git commit -m "feat: add BaseScreen abstract class"
""",
    },

    # ── Task 5: app.py ──
    {
        "id": 5,
        "name": "Create main application loop",
        "prompt": """Create pygame_app/app.py — the main Pygame application. This is the heart of the new GUI.

Key requirements:
- At the TOP, add the project root to sys.path so engine imports work:
  PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)
- GameApp class with __init__ that:
  - calls pygame.init() and pygame.mixer.init()
  - creates display at 1400x900 with RESIZABLE flag
  - sets caption "CivKings: Dynasty & Dominion"
  - creates pygame_gui.UIManager with theme.json path
  - stores self.game = None (set later by NewGameDialog)
  - self.running = True
  - imports and registers MainMenuScreen
- run() method: main loop at 30 FPS
  - process pygame events (QUIT, VIDEORESIZE)
  - pass events to ui_manager and current screen
  - update ui_manager and current screen with dt
  - fill screen with BG color (10,11,13)
  - draw current screen
  - draw ui_manager
  - flip display
- switch_screen(name) method to transition between screens
- handle_resize(w, h) method
- main() function at bottom that creates GameApp and calls run()

Import constants from pygame_app.constants.

After creating, commit: git add pygame_app/app.py; git commit -m "feat: add main Pygame application loop with state machine"
""",
    },

    # ── Task 6: MainMenuScreen ──
    {
        "id": 6,
        "name": "Create Main Menu screen",
        "prompt": """Create pygame_app/screens/main_menu.py.

MainMenuScreen extends BaseScreen (from pygame_app.screens.base).

enter() method:
- Create UILabel with text "CIVKINGS: DYNASTY & DOMINION" centered near top
- Create UILabel subtitle "A Strategy Game of Empires and Bloodlines"
- Create 3 UIButtons centered vertically: "New Game", "Load Game", "Quit"
- Store all elements in self.elements list and buttons in self.buttons dict

exit() method:
- Kill all UI elements (call .kill() on each)

handle_event(event):
- On UI_BUTTON_PRESSED:
  - "Quit" button: set self.app.running = False
  - "New Game" button: import NewGameDialog, register it, switch to it
  - "Load Game" button: show placeholder UIMessageWindow saying "Coming soon"

draw(surface): pass (background filled by app.py)

Use SCREEN_WIDTH, SCREEN_HEIGHT from pygame_app.constants for positioning.
Button size: 240x50. Center them horizontally.

After creating, commit: git add pygame_app/screens/main_menu.py; git commit -m "feat: add main menu screen with new game/load/quit"
""",
    },

    # ── Task 7: NewGameDialog ──
    {
        "id": 7,
        "name": "Create New Game Dialog",
        "prompt": """Create pygame_app/screens/new_game_dialog.py.

NewGameDialog extends BaseScreen.

enter() method creates these UI elements (all stored in self.elements):
- Title UILabel "NEW GAME"
- "Civilization:" label + UIDropDownMenu with civ names from game_data.CIVILIZATIONS.keys()
- "Difficulty:" label + UIDropDownMenu with ['Rookie','Easy','Standard','Hard','Immortal']
- "Map Size:" label + UIDropDownMenu with ['Small (12x12)','Medium (16x16)','Large (24x24)','Huge (32x32)']
- "AI Opponents:" label + UIHorizontalSlider (range 1-7, start 3) + count UILabel
- "Start Game" and "Back" UIButtons

handle_event():
- Back button: switch to 'main_menu' screen
- Start button: call self._start_game()
- Slider moved: update count label

_start_game() method:
- Get selected civ name from dropdown (handle tuple return from pygame_gui)
- Get difficulty, map size
- Parse map size string to int (e.g. 'Medium (16x16)' -> 16)
- Import Game from game module, create: self.app.game = Game(civ, map_width=size, map_height=size)
- Import AIPlayer from ai module, add AI players to game.ai_players dict
- Import GameScreen, register and switch to it

IMPORTANT: pygame_gui dropdowns may return selected_option as a tuple like ('Rome', 'Rome'). Extract the first element.
IMPORTANT: game_data.CIVILIZATIONS values are Civilization dataclass objects. Pass the value, not the key, to Game().

After creating, commit: git add pygame_app/screens/new_game_dialog.py; git commit -m "feat: add new game dialog with civ/difficulty/map/AI selection"
""",
    },

    # ── Task 8: GameScreen stub + main.py update ──
    {
        "id": 8,
        "name": "Create GameScreen stub and update main.py",
        "prompt": """Two files to create/modify:

FILE 1: Create pygame_app/screens/game_screen.py
A minimal GameScreen that proves the full flow works.

GameScreen extends BaseScreen.

enter():
- Get game from self.app.game
- Get civ name: game.player_civ.name
- Create UILabel showing: "Playing as {civ_name} - Turn {game.state.turn} - Map {game.map.width}x{game.map.height}"
- Create UIButton "Next Turn" in bottom-right corner (SCREEN_WIDTH-180, SCREEN_HEIGHT-60, 160, 45)
- Store in self.elements list

handle_event():
- On Next Turn button press: call game.process_turn(), update label text

exit(): kill all elements

draw(surface): pass

FILE 2: Modify main.py (the project entry point) to launch Pygame:

\"\"\"Entry point for CivKings game.\"\"\"
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        from pygame_app.app import main as pygame_main
        pygame_main()
    except ImportError as e:
        print(f"Pygame not available ({e}). Install: pip install -r requirements.txt")
        print("Falling back to text mode...")
        from ui import GameUI
        game_ui = GameUI(GameUI.new_game())

if __name__ == "__main__":
    main()

After creating both files, commit: git add pygame_app/screens/game_screen.py main.py; git commit -m "feat: add stub game screen and update main.py entry point"
""",
    },

    # ── Task 10: Fallback tile generator ──
    {
        "id": 10,
        "name": "Create fallback tile generator",
        "prompt": """Create tools/generate_fallback_tiles.py — generates colored hex PNG tiles as fallback.

This script:
1. Imports PIL (Pillow) for image generation
2. Defines TERRAIN_COLORS dict mapping terrain name strings to RGB tuples (same as pygame_app/constants.py)
3. For each terrain, generates a flat-topped hex tile on transparent background
4. Generates at 5 zoom levels: 0.5, 0.75, 1.0, 1.5, 2.0 with base size 128px
5. For each zoom level, packs all terrain tiles into a horizontal strip atlas PNG
6. Saves atlas PNG + JSON coordinate file to assets/tiles/

Hex drawing: use PIL ImageDraw.polygon with 6 vertices computed as:
  for i in range(6): angle = pi/3 * i; x = cx + r*cos(angle); y = cy + r*sin(angle)

Atlas JSON format: {"PLAINS_0": {"x": 0, "y": 0, "w": 128, "h": 128}, "GRASSLAND_0": {"x": 128, ...}}

File naming: atlas_z0_5.png, atlas_z0_5.json, atlas_z0_75.png, atlas_z0_75.json, atlas_z1_0.png, etc.

After creating the script, RUN IT: python tools/generate_fallback_tiles.py
Then verify the files exist: dir assets\\tiles\\
Then commit: git add tools/generate_fallback_tiles.py assets/tiles/; git commit -m "feat: add fallback hex tile generator with colored hexes"
""",
    },

    # ── Task 11: TileAtlas loader ──
    {
        "id": 11,
        "name": "Create TileAtlas loader",
        "prompt": """Create pygame_app/map/tile_atlas.py — loads sprite sheet atlases for terrain tiles.

TileAtlas class:
- __init__(tiles_dir: str): loads atlas PNGs and JSONs from tiles_dir for all zoom levels
- ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.5, 2.0]
- _zoom_tag(zoom) returns string like "z0_5", "z1_0" etc.
- _load_all(): for each zoom level, loads atlas_{tag}.png as pygame.Surface via pygame.image.load().convert_alpha(), loads atlas_{tag}.json for tile coordinates
- get_tile(terrain_name: str, zoom: float) -> pygame.Surface: returns subsurface for that terrain at nearest zoom level. Caches in _tile_cache dict.
- If terrain not found, return a 32x32 red semi-transparent square as error indicator
- loaded property: True if any atlases loaded

After creating, verify:
python -c "import pygame; pygame.init(); s=pygame.display.set_mode((100,100)); from pygame_app.map.tile_atlas import TileAtlas; a=TileAtlas('assets/tiles'); print(f'Loaded: {a.loaded}'); t=a.get_tile('PLAINS', 1.0); print(f'Size: {t.get_size()}'); pygame.quit(); print('OK')"

Then commit: git add pygame_app/map/tile_atlas.py; git commit -m "feat: add TileAtlas sprite sheet loader with zoom support"
""",
    },

    # ── Task 12: Camera ──
    {
        "id": 12,
        "name": "Create Camera system",
        "prompt": """Create pygame_app/map/camera.py — viewport camera with pan, zoom, smooth lerp.

Camera class:
- __init__(screen_w, screen_h): x=0, y=0, zoom=1.0, target_x/y/zoom for smooth lerp, min_zoom=0.3, max_zoom=3.0, lerp_speed=10.0
- world_to_screen(wx, wy) -> (int, int): converts world coords to screen pixels
  sx = (wx - self.x) * self.zoom + self.screen_w / 2
  sy = (wy - self.y) * self.zoom + self.screen_h / 2
- screen_to_world(sx, sy) -> (float, float): inverse of above
- get_visible_bounds() -> (min_wx, min_wy, max_wx, max_wy): world area visible in viewport
- update(dt): smooth lerp current position toward target
  t = min(1.0, self.lerp_speed * dt)
  self.x += (self.target_x - self.x) * t  (same for y, zoom)
- pan(dx, dy): adjust target by screen-space delta divided by zoom
- zoom_at(screen_x, screen_y, factor): zoom centered on screen position, adjust target so world point under cursor stays under cursor
- center_on(wx, wy): set target position
- snap_to(wx, wy): immediately set both current and target
- resize(new_w, new_h): update screen dimensions

No pygame imports needed — pure math. Only uses typing.Tuple.

Commit: git add pygame_app/map/camera.py; git commit -m "feat: add Camera with pan, zoom, smooth lerp, coordinate transforms"
""",
    },

    # ── Task 13: HexRenderer ──
    {
        "id": 13,
        "name": "Create HexRenderer",
        "prompt": """Create pygame_app/map/hex_renderer.py — renders hex tiles, cities, units, fog, highlights.

HexRenderer class:
- __init__(hex_map, tile_atlas, camera): stores refs, creates pygame fonts, initializes selection state
- hex_to_world(hx, hy) -> (float, float): flat-top hex to world pixels
  wx = HEX_SIZE * 1.5 * hx
  wy = HEX_SIZE * sqrt(3) * (hy + 0.5 * (hx & 1))
- world_to_hex(wx, wy) -> (int, int): inverse (approximate rounding)
- screen_to_hex(sx, sy): screen pixel to hex coords via camera.screen_to_world then world_to_hex
- get_visible_hexes() -> Set: hex coords visible in camera viewport (with margin)
- render(surface, game): main render method, draws layers in order:
  1. Terrain tiles from atlas (tile.terrain.name as string key)
  2. Resource icons (tile.resource — use getattr for safety, show short name text)
  3. River indicators (tile.has_river — blue dot)
  4. City markers (game.cities dict — gold circle for player, red for AI, name + pop text)
  5. Unit markers (game.units dict — green square for player, red for AI, type label + HP bar)
  6. Fog of war (game.fog.is_explored, game.fog.is_visible — semi-transparent black overlay)
  7. Selection highlight (self.selected_hex — gold hex outline)
  8. Move range (self.move_range set — blue hex outlines)
  9. Attack range (self.attack_range set — red hex outlines)
  10. Hover highlight (self.hovered_hex — white hex outline)

IMPORTANT ENGINE API:
- game.player_civ.name = player's civ name string (e.g. "Rome")
- city.owner and unit.owner = civ name strings — compare with game.player_civ.name
- unit.hp and unit.max_hp = ints
- tile.terrain.name = string like "PLAINS"
- tile.resource = Optional[ResourceType enum], has .name property
- tile.has_river = bool
- game.fog.is_visible(x, y) and game.fog.is_explored(x, y) = bools

Import TERRAIN_COLORS, HEX_SIZE, GOLD, RED, GREEN, TEXT, SUBTLE, BLUE from pygame_app.constants.
Draw hex outlines with pygame.draw.polygon using 6 vertices at angles pi/3 * i.

Commit: git add pygame_app/map/hex_renderer.py; git commit -m "feat: add HexRenderer with terrain, cities, units, fog, highlights"
""",
    },

    # ── Task 14: Wire into GameScreen + Minimap ──
    {
        "id": 14,
        "name": "Wire hex map into GameScreen + Minimap",
        "prompt": """Two files:

FILE 1: Create pygame_app/map/minimap.py
Minimap class (200x200, bottom-left corner):
- __init__(hex_map, camera): pre-renders terrain as colored dots
- _render_base(): create Surface, for each tile draw a colored rect based on terrain
- render(surface, game, screen_h): blit base, draw city dots (gold=player, red=AI), draw viewport rectangle (white outline), position at (10, screen_h - 210)
- handle_click(mx, my, screen_h) -> bool: if click in minimap area, convert to world coords, call camera.center_on, return True

FILE 2: Replace pygame_app/screens/game_screen.py with the FULL version:

GameScreen extends BaseScreen. This is the main gameplay coordinator.

enter():
- Create Camera(MAP_W, MAP_H) from constants
- Create TileAtlas('assets/tiles')
- Create HexRenderer(game.map, atlas, camera)
- Create Minimap(game.map, camera)
- Center camera on first city: game.cities first value, get position, hex_to_world, camera.snap_to
- Create map_surface = pygame.Surface((MAP_W, MAP_H))
- Create resource bar UILabel at top with formatted yields (use f"{val:.1f}" for floats!)
- Create "Next Turn" UIButton

handle_event():
- Next Turn button or Enter key: game.process_turn(), refresh UI
- Left click in map area: convert to hex, set selected_hex
- Middle mouse drag: camera pan
- Mouse wheel: camera.zoom_at
- Home key: center on capital
- Track held keys for WASD panning

update(dt):
- WASD/arrow key panning at 400 px/s
- camera.update(dt)

draw(surface):
- Fill map_surface dark, call hex_renderer.render(map_surface, game)
- Blit map_surface at (MAP_X, MAP_Y)
- Draw panel background rectangles (left, right, top, bottom bars) with PANEL_BG color
- Draw border lines with BORDER color
- Call minimap.render(surface, game, SCREEN_HEIGHT)

_format_resource_text(game):
- Get yields from game.city_manager.get_total_yields(civ_name, game.map.tiles)
- Format: "{civ} | Food: {f:.1f} | Prod: {p:.1f} | Gold: {int(gold)} | Sci: {s:.1f} | Turn {turn}"
- game.gold is Dict[str, int] keyed by civ name

Import MAP_X, MAP_Y, MAP_W, MAP_H, RESOURCE_BAR_HEIGHT, ACTION_BAR_HEIGHT, LEFT_PANEL_WIDTH, RIGHT_PANEL_WIDTH, SCREEN_WIDTH, SCREEN_HEIGHT, PANEL_BG, BORDER from constants.

Commit both: git add pygame_app/map/minimap.py pygame_app/screens/game_screen.py; git commit -m "feat: wire hex map rendering with camera, minimap, interaction"
""",
    },
]


async def send_task(prompt: str, port: int = 9160) -> bool:
    """Send one task to CynCo and stream response. Returns True on success."""
    from websockets.asyncio.client import connect

    ws = await connect(
        f"ws://localhost:{port}",
        ping_interval=None, ping_timeout=None,
        max_size=50_000_000,
    )

    # Drain initial events
    try:
        await asyncio.wait_for(ws.recv(), timeout=3)
    except Exception:
        pass

    await ws.send(json.dumps({"type": "user.message", "text": prompt}))

    tools = 0
    start = time.time()
    success = True

    for _ in range(1000):
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=300)
        except asyncio.TimeoutError:
            print("\n  TIMEOUT!")
            success = False
            break

        event = json.loads(msg)
        t = event.get("type", "")

        if t == "stream.token":
            print(event.get("text", ""), end="", flush=True)
        elif t == "message.complete":
            elapsed = time.time() - start
            usage = event.get("usage", {})
            print(f"\n  [{event.get('stopReason')} | {tools} tools | {elapsed:.0f}s | {usage.get('inputTokens',0)}/{usage.get('outputTokens',0)} tok]")
            break
        elif t == "approval.request":
            await ws.send(json.dumps({
                "type": "approval.response",
                "requestId": event["requestId"],
                "approved": True,
            }))
        elif t == "tool.start":
            tool = event.get("toolName", "")
            inp = str(event.get("input", {}))[:100]
            tools += 1
            print(f"\n  [{tool}] {inp}")
        elif t == "tool.complete":
            err = event.get("isError", False)
            result = str(event.get("result", ""))[:100]
            print(f"  <- {'ERR' if err else 'OK'}: {result[:70]}")
        elif t == "session.error":
            print(f"\n  SESSION ERROR: {event.get('error')}")
            success = False
            break

    await ws.close()
    return success


async def main():
    start_task = int(sys.argv[1]) if len(sys.argv) > 1 else 3  # Default: start from task 3

    tasks = [t for t in TASKS if t["id"] >= start_task]
    print(f"Running {len(tasks)} tasks (IDs {tasks[0]['id']}-{tasks[-1]['id']})")
    print(f"{'='*70}\n")

    for task in tasks:
        print(f"{'='*70}")
        print(f"  TASK {task['id']}: {task['name']}")
        print(f"{'='*70}")

        ok = await send_task(task["prompt"])

        if not ok:
            print(f"\n  TASK {task['id']} FAILED — stopping")
            break

        print()
        await asyncio.sleep(2)  # Brief pause between tasks

    # Summary
    print(f"\n{'='*70}")
    print("  ALL TASKS COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
