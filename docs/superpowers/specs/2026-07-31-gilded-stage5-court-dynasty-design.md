# Gilded Stage 5 — Court & Dynasty

> **STATUS: APPROVED 2026-08-07. IN FLIGHT.**
> This was drafted while the user was away, and §7 listed four design choices
> that are matters of taste — taste being the one thing the measurement loop
> cannot settle. Those four were answered on 2026-08-07, each by taking this
> spec's own recommendation; the answers are recorded in §7 and the gate the old
> header carried is discharged. **See §10 for which waves have landed.**

**Stage:** 5 of the 8-stage experience roadmap
(1 Frame · 2 Living Adversaries · 3 Policy dials · 4 Enterprises · **5 Court &
Dynasty** · 6 Diplomacy & War · 7 Initiatives · 8 Consequence & polish).

**Base when drafted:** `28599a2`, suite floor 1057 passed.
**Base for the next wave (5B):** `80aa0e8` on `master`. Gilded suite floor:
**1625 passed, 0 skipped, 0 xfail, 0 xpass**, over **1567 named cases**. Both
re-measured on three consecutive runs, not carried forward from the draft.

---

## 1. The finding this stage is built on

An inventory of `gilded/society/` produced an unusually lopsided result:

> **The simulation substrate is rich and ticking every turn. The player-facing
> surface is a read-only list of six names.**

⚠ **Line numbers re-measured on `80aa0e8`, see §10.2.** The House tab
(`house_lines()` at `gilded/ui/broadsheet.py:2225`, `_draw_house()` at `:2255`)
prints treasury, prestige,
legitimacy, capital, war status, the ruler's name, and the six court seats with
their occupants. Nothing on it can be clicked. Meanwhile, underneath it:

- `tick_loyalty()` (`gilded/society/realm.py:122-155`) recomputes a 0-100 loyalty
  for every councillor and director **every single turn**, from opinion, from
  whether they were paid, and from how far their labour/capital conviction sits
  from the ruler's. It has a threshold, `DISLOYAL_LOYALTY = 40.0`, that fires an
  event when first crossed. **None of this number is ever shown.**
- A global opinion matrix (`characters.py:28`, `modify_opinion` at `:333`)
  records the numeric change for every opinion move — **but not the reason.**
  ⚠ **Corrected 2026-07-31, see §9.1.** `modify_opinion` composes the reason into
  a return string and mutates only `society.opinions[(a,b)]`. All **20** call
  sites discard the return value. The reason exists for one expression's lifetime
  and is then gone, so there is no per-character history to read.
- Succession grievances (`relationships.py:52-73`) dock passed-over kin −15..−30
  opinion and drift them vengeful/ambitious.
- `disloyal_shareholders()` (`realm.py:162-191`) lists exactly those realm
  members who hold shares while loyalty < 40 or opinion ≤ −20.

### 1.1 The chain that already exists and is completely invisible

Those four facts compose, and the composition is the spine of this stage:

```
ruler dies  →  one kinsman inherits, the others are passed over
            →  passed-over kin take −15..−30 opinion  (relationships.py:65)
            →  their loyalty falls below 40           (realm.py:149-158)
            →  they appear in disloyal_shareholders() (realm.py:162)
            →  a rival's Takeover converts their stakes
            →  Grip on the House slips                (Stage 4's master meter)
```

**Every arrow in that chain is already implemented and already runs.** The player
cannot see a single one of them. He watches Grip slip and is told nothing about
why. This is precisely the complaint that started the whole redesign — "opaque",
"generic bullshit" — and the fix here costs almost no new simulation.

So Stage 5 is overwhelmingly a **legibility and agency** stage over machinery
that exists, in the same shape as Stage 4 L4.1-L4.6. That is a deliberate
choice, not a shortcut: the one thing this project has repeatedly proven is that
inventing new sim before surfacing the old sim produces systems nobody sees.

### 1.2 The one genuine gap

`Character.is_heir` is declared at `characters.py:143` and **is never assigned
anywhere in the codebase.** Succession picks the oldest adult kin at the moment
of death (`house_ai.py:46-53`); nobody is an heir before then.

This matters more than a missing field, because dormant *content* is already
waiting on it: the event chain `_trig_heir_radicalization`
(`chains_pack1.py:48-63`) reads `is_heir` and therefore can never fire. Wiring
heir designation activates written-but-unreachable content — the same pattern as
`market_simulation.py` in Stage 4.

---

## 2. Master tension spine

Stage 4's spine was **Grip on the House** — one meter, three forces. Stage 5 adds
the force that Stage 4 left implicit:

> **You are mortal, and the century is longer than you are.**

The ruler ages and dies inside a 70-turn century (`TURN_BUDGET = 70`). The
question the stage puts to the player every turn is not "who do I appoint" but
**"who will still be loyal to the person who follows me, and what will the ones
I passed over do with their shares?"**

Court appointments become the instrument: a seat is both a stat bonus *now*
(`court.get_bonus_for_stat`) and a loyalty bribe that outlives you. Passing over
an ambitious kinsman buys a competent chairman today and a hostile shareholder in
fifteen turns.

---

## 3. Scope

### 3.1 In — legibility (surface what already ticks)

| # | What | Substrate that already exists |
|---|------|-------------------------------|
| L1 | **Loyalty made visible** — a 0-100 meter per posted character, banded against `DISLOYAL_LOYALTY = 40` | `realm.tick_loyalty` |
| L2 | **Why it moved** — a short per-character history of opinion changes and their reasons | ⚠ **no substrate — must be built first, see §9.1 and Wave 5A0.** `modify_opinion(.., reason)` throws the reason away |
| L3 | **The family** — living kin, ages, parentage, who is in line | `Character.parent_ids/children_ids`, `Dynasty` |
| L4 | **The succession preview** — who inherits if the ruler died this turn, and who would be aggrieved | `house_ai.py:46-53` selection order |
| L5 | **Disloyal shareholders named** — the Stage-4 Grip shortfall attributed to the specific kin causing it | `realm.disloyal_shareholders` |

### 3.2 In — agency (wire levers the sim already accepts)

| # | Lever | Substrate |
|---|-------|-----------|
| A1 | **Appoint / dismiss a court seat** | `court.appoint()` / `court.dismiss()` — exist, no UI |
| A2 | **Designate an heir** | NEW small verb; sets the never-assigned `is_heir`, and succession must then prefer the designated heir |
| A3 | **Arrange a marriage** | `MarriageRegistry.arrange_match_between()` — exists, AI-only, no player UI |

### 3.3 Out of scope

- Any new opinion/loyalty *formula*. The numbers are not being rebalanced here;
  they are being shown. Balance changes belong in Stage 8.
- Assassination, imprisonment, exile. `prosecute` already exists; new punitive
  verbs are Stage 7 (action economy).
- A full graphical family tree. A legible **list** ordered by succession is the
  target; a drawn tree is polish.

---

## 4. Read-model

Following the shape that has worked three times (`dashboard.py`, `intel.py`,
`grip.py`): a **pure read-model module**, no simulation, no `game.rng`,
frozen dataclasses, and the UI reads only from it.

**New:** `gilded/peerage.py`

⚠ **Renamed from `gilded/court.py` on 2026-07-31, see §9.2.** `gilded/society/court.py`
already exists and holds `Court` and `CourtPosition` — the simulation object this
read-model reports *on*. Two files named `court.py`, one importing the other, is a
guaranteed misread for anyone (or anything) working from a bare filename.

```
CourtSeat      position, holder_name, holder_id, stat, bonus, loyalty, band, vacant
Kin            char_id, name, age, is_alive, is_heir, succession_rank,
               opinion_of_ruler, loyalty, shares_pct, is_disloyal, grievances[]
CourtReport    house, ruler_name, ruler_age, seats[], kin[], heir_designated,
               heir_if_ruler_died_now, aggrieved_if_that_happened[]
report(game, house) -> CourtReport
band_for(loyalty) -> str
```

Bands mirror `grip.BANDS` in construction — weakest-first so `BANDS.index()` is a
strength rank — cut against `DISLOYAL_LOYALTY = 40` rather than a fresh constant,
because a second threshold for one rule is the redundant-mechanism trap.

**Determinism:** `report()` must be pure and rng-free, and must return an empty
report for an unknown house rather than raising — both are L2 fix-list lessons
already paid for in `grip.py`.

---

## 5. Verification law

Unchanged from the UI-legibility spec §9, and non-negotiable:

1. **Assert the rule, not the constant.** A test that hard-codes `40` fails when
   the constant moves and proves nothing about the banding rule.
2. **Assert at a fixture that can discriminate.** A fixture sitting on the code's
   own default (a loyalty of exactly `LOYALTY_START = 50.0`, an `is_heir` of
   `False`) cannot tell the rule from a constant. Two distinct non-default inputs,
   in the same file.
3. **A wave is accepted only when the repo's own tests go red under a withheld
   mutation set** built after delivery and never shown to the implementer.
4. A mutant that is provably identical on every reachable input is **excluded**,
   not counted — and dead code found this way is **deleted**, never covered by a
   manufactured input.

---

## 6. Proposed wave split

| Wave | Content | Gate |
|------|---------|------|
| **5A0** | **The opinion ledger** — `modify_opinion` appends `(turn, other_id, delta, reason)` to a bounded per-character log instead of discarding it. Sim layer, no read-model, no UI. | suite green; a test proves a reason survives the call that made it |
| **5A** | `gilded/peerage.py` read-model + tests, no consumer | suite green; withheld sweep on `peerage.py` |
| **5B** | Court tab: seats, loyalty meters, kin list, succession preview | render tests read the surface, not the model |
| **5C** | A1 appoint/dismiss wired to `court.appoint/dismiss` | the lever changes the sim, and the change is visible |
| **5D** | A2 heir designation + succession prefers the designated heir + `_trig_heir_radicalization` reachable | a test proves the chain can now fire |
| ~~5E~~ | ~~A3 player-arranged marriage~~ | **struck — deferred to Stage 6, see §7 Q4** |

5A is built with **no consumer on purpose**, exactly as `widgets.py` was in the
UI-legibility Wave 1, so it is not shaped around one screen's accident.

5A0 comes **before** 5A rather than after, even though it is the less interesting
wave, because `Kin.grievances[]` cannot be reported from a substrate that does not
exist. Ordering it second would mean shipping `Kin` without the field and changing
the dataclass — and every test that constructs one — a wave later. Build the shape
once.

---

## 7. THE FOUR CHOICES — ANSWERED 2026-08-07

Each was answered by taking this spec's own recommendation. They are recorded as
decisions, not options, because a spec that keeps its questions open after they
are settled reads as still-blocked to every later reader.

**Q1 — Where does this live?** **(a) Extend the existing House tab.** The tab
list is already ten long and House is the thematically exact home. No new tab.
`TABS` at `broadsheet.py:71` does not grow, and the region census in
`test_ui_broadsheet.py` moves only by the regions this stage's own levers add.

**Q2 — What does a court appointment cost?** **(c) Free to appoint; dismissing
costs standing with the dismissed man's kin.** It is the only option where the
lever has a *shape*, and it feeds the succession spine directly. Scoped to
Wave 5C, not 5B.

**Q3 — How explicit is the heir?** **(a) A designation lever**, with the
aggrieved consequences fired at designation time rather than at death. It turns
a passive reveal into a decision, and it is what activates the dormant
`_trig_heir_radicalization` chain. Scoped to Wave 5D.

**Q4 — Is Wave 5E (player-arranged marriage) in this stage?** **Deferred to
Stage 6 Diplomacy.** It is a diplomacy lever wearing a family costume, and
Stage 5 is already four waves without it. **5E is struck from this stage.**

---

## 8. What this stage is worth

The player currently watches Grip on the House slip for reasons the simulation
knows precisely and never states. After Stage 5 he can look at the man who is
going to betray him, see the number, see the sentence explaining how it got
there, and decide whether to buy him off with a seat. That is the difference
between a system and a story, and the machinery for it is already written —
with one exception, the sentence itself, which §9.1 found is thrown away.

---

## 9. Corrections — measured against the tree on 2026-07-31

This spec was drafted from a reading of `gilded/society/`. Before any of it could
be briefed, every substrate claim it makes was re-checked against the code rather
than against the notes. Three were wrong. They are corrected in place above and
recorded here, because a spec that quietly repairs itself teaches nothing about
how much of it to trust.

### 9.1 The opinion reasons are not recorded — they are discarded

**Claimed** (§1, §3.1 L2, §4): every opinion change records a reason string, so a
per-character grievance history can simply be read out.

**Measured:** `modify_opinion` (`society/characters.py:333-338`) mutates
`society.opinions[(a,b)]` with the delta and *returns* a formatted sentence
containing the reason. Every one of its **20** call sites — 10 in `docket.py`, 4
in `house_ai.py`, 2 in `marriages.py`, 2 in `chains_pack1.py`, plus
`relationships.py` — discards the return value. Nothing is stored. The reason
lives for the duration of one expression.

**Why it slipped through:** the function's signature takes a `reason` parameter,
and a parameter named `reason` reads as a thing being recorded. It is being
*formatted*. This is the same shape as the audit's central class and as F23 —
a name that describes an intent no code discharges — and it is the second time
in two days that "the substrate already exists" turned out to mean "the substrate
already has the vocabulary".

**Consequence:** `Kin.grievances[]` has nothing to read. Rather than drop the
field or let an implementer invent one, Wave **5A0** now builds the ledger first.
Cutting L2 instead was the alternative and is worse: the grievance sentence is
the single thing §8 says this stage is for.

### 9.2 `gilded/court.py` collides with `gilded/society/court.py`

**Claimed** (§4): the new read-model is `gilded/court.py`.

**Measured:** `gilded/society/court.py` already exists and defines `Court` and
`CourtPosition` — the simulation object the read-model would report on and import
from. Two files with the same basename, one importing the other, addressed by
bare filename in briefs and gates. Renamed to `gilded/peerage.py`.

### 9.3 Path and line citations

The draft cites `realm.py`, `characters.py`, `house_ai.py` and `court.py` as
though they sat at `gilded/`. They are all under `gilded/society/`; the read-model
layer at `gilded/*.py` is a separate tier (`grip.py` imports *from*
`gilded.society.realm`). Succession is `society/house_ai.py:43-60`, not `46-53`.
The rule it implements is unchanged and as described: oldest living adult kin,
`is_heir` never consulted.

### 9.4 What re-checking did *not* overturn

Stated so the corrections above are not read as a verdict on the whole draft:
`DISLOYAL_LOYALTY = 40.0` and `LOYALTY_START = 50.0` (`society/realm.py:158`,
`:119`) are as described; `tick_loyalty` and `disloyal_shareholders` exist and
behave as claimed; `grip.BANDS` is weakest-first at `grip.py:19`;
`Court.appoint(position, character, turn) -> bool` and
`Court.dismiss(position) -> Optional[Character]` exist with no UI caller;
`Character.is_heir` is assigned `False` at `characters.py:143` and **assigned
nowhere else in the repository**, so §1.2's claim that `_trig_heir_radicalization`
(`chains_pack1.py:50`) can never fire is exact.

### 9.5 Status when these corrections were written

These corrections made the spec accurate. They did not make it approved; the
header gate stood until 2026-08-07, when §7's four questions were answered.
Superseded by §10.

---

## 10. Delivery record — measured on `80aa0e8`, 2026-08-10

### 10.1 What has landed

| Wave | Commit | State |
|------|--------|-------|
| **5A0** the opinion ledger | `9593e32` (dispatched as I5b) | **landed.** `society.opinion_history[(a,b)]` holds `OpinionEntry(.amount, .reason)`; the House tab prints the reasons as text |
| **5A** `gilded/peerage.py` | `ae39931`, hardened by `4eb355d`, `ee2d729`, `c5f977a` (5A2) | **landed.** `report(game, house) -> CourtReport` at `:107`, `band_for(loyalty) -> str` at `:27`; `CourtSeat` `:45`, `Kin` `:58`, `CourtReport` `:73`. 34 cases in `test_peerage.py` |
| **5B** the Court surface | — | **next** |
| **5C** appoint / dismiss | — | pending |
| **5D** heir designation | — | pending |

### 10.2 What 5B actually faces, re-measured

The draft's §1 numbers are two months and roughly forty waves stale. Measured on
`80aa0e8`:

- `TABS` is ten long at `broadsheet.py:71`, ending in `"House"`.
- `house_lines() -> List[str]` at `:2225` builds flat text; `_draw_house()` at
  `:2255` blits those strings one per line and returns early on overflow.
- **The House tab reads `realm.court.positions` and `g.society.opinions`
  directly. It does not import `gilded/peerage.py` at all.** The read-model 5A
  was built for has no consumer, which is exactly what 5A intended and exactly
  what 5B must change.
- House registers **no regions of its own**: `EXPECTED_REGIONS["House"] == 12`
  at `test_ui_broadsheet.py:39`, which is the ten tabs plus `end_turn` plus
  `narrate`. 5B is read-only, so that number must not move.
- Nothing on the tab shows a loyalty number, a band, a kinsman, a succession
  rank, or who inherits — every one of §3.1's L1-L5 is still unsurfaced.

### 10.3 Laws any new surface inherits

Established by Stage-6 hardening waves I6i and I6j and enforced by tests that
already exist:

- **Palette:** no literal RGB tuple outside `gilded/ui/widgets.py`
  (`test_i6i_palette.py::test_palette_lint_no_literal_rgb`). Use the named
  constants at `widgets.py:21-64` and `TONES` at `:133-141`.
- **Type scale:** no integer point size outside `widgets.py` — every size comes
  from one of the six named steps at `widgets.py:148-155`, and this is enforced
  at the level of the *source text*, at a call site and at a screen's own
  module-level alias (`test_ui_type_scale.py`, `test_type_scale_properties.py`,
  `test_type_scale_source.py`).
- The closest existing analogue for a list surface is the Enterprises tab,
  `broadsheet.py:1789-1967`: model → layout → `table.layout(rect)` → iterate
  `row_rects` / `cell_rects` / `text_rects`. It **clips** on overflow; it does
  not scroll or paginate.
