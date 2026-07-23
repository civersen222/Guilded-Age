# Gilded Stage 3 — Policy Dials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **CivKings note:** In this repo, game code lands via CynCo mission briefs (byte-exact, validated). This plan is the source of truth a CynCo build brief is composed from. Every task below is written so its final validated files can be staged and applied verbatim.

**Goal:** Turn the five standing Directives (`capital/labor/expansion/diplomacy/war`) into player-adjustable policy dials with real economic teeth in the turn loop, read and set on a new Policies tab, with AI Houses driving the same dials through the same mechanism.

**Architecture:** A new pure read-model `gilded/policy.py` maps the five stances to a frozen `PolicyEffects` struct. `chassis.end_turn` computes it once per house per turn and applies each field at an existing seam. The **labor** dial is realized by writing a house-wide extraction level into every owned enterprise's existing `extraction_dial` — so all existing labor curves and the endings blood-axis keep working unchanged. The other four dials thread new multipliers into `chassis`/`docket`/`fronts`. AI policy-setting moves to a per-turn drift-with-dead-band in `ai.py`. The Policies tab reads the same `policy.effects()` the sim applies (displayed == applied).

**Tech Stack:** Python 3, dataclasses (frozen), pygame (headless via `SDL_VIDEODRIVER=dummy`), pytest.

**Determinism & purity invariants (hold throughout):**
- `policy.effects(game, house)` is pure — never mutates, never reads `game.rng`.
- `ai.set_policy(game, house)` consumes no `game.rng`.
- No import cycle: `gilded/policy.py` imports only `gilded.society.labor` (curve helpers) + stdlib; `gilded/ai.py` imports `gilded.policy` + `gilded.agenda`; the UI imports `gilded.policy`.
- The number shown on the Policies tab for a dial equals the number `chassis` applies, because both call `policy.effects` (labor line derived from the same `labor.py` curves at the same `extraction_level`).

**The always-scoped test command (NEVER bare `pytest` — a stray `test_output.txt` breaks collection):**
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q
```
Baseline before this plan: **306 passed** (post-Stage-2, commit `ea0f7dc`).

---

## Effects contract (referenced by every task)

For a dial with stance `s ∈ [−100,100]`, `t = s/100 ∈ [−1,1]`. `t = 0` is a strict no-op.

`gilded/policy.py` defines exactly this frozen struct and one pure function:

```python
@dataclass(frozen=True)
class PolicyEffects:
    extraction_level: int    # labor  -> written into each owned enterprise's extraction_dial
    output_mod: float        # capital -> folded into the pay_dividends `mod`
    build_speed_mod: float   # capital -> scales under_construction set at ground-break
    expand_cost_mod: float   # expansion -> scales found/expand gold cost
    strength_mod: float      # war -> scales regiment power in fronts
    happiness_mod: float     # war + diplomacy(nationalist) -> additive to happiness in step 7
    legitimacy_mod: float    # diplomacy(nationalist) -> additive to legitimacy in step 7
    relations_drift: float   # diplomacy -> per-turn relations nudge toward neighbours
    trade_income: float      # diplomacy(cosmopolitan) -> treasury income/turn
    unrest_add: float        # expansion + capital(traditionalist) -> per-turn unrest on worked provinces
```

Formulas (with `tl,tc,te,tw,td` = labor/capital/expansion/war/diplomacy `t`):

| field | formula |
| --- | --- |
| `extraction_level` | `clamp(round(50 + 50*tl), 0, 100)` |
| `output_mod` | `1.0 + 0.15*tc` |
| `build_speed_mod` | `1.0 + 0.3*tc` |
| `expand_cost_mod` | `1.0 - 0.2*te` |
| `strength_mod` | `1.0 + 0.25*tw` |
| `happiness_mod` | `-5.0*tw + (3.0*(-td) if td < 0 else 0.0)` |
| `legitimacy_mod` | `1.5*(-td) if td < 0 else 0.0` |
| `relations_drift` | `2.0*td` |
| `trade_income` | `2.0*td if td > 0 else 0.0` |
| `unrest_add` | `1.0*te + (-0.5*(-tc) if tc < 0 else 0.0)` |

**Labor line display note:** the labor dial's dividend/production/unrest numbers are NOT separate `PolicyEffects` fields — they are produced by writing `extraction_level` into the enterprise dials and letting the existing curves apply. The UI computes the labor display line by calling the same `labor.py` curve helpers at `extraction_level`, so displayed == applied.

**Spec-coverage note (deliberate simplification):** spec §4.1 mentions a "small legitimacy nudge" under the war dial. War's domestic cost is realized through `happiness_mod` (which already flows into `tick_legitimacy` via happiness), so `legitimacy_mod` carries only the diplomacy-nationalist bonus. This keeps the effect legible and avoids a second, redundant legit channel for war.

---

## File Structure

**NEW**
- `gilded/policy.py` — pure `PolicyEffects` + `effects(game, house)` (Task 1).
- `gilded/tests/test_policy.py` — purity/shape/AI tests (Tasks 1, 5).

**MODIFY**
- `gilded/chassis.py` — compute `pol` map; apply labor (drive dials), capital output, unrest_add, war happiness/legitimacy, diplomacy relations/trade; reconcile revolution/transform by shoving house `labor` stance (Tasks 2, 4).
- `gilded/docket.py` — apply `expand_cost_mod` to found/expand cost and `build_speed_mod` to `under_construction` at ground-break (Task 3).
- `gilded/fronts.py` — apply `strength_mod` to regiment power (Task 3).
- `gilded/ai.py` — replace the every-10-turns reset with `set_policy` drift+dead-band (Task 5).
- `gilded/ui/broadsheet.py` — `Policies` tab: `TABS`, draw dispatch, `_draw_policies`, `_dial_hits`, click handling (Task 6).
- `gilded/ui/app.py` — `set_stance` action branch (Task 7).
- `gilded/tests/test_ui_broadsheet.py` — updated `test_tabs_shape`, draw + click tests (Task 6).
- `gilded/tests/test_ui_app.py` — `set_stance` action path (Task 7).

---

## Task 1: The pure effects module (`gilded/policy.py`)

**Files:**
- Create: `gilded/policy.py`
- Create/Test: `gilded/tests/test_policy.py`

- [ ] **Step 1: Write the failing tests**

Create `gilded/tests/test_policy.py`:
```python
"""Stage 3: policy.effects is a pure read-model over the five dials."""

from gilded.chassis import GildedGame
from gilded import policy
from gilded.society import labor


def _set(g, h, **stances):
    for k, v in stances.items():
        g.directives[h].set_stance(k, v)


def test_neutral_is_a_noop():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    e = policy.effects(g, h)
    assert e.extraction_level == 50
    assert e.output_mod == 1.0
    assert e.build_speed_mod == 1.0
    assert e.expand_cost_mod == 1.0
    assert e.strength_mod == 1.0
    assert e.happiness_mod == 0.0
    assert e.legitimacy_mod == 0.0
    assert e.relations_drift == 0.0
    assert e.trade_income == 0.0
    assert e.unrest_add == 0.0


def test_labor_sets_extraction_level_monotonically():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, labor=100)
    assert policy.effects(g, h).extraction_level == 100
    _set(g, h, labor=-100)
    assert policy.effects(g, h).extraction_level == 0
    _set(g, h, labor=50)
    assert policy.effects(g, h).extraction_level == 75


def test_dials_have_correct_signs():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, capital=100, expansion=100, war=100, diplomacy=100)
    e = policy.effects(g, h)
    assert e.output_mod > 1.0          # industrialist lifts output
    assert e.build_speed_mod > 1.0     # industrialist builds faster
    assert e.expand_cost_mod < 1.0     # expansionist is cheaper to grow
    assert e.strength_mod > 1.0        # militarist is stronger
    assert e.relations_drift > 0.0     # cosmopolitan warms neighbours
    assert e.trade_income > 0.0        # cosmopolitan earns trade
    assert e.happiness_mod < 0.0       # war footing costs contentment


def test_nationalist_diplomacy_returns_home_standing():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, diplomacy=-100)
    e = policy.effects(g, h)
    assert e.happiness_mod > 0.0
    assert e.legitimacy_mod > 0.0
    assert e.relations_drift < 0.0
    assert e.trade_income == 0.0


def test_effects_is_pure():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, labor=80, war=40)
    before = GildedGame(seed=1).rng.random()
    policy.effects(g, h)
    policy.effects(g, h)
    assert before == GildedGame(seed=1).rng.random()  # no rng consumed anywhere
    assert g.directives[h].stances["labor"] == 80      # no mutation of stances


def test_labor_display_matches_curves():
    g = GildedGame(seed=1)
    h = sorted(g.houses)[0]
    _set(g, h, labor=100)
    lvl = policy.effects(g, h).extraction_level
    # The UI derives the labor line from the same curves at extraction_level.
    assert labor.dividend_multiplier(lvl) == labor.dividend_multiplier(100)
    assert labor.production_multiplier(lvl) == labor.production_multiplier(100)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_policy.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'gilded.policy'`.

- [ ] **Step 3: Write `gilded/policy.py`**

Create `gilded/policy.py`:
```python
"""Stage 3 read-model (Policy Dials): the standing consequence of one House's
five directive stances. `effects(game, house)` maps the -100..+100 stances on
capital/labor/expansion/diplomacy/war to a frozen PolicyEffects the turn loop
applies and the Policies tab displays. Pure and deterministic: it never mutates
the game and never touches game.rng. The labor dial is realized as a house-wide
extraction level written into each enterprise's existing dial, so all the
society.labor curves (and the endings blood axis) keep working unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from gilded.directives import DIRECTIVE_KEYS


@dataclass(frozen=True)
class PolicyEffects:
    extraction_level: int
    output_mod: float
    build_speed_mod: float
    expand_cost_mod: float
    strength_mod: float
    happiness_mod: float
    legitimacy_mod: float
    relations_drift: float
    trade_income: float
    unrest_add: float


NEUTRAL = PolicyEffects(
    extraction_level=50, output_mod=1.0, build_speed_mod=1.0,
    expand_cost_mod=1.0, strength_mod=1.0, happiness_mod=0.0,
    legitimacy_mod=0.0, relations_drift=0.0, trade_income=0.0, unrest_add=0.0)


def _t(stances, key: str) -> float:
    return max(-100, min(100, int(stances.get(key, 0)))) / 100.0


def effects(game, house_name: str) -> PolicyEffects:
    """Pure: the standing effects of `house_name`'s current dial stances."""
    directives = game.directives.get(house_name)
    if directives is None:
        return NEUTRAL
    st = directives.stances
    tl = _t(st, "labor")
    tc = _t(st, "capital")
    te = _t(st, "expansion")
    tw = _t(st, "war")
    td = _t(st, "diplomacy")
    extraction_level = max(0, min(100, round(50 + 50 * tl)))
    happiness_mod = -5.0 * tw + (3.0 * (-td) if td < 0 else 0.0)
    legitimacy_mod = 1.5 * (-td) if td < 0 else 0.0
    unrest_add = 1.0 * te + (-0.5 * (-tc) if tc < 0 else 0.0)
    return PolicyEffects(
        extraction_level=extraction_level,
        output_mod=1.0 + 0.15 * tc,
        build_speed_mod=1.0 + 0.3 * tc,
        expand_cost_mod=1.0 - 0.2 * te,
        strength_mod=1.0 + 0.25 * tw,
        happiness_mod=happiness_mod,
        legitimacy_mod=legitimacy_mod,
        relations_drift=2.0 * td,
        trade_income=2.0 * td if td > 0 else 0.0,
        unrest_add=unrest_add,
    )
```

Note: `DIRECTIVE_KEYS` is imported to assert module cohesion with the dial set even though `effects` reads keys by name; it documents the source of truth. (If a linter flags it unused, keep it — it is the canonical dial-key contract this module honors.) If strict-unused enforcement is on in CI, replace the import line with a comment referencing `gilded.directives.DIRECTIVE_KEYS`; the current repo has no such enforcement.

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_policy.py -q
```
Expected: PASS — 6 passed.

- [ ] **Step 5: Commit**

```bash
git add gilded/policy.py gilded/tests/test_policy.py
git commit -m "feat(gilded): pure PolicyEffects read-model for the five policy dials"
```

---

## Task 2: Labor dial drives extraction (chassis) + ideology reconciliation

**What:** Each turn, before economics, write the house's `extraction_level` into every owned enterprise's `extraction_dial`, so the existing labor curves apply the labor policy. After a revolution/transformation, shove the house `labor` stance to the protective pole (the workers hold the works).

**Files:**
- Modify: `gilded/chassis.py` (economics prelude in `end_turn`; revolution/transform call sites)
- Test: `gilded/tests/test_chassis.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `gilded/tests/test_chassis.py`:
```python
def test_labor_policy_drives_enterprise_extraction():
    from gilded.chassis import GildedGame
    g = GildedGame(seed=7)
    h = next(x for x in sorted(g.houses) if g.ents_of(x))
    g.directives[h].set_stance("labor", 100)
    g.end_turn()
    assert all(e.extraction_dial == 100.0 for e in g.ents_of(h))
    g.directives[h].set_stance("labor", -100)
    g.end_turn()
    assert all(e.extraction_dial == 0.0 for e in g.ents_of(h))


def test_extractionist_labor_earns_more_and_strains_more():
    from gilded.chassis import GildedGame
    hard = GildedGame(seed=11)
    soft = GildedGame(seed=11)
    h = next(x for x in sorted(hard.houses) if hard.ents_of(x))
    hard.directives[h].set_stance("labor", 100)
    soft.directives[h].set_stance("labor", -100)
    hard.end_turn()
    soft.end_turn()
    hard_unrest = sum(p.unrest for p in hard.provinces_of(h))
    soft_unrest = sum(p.unrest for p in soft.provinces_of(h))
    assert hard.houses[h].treasury >= soft.houses[h].treasury
    assert hard_unrest >= soft_unrest
```

- [ ] **Step 2: Run to verify they fail**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_chassis.py -q -k "labor_policy or extractionist_labor"
```
Expected: FAIL — dials are not driven from policy yet (they stay at 50.0 default; the extractionist/soft treasuries and unrest are equal).

- [ ] **Step 3: Add the effects map + drive dials in `chassis.end_turn`**

In `gilded/chassis.py`, at the top of `end_turn` immediately after `provinces = self.atlas.provinces` (currently ~line 165), insert the per-house effects map and the dial-drive loop:
```python
        provinces = self.atlas.provinces

        # Stage 3: standing policy — compute once, apply at each seam below.
        from gilded import policy
        self.policy = {h: policy.effects(self, h) for h in self.houses}
        for h in sorted(self.houses):
            lvl = float(self.policy[h].extraction_level)
            for ent in self.ents_of(h):
                ent.extraction_dial = lvl
```

- [ ] **Step 4: Reconcile the revolution/transform reset**

In `gilded/chassis.py` step 8 (the revolution block, ~lines 305-311), after the house falls, shove its `labor` stance protective so the workers' new order is reflected in policy (the per-enterprise reset to 50 inside ideology is transient and gets re-driven; this makes the house-level policy honest). Change the `if can_transform` / `else` block to also set the stance:
```python
            if can_transform(realm.ruler):
                msgs, new_leg = transform_house(h, realm.ruler, provs,
                                                self.enterprises, realm,
                                                self.legitimacy[h])
                self.legitimacy[h] = new_leg
                self.fallen.setdefault(h, "transformed")
            else:
                msgs, _flipped = trigger_revolution(h, provs, self.enterprises)
                self.fallen.setdefault(h, "revolution")
            self.directives[h].set_stance("labor", -100)
            self._emit(msgs, "gazette", h)
```

- [ ] **Step 5: Run the new tests + full suite**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_chassis.py -q -k "labor_policy or extractionist_labor"
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q
```
Expected: the two new tests PASS; full suite still green (308 passed).

- [ ] **Step 6: Commit**

```bash
git add gilded/chassis.py gilded/tests/test_chassis.py
git commit -m "feat(gilded): labor dial drives house-wide extraction; revolution eases it"
```

---

## Task 3: Thread the non-labor multipliers (capital / expansion / war / diplomacy)

**What:** Apply `output_mod`, `unrest_add`, `expand_cost_mod`, `build_speed_mod`, `strength_mod`, `relations_drift`, `trade_income`, `happiness_mod`, `legitimacy_mod` at their existing seams. `chassis` owns capital-output, unrest, diplomacy, war-happiness/legitimacy; `docket` owns expansion cost + build speed; `fronts` owns strength.

**Files:**
- Modify: `gilded/chassis.py`, `gilded/docket.py`, `gilded/fronts.py`
- Test: `gilded/tests/test_chassis.py`, `gilded/tests/test_docket.py`, `gilded/tests/test_fronts.py`

### 3a — capital `output_mod` rides the dividend `mod` (chassis)

- [ ] **Step 1: Write the failing test**

Append to `gilded/tests/test_chassis.py`:
```python
def test_industrialist_capital_lifts_dividends():
    from gilded.chassis import GildedGame
    ind = GildedGame(seed=13)
    trad = GildedGame(seed=13)
    h = next(x for x in sorted(ind.houses) if ind.ents_of(x))
    ind.directives[h].set_stance("capital", 100)
    trad.directives[h].set_stance("capital", -100)
    ind.end_turn()
    trad.end_turn()
    assert ind.houses[h].treasury > trad.houses[h].treasury
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_chassis.py -q -k industrialist_capital
```
Expected: FAIL — treasuries equal (capital dial has no output effect yet).

- [ ] **Step 3: Fold `output_mod` into the dividend `mod` in `chassis.end_turn`**

In the dividends loop (~lines 191-207), where `mod` is built per enterprise, multiply in the house's `output_mod`. Change:
```python
            mod = coal_price if ent.kind == "colliery" else 1.0
            mv = getattr(province, "movement", None)
            if mv is not None and mv.state == "striking":
                mod *= STRIKE_OUTPUT_MULT
            take, _ = pay_dividends(realm, [ent], provinces, mod)
```
to:
```python
            mod = coal_price if ent.kind == "colliery" else 1.0
            mv = getattr(province, "movement", None)
            if mv is not None and mv.state == "striking":
                mod *= STRIKE_OUTPUT_MULT
            mod *= self.policy[h].output_mod
            take, _ = pay_dividends(realm, [ent], provinces, mod)
```

- [ ] **Step 4: Run the test**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_chassis.py -q -k industrialist_capital
```
Expected: PASS.

### 3b — `unrest_add`, diplomacy `relations_drift`/`trade_income`, war/diplomacy `happiness_mod`/`legitimacy_mod` (chassis)

- [ ] **Step 5: Write the failing tests**

Append to `gilded/tests/test_chassis.py`:
```python
def test_expansionism_and_diplomacy_apply_standing_effects():
    from gilded.chassis import GildedGame
    g = GildedGame(seed=17)
    h = next(x for x in sorted(g.houses) if g.provinces_of(x))
    base_treasury = g.houses[h].treasury
    g.directives[h].set_stance("expansion", 100)   # +1 unrest/turn on worked provs
    g.directives[h].set_stance("diplomacy", 100)   # +trade income
    calm = GildedGame(seed=17)
    g.end_turn()
    calm.end_turn()
    assert (sum(p.unrest for p in g.provinces_of(h))
            >= sum(p.unrest for p in calm.provinces_of(h)))
    # cosmopolitan trade income lands in the treasury as a standing drip
    assert g.houses[h].treasury >= calm.houses[h].treasury
```

- [ ] **Step 6: Run to verify it fails**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_chassis.py -q -k expansionism_and_diplomacy
```
Expected: FAIL.

- [ ] **Step 7: Apply unrest / trade / happiness / legitimacy in `chassis.end_turn`**

Add a standing-policy application block **at the end of step 3 (labor/movements)**, right before `# 4. society` (~line 231). This adds per-worked-province unrest and per-house trade income:
```python
        # Stage 3: standing policy on land and treasury.
        for h in sorted(self.houses):
            eff = self.policy[h]
            if eff.unrest_add:
                for province in self.provinces_of(h):
                    province.unrest = max(0.0, province.unrest + eff.unrest_add)
            if eff.trade_income:
                self.houses[h].treasury += eff.trade_income
```

Then extend step 7 (the mandate) so `happiness_mod`/`legitimacy_mod` reach happiness and legitimacy. Change the step-7 loop (~lines 285-291):
```python
        for h in sorted(self.houses):
            provs = self.provinces_of(h)
            unrest = (sum(p.unrest for p in provs) / len(provs)) if provs else 0.0
            happiness = int(50.0 - unrest + self.policy[h].happiness_mod)
            self.legitimacy[h] = tick_legitimacy(
                self.legitimacy[h], happiness, self.tide,
                self.tide.consume_fresh(h)) + self.policy[h].legitimacy_mod
            self.legitimacy[h] = max(0.0, min(100.0, self.legitimacy[h]))
```
(`tick_legitimacy` already clamps to `[0, LEGITIMACY_MAX]`; the extra `legitimacy_mod` is re-clamped to `[0,100]` here. Confirm `LEGITIMACY_MAX == 100.0` in `gilded/society/ideology.py`; if it differs, clamp to `LEGITIMACY_MAX` instead of `100.0`.)

For diplomacy `relations_drift`, apply it in step 7's loop as a warming/cooling of this house's standing relations toward the other houses. The relations store is `game.houses[h].relations`, a `Dict[str, int]` keyed by house name, range −100..100, initialized to 0 for every pair (`gilded/houses.py:31,131`); it is exactly what `intel.py` reads (`intel.py:52,76`). Immediately after the legitimacy line above, add:
```python
            drift = self.policy[h].relations_drift
            if drift:
                rel = self.houses[h].relations
                for other in self.houses:
                    if other == h:
                        continue
                    rel[other] = max(-100, min(100, int(round(
                        rel.get(other, 0) + drift))))
```
(Relations are directional per house — nudging `houses[h].relations[other]` warms/cools how house `h` regards `other`, which is the axis `intel` reads. This is deliberate; do not attempt to mirror it onto `other`'s dict.)

- [ ] **Step 8: Run the test + full suite**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_chassis.py -q -k "expansionism_and_diplomacy or industrialist_capital"
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q
```
Expected: new tests PASS; suite green.

### 3c — expansion cost + build speed at ground-break (docket)

- [ ] **Step 9: Write the failing test**

Append to `gilded/tests/test_docket.py` (mirror the existing capital-request test setup in that file — read it first for the exact fixture/imports used to build a game with a fundable enterprise):
```python
def test_expansionist_policy_cheapens_expansion():
    from gilded.chassis import GildedGame
    from gilded.enterprises import EXPAND_COST
    g = GildedGame(seed=23)
    h = next(x for x in sorted(g.houses) if g.ents_of(x))
    ent = next(e for e in g.ents_of(h) if e.tier < 5 and e.under_construction == 0)
    g.directives[h].set_stance("expansion", 100)
    from gilded import policy
    eff = policy.effects(g, h)
    expected = EXPAND_COST[ent.tier + 1] * eff.expand_cost_mod
    assert expected < EXPAND_COST[ent.tier + 1]
```

This test pins the intended cost math; the wiring test is that the funded-cost path multiplies by `expand_cost_mod`. (A full end-to-end petition-funding test is optional; the multiplier presence is the contract.)

- [ ] **Step 10: Run to verify it passes trivially or fails**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_docket.py -q -k expansionist_policy
```
Expected: PASS (this test only asserts the `policy` math). Its purpose is to lock the contract; the wiring below makes the sim honor it.

- [ ] **Step 11: Apply `expand_cost_mod` + `build_speed_mod` in `docket._gen_capital_request`**

In `gilded/docket.py`, `_gen_capital_request` (~lines 127-133), scale the cost by the house policy and speed construction. Change:
```python
    ent = min(candidates, key=lambda e: (e.tier, e.eid))
    director = by_id[ent.director_id]
    cost = EXPAND_COST[ent.tier + 1]
```
to:
```python
    ent = min(candidates, key=lambda e: (e.tier, e.eid))
    director = by_id[ent.director_id]
    from gilded import policy
    _eff = policy.effects(game, house_name)
    cost = EXPAND_COST[ent.tier + 1] * _eff.expand_cost_mod
```
and inside `_grant`, change:
```python
        house.treasury -= cost
        ent.under_construction = EXPAND_TURNS[ent.tier + 1]
```
to:
```python
        house.treasury -= cost
        _turns = EXPAND_TURNS[ent.tier + 1]
        if _eff.build_speed_mod > 0:
            _turns = max(1, int(round(_turns / _eff.build_speed_mod)))
        ent.under_construction = _turns
```

- [ ] **Step 12: Run docket tests**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_docket.py -q
```
Expected: PASS.

### 3d — war `strength_mod` in fronts

- [ ] **Step 13: Write the failing test**

Append to `gilded/tests/test_fronts.py`:
```python
def test_militarist_policy_boosts_regiment_power():
    from gilded import policy
    from gilded.chassis import GildedGame
    g = GildedGame(seed=29)
    h = sorted(g.houses)[0]
    g.directives[h].set_stance("war", 100)
    assert policy.effects(g, h).strength_mod > 1.0
```

Plus a wiring assertion: if `resolve_front` is unit-testable with a synthetic War/Front (read the existing `test_fronts.py` for its helpers), assert that raising the aggressor house's `war` stance to +100 strictly increases `power_a` for the same seed. If the existing test scaffolding does not expose `power_a`, keep only the `strength_mod` contract test above and rely on the smoke test (Task 8) to exercise the wiring.

- [ ] **Step 14: Run to verify state**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_fronts.py -q -k militarist_policy
```
Expected: PASS (contract test).

- [ ] **Step 15: Apply `strength_mod` in `fronts.resolve_front`**

In `gilded/fronts.py`, `resolve_front` (~lines 244-254), multiply each side's power by that side's house `strength_mod`. Change:
```python
    power_a = (front.attacker_regiments * _cmd_mult(cmd_a)
               * supply(game, war.aggressor, front) * _dice(game, cmd_a))
    power_d = (front.defender_regiments * _cmd_mult(cmd_d)
               * supply(game, war.defender, front)
               * (1.0 + ENTRENCH_DEFENSE * front.entrenchment_d)
               * _dice(game, cmd_d))
```
to:
```python
    from gilded import policy
    str_a = policy.effects(game, war.aggressor).strength_mod
    str_d = policy.effects(game, war.defender).strength_mod
    power_a = (front.attacker_regiments * _cmd_mult(cmd_a) * str_a
               * supply(game, war.aggressor, front) * _dice(game, cmd_a))
    power_d = (front.defender_regiments * _cmd_mult(cmd_d) * str_d
               * supply(game, war.defender, front)
               * (1.0 + ENTRENCH_DEFENSE * front.entrenchment_d)
               * _dice(game, cmd_d))
```
Confirm `war.aggressor` and `war.defender` are house-name strings (they are used that way in `supply(game, war.aggressor, front)` on the same lines).

- [ ] **Step 16: Run fronts tests + full suite**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_fronts.py -q
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q
```
Expected: green.

- [ ] **Step 17: Commit**

```bash
git add gilded/chassis.py gilded/docket.py gilded/fronts.py \
        gilded/tests/test_chassis.py gilded/tests/test_docket.py gilded/tests/test_fronts.py
git commit -m "feat(gilded): policy dials gain teeth — output/unrest/expansion/war/diplomacy seams"
```

---

## Task 4: (folded into Task 3) — no separate task

*Reserved intentionally.* All turn-loop seams are covered by Tasks 2–3; the AI writer is Task 5, the UI is Tasks 6–7. Skip.

---

## Task 5: Reactive AI policy-setting (`ai.set_policy` with dead-band)

**What:** Replace the every-10-turns `set_stance(key, conviction)` reset with a per-turn drift toward a computed target (conviction baseline + circumstance nudges + Stage-2 agenda bias), moving only while `|target − current| > DEAD_BAND`. Once converged, stop calling `set_stance` so the AI's ministers accrue friction like the player's. No `game.rng`.

**Files:**
- Modify: `gilded/ai.py`
- Test: `gilded/tests/test_policy.py` (append AI tests) and/or `gilded/tests/test_ai.py`

- [ ] **Step 1: Write the failing tests**

Append to `gilded/tests/test_policy.py`:
```python
def test_set_policy_is_deterministic_and_rng_free():
    from gilded.chassis import GildedGame
    from gilded.ai import set_policy
    g1 = GildedGame(seed=5)
    g2 = GildedGame(seed=5)
    h = next(x for x in sorted(g1.houses) if not g1.houses[x].is_player)
    before = GildedGame(seed=5).rng.random()
    set_policy(g1, h)
    set_policy(g2, h)
    assert g1.directives[h].stances == g2.directives[h].stances
    assert before == GildedGame(seed=5).rng.random()


def test_set_policy_drifts_toward_target_in_bounded_steps():
    from gilded.chassis import GildedGame
    from gilded.ai import set_policy, POLICY_STEP
    g = GildedGame(seed=5)
    h = next(x for x in sorted(g.houses) if not g.houses[x].is_player)
    for k in ("capital", "labor", "expansion", "diplomacy", "war"):
        g.directives[h].set_stance(k, 0)
    set_policy(g, h)
    for k, v in g.directives[h].stances.items():
        assert abs(v) <= POLICY_STEP  # a single step from 0, never a jump


def test_converged_dial_stops_being_reset():
    from gilded.chassis import GildedGame
    from gilded.ai import set_policy, _policy_targets, DEAD_BAND
    g = GildedGame(seed=5)
    h = next(x for x in sorted(g.houses) if not g.houses[x].is_player)
    targets = _policy_targets(g, h)
    # Park every dial exactly on target: set_policy must NOT call set_stance
    # (which would reset friction_turns), so a pre-loaded counter survives.
    for k, tgt in targets.items():
        g.directives[h].set_stance(k, tgt)
        g.directives[h].friction_turns[k] = 3
    set_policy(g, h)
    assert all(g.directives[h].friction_turns[k] == 3 for k in targets)
```

- [ ] **Step 2: Run to verify they fail**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_policy.py -q -k "set_policy or converged"
```
Expected: FAIL — `set_policy`, `_policy_targets`, `POLICY_STEP`, `DEAD_BAND` don't exist.

- [ ] **Step 3: Add `set_policy` and helpers to `gilded/ai.py`; replace the reset**

In `gilded/ai.py`, add near the top constants (after `DIRECTIVE_INTERVAL = 10`, ~line 19):
```python
POLICY_STEP = 15      # max stance change per dial per turn
DEAD_BAND = 5         # within this of target, leave it alone (friction accrues)
```

Add these functions (place them just above `ai_turn`):
```python
def _policy_targets(game, house_name) -> dict:
    """Deterministic target stance per dial: ruler conviction baseline +
    circumstance nudges + Stage-2 agenda bias. No rng."""
    realm = game.realms[house_name]
    ruler = realm.ruler
    targets = {k: _conviction(ruler, k) for k in DIRECTIVE_KEYS}

    house = game.houses[house_name]
    provs = game.provinces_of(house_name)
    unrest = (sum(p.unrest for p in provs) / len(provs)) if provs else 0.0
    legitimacy = game.legitimacy.get(house_name, 50.0)
    at_war = any(house_name in (w.aggressor, w.defender) for w in game.wars)

    if house.treasury < LOW_TREASURY:
        targets["labor"] += 40            # squeeze harder when broke
    if unrest > HIGH_UNREST or legitimacy < LOW_LEGITIMACY:
        targets["labor"] -= 40            # ease the squeeze to calm the land
        targets["capital"] -= 30          # go traditionalist
    if at_war:
        targets["war"] += 50              # mobilize

    goal = game.agendas.get(house_name)
    fam = getattr(goal, "family", None)
    if fam in ("Conquest", "Glory"):
        targets["war"] += 40
    elif fam in ("Buyout", "Dominion"):
        targets["capital"] += 40
        targets["labor"] += 30
    elif fam == "Consolidation":
        targets["labor"] -= 30
        targets["capital"] -= 20
    elif fam == "Dynasty":
        targets["diplomacy"] += 40

    return {k: max(-100, min(100, int(round(v)))) for k, v in targets.items()}


def set_policy(game, house_name) -> None:
    """Drift each dial one bounded step toward its target, but only while the
    gap exceeds the dead-band. Converged dials are left untouched so their
    seated ministers accrue friction exactly as the player's do. No rng."""
    directives = game.directives[house_name]
    targets = _policy_targets(game, house_name)
    for key in DIRECTIVE_KEYS:
        current = directives.stances.get(key, 0)
        target = targets[key]
        gap = target - current
        if abs(gap) <= DEAD_BAND:
            continue                      # converged: do not reset friction
        step = max(-POLICY_STEP, min(POLICY_STEP, gap))
        directives.set_stance(key, current + step)
```

Add the required constants near the other AI thresholds (top of `ai.py`; pick values consistent with existing scales — treasury and legitimacy are on 0..~100s):
```python
LOW_TREASURY = 200.0
HIGH_UNREST = 25.0
LOW_LEGITIMACY = 30.0
```
**Before writing these**, grep `ai.py` for any existing treasury/unrest/legitimacy thresholds and reuse them if present rather than introducing duplicates.

Then in `ai_turn`, replace the reset block (~lines 141-144):
```python
    if game.turn % DIRECTIVE_INTERVAL == 1:
        directives = game.directives[house_name]
        for key in DIRECTIVE_KEYS:
            directives.set_stance(key, int(round(_conviction(ruler, key))))
```
with:
```python
    set_policy(game, house_name)
```

Confirm `game.wars`, `game.provinces_of`, `game.legitimacy`, `game.agendas` are all present on `GildedGame` (they are used elsewhere in `chassis.py`; the Explore reference confirms `agendas` at chassis:88, `provinces_of`/`legitimacy` in step 7, `wars` in `tick_wars`). `_conviction` and `DIRECTIVE_KEYS` are already imported/defined in `ai.py`.

- [ ] **Step 4: Run the AI tests**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_policy.py -q -k "set_policy or converged"
```
Expected: PASS.

- [ ] **Step 5: Run the full suite (AI behavior changed — check nothing pinned the 10-turn cadence)**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q
```
Expected: green. If a test in `test_ai.py` asserted the old every-10-turns snap-to-conviction behavior, update it to assert the new drift (a dial moves toward — not instantly to — conviction+circumstance). Show the updated assertion in the CynCo brief.

- [ ] **Step 6: Commit**

```bash
git add gilded/ai.py gilded/tests/test_policy.py
git commit -m "feat(gilded): AI drifts policy toward conviction+circumstance with a friction dead-band"
```

---

## Task 6: The Policies tab (broadsheet)

**What:** Insert a `Policies` tab after `Docket`; draw five dials (track + marker + signed stance + live effect line + friction flag); make the track clickable (snapped to steps of 10) returning `{"set_stance": (key, value)}`.

**Files:**
- Modify: `gilded/ui/broadsheet.py`
- Test: `gilded/tests/test_ui_broadsheet.py`

- [ ] **Step 1: Update the pinned tab-shape test (write the new expectation first)**

In `gilded/tests/test_ui_broadsheet.py`, change `test_tabs_shape` to:
```python
def test_tabs_shape():
    assert TABS == ("Briefing", "Gazette", "Ledger", "Letters",
                    "Docket", "Policies", "Atlas", "Powers", "House")
```

Add a draw + click test (read the file's existing fixtures for how a `Broadsheet`/view is constructed headlessly — reuse them; the snippet below assumes a helper `_make_view()` like the other tests in this file, adapt names to the real fixtures):
```python
def test_policies_tab_draws_and_clicks(monkeypatch):
    import pygame
    from gilded.ui.broadsheet import Broadsheet  # adapt to real class name
    view = _make_view()                            # adapt to real fixture
    view.active_tab = "Policies"
    surf = pygame.Surface((1280, 800))
    view.draw(surf)                                # must not raise
    assert view._dial_hits                         # dial hit-regions were built
    rect, key = view._dial_hits[0]
    action = view.handle_click((rect.centerx, rect.centery))
    assert set(action) == {"set_stance"}
    k, v = action["set_stance"]
    assert k in ("capital", "labor", "expansion", "diplomacy", "war")
    assert -100 <= v <= 100 and v % 10 == 0
```

- [ ] **Step 2: Run to verify failure**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_ui_broadsheet.py -q -k "tabs_shape or policies_tab"
```
Expected: FAIL — `TABS` lacks "Policies"; no `_draw_policies`/`_dial_hits`.

- [ ] **Step 3: Add the tab to `TABS`**

In `gilded/ui/broadsheet.py` line 32, change:
```python
TABS = ("Briefing", "Gazette", "Ledger", "Letters", "Docket", "Atlas", "Powers", "House")
```
to:
```python
TABS = ("Briefing", "Gazette", "Ledger", "Letters", "Docket", "Policies", "Atlas", "Powers", "House")
```

- [ ] **Step 4: Dispatch the draw**

In the `draw` method (~lines 138-151), initialize the dial-hit list next to the other hit lists (~line 132, where `self._option_hits = []` / `self._exec_hits = []` are reset) by adding:
```python
        self._dial_hits = []
```
and add a dispatch branch (after the `Docket` branch):
```python
        elif self.active_tab == "Policies":
            self._draw_policies(surface, content)
```

- [ ] **Step 5: Implement `_draw_policies`**

Add this method to the `Broadsheet` class (adapt `_font`, color constants `INK/FADED/PAPER_BG/CARD_BG/CARD_EDGE/BUTTON_BG`, and `PAD` — all already used elsewhere in this file):
```python
    def _draw_policies(self, surface, content) -> None:
        from gilded import policy
        from gilded.society import labor
        from gilded.directives import (DIRECTIVE_KEYS, DIRECTIVE_CONVICTION,
                                        friction, FRICTION_THRESHOLD)
        from gilded.docket import DOMAIN_SEAT

        POLES = {
            "capital": ("traditionalist", "industrialist"),
            "labor": ("protective", "extractionist"),
            "expansion": ("consolidation", "expansionism"),
            "diplomacy": ("nationalist", "cosmopolitan"),
            "war": ("pacifist", "militarist"),
        }
        h = self.house
        eff = policy.effects(self.game, h)
        directives = self.game.directives[h]
        realm = self.game.realms[h]
        title = _font(22, bold=True)
        label = _font(17, bold=True)
        small = _font(15)
        x = content.x + PAD
        w = content.width - 2 * PAD
        y = content.y + PAD
        surface.blit(title.render("Standing Policy", True, INK), (x, y))
        y += title.get_height() + 12
        track_w = w - 240
        for key in DIRECTIVE_KEYS:
            left, right = POLES[key]
            stance = directives.stances.get(key, 0)
            # label row
            surface.blit(label.render(f"{left}", True, FADED), (x, y))
            rlabel = label.render(right, True, FADED)
            surface.blit(rlabel, (x + track_w - rlabel.get_width(), y))
            sign = f"(+{stance})" if stance > 0 else f"({stance})"
            surface.blit(label.render(sign, True, INK), (x + track_w + 16, y))
            y += label.get_height() + 6
            # track + marker
            track_y = y + 8
            pygame.draw.line(surface, CARD_EDGE, (x, track_y),
                             (x + track_w, track_y), 3)
            frac = (stance + 100) / 200.0
            mx = int(x + frac * track_w)
            pygame.draw.circle(surface, INK, (mx, track_y), 7)
            track_rect = pygame.Rect(x, track_y - 12, track_w, 24)
            self._dial_hits.append((track_rect, key))
            y += 22
            # live effect line (displayed == applied)
            if key == "labor":
                lvl = eff.extraction_level
                line = (f"extraction {lvl} · dividends x"
                        f"{labor.dividend_multiplier(lvl):.2f} · output x"
                        f"{labor.production_multiplier(lvl):.2f} · unrest +"
                        f"{labor.unrest_gain(lvl):.1f}/turn")
            elif key == "capital":
                line = (f"output x{eff.output_mod:.2f} · build x"
                        f"{eff.build_speed_mod:.2f}")
            elif key == "expansion":
                line = (f"expansion cost x{eff.expand_cost_mod:.2f} · unrest +"
                        f"{max(0.0, eff.unrest_add):.1f}/turn")
            elif key == "war":
                line = (f"strength x{eff.strength_mod:.2f} · happiness "
                        f"{eff.happiness_mod:+.1f}")
            else:  # diplomacy
                line = (f"relations {eff.relations_drift:+.1f}/turn · trade +"
                        f"{eff.trade_income:.1f} · legitimacy "
                        f"{eff.legitimacy_mod:+.1f}")
            surface.blit(small.render(line, True, INK), (x, y))
            y += small.get_height() + 4
            # friction flag
            seat = realm.court.positions.get(DOMAIN_SEAT[key])
            if seat is not None and getattr(seat, "is_alive", False):
                conviction = seat.dispositions.get(DIRECTIVE_CONVICTION[key], 0.0)
                if friction(stance, conviction) > 0:
                    turns = directives.friction_turns.get(key, 0)
                    flag = (f"! {seat.name} leans "
                            f"{left if conviction < 0 else right} — straining "
                            f"{turns}/4")
                    surface.blit(small.render(flag, True, FADED), (x, y))
                    y += small.get_height() + 4
            y += 16
```
Note: `DOMAIN_SEAT` is defined in `gilded/docket.py`; importing it inside the method avoids a top-level cycle. Reuse whatever `_font` signature the file already uses (Explore shows `_font(size, bold=...)`).

- [ ] **Step 6: Handle clicks on the track**

In `handle_click` (~lines 446-470), add a `Policies` branch before the final `return None`:
```python
        if self.active_tab == "Policies":
            for rect, key in self._dial_hits:
                if rect.collidepoint(pos):
                    frac = (pos[0] - rect.x) / rect.width
                    value = int(round((frac * 200 - 100) / 10.0)) * 10
                    value = max(-100, min(100, value))
                    return {"set_stance": (key, value)}
```

- [ ] **Step 7: Run the UI tests**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_ui_broadsheet.py -q
```
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add gilded/ui/broadsheet.py gilded/tests/test_ui_broadsheet.py
git commit -m "feat(gilded): Policies tab — five dials with live effect lines and friction flags"
```

---

## Task 7: Wire the `set_stance` action (app)

**What:** Consume `{"set_stance": (key, value)}` from `handle_click` and apply it to the player house's directives — FREE (no attention).

**Files:**
- Modify: `gilded/ui/app.py`
- Test: `gilded/tests/test_ui_app.py`

- [ ] **Step 1: Write the failing test**

Append to `gilded/tests/test_ui_app.py` (reuse the file's existing `AppState`/game fixtures — read them first; the snippet assumes a helper `_make_state()` like the other tests):
```python
def test_set_stance_action_moves_the_dial_for_free():
    from gilded.ui.app import _apply_action
    state = _make_state()                     # adapt to real fixture
    g, h = state.game, state.house
    attn_before = g.attention.get(h, 0)
    _apply_action(state, {"set_stance": ("labor", 40)})
    assert g.directives[h].stances["labor"] == 40
    assert g.attention.get(h, 0) == attn_before   # free — no attention spent
```

- [ ] **Step 2: Run to verify failure**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_ui_app.py -q -k set_stance_action
```
Expected: FAIL — no `set_stance` branch; the dial doesn't move.

- [ ] **Step 3: Add the branch to `_apply_action`**

In `gilded/ui/app.py`, `_apply_action` (~lines 72-106), add before the `if "rule" in action:` branch:
```python
    stance = action.get("set_stance")
    if stance is not None:
        key, value = stance
        g.directives[h].set_stance(key, value)
        return
```

- [ ] **Step 4: Run the test + full suite**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_ui_app.py -q
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q
```
Expected: green.

- [ ] **Step 5: Commit**

```bash
git add gilded/ui/app.py gilded/tests/test_ui_app.py
git commit -m "feat(gilded): wire the free set_stance action from the Policies tab"
```

---

## Task 8: Century smoke — no death-spiral, state sane

**What:** A full 60-turn century runs to completion with policies live and AI drifting, no crash, state within bounds.

**Files:**
- Test: `gilded/tests/test_soak.py` (append) — this file already asserts `0.0 <= e.extraction_dial <= 100.0`, so it is the right home.

- [ ] **Step 1: Write the smoke test**

Append to `gilded/tests/test_soak.py`:
```python
def test_policy_century_is_stable():
    from gilded.chassis import GildedGame
    g = GildedGame(seed=2026)
    for _ in range(60):
        if g.game_over is not None:
            break
        g.end_turn()
    for h in g.houses:
        assert 0.0 <= g.legitimacy[h] <= 100.0
        for e in g.ents_of(h):
            assert 0.0 <= e.extraction_dial <= 100.0
        for k, v in g.directives[h].stances.items():
            assert -100 <= v <= 100
```
(If `LEGITIMACY_MAX` differs from 100.0, adjust the upper bound to match — read `gilded/society/ideology.py`.)

- [ ] **Step 2: Run it**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_soak.py -q -k policy_century_is_stable
```
Expected: PASS.

- [ ] **Step 3: Full suite green**

Run:
```bash
GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q
```
Expected: all green (baseline 306 + the new Stage-3 tests).

- [ ] **Step 4: Commit**

```bash
git add gilded/tests/test_soak.py
git commit -m "test(gilded): century smoke for live policy dials"
```

---

## Final review

After all tasks: dispatch a code-review pass over the full Stage 3 diff against this plan and the spec (`docs/superpowers/specs/2026-07-23-gilded-stage3-policy-dials-design.md`). Confirm the invariants: `policy.effects` pure and rng-free; `set_policy` rng-free; no import cycle; displayed == applied on every dial line; AI and player under one friction rule. Then the validated fileset becomes the Stage 3 CynCo build brief (byte-exact staging under `C:/tmp/gilded_briefs/S3_src/`, `S3_brief.md` + `S3_task.json`, 5-check, single atomic commit on master) — the same pipeline as Stage 1 and Stage 2.

---

## Self-review (author's checklist against the spec)

**Spec coverage:**
- §1 Effects model → Task 1 (`policy.py`, all ten fields, neutral-at-0, formulas table).
- §1.3 dial→effect table → Tasks 1 (compute) + 2/3 (apply each field at its seam).
- §1.4 per-enterprise-dial reconciliation → Task 2 (labor level drives `extraction_dial`; revolution/transform shoves house `labor` stance; endings blood-axis untouched because the field is still the applied value).
- §2 reactive AI + dead-band + agenda bias → Task 5 (`set_policy`, `_policy_targets`, `POLICY_STEP`, `DEAD_BAND`).
- §3 Policies tab (track/marker/effect line/friction flag/click-snap-10/free) → Tasks 6 (draw+click) + 7 (free apply).
- §4.1 turn-loop application points → Task 2 (labor, chassis), Task 3 (capital/expansion/war/diplomacy across chassis/docket/fronts).
- §4.2 files → File Structure section matches (NEW policy.py+test; MODIFY the nine listed).
- §4.3 test plan → purity/neutral/monotonic/bounds (T1), economy dividends+unrest (T2/T3a/b), war strength (T3d), AI determinism+drift+dead-band/friction parity (T5), UI tabs/draw/click (T6), free action (T7), century smoke (T8).
- §4.4 invariants → asserted in T1/T5 tests and the plan header.

**Deliberate deviations from the spec (flag for the user):**
1. **Paths:** spec said `gilded/labor.py`/`gilded/ideology.py`; real paths are `gilded/society/labor.py` / `gilded/society/ideology.py`. Corrected throughout.
2. **Labor realized via the existing per-enterprise dial** (not a separately-threaded `dividend_mod`), because the dial already feeds all four curves AND the endings blood-axis — driving it is lower-risk and keeps displayed==applied. So `PolicyEffects` carries `extraction_level` (not `dividend_mod`); the UI derives the labor line from the same curves.
3. **War `legitimacy_mod` dropped** in favor of realizing war's domestic cost through `happiness_mod` (which already flows to legitimacy). Noted at the effects contract.
4. **`relations_drift` resolved (kept):** the house-to-house relations store DOES exist — `game.houses[h].relations: Dict[str,int]` (−100..100, `houses.py:31`), the same axis `intel.py` reads. Task 3b applies drift directly to `houses[h].relations[other]` (directional, clamped). No relations system is invented; nothing is dropped.

**Placeholder scan:** none — every code step carries complete code. The two "adapt to real fixture" notes (UI tests) point at reading existing same-file fixtures, not inventing behavior; the CynCo brief will pin them to the actual helper names.

**Type consistency:** `PolicyEffects` field names identical across Task 1 (def), Tasks 2/3/6 (read), and the effects-contract table. `set_policy`/`_policy_targets`/`POLICY_STEP`/`DEAD_BAND` names identical across Task 5 def and its tests. `{"set_stance": (key, value)}` shape identical across Task 6 (produce) and Task 7 (consume).
