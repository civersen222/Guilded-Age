# Gilded Stage 4 — Enterprises / the Economy: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the dormant economy into a legible, agency-rich domain unified by one master meter — *Grip on the House* — with emergent commodity prices, priced share warfare, and Directors that matter.

**Architecture:** A pure read-model layer over machinery that largely already exists. `gilded/market.py` clears a four-commodity production chain (coal→steel→freight, +farm) to emergent prices each turn and threads them into the existing dividend loop. `gilded/grip.py` derives the controlling-stake-vs-predator meter from the ledger + loyalty that already exist. Levers are new/wired docket initiatives (one attention each). The Enterprises tab is a read-model client — no sim logic in the UI.

**Tech Stack:** Python 3, gilded package (`gilded/`), pygame UI (headless-testable via `SDL_VIDEODRIVER=dummy`), pytest. No new dependencies.

---

## Plan conventions (managing-engineer model)

This plan is executed by **CynCo**, which authors its own implementations. This document therefore specifies, per task:

1. **The failing test — full code.** The test is the *contract*. Copy it verbatim; do not invent your own assertions.
2. **The implementation — signatures + behavior, not source.** Exact function/dataclass signatures, the seams to touch, and the observable behavior the test pins. CynCo writes the body.
3. **Exact verify commands + expected result.**

**Standing rules for every task:**
- Determinism: NO `game.rng` (or any RNG) in `market.py` price clearing or in `grip.py`. (Stage 2/3 discipline.)
- Reuse over rebuild: wire existing verbs/functions; only add new sim where §7 of the spec names a genuine gap.
- Scoped suite must stay green: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q`.
- Commit after each task with the message shown. Frequent, small commits.

**Spec:** `docs/superpowers/specs/2026-07-24-gilded-stage4-enterprises-design.md`.

---

## Grounding: the seams this plan touches (already in the code)

- `gilded/enterprises.py`
  - `ENTERPRISE_TYPES = {"colliery":("coalfield","coal",30.0,400.0), "ironworks":("iron","steel",40.0,600.0), "mill":("timber","freight",25.0,300.0), "estate":("farmland",None,20.0,250.0), "rail_co":("harbor","freight",35.0,500.0), "bank":(None,None,50.0,800.0)}` = (needs-endowment, capacity-kind, base_gold, found_cost).
  - `Enterprise` dataclass: `eid, kind, name, house, province(pid), tier=1, extraction_dial=50.0, director_id="", ledger(char_id→pct), under_construction=0, target_tier=1`; `workforce()=tier*10`.
  - `output_gold(ent, province, director, tech_mod=1.0)` → base_gold × richness × tier × staffing × production_multiplier(dial) × director_mod × tech_mod. `director_mod = 1.0 + industry/40.0`. Returns 0 if `under_construction>0` or richness≤0. **`tech_mod` is currently always passed 1.0.**
  - `capacity_out(ent, province)` → `(kind, tier*richness)` — the SUPPLY seam currently discarded into `chassis.capacity`. **Estates return kind `None`** (no farm supply today — a gap this plan fills).
- `gilded/chassis.py` `end_turn()`: computes policy, sets `extraction_dial` per house, ticks construction, builds `self.capacity = {house:{kind:0.0}}`, accrues `capacity_out`, computes `coal_price = 1.0 + COAL_STRIKE_PRICE * striking`, calls `pay_dividends(realm, ents, provinces, mod)` where `mod` folds `coal_price` / `STRIKE_OUTPUT_MULT` / `policy.output_mod`, take→`house.treasury`; then society/directors/loyalty/takeovers (`for tk in list(self.takeovers): tk.advance(...)`). Constructor: `self.enterprises=[]`, `self.takeovers=[]`, `ents_of(house)`.
- `gilded/society/shares.py`: `pay_dividends(realm, enterprises, provinces, tech_mod=1.0)`→`(house_take, events)`; `transfer_shares(ent, from_id, to_id, pct)`→amt; `house_stake(enterprises, char_id)`=avg stake across enterprises; `seize_enterprises(...)`.
- `gilded/society/schemes.py`: `Takeover(buyer, buyer_house, target_house)`; `advance(realms, enterprises, rng)` buys `disloyal_shareholders` up to `TAKEOVER_TRANCHE=15.0` at `TAKEOVER_PRICE`, completes when `house_stake(target_ents, buyer.id) > TAKEOVER_THRESHOLD` → seize.
- `gilded/society/realm.py`: `tick_directors(realm, enterprises, rng)` auto-fills EMPTY `director_id` (player appointment persists), pays `DIRECTOR_SALARY_PCT=10.0`; `tick_loyalty(...)` rebuilds `ch.loyalty` 0–100; `disloyal_shareholders(realm, enterprises)` = non-ruler holders with `loyalty<DISLOYAL_LOYALTY(40)` OR `opinion≤DISLOYAL_OPINION(-20)`. Char has `.loyalty, .gold_reserve, .get_effective_stat(stat), .is_alive, .id, .name`.
- `gilded/society/labor.py`: `production_multiplier(dial)=0.75+0.005*dial`; `dividend_multiplier(dial)=0.6+0.008*dial`; `accident_chance(dial)=max(0,dial-40)²/18000`.
- `gilded/intel.py`: the read-model pattern to mirror — `@dataclass(frozen=True) IntelReport`; pure `report(game, viewer, target)`, `threat_rank(game)`; NO mutation.
- `gilded/docket.py`: `@dataclass RulingContext(game, house, executor, rng, scale=1.0)`; helpers `_ents_of(game, house)`, `_ents_by_house(game)`, `_house_provinces(game, house)`; handlers `def _init_X(ctx, **kw) -> List[str]`; `INITIATIVES` dict verb→(domain, handler); entry `initiative(game, house, verb, executor, **kw)`. Existing capital verbs: `found_enterprise`, `expand_enterprise`, `start_takeover`.
- `gilded/ui/broadsheet.py`: `TABS = ("Briefing","Gazette","Ledger","Letters","Docket","Policies","Atlas","Powers","House")`.
- `gilded/ui/app.py`: `_apply_action(state, action)` maps click-actions to game moves (e.g. `place_informant` → `initiative(g,h,"establish_informant",executor,target_house=target)`).
- `market_simulation.py` (repo root, DORMANT — ADAPT, don't import): `price = base × (demand/supply)`, bounded `max(0.1, min(100.0, price))`, `supply==0 → base*10.0`.

---

# LAYER 1 — Market core

**Wave goal:** `gilded/market.py` clears a four-commodity chain to emergent prices each turn, threads price + input cost + `tech_mod` into the dividend loop. No UI. Verified by tests + smoke.

Deliver a `Market` that lives on `game.market`, advances once per `end_turn`, exposes `price(commodity) -> float` (a multiplier around 1.0), `value(ent, game) -> float`, and `confidence() -> float`.

---

### Task 1.1: Commodity constants and a bounded, damped price cell

**Files:**
- Create: `gilded/market.py`
- Test: `gilded/tests/test_market.py`

- [ ] **Step 1: Write the failing test**

```python
# gilded/tests/test_market.py
import gilded.market as market


def test_commodities_are_the_four_chain_commodities():
    assert set(market.COMMODITIES) == {"coal", "steel", "freight", "farm"}


def test_fresh_market_prices_are_neutral():
    m = market.Market()
    for c in market.COMMODITIES:
        assert m.price(c) == 1.0


def test_clear_price_rises_when_demand_exceeds_supply():
    # price multiplier = clamp( base(=1.0) * demand/supply ), damped toward it.
    p = market.clear_price(prev=1.0, supply=10.0, demand=20.0)
    assert p > 1.0


def test_clear_price_falls_when_supply_exceeds_demand():
    p = market.clear_price(prev=1.0, supply=20.0, demand=10.0)
    assert p < 1.0


def test_clear_price_is_bounded_both_ends():
    hi = market.clear_price(prev=market.PRICE_MAX, supply=1.0, demand=1e9)
    lo = market.clear_price(prev=market.PRICE_MIN, supply=1e9, demand=0.0)
    assert market.PRICE_MIN <= lo <= hi <= market.PRICE_MAX


def test_clear_price_zero_supply_is_scarcity_capped_not_infinite():
    p = market.clear_price(prev=1.0, supply=0.0, demand=100.0)
    assert p == market.PRICE_MAX


def test_clear_price_damps_toward_target_not_instant():
    # A single turn moves partway to the raw demand/supply target, not all the way.
    raw = 2.0  # demand/supply = 20/10
    p = market.clear_price(prev=1.0, supply=10.0, demand=20.0)
    assert 1.0 < p < raw


def test_clear_price_is_deterministic():
    a = market.clear_price(prev=1.0, supply=13.0, demand=27.0)
    b = market.clear_price(prev=1.0, supply=13.0, demand=27.0)
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_market.py -q`
Expected: FAIL (`ModuleNotFoundError` / attributes undefined).

- [ ] **Step 3: Implement (behavior spec — CynCo authors the body)**

In `gilded/market.py` define:
- `COMMODITIES = ("coal", "steel", "freight", "farm")`.
- `PRICE_MIN` and `PRICE_MAX` bounding a price multiplier (recommend `0.25` and `4.0` — a strike or glut moves prices a few-fold, never detonates the economy; tune in Task 1.6).
- A damping factor `PRICE_DAMPING` in `(0, 1]` (recommend `0.5`) so a turn blends previous price with the cleared target.
- `clear_price(prev, supply, demand) -> float`: raw target `= demand / supply`; if `supply <= 0` the target is `PRICE_MAX` (scarcity cap — adapts `market_simulation.py`'s `supply==0` branch without going infinite); blend `prev` toward the target by `PRICE_DAMPING`; clamp to `[PRICE_MIN, PRICE_MAX]`. No RNG.
- `class Market`: holds a dict `prices: {commodity: float}` initialised to `1.0`; `price(commodity) -> float` reads it; a `_set(commodity, value)` internal or direct dict write.

Keep this task pure arithmetic — no `game` coupling yet.

- [ ] **Step 4: Run test to verify it passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_market.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add gilded/market.py gilded/tests/test_market.py
git commit -m "feat(gilded): market price cell — bounded, damped, deterministic clearing"
```

---

### Task 1.2: Supply from enterprise capacity (incl. farm from estates)

**Files:**
- Modify: `gilded/market.py`
- Test: `gilded/tests/test_market.py`

- [ ] **Step 1: Write the failing test**

```python
from gilded.enterprises import found_enterprise
import random


def _prov(pid, richness):
    class P:
        def __init__(self): self.pid = pid
        def endowment(self, kind): return richness
    return P()


def test_supply_sums_capacity_by_commodity(make_game):
    # make_game: a fixture/helper giving a game with provinces + a house.
    g = make_game()
    supply = market.supply_by_commodity(g)
    assert set(supply.keys()) == set(market.COMMODITIES)
    for v in supply.values():
        assert v >= 0.0


def test_estates_supply_farm_even_though_capacity_kind_is_none(make_game):
    g = make_game()
    # Found an estate; farm supply must rise (capacity_out returns kind=None for estates,
    # so market must source farm supply from estates explicitly).
    before = market.supply_by_commodity(g)["farm"]
    est = found_enterprise("estate", g.player_house, g.provinces[0], eid="e_farm", rng=random.Random(0))
    g.enterprises.append(est)
    after = market.supply_by_commodity(g)["farm"]
    assert after > before


def test_colliery_supplies_coal(make_game):
    g = make_game()
    before = market.supply_by_commodity(g)["coal"]
    col = found_enterprise("colliery", g.player_house, g.provinces[0], eid="e_coal", rng=random.Random(0))
    g.enterprises.append(col)
    after = market.supply_by_commodity(g)["coal"]
    assert after > before
```

> **Fixture note for the implementer:** `make_game` must build a minimal game with `.provinces`, `.enterprises`, `.player_house`, and the realm/house wiring `capacity_out`/`found_enterprise` need. Reuse the existing test scaffolding in `gilded/tests/` (look at `test_chassis.py` / `test_enterprises.py` `conftest.py` for how a game is stood up). If no shared fixture exists, add one to `gilded/tests/conftest.py` and DO NOT weaken these assertions.

- [ ] **Step 2: Run test to verify it fails**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_market.py -k supply -q`
Expected: FAIL (`supply_by_commodity` undefined).

- [ ] **Step 3: Implement (behavior spec)**

Add `supply_by_commodity(game) -> dict[str, float]`:
- Start every commodity at a small positive floor (avoid divide-by-zero; e.g. `SUPPLY_FLOOR = 1.0`).
- For each enterprise, call `capacity_out(ent, province)`; when it yields a real kind (`coal`/`steel`/`freight`), add the amount to that commodity.
- **Farm supply:** estates return kind `None` from `capacity_out`, so add estate supply explicitly — for each `ent.kind == "estate"`, add `ent.tier * richness` (mirror the `capacity_out` formula) to `farm`.
- Pure read of `game.enterprises` + provinces; no mutation, no RNG.

- [ ] **Step 4: Run test to verify it passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_market.py -k supply -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/market.py gilded/tests/test_market.py gilded/tests/conftest.py
git commit -m "feat(gilded): market supply from enterprise capacity, farm sourced from estates"
```

---

### Task 1.3: Demand over the chain (input demand, war, construction, population)

**Files:**
- Modify: `gilded/market.py`
- Test: `gilded/tests/test_market.py`

- [ ] **Step 1: Write the failing test**

```python
def test_demand_has_all_commodities(make_game):
    g = make_game()
    demand = market.demand_by_commodity(g)
    assert set(demand.keys()) == set(market.COMMODITIES)


def test_ironworks_creates_coal_demand(make_game):
    # ironworks consume coal to make steel -> coal demand rises with an ironworks present.
    g = make_game()
    before = market.demand_by_commodity(g)["coal"]
    iron = found_enterprise("ironworks", g.player_house, g.provinces[0], eid="e_iron", rng=random.Random(0))
    g.enterprises.append(iron)
    after = market.demand_by_commodity(g)["coal"]
    assert after > before


def test_construction_creates_steel_demand(make_game):
    # An in-flight expansion (under_construction>0) demands steel.
    g = make_game()
    iron = found_enterprise("ironworks", g.player_house, g.provinces[0], eid="e_iron2", rng=random.Random(0))
    g.enterprises.append(iron)
    base = market.demand_by_commodity(g)["steel"]
    iron.under_construction = 2
    iron.target_tier = 2
    raised = market.demand_by_commodity(g)["steel"]
    assert raised > base


def test_population_creates_farm_demand(make_game):
    g = make_game()
    demand = market.demand_by_commodity(g)
    assert demand["farm"] > 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_market.py -k demand -q`
Expected: FAIL (`demand_by_commodity` undefined).

- [ ] **Step 3: Implement (behavior spec)**

Add `demand_by_commodity(game) -> dict[str, float]` per the spec §4.1 chain, each starting at a small positive floor:
- **coal:** each ironworks demands coal proportional to its steel-making activity (e.g. `ent.tier` scaled by a `COAL_PER_STEEL` factor) + a small households/rail baseline.
- **steel:** war demand from active fronts (regiments/entrenchment — read `game.fronts` the way chassis does; if fronts absent, contribute 0) + construction demand from every enterprise with `under_construction > 0` + a rail baseline.
- **freight:** proportional to total enterprise activity (sum of `ent.tier` across enterprises) — "every enterprise's reach."
- **farm:** population/workforce need — sum of `ent.workforce()` across enterprises (proxy for staffed population) + a realm-population term if readily available.
- Pure read; no mutation; no RNG. Name the tunable factors as module constants (`COAL_PER_STEEL`, `FREIGHT_PER_TIER`, etc.) so Task 1.6 can balance them.

- [ ] **Step 4: Run test to verify it passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_market.py -k demand -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/market.py gilded/tests/test_market.py
git commit -m "feat(gilded): market demand over the coal-steel-freight-farm chain"
```

---

### Task 1.4: `Market.clear(game)`, `value(ent, game)`, `confidence()`

**Files:**
- Modify: `gilded/market.py`
- Test: `gilded/tests/test_market.py`

- [ ] **Step 1: Write the failing test**

```python
def test_clear_moves_prices_from_supply_and_demand(make_game):
    g = make_game()
    m = market.Market()
    # Stack coal demand (ironworks) with thin coal supply -> coal price should rise after clear.
    for i in range(3):
        g.enterprises.append(found_enterprise("ironworks", g.player_house, g.provinces[0],
                                              eid=f"e_iron{i}", rng=random.Random(i)))
    m.clear(g)
    assert m.price("coal") > 1.0


def test_overbuilding_a_sector_depresses_its_price(make_game):
    g = make_game()
    m = market.Market()
    for i in range(5):
        g.enterprises.append(found_enterprise("colliery", g.player_house, g.provinces[0],
                                              eid=f"e_col{i}", rng=random.Random(i)))
    m.clear(g)
    assert m.price("coal") < 1.0


def test_confidence_is_mean_of_prices(make_game):
    m = market.Market()
    m.prices = {"coal": 1.0, "steel": 2.0, "freight": 0.5, "farm": 1.5}
    assert m.confidence() == (1.0 + 2.0 + 0.5 + 1.5) / 4.0


def test_value_rises_with_the_producing_commoditys_price(make_game):
    g = make_game()
    m = market.Market()
    col = found_enterprise("colliery", g.player_house, g.provinces[0], eid="e_v", rng=random.Random(0))
    g.enterprises.append(col)
    m.prices["coal"] = 1.0
    low = m.value(col, g)
    m.prices["coal"] = 2.0
    high = m.value(col, g)
    assert high > low


def test_clear_is_deterministic(make_game):
    g1 = make_game(); g2 = make_game()
    m1 = market.Market(); m2 = market.Market()
    m1.clear(g1); m2.clear(g2)
    assert m1.prices == m2.prices
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_market.py -k "clear or confidence or value" -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

- `Market.clear(game)`: compute `supply_by_commodity(game)` and `demand_by_commodity(game)`; for each commodity `self.prices[c] = clear_price(self.prices[c], supply[c], demand[c])`. No RNG. Idempotent given identical game state.
- `Market.confidence() -> float`: mean of `self.prices.values()`.
- `Market.value(ent, game) -> float`: expected annual dividend × a `PE_MULTIPLE` constant. Expected dividend = the enterprise's `output_gold(...)` (or a cheap proxy: `base_gold * tier * this_commodity_price`) × `dividend_multiplier(ent.extraction_dial)`. The producing commodity's price must be a factor so a boom raises value and a bust lowers it (pins `test_value_rises_...`). Banks (no commodity) ride `confidence()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_market.py -q`
Expected: PASS (all market tests).

- [ ] **Step 5: Commit**

```bash
git add gilded/market.py gilded/tests/test_market.py
git commit -m "feat(gilded): Market.clear + value + confidence over the chain"
```

---

### Task 1.5: Thread the market into the chassis dividend loop (price, input cost, tech_mod)

**Files:**
- Modify: `gilded/chassis.py` (constructor: add `self.market = Market()`; `end_turn` dividend section)
- Modify: `gilded/enterprises.py` (activate `tech_mod`; input-cost accounting)
- Test: `gilded/tests/test_chassis.py`

- [ ] **Step 1: Write the failing test**

```python
# add to gilded/tests/test_chassis.py
def test_market_advances_each_turn(make_chassis_game):
    ch = make_chassis_game()
    assert hasattr(ch, "market")
    # heavy coal demand -> after a turn coal price departs from 1.0
    seed_ironworks(ch, n=3)      # helper: append 3 ironworks to ch.enterprises
    ch.end_turn()
    assert ch.market.price("coal") != 1.0


def test_commodity_price_multiplies_producer_dividends(make_chassis_game):
    ch = make_chassis_game()
    col = seed_colliery(ch)      # helper: one colliery owned by player house
    ch.market.prices["coal"] = 2.0
    high_take = run_one_dividend_turn(ch)   # helper returns house treasury delta
    ch2 = make_chassis_game()
    seed_colliery(ch2)
    ch2.market.prices["coal"] = 0.5
    low_take = run_one_dividend_turn(ch2)
    assert high_take > low_take


def test_ironworks_pays_a_coal_input_cost(make_chassis_game):
    # With coal expensive, an ironworks nets less than the same ironworks with cheap coal.
    ch_dear = make_chassis_game(); iron = seed_ironworks(ch_dear, n=1)
    ch_dear.market.prices["coal"] = 3.0; ch_dear.market.prices["steel"] = 1.0
    dear = run_one_dividend_turn(ch_dear)
    ch_cheap = make_chassis_game(); seed_ironworks(ch_cheap, n=1)
    ch_cheap.market.prices["coal"] = 0.5; ch_cheap.market.prices["steel"] = 1.0
    cheap = run_one_dividend_turn(ch_cheap)
    assert cheap > dear


def test_tech_mod_is_active_not_pinned_to_one(make_chassis_game):
    from gilded.enterprises import output_gold
    # A developed province yields more than an undeveloped one, all else equal.
    ch = make_chassis_game()
    col = seed_colliery(ch)
    prov = province_of(ch, col)
    prov.development = 0
    base = output_gold(col, prov, director=None, tech_mod=ch.tech_mod_for(prov))
    prov.development = 50
    developed = output_gold(col, prov, director=None, tech_mod=ch.tech_mod_for(prov))
    assert developed > base
```

> **Implementer note:** `seed_*`, `run_one_dividend_turn`, `province_of` are helpers you add to the test module/conftest, reusing the existing chassis test scaffolding. Keep the *assertions* exactly as written — they encode the spec §4.3 acceptance. If the existing chassis test file already has a game-builder fixture, build the helpers on top of it.

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_chassis.py -k "market or input or tech_mod" -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

- Chassis constructor: `self.market = Market()`.
- `end_turn` dividend section (the existing block around the `coal_price`/`capacity` code): call `self.market.clear(self)` **before** paying dividends. When paying each enterprise, fold the producing commodity's `self.market.price(kind)` into the output multiplier already assembled there (alongside strike/`policy.output_mod`). Preserve the existing `COAL_STRIKE_PRICE` behavior — the strike now feeds the market's coal supply/price rather than being a lone special case (keep the current test green; generalize, don't delete).
- **Input cost:** for consuming enterprises (ironworks consume coal; rail cos consume steel), deduct an input cost = `input_units * market.price(input_commodity)` from that enterprise's gold before the ledger split. Add a helper in `enterprises.py`, e.g. `input_cost(ent, market) -> float` (0 for non-consumers), and apply it in the dividend loop so the ledger/house-take reflects the squeezed margin.
- **tech_mod:** add `Chassis.tech_mod_for(province) -> float` deriving a >1.0 multiplier from `province.development` (e.g. `1.0 + development/SOME_SCALE`), and pass it into `output_gold`/`pay_dividends` instead of the hardcoded `1.0`. This is the §4.3 activation of the pinned hook.
- Determinism preserved: `market.clear` is RNG-free; the rest of the loop is unchanged in its RNG use.

- [ ] **Step 4: Run test to verify it passes**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_chassis.py -q`
Expected: PASS (new + existing chassis tests).

- [ ] **Step 5: Commit**

```bash
git add gilded/chassis.py gilded/enterprises.py gilded/tests/test_chassis.py
git commit -m "feat(gilded): thread market price + input cost + tech_mod into dividends"
```

---

### Task 1.6: L1 soak — a strike ripples, a glut deflates, prices stay bounded

**Files:**
- Test: `gilded/tests/test_soak.py` (extend) or `gilded/tests/test_market_soak.py` (new)

- [ ] **Step 1: Write the failing test**

```python
def test_coal_strike_ripples_across_the_chain(make_chassis_game):
    ch = make_chassis_game()
    seed_colliery(ch); seed_ironworks(ch, n=1)     # a coal->steel chain exists
    ch.end_turn()
    calm_coal = ch.market.price("coal")
    calm_steel_take = last_ironworks_take(ch)      # helper: this-turn ironworks house-take
    trigger_coal_strike(ch)                        # helper: set the striking flag chassis reads
    ch.end_turn()
    assert ch.market.price("coal") > calm_coal          # supply down -> coal price up
    assert last_ironworks_take(ch) < calm_steel_take    # input cost up -> ironworks squeezed


def test_prices_never_leave_bounds_over_a_century(make_chassis_game):
    ch = make_chassis_game()
    seed_mixed_portfolio(ch)   # helper: a few of each enterprise across houses
    for _ in range(60):
        ch.end_turn()
        for c in market.COMMODITIES:
            assert market.PRICE_MIN <= ch.market.price(c) <= market.PRICE_MAX


def test_overbuilding_deflates_own_dividends_over_time(make_chassis_game):
    ch = make_chassis_game()
    seed_colliery(ch)
    ch.end_turn(); base = ch.market.price("coal")
    for i in range(6):
        seed_colliery(ch)      # flood coal supply
    for _ in range(3):
        ch.end_turn()
    assert ch.market.price("coal") < base
```

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/ -k soak -q`
Expected: FAIL (before threading/tuning is complete) or reveals oscillation.

- [ ] **Step 3: Implement (behavior spec)**

No new API. Tune the constants from Tasks 1.1/1.3 (`PRICE_DAMPING`, `PRICE_MIN/MAX`, the `*_PER_*` demand factors) so: a strike visibly raises coal and squeezes ironworks; oversupply deflates; and prices never oscillate outside bounds over 60 turns (spec §11 balance/determinism). Damping (blend toward target) is the primary anti-oscillation tool — raise it if prices ring, lower it if they respond too slowly.

- [ ] **Step 4: Run test to verify it passes**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/ -k soak -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/tests/
git commit -m "test(gilded): L1 market soak — strike ripple, glut deflation, bounded over a century"
```

- [ ] **Step 6: Layer-1 gate**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q`
Expected: full scoped suite GREEN. Do not proceed to L2 until green.

---

# LAYER 2 — Grip read-model

**Wave goal:** `gilded/grip.py`, a pure read-model (mirrors `intel.py`) deriving the master meter from ledger + loyalty + market. No mutation, no `game.rng`.

---

### Task 2.1: `EnterpriseLine` + `GripReport` dataclasses and per-enterprise breakdown

**Files:**
- Create: `gilded/grip.py`
- Test: `gilded/tests/test_grip.py`

- [ ] **Step 1: Write the failing test**

```python
# gilded/tests/test_grip.py
import gilded.grip as grip


def test_report_is_frozen_and_pure(make_game):
    g = make_game_with_enterprises()   # helper: player house owns a few enterprises with a ledger
    before = snapshot(g)               # helper: cheap structural snapshot
    r = grip.report(g, g.player_house)
    assert isinstance(r, grip.GripReport)
    assert snapshot(g) == before       # read-model must not mutate game state


def test_breakdown_has_a_line_per_house_enterprise(make_game_with_enterprises):
    g = make_game_with_enterprises()
    r = grip.report(g, g.player_house)
    house_eids = {e.eid for e in g.enterprises if e.house == g.player_house}
    assert {ln.eid for ln in r.enterprises} == house_eids


def test_enterprise_line_fields(make_game_with_enterprises):
    g = make_game_with_enterprises()
    ln = grip.report(g, g.player_house).enterprises[0]
    assert hasattr(ln, "eid") and hasattr(ln, "name") and hasattr(ln, "sector")
    assert hasattr(ln, "tier") and hasattr(ln, "dividend")
    assert hasattr(ln, "director")        # None or a small record with id/name/industry/disloyal
    assert hasattr(ln, "your_stake")      # ruler's stake pct in this enterprise
    assert hasattr(ln, "top_outside")     # (holder_id, pct) or None — largest holder not in loyal bloc
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_grip.py -k "line or breakdown or pure" -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

- `@dataclass(frozen=True) EnterpriseLine`: `eid, name, sector, tier, dividend, director, your_stake, top_outside`. `sector` = the enterprise's capacity kind / commodity (coal/steel/freight/farm; banks → `"bank"`). `director` = `None` or a frozen record `(id, name, industry, disloyal: bool)` where `disloyal` uses the exact `disloyal_shareholders`/loyalty test from `realm.py`. `dividend` = this-turn dividend for the enterprise (reuse the market-aware output; if a stored last-dividend isn't available, compute expected via `market.value`/`output_gold`). `your_stake` = ruler's ledger pct. `top_outside` = largest single holder NOT in the loyal bloc.
- `@dataclass(frozen=True) GripReport`: fields filled in Tasks 2.2–2.3 plus `enterprises: tuple[EnterpriseLine, ...]`.
- `report(game, house) -> GripReport`: pure; builds the per-enterprise lines. Mirror `intel.report`'s style. No mutation, no RNG.

- [ ] **Step 4: Run test to verify it passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_grip.py -k "line or breakdown or pure" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/grip.py gilded/tests/test_grip.py
git commit -m "feat(gilded): grip read-model — per-enterprise breakdown"
```

---

### Task 2.2: Loyal bloc + controlling stake + top predator

**Files:**
- Modify: `gilded/grip.py`
- Test: `gilded/tests/test_grip.py`

- [ ] **Step 1: Write the failing test**

```python
def test_loyal_bloc_excludes_disloyal_holders(make_game_with_enterprises):
    from gilded.society.realm import disloyal_shareholders
    g = make_game_with_enterprises()
    r = grip.report(g, g.player_house)
    realm = realm_of(g, g.player_house)
    disloyal_ids = {c.id for c in disloyal_shareholders(realm, g.enterprises)}
    assert disloyal_ids.isdisjoint(set(r.loyal_bloc))   # loyal bloc == not disloyal


def test_ruler_is_always_in_the_loyal_bloc(make_game_with_enterprises):
    g = make_game_with_enterprises()
    r = grip.report(g, g.player_house)
    assert ruler_id(g, g.player_house) in r.loyal_bloc


def test_controlling_stake_is_loyal_bloc_average_holding(make_game_with_enterprises):
    g = make_game_with_enterprises()
    r = grip.report(g, g.player_house)
    assert 0.0 <= r.controlling_stake <= 100.0


def test_flipping_a_kin_disloyal_lowers_controlling_stake(make_game_with_enterprises):
    g = make_game_with_enterprises()
    high = grip.report(g, g.player_house).controlling_stake
    make_a_shareholder_disloyal(g, g.player_house)   # helper: drop one kin's loyalty below 40
    low = grip.report(g, g.player_house).controlling_stake
    assert low < high


def test_top_predator_is_largest_outside_holder(make_game_with_enterprises):
    g = make_game_with_enterprises()
    r = grip.report(g, g.player_house)
    if r.top_predator is not None:
        assert r.top_predator.stake >= 0.0
        assert r.top_predator.holder_id not in r.loyal_bloc
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_grip.py -k "bloc or controlling or predator or flipping" -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

- `loyal_bloc(game, house) -> tuple[str, ...]`: ruler + kin who are NOT in `disloyal_shareholders(realm, enterprises)`. Same test the `Takeover` engine means by "not for sale" (spec §3). Ruler always included.
- `controlling_stake`: per enterprise, sum the ledger pct held by loyal-bloc members; average across the house's enterprises (the `house_stake` yardstick generalized to the bloc). Range 0–100.
- `top_predator`: the single outside character (not in loyal bloc, not the house) with the largest average stake across the house's enterprises; expose as a frozen record `(holder_id, name, stake)` reported against `TAKEOVER_THRESHOLD` (import from `schemes.py`). `None` if no outside holder.
- Add `loyal_bloc`, `controlling_stake`, `top_predator`, `threshold` to `GripReport`.

- [ ] **Step 4: Run test to verify it passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_grip.py -k "bloc or controlling or predator or flipping" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/grip.py gilded/tests/test_grip.py
git commit -m "feat(gilded): grip — loyal bloc, controlling stake, top predator"
```

---

### Task 2.3: Bands (IRON_GRIP → CONTESTED → IMPERILED → SEIZED)

**Files:**
- Modify: `gilded/grip.py`
- Test: `gilded/tests/test_grip.py`

- [ ] **Step 1: Write the failing test**

```python
def test_bands_are_ordered(make_game_with_enterprises):
    assert grip.BANDS == ("IRON_GRIP", "CONTESTED", "IMPERILED", "SEIZED")


def test_dominant_control_reads_iron_grip(make_game_with_enterprises):
    g = make_game_with_enterprises()
    set_player_control(g, controlling=90.0, predator=5.0)   # helper adjusts ledgers/loyalty
    assert grip.report(g, g.player_house).band == "IRON_GRIP"


def test_predator_near_threshold_reads_imperiled(make_game_with_enterprises):
    g = make_game_with_enterprises()
    from gilded.society.schemes import TAKEOVER_THRESHOLD
    set_player_control(g, controlling=51.0, predator=TAKEOVER_THRESHOLD - 2.0)
    assert grip.report(g, g.player_house).band == "IMPERILED"


def test_completed_takeover_reads_seized(make_game_with_enterprises):
    g = make_game_with_enterprises()
    mark_house_seized(g, g.player_house)   # helper: a completed Takeover against the house
    assert grip.report(g, g.player_house).band == "SEIZED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_grip.py -k band -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

- `BANDS = ("IRON_GRIP", "CONTESTED", "IMPERILED", "SEIZED")`.
- Band derivation from the gap between loyal `controlling_stake` and the top predator's stake relative to `TAKEOVER_THRESHOLD`: a completed `Takeover` against the house → `SEIZED`; predator within a small margin of the threshold → `IMPERILED`; predator materially present but far → `CONTESTED`; predator negligible / control commanding → `IRON_GRIP`. Pick concrete cutoffs as module constants; keep them the ONLY place bands are decided.
- Add `band` to `GripReport`.

- [ ] **Step 4: Run test to verify it passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_grip.py -q`
Expected: PASS (all grip tests).

- [ ] **Step 5: Commit + Layer-2 gate**

```bash
git add gilded/grip.py gilded/tests/test_grip.py
git commit -m "feat(gilded): grip bands — iron grip to seized"
```

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q`
Expected: full scoped suite GREEN before L3.

---

# LAYER 3 — Levers

**Wave goal:** priced buy/sell + valuation; `appoint_director` + candidate pool + disloyal-Director skim/accident; existing found/expand/start_takeover confirmed callable as player initiatives. Each lever = one attention.

---

### Task 3.1: Priced share transfer wrapper in `shares.py`

**Files:**
- Modify: `gilded/society/shares.py`
- Test: `gilded/tests/test_shares.py` (or existing shares test module)

- [ ] **Step 1: Write the failing test**

```python
def test_priced_transfer_moves_gold_and_shares(make_ledger_game):
    from gilded.society.shares import priced_transfer
    g = make_ledger_game()
    ent = g.enterprises[0]
    buyer = char(g, "buyer"); seller = char(g, "seller")   # buyer has gold, seller holds pct
    seller_pct_before = ent.ledger.get(seller.id, 0.0)
    buyer_gold_before = buyer.gold_reserve
    price = priced_transfer(ent, seller.id, buyer.id, pct=5.0, market=g.market, game=g)
    assert ent.ledger.get(buyer.id, 0.0) > 0.0
    assert ent.ledger.get(seller.id, 0.0) == seller_pct_before - 5.0
    assert buyer.gold_reserve == buyer_gold_before - price
    assert price > 0.0


def test_priced_transfer_price_tracks_valuation(make_ledger_game):
    from gilded.society.shares import priced_transfer
    g = make_ledger_game(); ent = g.enterprises[0]
    g.market.prices[sector_of(ent)] = 2.0
    dear = priced_transfer(ent, "seller", "buyer", pct=1.0, market=g.market, game=g, dry_run=True)
    g.market.prices[sector_of(ent)] = 0.5
    cheap = priced_transfer(ent, "seller", "buyer", pct=1.0, market=g.market, game=g, dry_run=True)
    assert dear > cheap


def test_priced_transfer_blocks_when_buyer_cannot_pay(make_ledger_game):
    from gilded.society.shares import priced_transfer
    g = make_ledger_game(); ent = g.enterprises[0]
    broke = char(g, "buyer"); broke.gold_reserve = 0.0
    price = priced_transfer(ent, "seller", broke.id, pct=5.0, market=g.market, game=g)
    assert price == 0.0                       # no gold -> no move
    assert ent.ledger.get(broke.id, 0.0) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_shares.py -k priced -q`
Expected: FAIL (`priced_transfer` undefined).

- [ ] **Step 3: Implement (behavior spec)**

`priced_transfer(ent, from_id, to_id, pct, market, game, dry_run=False) -> float`:
- price = `market.value(ent, game) * pct / 100.0`.
- If `dry_run`: return price without moving anything.
- If the buyer's `gold_reserve < price`: no-op, return `0.0` (affordability gate).
- Otherwise move gold buyer→seller, then call the existing `transfer_shares(ent, from_id, to_id, pct)`; return the price paid.
- A small "generous buyer" opinion bump on the seller (mirror the `Takeover`) — apply through the existing opinion mechanism.

- [ ] **Step 4: Run test to verify it passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_shares.py -k priced -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/society/shares.py gilded/tests/test_shares.py
git commit -m "feat(gilded): priced_transfer — market-valued share trade over transfer_shares"
```

---

### Task 3.2: `buy_shares` / `sell_shares` initiatives

**Files:**
- Modify: `gilded/docket.py`
- Test: `gilded/tests/test_docket.py`

- [ ] **Step 1: Write the failing test**

```python
def test_buy_shares_initiative_buys_back_a_named_kin(make_docket_game):
    from gilded.docket import initiative, INITIATIVES
    assert INITIATIVES["buy_shares"][0] == "capital"      # domain
    g = make_docket_game()
    kin = disloyal_kin(g, g.player_house)                 # helper: a disloyal holder
    ent = g.enterprises[0]
    ruler_before = ent.ledger.get(ruler_id(g, g.player_house), 0.0)
    initiative(g, g.player_house, "buy_shares",
               ruler_char(g, g.player_house), eid=ent.eid, seller_id=kin.id, pct=5.0)
    assert ent.ledger.get(ruler_id(g, g.player_house), 0.0) > ruler_before


def test_sell_shares_initiative_raises_treasury_lowers_control(make_docket_game):
    from gilded.docket import initiative
    g = make_docket_game(); ent = g.enterprises[0]
    ruler = ruler_char(g, g.player_house)
    stake_before = ent.ledger.get(ruler.id, 0.0)
    gold_before = ruler.gold_reserve
    initiative(g, g.player_house, "sell_shares", ruler, eid=ent.eid, buyer_id=some_rival(g).id, pct=5.0)
    assert ent.ledger.get(ruler.id, 0.0) < stake_before
    assert ruler.gold_reserve > gold_before


def test_buy_and_sell_each_cost_one_attention(make_docket_game):
    from gilded.docket import INITIATIVES
    # domain tuple present + single-attention like every other initiative (no special multiplier)
    assert "buy_shares" in INITIATIVES and "sell_shares" in INITIATIVES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_docket.py -k shares -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

- `_init_buy_shares(ctx, eid=None, seller_id=None, pct=0.0, **kw) -> List[str]`: locate the enterprise by `eid` in `ctx.game.enterprises`; buyer = `ctx.executor` (ruler); call `priced_transfer(ent, seller_id, ctx.executor.id, pct, ctx.game.market, ctx.game)`; return a human-readable event line ("bought back N% of X from <kin> for <gold>"). No-op event if the transfer returns 0.
- `_init_sell_shares(ctx, eid=None, buyer_id=None, pct=0.0, **kw) -> List[str]`: seller = `ctx.executor`; `priced_transfer(ent, ctx.executor.id, buyer_id, pct, ...)`; event line.
- Register both in `INITIATIVES` under domain `"capital"`, following the existing entry shape. One attention each (no multiplier — spec §5, mandate 5).

- [ ] **Step 4: Run test to verify it passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_docket.py -k shares -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/docket.py gilded/tests/test_docket.py
git commit -m "feat(gilded): buy_shares / sell_shares initiatives (capital, one attention)"
```

---

### Task 3.3: `appoint_director` initiative + candidate pool

**Files:**
- Modify: `gilded/docket.py`
- Test: `gilded/tests/test_docket.py`

- [ ] **Step 1: Write the failing test**

```python
def test_director_candidates_ranked_by_industry(make_docket_game):
    from gilded.docket import director_candidates
    g = make_docket_game(); ent = g.enterprises[0]
    cands = director_candidates(g, g.player_house, ent.eid)
    inds = [c.get_effective_stat("industry") for c in cands]
    assert inds == sorted(inds, reverse=True)          # best industry first
    ruler = ruler_id(g, g.player_house)
    assert all(c.id != ruler for c in cands)           # ruler is not a candidate


def test_appoint_director_sets_director_id_and_persists(make_docket_game):
    from gilded.docket import initiative, director_candidates
    g = make_docket_game(); ent = g.enterprises[0]
    pick = director_candidates(g, g.player_house, ent.eid)[0]
    initiative(g, g.player_house, "appoint_director",
               ruler_char(g, g.player_house), eid=ent.eid, char_id=pick.id)
    assert ent.director_id == pick.id
    tick_directors(realm_of(g, g.player_house), g.enterprises, random.Random(0))
    assert ent.director_id == pick.id                  # auto-assign only fills EMPTY slots -> persists


def test_appoint_director_is_capital_domain(make_docket_game):
    from gilded.docket import INITIATIVES
    assert INITIATIVES["appoint_director"][0] == "capital"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_docket.py -k director -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

- `director_candidates(game, house, eid) -> list[Character]`: living house characters, adult, not the ruler, ranked by `get_effective_stat("industry")` descending. (Mirror the eligibility `tick_directors` uses.)
- `_init_appoint_director(ctx, eid=None, char_id=None, **kw) -> List[str]`: set `ent.director_id = char_id` on the matching enterprise; event line. Because `tick_directors` only fills EMPTY `director_id`, the appointment persists (grounding note). Sacking = a set to `""` (auto-refill next turn) — reuse this handler with `char_id=""` or leave sacking to the existing prosecution path; do not add a second verb.
- Register `appoint_director` in `INITIATIVES` under `"capital"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_docket.py -k director -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/docket.py gilded/tests/test_docket.py
git commit -m "feat(gilded): appoint_director initiative + industry-ranked candidate pool"
```

---

### Task 3.4: Disloyal Directors skim dividends + raise accident odds

**Files:**
- Modify: `gilded/enterprises.py` (skim + accident hooks)
- Modify: `gilded/chassis.py` (apply skim in the dividend loop)
- Test: `gilded/tests/test_enterprises.py`, `gilded/tests/test_chassis.py`

- [ ] **Step 1: Write the failing test**

```python
# test_enterprises.py
def test_disloyal_director_skims_a_portion_of_output():
    from gilded.enterprises import director_skim
    # skim > 0 when director is disloyal, 0 when loyal or absent
    assert director_skim(output=1000.0, director=None) == 0.0
    assert director_skim(output=1000.0, director=loyal_director()) == 0.0
    skimmed = director_skim(output=1000.0, director=disloyal_director())
    assert 0.0 < skimmed < 1000.0


def test_disloyal_director_worsens_accident_odds():
    from gilded.enterprises import accident_chance_with_director, accident_chance
    base = accident_chance(dial=60.0)
    worse = accident_chance_with_director(dial=60.0, director=disloyal_director())
    same = accident_chance_with_director(dial=60.0, director=loyal_director())
    assert worse > base
    assert same == base


# test_chassis.py
def test_disloyal_director_diverts_gold_from_treasury(make_chassis_game):
    ch = make_chassis_game()
    ent = seed_colliery(ch)
    make_director_disloyal(ch, ent)          # helper: assign a director with loyalty < 40
    treasury_take = run_one_dividend_turn(ch)
    ch2 = make_chassis_game()
    ent2 = seed_colliery(ch2)
    make_director_loyal(ch2, ent2)
    loyal_take = run_one_dividend_turn(ch2)
    assert treasury_take < loyal_take        # skim diverts house-take to the director's purse
    assert director_of(ch, ent).gold_reserve > 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/ -k "skim or accident or divert" -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

- `director_skim(output, director) -> float`: `0.0` if `director is None` or the director is loyal; otherwise a bounded fraction (e.g. `SKIM_PCT`) of `output`. Disloyalty = the same loyalty/opinion test used by `disloyal_shareholders` / the loyalty line (`DISLOYAL_LOYALTY=40`).
- `accident_chance_with_director(dial, director) -> float`: existing `accident_chance(dial)` × a `>1` factor when the director is disloyal, else unchanged. Keep `accident_chance` itself untouched.
- Chassis dividend loop: after computing an enterprise's output, subtract `director_skim(output, director)` from the house-take and credit it to the director's `gold_reserve` (a resentful Director enriches himself). Apply `accident_chance_with_director` where the loop currently rolls accidents.
- These make Directors a live tension (spec §5.3). Determinism unchanged (skim is arithmetic; the accident roll already uses the existing RNG).

- [ ] **Step 4: Run test to verify it passes**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/ -k "skim or accident or divert" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/enterprises.py gilded/chassis.py gilded/tests/
git commit -m "feat(gilded): disloyal Directors skim dividends and raise accident odds"
```

---

### Task 3.5: Confirm found / expand / start_takeover are callable as player initiatives + valuation on takeover

**Files:**
- Modify: `gilded/docket.py` (only if `start_takeover` needs `market.value` pricing threaded)
- Test: `gilded/tests/test_docket.py`

- [ ] **Step 1: Write the failing test**

```python
def test_found_expand_takeover_are_registered_capital_initiatives():
    from gilded.docket import INITIATIVES
    for verb in ("found_enterprise", "expand_enterprise", "start_takeover"):
        assert verb in INITIATIVES
        assert INITIATIVES[verb][0] == "capital"


def test_player_can_found_via_initiative(make_docket_game):
    from gilded.docket import initiative
    g = make_docket_game()
    n_before = len(g.enterprises)
    initiative(g, g.player_house, "found_enterprise",
               ruler_char(g, g.player_house), kind="colliery", province_pid=g.provinces[0].pid)
    assert len(g.enterprises) == n_before + 1


def test_player_can_launch_takeover_via_initiative(make_docket_game):
    from gilded.docket import initiative
    g = make_docket_game()
    n_before = len(g.takeovers)
    initiative(g, g.player_house, "start_takeover",
               ruler_char(g, g.player_house), target_house=some_rival_house(g))
    assert len(g.takeovers) == n_before + 1
```

- [ ] **Step 2: Run test to verify it fails / passes**

Run: `SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_docket.py -k "found_expand or found via or launch_takeover" -q`
Expected: mostly PASS already (these verbs exist) — this task is a *confirmation contract* plus wiring `market.value` into the takeover price if it isn't. If any assertion fails, fix the wiring; do not weaken the test.

- [ ] **Step 3: Implement (behavior spec)**

If the tests pass unchanged, add only the `market.value`-priced takeover cost per spec §5.4 (the `Takeover`/`start_takeover` cost should reference `market.value` so a boom raises it). If the verbs are already fully callable and priced, this task is test-only (locks the contract for L4's UI wiring).

- [ ] **Step 4: Run + Layer-3 gate**

```bash
git add gilded/docket.py gilded/tests/test_docket.py
git commit -m "test(gilded): lock found/expand/takeover as player initiatives; price takeover via market"
```

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q`
Expected: full scoped suite GREEN before L4.

---

# LAYER 4 — The Enterprises panel

**Wave goal:** an "Enterprises" tab that renders the Grip banner (collapsed) ↔ full ledger (expanded), and turns every click into one of the L3 initiatives. UI is a read-model client — no sim logic.

---

### Task 4.1: Register the "Enterprises" tab + collapsed Grip banner render

**Files:**
- Modify: `gilded/ui/broadsheet.py`
- Test: `gilded/tests/test_broadsheet.py` (the existing UI test module)

- [ ] **Step 1: Write the failing test**

```python
def test_enterprises_tab_registered():
    from gilded.ui.broadsheet import TABS
    assert "Enterprises" in TABS


def test_enterprises_banner_shows_grip_band_and_predator(render_broadsheet):
    # render_broadsheet: existing helper that renders a tab to text/lines headlessly
    lines = render_broadsheet(tab="Enterprises", expanded=False)
    text = "\n".join(lines)
    assert "GRIP" in text.upper()
    assert any(band in text for band in ("IRON GRIP", "CONTESTED", "IMPERILED", "SEIZED"))
    # predator advance + market ticker present on the banner
    assert "coal" in text and "steel" in text and "freight" in text


def test_banner_is_default_collapsed_view(render_broadsheet):
    lines = render_broadsheet(tab="Enterprises")     # default
    assert any("GRIP" in l.upper() for l in lines)
```

> **Implementer note:** Follow the existing tab render tests (`Powers`/`Policies`) for how `render_broadsheet` and headless rendering work in this suite. Reuse that harness; match its assertion style.

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_broadsheet.py -k "enterprises or banner" -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

- Add `"Enterprises"` to `TABS` (place after `Policies`, mirroring the spec's panel ordering).
- Render the collapsed banner from `grip.report(game, house)` + `game.market`: band label, controlling stake, top predator (name, stake, `TAKEOVER_THRESHOLD`, a "courting your kin" note when a kin slipped), and the market ticker `coal ▲/▼  steel …  freight …  farm …` from `market.price(...)` deltas. Pure render off the read-models — no sim calls that mutate.

- [ ] **Step 4: Run test to verify it passes**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_broadsheet.py -k "enterprises or banner" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/ui/broadsheet.py gilded/tests/test_broadsheet.py
git commit -m "feat(gilded): Enterprises tab + collapsed Grip banner"
```

---

### Task 4.2: Expanded ledger table with per-enterprise rows + action affordances

**Files:**
- Modify: `gilded/ui/broadsheet.py`
- Test: `gilded/tests/test_broadsheet.py`

- [ ] **Step 1: Write the failing test**

```python
def test_expanded_ledger_lists_every_house_enterprise(render_broadsheet, make_ui_game):
    g = make_ui_game()
    lines = render_broadsheet(tab="Enterprises", expanded=True, game=g)
    text = "\n".join(lines)
    for e in [e for e in g.enterprises if e.house == g.player_house]:
        assert e.name in text


def test_expanded_rows_show_dividend_director_and_stakes(render_broadsheet, make_ui_game):
    g = make_ui_game()
    text = "\n".join(render_broadsheet(tab="Enterprises", expanded=True, game=g))
    assert "Dir" in text or "Director" in text
    assert "%" in text                       # stakes shown as percentages


def test_disloyal_director_shows_skim_flag(render_broadsheet, make_ui_game):
    g = make_ui_game_with_disloyal_director()
    text = "\n".join(render_broadsheet(tab="Enterprises", expanded=True, game=g))
    assert "skim" in text.lower() or "!" in text


def test_expanded_view_exposes_action_affordances(render_broadsheet, make_ui_game):
    g = make_ui_game()
    text = "\n".join(render_broadsheet(tab="Enterprises", expanded=True, game=g))
    for label in ("Expand", "Director", "shares", "Found"):
        assert label in text
    # Buyouts section: defend (buy back) + attack (launch)
    assert "back" in text.lower() and "takeover" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_broadsheet.py -k "expanded or skim" -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

Render the expanded table from `grip.report(...).enterprises`: one row per enterprise (venture, sector, tier, this-turn dividend + delta, Director + loyalty flag with an inline `skim` marker for disloyal, your stake vs. largest outside holder). Include per-row affordances (**Expand**, **Appoint Director**, **Buy/Sell shares**), a **Found** affordance, and a **Buyouts** section (Defend: buy back a named kin's stake at its `market.value` price; Attack: launch a takeover of a named rival). Emit these as clickable action descriptors the app layer can dispatch (Task 4.3) — do not call initiatives from the render.

- [ ] **Step 4: Run test to verify it passes**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_broadsheet.py -k "expanded or skim" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/ui/broadsheet.py gilded/tests/test_broadsheet.py
git commit -m "feat(gilded): expanded Enterprises ledger with per-row actions + buyouts section"
```

---

### Task 4.3: Wire click-actions to initiatives in `app.py`

**Files:**
- Modify: `gilded/ui/app.py`
- Test: `gilded/tests/test_app.py` (the existing app-action test module)

- [ ] **Step 1: Write the failing test**

```python
def test_expand_action_calls_expand_initiative(make_app_state):
    state = make_app_state()
    ent = house_enterprise(state)
    _apply_action(state, {"kind": "expand_enterprise", "eid": ent.eid})
    assert ent.under_construction > 0 or ent.target_tier > ent.tier


def test_appoint_director_action(make_app_state):
    state = make_app_state()
    ent = house_enterprise(state); cand = top_candidate(state, ent)
    _apply_action(state, {"kind": "appoint_director", "eid": ent.eid, "char_id": cand.id})
    assert ent.director_id == cand.id


def test_buy_back_action_moves_shares_to_ruler(make_app_state):
    state = make_app_state()
    ent = house_enterprise(state); kin = disloyal_kin_of(state)
    before = ent.ledger.get(ruler_id_of(state), 0.0)
    _apply_action(state, {"kind": "buy_shares", "eid": ent.eid, "seller_id": kin.id, "pct": 5.0})
    assert ent.ledger.get(ruler_id_of(state), 0.0) > before


def test_found_and_launch_takeover_actions(make_app_state):
    state = make_app_state()
    n = len(game_of(state).enterprises)
    _apply_action(state, {"kind": "found_enterprise", "kind_name": "colliery",
                          "province_pid": first_province_pid(state)})
    assert len(game_of(state).enterprises) == n + 1
    t = len(game_of(state).takeovers)
    _apply_action(state, {"kind": "start_takeover", "target_house": rival_house_of(state)})
    assert len(game_of(state).takeovers) == t + 1
```

> **Implementer note:** match the existing `_apply_action` dispatch shape (see `place_informant` / `set_stance` / `rule`). Reuse whatever the current action dicts look like; the assertions above pin *behavior*, not the exact key names — align keys with the descriptors emitted in Task 4.2.

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_app.py -k "expand or appoint or buy_back or found or takeover" -q`
Expected: FAIL.

- [ ] **Step 3: Implement (behavior spec)**

Extend `_apply_action(state, action)` with cases for `expand_enterprise`, `appoint_director`, `buy_shares`, `sell_shares`, `found_enterprise`, `start_takeover` — each resolving the executor (ruler) and calling `initiative(game, house, verb, executor, **kw)` with the action's args, exactly as `place_informant` does today. No sim logic in `app.py`; it only translates clicks to initiative calls.

- [ ] **Step 4: Run test to verify it passes**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_app.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/ui/app.py gilded/tests/test_app.py
git commit -m "feat(gilded): wire Enterprises panel click-actions to capital initiatives"
```

---

### Task 4.4: Stage-4 smoke + AI parity + full-suite gate

**Files:**
- Create: `gilded/tests/test_stage4_smoke.py` (or extend the existing soak/smoke harness)

- [ ] **Step 1: Write the failing test**

```python
def test_stage4_century_smoke(capsys):
    """A full century runs; market, grip, levers, and AI all exercise without error."""
    g = new_game(seed=0)
    saw_price_move = False
    saw_takeover = False
    for _ in range(60):
        g.end_turn()
        for c in ("coal", "steel", "freight", "farm"):
            assert market.PRICE_MIN <= g.market.price(c) <= market.PRICE_MAX
        if any(g.market.price(c) != 1.0 for c in ("coal", "steel", "freight", "farm")):
            saw_price_move = True
        if any(getattr(tk, "complete", False) for tk in g.takeovers):
            saw_takeover = True
        # grip read-model is callable and pure every turn
        r = grip.report(g, g.player_house)
        assert r.band in grip.BANDS
    assert saw_price_move          # the market actually moved over a century
    print("STAGE4 SMOKE OK", "takeover_fired" if saw_takeover else "no_takeover")


def test_ai_houses_exercise_capital_initiatives(capsys):
    """Rivals act through the same initiatives (parity) — at least one AI capital move over a century."""
    g = new_game(seed=1)
    ai_capital_moves = 0
    for _ in range(60):
        g.end_turn()
        ai_capital_moves += ai_capital_move_count(g)   # helper reading the turn's initiative log
    assert ai_capital_moves > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_stage4_smoke.py -q`
Expected: FAIL (until all layers are integrated) — then diagnose real failures, not by weakening asserts.

- [ ] **Step 3: Implement (behavior spec)**

No new product code expected here — this task proves the integrated stage. If `saw_price_move` or AI parity fails, the gap is in L1/L4 threading, not the test; fix the source. Add only the small test helpers (`ai_capital_move_count`, `new_game`).

- [ ] **Step 4: Run to verify it passes**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_stage4_smoke.py -q`
Expected: PASS, prints `STAGE4 SMOKE OK`.

- [ ] **Step 5: Commit + full Stage-4 gate**

```bash
git add gilded/tests/test_stage4_smoke.py
git commit -m "test(gilded): Stage 4 century smoke + AI capital-initiative parity"
```

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q`
Expected: **full scoped suite GREEN** — Stage 4 complete.

---

## Acceptance mapping (spec §9 → tasks)

| Spec acceptance criterion | Task(s) |
|---|---|
| Coal strike raises coal price, ironworks input cost, cuts steel supply, dividends fall house-wide | 1.5, 1.6 |
| Over-building a sector depresses its price and own dividends | 1.4, 1.6 |
| `market.value` prices a trade AND a buyout; boom↑ bust↓ | 1.4, 3.1, 3.5 |
| Buying back disloyal kin cuts predator's reach + improves Grip; selling raises treasury, lowers control | 3.1, 3.2, 2.2 |
| Disloyal Director diverts dividends + raises accidents; loyal high-industry reverses | 3.3, 3.4 |
| Enterprises panel: Grip banner default → full ledger; every button = one attention; AI same initiatives | 4.1, 4.2, 4.3, 4.4 |
| Full suite green; century smoke OK; determinism (no `game.rng` in market/grip) | every layer gate + 4.4 |

## Out of scope (do not build — spec §10)

Inter-house trade routes / tariffs; action-economy redesign (Stage 7); scripted narrative market shocks; new styling/polish (Stage 8).

---

## Self-review

- **Spec coverage:** §3 Grip → L2 (2.1–2.3); §4 Market chain/prices/threading → L1 (1.1–1.5) + legibility ticker in 4.1; §5.1 Found/Expand → 3.5 + 4.3; §5.2 priced trade/valuation → 1.4 + 3.1 + 3.2; §5.3 Directors + disloyal skim → 3.3 + 3.4; §5.4 buyout attack/defend → 3.1(buyback) + 3.5 + 4.2; §6 panel → L4; §7 module map → covered file-by-file; §8 build layers → L1–L4 = the four waves; §9 acceptance → mapping table above. No gap found.
- **Placeholder scan:** no TBD/TODO; every code step is either a full test (contract) or an explicit behavior spec with signatures — deliberate per the managing-engineer model (CynCo authors bodies).
- **Type consistency:** `market.price(commodity)`, `market.value(ent, game)`, `market.confidence()`, `clear_price(prev, supply, demand)`, `supply_by_commodity`/`demand_by_commodity`, `Market.clear(game)`; `grip.report(game, house)`, `GripReport`, `EnterpriseLine`, `BANDS`, `loyal_bloc`; `priced_transfer(ent, from_id, to_id, pct, market, game, dry_run)`; initiatives `buy_shares`/`sell_shares`/`appoint_director` + `director_candidates`; `director_skim`/`accident_chance_with_director` — names used consistently across tasks.
