# CivKings Completion Plan — Final 12 Tasks

Complete the game from 65% to fully playable. Each task is one CynCo session.

## Critical Bug Fixes (Tasks 1-3)

### Task 1: Fix victory conditions
- Read game.py lines 980-1000 — there are duplicate _check_victory methods that return None
- Remove the duplicate, fix the remaining one to actually check victory conditions:
  - Domination: player owns 10+ cities
  - Science: player reached Modern era
  - Culture: player culture_points > 500
  - Religion: player founded religion AND 60%+ cities follow it
  - Dynasty: dynasty prestige > 1000
- Return a dict {winner: civ_name, type: "Domination"} or None

### Task 2: Wire victory check into process_turn and add victory screen
- In process_turn, after all other processing, call _check_victory()
- If it returns a result, set self.state.game_over = True, self.state.winner = result
- In game_screen.py, after process_turn, if game.state.game_over, show a victory popup
- Create pygame_app/popups/victory_popup.py with winner name, victory type, and "Return to Menu" button

### Task 3: Wire religion spread into process_turn
- Read religion.py or religion_manager.py to find the spread logic
- In process_turn, call the religion manager's per-turn processing
- Religion should spread from cities with holy sites to adjacent cities
- Log spread events to turn_events

## UI Completions (Tasks 4-8)

### Task 4: Government selection popup
- Create pygame_app/popups/government_popup.py
- Show all GOVERNMENT_TYPES with their bonuses
- Current government highlighted
- "Switch" button that calls game.change_government()
- Wire to G key in game_screen.py

### Task 5: Render culture borders on hex map
- Read pygame_app/map/hex_renderer.py render method
- After terrain rendering, draw colored borders around hexes owned by each civ
- Use game.culture_borders dict — color by owner (player=blue, AI=red/orange/etc)
- Draw as thin colored outlines on hex edges

### Task 6: Spy network display in diplomacy popup
- In diplomacy.py popup, show spy level for selected civ
- Display: "Spy Network: Level X/3" with intel revealed at each level
- Level 1: show city populations
- Level 2: show military strength
- Level 3: show "Sabotage" button

### Task 7: Trade route visualization
- In hex_renderer.py, draw dotted lines between cities that have active trade routes
- Read game.trade_routes for the city pairs
- Draw in gold color over the hex map

### Task 8: Wonder selection in production popup
- In production.py popup, add a "Wonders" section showing buildable wonders
- Check game.wonders_built to exclude already-built wonders
- Each wonder shows cost and bonus
- Building a wonder calls game.build_wonder()

## Gameplay Polish (Tasks 9-12)

### Task 9: Unit promotion choice popup
- When a unit gains enough XP for promotion, show a popup with 3 choices
- +1 Attack, +1 Defense, +1 Movement
- Wire to military.py _offer_promotion — instead of random, let player choose
- AI auto-picks the highest stat

### Task 10: End game statistics screen
- After victory/defeat, show a statistics popup
- Total turns played, cities founded, units trained, wars won, techs researched
- Track these stats in game.state during play

### Task 11: Balance pass
- Adjust costs: buildings, units, wonders
- Adjust yields: science per pop, culture per pop, faith generation
- Adjust AI: make it more aggressive with military, smarter with tech choices
- Ensure a game takes 200-400 turns to win

### Task 12: Full playtest — 100 turns with verification
- Run 100 turns programmatically
- Verify: no crashes, victory reachable, AI expands and fights
- Verify: all popups open without error (T/D/Y/R/P/G/H keys)
- Fix any remaining issues
