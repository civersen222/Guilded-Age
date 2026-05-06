"""Run the 'Make It Playable' plan tasks through CynCo sequentially."""
import asyncio
import json
import sys
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TASKS = [
    {
        "id": 1,
        "name": "Fix event log",
        "prompt": """Read docs/CYNCO_PLAYABLE_PLAN.md Task 1. The event log shows 0 entries after turns.

In pygame_app/screens/game_screen.py, find EVERY place where game.process_turn() is called.
Immediately after each call, add:
  events = game.state.turn_events or []
  for evt_text in events:
      self._event_log.add_event(str(evt_text), "info")

There are probably 2-3 places process_turn is called (Next Turn button, Enter key, action bar).
Fix ALL of them.

Test: python -c "import sys; sys.path.insert(0,'.'); from game import Game; from game_data import CIVILIZATIONS; g=Game(CIVILIZATIONS['Rome']); g.process_turn(); print(f'Events: {len(g.state.turn_events or [])} - {(g.state.turn_events or [])[:3]}')"

Commit: git add pygame_app/; git commit -m 'fix: populate event log after every process_turn call'""",
    },
    {
        "id": 2,
        "name": "Auto-research next tech",
        "prompt": """Read docs/CYNCO_PLAYABLE_PLAN.md Task 2. Research stops after first tech completes.

In pygame_app/screens/game_screen.py, after every process_turn() call, add a check:
  if game.tech_manager.current_research is None:
      available = game.tech_manager.get_available_techs()
      if available:
          tech = available[0]
          tech_name = tech.name if hasattr(tech, 'name') else str(tech)
          game.tech_manager.start_research(tech)
          self._event_log.add_event(f"Auto-researching: {tech_name}", "science")

Test by processing 20 turns and checking research progresses.

Commit: git add pygame_app/; git commit -m 'feat: auto-select next research when current completes'""",
    },
    {
        "id": 3,
        "name": "Production popup works",
        "prompt": """Read docs/CYNCO_PLAYABLE_PLAN.md Task 3. Make Build button in production popup actually work.

Read pygame_app/popups/production.py handle_event method. When the Build button is pressed,
it should call: self._city.assign_production(selected_item_name, researched_techs=researched)
where researched = set(self._game.tech_manager.researched.keys()) if hasattr(self._game, 'tech_manager') else set()

Check that:
1. The Build button event is detected (UI_BUTTON_PRESSED matching self.build_btn or similar)
2. The selected item is retrieved from the UISelectionList
3. city.assign_production is called with correct args
4. The popup shows feedback ("Building Warrior" or "Cannot build - requires X")
5. After assigning, refresh the popup to show current production

Test: python -c "import sys; sys.path.insert(0,'.'); from game import Game; from game_data import CIVILIZATIONS; g=Game(CIVILIZATIONS['Rome']); city=list(g.cities.values())[0]; city.assign_production('Warrior'); print(f'Production: {city.current_production}')"

Commit: git add pygame_app/; git commit -m 'fix: production popup Build button assigns production to city'""",
    },
    {
        "id": 4,
        "name": "Show move range",
        "prompt": """Read docs/CYNCO_PLAYABLE_PLAN.md Task 4. Show blue hexes where unit can move.

In pygame_app/screens/game_screen.py _select_unit() method, after selecting a unit:
1. Get moves = unit.moves_left (int, movement points remaining)
2. BFS from unit.position: expand to adjacent hexes up to 'moves' steps away
3. For adjacency, use game.map.get_neighbors(x, y) — this returns list of HexTile objects, get their (x,y) from tile.x, tile.y
4. Skip water tiles (tile.terrain.name in ('WATER_COAST', 'OCEAN')) for land units
5. Skip hexes with enemy units
6. Add all reachable hexes to self._hex_renderer.move_range set

The hex_renderer already draws blue outlines for hexes in self.move_range.

When clicking a hex IN the move range with a unit selected, move the unit there:
  game.military_manager.move_unit(unit, (hx, hy))
  unit.position = (hx, hy)  # in case move_unit doesn't update it

Commit: git add pygame_app/; git commit -m 'feat: show blue move range when unit selected, click to move'""",
    },
    {
        "id": 5,
        "name": "AI does things",
        "prompt": """Read docs/CYNCO_PLAYABLE_PLAN.md Task 5. AI players exist but do nothing visible.

Read game.py _process_ai_turn() and ai.py take_turn(). Verify the AI:
1. Has cities (check game.cities for AI-owned cities)
2. Researches techs (check game.research dict for AI tech managers)
3. Builds units in cities (calls city.assign_production)
4. Returns event strings that get added to turn events

If _process_ai_turn doesn't call ai.take_turn(game), fix it to do so.
If the AI has no cities, it can't do anything — verify AI cities are created in Game.__init__.

Run test: python -c "import sys; sys.path.insert(0,'.'); from game import Game; from game_data import CIVILIZATIONS; g=Game(CIVILIZATIONS['Rome'], [CIVILIZATIONS['Egypt']]); [g.process_turn() for _ in range(20)]; print('AI cities:', [(n,c.population) for n,c in g.cities.items() if c.owner != 'Rome']); print('AI units:', len([u for u in g.units.values() if u.owner != 'Rome']))"

Commit: git add game.py ai.py; git commit -m 'fix: AI actively researches, builds, and plays each turn'""",
    },
    {
        "id": 6,
        "name": "Dynasty spawns heirs",
        "prompt": """Read docs/CYNCO_PLAYABLE_PLAN.md Task 6. Dynasty has only 1 member.

In game.py process_turn(), add dynasty/character aging:
1. If game.dynasty and game.dynasty.root:
   ruler = game.dynasty.root
   aged = ruler.age_up()  # returns Optional[str] event description
   if aged: add to turn events
2. Every 10 turns (game.state.turn % 10 == 0), if ruler has no children:
   from simulation import generate_child
   child = generate_child(f"{ruler.name} II", ruler, ruler)  # self-paired for simplicity
   game.dynasty.all_characters[child.id] = child
   ruler.children_ids.append(child.id)
   if hasattr(game, 'dynasty_manager'): game.dynasty_manager.add_member(child)
   add event: "A heir is born: {child.name}"

Test: play 30 turns, check dynasty has 2+ members.

Commit: git add game.py; git commit -m 'feat: dynasty aging and heir generation every 10 turns'""",
    },
    {
        "id": 7,
        "name": "Context-sensitive action bar",
        "prompt": """Read docs/CYNCO_PLAYABLE_PLAN.md Task 7. Action bar should change based on selection.

Check pygame_app/panels/action_bar.py — verify it has these modes in ACTION_BUTTONS dict:
  "default": [("Next Turn", "Next Turn"), ("Tech Tree", "Tech Tree"), ("Diplomacy", "Diplomacy"), ("Dynasty", "Dynasty"), ("Save", "Save")]
  "unit_selected": [("Move", "Move"), ("Fortify", "Fortify"), ("Skip", "Skip"), ("Deselect", "Deselect")]
  "settler_selected": [("Settle", "Settle"), ("Move", "Move"), ("Skip", "Skip"), ("Deselect", "Deselect")]
  "city_selected": [("Production", "Production"), ("Deselect", "Deselect")]

In game_screen.py:
- _select_unit(): call self._action_bar.set_mode("settler_selected" if unit.unit_type == "Settler" else "unit_selected")
- When clicking a city: call self._action_bar.set_mode("city_selected")
- On Escape/deselect: call self._action_bar.set_mode("default")
- Handle "Deselect" action: clear selection, set mode default

Commit: git add pygame_app/; git commit -m 'feat: action bar shows unit/settler/city/default buttons based on selection'""",
    },
    {
        "id": 8,
        "name": "Fix zoom tile sizing",
        "prompt": """Read docs/CYNCO_PLAYABLE_PLAN.md Task 8. Hex tiles still have gaps at some zoom levels.

In pygame_app/map/hex_renderer.py, find where tile_surface is scaled. Change from square scaling to rectangular:

  target_w = max(4, int(HEX_SIZE * 2.0 * zoom * 1.18))
  target_h = max(4, int(HEX_SIZE * 1.732 * zoom * 1.18))

And scale with: pygame.transform.smoothscale(base_tile, (target_w, target_h))

Also scale city and unit sprites proportionally:
  city_size = max(16, int(64 * zoom))
  unit_size = max(12, int(48 * zoom))

Commit: git add pygame_app/; git commit -m 'fix: rectangular tile scaling matching hex proportions, sprite zoom scaling'""",
    },
    {
        "id": 85,
        "name": "Fix fog of war exploration",
        "prompt": """Fog of war does not update when units move. When a unit moves to a new position,
the fog should reveal tiles around its new position.

In pygame_app/screens/game_screen.py, after a unit moves (in _move_selected_unit or wherever
unit.position changes), update the fog:
  # Reveal tiles around new unit position
  sources = []
  for city in game.cities.values():
      if city.owner == game.player_civ.name:
          sources.append((city.position[0], city.position[1], 3))
  for unit in game.units.values():
      if unit.owner == game.player_civ.name:
          sources.append((unit.position[0], unit.position[1], 2))
  game.fog.update_visibility(sources)

Also do this in process_turn() handling — after each turn, recalculate fog for all player units/cities.

Test: move a unit, verify fog.explored grows.

Commit: git add pygame_app/ game.py; git commit -m 'fix: update fog of war when units move and each turn'""",
    },
    {
        "id": 9,
        "name": "Readable side panels",
        "prompt": """Read docs/CYNCO_PLAYABLE_PLAN.md Task 9. Side panel text barely readable.

In pygame_app/panels/city_panel.py refresh():
- Each city button text should be: "{city.name} (Pop {city.population})" on first line
- If city.current_production: append " [{city.current_production}]"
- If no production: append " [IDLE]"
- Button height should be 40px minimum

In pygame_app/panels/unit_panel.py refresh():
- Each unit button text: "{unit.unit_type} HP:{unit.hp}/{unit.max_hp} Mv:{unit.moves_left}"
- Button height 35px minimum

Commit: git add pygame_app/panels/; git commit -m 'fix: readable city and unit panel text with proper sizing'""",
    },
    {
        "id": 10,
        "name": "Turn summary popup",
        "prompt": """Read docs/CYNCO_PLAYABLE_PLAN.md Task 10. Show what happened each turn.

In pygame_app/screens/game_screen.py, after process_turn() and event log population,
show the turn summary popup:
  events = game.state.turn_events or []
  if events and hasattr(self, '_turn_summary'):
      self._turn_summary.show(self.ui_manager, events, game.state.turn)

Verify pygame_app/panels/turn_summary.py show() method:
- Creates a UIWindow with title "Turn {turn} Summary"
- Lists all events as text
- Has a "Dismiss" button
- Window size: 500x400, centered

If show() crashes, check UIWindow constructor uses positional rect, window_display_title= (NOT window_title or relative_rect).

Commit: git add pygame_app/; git commit -m 'feat: turn summary popup shows events after each turn'""",
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
            e = time.time() - start
            print(f"\n  [{event.get('stopReason')} | {tools} tools | {e:.0f}s]")
            break
        elif t == "approval.request":
            await ws.send(json.dumps({"type": "approval.response", "requestId": event["requestId"], "approved": True}))
        elif t == "tool.start":
            tools += 1
            print(f"\n  [{event.get('toolName')}] {str(event.get('input', {}))[:100]}")
        elif t == "tool.complete":
            print(f"  <- {'ERR' if event.get('isError') else 'OK'}: {str(event.get('result', ''))[:70]}")
        elif t == "session.error":
            print(f"\n  SESSION ERROR: {event.get('error')}")
            return False
    await ws.close()
    return True


async def main():
    sid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    tasks = [t for t in TASKS if t["id"] >= sid]
    print(f"Running {len(tasks)} tasks (IDs {tasks[0]['id']}-{tasks[-1]['id']})\n")
    for task in tasks:
        print(f"{'='*70}")
        print(f"  TASK {task['id']}: {task['name']}")
        print(f"{'='*70}")
        ok = await send_task(task["prompt"])
        if not ok:
            print(f"\n  FAILED at task {task['id']}")
            break
        print()
        await asyncio.sleep(2)
    print(f"\n{'='*70}\n  BATCH COMPLETE\n{'='*70}")


asyncio.run(main())
