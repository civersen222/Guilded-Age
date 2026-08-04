# Gilded — The Interaction Model

> **STATUS: APPROVED 2026-08-03.** The spine and all four models were presented
> and approved in conversation before this document was written. No wave may be
> briefed until §7's wave split is read back, but the design itself is settled.

**What this is:** a cross-cutting specification that Stages 5–8 of the experience
roadmap are all required to conform to. It is not a stage. It defines *how the
player touches this game*, once, so that four domain stages consume one
interaction language instead of inventing four.

**Base:** `28f57e7` on `master`. Gilded suite floor at time of writing: **1261
passed** (Wave 19 delivery; gate result pending at authoring time — see §9.3).

**Roadmap position:** the 8-stage experience redesign is
1 Frame · 2 Living Adversaries · 3 Policy dials · 4 Enterprises · 5 Court &
Dynasty · 6 Diplomacy & War · 7 Initiatives · 8 Consequence & polish.
Stages 1–4 have landed. This document precedes Stage 5 and binds 5 through 8.

---

## 1. The finding this document is built on

Four independent inventories were run on 2026-08-03 — `gilded/society/` (the
Stage 5 draft, 2026-07-31), diplomacy/war, the action economy, and the
consequence/chronicle layer. They examined unrelated subsystems and returned the
same verdict four times:

> **The simulation is rich, the player-facing surface is empty, and the wire
> between them was never run.**

This is the precise shape of the complaint that started the whole redesign. The
game was called opaque and shallow. It is not shallow. It is **mute**.

### 1.1 The four faces of the defect

| Domain | What the sim does every turn | What the player sees |
|---|---|---|
| Court & Dynasty | recomputes every councillor's loyalty; docks passed-over kin −15..−30 opinion; lists disloyal shareholders | six names |
| Diplomacy & War | front line, entrenchment, regiments, supply, casualties, war score | a red line on the Atlas |
| Action economy | 15 initiative verbs, fully implemented | 3 of them reachable |
| Consequence | every meter's causes are known at the moment they apply | bare numbers |

### 1.2 The measured particulars

Every claim below was verified directly against the tree at `28f57e7`. Claims
that were *not* personally verified are segregated into §9.2 and are not relied
on by this design.

**The input layer has no pointer.** `gilded/ui/app.py:170-183` handles exactly
two event types — `KEYDOWN` (`:173`) and `MOUSEBUTTONDOWN` (`:180`). There is no
`MOUSEMOTION` handling anywhere in `gilded/ui/`. No hover, no tooltip, no cursor
feedback, no mechanism by which a control can explain why it is unavailable.

> **Corrigendum, 2026-08-03, after Wave I2c.** This section called these five
> "dead buttons" and said the player clicks them into silence. **That is wrong,
> and the truth is worse.** They are never drawn. `_draw_enterprises` filters
> the offers twice before rendering: `if eid is None: continue` discards
> `found_enterprise` and `attack_takeover` outright, and the `if verb ==
> "expand_enterprise" / elif verb == "appoint_director"` chain has no arm for
> `buy_shares`, `sell_shares` or `defend_buyout`, so they fall out silently. A
> live game at seed 42 offers ten actions with finished player-facing labels —
> "Buy Shares in Ferdale Ironworks", "Hostile Takeover of Vantrell" — and draws
> exactly four of them.
>
> So the defect is not a button that lies. It is an offer the game computes,
> labels, prices, and throws away without ever showing it. The player is not
> misled; they are *never told the option exists*. Read against this document's
> own bar — "nothing is ever unexplained" — that is a worse failure than a dead
> button, because a dead button at least admits the verb is supposed to exist.
>
> This was found by Wave I2c's coverage check, which walks the drawn hit
> structures and, once its unwrapping was corrected, collected eleven real keys
> and **none of these five**. The table's `broadsheet.py:15xx` line numbers are
> the *emit* sites in `enterprise_actions()` and remain correct; what was wrong
> was the claim that emitting put them on screen. I asserted a rendering path I
> had not measured, and the measurement had been available the whole time.
>
> Consequences: Wave I4 must **draw** these controls, not merely wire them —
> and §4.2 check 1 must quantify over what the game OFFERS, not only over what
> it draws, or it can never see them. Both changes are recorded in the plan.

**The game ships dead buttons.** `gilded/ui/broadsheet.py:enterprise_actions()`
emits **five** action kinds that nothing can execute. The set was computed
mechanically as *emitted minus handled* rather than read off the screen:

| Emitted at | Action key | Handler in `app.py` | Verb in `INITIATIVES`? |
|---|---|---|---|
| `broadsheet.py:1561` | `buy_shares` | none | yes |
| `broadsheet.py:1562` | `sell_shares` | none | yes |
| `broadsheet.py:1564` | `found_enterprise` | none | yes |
| `broadsheet.py:1574` | `defend_buyout` | none | no |
| `broadsheet.py:1588` | `attack_takeover` | none | **no — nothing by that name exists anywhere** |

**`attack_takeover` is the worst thing in this document.** It is emitted by the
Powers tab, handled by nothing, and corresponds to no verb in `INITIATIVES` —
the nearest real verb is `start_takeover`. It is not a button that stopped
working; it is a button that never could have worked, under a name the
simulation has never heard of.

It is nonetheless defended by **five tests** in `test_ui_broadsheet.py`
(`:439`, `:456`, `:463`, `:497`, `:1437`) asserting that it is offered, that it
names a rival, that it differs by seed, and that it targets the top threat. Every
one of them asserts the *emitter produced the dict*. Not one asserts that
anything can consume it.

This is the exact hollow shape this project has a standing rule about, found in
the wild at its purest: five green tests, a feature that has never once
executed, and a suite that would report no change if the whole path were
deleted. It is also the strongest possible argument for §4.2 check 1 — a single
coverage assertion catches all five of these at once, where five separate
feature tests caught none of them.

`app.py:_apply_action` (`:75-152`) handles eight keys and only eight:
`toggle_narrate`, `end_turn`, `place_informant`, `set_stance`, `rule`,
`expand_enterprise`, `close_director_picker`, `appoint_director`. Clicking any of
the five above produces no action, no error and no feedback.

**The root cause is that there is no shared registry.**
`broadsheet.py:1811 handle_click` is a hand-written cascade of per-tab `if`
blocks, each consulting its own ad-hoc hit structure. **There are eleven**,
populated at eleven different places and cleared at two:

| Structure | Populated | Shape |
|---|---|---|
| `_tab_rects` | `:840,843` | `dict[str, Rect]` |
| `_narrate_rect` | `:899` | bare `Rect` |
| `_end_turn_rect` | `:904` | bare `Rect` |
| `_option_hits` | `:1006` | `list[(Rect, tuple)]` |
| `_exec_hits` | `:1017` | `list[(Rect, pid)]` |
| `_dial_hits` | `:1322` | `list[(Rect, key)]` |
| `_atlas_polys` | `:1364` | polygons, hit via `pick_province` |
| `_informant_hits` | `:1457,1470` | `list[(Rect, dict)]` |
| `_enterprise_hits` | `:1713` | `list[(Rect, dict)]` |
| `_appoint_hits` | `:1730` | `list[(Rect, dict)]` |
| `_director_picker_hits` | `:1753,1778` | `list[(Rect, dict)]` |

Five different shapes across eleven structures, each convention invented
separately. The emitter and the handler share no contract, so the five dead
buttons are the arithmetic difference between two lists that nothing compares.

**Corrigendum.** An earlier revision of this document said *seven*. It was
counting the names visible in the `handle_click` cascade and missed the two bare
rects and two of the Enterprises lists. The number was recounted mechanically
over the file rather than read off the screen. Recorded rather than quietly
edited, because this document's authority rests on §9 and a spec that silently
repairs its own measurements is not evidence.

**Twelve of fifteen initiative verbs are unreachable from the UI.**
`gilded/docket.py:837-853` declares `INITIATIVES` with fifteen entries. Exactly
three are dispatchable from `app.py`: `expand_enterprise`, `appoint_director`,
`establish_informant`. The other twelve — `propose_marriage`,
`found_enterprise`, `build_rail`, `start_scheme`, `tour_province`,
`adjust_garrison`, `acquire_minor`, `declare_war`, `negotiate_peace`,
`start_takeover`, `buy_shares`, `sell_shares` — are reachable only from the text
console.

**Commanders have never existed in a real game.** `Front.commander_a_id` and
`commander_d_id` are declared at `gilded/fronts.py:52-53`. The function that
assigns them, `fronts.appoint()` at `:142`, is imported by **no game code** —
`docket.py:22-24` imports six names from `gilded.fronts` and `appoint` is not
among them; no other module imports it. Only `gilded/tests/test_fronts.py`
reaches it. Therefore `resolve_front` calls `_find_commander(game, "")` at
`:247-248` on every battle, and the commander-temperament path has never once
executed outside a test. This is the same shape as `Character.is_heir`
(declared, never assigned) that the Stage 5 draft found — the second instance of
the pattern in three days.

**The revolution countdown is a secret.** `chassis.py:89` declares
`brewing_turns`; it is written at `:357-362` and read at `:360`. It appears in
**no** UI file. The revolution fires on the third consecutive qualifying turn.
The player receives no warning that the count began.

**Causes are computed and discarded.** `society/characters.py:333-338`
`modify_opinion` mutates the opinion matrix and *returns* a formatted sentence
containing the reason; **36 non-test call sites discard the return value.**
`dashboard.py:MetricDelta` is `(change: float, direction: int)` — no cause field
exists. `society/ideology.py:85-97 tick_legitimacy` applies three concurrent
forces — contentment (a recovery **or** a drain; the arms are an `if/else` and
cannot both fire), atrocity drain, tide drain — and then **silently clamps** to
`0.0 .. LEGITIMACY_MAX` at `:97`. All of it returns as one float, which
`chassis.py:349` stores as a bare number. The clamp is the worst of the four: a
meter that stops falling with no explanation reads to the player as the game
lying.

**The attention economy is flat.** `chassis.py:37 ATTENTION_PER_TURN = 3`, reset
each turn at `:162`, never scaled anywhere. `TURN_BUDGET = 70` (`:45`). The
docket generates up to `MAX_PETITIONS = 6` (`docket.py:33`); ruling three
consumes the entire turn's attention. Unattended petitions with no seated
minister auto-resolve after `FESTER_TURNS = 2` (`docket.py:32`, `:585`).

### 1.3 What follows from this

The four remaining stages are not four design problems. They are one integration
defect with four faces. Fixing it per-stage would fix it four times and permit it
to regrow a fifth. This document therefore defines four models, and Stages 5–8
consume them.

---

## 2. The Pointer model

*Serves: "input always answers."*

### 2.1 Structure

One registry of interactive regions, populated during draw, in
`gilded/ui/widgets.py`.

```
RegionState  ENABLED      the player may do this now
             DISABLED     the player could do this, but not right now, and
                          the game knows why — `reason` is required
             ACTIVE       currently selected (the open tab, the chosen option)
             UNAVAILABLE  this does not apply to this player at all — a
                          foreign House's internal control, a verb this
                          House can never take. No `reason`, because there
                          is no condition that would turn it on.

Region       rect:    pygame.Rect
             action:  dict | None
             state:   RegionState
             reason:  str        why DISABLED — required when state is DISABLED
             hint:    str        what this does and what it costs
             group:   str        owning tab or panel

RegionSet    add(region) -> None
             at(pos) -> Region | None
             clear() -> None
```

`handle_click(pos)` becomes `regions.at(pos)` and returns that region's action.
Hover becomes `regions.at(mouse_pos)` driven by a new `MOUSEMOTION` branch in
`app.py:step_once`. The two paths consult the identical structure, so a thing
that can be hovered is by construction a thing that can be clicked.

### 2.2 Rules

1. A region drawn in the ENABLED style **must** carry a non-`None` action.
2. A region carrying an action **must** be dispatchable. §4 supplies the other
   half of this guarantee; neither model closes the hole alone.
3. `state == DISABLED` with an empty `reason` is a **test failure**, not a
   default. This is the entire silent-refusal class of defect.
4. A click on a DISABLED region surfaces its `reason`. It never does nothing.
5. The eleven ad-hoc hit structures in `broadsheet.py` migrate to the registry.
   They may be migrated one tab at a time; a partially migrated tree must still
   pass.
6. **Three emitted keys are view-local**, not game actions: `tab`,
   `select_province`, `open_director_picker`. `handle_click` mutates the view
   and returns them; `_apply_action` receives them and does nothing. They are
   not dead buttons — the click already worked. They are nonetheless *emitted
   keys*, so §4's registry must carry them with `domain == "view"` rather than
   exempt them. An exemption clause is how the four real dead buttons survived;
   the registry gets no escape hatch.

### 2.3 Why a registry rather than adding hover per tab

Adding hover to each tab's existing hit list would produce seven hover
conventions to match the seven click conventions, and would leave the emitter /
handler contract exactly as unenforceable as it is now. The registry is the only
form in which rule 2 is checkable.

---

## 3. The Provenance model

*Serves: "nothing is ever unexplained."*

### 3.1 Structure

**New:** `gilded/provenance.py` — a pure data module, no simulation, no
`game.rng`, frozen dataclasses.

```
Cause        label:  str      "Tide pressure"
             amount: float    -0.53
             source: str      "ideology.tick_legitimacy"

Attributed   value:     float
             previous:  float
             causes:    tuple[Cause, ...]
             delta -> float                 (value - previous)
```

### 3.2 The rule that gives it teeth

`sum(c.amount for c in causes)` must equal `delta` within `1e-6`.

The tolerance is stated as a number, not left to the implementer, because a
tolerance chosen after the fact is chosen to make the current code pass. `1e-6`
is float-noise on the scales these meters use (legitimacy 0–100, opinion in
integers); anything a player could see is far above it. If a real site cannot
meet it, that is a finding to raise — not a licence to widen the bar.

Without this the model degrades into a decorative label: a number could fall by
3.1 while its stated causes account for 2.4 and nobody would know. The sum check
makes an incomplete explanation a failing test rather than a rounding shrug.

### 3.3 The four sites

| Site | Today | Required |
|---|---|---|
| `society/ideology.py:85-97 tick_legitimacy` | three concurrent forces + a silent clamp → one float | three named `Cause`s, plus a clamp cause when `:97` bites — without it the causes sum to more than the delta and §3.2 fails, correctly |
| `dashboard.py MetricDelta` | `change`, `direction` | + `causes` |
| `society/characters.py:333-338 modify_opinion` | reason returned, discarded at 36 call sites | reason appended to a bounded per-character ledger |
| `chassis.py:89,357-362 brewing_turns` | never rendered | a visible countdown naming both preconditions |

`brewing_turns` is the highest-priority single item in this document. A
revolution that arrives unannounced, after a three-turn counter the game kept
secret, is the most player-hostile behaviour any of the four inventories found.

### 3.4 Scope discipline

This model **reports** numbers. It does not **rebalance** them. No formula may
change under this work. A legibility pass that quietly alters behaviour destroys
the ability to attribute any later change, and balance belongs to Stage 8 where
it can be argued on its own evidence.

---

## 4. The Affordance model

*Serves: "the screen teaches itself."*

### 4.1 Structure

**New:** `gilded/ui/actions.py` — one declared registry both sides read.

```
PlayerAction   key:            str
               label:          str
               domain:         str
               attention_cost: int
               gold_cost:      Callable | int
               eligible(game, house, **kw) -> tuple[bool, str]
               dispatch(game, house, **kw) -> list[str]

ACTIONS: dict[str, PlayerAction]
```

`broadsheet` may emit only action keys present in `ACTIONS`. `app._apply_action`
dispatches **through** `ACTIONS` rather than through a hand-written cascade.
Adding a verb wires it everywhere at once.

`eligible()` returns its own refusal sentence, which feeds directly into the
Pointer model's `Region.reason`. The two models meet here: §2 rule 2 and §4's
registry are the same guarantee approached from the draw side and the dispatch
side.

### 4.2 The test that makes the defect extinct

At a fixture game:

1. **Coverage.** Every action key emitted by any tab is present in `ACTIONS`.
2. **Dispatchability.** For every key in `ACTIONS`, at a fixture constructed so
   that `eligible()` returns `True`, `dispatch()` runs to completion without
   raising and returns a list of strings. A key whose eligibility cannot be
   arranged at any fixture is not "hard to test" — it is unreachable in play,
   and §6 rule 4 applies: delete it, do not manufacture the input.

Check 1 **fails today, five times** (§1.2). That is a requirement of the
verification law in §6 — a new check that cannot fail at base measures nothing —
and it is satisfied here without contrivance.

**How a known-failing check lives in a green suite.** In I2 the registry covers
only the already-wired verbs, so check 1 still fails by five. It is committed in
I2 marked `xfail(strict=True)` with the five missing keys named in the reason
string. `strict` is what makes this honest: if I4's wiring lands and the check
starts passing, a `strict` xfail turns the suite **red** until the marker is
removed, so the marker cannot be forgotten and quietly go on excusing a defect
that no longer exists. I4 removes it. This is the only sanctioned xfail in this
work; a second one is a design smell to raise, not to add.

### 4.3 What this buys the surface

Because cost and eligibility are declared rather than implied, the UI can state
a price before commitment ("Found Enterprise · 1 attention · 250g") and render
an ineligible control greyed *with its reason attached*. Three of the four
polish bars fall out of one structure.

### 4.4 Explicitly not decided here

What three attention points *should* be; whether petitions and initiatives
should compete for one pool; whether the budget should scale across the century.
Those are Stage 7's design questions and they require the player to have played
a reachable game first. This document makes the verbs reachable and the costs
visible. It does not retune them.

---

## 5. The Type & Space model

*Serves: "it looks expensive."*

Least invention of the four; largely a promotion of what `gilded/ui/widgets.py`
already does into enforceable law.

1. **Semantic colour roles, not literal tuples at call sites.** `INK`, `FADED`,
   `PAPER_BG`, `CARD_BG`, `CARD_EDGE` exist at `widgets.py:21-25`. Add
   `POSITIVE`, `NEGATIVE`, `WARNING`, `DISABLED`, `HOVER`. A literal RGB tuple
   outside `widgets.py` is a lint failure.
   **Measured at `28f57e7`: 35 such literals exist** — 18 in `broadsheet.py`,
   17 in `atlas_view.py`, none anywhere else in `gilded/ui/`. The rule is stated
   as an absolute because the count is small enough to reach zero in one wave;
   the lint test therefore fails at base by 35 and passes only when the
   migration is complete, with no threshold to negotiate.
2. **A named type scale.** **Measured at `28f57e7`: 12 distinct sizes across 30
   literal `font(n)` calls** — 11, 12, 14, 15, 16, 17, 18, 19, 22, 24, 26, 30.
   Twelve sizes is not a scale, it is an accident. I6 collapses them to a named
   set with jobs (caption / body / lede / head / display is the expected shape,
   but the final set is chosen by mapping the 30 existing call sites onto the
   fewest sizes that no reviewer can tell apart on screen — derived from what is
   there, not invented and imposed).
3. **One spacing unit.** All padding and gaps are multiples of it.
   `MEASURE_CHARS = 66` (`:31`) and `COLUMN_GAP = 24` (`:32`) are the right
   instinct already; generalise rather than replace. The unit is likewise
   derived: pick the value that most existing paddings are already near, so the
   migration moves the fewest pixels. **A unit chosen before the current spacing
   is measured would silently redesign every screen under the banner of
   consistency**, which §3.4's discipline forbids for numbers and this section
   forbids for layout.
4. **`Meter`, `Chip` and `Panel` gain the §2 states** so the vocabulary is
   complete and no screen hand-rolls its own grey.
5. **Period discipline.** Ink on paper; rules and hairlines rather than drop
   shadows; small caps for headers; tabular figures for anything in a column.
   The 1900 broadsheet framing is the strongest art idea in the project and is
   currently under-committed to.

---

## 6. Verification law

Carried unchanged from the UI-legibility spec §9 and the S-series practice, and
non-negotiable:

1. **Assert the rule, not the constant.** A test hard-coding a threshold proves
   nothing about the rule that uses it.
2. **Assert at a fixture that can discriminate.** A fixture sitting on a
   default value cannot tell a rule from a constant. Two distinct non-default
   inputs, in the same file.
3. **A wave is accepted only when the repo's own tests go red under a withheld
   mutation set**, built after delivery and never shown to the implementer.
4. **A mutant provably identical on every reachable input is excluded, not
   counted** — and dead code found this way is **deleted**, never covered by a
   manufactured input.
5. **A new check must be able to fail at base.** A check that is green before
   the work exists measures nothing. Where a check is vacuous at base because
   its subject does not yet exist, it must be calibrated synthetically against
   constructed cases — banned forms *and* allowed forms, because a gate that
   punishes the correct answer teaches that the gate is noise.

---

## 7. Wave split

| Wave | Content | Gate |
|---|---|---|
| **I1** | `RegionSet`/`Region` in `widgets.py` + `MOUSEMOTION` in `app.py`. **No consumer.** | suite green; withheld sweep on the new types |
| **I2** | `gilded/ui/actions.py` + `ACTIONS` covering the already-wired verbs only; `app._apply_action` dispatches through it | behaviour byte-identical; §4.2 check 2 passes, check 1 lands `xfail(strict=True)` naming the five missing keys |
| **I3** | Migrate `broadsheet.handle_click`'s eleven hit structures to the registry, tab by tab | every existing click still works; hover states appear |
| **I4** | Wire the five dead buttons + the remaining unreachable verbs into `ACTIONS` | §4.2 check 1 passes **and its `xfail` marker is removed**; each verb demonstrably changes the sim |
| **I5** | `gilded/provenance.py` + the four §3.3 sites | the sum check holds at a discriminating fixture |
| **I6** | §5 type/space/colour law + the lint test | no literal RGB outside `widgets.py` |

**I1 is built with no consumer on purpose**, exactly as `widgets.py` was in
UI-legibility Wave 1, so its shape is not bent around one screen's accident.

**I2 before I3** so that the registry exists before anything is migrated onto it,
and so the migration is provably behaviour-preserving rather than a rewrite.

**I4 is where the game visibly changes.** Everything before it is scaffolding.

`gilded/ui/broadsheet.py` is 1866 lines and does both drawing and input
handling. I3 is the natural moment to separate them; the split is a consequence
of the migration, not an independent refactor.

---

## 8. Out of scope

- **Any simulation formula change.** §3.4 states why. Balance is Stage 8.
- **Retuning the attention economy.** §4.4. Stage 7, after play.
- **New domain content** — new verbs, new events, new systems. This document
  makes the existing surface reachable and legible. It adds no mechanics.
- **A graphical family tree, animated transitions, sound.** Polish beyond the
  four models; revisit once the models are consumed by a stage.

---

## 9. Measurement provenance

A spec is a claim about a tree, and claims decay. This section states which
claims were verified and by whom, so a later reader knows how much of it to
trust without re-deriving all of it.

### 9.1 Verified directly against `28f57e7` while writing this document

`app.py:170-183` event types; `app.py:75-152` handler key set;
`broadsheet.py:1550-1574` the four emitted-but-unhandled actions;
`broadsheet.py:1811-1866` the eleven ad-hoc hit structures and their eleven
populate sites, enumerated mechanically over the file (an earlier revision said
seven — see the corrigendum in §1.2);
the three view-local emitted keys `tab`, `select_province`,
`open_director_picker`;
`docket.py:837-853` fifteen `INITIATIVES` entries;
`docket.py:22-24` the six names imported from `gilded.fronts`;
`fronts.py:52-53,142,145-147,247-248` commander fields and their only writer;
absence of any game-code importer of `fronts.appoint`;
`chassis.py:37,45,89,162,349,357-362`;
`docket.py:32,33,511,585`;
`society/characters.py:333-338` and its 36 non-test call sites;
`dashboard.py MetricDelta` field list;
`society/ideology.py:85-97 tick_legitimacy`;
`widgets.py:21-32` palette and measure constants;
the §5 counts — 35 literal RGB tuples outside `widgets.py` (18 `broadsheet.py`,
17 `atlas_view.py`) and 12 distinct sizes across 30 literal `font(n)` calls —
counted by regex over `gilded/ui/**/*.py` at this commit. These are the floors
the §5 lint must fail against at base; they were measured before the rules were
written, not after.

### 9.2 Reported by inventory agents and NOT independently verified

Not relied upon by any model above; recorded so a later stage can check them
rather than re-discover them:

- `endings.py` axis formulae and the five ending keys.
- `saga/` Director/beat/FactStore behaviour and the narrator's LLM boundary.
- The escalation figures (legitimacy tide drain ~15× worse by turn 60).
- `intel.py:84-107` tier-3 apparent-intent rendering.
- The claim that `WarGoal.kind == "humble"` has no victory condition.
- Per-character stress, `Movement.conviction`, and tech-modifier visibility.

**Two agent claims were checked and found wrong**, which is why the rest are
quarantined: `INITIATIVES` was reported as holding 12 verbs and holds 15; and
`tick_legitimacy` was cited at `gilded/ideology.py`, which does not exist — the
module is `gilded/society/ideology.py`.

### 9.3 Suite floor

**Confirmed 1261 passed at `28f57e7`.** Stated provisionally when this document
was written, because the withheld Wave 19 gate was still running. That gate has
since reported — 115/115 checks, 91/91 mutations killed, 0 broken anchors,
exit 0 — and `pytest gilded/tests` at this commit returns 1261 passed. Any wave
in §7 that lands fewer than 1261 has deleted a test, and must say which and why.
