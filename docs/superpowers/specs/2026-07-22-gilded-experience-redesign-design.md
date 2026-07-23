# The Gilded Machine — Play-Experience Redesign (Design)

**Status:** approved vision, Stage 1 specced. Program-level doc; each later stage gets its own spec.

**Date:** 2026-07-22

## The problem this fixes

The Gilded Machine has a genuinely deep simulation, but as a *game* it fails. A
player at the current pygame client experiences: obscure tabs, no explanation of
what anything means, no visible subsystems or how they interact, no sense of
winning or losing — just "End Turn" on repeat while some numbers drift. The sim
hides its own state and consequences from the player, and the only agency exposed
is ruling on ~3 of at most 6 petitions per turn. That is not a game.

**This is a ground-up redesign of the play experience — the turn loop, the
control surface, and the feedback — built on top of the existing simulation and
setting, which we keep.** (Foundation decision: keep the mortal-ruler /
industrial-century / dynasty / rising-Tide / four-axis-judgment bones; rebuild
everything the player sees and does.)

## The fantasy

You are the mortal head of a great house dragging your dynasty through the
century (1900–2000) that industrialization and revolution will either crown or
bury. You govern; you do not micromanage pawns. Your ruler ages and dies and an
heir takes the chair. At 2000 the age judges what you built and what it cost.

## The five pillars

1. **Agency.** Every turn you actively steer many systems — policy, enterprises,
   court, blood, diplomacy, war. What you do not personally touch, your standing
   directives and appointed council run *for* you, so breadth never becomes
   busywork.
2. **Legibility.** A scoreboard is always on screen: your four axes as meters,
   legitimacy, the Tide of revolution, the current era, the Rival's standing, and
   how far into the century you are. Every turn opens by telling you *what changed
   and why*.
3. **Escalating tension.** The Tide rises, the Rival maneuvers, your ruler ages
   and dies. The century has acts (the eras) that ratchet pressure. Standing still
   is losing.
4. **Consequence & story.** Choices feed the Chronicle (the Director/saga engine
   already shipped), so the century reads as one coherent story and the final
   judgment reflects how you actually ruled.
5. **Living adversaries.** Every rival house — above all *the* Rival — pursues a
   persistent, multi-turn **agenda** that drives its real moves and is *partially
   legible* to you through intelligence. The world is full of intent you can read,
   race, or counter. This is a first-class pillar, not set dressing.

## The target turn (core loop: "deep but never opaque")

- The **Council briefing** opens each turn:
  - **Scoreboard** across the top (always visible on every screen thereafter).
  - **"Since last session"** delta feed — what moved and *why*, e.g. *"Unrest in
    Galstad fell 8 because you sent troops; legitimacy dropped 5 — the papers
    called it a massacre."*
  - **The Agenda** — the handful of most consequential decisions this turn, each a
    card showing the stakes, a preview of the likely consequence, and who would
    carry it out.
- Deeper than the Agenda? Open any **panel** — Policy, Enterprises, Court,
  Dynasty, Diplomacy, War, Provinces — each a real control surface showing that
  subsystem's full state and letting you act.
- You spend limited **ruler attention** where it matters; the rest runs on your
  standing policy and council. **End Turn**, and next turn's briefing shows what
  your decisions did. The loop closes every turn.

The difference from today: you always know the score, you always see consequence,
and there are far more than six things you can meaningfully do — most turns you
will leave decisions on the table.

## The control-surface domains

Where the "hundreds of meaningful choices over a century" live. Each is a panel
introduced by a later stage; most expose sim systems that already run but have no
UI today.

- **Policy** — the 5 standing directive dials (capital / labor / expansion /
  diplomacy / war), which auto-decide everything you do not personally attend.
- **Enterprises** — your industrial portfolio: every works, its tier, its
  **extraction dial** (profit vs. atrocity — the moral core), its director;
  found and expand.
- **Court** — the 6 council seats: appoint, watch loyalty, detect schemes.
- **Dynasty** — marriages, heirs, education, succession on your ruler's death.
- **Diplomacy** — relations (−100..+100), alliances, betrothals with rival houses.
- **War** — fronts, regiment allocation, commanders.
- **Provinces** — development, garrison, tours, unrest (the Atlas, made actionable).

## The staged roadmap

Ground-up, shipped in stages. Each stage is its own spec → plan → CynCo waves,
and each leaves a better, fully-working game than the last.

1. **The Frame (legibility).** Scoreboard + Council briefing + delta feed +
   Agenda from existing petitions. No new sim systems. You can see the board and
   what every house *did* last turn. Everything else plugs into this frame.
   **(Detailed spec below.)**
2. **Living Adversaries (AI-intent engine).** Pulled to the front, second only to
   the Frame it displays on. Each rival house adopts a persistent agenda that
   drives its moves; a Rivals/Intelligence panel shows each house's *apparent*
   aim, progress, and recent maneuvers, gated by what your court can observe
   (rumor vs. confirmed). The Rival is dead-center.
3. **Policy panel** — the 5 directive dials with live preview of what they
   auto-decide.
4. **Enterprises panel** — portfolio, extraction dials, found/expand, directors.
5. **Court & Dynasty** — appointments, loyalty, schemes; marriage, heirs,
   succession.
6. **Diplomacy & War** — relations, alliances, betrothals; regiments, fronts,
   commanders.
7. **Initiatives + action economy** — unify proactive moves (found/expand, build
   rail, tour, schemes, marriage offers) and rebalance ruler attention into
   coherent pacing with real tradeoffs.
8. **Consequence & polish** — tighten per-event cause→effect attribution, richer
   Chronicle wiring, escalation-curve tuning, endgame framing.

**Unifying principle:** the AI-intent engine ships at Stage 2, then *every later
domain stage extends it*. When Enterprises lands, a rival's "corner steel" agenda
appears as market-share bars you are losing; when War lands, "build a coalition"
shows the alliance visibly forming against you. Each stage deepens *your* agency
and *their* legibility in the same subsystem, together. This is what keeps the
game from ever feeling generic.

---

# Stage 1 spec — The Frame (legibility)

**Goal:** rebuild the app shell so the player can always read the score, the
world, and what just changed — using only state the sim already tracks. No new
sim mechanics.

**A player finishing Stage 1 can, by looking at the screen, answer:** What are my
four axes right now? Is the Tide rising, and what phase is it? What era is it, and
how close is the next? Who is my Rival and how do I stand against them? How far
into the century am I? What changed last turn, and roughly why?

## 1. The scoreboard read-model

A new deterministic read-model that computes the live board for a house on any
turn **without mutating game state**. Lives in the read-model layer (a new
`gilded/dashboard.py`, sibling to `papers.py`), not in the sim.

`scoreboard(game, house_name) -> Scoreboard` returns:

- `year` (via `year_of(game.turn)`), `turn`, `century_pct` (`turn / TURN_BUDGET`,
  clamped 0..1).
- `era_idx`, `era_title` (from `game.director.age_idx` → `ERAS`; before the first
  era is crossed, "Before the Age"), and `next_era` hint: the turn/tide threshold
  of `ERAS[age_idx + 1]` (or "the final age" at the last era).
- `axes`: `capital`, `standing`, `blood`, `world` (0..100), computed by reusing
  `endings._axis_capital/_axis_standing/_axis_blood/_axis_world` — these already
  take `(game, house_name)` and do not require game-over. This guarantees the
  mid-game meters and the final judgment are the *same numbers*.
- `legitimacy` (`game.legitimacy[house]`), `prestige`, `treasury`.
- `tide_level` (`game.tide.level`), `tide_phase` (`game.tide.phase()`),
  `atrocities` (`game.tide.atrocities`).
- `rival_name` (`game.director.rival`), `rival_axes` (the same four axes computed
  for the rival house, or `None` if no rival is bound yet), and `rank`: the
  player's position among all houses ordered by a documented composite (mean of
  the four axes) with ties broken by house name.
- `unrest_avg`: mean `province.unrest` across the house's provinces (0 if none).

The `Scoreboard` is a frozen dataclass of plain values (no live game references),
so it is safe to retain across turns for diffing.

## 2. The delta model

`delta(prev: Scoreboard, curr: Scoreboard) -> Delta` returns the turn-over-turn
change for `axes` (each), `legitimacy`, `treasury`, `tide_level`, `unrest_avg`,
and `rank`. Each numeric delta carries the signed change and a direction flag.
`prev is None` (first turn) yields an all-zero delta marked "first session".

**The "why".** Stage 1 pairs the numeric deltas with the turn's narrative events —
the existing `gazette`/`ledger`/`letters` from `papers.compose`, which already
narrate causes ("Scandal rocks Karsgate: legitimacy falls 16"). The briefing
shows *deltas + the events that explain them*, side by side. Deep per-event
attribution (tagging each delta with the exact event that caused it) is
explicitly **out of scope for Stage 1** and deferred to Stage 8.

Snapshot handling is **non-invasive**: the caller (app / console) retains the
previous `Scoreboard` and diffs against the current one. No sim change, no new
turn-boundary hooks.

## 3. The Council briefing view

A new default view shown when a turn opens. Layout, top to bottom:

- **Scoreboard HUD strip** — persistent across *all* tabs, not just the briefing:
  the four axes as labeled meters, legitimacy, Tide (level + phase), era + next-era
  hint, year + century progress, Rival name + how you rank against them.
- **"Since last session"** — the delta feed: each moved metric with its signed
  change and an up/down cue, followed by the grouped narrative events
  (`gazette`/`ledger`/`letters`) that explain the turn. On the first turn it reads
  as an opening-of-the-century briefing.
- **The Agenda** — the existing petitions surfaced as decision cards (reuse the
  current docket petition rendering and the `{"rule": (pid, key, exec_id)}`
  action), plus the attention counter and End Turn.

The existing tabs (Gazette, Ledger, Letters, Docket, Atlas, House) remain
reachable; the briefing becomes the landing view each turn and the HUD rides above
all of them. No existing petition/attention behavior changes.

## 4. Explicitly out of scope for Stage 1

- Any new sim mechanic, lever, or player action beyond what exists today.
- The AI-agenda engine (Stage 2), directive dials UI (Stage 3), and all domain
  panels (Stages 4–6).
- Per-event causal attribution beyond "deltas next to the events" (Stage 8).
- Reworking the action economy (Stage 7).

## 5. Architecture & constraints

- **Read-model, not sim.** `gilded/dashboard.py` is pure/deterministic and only
  *reads* `GildedGame`; it never mutates. The UI consumes it exactly as it
  consumes `papers.compose` today. No sim logic enters `gilded/ui/`.
- **Determinism preserved.** No new RNG; the scoreboard is a pure function of game
  state. The sim stays zero-LLM and deterministic.
- **Tests stay model-free.** The repo-root `conftest.py` continues to force
  `GILDED_NARRATE=0`; UI tests run headless with `SDL_VIDEODRIVER=dummy`.
- **Build discipline.** All game-code changes ship as byte-exact CynCo mission
  briefs, pre-validated on the scratch worktree and verified with the standard
  5-check protocol against the pre-existing baseline (currently `1 failed, N
  passed`, the lone failure being `test_civkings.py::test_100_turn_stability`).
  Design docs and scratch harnesses are authored directly.

## 6. Testing / acceptance for Stage 1

- **Read-model unit tests:** `scoreboard(game, house)` returns all fields with
  correct ranges; its axis values equal `endings.judge` axis values at game-end
  for the same state (the "same numbers mid-game and at judgment" guarantee);
  `rank` is stable and tie-broken by name; calling it does not mutate state
  (a soak/equality check on game state before/after).
- **Delta unit tests:** `delta(prev, curr)` reports correct signed changes;
  `prev is None` yields the first-session zero delta.
- **UI headless tests** (`SDL_VIDEODRIVER=dummy`): the HUD renders on every tab;
  the briefing shows a delta feed and an agenda; ruling a petition from the
  Agenda still consumes attention and applies the ruling; End Turn still advances.
- **Baseline holds:** full suite tail stays `1 failed, N passed` (only the
  pre-existing stability failure).
- **Acceptance probe** (scratch, not committed): a headless script advances a few
  turns and prints the scoreboard + delta, demonstrating the six player questions
  above are answerable from the read-model.

## 7. Deferred / open questions

- Exact composite used for `rank` (mean-of-axes is the Stage 1 choice; may be
  revisited when Living Adversaries lands and a richer standing exists).
- Whether the HUD should also show a one-line Rival *intent* string — deferred to
  Stage 2, where real agendas exist; Stage 1 shows Rival identity + relative rank
  only.
- Visual styling/legibility polish (fonts, color, meter design) is intentionally
  minimal in Stage 1 and refined in Stage 8.
