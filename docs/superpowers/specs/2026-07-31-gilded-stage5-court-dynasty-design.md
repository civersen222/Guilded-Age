# Gilded Stage 5 — Court & Dynasty

> **STATUS: DRAFT — NOT APPROVED, NOT DISPATCHED.**
> Every earlier stage of this roadmap was approved by the user before any game
> code was briefed. This one was drafted while he was away, so that the reading
> and the inventory were not wasted time — but §7 lists four design choices that
> are matters of taste, and taste is the one thing the measurement loop cannot
> settle. **No Stage 5 wave may be briefed or dispatched until those four are
> answered.** The hardening waves that ran alongside this draft are a separate,
> already-authorised lane.

**Stage:** 5 of the 8-stage experience roadmap
(1 Frame · 2 Living Adversaries · 3 Policy dials · 4 Enterprises · **5 Court &
Dynasty** · 6 Diplomacy & War · 7 Initiatives · 8 Consequence & polish).

**Base:** `28599a2` on `master`. Gilded suite floor: **1057 passed, 0 skipped.**

---

## 1. The finding this stage is built on

An inventory of `gilded/society/` produced an unusually lopsided result:

> **The simulation substrate is rich and ticking every turn. The player-facing
> surface is a read-only list of six names.**

The House tab (`gilded/ui/broadsheet.py:1783-1807`) prints treasury, prestige,
legitimacy, capital, war status, the ruler's name, and the six court seats with
their occupants. Nothing on it can be clicked. Meanwhile, underneath it:

- `tick_loyalty()` (`gilded/society/realm.py:122-155`) recomputes a 0-100 loyalty
  for every councillor and director **every single turn**, from opinion, from
  whether they were paid, and from how far their labour/capital conviction sits
  from the ruler's. It has a threshold, `DISLOYAL_LOYALTY = 40.0`, that fires an
  event when first crossed. **None of this number is ever shown.**
- A global opinion matrix (`characters.py:28`, `modify_opinion` at `:333`)
  records a reason string for every change.
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
| L2 | **Why it moved** — the reason strings already recorded on every opinion change, shown as a short per-character history | `modify_opinion(.., reason)` |
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

**New:** `gilded/court.py`

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
| **5A** | `gilded/court.py` read-model + tests, no consumer | suite green; withheld sweep on `court.py` |
| **5B** | Court tab: seats, loyalty meters, kin list, succession preview | render tests read the surface, not the model |
| **5C** | A1 appoint/dismiss wired to `court.appoint/dismiss` | the lever changes the sim, and the change is visible |
| **5D** | A2 heir designation + succession prefers the designated heir + `_trig_heir_radicalization` reachable | a test proves the chain can now fire |
| **5E** | A3 player-arranged marriage | |

5A is built with **no consumer on purpose**, exactly as `widgets.py` was in the
UI-legibility Wave 1, so it is not shaped around one screen's accident.

---

## 7. OPEN CHOICES — the user must answer these four

These are matters of taste. They are not blockers to *understanding* the stage,
but they are blockers to briefing it.

**Q1 — Where does this live?** (a) Extend the existing **House** tab, which is
currently near-empty and thematically exact; or (b) a **new Court tab**, leaving
House as the realm summary. Recommendation: **(a)** — the tab list is already ten
long, and House is the natural home.

**Q2 — What does a court appointment cost?** (a) **Free**, like the Stage-3
policy dials; (b) **one attention**, like placing an informant; or (c) free to
appoint, but dismissing costs standing with the dismissed man's kin.
Recommendation: **(c)** — it is the only option where the lever has a *shape*,
and it feeds the succession spine directly.

**Q3 — How explicit is the heir?** (a) A **designation lever** the player sets,
with the aggrieved consequences fired at designation time rather than at death;
or (b) **no lever** — succession order is merely made visible, and the drama is
in watching it. Recommendation: **(a)** — it turns a passive reveal into a
decision, and it is what activates the dormant radicalization chain.

**Q4 — Is Wave 5E (player-arranged marriage) in this stage or deferred to
Stage 6 Diplomacy?** Marriage is a cross-house instrument and already nudges
inter-house relations (+3 per blood tie). Recommendation: **defer to Stage 6** —
it is a diplomacy lever wearing a family costume, and Stage 5 is already five
waves.

---

## 8. What this stage is worth

The player currently watches Grip on the House slip for reasons the simulation
knows precisely and never states. After Stage 5 he can look at the man who is
going to betray him, see the number, see the sentence explaining how it got
there, and decide whether to buy him off with a seat. That is the difference
between a system and a story, and the machinery for it is already written.
