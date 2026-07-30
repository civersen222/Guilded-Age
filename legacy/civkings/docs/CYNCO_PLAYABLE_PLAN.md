# CivKings: Make It Playable — CynCo Execution Plan

## Current State (as of Turn 6 test)
- 0 crashes on basic operations
- All 10 gameplay tasks completed ✅
- Event log, auto-research, production, move range, AI, dynasty, action bar, hex rendering, side panels, turn summary all working

## Priority: GAMEPLAY LOOP FIRST, POLISH SECOND

---

## Task 1: Fix the event log — show what's happening each turn

The event log (pygame_app/panels/event_log.py) has 0 entries because game_screen.py 
doesn't pass turn events to it after process_turn(). 

Fix: In game_screen.py, everywhere process_turn() is called, immediately after:
```
events = game.state.turn_events or []
for evt_text in events:
    self._event_log.add_event(evt_text, "info")
```

Test: process 3 turns, verify event_log.events has entries.

---

## Task 2: Auto-select next research when current completes

game.tech_manager.current_research is None after initial tech finishes.
Players need to either auto-research or be prompted.

Fix in game_screen.py: after process_turn(), check if game.tech_manager.current_research is None.
If so, get available = game.tech_manager.get_available_techs(). If any available, 
auto-start the first one AND add an event: "Started researching: {tech.name}".
Also show a notification to the player.

Test: play 20 turns, verify research progresses continuously.

---

## Task 3: Make production popup functional — build units and buildings

When clicking a city and selecting an item in the production popup, clicking "Build" 
should call city.assign_production(item_name). Verify by:
1. Click city to open production popup
2. Select "Warrior" from the list
3. Click Build
4. Verify city.current_production == "Warrior"
5. Process turns until production completes
6. Verify a new Warrior unit appears

Fix: Read production.py handle_event(). Make sure the Build button calls 
city.assign_production(selected_item) with correct params. The city.assign_production 
method signature is: assign_production(item: str, researched_techs=None, owned_resources=None)
Pass researched_techs=set(game.tech_manager.researched.keys()).

Test: assign Warrior, process 5 turns, check game.units grew.

---

## Task 4: Show move range when unit selected

When a unit is selected, the hex renderer should show which hexes the unit can move to
(blue highlighted hexes). Currently move_range is cleared but never populated.

Fix in game_screen.py _select_unit(): after selecting a unit, calculate reachable hexes:
- Get unit.moves_left (movement points)
- BFS from unit.position, expanding up to moves_left steps
- Add each reachable (hx, hy) to self._hex_renderer.move_range set
- Skip water tiles (terrain OCEAN, WATER_COAST) for land units

When clicking a hex in the move_range, move the unit there.
When clicking outside move_range, deselect.

Test: select Militia unit, verify blue hexes appear around it.

---

## Task 5: Make AI actually do things each turn

AI players (Rome, Greece, Mesopotamia) exist but their turns produce no visible results.

Fix in game.py _process_ai_turn(): verify it calls ai.take_turn(self) and that the AI:
- Researches technologies (picks from available, accumulates progress)
- Builds units in its cities
- Moves units on the map
- AI actions should generate event strings returned from _process_ai_turn()

Test: play 20 turns, check AI cities have grown (population > 1), AI has built units,
AI has researched techs.

---

## Task 6: Dynasty — spawn heirs, show family tree

Dynasty currently has only the founder. Characters should age each turn, 
have children, and eventually die with succession.

Fix in game.py process_turn():
- Call ruler.age_up() each turn (from simulation.py)
- Every ~10 turns, if ruler has no children, generate a child via generate_child()
- Add children to game.dynasty via dynasty_manager.add_member()
- Show all members in the dynasty popup (already fixed to list all)

Test: play 30 turns, verify dynasty has 2+ members.

---

## Task 7: Make the action bar context-sensitive

When a unit is selected, the action bar should show unit actions (Move, Fortify, Skip).
When a Settler is selected, show "Settle" button additionally.
When a city is selected, show "Production" button.
When nothing is selected, show default buttons (Next Turn, Tech Tree, etc.)

Fix in game_screen.py: 
- _select_unit(): call self._action_bar.set_mode("unit_selected") or "settler_selected"
- When clicking a city: call self._action_bar.set_mode("city_selected")
- On deselect: call self._action_bar.set_mode("default")

Verify action_bar.py has these modes with the right buttons defined.

Test: click unit -> see Move/Fortify/Skip. Click settler -> see Settle. Click empty -> default.

---

## Task 8: Zoom rendering — eliminate ALL gaps

The hex tile images still have thin gaps at certain zoom levels because the tile size 
multiplier doesn't perfectly match hex geometry at all scales.

Fix: Instead of a single multiplier (2.5), compute the exact pixel size needed:
- Hex horizontal spacing = HEX_SIZE * 1.5 * zoom (distance between centers)
- Hex width needs to be = HEX_SIZE * 2.0 * zoom (to cover full hex)
- But tiles are hex-shaped (transparent corners) so they need 10-15% overlap
- Use: target_w = int(HEX_SIZE * 2.0 * zoom * 1.15)
- target_h = int(HEX_SIZE * 1.732 * zoom * 1.15)
- Scale tile to (target_w, target_h) instead of square (target_size, target_size)
- This makes tiles slightly rectangular matching hex proportions

Test: zoom in and out 10 levels, verify no black gaps at any level.

---

## Task 9: Side panel content — city and unit details visible

City panel and unit panel show buttons but the text is barely readable.

Fix: 
- City panel buttons should show: "CityName (Pop X) [Building: Item]" or "[IDLE]"
- Unit panel buttons should show: "UnitType HP:X/Y Mv:N"
- Make buttons tall enough (35-40px) for text to be readable
- Update text every turn via refresh()

Test: verify panel buttons show readable text after 5 turns.

---

## Task 10: Turn summary popup at start of each turn

After clicking Next Turn, show a popup listing what happened:
- "Roma completed Granary"
- "Research complete: Pottery"
- "Egypt declared war!"
- etc.

Fix: game_screen.py after process_turn(), if events exist, call 
self._turn_summary.show(self.ui_manager, events, game.state.turn).
Verify turn_summary.py show() creates a UIWindow with event list.

Test: play 3 turns, verify popup appears with events after each turn.
