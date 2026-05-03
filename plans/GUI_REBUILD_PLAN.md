# GUI Rebuild Plan: From CLI to Desktop Game

## Current Problems

1. **Crash on start**: `ui.py:320` accesses `self.game.fog` but `Game` has no `fog` attribute. `fog` lives on `self.map.fog`.
2. **Menu logic bug**: `main.py` prints the main menu (Start/Load/Quit) every loop iteration, including during gameplay.
3. **Wrong interface**: The mockup (`.localcode-mockup.html`) shows a **desktop GUI** with:
   - Left panel: Dynasty/character cards with stats and traits
   - Center: Interactive hex map with panning/zooming, city markers, fog of war
   - Right panel: City management, production queues, resource stats
   - Top bar: Gold, Science, Prestige, Turn number, End Turn button
   - Event modal popups with choice buttons
4. **Current code is pure CLI**: All output via `print()`, all input via `input()`. No GUI at all.

## Decision Points

### Option A: Fix the CLI and keep it text-based
- Fix the `fog` crash
- Fix menu logic
- Add interactive map navigation (arrow keys, zoom)
- Keep the terminal interface
- **Pros**: Fast to implement, no new dependencies
- **Cons**: Not what the mockup shows

### Option B: Build the GUI desktop game (Tkinter)
- Use Tkinter (built-in Python, no pip install needed)
- Recreate the mockup design: left panel, hex map, right panel, top bar
- Interactive map with pan/zoom
- Character cards, city management UI
- Event modal popups
- **Pros**: Matches your vision/mockup
- **Cons**: More work, but still doable

## Recommended Approach: Option B

The mockup clearly shows a GUI game. Let's build it with Tkinter.

## Implementation Plan

### Phase 1: Fix immediate crashes (30 min)
- [ ] B1.1: Add `fog` property to `Game` class (delegate to `self.map.fog`)
- [ ] B1.2: Fix `main.py` menu logic (separate main menu from in-game menu)
- [ ] B1.3: Test the game starts and map displays without crash

### Phase 2: Tkinter GUI skeleton (1-2 hours)
- [ ] B2.1: Create `gui_main.py` with main window class
- [ ] B2.2: Implement top bar (gold, science, prestige, turn, end turn button)
- [ ] B2.3: Implement left panel (character cards, dynasty info)
- [ ] B2.4: Implement right panel (city stats, production queue)
- [ ] B2.5: Wire up data binding (game state -> UI updates)

### Phase 3: Interactive hex map (2-3 hours)
- [ ] B3.1: Create hex grid rendering on Tkinter Canvas
- [ ] B3.2: Terrain coloring (plains, forest, mountain, water)
- [ ] B3.3: City markers on map
- [ ] B3.4: Unit markers on map
- [ ] B3.5: Pan (drag) and zoom (scroll wheel)
- [ ] B3.6: Fog of war overlay
- [ ] B3.7: Click to select units/cities

### Phase 4: UI interactions (2-3 hours)
- [ ] B4.1: Character card selection and detail view
- [ ] B4.2: City management (view details, choose production)
- [ ] B4.3: Production queue UI with drag/drop or list
- [ ] B4.4: Tech tree popup
- [ ] B4.5: Diplomacy panel
- [ ] B4.6: Event modal popups with choice buttons
- [ ] B4.7: Map tooltip on hover

### Phase 5: Polish and cleanup (1-2 hours)
- [ ] B5.1: Fix all remaining CLI references
- [ ] B5.2: Update `main.py` entry point to launch GUI
- [ ] B5.3: Add save/load through GUI
- [ ] B5.4: Test full game loop in GUI

## Files to Create
- `gui_main.py` — Main Tkinter window, layout, top bar
- `gui_map.py` — Hex map rendering, pan/zoom, click handling
- `gui_panels.py` — Left dynasty panel, right city panel
- `gui_popups.py` — Event modals, tech tree, diplomacy

## Files to Modify
- `game.py` — Add `fog` property, ensure clean data access
- `ui.py` — Deprecate or keep as CLI fallback
- `main.py` — Launch GUI instead of CLI
- `hex_map.py` — Ensure map data is accessible to GUI

## Estimated Total: 6-10 hours of work
