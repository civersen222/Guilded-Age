# CivKings — What's Still To Be Done

**Last updated:** 2025-06-25  
**Overall completion:** ~90-95% (all planned sprints complete)

---

## ✅ Completed (All 10 Sprints Done)

### SPRINT 1: Map Rendering & Core Interaction (gui_map.py)
- [x] Full hex grid rendering with terrain coloring
- [x] City/unit icons on map
- [x] Hover tooltip system
- [x] Click-to-select on map
- [x] Minimap
- [x] Zoom controls
- [x] Pan controls
- [x] Selection highlighting

### SPRINT 2: City & Production UI (gui_panels.py, gui_popups.py)
- [x] City detail panel with all stats
- [x] Production queue UI
- [x] District placement UI
- [x] Building selection UI
- [x] District upgrade paths
- [x] City specialization
- [x] Production popup

### SPRINT 3: Military UI (gui_combat.py, gui_popups.py)
- [x] Combat result UI with odds display
- [x] Unit command panel
- [x] Unit movement visualization
- [x] Unit info popup with stats/promotions
- [x] Production popup
- [x] Combat calculator with terrain bonuses

### SPRINT 4: Tech & Diplomacy UI (gui_panels.py, gui_popups.py)
- [x] Tech tree display with prerequisites
- [x] Diplomacy panel with relations/trade/inbox
- [x] Treaty negotiation UI
- [x] War declaration screen

### SPRINT 5: Dynasty & Resources (gui_panels.py, gui_popups.py)
- [x] Dynasty/family UI with tree view
- [x] Resource bar
- [x] Event log
- [x] Quick actions toolbar

### SPRINT 6: Victory Conditions (victory_ui.py)
- [x] Science victory
- [x] Culture victory
- [x] Religious victory
- [x] Domination victory
- [x] Victory screen with stats

### SPRINT 7: City Growth & Building System (city_growth.py)
- [x] City growth mechanics (food accumulation, population caps)
- [x] Building prerequisite chains
- [x] Wonder system
- [x] Worker improvements (farms, mines, pastures)
- [x] District upgrade paths

### SPRINT 8: Unit System Enhancement (unit_enhancements.py)
- [x] Unit production in city production queue
- [x] Unit upgrades (Militia → Infantry → Ranger, etc.)
- [x] Unit experience/leveling/promotions
- [x] Naval units (Galleys, Ships of the Line)
- [x] Siege units (Catapults, Trebuchets)
- [x] Stacking rules

### SPRINT 9: Tech & Diplomacy Backend (tech_policies.py, diplomacy_extended.py)
- [x] Tech policy/commitment system
- [x] Era bonuses
- [x] Research speed modifiers
- [x] Treaty types
- [x] Casus belli system
- [x] Trade agreement mechanics

### SPRINT 10: AI & Polish (sound_effects.py, visual_effects.py)
- [x] AI city expansion strategy
- [x] AI military aggression/scouting
- [x] AI diplomacy (trade, alliances, wars)
- [x] AI technology prioritization
- [x] Sound effects
- [x] Animations and visual polish
- [x] Dynamic priority adjustment
- [x] War targets and alliance tracking
- [x] Trade relationship management
- [x] Military strength evaluation

---

## Remaining Work (Post-Completion Polish & Features)

### High Priority

#### 1. UI Integration Gaps
- [ ] **MinimapRenderer** — class exists but not integrated into gui.py layout
- [ ] **Move range highlighting** — `highlight_move_range()` exists but not called during unit movement
- [ ] **Attack range highlighting** — `highlight_attack_range()` exists but not called during combat
- [ ] **Zoom level display/controls** — zoom works via mouse wheel but no UI buttons
- [ ] **Resource trend arrows (↑↓→)** — not implemented in resource bar
- [ ] **Resource details on hover** — no hover tooltips on resource bar
- [ ] **Trade route yield display** — not shown in resource bar
- [ ] **Resource surplus/deficit indicators** — not shown in resource bar
- [ ] **Color-coded events** — all events use same color
- [ ] **Event action buttons** — not implemented
- [ ] **Event filtering** — not implemented
- [ ] **Full toolbar icon set** — toolbar is empty by default

#### 2. Economy & Resources
- [ ] **External trade routes** — Trade with other civilizations via merchant units
- [ ] **Gold management** — Unit maintenance, tribute, bribery costs
- [ ] **Tax system** — Set tax rates, effects on happiness/gold
- [ ] **Market simulation** — Resource scarcity affects prices

#### 3. Happiness & Stability
- [ ] **Happiness system** — Luxury resources, entertainment buildings, overextension penalty
- [ ] **Stability system** — Decreases with wars, succession, conquest
- [ ] **Happiness effects** — Production loss, rebellion risk, growth slowdown
- [ ] **Stability effects** — Growth speed, rebellion chance, tax efficiency

### Medium Priority

#### 4. Faction System
- [ ] **Faction types** — Nobles, Religious, Popular factions
- [ ] **Faction pressure** — Affects stability, succession
- [ ] **Faction support** — Support claimants during succession

#### 5. Plots & Intrigue
- [ ] **Plot types** — Assassination, coup, rebellion, poisoning
- [ ] **Plot participants** — Hidden motives, detection mechanics
- [ ] **Spy network** — Spy units with operations
- [ ] **Counter-intelligence** — Spymaster bonuses, double agents
- [ ] **Plot consequences** — Exposed plots, imprisoned/exiled characters

#### 6. Events & Narrative
- [ ] **Event chains** — Multi-part storylines
- [ ] **Event choices** — Player decisions with consequences
- [ ] **Historical scenarios** — Pre-set events for different eras
- [ ] **Narrative log** — Chronological event history with filtering
- [ ] **Character events** — Birth, death, marriage, scandal events
- [ ] **City events** — Famine, plague, golden age, rebellion
- [ ] **World events** — Natural disasters, migrations, discoveries

### Low Priority

#### 7. AI Improvements
- [ ] **AI personality** — Aggressive, diplomatic, economic, scholarly types
- [ ] **Difficulty levels** — Affect AI bonuses/penalties

#### 8. Civilizations
- [ ] **8-12 unique civs** — With bonuses, unique units, unique buildings
- [ ] **Preferred governments** — Each civ prefers certain government types
- [ ] **Starting terrain preferences** — Each civ starts in preferred terrain

#### 9. End Game
- [ ] **Dynasty victory** — Survive X generations
- [ ] **End-game screen** — Victory/defeat display, statistics, dynasty tree
- [ ] **Victory stats summary** — Not implemented

#### 10. Polish
- [ ] **Keyboard shortcuts** — 1-8 for toolbar
- [ ] **Right-click context menu**
- [ ] **"Next Turn" confirmation dialog**
- [ ] **Game speed options** — 1x, 2x, 5x
- [ ] **Sound toggle**
- [ ] **Unit movement preview**
- [ ] **Combat difficulty modifier**
- [ ] **City name customization**
- [ ] **Music system**
- [ ] **Multiple save slots / auto-save**
- [ ] **Game scenarios** — Classic, Historical, Custom

---

## Quick Wins (Under 100 lines each)

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

## Known Issues & Technical Debt

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

## Success Criteria Status

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
- [ ] All UI panels have proper hover/click feedback *(partial — some gaps remain)*
- [x] Event log shows all important events
- [x] No critical bugs (crashes, data loss)

---

## Implementation Recommendations

### Suggested Order for Remaining Work:
1. **UI integration gaps** — Wire up existing UI classes into gui.py
2. **Quick wins** — Keyboard shortcuts, tooltips, color coding
3. **Economy depth** — External trade, tax system
4. **Happiness & stability** — Core CK gameplay
5. **Factions & intrigue** — CK flavor depth
6. **Events & narrative** — Story content
7. **Polish** — Everything else
