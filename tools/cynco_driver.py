"""Drive CynCo engine to execute CivKings overhaul plan tasks.

Starts the CynCo engine, connects via WebSocket, sends plan tasks
one at a time with auto-approve, streams output to terminal.

Usage:
    python tools/cynco_driver.py                    # Start from Phase 1 Task 1
    python tools/cynco_driver.py --task 5           # Start from Task 5
    python tools/cynco_driver.py --phase 2          # Start from Phase 2
    python tools/cynco_driver.py --interactive      # Pause between tasks for review
"""
import asyncio
import json
import subprocess
import sys
import os
import time
import signal
import argparse
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────
ENGINE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'localcode'))
PROJECT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
WS_PORT = 9160
MODEL = "qwen3.6"
LOG_DIR = os.path.join(PROJECT_DIR, 'tools', 'cynco_logs')

# ── Plan Tasks ──────────────────────────────────────────────────
# Each task is a prompt that tells CynCo exactly what to do.
# CynCo reads the plan file for full code details.

PLAN_FILE = "docs/superpowers/plans/2026-05-04-civkings-overhaul-plan.md"

TASKS = [
    # Phase 1: Pygame Core Scaffold
    {
        "id": 1,
        "phase": 1,
        "name": "Create requirements.txt and install dependencies",
        "prompt": (
            f"Read the implementation plan at {PLAN_FILE}, specifically Task 1. "
            "Create requirements.txt with pygame-ce>=2.5.0, pygame-gui>=0.6.14, Pillow>=10.0.0. "
            "Then run: pip install -r requirements.txt "
            "Then verify imports work: python -c \"import pygame; import pygame_gui; from PIL import Image; print('OK')\" "
            "Then commit: git add requirements.txt && git commit -m 'chore: add Pygame-ce, pygame-gui, Pillow dependencies'"
        ),
    },
    {
        "id": 2,
        "phase": 1,
        "name": "Create constants and package structure",
        "prompt": (
            f"Read Task 2 in {PLAN_FILE}. Create the pygame_app/ package structure: "
            "Create empty __init__.py files in: pygame_app/, pygame_app/screens/, pygame_app/map/, "
            "pygame_app/panels/, pygame_app/popups/, pygame_app/effects/, pygame_app/audio/. "
            "Create pygame_app/constants.py with all the constants from the plan (colors, layout sizes, terrain colors). "
            "IMPORTANT: TERRAIN_COLORS must use string keys like 'PLAINS' not TerrainType enums — "
            "do NOT import from game_data in constants.py. "
            "Commit with: git commit -m 'feat: create pygame_app package structure with constants'"
        ),
    },
    {
        "id": 3,
        "phase": 1,
        "name": "Create dark fantasy theme.json",
        "prompt": (
            f"Read Task 3 in {PLAN_FILE}. Create pygame_app/theme.json with the exact JSON from the plan. "
            "This is the pygame_gui theme file with dark fantasy colors (#0a0b0d backgrounds, #c5a059 gold accents, "
            "#e0e0e0 text). Include sections for: #defaults, button, window, text_box, selection_list, panel, label, horizontal_slider. "
            "Commit with: git commit -m 'feat: add dark fantasy pygame_gui theme'"
        ),
    },
    {
        "id": 4,
        "phase": 1,
        "name": "Create BaseScreen class",
        "prompt": (
            f"Read Task 4 in {PLAN_FILE}. Create pygame_app/screens/base.py with the BaseScreen abstract class. "
            "It takes an app reference in __init__, stores self.app and self.ui_manager. "
            "Has empty methods: enter(), exit(), handle_event(event), update(dt), draw(surface). "
            "Commit with: git commit -m 'feat: add BaseScreen abstract class'"
        ),
    },
    {
        "id": 5,
        "phase": 1,
        "name": "Create main application loop",
        "prompt": (
            f"Read Task 5 in {PLAN_FILE}. Create pygame_app/app.py with the GameApp class. "
            "CRITICAL: At the top, add PROJECT_ROOT to sys.path so engine imports (game.py, game_data.py) work. "
            "PROJECT_ROOT = parent of pygame_app directory (the civkings project root). "
            "GameApp.__init__: pygame.init(), mixer.init(), display.set_mode(1400x900 RESIZABLE), "
            "UIManager with theme.json, state machine, import and register MainMenuScreen. "
            "GameApp.run(): main loop at 30 FPS — process events, update, draw, flip. "
            "Handle QUIT, VIDEORESIZE. Add main() entry point. "
            "Commit with: git commit -m 'feat: add main Pygame application loop with state machine'"
        ),
    },
    {
        "id": 6,
        "phase": 1,
        "name": "Create Main Menu screen",
        "prompt": (
            f"Read Task 6 in {PLAN_FILE}. Create pygame_app/screens/main_menu.py. "
            "MainMenuScreen extends BaseScreen. "
            "enter(): create UILabel title 'CIVKINGS: DYNASTY & DOMINION', subtitle, "
            "and three UIButtons: New Game, Load Game, Quit. Centered on screen. "
            "handle_event(): Quit button sets app.running=False, New Game switches to new_game_dialog screen, "
            "Load Game shows placeholder UIMessageWindow for now. "
            "exit(): kill all UI elements. "
            "Commit with: git commit -m 'feat: add main menu screen with new game/load/quit'"
        ),
    },
    {
        "id": 7,
        "phase": 1,
        "name": "Create New Game Dialog screen",
        "prompt": (
            f"Read Task 7 in {PLAN_FILE}. Create pygame_app/screens/new_game_dialog.py. "
            "NewGameDialog extends BaseScreen. "
            "enter(): UIDropDownMenu for civilization (from game_data.CIVILIZATIONS.keys()), "
            "difficulty dropdown (Rookie/Easy/Standard/Hard/Immortal), "
            "map size dropdown (Small 12x12, Medium 16x16, Large 24x24, Huge 32x32), "
            "UIHorizontalSlider for AI count (1-7), label showing current count. "
            "Start Game button: creates Game(civ, map_width=size, map_height=size), "
            "adds AIPlayer instances for selected AI civs, stores in app.game, "
            "switches to 'game' screen. Back button returns to main_menu. "
            "Handle pygame_gui dropdown selected_option possibly being a tuple. "
            "Commit with: git commit -m 'feat: add new game dialog with civ/difficulty/map/AI selection'"
        ),
    },
    {
        "id": 8,
        "phase": 1,
        "name": "Create stub GameScreen and update main.py",
        "prompt": (
            f"Read Tasks 8 and 9 in {PLAN_FILE}. "
            "1) Create pygame_app/screens/game_screen.py with a minimal GameScreen that shows "
            "a label with civ name + turn number + map size, and a Next Turn button. "
            "Next Turn calls game.process_turn() and updates the label. "
            "2) Update main.py to import and call pygame_app.app.main() instead of the old tkinter gui. "
            "Keep a fallback to text ui.py if pygame import fails. "
            "3) Test: run 'python main.py' — should open pygame window with menu. "
            "Commit both files: git commit -m 'feat: add stub game screen, update main.py entry point'"
        ),
    },
    # Phase 2: Hex Map Renderer
    {
        "id": 10,
        "phase": 2,
        "name": "Create fallback tile generator",
        "prompt": (
            f"Read Task 10 in {PLAN_FILE}. Create tools/generate_fallback_tiles.py. "
            "This generates colored hex PNG tiles as fallback when ComfyUI assets don't exist. "
            "For each terrain type (PLAINS, GRASSLAND, FOREST, HILLS, MOUNTAIN, DESERT, TUNDRA, WATER_COAST, OCEAN), "
            "generate a flat-topped hex image with the terrain color on transparent background. "
            "Generate at 5 zoom levels (0.5, 0.75, 1.0, 1.5, 2.0) with base size 128px. "
            "Pack all tiles for each zoom into a horizontal strip atlas PNG + JSON coordinate file. "
            "Save to assets/tiles/atlas_z0_5.png, atlas_z0_5.json, atlas_z0_75.png, etc. "
            "Run the script after creating it. "
            "Commit with: git commit -m 'feat: add fallback hex tile generator with colored hexes'"
        ),
    },
    {
        "id": 11,
        "phase": 2,
        "name": "Create TileAtlas loader",
        "prompt": (
            f"Read Task 11 in {PLAN_FILE}. Create pygame_app/map/tile_atlas.py. "
            "TileAtlas class loads PNG atlas + JSON from assets/tiles/ for all zoom levels. "
            "get_tile(terrain_name, zoom) returns the subsurface for that terrain at nearest zoom. "
            "Cache extracted surfaces in _tile_cache dict. "
            "Return red square if terrain not found (error indicator). "
            "Verify with: python -c \"import pygame; pygame.init(); s=pygame.display.set_mode((100,100)); "
            "from pygame_app.map.tile_atlas import TileAtlas; a=TileAtlas('assets/tiles'); "
            "print(f'Loaded: {a.loaded}'); t=a.get_tile('PLAINS', 1.0); print(f'Size: {t.get_size()}'); pygame.quit()\" "
            "Commit with: git commit -m 'feat: add TileAtlas sprite sheet loader with zoom support'"
        ),
    },
    {
        "id": 12,
        "phase": 2,
        "name": "Create Camera system",
        "prompt": (
            f"Read Task 12 in {PLAN_FILE}. Create pygame_app/map/camera.py. "
            "Camera class with: x, y (world center), zoom (0.3-3.0), target_x/y/zoom for smooth lerp. "
            "Methods: world_to_screen, screen_to_world, get_visible_bounds, update(dt) with lerp, "
            "pan(dx,dy), zoom_at(screen_x, screen_y, factor), center_on(wx,wy), snap_to(wx,wy), resize(w,h). "
            "zoom_at must adjust target position so the world point under cursor stays under cursor after zoom. "
            "Commit with: git commit -m 'feat: add Camera with pan, zoom, smooth lerp, coordinate transforms'"
        ),
    },
    {
        "id": 13,
        "phase": 2,
        "name": "Create HexRenderer",
        "prompt": (
            f"Read Task 13 in {PLAN_FILE}. Create pygame_app/map/hex_renderer.py. "
            "HexRenderer class renders hex tiles, resources, cities, units, fog, highlights. "
            "IMPORTANT API details from the engine: "
            "- game.map is HexMap, game.cities is Dict[str, City], game.units is Dict[str, Unit] "
            "- game.fog is ExponentialFogOfWar with is_visible(x,y) and is_explored(x,y) "
            "- tile.terrain is TerrainType enum — use tile.terrain.name to get string like 'PLAINS' "
            "- tile.has_river is bool, tile.resource is Optional[ResourceType enum] "
            "- city.owner and unit.owner are civ name strings like 'Rome' "
            "- game.player_civ.name gives the player's civ name "
            "- unit.hp and unit.max_hp are ints "
            "Render layers in order: terrain tiles, rivers, resources, cities, units, fog, "
            "selection highlight, move range, attack range, hover highlight. "
            "Import SUBTLE from constants (not redefine it). "
            "Commit with: git commit -m 'feat: add HexRenderer with terrain, cities, units, fog, highlights'"
        ),
    },
    {
        "id": 14,
        "phase": 2,
        "name": "Wire hex map into GameScreen + create Minimap",
        "prompt": (
            f"Read Tasks 14 and 14b in {PLAN_FILE}. "
            "1) Replace the stub game_screen.py with the full version that: "
            "- Creates Camera, TileAtlas, HexRenderer in enter() "
            "- Centers camera on first city (game.cities first value .position) "
            "- Creates map_surface for off-screen rendering "
            "- Handles input: left click selects hex, middle-drag pans, scroll zooms, WASD pans "
            "- Enter key and Next Turn button process turn and refresh UI "
            "- Home key centers on capital "
            "- Resource bar label shows yields with f'{val:.1f}' formatting (NO float garbage) "
            "- draw() renders map to off-screen surface at MAP_X,MAP_Y offset, draws panel backgrounds "
            "2) Create pygame_app/map/minimap.py — 200x200 in bottom-left corner, terrain dots, "
            "city markers, viewport rectangle, click-to-jump. Wire into GameScreen.draw(). "
            "3) Test: python main.py -> New Game -> verify hex map renders, camera works, minimap shows. "
            "Commit with: git commit -m 'feat: wire hex map rendering with camera, minimap, interaction'"
        ),
    },
]


# ── Engine Process Management ───────────────────────────────────

def kill_stale_engines():
    """Kill any existing CynCo engine processes."""
    try:
        if sys.platform == 'win32':
            subprocess.run(
                ['taskkill', '/F', '/IM', 'bun.exe', '/T'],
                capture_output=True, timeout=5
            )
        else:
            subprocess.run(['pkill', '-f', 'bun.*engine/main'], capture_output=True, timeout=5)
    except Exception:
        pass
    time.sleep(1)


def start_engine():
    """Start the CynCo engine as a subprocess."""
    env = os.environ.copy()
    env['LOCALCODE_MODEL'] = MODEL
    env['LOCALCODE_PROVIDER'] = 'llama-cpp'
    env['LOCALCODE_EXPERTISE'] = 'advanced'
    env['LOCALCODE_CONTEXT_LENGTH'] = '65536'
    env['LOCALCODE_TIMEOUT'] = '300000'

    engine_main = os.path.join(ENGINE_DIR, 'engine', 'main.ts')
    print(f"Starting CynCo engine: bun {engine_main}")
    print(f"  Model: {MODEL}")
    print(f"  Working dir: {PROJECT_DIR}")
    print(f"  Port: {WS_PORT}")

    proc = subprocess.Popen(
        ['bun', engine_main],
        cwd=PROJECT_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,  # Unbuffered for real-time reading
    )
    return proc


# ── WebSocket Client ────────────────────────────────────────────

async def run_task(task: dict, log_file):
    """Connect to engine and run a single task."""
    import websockets

    task_id = task['id']
    task_name = task['name']
    prompt = task['prompt']

    print(f"\n{'='*70}")
    print(f"  TASK {task_id}: {task_name}")
    print(f"{'='*70}\n")
    log_file.write(f"\n{'='*70}\n  TASK {task_id}: {task_name}\n{'='*70}\n\n")

    # Try connecting to engine (with retries)
    ws = None
    for port in [WS_PORT, WS_PORT + 1, WS_PORT + 2]:
        for attempt in range(15):
            try:
                ws = await websockets.connect(
                    f"ws://localhost:{port}",
                    max_size=10_000_000,
                    ping_interval=None,   # Disable keepalive pings — model needs time to think
                    ping_timeout=None,
                    close_timeout=30,
                )
                print(f"  Connected to engine on port {port}")
                break
            except (ConnectionRefusedError, OSError):
                if attempt < 14:
                    await asyncio.sleep(2)
        if ws:
            break

    if not ws:
        print("  ERROR: Could not connect to engine!")
        return False

    try:
        # Wait for session.ready (engine sends this on connection)
        ready = False
        try:
            for _ in range(10):  # Try multiple messages — engine may send other events first
                raw = await asyncio.wait_for(ws.recv(), timeout=30)
                event = json.loads(raw)
                etype = event.get('type', '')
                if etype == 'session.ready':
                    model = event.get('model', '?')
                    ctx = event.get('contextLength', '?')
                    print(f"  Session ready — model: {model}, context: {ctx}")
                    ready = True
                    break
                else:
                    print(f"  [pre-ready event: {etype}]")
        except asyncio.TimeoutError:
            print("  WARNING: No session.ready received, proceeding anyway")

        # Send the task prompt
        msg = json.dumps({"type": "user.message", "text": prompt})
        await ws.send(msg)
        print(f"  Sent task prompt ({len(prompt)} chars)")
        print(f"\n--- CynCo Output ---\n")
        log_file.write(f"PROMPT: {prompt}\n\n--- OUTPUT ---\n")

        # Stream events
        full_response = []
        tool_count = 0
        start_time = time.time()

        async for raw_msg in ws:
            event = json.loads(raw_msg)
            etype = event.get('type', '')

            if etype == 'stream.token':
                text = event.get('text', '')
                print(text, end='', flush=True)
                full_response.append(text)
                log_file.write(text)

            elif etype == 'approval.request':
                req_id = event.get('requestId', '')
                tool_name = event.get('toolName', '')
                desc = event.get('description', '')
                risk = event.get('risk', 'low')
                print(f"\n  [AUTO-APPROVE: {tool_name} (risk: {risk})]")
                log_file.write(f"\n[AUTO-APPROVE: {tool_name}]\n")
                response = {
                    "type": "approval.response",
                    "requestId": req_id,
                    "approved": True,
                }
                await ws.send(json.dumps(response))

            elif etype == 'tool.start':
                tool_name = event.get('toolName', '')
                tool_input = event.get('input', {})
                tool_count += 1
                # Show tool name + abbreviated input
                input_str = str(tool_input)[:120]
                print(f"\n  [{tool_name}] {input_str}")
                log_file.write(f"\n[{tool_name}] {input_str}\n")

            elif etype == 'tool.complete':
                tool_name = event.get('toolName', '')
                is_error = event.get('isError', False)
                result = str(event.get('result', ''))[:200]
                marker = 'X' if is_error else 'OK'
                print(f"  [{tool_name} {marker}] {result[:80]}")
                log_file.write(f"[{tool_name} {marker}] {result[:200]}\n")

            elif etype == 'message.complete':
                elapsed = time.time() - start_time
                stop = event.get('stopReason', '?')
                usage = event.get('usage', {})
                in_tok = usage.get('inputTokens', 0)
                out_tok = usage.get('outputTokens', 0)

                print(f"\n\n--- Task {task_id} Complete ---")
                print(f"  Stop: {stop} | Tools: {tool_count} | Time: {elapsed:.1f}s")
                print(f"  Tokens: {in_tok} in / {out_tok} out")
                log_file.write(f"\n--- COMPLETE: {stop} | tools={tool_count} | {elapsed:.1f}s | {in_tok}/{out_tok} tok ---\n")
                break

            elif etype == 'session.error':
                error = event.get('error', 'unknown')
                print(f"\n  SESSION ERROR: {error}")
                log_file.write(f"\nERROR: {error}\n")
                return False

            elif etype == 'context.status':
                util = event.get('utilization', 0)
                if util > 0.8:
                    print(f"\n  [CONTEXT: {util*100:.0f}% used]")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        log_file.write(f"\nERROR: {e}\n")
        return False
    finally:
        await ws.close()

    return True


# ── Main Driver ─────────────────────────────────────────────────

async def main_async(args):
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(LOG_DIR, f'cynco_run_{timestamp}.log')

    # Filter tasks
    tasks = TASKS
    if args.task:
        tasks = [t for t in tasks if t['id'] >= args.task]
    elif args.phase:
        tasks = [t for t in tasks if t['phase'] >= args.phase]

    if not tasks:
        print("No tasks to run!")
        return

    print(f"CivKings CynCo Driver")
    print(f"  Tasks: {len(tasks)} (IDs {tasks[0]['id']}-{tasks[-1]['id']})")
    print(f"  Log: {log_path}")
    print(f"  Interactive: {args.interactive}")
    print()

    # Kill stale engines and start fresh
    kill_stale_engines()
    time.sleep(2)
    engine_proc = start_engine()

    # Wait for engine to start — watch stdout for "Ready" signal
    print("Waiting for engine to start and load model...")
    ready = False
    start_wait = time.time()
    while time.time() - start_wait < 120:  # max 2 minutes
        if engine_proc.poll() is not None:
            print(f"  Engine process died with code {engine_proc.returncode}")
            return
        # Check stdout for ready signal
        try:
            line = engine_proc.stdout.readline()
            if line:
                line = line.strip()
                if line:
                    print(f"  [engine] {line}")
                if 'Ready' in line or 'Waiting for TUI' in line:
                    ready = True
                    print("  Engine is ready!")
                    break
                if 'reachable' in line:
                    # llama-cpp is reachable means almost ready
                    time.sleep(3)
                    ready = True
                    print("  Engine is ready!")
                    break
        except Exception:
            time.sleep(1)

    if not ready:
        print("  WARNING: Engine may not be ready yet, trying to connect anyway...")
        time.sleep(5)

    with open(log_path, 'w', encoding='utf-8') as log_file:
        log_file.write(f"CynCo Driver Run — {timestamp}\n")
        log_file.write(f"Tasks: {[t['id'] for t in tasks]}\n\n")

        for task in tasks:
            success = await run_task(task, log_file)

            if not success:
                print(f"\nTask {task['id']} failed! Check log: {log_path}")
                if args.interactive:
                    try:
                        resp = input("Continue to next task? [y/n]: ").strip().lower()
                        if resp != 'y':
                            break
                    except EOFError:
                        print("  (non-interactive terminal, stopping)")
                        break
                else:
                    break

            if args.interactive and task != tasks[-1]:
                try:
                    print(f"\nTask {task['id']} done. Review the changes, then press Enter to continue...")
                    input()
                except EOFError:
                    print("  (non-interactive terminal, continuing automatically)")
                    time.sleep(3)

            # Brief pause between tasks to let engine reset
            await asyncio.sleep(3)

    # Cleanup
    print("\nShutting down engine...")
    engine_proc.terminate()
    try:
        engine_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        engine_proc.kill()

    print(f"Done! Full log at: {log_path}")


def main():
    parser = argparse.ArgumentParser(description='Drive CynCo to execute CivKings overhaul plan')
    parser.add_argument('--task', type=int, help='Start from this task ID')
    parser.add_argument('--phase', type=int, help='Start from this phase number')
    parser.add_argument('--interactive', action='store_true', help='Pause between tasks for review')
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
