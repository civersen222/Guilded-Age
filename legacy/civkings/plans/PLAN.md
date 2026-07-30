# CivKings - Full Game Completion Plan

## Current State Assessment
**Completion: ~25-30%**

Working systems: character stats/traits, dynasty/lineage, basic hex map, fog of war, basic combat, simple research tree, city production queue, border expansion, succession laws, vassalage/taxes (partial).

Dead code: `src/` TypeScript files — ignore or remove.

---

## Phase 0: Cleanup
- [ ] Remove `src/` directory (TypeScript stubs, not needed for Python-only)
- [ ] Remove `__pycache__`
- [ ] Add `requirements.txt` (empty — stdlib only)
- [ ] Add `README.md` with game description and controls
- [ ] Add `game_data.py` — centralized data definitions (terrain yields, unit types, buildings, traits, tech tree, events)

## Phase 1: Core Game Loop & CLI Interface
The game needs a real playable loop, not just a simulation script.

- [ ] **`ui.py`** — CLI interface
  - Map rendering with terrain, cities, units, fog of war
  - Command parser (move, attack, found city, produce, research, interact character)
  - Info panels (city stats, character sheet, empire overview)
  - Event log / narrative display
  - Confirmation prompts for dangerous actions

- [ ] **`game.py`** — Game orchestration (replaces `main.py` + `game_manager.py`)
  - `Game` class holding all state
  - `turn()` method: player phase → NPC phase → event resolution
  - Phase management (Player Input → Resolution → Next Turn)
  - Player vs AI turn flow
  - Game state management (playing, paused, game over)

## Phase 2: Civilization Systems

### 2A: Map & Exploration
- [ ] **Map features** in `game_data.py`:
  - Rivers, hills, resource nodes (iron, horses, gold, spices, etc.)
  - Climate zones affecting yields
  - Coastline bonuses for naval
- [ ] **Fog of war improvements**:
  - Visibility radius based on unit/city position
  - Discovery mechanics (exploring reveals terrain type, then resources)
  - Landmarks/ruins that grant bonuses when discovered
- [ ] **Exploration events**:
  - Discovering new terrain types grants science
  - Finding resources grants gold/science
  - Ancient ruins events

### 2B: Cities & Buildings
- [ ] **District system** (`game_data.py`):
  - Campus (science adjacency to mountains/other campuses)
  - Commercial Hub (gold adjacency to markets/roads)
  - Holy Site (faith, can found religion)
  - Encampment (unit maintenance reduction)
  - Harbor (naval production, trade)
  - Entertainment (happiness)
  - Fortress (defense bonus)
  - Each district has adjacency rules and yields

- [ ] **Building system**:
  - Buildings within districts (Granary, Market, Temple, Library, etc.)
  - Building provides specific bonuses
  - Wonders (one-time global effects, unique buildings)

- [ ] **City management**:
  - Worker improvements (Farm, Mine, Quarry, Pasture, Fortress)
  - Tile assignment/unassignment
  - Specialist slots (Scholar, Merchant, Hunter, etc.)
  - Production queue with unit/building/district options

### 2C: Economy
- [ ] **Resources** (`game_data.py`):
  - Bonus resources (wheat, cattle, fish) — food
  - Luxury resources (silk, spices, ivory) — happiness
  - Strategic resources (iron, horses, oil) — unit requirements

- [ ] **Trade routes**:
  - Internal: city-to-city gold/food routes
  - External: trade with other civilizations
  - Merchant units for external trade

- [ ] **Gold management**:
  - Unit maintenance costs
  - Tribute payments
  - Bribery costs
  - Gold per turn display

### 2D: Military
- [ ] **Unit types** (`game_data.py`):
  - Melee (Swordsman, Legion)
  - Ranged (Archer, Crossbowman)
  - Cavalry (Horseman, Knight)
  - Siege (Siege Tower, Catapult)
  - Naval (Trireme, Galley)
  - Settler (founds cities)
  - Worker (improves tiles)
  - Each with movement, attack, defense, cost, resource requirements

- [ ] **Unit promotions**:
  - Experience system (units gain XP from combat)
  - Promotion tiers (Veteran, Elite, Champion)
  - Bonuses per promotion tier

- [ ] **Movement**:
  - Hex movement points
  - Terrain movement costs
  - Roads/harbors reduce costs
  - Fortification action

- [ ] **Combat**:
  - Attack/defense with terrain bonuses
  - Flanking bonuses
  - Siege mechanics (attack fortified cities)
  - Naval combat
  - Support units (healers, siege engines)
  - Retreating option

- [ ] **Military organization**:
  - Stacking limits
  - Army morale
  - Logistics (supply lines for distant armies)

### 2E: Technology & Policy
- [ ] **Full tech tree** (`game_data.py`):
  - 40+ technologies across Scientific/Military/Civic branches
  - Prerequisites chains
  - Tech unlocks: units, buildings, districts, improvements, bonuses
  - Era system (Ancient → Classical → Medieval → Renaissance → Industrial → Modern)

- [ ] **Policy/Civics system**:
  - Government types (Monarchy, Republic, Theocracy, Feudalism, etc.)
  - Policy slots (Military, Economic, Cultural, Defense)
  - Policy effects (conscription, trade laws, etc.)
  - Government transition mechanics

### 2F: Happiness & Stability
- [ ] **Happiness system**:
  - Base happiness from population
  - Luxury resources boost happiness
  - Entertainment buildings boost happiness
  - Overextension penalty (too many cities)
  - Religious unity bonus
  - Conquered population penalty
  - Happiness effects: production loss, rebellion risk, growth slowdown

- [ ] **Stability system**:
  - Stability decreases with wars, succession, conquest
  - Stability affects growth speed, rebellion chance, tax efficiency
  - Policies/actions to restore stability

## Phase 3: Crusader Kings Systems

### 3A: Character Deepening
- [ ] **Lifestyle/Skill progression**:
  - Characters gain skill points from actions
  - Diplomacy, Martial, Stewardship, Intrigue, Scholarship trees
  - Skill levels (Novice → Expert → Master → Legendary)
  - Skills unlock special actions

- [ ] **Age system**:
  - Characters age each turn
  - Age affects stats (prime years, decline)
  - Death events at old age
  - Life expectancy trait

- [ ] **Personality traits**:
  - Expand trait database (50+ traits)
  - Positive, negative, and neutral traits
  - Trait combinations create modifiers
  - Traits change over time based on events

### 3B: Marriage System
- [ ] **Marriage mechanics**:
  - Character marriage proposals
  - Dowry system (gold, promises, territory)
  - Marriage creates alliance between rulers
  - Political marriages for alliances
  - Divorce mechanics (costs prestige/opinion)
  - Widow/widower status

- [ ] **Marriage events**:
  - Random marriage proposals
  - Arranged marriages for diplomacy
  - Dynastic marriages to secure alliances
  - Marriage ceremony events

### 3C: Alliances & Diplomacy
- [ ] **Diplomatic relations**:
  - Relations score between civilizations (-100 to +100)
  - Declaration of War (costs prestige, requires casus belli)
  - Peace treaties (temporaray truces)
  - Non-aggression pacts
  - Defensive pacts
  - Trade agreements
  - Vassal states (full vassalage)
  - Tributary states

- [ ] **Diplomatic actions**:
  - Demand tribute
  - Request alliance
  - Broker peace
  - Spy on negotiations
  - Bribe officials
  - Propose marriage

### 3D: Plots & Conspiracies
- [ ] **Plot system**:
  - Characters can plot against rulers
  - Plot participants have hidden motives
  - Plot success depends on intrigue stats, resources
  - Plot types: assassination, coup, rebellion, poisoning
  - Detection mechanics (spymaster bonus)
  - Consequences of exposed plots

- [ ] **Spy network**:
  - Spy units with operations (sabotage, steal tech, incite rebellion)
  - Counter-intelligence
  - Double agents

### 3E: Religion & Faith
- [ ] **Religion system**:
  - Multiple religions (pantheon, monotheism, polytheism)
  - Holy orders (clergy units)
  - Religious doctrines (faith-based bonuses)
  - Religious spread mechanics
  - Heresy and schism
  - Holy wars / crusades
  - Religious unity affects happiness

- [ ] **Faith resource**:
  - Generated by holy sites and religious population
  - Used for religious actions (crusades, inquisitions)
  - Converts to legitimacy

### 3F: Court & Factions
- [ ] **Court positions**:
  - Marshal (military bonus)
  - Spymaster (intrigue bonus, plot detection)
  - Chancellor (diplomacy, gold bonus)
  - Steward (stewardship, economy bonus)
  - Chaplain (faith bonus)
  - Each position can be filled by a character
  - Position holders provide ongoing bonuses

- [ ] **Faction system**:
  - Nobles faction (wants more power)
  - Religious faction (wants religious policies)
  - Popular faction (wants lower taxes/more happiness)
  - Factions can support claimants during succession
  - Faction pressure affects stability

### 3G: Succession Deepening
- [ ] **Succession laws**:
  - Primogeniture (eldest inherits all)
  - Ultogeniture (youngest inherits)
  - Gavelkind (partible inheritance)
  - Seniority (eldest male)
  - Cognatic (gender neutral)
  - Elective (highest prestige determines heir)
  - Custom succession events

- [ ] **Succession crises**:
  - Multiple claimants with different laws
  - Civil war risk
  - Fragmentation of empire
  - Foreign intervention in succession

## Phase 4: AI & Multi-Civilization

- [ ] **Civilization definitions** (`game_data.py`):
  - 8-12 unique civilizations with bonuses
  - Unique units (replace standard units)
  - Unique buildings
  - Preferred government types
  - Starting terrain preferences

- [ ] **AI systems**:
  - AI personality (aggressive, diplomatic, economic, scholarly)
  - AI decision making (what to produce, where to expand, who to ally)
  - AI diplomacy (form alliances, declare war, trade)
  - AI character management (marriage, appointments, plots)
  - Difficulty levels (affect AI bonuses/penalties)

- [ ] **AI turn processing**:
  - City production decisions
  - Unit movement and actions
  - Diplomacy decisions
  - Research priority

## Phase 5: Events & Narrative

- [ ] **Event system**:
  - Random events (already partially exists)
  - Triggered events (tech unlocks, character milestones, death)
  - Event chains (multi-part storylines)
  - Event choices with consequences
  - Historical scenario events

- [ ] **Event categories**:
  - Character events (birth, death, marriage, scandal)
  - City events (famine, plague, golden age, rebellion)
  - World events (natural disasters, migrations, discoveries)
  - Diplomatic events (embassies, threats, treaties)
  - Military events (battles, sieges, conquests)
  - Religious events (miracles, heresies, reformations)

- [ ] **Narrative log**:
  - Chronological event history
  - Highlight important events
  - Filter by category

## Phase 6: Polish & Completion

- [ ] **Save/Load system**:
  - JSON save files
  - Multiple save slots
  - Auto-save on turn end

- [ ] **Game scenarios**:
  - Classic (random map, random civs)
  - Historical (set date, specific civs, specific locations)
  - Custom (choose parameters)

- [ ] **Win conditions**:
  - Domination (control X cities or Y% of map)
  - Science (reach modern era + space race milestone)
  - Culture (accumulate X culture, publish all philosophies)
  - Diplomacy (win World Congress / gain X diplomatic victory points)
  - Conquest (annex all starting capitals)
  - Dynasty (survive X generations)

- [ ] **End-game screen**:
  - Victory/defeat display
  - Statistics (turns played, cities, techs, battles, characters)
  - Dynasty tree visualization
  - Option to restart or continue

---

## Implementation Order & File Structure

```
civkings/
├── README.md
├── game_data.py          # All static data (terrain, units, buildings, tech, traits, events, civs)
├── game.py               # Main game class, turn management, orchestration
├── ui.py                 # CLI rendering, input, display
├── map.py                # Hex map, terrain, resources, fog of war, cities on map
├── city.py               # City logic, districts, buildings, production
├── military.py           # Units, armies, combat, movement
├── economy.py            # Resources, trade routes, gold, yields
├── diplomacy.py          # Civilization relations, alliances, wars, pacts
├── characters.py         # Characters, traits, lifestyles, court positions
├── dynasty.py            # Dynasty, succession, marriage, heirs
├── plots.py              # Plots, spies, intrigue
├── religion.py           # Religion, faith, holy sites, doctrines
├── ai.py                 # AI civilizations, decision making
├── events.py             # Event system, event chains, narrative
├── tech.py               # Technology tree, civics/policies
├── save.py               # Save/load game
└── main.py               # Entry point: load game, run loop
```

## Priority & Scope Notes

**Must-have for "full game":**
- Phase 0 (cleanup) + Phase 1 (core loop) — this alone makes it playably functional
- Phase 2A-2B (map, cities, districts) — core Civ gameplay
- Phase 2D (military units, movement, combat) — core Civ gameplay
- Phase 2E (tech tree) — core Civ gameplay
- Phase 3A-3B (characters, marriage) — core CK gameplay
- Phase 3C (diplomacy) — core CK gameplay
- Phase 4 (AI + multi-civ) — required for a strategy game

**Should-have (makes it great):**
- Phase 2C (economy depth)
- Phase 2F (happiness)
- Phase 3D (plots)
- Phase 3E (religion)
- Phase 3F (court/factions)
- Phase 5 (events/narrative)

**Nice-to-have (can be simplified):**
- Phase 3G (succession deepening) — implement basic version in Phase 3B
- Phase 6 (scenarios, polish) — polish after core is done

## Estimated New Code
- `game_data.py`: ~800 lines (all static data)
- `game.py`: ~400 lines (orchestration)
- `ui.py`: ~600 lines (CLI rendering)
- `map.py`: ~300 lines (map improvements)
- `city.py`: ~500 lines (districts, buildings)
- `military.py`: ~600 lines (units, combat, movement)
- `economy.py`: ~300 lines (resources, trade)
- `diplomacy.py`: ~400 lines (relations, alliances)
- `characters.py`: ~400 lines (deep characters)
- `dynasty.py`: ~350 lines (marriage, succession)
- `plots.py`: ~250 lines (plots, spies)
- `religion.py`: ~300 lines (religion system)
- `ai.py`: ~500 lines (AI logic)
- `events.py`: ~300 lines (event system)
- `tech.py`: ~250 lines (tech tree expansion)
- `save.py`: ~100 lines (save/load)
- `main.py`: ~50 lines (entry point)

**Total: ~6,140 lines of new Python code**

## Key Design Decisions
1. **Pure stdlib** — no external dependencies
2. **Data-driven** — all game data in `game_data.py`, code is thin logic
3. **CLI text-first** — ASCII map, text descriptions, numbered menus
4. **Turn-based** — each turn = 1 year in-game
5. **Single-player** — no network, no multiplayer
