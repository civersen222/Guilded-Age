# CivKings - Completion Plan

## What's Done (Phase 0)

### Bug Fixes
- **`game_data.py`**: Fixed `ResourceType` enum crash — changed `self.name = name` to `self.display_name = display_name` to avoid conflict with Python's built-in enum `name` property

### New Files Created
- **`requirements.txt`** — declares no external dependencies (pure Python stdlib)
- **`README.md`** — full project documentation (features, installation, controls, file structure)
- **`.gitignore`** — excludes `__pycache__/`, environments, IDE config, game saves

### Existing Systems (Working)
| File | Purpose |
|------|---------|
| `game.py` | Core game engine — state management, turn processing, victory conditions |
| `ui.py` | CLI interface — menu, map rendering, command parser |
| `city.py` | City management — population, production queue, districts, buildings |
| `military.py` | Unit types, combat engine, promotions |
| `diplomacy.py` | Relations, alliances, trade routes |
| `tech.py` | Technology research system |
| `events.py` | Random world events |
| `ai.py` | AI opponent logic |
| `map.py` | Improved hex map with resources, rivers, landmarks, fog of war |
| `hex_map.py` | Base hex map, terrain types, fog of war |
| `game_data.py` | All game data (units, buildings, techs, civs, terrain, resources) |
| `empire_manager.py` | Empire management |
| `game_manager.py` | Game orchestration |
| `simulation.py` | Simulation logic |

---

## What's Left

### Phase 1: Core Game Loop & CLI Interface

#### 1A: Map Rendering Improvements
- [ ] Fix resource display on map (currently resources aren't shown)
- [ ] Add terrain icons for rivers and landmarks
- [ ] Show territory ownership colors (ASCII codes)
- [ ] Add minimap for large maps

#### 1B: Command Parser
- [ ] Move command from menu numbers to typed commands (`move 3,4`, `attack 5,6`, `research agriculture`)
- [ ] Add autocomplete for unit/city names
- [ ] Add help system (`help <command>`)
- [ ] Add undo for dangerous actions

#### 1C: Player Input System
- [ ] Replace static menu with interactive input mode (click/map selection)
- [ ] Add context-sensitive actions (right-click menu for selected unit)
- [ ] Add keyboard shortcuts (F5 for turn, M for map, C for cities)
- [ ] Add confirmation dialogs for war declarations, city founding, unit deaths

#### 1D: Info Panels
- [ ] Character sheet display (traits, stats, dynasty)
- [ ] City detail panel (all yields, health, policies)
- [ ] Empire overview (total income, army strength, tech progress)
- [ ] Turn event narrative (flavor text for events)

---

### Phase 2: Map & Exploration

#### 2A: Map Features
- [ ] Add river tiles with visual representation
- [ ] Add resource nodes with discovery mechanic
- [ ] Add climate zones (tropical, temperate, arid, cold)
- [ ] Add coastline/nautical bonuses
- [ ] Add terrain hazards (swamps, badlands)

#### 2B: Fog of War
- [ ] Fix `ImprovedFogOfWar.update_visibility()` — line 37 has `if (nq, nr) in set():` which does nothing useful
- [ ] Add visibility radius scaling with technology (e.g., Cartography increases range)
- [ ] Add exploration events (discovering new terrain types)
- [ ] Add scouting unit bonuses

#### 2C: Exploration Events
- [ ] Discover new terrain → science bonus
- [ ] Find resources → gold bonus
- [ ] Ancient ruins events (combat or reward)

---

### Phase 3: City & District System

#### 3A: District Placement
- [ ] Implement district types (Campus, Theater, Industrial, Harbor, etc.)
- [ ] District adjacency bonuses (Campus next to River = +science)
- [ ] District placement UI (click on map)
- [ ] District upgrade paths (e.g., Market → Bank → Stock Exchange)

#### 3B: City Policies
- [ ] Government policies (militaristic, trade-focused, scientific)
- [ ] Policy slots that change per era
- [ ] Policy maintenance cost (gold)
- [ ] Policy switching cost (unhappiness)

#### 3C: Building Chain
- [ ] Implement building prerequisites (Granary before Food Market)
- [ ] Wonders of the World (unique, one-per-world)
- [ ] Building destruction in war
- [ ] Building restoration cost

---

### Phase 4: Military System

#### 4A: Unit Movement & Combat
- [ ] Implement terrain-based movement costs
- [ ] Add unit promotions (veteran, elite, legendary)
- [ ] Implement siege mechanics (walls, catapults)
- [ ] Add supply line mechanics (units beyond range take penalties)
- [ ] Add morale system (affects combat effectiveness)

#### 4B: Unit Types
- [ ] Add more units per era (Ancient → Information)
- [ ] Add naval units with ocean/coast rules
- [ ] Add ranged units with attack/defense ranges
- [ ] Add support units (medics, engineers)

#### 4C: Logistics
- [ ] Supply depots for large armies
- [ ] Fortifications (camps, forts, walls)
- [ ] Garrison units (defense bonus)

---

### Phase 5: Diplomacy & Trade

#### 5A: Relations System
- [ ] Opinion modifiers (trade, borders, wars, gifts)
- [ ] Diplomacy actions (declare war, peace treaty, non-aggression, alliance)
- [ ] Trade agreements (open borders, research pact, trade route)
- [ ] Espionage (schemes, counter-schemes)

#### 5B: Trade Routes
- [ ] Establish trade routes between cities
- [ ] Trade route bonuses (gold, science, culture)
- [ ] Trade route protection (need military escort)
- [ ] Trade route disruption (raiding, piracy)

#### 5C: Vassalage & Empires
- [ ] Vassal mechanics (taxes, autonomy, rebellion)
- [ ] League/alliance systems (Delian League, Hanseatic League)
- [ ] Tributary states

---

### Phase 6: AI Improvements

#### 6A: AI Strategy
- [ ] Implement weighted strategy profiles (militaristic, scientific, cultural, diplomatic)
- [ ] AI city planning (district placement, production priorities)
- [ ] AI diplomacy (when to declare war, when to make peace)
- [ ] AI expansion patterns (settlement priority)

#### 6B: AI Difficulty
- [ ] Easy: Less research, fewer bonuses, predictable
- [ ] Medium: Balanced
- [ ] Hard: More research, better city placement, aggressive diplomacy
- [ ] Legend: Optimal play, perfect information

---

### Phase 7: Crusader Kings Elements

#### 7A: Character System
- [ ] Character traits (bold, cunning, just, tyrannical)
- [ ] Character stats (stewardship, martial, intrigue, diplomacy, learning)
- [ ] Character aging and death
- [ ] Character relationships (spouses, children, rivals)

#### 7B: Dynasty System
- [ ] Dynasty name and prestige
- [ ] Dynasty traits (wealth, martial, learning)
- [ ] Dynasty points (earned through achievements)
- [ ] Dynasty prestige bonuses

#### 7C: Succession & Inheritance
- [ ] Succession laws (primogeniture, agnatic, elective, etc.)
- [ ] Inheritance disputes and succession crises
- [ ] Heir training (young character education)
- [ ] Regency system (minor heirs)

#### 7D: Marriage & Alliances
- [ ] Marriage system (arranged marriages, dynastic marriages)
- [ ] Marriage bonuses (diplomacy, heirs, claims)
- [ ] Divorce and annulment
- [ ] Marriage plots

#### 7E: Plots & Intrigue
- [ ] Plot types (assassination, rebellion, usurpation)
- [ ] Plot success/failure mechanics
- [ ] Intrigue agents (spies, assassins)
- [ ] Counter-intelligence

---

### Phase 8: Victory Conditions

#### 8A: Win Conditions
- [ ] Domination victory (control X cities/Y% of map)
- [ ] Science victory (reach modern era + space race milestone)
- [ ] Culture victory (accumulate X culture, publish all philosophies)
- [ ] Diplomacy victory (win World Congress / gain X diplomatic points)
- [ ] Conquest victory (annex all starting capitals)
- [ ] Dynasty victory (survive X generations)

#### 8B: End Game
- [ ] Victory/defeat screen with statistics
- [ ] Dynasty tree display
- [ ] Post-game summary (turns, achievements, stats)

---

### Phase 9: Save/Load & Scenarios

#### 9A: Save System
- [ ] JSON save files (full game state)
- [ ] Multiple save slots
- [ ] Auto-save on turn end
- [ ] Save validation on load

#### 9B: Scenarios
- [ ] Classic scenario (random map)
- [ ] Historical scenarios (set date, specific civs, specific locations)
- [ ] Custom scenario editor (optional)

---

### Phase 10: Polish & Depth

#### 10A: Happiness & Stability
- [ ] Happiness system (luxury resources, entertainment buildings, overextension penalty)
- [ ] Stability system (decreases with wars, succession, conquest)
- [ ] Happiness effects (production loss, rebellion risk, growth slowdown)
- [ ] Stability effects (growth speed, rebellion chance, tax efficiency)

#### 10B: Events & Narrative
- [ ] Event chains (multi-part storylines)
- [ ] Event choices (player decisions with consequences)
- [ ] Historical scenarios (pre-set events for different eras)
- [ ] Narrative log (chronological event history with filtering)
- [ ] Character events (birth, death, marriage, scandal)
- [ ] City events (famine, plague, golden age, rebellion)
- [ ] World events (natural disasters, migrations, discoveries)

#### 10C: Civilizations (12 Total)
- [ ] 8-12 unique civs with bonuses, unique units, unique buildings
- [ ] Preferred governments per civ
- [ ] Starting terrain preferences per civ

---

## Estimated Remaining Work

| Category | Estimated New Lines | Priority |
|------|------|------|
| Map & Terrain | ~400 lines | 🔴 High |
| City & Districts | ~800 lines | 🔴 High |
| Military System | ~700 lines | 🔴 High |
| Technology & Civics | ~500 lines | 🔴 High |
| Economy & Resources | ~400 lines | 🔴 High |
| Character Deepening | ~300 lines | 🟡 Medium |
| Marriage & Dynasties | ~250 lines | 🟡 Medium |
| Court & Factions | ~300 lines | 🟡 Medium |
| Plots & Intrigue | ~200 lines | 🟡 Medium |
| Happiness & Stability | ~200 lines | 🟢 Lower |
| Events & Narrative | ~300 lines | 🟢 Lower |
| AI Improvements | ~400 lines | 🟢 Lower |
| Civilizations & Scenarios | ~300 lines | 🟢 Lower |
| Win Conditions & End Game | ~200 lines | 🟢 Lower |
| Save/Load | ~100 lines | 🟢 Lower |
| **Total** | **~4,850 lines** | |

---

## Implementation Recommendations

### Suggested Order:
1. **Map resources & terrain** (quick win, enables everything else)
2. **District & building system** (core Civ gameplay)
3. **Unit movement & combat** (core military gameplay)
4. **Trade routes & economy** (core economy gameplay)
5. **Character & dynasty** (core CK gameplay)
6. **AI improvements** (playability)
7. **Win conditions & end game** (game completion)
8. **Save/load** (persistence)
9. **Polish & narrative** (depth)

---

## Key Design Decisions

1. **Keep it pure Python** — no external dependencies required
2. **Modular architecture** — each system in its own file, minimal cross-imports
3. **JSON save format** — human-readable, easy to debug
4. **CLI-first** — ASCII map, keyboard input, no GUI required
5. **Configurable difficulty** — AI bonuses/penalties via game settings
6. **Pluggable civs** — new civs added via data files, not code changes

---

## Known Bugs

- [ ] `ImprovedFogOfWar.update_visibility()` line 37: `if (nq, nr) in set():` does nothing useful
- [ ] Resources not displayed on map
- [ ] No confirmation dialogs for dangerous actions
- [ ] No undo for commands

---

## Future Ideas (Out of Scope)

- Multiplayer (networked turns)
- GUI with Pygame/Tkinter
- Mod support via JSON data files
- Map editor
- AI-generated scenarios
- Leaderboard system

---

*Last updated: 2025-01-15*
