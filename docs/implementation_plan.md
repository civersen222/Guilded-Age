# Combat & Production System Overhaul

## Problem Statement

1. **Combat casualties not tracked** — `Casualty`/`CombatResult` classes exist in `combat.py` but are never used.
2. **Combat doesn't apply damage** — Power is calculated but no `deal_damage()` calls.
3. **Production is hardcoded** — All units cost exactly 100 regardless of `production_cost` from `UNIT_TYPES`.
4. **Production capacity is fixed** — Cities always have 100 capacity, no building/district bonuses.
5. **AI doesn't use production** — Creates units instantly without paying costs.
6. **No unit death handling** — Dead units are never removed from the game state.

## Implementation Status

### Phase 1: Fix Combat System ✅ COMPLETE
- [x] Wire `MilitaryManager.combat()` to use `CombatResult`
- [x] Apply `deal_damage()` to both attacker and defender
- [x] Record casualties in `CombatResult` when units die
- [x] Track `last_combat_result` on each Unit
- [x] Clean up dead units after combat

### Phase 2: Fix Production System ✅ COMPLETE
- [x] Add `production_capacity` to City (default 100, boosted by districts/buildings)
- [x] Look up `production_cost` from `UNIT_TYPES` instead of hardcoding 100
- [x] Calculate production progress as `production_points / item_cost`
- [x] Add `is_production_complete()` method
- [x] Add `get_production_details()` for UI display
- [x] Add `assign_production()` with tech/resource validation
- [x] Add `process_production()` for per-turn processing

### Phase 3: Fix Game Loop ✅ COMPLETE
- [x] Wire up player unit production from cities
- [x] Add gold maintenance deduction for units
- [x] Clean up dead units from `self.units` dict
- [x] Fix AI to use production queue instead of instant spawn

### Phase 4: UI Integration ✅ COMPLETE
- [x] Wire `ProductionPopup` to use real unit costs
- [x] Show affordability (gold cost for maintenance)
- [x] Show technology requirements (gray out unavailable units)
- [x] Update `ProductionQueuePanel` to show progress bar
- [x] Show production capacity and current progress

## Phase 4: UI Integration - Implementation Plan

### 4a. ProductionPopup (gui_popups.py)
- Use `city.get_production_cost(item)` for real costs
- Check `city.assign_production()` for tech/resource validation
- Gray out unavailable units with reason tooltip

### 4b. ProductionQueuePanel (gui_panels.py)
- Show progress bar: `city.production / city.get_production_cost(current_item)`
- Display capacity and current production points
- Allow queue management

## Files Modified

| File | Status |
|------|--------|
| `combat.py` | ✅ Fixed CombatResult, casualty recording |
| `military.py` | ✅ Wired to return CombatResult |
| `city.py` | ✅ Production cost/capacity, UnitProduction methods |
| `game.py` | ✅ Production queue, cleanup, gold maintenance, AI production |
| `gui_popups.py` | ✅ Real costs, tech/resource requirements, affordability |
| `gui_panels.py` | ✅ Progress bar, capacity display, real costs |

## Dependencies

- `combat.py` imports `Unit` from `military.py`
- `city.py` imports `UNIT_TYPES` from `game_data.py`
- `game.py` imports `CombatResult` from `combat.py`

## Testing Strategy

1. **Combat**: Create two units, trigger combat, verify `CombatResult` has correct casualties
2. **Production**: Build a Militia (cost 25) — should complete in 1 turn at 100 capacity
3. **Gold Maintenance**: Verify gold decreases each turn based on unit count
4. **Tech Requirements**: Verify Archer can't be built without Archery tech
5. **Dead Unit Cleanup**: Verify dead units are removed from `self.units`
6. **AI Production**: Verify AI builds units over multiple turns using production queue
