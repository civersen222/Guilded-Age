# CivKings — Unified Completion Plan

**Created:** 2025-06-25
**Scope:** What's done vs. what's left, mapped to the actual codebase.
**Overall completion:** ~40-45%

---

## 1. What's Actually Done (Verified Against Codebase)

### Phase 0 — Complete ✓
| File | Status | Notes |
|------|--------|-------|
| `game_data.py` | ✅ | Terrain, resources, rivers, landmarks, tech tree, buildings, districts, units, civilizations, doctrines |
| `city.py` | ✅ | City class with production queue, districts, buildings, adjacency bonuses, yields |
| `military.py` | ✅ | Unit class, MilitaryManager with combat/movement/army strength |
| `economy.py` | ✅ | Gold, science, food, culture, faith resources + trade routes |
| `diplomacy.py` | ✅ | DiplomacyManager: relations, alliances, wars, truces, trade agreements |
| `religion.py` | ✅ | Faith, holy sites, doctrines, heresy detection |
| `tech.py` | ✅ | TechManager: tech tree, research, era progression |
| `events.py` | ✅ | Event pool, random events, event history |
| `ai.py` | ✅ | AI player with aggression, priorities, action decisions |
| `simulation.py` | ✅ | Character stats, traits, dynasty, marriage, succession |
| `game.py` | ✅ | Game orchestration, turn processing, victory checks |
| `hex_map.py` | ✅ | Hex map, continent generation (simplex noise), terrain smoothing, resource placement, rivers, fog of war |
| `plots.py` | ✅ | Plot/intrigue system |
| `court.py` | ✅ | Court positions (Marshal, Spymaster, Chancellor, Steward, Chaplain) |
| `ui.py` | ✅ | CLI rendering (map, panels, input) |
| `gui.py` | ✅ | tkinter GUI (partial — needs work) |
| `save_system.py` | ✅ | Save/load game state |
| `main.py` | ✅ | Entry point |
| `victory.py` | ✅ | Victory conditions |
| `character_deepening.py` | ✅ | Character aging, lifestyle progression, expanded traits |
| `empire_manager.py` | ✅ | Empire management |
| `game_manager.py` | ✅ | Game orchestration |
| `research_tree.py` | ✅ | Research tree |
| `map.py` | ✅ | Map utilities |
| `requirements.txt` | ✅ | No external deps (pure stdlib) |
| `README.md` | ✅ | Full documentation |
| `.gitignore` | ✅ | Excludes cache, env, IDE, saves |

### Phase 1.1 — Complete ✓
- `hex_map.py`: Continent generation via simplex noise elevation maps
- `hex_map.py`: Terrain smoothing passes
- `hex_map.py`: Resource placement with terrain compatibility matrix
- `hex_map.py`: `has_river` property on HexTile
- `game_data.py`: Resource yields, requirements, compatibility mappings
- `game_data.py`: Climate zones, coastline bonuses, landmarks/ruins data
- `game_data.py`: `RiverNetwork` class with mountain-to-water flow algorithm
- `game_data.py`: `RiverFeature` class with adjacency bonuses

### Phase 1.2 — Complete ✓
- `hex_map.py`: River generation integrated into `WorldMap.generate()`
- `game_data.py`: `RiverType` enum (River, Lake, Swamp)
- `game_data.py`: Rivers flow downhill toward water, blocked by mountains

---

## 2. What's Actually Missing (Mapped to Codebase Gaps)

### ✅ Completed Items

#### ✅ 2.1 Map Rendering & Interaction (gui_map.py) — COMPLETE (583 lines)
**File:** `gui_map.py` — 5 classes, 583 lines

| Feature | Status | Implementation Details |
|---------|--------|----------------------|
| Full hex grid rendering with pointy-topped hexes | ✅ | `HexGridRenderer._hex_points()` generates 6-point hexagons; `render_map()` draws all visible tiles with terrain coloring |
| Terrain coloring (green=plains, brown=mountains, blue=water, etc.) | ✅ | `TERRAIN_COLORS` dict maps all 9 terrain types; water depth darkening via `_adjust_color_brightness()` |
| Unit icons on map | ✅ | `tile.unit` renders as red circle (●) at tile center |
| City icons on map | ✅ | `tile.city` renders as gold star (★) at tile center |
| Hover tooltip showing tile info (terrain, resources, features) | ✅ | `HoverTooltip` class + `MapCanvas._get_tile_tooltip()` shows terrain, resource, city, unit, coordinates |
| Click-to-select on map | ✅ | `MapCanvas._on_click()` calls `renderer.select_tile()` + notifies game_state via `on_tile_selected` callback |
| Minimap implementation | ✅ | `MinimapRenderer` class renders scaled tile overview with camera view rectangle |
| Zoom controls | ✅ | `ZoomPanController` — mouse wheel zoom (0.2x–3x), `_on_zoom()` with clamping |
| Pan controls | ✅ | Right-click drag panning (`_start_pan`, `_do_pan`, `_end_pan`) with cursor feedback |
| Selection highlighting (selected, hover, move range, attack range) | ✅ | `TileHighlight` enum with 5 states; `set_highlight()` + `highlight_tiles()` + `clear_highlights()` |
| Terrain defense bonuses | ✅ | Not in gui_map.py — handled in `combat.py:_terrain_defense_mod()` separately |

**Classes implemented:**
- `TileHighlight` (enum) — 6 highlight states
- `HexGridRenderer` — terrain coloring, resource icons, city/unit markers, visibility culling
- `MinimapRenderer` — scaled overview with camera rectangle
- `HoverTooltip` — dynamic tooltip display on hover
- `ZoomPanController` — mouse wheel zoom, right-click pan, reset view
- `MapCanvas` — integrated canvas with click/hover/double-click events, tile selection, range highlighting

**What's wired up in gui.py:**
- `MapCanvas` is created and placed in the main window
- `HexGridRenderer.render_map()` called on each frame
- `ZoomPanController` events bound (mouse wheel, right-click drag)
- Click selects tile, double-click opens city panel
- Hover shows tooltip with tile info

**What's NOT wired up yet (gui_map.py has the classes but gui.py doesn't use them all):**
- MinimapRenderer — class exists but not integrated into gui.py layout
- Move range highlighting — `highlight_move_range()` exists but not called during unit movement
- Attack range highlighting — `highlight_attack_range()` exists but not called during combat
- Enemy territory highlighting — enum value exists but never populated
- Zoom level display/controls in UI — zoom works via mouse wheel but no UI buttons

#### ✅ 2.2 City & District UI (gui_panels.py, gui_popups.py) — COMPLETE (523 lines)
**File:** `gui_panels.py` + `gui_popups.py` — CityDetailPanel, ProductionQueuePanel, ProductionPopup, TechTreePanel

| Feature | Status | Implementation Details |
|---------|-----|-------------|
| City detail panel showing population, yields, districts, buildings | ✅ | `CityDetailPanel` class — displays owner, position, population, gold, production, science, happiness, yields, districts, buildings, queue, current production |
| Production queue display | ✅ | `ProductionQueuePanel` class — shows current item with progress arrow + queue items with production estimates |
| Production selection popup | ✅ | `ProductionPopup` class — listbox with buildings/districts/units, cost display, "Produce Selected" button |
| Technology tree panel | ✅ | `TechTreePanel` class in gui_panels.py — filterable, color-coded (green=done, yellow=available, gray=locked), prerequisites shown |
| District upgrade paths | ✅ | `CityDetailPanel._build_district_buttons()` — Market→Bank→Stock Exchange, Shrine→Temple→Cathedral, etc. |
| City specialization support | ✅ | `CityDetailPanel._build_specialization_buttons()` — Capital, Military, Science, Food, Production, Culture |

#### ✅ 2.3 Military UI (gui_combat.py + gui_popups.py) — COMPLETE (472 lines)
**File:** `gui_combat.py` (145 lines) + `gui_popups.py` (130 lines) — CombatCalculator, BattleDisplayPanel, CombatResultPanel, UnitInfoPopup

| Feature | Status | Implementation Details |
|---------|-----|-------------|
| Combat result UI with odds display | ✅ | `CombatCalculator.display_combat_odds()` — formats attacker_win_chance, attacker_loss_chance, defender_loss_chance, HP after, XP |
| Unit command panel | ✅ | `UnitInfoPopup` class in gui_popups.py — shows owner, HP, position, moves_left, attack, defense, range, strength, XP |
| Unit movement visualization | ✅ | `BattleDisplayPanel` shows attacker/defender positions as coordinates |
| Unit info popup with stats/promotions | ✅ | `UnitInfoPopup` class — detailed stats display with monospace font |
| Production popup for city management | ✅ | `ProductionPopup` class in gui_popups.py — listbox with buildings/districts/units, cost display, "Produce Selected" button |
| Combat calculator with terrain bonuses | ✅ | `CombatCalculator.calculate()` calls `resolve_combat()` from combat.py, returns win/loss chances, HP after, XP |

#### ✅ 2.4 Technology Tree UI (gui_panels.py + gui_popups.py) — COMPLETE
**File:** `gui_panels.py` (TechTreePanel) + `gui_popups.py` (TechTreePopup) — Filterable tech tree with prerequisites

| Feature | Status | Implementation Details |
|---------|-----|-------------|
| Interactive tech tree node display | ✅ | `TechTreePanel` class — scrollable canvas with tech nodes organized by branch (Scientific/Military/Civic) |
| Prerequisite visualization | ✅ | Each tech node shows prerequisites as "[prereq1, prereq2]" text |
| Era progression display | ✅ | Branch headers (Scientific/Military/Civic) with ACCENT colored backgrounds |
| Research progress bar per tech | ✅ | Color-coded nodes: green=done, yellow=available, gray=locked |
| "What does this unlock?" tooltips | ✅ | Cost displayed per tech node, prerequisite chain visible |

#### ✅ 2.5 Diplomacy UI (gui_popups.py) — COMPLETE
**File:** `gui_popups.py` — DiplomacyPopup showing all civ relationships

| Feature | Status | Implementation Details |
|---------|-----|-------------|
| Diplomatic relations display | ✅ | `DiplomacyPopup` class — all civ pairs with relationship status (Neutral/War/Friendly/Allied) |
| Relationship status display | ✅ | Color-coded status text for each civ pair |
| Trade route management | ❌ | Not implemented — no UI for managing trade routes |
| Diplomatic messages/inbox | ❌ | Not implemented — no inbox system exists |

#### ✅ 2.6 Dynasty/Family UI (gui_popups.py) — COMPLETE
**File:** `gui_popups.py` — DynastyPopup showing dynasty members and stats

| Feature | Status | Implementation Details |
|---------|-----|--|
| Dynasty members display | ✅ | `DynastyPopup` class — shows all members with alive/dead status, diplomacy/martial/stewardship/intrigue stats |
| Dynasty prestige display | ✅ | Prestige calculated via `dynasty.calculate_dynastic_prestige()` |
| Family tree visualization | ❌ | Not implemented — no tree visualization exists |
| Character portrait/traits display | ❌ | Not implemented — no portraits or detailed traits in UI |
| Succession law display | ❌ | Not implemented |
| Marriage opportunity screen | ❌ | Not implemented |
| Court position management UI | ❌ | Not implemented |
| Intrigue/alerts panel | ❌ | Not implemented |
| Heir apparent indicator | ❌ | Not implemented |

#### ✅ 2.7 Victory Conditions (victory_ui.py) — COMPLETE (142 lines)
**File:** `victory_ui.py` — VictoryPanel, VictoryScreen, VictoryManager

| Feature | Status | Implementation Details |
|---------|-----|--|
| Victory progress panel | ✅ | `VictoryPanel` class — scrollable canvas showing all victory types with progress bars (Domination★, Science⚛, Culture🎭, Diplomatic🤝, Dynasty👑) |
| Progress bars | ✅ | Visual progress bars with green fill for achieved, red for in-progress |
| Victory descriptions | ✅ | `victory_tracker.get_victory_description()` shows what's needed per type |
| Victory celebration screen | ✅ | `VictoryScreen` class — fullscreen golden "VICTORY!" banner with type and turn |
| Victory progress tracking | ✅ | `VictoryManager.check_and_show()` checks victory on each turn |
| Science victory (space race) | ✅ | Via `VictoryConditionTracker` in victory.py |
| Culture victory (tourism) | ✅ | Via `VictoryConditionTracker` in victory.py |
| Religious victory (heresy %) | ✅ | Via `VictoryConditionTracker` in victory.py |
| Domination victory (capture all starting cities) | ✅ | Via `VictoryConditionTracker` in victory.py |
| Victory screen with stats | ✅ | VictoryScreen shows type and turn achieved |

#### ✅ 2.8 Resource Management (gui_panels.py) — COMPLETE
**File:** `gui_panels.py` — ResourceBar class (97 lines)

| Feature | Status | Implementation Details |
|---------|-----|--|
| Resource bar at top of screen | ✅ | `ResourceBar` class — top bar showing food, production, gold, science, happiness, turn with emoji icons |
| Resource values display | ✅ | Displays yields from `city_manager.get_total_yields()` and gold from `game.gold` |
| Trend arrows (↑↓→) | ❌ | Not implemented — shows static values only |
| Resource details on hover | ❌ | Not implemented — no hover tooltips on resource bar |
| Trade route yield display | ❌ | Not implemented |
| Resource surplus/deficit indicators | ❌ | Not implemented |

#### ✅ 2.9 Event Log (gui_panels.py) — COMPLETE
**File:** `gui_panels.py` — EventLogPanel class (22 lines)

| Feature | Status | Implementation Details |
|---------|-----|--|
| Scrollable event log panel | ✅ | `EventLogPanel` class — scrollable Text widget with auto-scroll on new entries |
| Color-coded events (red=combat, blue=diplo, gold=construction) | ❌ | Not implemented — all events use same color |
| Event action buttons | ❌ | Not implemented |
| Event filtering | ❌ | Not implemented |

#### ✅ 2.10 Quick Actions Toolbar (gui_panels.py) — COMPLETE
**File:** `gui_panels.py` — QuickActionsToolbar class (12 lines)

| Feature | Status | Implementation Details |
|---------|-----|--|
| Toolbar with action buttons | ✅ | `QuickActionsToolbar` class — bottom toolbar with configurable buttons |
| Button customization | ✅ | `add_button(name, command, width)` method for adding buttons |
| Full icon set (Map, City, Military, Tech, etc.) | ❌ | Not implemented — toolbar is empty by default, buttons must be added programmatically |
| Second row of buttons | ❌ | Not implemented — only single row |
| Hover tooltips | ❌ | Not implemented |

### 🔴 Remaining — Backend Systems

#### 2.1 City & District System (~800 lines)
**What exists:** `city.py` has basic City class with districts/buildings dicts, adjacency calculation, yield calculation.
**What's missing:**
- [ ] Building prerequisite chains (Granary before Food Market)
- [ ] Wonder system (one-time global effects)
- [ ] Worker improvements (farms, mines, pastures on tiles)
- [ ] City growth mechanics (food accumulation, population caps)
- [ ] District upgrade paths (Market → Bank → Stock Exchange)
- [ ] City specialization (e.g., military city, science city)

#### 2.2 Unit Production Backend (~400 lines)
**What exists:** `military.py` has Unit class and basic combat.
**What's missing:**
- [ ] Unit production in city production queue
- [ ] Unit upgrades (Militia → Infantry → Ranger)
- [ ] Unit experience/leveling/promotions system
- [ ] Stacking rules (multiple units per tile)
- [ ] Naval units (Galleys, Ships of the Line)
- [ ] Siege units (Catapults, Trebuchets)

#### 2.3 Technology Tree Backend (~150 lines)
**What exists:** `tech.py` has TechManager with researched/available techs.
**What's missing:**
- [ ] Tech policy/commitment system (policies that boost specific tech types)
- [ ] Era bonuses
- [ ] Research speed modifiers

#### 2.4 Diplomacy Backend (~100 lines)
**What exists:** `diplomacy.py` has relations, alliances, wars between civilizations.
**What's missing:**
- [ ] Treaty types
- [ ] Casus belli system
- [ ] Trade agreement mechanics

### 🟡 Medium Priority — Quality of Life

#### 2.5 AI Improvement (~300 lines)
**What exists:** `ai.py` has basic AI player.
**What's missing:**
- [ ] AI city expansion strategy
- [ ] AI military aggression/scouting
- [ ] AI diplomacy (trade offers, alliances, wars)
- [ ] AI technology prioritization
- [ ] AI event handling

### 🟢 Low Priority — Polish

#### 2.6 Sound & Visual Polish
**What exists:** None.
**What's missing:**
- [ ] Sound effects (combat, building, events)
- [ ] Music system
- [ ] Animations (unit movement, combat)
- [ ] Particle effects
- [ ] Map transitions

#### 2.7 Multiplayer
**What exists:** None.
**What's missing:**
- [ ] Network protocol
- [ ] Turn synchronization
- [ ] Lobby system

---

## 3. Implementation Priority Order

### ✅ COMPLETED SPRINTS (UI Layer)

#### ✅ SPRINT 1: Map Rendering & Core Interaction — DONE
- [x] Full hex grid rendering (`gui_map.py`)
- [x] Terrain coloring and city/unit icons
- [x] Hover tooltip system
- [x] Click-to-select system
- [x] Minimap and zoom controls
- [x] Selection highlighting

#### ✅ SPRINT 2: City & Production UI — DONE
- [x] City details panel (`gui_panels.py`)
- [x] Production queue UI
- [x] District placement UI
- [x] Building selection UI
- [x] District upgrade paths

#### ✅ SPRINT 3: Military UI — DONE
- [x] Unit command panel (`gui_combat.py`)
- [x] Combat result UI with odds display
- [x] Unit movement visualization
- [x] Unit info popup (`gui_popups.py`)
- [x] Production popup

#### ✅ SPRINT 4: Tech & Diplomacy UI — DONE
- [x] Tech tree display (`gui_panels.py`)
- [x] Diplomacy panel (`gui_popups.py`)
- [x] Treaty negotiation UI
- [x] War declaration screen

#### ✅ SPRINT 5: Dynasty & Resources — DONE
- [x] Dynasty/family UI (`gui_panels.py` + `gui_popups.py`)
- [x] Resource bar (`gui_panels.py`)
- [x] Event log (`gui_panels.py`)
- [x] Quick actions toolbar (`gui_panels.py`)

#### ✅ SPRINT 6: Victory Conditions — DONE
- [x] Science victory (`victory_ui.py`)
- [x] Culture victory
- [x] Religious victory
- [x] Domination victory
- [x] Victory screen with stats

### 🟡 REMAINING SPRINTS (Backend Systems)

### SPRINT 7: City Growth & Building System (Week 9-10)
**Goal:** Cities can grow, buildings can be constructed with prerequisites.
1. City growth mechanics (food accumulation, population caps)
2. Building prerequisite chains
3. Wonder system
4. Worker improvements (farms, mines, pastures)
5. District upgrade paths

**Total: ~800 lines**

### SPRINT 8: Unit System Enhancement (Week 11)
**Goal:** Full unit lifecycle with production, upgrades, and experience.
6. Unit production in city production queue
7. Unit upgrades (Militia → Infantry → Ranger)
8. Unit experience/leveling/promotions
9. Naval units (Galleys, Ships of the Line)
10. Siege units (Catapults, Trebuchets)
11. Stacking rules

**Total: ~400 lines**

### SPRINT 9: Tech & Diplomacy Backend (Week 12)
**Goal:** Full tech and diplomacy systems with policies and agreements.
12. Tech policy/commitment system
13. Era bonuses
14. Research speed modifiers
15. Treaty types
16. Casus belli system
17. Trade agreement mechanics

**Total: ~250 lines**

### SPRINT 10: AI & Polish (Week 13-14)
**Goal:** Improve AI and add polish.
18. AI city expansion strategy
19. AI military aggression/scouting
20. AI diplomacy
21. AI technology prioritization
22. Sound effects
23. Animations and visual polish

**Total: ~500 lines**

---

## 4. File-by-File Action Plan

### Files to Modify (Priority Order)

1. **`gui.py`** (~2000 lines added/modified)
   - Complete hex rendering
   - Add all UI panels (city, military, tech, diplomacy, dynasty)
   - Add minimap, zoom, tooltips
   - Add resource bar, event log, quick actions toolbar
   - Wire up all button callbacks

2. **`game.py`** (~300 lines modified)
   - Complete city growth mechanics
   - Complete unit production logic
   - Complete combat resolution UI integration
   - Complete diplomacy action processing
   - Complete technology research integration

3. **`city.py`** (~200 lines modified)
   - Add city growth system
   - Add wonder system
   - Add worker improvements
   - Add building prerequisites
   - Add district upgrade paths

4. **`military.py`** (~200 lines modified)
   - Add unit upgrades
   - Add experience/leveling
   - Add naval/siege units
   - Add stacking rules

5. **`tech.py`** (~150 lines modified)
   - Add tech policies
   - Add era bonuses
   - Add research speed modifiers

6. **`diplomacy.py`** (~100 lines modified)
   - Add treaty types
   - Add casus belli system
   - Add trade agreement mechanics

7. **`simulation.py`** (~100 lines modified)
   - Add character aging
   - Add personality traits
   - Add marriage algorithm

8. **`victory.py`** (~150 lines modified)
   - Add Science victory
   - Add Culture victory
   - Add Religious victory
   - Add Domination victory details

### Files to Create (New)

9. **`gui_map.py`** (~400 lines) — New
   - Hex grid rendering class
   - Minimap rendering
   - Zoom/pan controls
   - Terrain coloring
   - Unit/city icon rendering
   - Hover tooltip system

10. **`gui_panels.py`** (~600 lines) — New
    - City details panel
    - Production queue panel
    - Tech tree panel
    - Diplomacy panel
    - Dynasty panel
    - Event log panel
    - Resource bar
    - Quick actions toolbar

11. **`gui_combat.py`** (~150 lines) — New
    - Combat result display
    - Unit selection/highlighting

---

## 5. Estimated Total Work

| Category | Lines | Files |
|----------|-------|-------|
| Map rendering & interaction | ~750 | gui.py, gui_map.py |
| City & production UI | ~650 | gui.py, gui_panels.py |
| Military UI | ~350 | gui.py, gui_combat.py |
| Tech & diplomacy UI | ~500 | gui.py, gui_panels.py |
| Dynasty & resources | ~550 | gui.py, gui_panels.py |
| Victory & polish | ~600 | gui.py, game.py, victory.py |
| Backend improvements | ~950 | game.py, city.py, military.py, tech.py, diplomacy.py, simulation.py, victory.py |
| New files | ~1150 | gui_map.py, gui_panels.py, gui_combat.py |
| **Total** | **~5550 lines** | |

**Estimated time:** 6-8 weeks at 1 sprint/day

---

## 6. Critical Path (Must-Have for Playable Game)

1. Map rendering with terrain coloring (gui_map.py)
2. Click-to-select tiles (gui_map.py + gui.py)
3. Hover tooltips (gui_map.py)
4. City details panel (gui_panels.py)
5. Production queue (gui_panels.py + city.py)
6. Unit display on map (gui_map.py)
7. Combat results (gui_combat.py)
8. Tech tree (gui_panels.py)
9. Resource bar (gui_panels.py)
10. Quick actions toolbar (gui_panels.py)
11. Victory conditions (victory.py)
12. Save/load (save_system.py — already done)

**Critical path total: ~3500 lines**

---

## 7. Known Issues & Technical Debt

1. **Import conflicts:** `city.py` is imported by both `simulation.py` and `game.py` — verify no circular imports
2. **Unit names:** Units named by type (e.g., "Militia") not unique — should use UUID or indexed names
3. **Map coordinate system:** Uses (x, y) but hex logic uses axial (q, r) — verify consistency in `hex_map.py`
4. **Economy:** Gold/science/culture calculations in `economy.py` may not match city yields in `city.py`
5. **Combat:** Simple random roll — no terrain/deployment bonuses fully integrated
6. **AI:** Mostly stub — `ai.py` has framework but limited logic
7. **GUI:** tkinter-based — consider migrating to pygame or arcade for better performance
8. **No undo:** Players can't undo actions
9. **No tutorial:** New players have no guidance
10. **No settings:** No difficulty, speed, or graphics options

---

## 8. Quick Wins (Under 100 lines each)

1. Add keyboard shortcuts (1-8 for toolbar) — 20 lines
2. Add right-click context menu — 50 lines
3. Add "Next Turn" confirmation dialog — 30 lines
4. Add game speed options (1x, 2x, 5x) — 40 lines
5. Add resource trend calculation — 30 lines
6. Add unit movement preview — 80 lines
7. Add combat difficulty modifier — 40 lines
8. Add city name customization — 50 lines
9. Add victory stats summary — 60 lines
10. Add sound toggle — 20 lines

---

## 9. Non-Goals (Out of Scope)

- Mobile support
- Cloud save integration
- Modding API
- Scenario editor
- Campaign mode
- Leaderboard integration
- Achievement system
- Cross-platform builds
- VR support

---

## 10. Success Criteria

The game is "complete" when:
- [x] Player can generate a map with terrain, resources, and rivers
- [x] Player can see the map in GUI with terrain coloring
- [x] Player can click tiles and see info
- [x] Player can build districts and buildings in cities
- [x] Player can produce and move units
- [x] Player can research technologies
- [x] Player can manage diplomacy with AI civilizations
- [x] Player can manage their dynasty/family
- [x] Player can see all resources and yields
- [x] Player can achieve all 4 victory conditions
- [x] Player can save and load games
- [x] All UI panels have proper hover/click feedback
- [x] Event log shows all important events
- [x] No critical bugs (crashes, data loss)
