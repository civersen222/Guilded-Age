# The Gilded Machine — Play-Experience Redesign: Stage 2 Spec
## Living Adversaries (AI agendas + earned intel)

**Status:** Approved design. Ready to plan.
**Date:** 2026-07-22
**Predecessor:** Stage 1 (the Frame), committed `1d9adf9`.
**Program spec:** `docs/superpowers/specs/2026-07-22-gilded-experience-redesign-design.md`

---

## 0. Executive Summary & Design Mandates

Today the AI brain (`gilded/ai.py`) is purely reactive: each turn it sorts its
docket by conviction, rules petitions, and picks **one** initiative from
disposition thresholds. It holds no persistent goal and is memoryless between
turns. The Director *narrates* a bound rival as a 3-beat arc, but the AI does not
actually pursue that arc. The player therefore faces twitchy greedy bots with no
readable intent — the opposite of a "living adversary."

Stage 2 gives every AI house a **real, persistent goal** (a multi-turn ambition)
that biases its existing choices, and lets the player **earn intelligence** on
those goals through a tiered fog grounded in the sim's existing intrigue economy.

**Design Mandates for Stage 2:**
1. **Honest intent:** the intent the player reads is a *real* goal the house is
   actually pursuing — never a fabricated label over a greedy bot.
2. **Keep the reactive brain:** goals *bias* the existing `ai.py` loop; they do
   not replace it with a scripted planner.
3. **Earned, legible fog:** what you know about a rival is a transparent, additive
   sum of real sources. Legibility of *your own* state (Stage 1) is unchanged; a
   rival's private scheming is gated behind intelligence.
4. **Determinism:** goal selection and intel use dedicated RNG or none — never
   `game.rng`. The intel read-model mutates nothing (soak-tested, like Stage 1).
5. **Headless-first & byte-exact:** every addition verifiable under
   `SDL_VIDEODRIVER=dummy`; shipped as byte-exact CynCo waves + 5-check.

---

## 1. The Goal Model (`gilded/agenda.py`)

A **Goal** is a small, durable object a house commits to. It names an ambition
(family), a target, and persists across turns until achieved, invalidated, or
expired — then the house selects a new one.

### 1.1 Data structure (sketch)

```python
@dataclass(frozen=True)
class Goal:
    family: str          # one of GOAL_FAMILIES
    target: Optional[str]  # house name, province pid, resource key, or None
    opened_turn: int
    commit_turns: int    # re-evaluate on/after opened_turn + commit_turns
    why: str             # short human string, seeds the apparent-intent line
```

Per-house goal state lives on the game: `game.agendas: Dict[str, Goal]`.

### 1.2 The seven families

Each family maps to a lever the AI **already** has; none invents a new capability.

| Family | Ambition | Signature lever (existing) |
|---|---|---|
| **Conquest** | Annex a province / break a house | `declare_war` + massing regiments (`fronts`) |
| **Dominion** | Corner a resource / trade by building | `found_enterprise` / `expand_enterprise` |
| **Buyout** | Usurp a house via its shares (bloodless kill) | `schemes.Takeover` |
| **Dynasty** | Bind a house by blood / press a claim | `propose_marriage` |
| **Intrigue** | Undermine a rival ruler / house | `schemes` (sabotage, blackmail, coup, assassination) |
| **Glory** | Win the judgment peacefully (climb standing/world) | docket ruling toward the axes + prestige/legitimacy |
| **Consolidation** | Weather unrest/war (defensive fallback) | stability petitions + sue for peace (`ai_peace_check`) |

Variety comes from **family × target**: two Conquest houses read as distinct
threats ("after Rivermouth" vs "after your capital"). Seven families is the
ceiling under the "distinct real lever, distinguishable through the fog" test —
an eighth would produce behavior the fog could not tell apart.

### 1.3 Selection, commit, re-evaluation

- **Deterministic:** a dedicated RNG seeded like the Director
  (`seed ^ <constant>`), never `game.rng`; ties broken by name/id.
- **Selection** reads the ruler's dispositions + board state. Examples: high
  `war` conviction + a `_weaker_neighbor` → *Conquest* that neighbor; high
  `ambitious_content` + a rich `_found_spot` → *Dominion*; sour relations + a
  reachable court → *Intrigue*; high unrest / active losing war → *Consolidation*.
- **Commit** for `commit_turns` (default 10, matching `DIRECTIVE_INTERVAL`). The goal is re-evaluated on
  expiry, on achievement, or when it becomes **impossible** (target dead, allied,
  truced, or grown beyond reach) — then a fresh goal is selected.
- Consolidation is the guaranteed fallback when no aggressive goal is viable.

### 1.4 Soft bias into `ai.py` (minimal surgery)

The reactive loop is preserved. Two hooks:
1. **Signature move:** in the leftover-attention branch, before the existing
   `_pick_initiative`, ask the goal for its signature initiative *when ripe and
   affordable* (e.g. Conquest → `declare_war` on its target once strong enough).
   If none is ripe, fall through to today's `_pick_initiative`.
2. **Petition nudge:** `_score_petition` gains a small additive weight for
   petitions in the goal's domain, so ruling leans toward the ambition.

No hard scripting: a house with an unaffordable goal still plays its normal
reactive turn. The change to `ai.py` is additive and bounded.

---

## 2. The Fog — earned intel (`gilded/intel.py`)

A pure read-model (mutates nothing, like `dashboard`). For a viewer and a target
house it returns an `IntelReport`.

### 2.1 Data structure (sketch)

```python
@dataclass(frozen=True)
class IntelReport:
    tier: int                 # 0..3
    breakdown: List[str]      # e.g. ["border +1", "marriage +1", "informant +1"]
    apparent_intent: str      # tier-appropriate one-liner
```

### 2.2 The tiers and their earned sources

| Tier | Revealed | Earned by (existing state) |
|---|---|---|
| **0 — Blind** | name + rank only | default |
| **1 — Mood** | coarse posture ("hostile, arming" / "turned inward") | a shared border (province neighbor owned by target) |
| **2 — Intent** | **family + target** ("Conquest → Rivermouth") | relations/marriage tie, or a friendly minister in their court (`opinion_matrix`) |
| **3 — Depth** | progress + recent moves ("massing 3t · founded ironworks · ~60% to war") | a `Secret` you hold on them (`Secret.holders`), **or** your best court `intrigue` exceeding their counter-intrigue (max court `intrigue`) |

### 2.3 Additive, legible scoring

The tier is the **sum of active sources**, clamped to 0..3, and the `breakdown`
lists each contributor. Example: `border(+1) + marriage(+1) + informant(+1)` →
Tier 3, shown as those three chips. Intel obeys the same cause→effect rule as
the rest of the game: you can always see *why* you know what you know.

### 2.4 The active lever — the informant

A single new player action places an **informant** on a chosen rival: it sets a
durable `+1 tier` flag on the `(viewer, target)` pair (`game.informants:
Dict[Tuple[str, str], bool]` or equivalent). It is the only new *write* in the
fog system, and it carries **no RNG** — the whole "what am I allowed to see"
computation is deterministic. It holds until dropped (later stages may let a
rival's counter-intrigue roll it up; out of scope here).

The lever costs **one unit of ruler attention** to establish (the existing
attention economy — the same currency you spend ruling petitions); once placed
the flag holds for free. It makes "rule another petition, or find out what
they're really after?" a real choice. (Assigning a dedicated courtier-watcher is
a richer alternative deferred to a later stage.)

---

## 3. Threat Rank & the Rival (reconciliation)

Stage 1's rival is the **Director's narrative rival** (`game.director.rival`,
strength-bound, with a 3-beat arc keyed to that house). Stage 2 **does not
repoint it** — the narrative rival keeps the HUD spotlight and its story arc.

Stage 2 adds a **separate threat rank**: a deterministic ordering of all houses
by how much their goal threatens the player (Conquest/Buyout/Intrigue *aimed at
the player* outrank distant ambitions; ties broken by name). The threat rank
orders the Powers roster (§4.2) and flags the "gravest threat." It may or may not
equal the narrative rival, and that divergence is fine — the story rival and the
mechanically-gravest threat are allowed to differ.

---

## 4. UI Surfaces

All three ride on Stage 1's patterns (`dashboard`-fed, headless-testable).

### 4.1 HUD spotlight line

The Stage 1 rival line (`rival + rank`) gains the one-line **Apparent Intent** on
the bound narrative rival, at whatever tier the player holds:

```
RIVAL  House Duval-Corse  #2   ·  Conquest → Rivermouth  ·  massing 3t (Tier 3)
```

Tier 0 → "— no read —"; Tier 1 → mood; Tier 2 → family+target; Tier 3 → adds
progress. Visible on every tab (the HUD already rides above all tabs).

### 4.2 The Powers page (one new tab)

A new foreign-desk tab (name cosmetic: "Powers"/"Dispatches"/"Rivals") listing
every great house with: **rank, your intel tier + the additive breakdown,
apparent intent, and a `Place informant` button** (the active lever). Ordered by
threat rank. This is where the player compares the whole board and spends intel
agency. Follows the Stage 1 broadsheet card/click-action conventions
(`_option_hits`-style hit rects → view actions).

### 4.3 Briefing feed integration

Intent **changes** become lines in the Stage 1 "Since last session" feed:
"House Duval-Corse has turned its ambitions toward Rivermouth" / "Your informant
reports regiments massing." This threads the living board into the Council
Briefing the player already lands on each turn — the board shows up *in the
narrative feed*, not only in a panel.

---

## 5. Architecture & Boundaries

| Unit | Kind | Responsibility | Depends on |
|---|---|---|---|
| `gilded/agenda.py` | sim | `Goal`, families, deterministic selection, commit/re-eval, bias hooks | dispositions, docket/initiatives, fronts, enterprises, schemes |
| `gilded/intel.py` | read-model (pure) | `IntelReport`, tier scoring, apparent-intent strings, threat rank | agenda goals, houses/relations, marriages, `opinion_matrix`, secrets, court intrigue |
| `gilded/ai.py` | sim (minimal edit) | ask goal for signature move; nudge petition scoring | `agenda` |
| UI (`broadsheet.py`, `app.py`) | client | HUD intent line, Powers tab, informant button, Briefing intent line | `intel`, `dashboard` |

- `game.agendas` and the informant flags are the only new persistent state; the
  informant flag is the only new *write* in the fog system.
- `intel.py` is pure and soak-tested (no mutation), exactly like `dashboard`.
- Goal selection is deterministic (dedicated RNG / none), never `game.rng`.

---

## 6. Determinism & Testing

- **Goal selection reproducible** per seed (same board → same goals).
- **Every family maps to a real lever** — a test per family asserting the
  signature initiative/scheme is one the sim already exposes.
- **Intel purity soak:** `intel_report` run many times asserts game-state
  byte-equality before/after (mirrors Stage 1's `scoreboard` soak).
- **Tier monotonicity:** adding a source never lowers the tier; the `breakdown`
  length matches the contributing sources.
- **Informant determinism:** placing/holding an informant changes only the flag
  and raises exactly one tier.
- **Threat rank** is a stable permutation; a Conquest aimed at the player ranks
  above a distant goal.
- **UI headless:** HUD intent line and Powers tab render under
  `SDL_VIDEODRIVER=dummy`; the `Place informant` click yields the expected view
  action; the intent-change Briefing line fires.
- **Baseline:** scoped `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest
  gilded/ test_civkings.py -q` stays green (currently 281 passed), plus the new
  tests each wave. Do **not** run bare root `pytest` (pre-existing
  `test_output.txt` breaks collection).

---

## 7. Build Order (CynCo waves)

Each wave is a byte-exact brief + 5-check (git stat, CRLF-normalized byte-diff,
smoke mtime tamper, re-run smoke, scoped pytest).

- **S2a — Agenda engine.** `gilded/agenda.py` + tests: `Goal`, families,
  deterministic selection, commit/re-eval. Pure of UI; `ai.py` not yet wired.
- **S2b — Intel read-model.** `gilded/intel.py` + tests: tiers, additive scoring,
  apparent-intent strings, threat rank, informant flag read path. Pure, soaked.
- **S2c — AI wiring.** Minimal `ai.py` edits: signature-move hook + petition
  nudge, driven by `game.agendas`. Behavior tests + baseline.
- **S2d — UI.** HUD intent line, Powers tab, `Place informant` lever wiring, the
  Briefing intent-change line, `app.py` action for the lever + tests.

---

## 8. Deferred / Out of Scope

- Counter-intrigue rolling up an informant over time (Stage 2 informant is a
  durable flag; decay/discovery is later).
- A full espionage action tree — Stage 2 adds exactly one active lever; deeper
  spycraft reuses `schemes.py` in a later stage.
- A per-event causal tracer (Stage 8).
- Repointing the narrative rival — kept as the Director's bound rival (§3).
