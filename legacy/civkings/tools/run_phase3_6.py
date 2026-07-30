"""Run Phase 3-6 tasks through CynCo."""
import asyncio
import json
import sys
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TASKS = [
    # ── Phase 3: UI Panels ──
    {
        "id": 15,
        "name": "Resource Bar panel",
        "prompt": """Create pygame_app/panels/resource_bar.py.

ResourceBar class that displays game yields in a top bar.

__init__(self, ui_manager, game):
- Create a pygame_gui UIPanel spanning (0, 0, SCREEN_WIDTH, RESOURCE_BAR_HEIGHT=40)
- Create UILabels inside it for: civ name, food, production, gold, science, culture, faith, turn counter
- Space them evenly across the bar

refresh(self, game):
- Read yields from game.city_manager.get_total_yields(civ_name, game.map.tiles)
- civ_name = game.player_civ.name
- game.gold is Dict[str, int] keyed by civ name
- Format ALL floats with f"{val:.1f}" — NEVER show raw floats like 1.920000000004
- Gold should show: "Gold: 100 (+21/t)" where +21 is the per-turn income from yields
- Update each label's text

destroy(self): kill all UI elements

Import SCREEN_WIDTH, RESOURCE_BAR_HEIGHT, GOLD as GOLD_COLOR from pygame_app.constants.

After creating, commit: git add pygame_app/panels/resource_bar.py; git commit -m "feat: add ResourceBar panel with formatted yields"
""",
    },
    {
        "id": 16,
        "name": "City Panel (left sidebar)",
        "prompt": """Create pygame_app/panels/city_panel.py.

CityPanel class — left sidebar listing all player cities.

__init__(self, ui_manager, rect): Create UIPanel at rect, store ui_manager.

refresh(self, game):
- Get player cities: [c for c in game.cities.values() if c.owner == game.player_civ.name]
- Clear existing city labels
- For each city create a UIButton inside the panel with text like "Roma (Pop 3) - Building: Granary"
- If city has no current_production, show "IDLE" in the button text
- Store buttons in self.city_buttons dict mapping button -> city

handle_event(self, event) -> optional city:
- If a city button was pressed, return the corresponding city (for camera centering)

destroy(self): kill panel and all children

Use LEFT_PANEL_WIDTH=260, RESOURCE_BAR_HEIGHT from constants.
Panel rect: (0, RESOURCE_BAR_HEIGHT, LEFT_PANEL_WIDTH, 400)

After creating, commit: git add pygame_app/panels/city_panel.py; git commit -m "feat: add CityPanel sidebar listing player cities"
""",
    },
    {
        "id": 17,
        "name": "Unit Panel (left sidebar below cities)",
        "prompt": """Create pygame_app/panels/unit_panel.py.

UnitPanel class — left sidebar below city panel, listing player units.

__init__(self, ui_manager, rect): Create UIPanel, store manager.

refresh(self, game):
- Get player units: [u for u in game.units.values() if u.owner == game.player_civ.name]
- Clear old buttons
- For each unit: UIButton with text "{unit.unit_type} HP:{unit.hp}/{unit.max_hp} Mv:{unit.moves_left}"
- Units with moves_left > 0 should look different (maybe add * prefix)

handle_event(self, event) -> optional unit

destroy(self): kill all

Panel rect: (0, RESOURCE_BAR_HEIGHT + 400, LEFT_PANEL_WIDTH, 300)

After creating, commit: git add pygame_app/panels/unit_panel.py; git commit -m "feat: add UnitPanel sidebar listing player units"
""",
    },
    {
        "id": 18,
        "name": "Event Log (right sidebar)",
        "prompt": """Create pygame_app/panels/event_log.py.

EventLog class — right sidebar with scrollable event history.

__init__(self, ui_manager, rect):
- Create UIPanel at rect
- Create UITextBox inside for scrollable HTML text
- self.events = [] list of event strings

add_event(self, text: str, category: str = "info"):
- Color map: economy=gold(#c5a059), combat=red(#b23a3a), growth=green(#3ab24e), science=blue(#3a78b2), dynasty=purple(#8a3ab2), info=white(#e0e0e0)
- Prepend colored HTML to the text box: '<font color="{color}">{text}</font><br>'
- Keep last 100 events max

add_turn_events(self, events: list, turn: int):
- For each event string, try to categorize it (if contains "gold"/"tax" -> economy, "combat"/"attack" -> combat, "grew"/"food" -> growth, "research"/"tech" -> science)
- Add with appropriate category
- Add a separator: "--- Turn {turn} ---"

destroy(self): kill all

Panel rect: (SCREEN_WIDTH - RIGHT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT, RIGHT_PANEL_WIDTH, SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT)

After creating, commit: git add pygame_app/panels/event_log.py; git commit -m "feat: add EventLog panel with color-coded scrollable events"
""",
    },
    {
        "id": 19,
        "name": "Turn Summary popup",
        "prompt": """Create pygame_app/panels/turn_summary.py.

TurnSummary class — modal popup showing all events from the last turn.

show(self, ui_manager, events: list, turn: int):
- If no events, don't show anything
- Create a UIWindow centered on screen, title "Turn {turn} Summary"
- Size: 500x400
- Inside: UITextBox listing all events as HTML (colored by category like EventLog)
- "Dismiss" UIButton at bottom
- Store window reference in self.window

handle_event(self, event) -> bool:
- If dismiss button pressed, kill the window, return True
- Return False otherwise

is_visible property: return whether window exists and is alive

After creating, commit: git add pygame_app/panels/turn_summary.py; git commit -m "feat: add TurnSummary popup for start-of-turn notifications"
""",
    },
    {
        "id": 20,
        "name": "Action Bar (bottom)",
        "prompt": """Create pygame_app/panels/action_bar.py.

ActionBar class — bottom bar with context-sensitive buttons.

__init__(self, ui_manager):
- Create UIPanel at (0, SCREEN_HEIGHT - ACTION_BAR_HEIGHT, SCREEN_WIDTH, ACTION_BAR_HEIGHT)
- self.buttons = {} dict
- self.mode = 'default'  # 'default', 'unit_selected', 'city_selected'

set_mode(self, mode: str, context=None):
- Clear existing buttons
- If mode == 'default': create buttons for "Next Turn" (Enter), "Tech Tree" (T), "Diplomacy" (D)
- If mode == 'unit_selected': create "Move" (M), "Attack" (A), "Fortify" (F), "Skip" (Space)
- If mode == 'city_selected': create "Production" (P)
- Each button is 100x35, spaced 110px apart, starting 10px from left

handle_event(self, event) -> optional str:
- If a button was pressed, return the button's action name as a string

destroy(self): kill all

Use SCREEN_WIDTH, SCREEN_HEIGHT, ACTION_BAR_HEIGHT from constants.

After creating, commit: git add pygame_app/panels/action_bar.py; git commit -m "feat: add ActionBar with context-sensitive buttons"
""",
    },
    {
        "id": 21,
        "name": "Wire all panels into GameScreen",
        "prompt": """Modify pygame_app/screens/game_screen.py to integrate all the new panels.

Read the current game_screen.py first, then modify it:

In enter():
- Import and create: ResourceBar, CityPanel, UnitPanel, EventLog, TurnSummary, ActionBar
- ResourceBar(self.ui_manager, self.app.game)
- CityPanel(self.ui_manager, pygame.Rect(0, 40, 260, 400))
- UnitPanel(self.ui_manager, pygame.Rect(0, 440, 260, 300))
- EventLog(self.ui_manager, pygame.Rect(SCREEN_WIDTH-280, 40, 280, SCREEN_HEIGHT-90))
- TurnSummary() — no args needed until show() is called
- ActionBar(self.ui_manager)
- Remove the old placeholder UILabel for resources (replaced by ResourceBar)

In update(dt):
- Call self.resource_bar.refresh(game)
- Call self.city_panel.refresh(game)
- Call self.unit_panel.refresh(game)

In handle_event():
- When Next Turn pressed: call game.process_turn(), get events from game.state.turn_events
- Pass events to event_log.add_turn_events() and turn_summary.show()
- Handle city_panel clicks: center camera on city, set selected_hex
- Handle unit_panel clicks: center camera on unit, set selected_hex
- Handle action_bar clicks: process the action
- Handle turn_summary dismiss

In exit():
- Destroy all panels

After modifying, verify: python -m py_compile pygame_app/screens/game_screen.py
Then commit: git add pygame_app/screens/game_screen.py; git commit -m "feat: wire all UI panels into GameScreen"
""",
    },

    # ── Phase 4: Key Popups ──
    {
        "id": 22,
        "name": "Production Popup",
        "prompt": """Create pygame_app/popups/production.py.

ProductionPopup class — UIWindow for managing city production queue.

show(self, ui_manager, city, game):
- Create UIWindow "Production: {city.name}", size 600x500, centered
- LEFT side: UISelectionList of available items grouped as:
  "-- UNITS --", then each unit from game_data.UNIT_TYPES: "{name} ({cost} prod)"
  "-- BUILDINGS --", then each building from game_data.BUILDINGS not already built in city
- RIGHT side: UITextBox showing current production queue (city.production_queue)
- Show current production rate from city yields
- "Build" button: calls city.assign_production(selected_item)
- "Close" button

handle_event(self, event) -> bool:
- Handle Build button: assign production, refresh display
- Handle Close button: kill window
- Return True if handled

Import BUILDINGS, UNIT_TYPES from game_data.

After creating, commit: git add pygame_app/popups/production.py; git commit -m "feat: add ProductionPopup for city production management"
""",
    },
    {
        "id": 23,
        "name": "Tech Tree Popup",
        "prompt": """Create pygame_app/popups/tech_tree.py.

TechTreePopup class — shows all technologies organized by era.

show(self, ui_manager, game):
- Create UIWindow "Technology Tree", size 900x600, centered
- Get all techs from game_data.TECHNOLOGIES
- Get researched techs from game.tech_manager (has_tech method)
- Get current research from game.tech_manager.current_research
- Get available techs from game.tech_manager.get_available_techs()
- Build HTML content for UITextBox organized by era:
  "=== ANCIENT ERA ===\n"
  For each tech in era:
    If researched: "[DONE] {name}"
    If currently researching: "[RESEARCHING] {name} ({progress}/{cost})"
    If available: "[AVAILABLE] {name} - Cost: {cost}"
    If locked: "[LOCKED] {name} - Requires: {prerequisites}"
- Color code: green for done, blue for current, white for available, grey for locked
- "Research" button: start researching selected available tech
- "Close" button

handle_event(self, event) -> bool

After creating, commit: git add pygame_app/popups/tech_tree.py; git commit -m "feat: add TechTreePopup with era-organized tech display"
""",
    },
    {
        "id": 24,
        "name": "Diplomacy Popup",
        "prompt": """Create pygame_app/popups/diplomacy.py.

DiplomacyPopup class — shows diplomatic relations with all known civs.

show(self, ui_manager, game):
- Create UIWindow "Diplomacy", size 700x500, centered
- LEFT: UISelectionList of known civ names (all civs in game.civilizations except player)
- RIGHT: UITextBox showing selected civ's details:
  "Relations with {civ}: {score}"
  "Status: {Allied/Neutral/Hostile/At War}"
  "Treaties: {list of active treaties}"
- Action buttons: "Declare War", "Propose Alliance", "Trade Agreement"
- Use game.diplomacy_manager methods: get_relation(), declare_war(), propose_alliance(), is_at_war(), is_allied()

handle_event(self, event) -> bool

After creating, commit: git add pygame_app/popups/diplomacy.py; git commit -m "feat: add DiplomacyPopup with relations and actions"
""",
    },
    {
        "id": 25,
        "name": "Dynasty Popup",
        "prompt": """Create pygame_app/popups/dynasty.py.

DynastyPopup class — shows current ruler, heirs, traits, stats.

show(self, ui_manager, game):
- Create UIWindow "Dynasty", size 600x500, centered
- If game.dynasty and game.dynasty.root:
  ruler = game.dynasty.root (or first character in game.characters)
  Show: name, age (ruler.age), stats (ruler.base_stats dict with diplomacy/martial/stewardship/intrigue)
  Show traits: ruler.traits list
  Show dynasty prestige: game.dynasty.calculate_dynastic_prestige()
- If game.court:
  Show court positions from game.court
- "Close" button

handle_event(self, event) -> bool

After creating, commit: git add pygame_app/popups/dynasty.py; git commit -m "feat: add DynastyPopup with ruler stats, traits, court"
""",
    },
    {
        "id": 26,
        "name": "Combat Result Popup",
        "prompt": """Create pygame_app/popups/combat_result.py.

CombatResultPopup class — shows outcome after combat.

show(self, ui_manager, result):
- result is a CombatResult object with: attacker_victory, defender_victory, description, attacker_casualties, defender_casualties
- Create UIWindow "Battle Result", size 400x350, centered
- Show: "VICTORY!" or "DEFEAT!" header
- Show casualties from both sides
- Show XP gained
- "Continue" button

handle_event(self, event) -> bool

After creating, commit: git add pygame_app/popups/combat_result.py; git commit -m "feat: add CombatResultPopup showing battle outcomes"
""",
    },
    {
        "id": 27,
        "name": "Event Choice Popup",
        "prompt": """Create pygame_app/popups/event_choice.py.

EventChoicePopup class — shows random events with player choices.

show(self, ui_manager, event):
- event is an Event object with: name, description, choices (list of dicts), effects (dict)
- Create UIWindow "{event.name}", size 450x400, centered
- Show event description text in UITextBox
- If event has choices: create a UIButton for each choice showing the choice text and effects
- If no choices: show effects and a single "OK" button
- When choice selected: call event.evaluate_choice(choice)

handle_event(self, event) -> bool

After creating, commit: git add pygame_app/popups/event_choice.py; git commit -m "feat: add EventChoicePopup for random event decisions"
""",
    },

    # ── Phase 5: Sound + Effects (minimal) ──
    {
        "id": 30,
        "name": "Sound Manager",
        "prompt": """Create pygame_app/audio/sound_manager.py.

SoundManager class — loads and plays sound effects.

__init__(self, sounds_dir='assets/sounds'):
- self.sounds = {} dict mapping (category, name) -> pygame.mixer.Sound
- self.enabled = True
- Try to load any .ogg/.wav files found in sounds_dir subdirectories
- If no sound files exist, that's OK — just log and continue (graceful fallback)

play(self, category: str, name: str, volume: float = 0.7):
- If not enabled, return
- Look up (category, name) in self.sounds
- If found, set volume and play
- If not found, silently ignore (no crash)

toggle(self): flip self.enabled

Also create a placeholder sound generator: tools/generate_placeholder_sounds.py
- Uses wave module to create simple sine wave .wav files
- Creates: assets/sounds/ui/click.wav (short 100ms click), assets/sounds/ui/confirm.wav (200ms chime)
- Run the generator after creating it

After creating both files, commit: git add pygame_app/audio/sound_manager.py tools/generate_placeholder_sounds.py assets/sounds/; git commit -m "feat: add SoundManager with placeholder sounds"
""",
    },
    {
        "id": 31,
        "name": "Music Manager",
        "prompt": """Create pygame_app/audio/music_manager.py.

MusicManager class — streams era-based background music.

__init__(self, music_dir='assets/music'):
- self.music_dir = music_dir
- self.current_era = None
- self.enabled = True
- Map era names to filenames: {'ANCIENT': 'ancient.ogg', 'CLASSICAL': 'classical.ogg', etc.}

update_era(self, era_name: str):
- If era hasn't changed, return
- If music file exists for this era:
  pygame.mixer.music.fadeout(2000)
  pygame.mixer.music.load(path)
  pygame.mixer.music.play(-1, fade_ms=2000)
- Update self.current_era
- If file doesn't exist, silently skip (graceful fallback)

stop(self): pygame.mixer.music.stop()
toggle(self): flip enabled, stop if disabled

After creating, commit: git add pygame_app/audio/music_manager.py; git commit -m "feat: add MusicManager with era-based background music"
""",
    },
    {
        "id": 34,
        "name": "Particle System",
        "prompt": """Create pygame_app/effects/particles.py.

ParticleEmitter class — lightweight particles for visual feedback.

Particle dataclass: x, y, vx, vy, lifetime, max_lifetime, color, size

ParticleEmitter:
- __init__(self): self.particles = []

- emit(self, x, y, count=10, color=(255,200,50), lifetime=1.0, speed=50):
  Create count particles at (x,y) with random velocities in circle, store in self.particles

- update(self, dt):
  For each particle: update position by velocity*dt, reduce lifetime
  Remove expired particles (lifetime <= 0)

- draw(self, surface):
  For each particle: calculate alpha from remaining lifetime ratio
  Draw small circle with that alpha (use a temp surface with per-pixel alpha)

After creating, commit: git add pygame_app/effects/particles.py; git commit -m "feat: add ParticleEmitter for combat and celebration effects"
""",
    },

    # ── Phase 6: Engine Fixes ──
    {
        "id": 36,
        "name": "Fix AI player initialization",
        "prompt": """Read game.py and fix AI player initialization so AI opponents actually appear on the map with cities and units.

Current problem: Game.__init__ creates self.ai_players as empty dict. The new_game_dialog adds AIPlayer instances to it, but they don't get starting cities or units on the map.

Fix needed in game.py:
1. Find where the player's starting city is created (around line 120-140)
2. After player setup, add a method or code block that also creates starting positions for AI civs
3. For each AI player in self.ai_players:
   - Find a starting tile at least 5 hexes from all existing cities (use self.map.get_distance)
   - Create a City for the AI civ at that position
   - Create a starting Unit (Militia or Warrior) for the AI at that position
   - Add to self.cities, self.units, self.city_manager, self.military_manager
4. Update process_turn() to make sure AI players actually take actions each turn

IMPORTANT: Read the existing code carefully. Don't break what already works. Add the AI setup code after the player setup code.

Test: python -c "from game import Game; from game_data import CIVILIZATIONS; from ai import AIPlayer; g = Game(CIVILIZATIONS['Rome']); g.ai_players['Egypt'] = AIPlayer('Egypt'); print(f'AI cities: {[c.name for c in g.cities.values() if c.owner != g.player_civ.name]}')"

After fixing, commit: git add game.py; git commit -m "fix: AI players now spawn with starting cities and units"
""",
    },
    {
        "id": 38,
        "name": "Verify and fix save/load",
        "prompt": """Read save_system.py and verify it works with the current game state including all managers.

Test save/load roundtrip:
python -c "
from game import Game
from game_data import CIVILIZATIONS
g = Game(CIVILIZATIONS['Rome'])
g.process_turn()
path = g.save_game('test_save')
print(f'Saved to: {path}')
loaded = Game.load_game(path)
if loaded:
    print(f'Loaded: turn={loaded.state.turn}, cities={len(loaded.cities)}')
else:
    print('Load failed!')
"

If save/load works, just commit a message confirming it.
If it fails, fix the issues and commit the fix.

After testing/fixing, commit any changes.
""",
    },
]


async def send_task(prompt, port=9160):
    from websockets.asyncio.client import connect
    ws = await connect(f"ws://localhost:{port}", ping_interval=None, ping_timeout=None, max_size=50_000_000)
    try:
        await asyncio.wait_for(ws.recv(), timeout=3)
    except:
        pass

    await ws.send(json.dumps({"type": "user.message", "text": prompt}))
    tools = 0
    start = time.time()

    for _ in range(1000):
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=300)
        except asyncio.TimeoutError:
            print("\n  TIMEOUT!")
            return False

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
            await ws.send(json.dumps({"type": "approval.response", "requestId": event["requestId"], "approved": True}))
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
            return False
    await ws.close()
    return True


async def main():
    start_id = int(sys.argv[1]) if len(sys.argv) > 1 else TASKS[0]["id"]
    tasks = [t for t in TASKS if t["id"] >= start_id]
    print(f"Running {len(tasks)} tasks (IDs {tasks[0]['id']}-{tasks[-1]['id']})\n")

    for task in tasks:
        print(f"{'='*70}")
        print(f"  TASK {task['id']}: {task['name']}")
        print(f"{'='*70}")
        ok = await send_task(task["prompt"])
        if not ok:
            print(f"\n  TASK {task['id']} FAILED")
            break
        print()
        await asyncio.sleep(2)

    print(f"\n{'='*70}\n  BATCH COMPLETE\n{'='*70}")

asyncio.run(main())
