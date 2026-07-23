# The Gilded Machine — Play-Experience Redesign: Stage 3 Spec
## Policy Dials (Agency + Consequence)

**Status:** Approved design. Ready for implementation planning.
**Date:** 2026-07-23
**Predecessors:** Stage 1 (the Frame, `1d9adf9`), Stage 2 (Living Adversaries, `ea0f7dc`).
**Program spec:** `docs/superpowers/specs/2026-07-22-gilded-experience-redesign-design.md`

---

## 0. Executive Summary & Design Mandate

The five standing **Directives** (`gilded/directives.py`: `capital`, `labor`,
`expansion`, `diplomacy`, `war` — each a −100..+100 stance) already exist as a
narrative/AI-flavor layer, but they carry almost no economic weight and the
player cannot see or set them as a coherent control surface. Stage 3 turns them
into the game's primary **standing-policy control**: five dials the player reads
and adjusts on a new **Policies** tab, each with real, legible teeth in the turn
loop, and each with a real cost paid not in gold but in **minister friction**
(the existing convictions/resignation system). AI Houses set the same five dials
through the same mechanism, so the lever is honest.

This is the first Stage that gives the player broad **standing agency** (Pillar
1) fused with **consequence** (Pillar 4): a dial you move today changes the
numbers on the Briefing for the rest of the century, and a dial your minister
hates slowly costs you that minister.

### Design Mandates for Stage 3
1. **Displayed == Applied.** A single pure module, `gilded/policy.py`, maps the
   five stances to a `PolicyEffects` struct. BOTH the turn loop and the Policies
   tab consume that one function. The number the player reads as the effect of a
   dial is byte-identical to the number the sim applies.
2. **Determinism.** Neither effect computation (`policy.effects`) nor AI
   policy-setting (`ai.set_policy`) may consume `game.rng`. Same seed ⇒ same
   policies ⇒ same economy. (Carries the Stage 2 invariant forward.)
3. **Purity of the read-model.** `policy.effects(game, house)` never mutates game
   state. It is safe to call from the UI every frame.
4. **Honest levers (player/AI parity).** AI Houses drive the same five
   `Directives` via `set_stance`, accrue the same friction, and can lose the same
   ministers. No shadow economy for the AI.
5. **No new attention cost.** Moving a dial is FREE (no petition, no
   action-economy charge). The cost is friction, paid over time. Stage 7 owns the
   action economy; Stage 3 must not pre-empt it.
6. **Headless-verifiable.** All UI additions verifiable under
   `SDL_VIDEODRIVER=dummy` and snapshot/queryable in tests.

---

## 1. The Effects Model (`gilded/policy.py`, pure)

A new pure, deterministic module in the read-model layer. It imports only
low-level constants (`labor`, `enterprises`) — never `chassis`, `ai`, or any UI
— so it introduces no import cycle.

### 1.1 The normalization

For a dial with stance `s ∈ [−100, +100]`, let `t = s / 100 ∈ [−1, +1]`.
`t = 0` is the neutral pole and MUST produce a no-op (multipliers 1.0, additive
terms 0). Every effect below is continuous and monotonic in `t`.

### 1.2 The `PolicyEffects` struct

```python
@dataclass(frozen=True)
class PolicyEffects:
    extraction_level: int      # 0..100, house-wide, fed into labor.py curves
    output_mod: float          # multiplier on province/enterprise output
    dividend_mod: float        # multiplier on shareholder dividends
    expand_cost_mod: float     # multiplier on found/expand cost
    build_speed_mod: float     # multiplier on construction progress per turn
    strength_mod: float        # multiplier on military strength
    happiness_mod: float       # additive, applied per turn
    relations_drift: float     # additive relations change/turn toward neighbours
    unrest_add: float          # additive unrest/turn on worked provinces
    trade_income: float        # additive treasury income/turn from diplomacy
```

One public function:

```python
def effects(game, house) -> PolicyEffects: ...
```

### 1.3 The dial → effect table

Each dial's poles and the exact shape of its contribution. Magnitudes below are
the **design intent**; the implementation plan will include one explicit tuning
pass, but the SHAPE (which pole does what, sign, monotonicity, neutral-at-0) is
fixed by this spec.

| Dial | −100 pole | +100 pole | Effect (with `t = stance/100`) |
| --- | --- | --- | --- |
| **labor** | protective (worker-first) | extractionist | Sets house-wide `extraction_level = round(50 + 50·t)` (range 0..100). This level is fed into the EXISTING `labor.py` curves: `dividend_multiplier` (0.6×@0 → 1.0×@50 → 1.4×@100), `production_multiplier` (0.75×@0 → 1.0×@50 → 1.25×@100), `unrest_gain` (quadratic, up to ~5/turn near 100), and accident risk (zero below 40). `output_mod`/`dividend_mod`/`unrest_add` are read straight off those curves at the computed level. |
| **expansion** | consolidation | expansionism | `expand_cost_mod = 1 − 0.2·t` (cheaper to found/expand when expansionist), and `unrest_add += 1.0·t` on worked provinces (land-hunger strains the populace). |
| **capital** | traditionalist | industrialist | `output_mod ×= 1 + 0.15·t` (industry lifts output), `build_speed_mod = 1 + 0.3·t` (industrialism speeds construction, slows it when traditionalist), and traditionalist pole eases unrest: `unrest_add −= 0.5·|t|` when `t < 0`. |
| **war** | pacifist | militarist | `strength_mod = 1 + 0.25·t` (militarism buys battlefield strength), `happiness_mod −= 5·t` (a war footing costs domestic contentment when militarist; pacifism returns a small happiness dividend). |
| **diplomacy** | nationalist | cosmopolitan | `relations_drift += 2·t`/turn (cosmopolitan warms neighbours), `trade_income += 2·t` per turn (open trade, when cosmopolitan), and the nationalist pole returns home standing: `happiness_mod += 3·|t|` when `t < 0` (with a matching small legitimacy nudge in the turn loop). |

Contributions from the five dials COMBINE additively into the shared
`PolicyEffects` (multipliers multiply, additive terms sum). `effects()` reads the
current stances off `game.directives[house].stances` and never writes them.

### 1.4 Reconciliation: the per-enterprise extraction dial

`enterprises.py` currently carries a per-enterprise `extraction_dial` (default
50, console-only, never surfaced). Stage 3 makes the **house `labor` stance the
single house-wide extraction policy**. The per-enterprise dial is retired as a
*player* concept: enterprise extraction is driven by the house policy's
`extraction_level`. The one existing pathway that resets extraction — the
revolution/ideology reset in `ideology.py` — is redirected to shove the house
`labor` stance toward the protective pole instead of poking a per-enterprise
field. (The exact reset target and whether the per-enterprise field is removed
outright or left as a dormant default is a detail the implementation plan nails
down; the design decision is: **one house-wide extraction level, sourced from the
`labor` dial.**)

---

## 2. Reactive AI Policy-Setting (`ai.set_policy`, deterministic)

Today AI flavor resets directive stances on a coarse every-~10-turns cadence.
Stage 3 replaces that with a per-turn **drift toward a computed target**, living
in `gilded/ai.py` (the writer stays out of the pure `policy.py`).

### 2.1 The target per dial

For each dial, compute a target stance = **ruler conviction baseline** +
**circumstance nudges** + **Stage 2 agenda bias**, then clamp to [−100, +100]:

- **Conviction baseline:** the seated ruler's convictions give each dial its
  resting pole (the same convictions that already drive minister friction).
- **Circumstance nudges (state-driven, deterministic):**
  - treasury low → `labor` target toward extractionist (capital).
  - high unrest / low legitimacy → `labor` toward protective AND `capital` toward
    traditionalist (calm the populace).
  - at war → `war` toward militarist.
- **Stage 2 agenda bias** (reads `game.agendas[house]`, the goal family):
  - Conquest / Glory → `war` toward militarist.
  - Buyout / Dominion → `capital` toward industrialist + `labor` toward
    extractionist.
  - Consolidation → ease extraction (`labor` toward protective) + `capital`
    toward traditionalist.
  - Dynasty → `diplomacy` toward cosmopolitan.

### 2.2 The drift + dead-band (friction parity)

Each turn, for each dial, move the current stance toward the target by a bounded
step **only while `|target − current| > dead_band`** (dead-band ≈ 5). Once a dial
is within the dead-band it **converges and the AI STOPS calling `set_stance` for
it**.

This dead-band is the mechanism that gives AI ministers the same exposure to
friction as the player's: `set_stance` resets the friction counter, so an AI that
re-set its stance every turn would never accrue friction. By going quiet once
converged, the AI's ministers accrue friction against a stance they dislike
exactly as the player's do — and can resign. Player and AI live under one rule.

`set_policy` reads circumstance and agenda state, computes targets, and calls
`game.directives[house].set_stance` — it consumes NO `game.rng`.

---

## 3. The Policies Tab (`ui/broadsheet.py` + `ui/app.py`)

### 3.1 Tab placement

A new **Policies** tab is inserted after **Docket**:

`Briefing · Gazette · Ledger · Letters · Docket · Policies · Atlas · Powers · House`

This updates the pinned `test_tabs_shape` assertion.

### 3.2 `_draw_policies()`

Renders the five dials for the player's house. For each dial:

- **Track + marker**, labelled with both poles and the signed stance, e.g.
  `labor  ——●——  capital  (+40)`.
- **Live effect line** computed from `policy.effects(game, player_house)` — the
  same function the sim uses — so the player reads exactly what will be applied,
  e.g. `dividends ×1.16 · output ×1.08 · unrest +1.3/turn`.
- **Friction flag** when the current stance clashes with the seated minister's
  convictions, surfacing the existing friction counter, e.g.
  `⚠ Chancellor Vale leans labor — straining 2/4`.

### 3.3 Interaction

- Clicking along a dial's track sets that stance, **snapped to steps of 10**.
- `handle_click` returns `{"set_stance": (key, value)}`.
- A new `_dial_hits: List[Tuple[rect, key]]` maps click regions to dials.
- `_apply_action` gains a `set_stance` branch that calls
  `game.directives[player_house].set_stance(key, value)`. This is **FREE** — no
  attention, no petition, no action-economy charge.

Moving a dial takes effect next `end_turn`; the effect line updates immediately
(pure read), so the player previews consequence before ending the turn.

---

## 4. Turn-Loop Wiring, Files, and Tests

### 4.1 Application points (`chassis.end_turn`)

Each turn, `end_turn` calls `policy.effects(game, house)` once per house and
applies the fields at the existing seams:

- **labor →** `society/shares.py` dividend payout uses `dividend_mod`;
  `labor.py` unrest/accidents driven by `extraction_level`.
- **expansion →** `docket.py` found/expand cost scaled by `expand_cost_mod`;
  worked-province unrest gains `unrest_add`.
- **capital →** province/enterprise `output_mod`; `under_construction` progress
  scaled by `build_speed_mod`.
- **war →** `fronts.py` strength scaled by `strength_mod`; `happiness_mod`
  applied; small legitimacy nudge.
- **diplomacy →** neighbour relations nudged by `relations_drift`; `trade_income`
  added to treasury; nationalist `happiness_mod` + legitimacy nudge.

Friction continues to be ticked by the existing `tick_friction()` — Stage 3 does
not change the friction/resignation math, only makes stances something the player
actively moves.

### 4.2 Files

**NEW**
- `gilded/policy.py` — the pure effects module (§1).
- `gilded/tests/test_policy.py` — effects + AI tests.

**MODIFY**
- `gilded/ai.py` — replace the coarse reset with `set_policy` (§2).
- `gilded/chassis.py` — call `policy.effects` and apply at the seams (§4.1).
- `gilded/society/shares.py` — dividends consume `dividend_mod`.
- `gilded/labor.py` — extraction driven by house `extraction_level`.
- `gilded/fronts.py` — strength consumes `strength_mod`.
- `gilded/docket.py` — found/expand cost consumes `expand_cost_mod`.
- `gilded/ideology.py` — revolution/ideology reset shoves the `labor` stance
  (§1.4 reconciliation).
- `gilded/ui/broadsheet.py` — Policies tab + `_draw_policies` + `_dial_hits`.
- `gilded/ui/app.py` — `set_stance` action wiring.
- `gilded/tests/test_ui_broadsheet.py` — tab shape + draw + click.
- `gilded/tests/test_ui_app.py` — `set_stance` action path.

### 4.3 Test plan

- **Policy purity & shape:** `effects` never mutates; every dial is a no-op at
  stance 0; each effect is monotonic in `t`; all fields stay within declared
  bounds across the full [−100, +100] sweep.
- **Economy teeth:** on a fixed seed, a capital/extractionist-leaning house earns
  strictly more dividends AND accrues strictly more unrest than the same house at
  neutral.
- **War:** militarist `war` raises `strength_mod` and lowers `happiness_mod`.
- **Reactive AI:** `set_policy` is deterministic (no `game.rng`); a broke house
  drifts `labor` toward extractionist; a house whose dial has converged inside
  the dead-band stops calling `set_stance`, accrues friction, and can lose a
  minister (player/AI parity).
- **UI:** `test_tabs_shape` updated; `_draw_policies` renders without error under
  dummy SDL; a click on a dial track returns `{"set_stance": (key, snapped)}` and
  `_apply_action` moves the stance for free.
- **Century smoke:** a full 60-turn century runs to completion with policies
  live, no death-spiral, state sane.

### 4.4 Invariants (carried + new)

- `policy.effects` is pure and consumes no `game.rng`.
- `ai.set_policy` consumes no `game.rng`.
- No import cycle: `policy.py` imports only low-level `labor`/`enterprises`
  constants; `ai.py` imports `policy` + `agenda`; the UI imports `policy`.
- Displayed effect (Policies tab) == applied effect (turn loop), because both
  call `policy.effects`.
- The AI drives the same five `Directives` via `set_stance` and is subject to the
  same friction/resignation system as the player.

---

## 5. Out of Scope (Stage 3)

- The action economy / attention budget (Stage 7) — dials are free here.
- Per-event causal tracing (Stage 8) — the effect line implies causality, it does
  not trace it.
- New Directives beyond the existing five.
- Any change to the friction/resignation math itself.
- Enterprises redesign (Stage 4) — Stage 3 only reconciles the per-enterprise
  extraction dial into the house `labor` policy.
