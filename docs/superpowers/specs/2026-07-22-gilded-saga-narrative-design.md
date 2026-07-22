# The Gilded Saga — Narrative Director Design

**Date:** 2026-07-22
**Status:** Approved (brainstorming complete; composed "all three" shape + determinism boundary confirmed by user)
**Package:** `gilded/` (CivKings repo, master). Built on the completed Gilded Machine (G1–G23, HEAD `4dc27c0`).
**Implemented by:** CynCo one-shot missions (byte-exact briefs), not hand-edits.

---

## The Problem (why the game felt small)

The Gilded Machine simulates a century of dynastic capitalism in real depth: houses,
courts, enterprises, labor movements, schemes, marriages, wars, an ideological tide, and
four-axis endings. Yet a player who sat down and played reported it felt like "a shitty
MVP." The diagnosis was not that the sim is shallow — it is that the sim's depth is
**invisible and incoherent at the surface**. Each turn the broadsheet prints a flat pile
of independent event lines (`TurnEvent`s) with no spine: nothing foreshadows, nothing
pays off, nothing accumulates into a *story*. A famine, a succession, a rival's rise, and
the century's ideological turn all read as unrelated noise of equal weight. There is no
sense that the player is living through a **named age** with **antagonists** and
**threads** that begin, build, and resolve.

The Gilded Machine's sibling project `C:/Users/civer/dndai` (a persistent-world AI D&D
game) solved the analogous problem with a **Director / Arc engine**: an authored spine of
acts and beats, each with a completion predicate read against durable typed **world
facts**, split into *load-bearing* beats (mechanically guaranteed to advance) and *soft*
beats (LLM-colored atmosphere), advanced by a **villain clock** that drifts the world
forward on a baseline and spikes reactively — all expressed through the systems that
already exist. This spec **pilfers that machinery** and adapts it to the Gilded Machine so
that a played century reads as one coherent, large chronicle.

## The one decisive simplification vs dndai

dndai suffered a **binding gap**: its LLM authored an arc full of invented proper nouns
(`elder_thorne`, `leech_hive`) that never matched the separately-generated world, so no
beat could ever advance. Its entire "cast materialization" subsystem exists to mint stable
IDs for invented entities and rewrite predicates onto them.

**The Gilded Machine has no binding gap.** Its entities already exist with stable IDs from
turn one: houses keyed by `name` (`gilded/houses.py`), provinces by `pid`
(`gilded/world.py`), characters by `id` (`gilded/society/characters.py`). The Director
never invents entities — it **selects** real ones and binds a story symbol to them (e.g.
`@rival → "Karsgate"`). Cast "materialization" collapses to a one-line lookup. This makes
the whole adaptation dramatically lower-risk than dndai's, and it means the Director can be
**fully deterministic**: it reads real state and real events, and every choice it makes is
tie-broken by stable id.

---

## Design Principles (locked)

- **The sim is authoritative; the Director only observes and narrates.** The Director never
  mutates house/province/character/enterprise/war/tide state. It reads the turn's
  `TurnEvent`s and game state, writes its own durable **facts**, advances **beats**, and
  emits **chronicle** `TurnEvent`s and (optionally) LLM prose. The century plays out
  identically with the Director removed.
- **Structure is deterministic; only prose calls the model.** Facts, beats, predicates,
  the three beat-sources, and the chronicle event lines are pure deterministic Python.
  *Only* the optional narration layer calls the local model, at the display boundary,
  behind an interface whose fallback is today's templated text. Determinism/soak/headless
  tests keep passing untouched.
- **Never perturb the existing RNG stream.** The Director must not consume from
  `game.rng`. Existing golden/soak/stability tests assert outcomes off that stream; shifting
  it by one draw would break them. The Director uses a **separate** `Random` seeded from
  `game.seed` and, wherever possible, makes choices deterministically from state
  (tie-broken by id) rather than drawing at all.
- **Two-tier beats.** *Load-bearing* beats advance only via deterministic predicates over
  facts/turn/tide — mechanically guaranteed. *Soft* beats are atmosphere: their foreshadow
  text is injected into narration context but they gate nothing.
- **One Director, three beat-sources, one chronicle.** The Age, the Rival, and the
  Chronicle are three producers of beats feeding a single Director and a single narrated
  broadsheet — not three separate systems.
- **Deterministic floors over prompted hope** (inherited from dndai): every guaranteed beat
  advances through a typed fact the engine writes, never through hoping the model emits the
  right string.
- **On by default, toggleable, degrade to templated — never to nothing.** In the player
  app the LLM narrator is on by default; if the model is unreachable or disabled it falls
  back to today's templated broadsheet text, not to blank.

---

## Architecture overview

```
                gilded.chassis.GildedGame.end_turn()
  steps 0–8 (existing systems resolve) → self.events: List[TurnEvent]
                              │
                              ▼  NEW step 8.5 (deterministic Director pass)
        ┌─────────────────────────────────────────────────────────┐
        │  Director.observe(game)                                  │
        │   1. facts_from_turn(game) → durable WorldFacts          │
        │   2. tick three beat-sources → new/updated beats         │
        │        (C) Age    (A) Rival    (B) Chronicle             │
        │   3. advance(): eval predicates over facts → complete    │
        │        beats, open successors, fire payoffs              │
        │   4. emit chronicle TurnEvents into game.events          │
        └─────────────────────────────────────────────────────────┘
                              │
   step 9 (existing): turn++, endings, open_turn()
                              │
                              ▼  display boundary (papers.compose / ui.app)
        Narrator.render(report, director, game)   ← ONLY LLM call site
          NarratorTemplated (default, deterministic) → today's text
          NarratorLLM (local Qwen3.6)  → one coherent chronicle prose
```

The Director object lives on `GildedGame` (like `tide`, `scheme_mgr`, `marriages`). Its
state is picklable (plain dataclasses / dicts) so it rides the existing save/load path
(`console.cmd_save` drops the docket then pickles; the Director adds no un-picklable
fields).

---

## Section 1 — World facts (the durable substrate)

### `gilded/saga/facts.py`

A **WorldFact** is a durable, typed statement the story can read, distinct from the
transient `TurnEvent` (which is display text for one turn). Facts persist for the whole
century.

```python
@dataclass(frozen=True)
class WorldFact:
    turn: int              # when written
    subject_kind: str      # "house" | "province" | "character" | "world"
    subject_id: str        # house name | str(pid) | character id | ""  (world)
    predicate: str         # canonical verb, e.g. "went_to_war", "suffered_famine",
                           #   "committed_atrocity", "lost_ruler", "reached_tide_phase"
    object: str = ""       # optional target/qualifier, e.g. other house name, phase
    magnitude: float = 0.0 # optional scalar (atrocity weight, war score, etc.)
```

`FactStore` (also in `facts.py`) holds `List[WorldFact]` plus indexes for fast predicate
evaluation:
- `by_subject: Dict[(kind, id), List[WorldFact]]`
- `by_predicate: Dict[str, List[WorldFact]]`

`FactStore.add(fact)` appends and updates indexes. `FactStore.exists(predicate, *, subject=None, object=None, since_turn=None) -> bool` and `FactStore.count(...) -> int` are the primitives predicates use. Facts are **append-only**; nothing is ever mutated or deleted (a house can `went_to_war` many times — each is its own fact with its own turn).

### `facts_from_turn(game) -> List[WorldFact]`

A **pure** function (module-level, unit-testable with a stub game) that reads the turn's
`game.events` **and** post-resolution game state and returns the facts implied. It is the
Gilded analogue of dndai's `factsFromEvent`, but it reads the deterministic sim record
rather than typed engine triggers, because the sim already resolved everything. Wired
sources (all already produced by the existing loop):

| Fact predicate | Derived from | subject / object / magnitude |
|---|---|---|
| `went_to_war` | new entries in each `house.at_war_with` vs last turn (tracked on Director) | subject=aggressor house, object=defender house |
| `made_peace` | `negotiate_peace` gazette events / war removed from `game.wars` | subject=house, object=house |
| `committed_atrocity` | `game.tide.house_atrocities` delta this turn | subject=house, magnitude=weight |
| `suffered_strike` | province `movement.state == "striking"` newly true | subject=province pid |
| `suffered_revolution` | `game.fallen[h] == "revolution"` newly set | subject=house |
| `transformed` | `game.fallen[h] == "transformed"` newly set | subject=house |
| `lost_ruler` | realm.ruler changed this turn (step 4 succession) | subject=house, object=new ruler id |
| `dynasty_extinct` | no living characters in a realm | subject=house |
| `reached_tide_phase` | `game.tide.phase()` changed vs last recorded | subject="" world, object=phase |
| `scandal` | gazette events matching scandal markers | subject=house |
| `founded_enterprise` / `expanded_enterprise` | ledger "completes its works" events | subject=house, object=enterprise name |
| `treasury_leader` | house with max `_house_wealth`-style treasury (recomputed) changed | subject=house |

To detect deltas without perturbing anything, the Director snapshots the small set of
scalars it watches (`at_war_with` sets, `house_atrocities`, `fallen`, ruler ids, tide
phase, treasury-leader) at the end of each `observe()` and diffs on the next call. The
snapshot lives on the Director and is picklable.

**Determinism note:** `facts_from_turn` reads only already-resolved state and the current
turn's events; it draws no randomness and mutates no game state.

---

## Section 2 — Beats & predicates (the spine language)

### `gilded/saga/beats.py`

```python
@dataclass
class Predicate:
    kind: str          # "fact_exists" | "turn_reached" | "tide_reached" | "all" | "any"
    # fact_exists:
    predicate: str = ""; subject_kind: str = ""; subject_id: str = ""; object: str = ""
    min_count: int = 1
    # turn_reached: turn:int   tide_reached: level:float
    turn: int = 0; level: float = 0.0
    # all/any:
    parts: List["Predicate"] = field(default_factory=list)

def eval_predicate(pred: Predicate, facts: FactStore, game) -> bool: ...
```

`eval_predicate` mirrors dndai's `evalPredicate` but over the Gilded FactStore. `all`/`any`
compose arbitrarily, so the completion-condition space is effectively unbounded even though
the leaf kinds are few. `subject_id` may be the literal `"@self"` — resolved against the
beat's bound cast symbol at eval time (see Rival, §4.A), so a Rival beat template can say
"the Rival went to war" without hardcoding a house name.

```python
@dataclass
class Beat:
    bid: str                     # stable id, e.g. "age_socialist", "rival_first_blood"
    source: str                  # "age" | "rival" | "chronicle"
    title: str                   # named, player-facing: "The Red Decade Dawns"
    load_bearing: bool           # True → advances only via completion predicate
    completion: Optional[Predicate]
    foreshadow: str = ""         # soft vocabulary injected into narration context
    payoff: str = ""             # chronicle line emitted on completion
    cast: Dict[str, str] = field(default_factory=dict)  # symbol → real id, e.g. {"self":"Karsgate"}
    state: str = "pending"       # "pending" | "active" | "complete"
    opened_turn: int = 0; closed_turn: int = 0
    next_bids: List[str] = field(default_factory=list)  # successors opened on completion
```

Soft beats (`load_bearing=False`, `completion=None`) never gate; they exist to color
narration and are closed by their source's own logic (e.g. an Age era ends when the next
era opens).

### `gilded/saga/director.py`

```python
class Director:
    def __init__(self, seed: int):
        self.rng = random.Random(seed ^ 0x5A6A)   # dedicated; never game.rng
        self.facts = FactStore()
        self.beats: Dict[str, Beat] = {}
        self.active: List[str] = []                # currently-active bids
        self.snapshot = {}                         # delta-detection state (see §1)
        self.rival: Optional[str] = None           # bound rival house name
        self.age_idx = -1                           # index into the era ladder
        self.threads: Dict[str, str] = {}          # chronicle thread bid → phase

    def observe(self, game) -> List[TurnEvent]:
        new_facts = facts_from_turn(game)          # §1
        for f in new_facts: self.facts.add(f)
        events = []
        events += self._tick_age(game)             # §4.C
        events += self._tick_rival(game)           # §4.A
        events += self._tick_chronicle(game)       # §4.B
        events += self._advance(game)              # complete beats, open successors
        self._resnapshot(game)
        return events

    def _advance(self, game) -> List[TurnEvent]:
        out = []
        for bid in list(self.active):
            b = self.beats[bid]
            if b.load_bearing and b.completion and eval_predicate(b.completion, self.facts, game):
                b.state = "complete"; b.closed_turn = game.turn
                self.active.remove(bid)
                if b.payoff: out.append(TurnEvent(b.payoff, "gazette"))
                for nb in b.next_bids: self._open(nb, game)
        return out
```

`observe()` returns chronicle `TurnEvent`s that the chassis appends to `game.events`, so
`papers.compose` surfaces them with zero further wiring. It is the single call the chassis
adds.

---

## Section 3 — Wiring into the chassis (one seam)

`GildedGame.__init__` constructs `self.director = Director(seed)` after `self.tide`.
`GildedGame.end_turn` inserts one call as **step 8.5**, after step 8 (revolution checks)
and before step 9 (turn increment / endings), so the Director sees the fully-resolved
turn:

```python
        # 8.5 the Director reads the resolved turn and chronicles it
        self.events.extend(self.director.observe(self))
```

That is the entire structural change to the existing engine. Because `observe()` is
deterministic and appends only after all systems have run, existing determinism, soak, and
stability tests are unaffected in their *state* assertions. Tests that assert an **exact
event list** would see extra chronicle lines — the plan audits `test_papers.py` /
`test_soak.py` and updates any exact-list assertions to allow the new lines (they assert
substrings/counts, per the codebase's existing style; the plan verifies this before
touching them).

The Director is also constructed for AI-only games (no player house), so a headless
AI-run century still produces a saga (the shakedown harness reads it).

---

## Section 4 — The three beat-sources

### (C) The Age — named eras promoted from the tide

The century already has a single rising meter: `game.tide` (`IdeologicalTide`, `level`
0–100, `phase()` → `reformist | socialist | revolutionary`). The Age turns that scalar into
a ladder of **named, authored eras**, each a soft backdrop beat with a load-bearing
*dawn* — the era opens deterministically when the tide crosses its threshold or the turn
clock reaches it (whichever first), guaranteeing every century marches through the ladder.

An authored constant ladder in `gilded/saga/content/eras.py`:

```python
ERAS = [
  Era("age_gilded",   "The Gilded Peace",   tide=0.0,  turn=1,
      foreshadow="smoke on the horizon, order still holding"),
  Era("age_reform",   "The Reforming Wind", tide=33.3, turn=18,
      foreshadow="petitions harden into demands"),
  Era("age_red",      "The Red Decade",     tide=66.6, turn=45,
      foreshadow="the barricades are spoken of openly"),
  Era("age_reckoning","The Reckoning",      tide=90.0, turn=63,
      foreshadow="the old order counts its last days"),
]
```

`_tick_age(game)` finds the highest-index era whose `tide` OR `turn` threshold is met;
if it exceeds `self.age_idx`, it closes the prior era beat, opens the new one (emitting its
`payoff` chronicle line, e.g. *"The Red Decade dawns over the continent."*), and advances
`age_idx`. Eras are the load-bearing floor of the saga: they can never stall (the tide
rises every turn by `TIDE_BASE_RISE`, and the turn clock always advances), so the spine is
guaranteed to progress even in a passive game. Era `foreshadow` is the base atmosphere layer
injected into every narration.

### (A) The Rival — an AI house promoted to a tracked antagonist

At a chosen turn (default: end of turn 1, so the antagonist is present from the start), the
Director **promotes** one AI house to the Rival and binds `@self` to its real name. Selection
is deterministic from state — the AI house that is the strongest *and* most divergent from
the player (highest `_strength`, tie-broken by name), or, in an AI-only game, simply the
strongest — so no `game.rng` draw is needed and the pick is reproducible.

The Rival is **not a new actor**: the promoted house keeps playing the same deterministic AI
loop (`ai.py`) on the same levers. The Rival source is a **narrative tracker** over that
house's real, already-happening deeds, plus an optional *villain clock* that raises the
stakes without cheating:

- **Rival arc beats** (`gilded/saga/content/rival_arc.py`) are templates whose predicates
  key off facts about `@self`: e.g. `rival_first_blood` completes on
  `fact_exists(went_to_war, subject=@self)`; `rival_ascendant` on `@self` becoming
  `treasury_leader`; `rival_bloody_hands` on `count(committed_atrocity, subject=@self) ≥ 3`;
  `rival_menace` on `@self` reaching a war score / province count. Each opens the next,
  giving the Rival a rising three-to-four beat arc with foreshadow and payoff.
- **Villain clock (baseline + spike), expressed only through existing channels:** the clock
  never invents a surface. Baseline: every `RIVAL_CLOCK_TURNS` turns the Director may nudge
  the Rival's **directive stances** toward ambition/war *by writing them through the same
  `Directives.set_stance` the AI already uses* — a legal move the AI itself could make, not a
  state cheat, and applied *before* the Rival's own `ai_turn` so its behavior stays
  self-consistent. Reactive spike: when a fact shows the player threatening the Rival
  (declared war on it, out-earned it), the clock advances the Rival arc's foreshadow and can
  bring the next beat's threshold forward. If nudging directives proves too invasive for the
  determinism budget, the clock degrades to **pure narration pressure** (foreshadow
  escalation only) — decided during implementation behind a flag; the arc still advances off
  the Rival's real deeds regardless.

Binding is a one-liner (`cast={"self": rival_name}`); there is no `arc_cast` table, no
symbol-rewrite pass, no nullable ids — the house already exists.

### (B) The Chronicle — emergent named threads with foreshadow & payoff

The Chronicle scans the FactStore each turn for **patterns** that deserve to become named
threads, promotes them, and resolves them at payoff. Threads are the emergent, per-playthrough
texture that makes each century feel authored. A thread is a small deterministic detector +
a payoff predicate; detectors live in `gilded/saga/content/threads.py`:

| Thread | Promoted when | Payoff when |
|---|---|---|
| `thread_famine_<pid>` | a province's unrest/strike facts cross a threshold | strike ends / revolution / peace restored there |
| `thread_succession_<house>` | `lost_ruler` with a contested/young heir (from realm state) | line stabilizes N turns, or dynasty_extinct |
| `thread_feud_<a>_<b>` | two houses accrue mutual `went_to_war` / negative relations | `made_peace` between them, or one falls |
| `thread_scandal_<house>` | repeated `scandal` / `committed_atrocity` on one house | legitimacy recovers, or revolution/transform |

Promotion is deterministic (threshold crossing, tie-broken by id) and capped
(`MAX_ACTIVE_THREADS`, e.g. 3) so the chronicle stays legible: if more patterns qualify than
the cap, the highest-magnitude ones win, ties by id. Each promoted thread opens a beat with
`foreshadow` (injected while active) and a `payoff` chronicle line emitted on resolution. A
thread that never resolves by century's end is handed to the endings layer (§6) as an
"unresolved thread" — deliberately, so an epilogue can name what was left hanging.

---

## Section 5 — The narration layer (the only model call)

### `gilded/saga/narrator.py`

```python
class Narrator(Protocol):
    def render(self, report: TurnReport, director: Director, game) -> TurnReport: ...
```

`render` takes the composed `TurnReport` (§`papers.compose`) plus the Director's active
beats/facts and returns a `TurnReport` — it may rewrite/augment the prose but returns the
same structured shape the UI already consumes. It is **display-only**: it never touches
`game` state, and it runs at the compose/UI boundary, *after* the deterministic turn is
fully recorded.

- **`NarratorTemplated`** (default, deterministic): returns the report unchanged — i.e.
  today's exact broadsheet. This is the guaranteed fallback and the narrator used in every
  automated test, so determinism/soak/headless suites are byte-for-byte unaffected.
- **`NarratorLLM`** (opt-in, player app default-on): calls the **local Qwen3.6** model (the
  same server CynCo uses — model server on `:11434`, llama.cpp direct) with a prompt built
  from: the active Age era + Rival beat + open Chronicle threads (their `foreshadow`), the
  turn's gazette/ledger/letters lines, and the reading house's identity. It returns a single
  coherent chronicle paragraph (or a lightly-rewritten gazette) that ties the turn's events
  to the standing threads. **No grammar/GBNF and no `decide()` call** — the sim already
  adjudicated, so narration is pure prose (`narrate`-style, temperature ~0.7). Local-model
  gotchas from the dndai ledger apply: send `chat_template_kwargs:{enable_thinking:false}`
  (else an open `<think>` burns the budget) and warm the model once before the first call.
  On any error/timeout/unreachable model it falls back to the templated report — **never to
  blank** (no silent *degradation*, but graceful *fallback*; the distinction from dndai's
  "fail loud" is deliberate — this is a single-player desktop toy, not a GPU pipeline).

### Selection & toggling

`GildedGame` does **not** own the narrator (keeping the sim model-free). The narrator is a
UI/console concern: `gilded/ui/app.py` and `gilded/console.py` construct a narrator —
`NarratorLLM` by default, `NarratorTemplated` when `GILDED_NARRATE=0` or the model is
unreachable — and pass the composed report through `narrator.render(...)` before display. A
UI toggle (a Broadsheet control, e.g. a key/button) flips between them live. Because the sim
never holds the narrator, no test path can accidentally invoke the model.

---

## Section 6 — Endings integration

`gilded/endings.py::judge` gains a fifth, narrative strand without disturbing its four
axes: the epilogue names the **age the house lived and died in** (the final Age era), its
**defining antagonism** (the Rival arc's furthest-reached beat — did the Rival fall, win, or
outlast the house?), and its **unresolved threads** (Chronicle beats still open at the
close). This is deterministic text assembled from the Director's final state, appended as a
short coda to the existing four-paragraph epilogue — so the century *closes a story*, not
just a ledger. `judge` reads `game.director` (available since it now lives on the game);
when the Director is absent (older saves) the coda is skipped and the epilogue is exactly
today's.

---

## Section 7 — Testing strategy

Mirrors dndai's tiers, adapted to the Gilded Machine's pytest suite (baseline: `1 failed,
291 passed`; the one failure is the pre-existing `test_civkings.py` stability test,
unrelated).

### Tier 1 — Unit (pure, fast, deterministic)
- `facts_from_turn`: table-driven — a stub game/events in, expected `WorldFact`s out; covers
  war/peace/atrocity/strike/succession/tide-phase/scandal, no-match, and multi-fact turns.
- `eval_predicate`: `fact_exists`/`turn_reached`/`tide_reached`/`all`/`any`, including
  `@self` cast resolution and `min_count`.
- Director `_advance`: a beat with a satisfied predicate completes, emits payoff, opens
  successors; an unsatisfied one stays active.
- Age ladder: given tide/turn inputs, assert the correct era opens once and only once.
- Rival selection: deterministic pick given a stub roster; stable under reordering.
- Chronicle promotion: threshold crossing promotes exactly the capped set, tie-broken by id.

### Tier 2 — Integration (the real engine, headless, templated narrator)
- Construct a real `GildedGame(seed=…)`, run the full century via `end_turn()`, assert:
  the Age ladder advanced through all four eras; a Rival was bound and its arc advanced ≥1
  beat; ≥1 Chronicle thread promoted and ≥1 resolved; every emitted chronicle `TurnEvent`
  references a real bound entity (no dangling symbols).
- **Determinism guard:** two runs at the same seed produce identical Director final state
  and identical chronicle event streams (proves no `game.rng` perturbation, no wall-clock,
  no model).
- **Non-perturbation guard:** a century run *with* the Director produces the same
  house/province/tide/ending **state** as one with `observe()` stubbed out — the Director
  changes the *record*, never the *outcome*. (The one intentional exception, if the Rival
  villain-clock directive-nudge is enabled, is asserted explicitly and gated by its flag;
  with the flag off, state is identical.)

### Tier 3 — Watchable saga artifact (acceptance centerpiece)
The Gilded analogue of dndai's storybook, adapted to a desktop toy: a harness
(`C:/tmp/gilded_saga_run.py`, mine — not committed) plays a full century headless, then
runs **`NarratorLLM`** over each turn's report and writes a scrollable **saga** — one
chapter per Age era, each turn showing (1) what happened (the chronicle lines), (2) the
standing threads/antagonist, and (3) the LLM prose tying them together — ending with the
epilogue coda. The acceptance bar: a human reads the century start-to-finish and it feels
like *one large, coherent story with a named age, a rival, and threads that pay off* — the
original complaint, answered. (Automated suites use the templated narrator and never gate on
the model; the LLM artifact is a human read, run on demand.)

---

## New / changed files

**New (all under `gilded/saga/`, a self-contained package):**
- `facts.py` — `WorldFact`, `FactStore`, `facts_from_turn(game)`.
- `beats.py` — `Predicate`, `eval_predicate`, `Beat`.
- `director.py` — `Director` (observe / tick sources / advance / snapshot).
- `narrator.py` — `Narrator` protocol, `NarratorTemplated`, `NarratorLLM`.
- `content/eras.py` — the Age ladder.
- `content/rival_arc.py` — the Rival beat templates.
- `content/threads.py` — Chronicle thread detectors.
- `tests/test_saga_facts.py`, `test_saga_beats.py`, `test_saga_director.py`,
  `test_saga_sources.py`, `test_saga_integration.py`, `test_saga_narrator.py`.

**Changed:**
- `gilded/chassis.py` — construct `self.director`; add the one step-8.5 `observe` call.
- `gilded/endings.py` — the narrative coda in `judge`/`_epilogue_text`.
- `gilded/console.py` and `gilded/ui/app.py` — construct a `Narrator`, pass the composed
  report through `render`; env/toggle selection. (`gilded/ui/broadsheet.py` — a narrator
  toggle control.)
- `gilded/tests/test_papers.py`, `test_soak.py` — audit exact-event assertions; relax to
  substring/count where the new chronicle lines would otherwise fail them (verified before
  changing).

---

## Staged implementation (for writing-plans → CynCo waves)

Each wave produces working, independently-testable software and is one (occasionally two)
byte-exact CynCo mission(s), verified with the 5-check protocol against the devtree scratch
worktree, keeping the pytest baseline at `1 failed`.

- **Wave N1 — Facts & spine (deterministic core):** `facts.py`, `beats.py`, `director.py`
  skeleton (`observe`/`_advance`/snapshot, no sources yet), the chassis step-8.5 wiring, and
  the papers/soak assertion audit. *Deliverable: durable facts accrue and beats advance;
  the century plays identically in state; all tests green.*
- **Wave N2 — The three beat-sources:** `content/eras.py` + `_tick_age`; Rival promotion +
  `content/rival_arc.py` + `_tick_rival` (villain clock behind its flag); `content/threads.py`
  + `_tick_chronicle`. *Deliverable: a run produces an advancing Age ladder, a bound Rival
  arc, and promoting/resolving Chronicle threads — the integration + determinism guards
  pass.*
- **Wave N3 — Narration layer:** `narrator.py` (templated + LLM), console/app/broadsheet
  wiring and toggle. *Deliverable: the broadsheet reads as one chronicle with the LLM on;
  templated fallback keeps every test byte-identical.*
- **Wave N4 — Endings coda + saga artifact:** the `judge` narrative coda and the
  `gilded_saga_run.py` acceptance harness. *Deliverable: the century closes a story; a human
  can read the whole saga.*
