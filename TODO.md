# CivKings — What's Still To Be Done

**Last updated:** Current codebase state after Phase 0 completion  
**Overall completion:** ~40-45%

---

## What's Already Done

### Phase 0 — Complete ✓
- `game_data.py` — Centralized data (terrain, units, buildings, traits, tech tree, civilizations, doctrines)
- `city.py` — City class with production, districts, buildings, yields
- `military.py` — Military manager with unit combat
- `economy.py` — Gold, science, food, culture, faith resources + trade routes
- `diplomacy.py` — Alliances, wars, truces, trade agreements between civs
- `religion.py` — Religions, faith, holy sites, doctrines, heresy detection
- `tech.py` — Technology tree with research progress
- `events.py` — Event pool, random event generation, event history
- `ai.py` — AI player with aggression, priorities, action decisions
- `simulation.py` — Character stats, traits, dynasty/lineage, marriage, succession
- `game.py` — Game orchestration, turn processing, victory checks
- `maps.py` / `hex_map.py` — Hex map, terrain generation, fog of war, city borders
- `plots.py` — Plot/intrigue system
- `ui.py` — CLI rendering (map, panels, input)
- `main.py` — Entry point
- `requirements.txt`, `README.md`, `.gitignore` — Project setup

### Phase 1.1 — Complete ✓
- `hex_map.py` — Continent generation via simplex noise elevation maps
- `hex_map.py` — Terrain smoothing passes to reduce fragmentation
- `hex_map.py` — Resource placement with terrain compatibility matrix
- `hex_map.py` — `has_river` property on HexTile
- `game_data.py` — Resource yields, requirements, compatibility mappings
- `game_data.py` — Climate zones, coastline bonuses, landmarks/ruins data
- `game_data.py` — `RiverNetwork` class with mountain-to-water flow algorithm
- `game_data.py` — `RiverFeature` class with adjacency bonuses

### Phase 1.2 — Complete ✓
- `hex_map.py` — River generation integrated into `WorldMap.generate()`
- `game_data.py` — `RiverType` enum (River, Lake, Swamp)
- `game_data.py` — Rivers flow downhill toward water, blocked by mountains

---

## Still To Be Done

### 🔴 High Priority (Core Gameplay)

#### 1. Map & Terrain Depth
- [ ] **Resource nodes** — Iron, horses, gold, spices, wheat, cattle, fish on the map
- [ ] **Rivers & hills** — Special terrain features with adjacency bonuses
- [ ] **Climate zones** — Affect crop yields, movement, happiness
- [ ] **Coastline bonuses** — Naval production and trade bonuses
- [ ] **Landmarks/ruins** — Discoverable tiles that grant bonuses
- [ ] **Exponential fog** — Fog that expands with distance from cities/units

#### 2. City & District System (Major Work)
- [ ] **Full district types** — Campus, Commercial Hub, Holy Site, Encampment, Harbor, Entertainment, Fortress
- [ ] **District adjacency rules** — Bonuses for placing districts next to mountains, rivers, other districts
- [ ] **Building types** — Granary, Market, Temple, Library, Walls, etc. with specific stat bonuses
- [ ] **Worker improvements** — Farms, Mines, Quarries, Pastures, Fortresses on tiles
- [ ] **Tile management** — Assign/unassign tiles to cities, specialist slots
- [ ] **Wonder system** — One-time global effects, unique buildings
- [ ] **Production queue UI** — Select what to build (unit/building/district)
- [ ] **City growth mechanics** — Food accumulation, population caps, growth events

#### 3. Military System (Major Work)
- [ ] **Full unit roster** — Melee, ranged, cavalry, siege, naval, settler, worker types
- [ ] **Unit stats** — Attack, defense, movement, range, HP per unit type
- [ ] **Unit promotions** — XP system (Novice → Veteran → Elite → Champion)
- [ ] **Hex movement** — Movement points, terrain costs, roads/harbors reduce costs
- [ ] **Combat system** — Attack/defense calculations, terrain bonuses, flanking, siege mechanics
- [ ] **Naval combat** — Sea battles, coastal attacks
- [ ] **Unit stacking** — Army limits, support units (healers, siege engines)
- [ ] **Fortification action** — Units can fortify for defense bonus
- [ ] **Retreat option** — Escape damaged units from combat

#### 4. Technology & Civics (Major Work)
- [ ] **Full tech tree** — 40+ technologies across Scientific/Military/Civic branches
- [ ] **Prerequisite chains** — Tech A unlocks Tech B, etc.
- [ ] **Tech unlocks** — Units, buildings, districts, improvements, stat bonuses
- [ ] **Era system** — Ancient → Classical → Medieval → Renaissance → Industrial → Modern
- [ ] **Civics/policies** — Government types (Monarchy, Republic, Theocracy, Feudalism)
- [ ] **Policy slots** — Military, Economic, Cultural, Defense policies
- [ ] **Government transition** — Switch government types with costs/bonuses

#### 5. Economy & Resources (Major Work)
- [ ] **Resource types** — Bonus (food), Luxury (happiness), Strategic (unit requirements)
- [ ] **Internal trade routes** — City-to-city gold/food routes
- [ ] **External trade routes** — Trade with other civilizations via merchant units
- [ ] **Gold management** — Unit maintenance, tribute, bribery costs
- [ ] **Tax system** — Set tax rates, effects on happiness/gold
- [ ] **Market/economy simulation** — Resource scarcity affects prices

### 🟡 Medium Priority (CK Integration)

#### 6. Character Deepening
- [ ] **Lifestyle/skill progression** — Diplomacy, Martial, Stewardship, Intrigue, Scholarship
- [ ] **Skill levels** — Novice → Expert → Master → Legendary
- [ ] **Age system** — Characters age each turn, effects on stats, death at old age
- [ ] **Expanded trait database** — 50+ traits, positive/negative/neutral combinations
- [ ] **Trait changes** — Traits evolve based on events and actions

#### 7. Marriage & Dynasties
- [ ] **Marriage proposals** — Character-to-character marriage mechanics
- [ ] **Dowry system** — Gold, promises, territory as dowry
- [ ] **Political marriages** — Alliances through marriage
- [ ] **Divorce mechanics** — Costs prestige/opinion
- [ ] **Widow/widower status** — Remarriage options
- [ ] **Marriage events** — Random proposals, arranged marriages, ceremonies

#### 8. Court & Factions
- [ ] **Court positions** — Marshal, Spymaster, Chancellor, Steward, Chaplain
- [ ] **Position holders** — Characters fill positions, provide bonuses
- [ ] **Faction system** — Nobles, Religious, Popular factions
- [ ] **Faction pressure** — Affects stability, succession
- [ ] **Faction support** — Support claimants during succession

#### 9. Plots & Intrigue (Partial)
- [ ] **Plot types** — Assassination, coup, rebellion, poisoning
- [ ] **Plot participants** — Hidden motives, detection mechanics
- [ ] **Spy network** — Spy units with operations (sabotage, steal tech, incite rebellion)
- [ ] **Counter-intelligence** — Spymaster bonuses, double agents
- [ ] **Plot consequences** — Exposed plots, imprisoned/exiled characters

### 🟢 Lower Priority (Polish & Depth)

#### 10. Happiness & Stability
- [ ] **Happiness system** — Luxury resources, entertainment buildings, overextension penalty
- [ ] **Stability system** — Decreases with wars, succession, conquest
- [ ] **Happiness effects** — Production loss, rebellion risk, growth slowdown
- [ ] **Stability effects** — Growth speed, rebellion chance, tax efficiency

#### 11. Events & Narrative
- [ ] **Event chains** — Multi-part storylines
- [ ] **Event choices** — Player decisions with consequences
- [ ] **Historical scenarios** — Pre-set events for different eras
- [ ] **Narrative log** — Chronological event history with filtering
- [ ] **Character events** — Birth, death, marriage, scandal events
- [ ] **City events** — Famine, plague, golden age, rebellion
- [ ] **World events** — Natural disasters, migrations, discoveries

#### 12. AI Improvements
- [ ] **AI personality** — Aggressive, diplomatic, economic, scholarly types
- [ ] **AI diplomacy** — Form alliances, declare war, trade negotiations
- [ ] **AI character management** — Marriage, appointments, plots
- [ ] **Difficulty levels** — Affect AI bonuses/penalties
- [ ] **AI city management** — Production priorities, district placement

#### 13. Civilizations (12 Total)
- [ ] **8-12 unique civs** — With bonuses, unique units, unique buildings
- [ ] **Preferred governments** — Each civ prefers certain government types
- [ ] **Starting terrain preferences** — Each civ starts in preferred terrain

#### 14. Win Conditions & End Game
- [ ] **Domination victory** — Control X cities or Y% of map
- [ ] **Science victory** — Reach modern era + space race milestone
- [ ] **Culture victory** — Accumulate X culture, publish all philosophies
- [ ] **Diplomacy victory** — Win World Congress / gain X diplomatic points
- [ ] **Conquest victory** — Annex all starting capitals
- [ ] **Dynasty victory** — Survive X generations
- [ ] **End-game screen** — Victory/defeat display, statistics, dynasty tree

#### 15. Save/Load & Scenarios
- [ ] **JSON save files** — Save game state
- [ ] **Multiple save slots** — Load different saves
- [ ] **Auto-save** — Save on turn end
- [ ] **Game scenarios** — Classic, Historical, Custom
- [ ] **Historical scenarios** — Set date, specific civs, specific locations

---

## Estimated Remaining Work

| Category | Estimated New Lines | Priority |
|----------|-------------------|----------|
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
3. **Full unit roster & movement** (core Civ gameplay)
4. **Combat system** (core Civ gameplay)
5. **Full tech tree** (core Civ gameplay)
6. **Economy depth** (resources, trade, taxes)
7. **Character deepening** (core CK gameplay)
8. **Marriage & dynasties** (core CK gameplay)
9. **Court & factions** (CK flavor)
10. **Plots & intrigue** (CK flavor)
11. **AI improvements** (playability)
12. **Events & narrative** (flavor)
13. **Win conditions & end game** (completion)
14. **Save/Load** (polish)
15. **Scenarios & polish** (final touches)

### Key Design Principles (from PLAN.md):
- **Pure stdlib** — no external dependencies
- **Data-driven** — all game data in `game_data.py`, code is thin logic
- **CLI text-first** — ASCII map, text descriptions, numbered menus
- **Turn-based** — each turn = 1 year in-game
- **Single-player** — no network, no multiplayer
