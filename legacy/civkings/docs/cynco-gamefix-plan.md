# CivKings Visual & Gameplay Fix Plan — For CynCo

> **For agentic workers:** Each task is one CynCo session. Restart the engine between tasks. Each task is self-contained: read, edit, test, commit. Use ReplaceFunction for large function rewrites, Edit for small fixes.

**Goal:** Make CivKings visually complete and playable for 100+ turns through the pygame GUI with cities visible, units moving, resources updating, and no crashes.

**Architecture:** Fix wiring bugs between the game engine (game.py, game_manager.py) and the pygame GUI (pygame_app/). The game simulation works (500 turns stable). The GUI renders hexes. The gap is data flow: the GUI doesn't read game state correctly, and cities/units don't render on the map.

**Tech Stack:** Python 3.14, pygame-ce, pygame_gui

**Current state:** 20 tests passing, 50+ turns stable, hex map renders, turn counter works, AI plays. 15 CynCo commits.

---

### Task 1: Fix resource bar to show real science, culture, faith values

**Files:**
- Modify: `pygame_app/panels/resource_bar.py`

The resource bar shows Sci: 0.0, Culture: 0.0, Faith: 0.0 because it reads from `game.city_manager.get_total_yields()` which may return empty or crash. The game tracks these via `game.tech_manager`, `game.religion_manager`, etc.

**CynCo task:**
```
Read pygame_app/panels/resource_bar.py refresh() method. The science value should come from game.tech_manager — read tech.py to find the right attribute. Culture should come from cities or era_system. Faith from game.religion_manager or game.faith_points dict.

Replace the yield-based resource reading with direct attribute access using getattr with defaults:
- Science: sum of city science yields or tech_manager progress
- Culture: sum of city culture yields  
- Faith: game.faith_points.get(civ_name, 0)

Use Edit. Run the game for 5 turns to verify values change. Commit.
```

**Verify:** Run game, press RETURN 10 times, check that Sci/Culture/Faith change from 0.0.

---

### Task 2: Make cities visible on the hex map

**Files:**
- Modify: `pygame_app/map/hex_renderer.py` (city rendering section, ~lines 486-530)
- Read: `city.py` (City class attributes)

Cities should show as labeled markers on the hex grid. The hex_renderer already has city rendering code but cities may not be in `game.cities` dict or the rendering is culled by camera.

**CynCo task:**
```
Read pygame_app/map/hex_renderer.py lines 486-530 (city rendering). Read game.py to see how game.cities is populated. The cities dict may be empty because GameManager._initialize_cities creates City objects but may not add them to game.cities.

Check: does game.cities get populated? Add a debug print in hex_renderer render() showing len(game.cities). If cities dict is empty, trace back to game.py initialization to find where cities should be added.

Fix the wiring so cities appear on the map. Each city should show as a colored rectangle with its name. Commit.
```

**Verify:** Start game, see a colored rectangle with "Byzantium City" text on a hex tile.

---

### Task 3: Make units visible on the hex map

**Files:**
- Modify: `pygame_app/map/hex_renderer.py` (unit rendering section, ~lines 531-612)
- Read: `military.py` (Unit class), `game.py` (game.units dict)

Units should show as sprites or colored shapes on hex tiles. The renderer has unit drawing code but game.units may be empty.

**CynCo task:**
```
Read pygame_app/map/hex_renderer.py lines 531-612 (unit rendering). Read game.py to see how game.units is populated — specifically MilitaryManager and how units are created.

Add debug: print(f"Units to render: {len(getattr(game, 'units', {}))}") in the render method.

If game.units is empty, check if the initial Settler unit from GameManager._initialize_cities is added to game.units. Fix the wiring. Commit.
```

**Verify:** Start game, see a unit icon on the starting city hex.

---

### Task 4: Dismiss turn summary popup on click/key

**Files:**
- Modify: `pygame_app/screens/game_screen.py`

The turn summary popup covers the entire map area and doesn't auto-dismiss. Player can't see the map after advancing turns.

**CynCo task:**
```
Read pygame_app/screens/game_screen.py handle_event method. Find where _turn_summary is checked. The popup should dismiss when the player clicks anywhere or presses any key.

Add: if self._turn_summary is visible and user clicks or presses a key, set self._turn_summary.visible = False or call dismiss(). Commit.
```

**Verify:** Advance a turn, see summary, click anywhere, summary disappears and map is visible.

---

### Task 5: Add city production assignment on city click

**Files:**
- Modify: `pygame_app/screens/game_screen.py` (click handler)
- Read: `pygame_app/popups/production.py`

Cities show "[IDLE]" in the panel. Clicking a city should open the production popup to assign what to build.

**CynCo task:**
```
Read game_screen.py handle_event for MOUSEBUTTONDOWN. When a city hex is clicked, it should select the city and show the production popup. Check if _open_production_popup_for exists and if it's wired to city clicks.

If clicking a city hex doesn't open production, add the wiring: detect city click → set selected_city → open production popup. Commit.
```

**Verify:** Click on city hex, see production popup with build options (Settler, Warrior, etc).

---

### Task 6: Wire unit movement to hex clicks

**Files:**
- Modify: `pygame_app/screens/game_screen.py`
- Read: `pygame_app/map/hex_renderer.py` (move range rendering)

Selecting a unit and clicking a destination hex should move the unit. The renderer already draws move range (blue hexes) and attack range (red hexes).

**CynCo task:**
```
Read game_screen.py handle_event for unit selection and movement. When a unit is selected and player clicks a valid hex, it should call game.move_unit() or similar. Check what movement API exists in game.py or military.py.

Wire: click unit → show move range → click destination → move unit. Commit.
```

**Verify:** Select a unit, see blue hex highlights, click a blue hex, unit moves there.

---

### Task 7: Connect fog of war to GUI

**Files:**
- Modify: `pygame_app/map/hex_renderer.py` (fog rendering, ~lines 615-625)
- Read: `game.py` (self._fog / ExponentialFogOfWar)

The fog of war system exists but may not darken unexplored hexes in the GUI.

**CynCo task:**
```
Read hex_renderer.py lines 615-625 (fog rendering). It reads game.fog to determine which hexes are visible. Check if game.fog.visible_hexes is populated after calling _update_fog in game_screen.py.

If fog isn't rendering, add debug to check fog state. Fix wiring. The unexplored map should be darker. Commit.
```

**Verify:** Start game, see dark/hidden hexes around the map edges, visible area around your city.

---

### Task 8: Add 100-turn stability test

**Files:**
- Create or modify: `test_civkings.py`

**CynCo task:**
```
Add a test to test_civkings.py that creates a game via create_sample_game and runs 100 turns, checking for no exceptions. Also verify that after 100 turns: turn count is 101, at least one city exists, and game is not over.

Run python -m pytest test_civkings.py -v to verify all tests pass. Commit.
```

**Verify:** `python -m pytest test_civkings.py::test_100_turn_stability -v` passes.

---

### Task 9: Full GUI play-test screenshot evaluation

This is not a CynCo task — it's a manual verification step.

Launch the game, play 30 turns via keyboard, take screenshots at turns 1, 10, 20, 30. Evaluate:
- [ ] Hex map visible with terrain variety
- [ ] Turn counter updates each turn
- [ ] At least one resource value changes over time
- [ ] City visible on map as labeled marker
- [ ] Unit visible on map
- [ ] Turn summary popup dismisses on click
- [ ] No crashes for 30 turns
- [ ] Fog of war visible (dark unexplored areas)

---

## Execution Notes for CynCo Supervisor

1. **One task per engine session.** Restart between tasks.
2. **65K context.** Set LOCALCODE_CONTEXT_LENGTH=65536.
3. **Use ReplaceFunction** for any function > 10 lines.
4. **Use Edit** for one-line or few-line fixes.
5. **CRLF handling is fixed** — Edit tool normalizes line endings.
6. **Semantic merge is disabled** — failed Edits fail cleanly, no file corruption.
7. **Check uncommitted changes** after each task — CynCo often edits but forgets to commit.
8. **Send commit command separately** if CynCo didn't commit.
9. **Play-test with `python C:/tmp/civkings-play3.py`** to screenshot the GUI after each visual fix.
