# CivKings — Road to Playable

> Feed this plan to CynCo one sprint at a time. Each sprint is a self-contained chunk that produces testable progress. Copy the sprint text into the chat as your prompt.

---

## Sprint 0: Fix Fatal Circular Import (5 min)

```
The game cannot import at all. military.py and combat.py have a circular dependency that causes a NameError at module load time. Fix this before anything else.

1. The problem: military.py imports CombatResult from combat.py. combat.py uses Unit (from military.py) in function signatures. At import time, Python tries to load both simultaneously and fails with NameError: name 'Unit' is not defined.

2. Fix: In combat.py, move the import of Unit into a TYPE_CHECKING block:
   - Add `from __future__ import annotations` at the top of combat.py
   - Move `from military import Unit` into `if TYPE_CHECKING:` block
   - This defers the type reference so it doesn't trigger at import time

3. Do the same in military.py if it references combat types in signatures:
   - Add `from __future__ import annotations` at the top
   - Move `from combat import CombatResult` into `if TYPE_CHECKING:` block
   - For any runtime usage of CombatResult (not just type hints), use a local import inside the function body instead

4. Verify the full import chain loads:
   python -c "from game import Game; print('OK')"
   This must succeed with zero errors before moving to Sprint 1.

5. Run: python main.py — confirm it at least starts (GUI errors from missing tkinter in headless are fine, but no ImportError or NameError).
```

---

## Sprint 1: GUI Launches + AI Exists (15 min)

```
Fix the import error that prevents the GUI from launching, then wire the AI into the game loop so opponents actually take turns.

1. In ai.py, the import of TreatyType and CasusBelliType fails because they're in diplomacy_extended.py, not diplomacy.py. Fix the import to pull from the correct module.

2. In game.py process_turn(), the AI players are never called. After processing the human player's turn, loop through AI civilizations and call their decision-making (move units, build in cities, research tech). The AIPlayer class already exists in ai.py with methods for this.

3. Fix the religion.py typo: self.finder should be self.founder (line 14).

4. Verify: python gui.py launches without errors. Start a new game. Hit "End Turn" and confirm AI civs do something (move units, start production).
```

---

## Sprint 2: Unit Movement on the Map (1 session)

```
Make units movable on the hex map. The player clicks a unit, sees valid move hexes highlighted, clicks a destination, unit moves.

1. In gui_map.py, add click handler: left-click on a hex with a unit selects it. Highlight valid movement hexes (use unit.movement_points and hex adjacency from hex_map.py). Left-click on a highlighted hex moves the unit there.

2. In military.py, add a move_unit(unit, target_hex) method that updates the unit's position, deducts movement points, and updates fog of war.

3. In gui.py, after a unit moves, refresh the hex map canvas to show the new position. Clear the highlight.

4. Add right-click to deselect. Show selected unit info in the bottom status bar.

5. Verify: start a game, click a unit (warrior or settler), see blue highlighted hexes, click one, unit moves there. Movement points decrease. Fog of war updates.
```

---

## Sprint 3: City Production Queue (1 session)

```
Let the player choose what each city builds. Click a city on the map or in the city panel, open the production popup, select a building/unit/district, it goes into the queue and completes over turns.

1. The production popup already exists in gui_popups.py. Wire it: clicking a city in the city panel or on the map opens it. The popup should show available buildings, units, and districts with their costs.

2. In city.py, the production queue logic exists. Make sure: when the player selects an item, it's added to the queue. Each turn, production points accumulate. When complete, the building/unit is created.

3. For units: when production completes, spawn the unit on the city's hex tile. Add it to the MilitaryManager.

4. For buildings: when complete, add to the city's building list and apply yield bonuses.

5. Show production progress in the city panel (e.g., "Granary: 15/30 production").

6. Verify: open a city, queue a Warrior, end turn a few times, warrior appears on the city tile.
```

---

## Sprint 4: End Turn Flow + GUI Refresh (1 session)

```
Make "End Turn" actually advance the game and refresh everything on screen.

1. Add an "End Turn" button to the main GUI (bottom bar or prominent button). When clicked: call game.process_turn(), then refresh ALL panels (map, city list, unit list, tech, economy, diplomacy).

2. After process_turn(), update: hex map (unit positions, fog of war, city borders), city panel (population, production progress, yields), unit panel (movement points reset), tech panel (research progress), economy panel (gold, science totals).

3. Show the turn number prominently (e.g., "Turn 15 — Ancient Era").

4. Display events that fired during the turn as a popup or notification banner.

5. Show a "Year" counter based on turn number (e.g., Turn 1 = 4000 BC, scaling forward).

6. Verify: play 10 turns. Watch cities grow population, tech research, gold accumulate, AI units move around the map.
```

---

## Sprint 5: Combat + Unit Interactions (1 session)

```
When a unit moves onto a hex with an enemy unit, trigger combat. Show the result.

1. In the movement handler from Sprint 2: if the target hex has an enemy unit, don't move — instead call combat.resolve_combat(attacker, defender, terrain). Show the result in a popup (casualties, winner).

2. If the attacker wins, the defender is destroyed and the attacker moves onto the hex. If the defender wins, the attacker stays in place with reduced health.

3. Add health bars to unit rendering on the hex map (small colored bar under the unit icon).

4. Handle city capture: if a military unit moves onto a hex with an enemy city and no defending unit, capture the city (change ownership). Show a "City Captured!" popup.

5. Verify: move a warrior toward an AI unit. Attack it. See combat result. Winner survives, loser disappears.
```

---

## Sprint 6: Tech Tree + Research Selection (1 session)

```
Let the player choose which technology to research. Show the tech tree visually.

1. The tech tree popup exists in gui_popups.py. Wire it: show all techs organized by era, with prerequisite lines drawn between them. Researched techs are green, available techs are white, locked techs are gray.

2. Click an available tech to set it as the current research target. Show progress in the tech panel ("Researching: Bronze Working — 12/30 science").

3. When research completes, show a notification, unlock the tech's bonuses (new buildings, units, abilities), and auto-open the tech selection popup for the next tech.

4. Apply tech bonuses: if a tech unlocks a building, it appears in city production lists. If it unlocks a unit, it appears in recruitment options.

5. Verify: start researching Bronze Working, end turns until it completes, confirm Swordsman unit becomes available in city production.
```

---

## Sprint 7: Diplomacy Actions (1 session)

```
Let the player interact with other civilizations: declare war, propose alliances, trade.

1. In the diplomacy panel, show all known civilizations with their relationship score (-100 to +100) and current status (peace/war/alliance).

2. Add action buttons: "Declare War", "Propose Alliance", "Send Trade Route", "Offer Treaty". Each calls the appropriate DiplomacyManager method.

3. AI civs should respond to proposals based on their relationship score and AI personality (already in ai.py).

4. Show a diplomacy inbox for incoming messages and proposals from AI civs.

5. Wire the extended diplomacy (diplomacy_extended.py): casus belli system, treaty types, war weariness. Show active treaties in the diplomacy panel.

6. Verify: declare war on an AI civ. Their units become hostile. Propose alliance with another. They accept if relations are high enough.
```

---

## Sprint 8: Economy Integration (1 session)

```
Unify the fragmented economy systems into a coherent resource flow.

1. Consolidate: each turn, calculate total gold income (from cities via tax_system.py), subtract expenses (unit maintenance via gold_management.py, building upkeep). Show net income.

2. Wire happiness_system.py into city yields: low happiness reduces production. Very low happiness triggers unrest (from stability_system.py).

3. Show trade route income (from external_trade_routes.py) in the economy panel. Trade routes between your cities and AI cities generate gold/food/science.

4. Wire market_simulation.py: resource prices fluctuate each turn. Show current market prices in the economy panel.

5. If gold goes negative, units start disbanding (most expensive first). Show a warning.

6. Verify: watch gold accumulate over turns. Build expensive units, see maintenance costs. Go negative, see units disband.
```

---

## Sprint 9: Dynasty + Events + Polish (1 session)

```
Wire the remaining systems and polish the experience.

1. Wire plots.py into the game loop: call process_plots() each turn. Show active plots in a panel. Let the player assign spies.

2. Wire dynasty events: when rulers age and die, succession happens. Show character info in the dynasty panel with traits and stats.

3. Wire faction_system.py effects: faction influence affects happiness, stability, and available policies. Show faction standings in the factions panel.

4. Add keyboard shortcuts: Enter = End Turn, Escape = deselect, Tab = cycle units.

5. Add sound effects for key events (combat, city founded, tech complete) using sound_effects.py.

6. Clean up: remove fix_*.py scripts, panels_new.py, and any dead code. Consolidate economy.py with the 7 economy sub-files.

7. Verify: play a full game for 50+ turns. All systems visible, AI active, cities growing, wars happening, techs researching.
```

---

## Sprint 10: Victory + Final Integration (1 session)

```
Make the game winnable and fully integrated.

1. Wire victory.py into the game loop: check victory conditions each turn. When a civ achieves victory, show the victory screen popup.

2. Add a "Score" display showing all civs ranked by points (military + science + culture + diplomacy + dynasty).

3. Make sure all 5 victory types are achievable: Domination (capture all capitals), Science (research all techs), Culture (max cultural output), Diplomacy (alliance with all), Dynasty (longest unbroken dynasty).

4. Add a "Game Over" state: after victory, show final stats and offer "New Game" or "Quit".

5. Final test: play a complete game from start to victory. All systems interact, AI competes, decisions matter.
```
