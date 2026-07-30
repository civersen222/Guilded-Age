# Gilded UI Legibility — Stage 5 Design

**Date:** 2026-07-29
**Status:** approved (option C, hybrid)
**Supersedes for the visual layer:** the Stage 8 deferral in
`2026-07-22-gilded-experience-redesign-design.md §7`

---

## 1. Why this document exists

The player opened the build on seed 7 and stopped playing. The verdict was that the
interface is unusable, and having rendered all ten tabs to PNG and read the pixels, that
is correct.

**This is not a regression.** Every spec in the corpus was read to check. No spec has ever
described the visual layer:

- `2026-07-22-gilded-experience-redesign-design.md §7` — "Visual styling/legibility polish
  (fonts, color, meter design) is intentionally minimal in Stage 1 and refined in Stage 8."
- `2026-07-21-gilded-machine-design.md §7` is the only layout text in the corpus and is
  conceptual: "A broadsheet, not a battlemap ... the turn report as a period newspaper
  (masthead, columns) ... the atlas is a side view ... port their content into text panels."
- No spec mentions a table, a column, a grid, a meter, colour semantics, information
  density, a map legend, the province letter codes, or a HUD height.

Stage 1 was right to defer this. The deferral is now being paid off. What shipped is the
faithful output of a direction ("text-forward broadsheet") that carried no layout rules.

## 2. The finding that shapes the whole design

**The read-models already carry table-shaped data. The renderer flattens it to prose and
discards the remainder.**

Measured, by grep across `gilded/ui/`:

| Computed every turn | Where | Used by the UI? |
|---|---|---|
| `Scoreboard.rival_axes` — the rival's four axes | `dashboard.py:87,109` | **Never referenced. Zero hits.** |
| `Delta.axes[k].change` / `.direction` per metric | `dashboard.py:115-151` | Only to build prose ("Capital fell 47") |
| `Scoreboard.prestige` | `dashboard.py:34` | One bare number on the House tab |
| `Scoreboard.unrest_avg` | `dashboard.py:42` | Only as a prose delta line |
| `EnterpriseLine` — 9 fields, already one row | `grip.py:40-49` | Flattened into a pipe-delimited string |
| `GripReport.band` (SEIZED/IMPERILED/CONTESTED/IRON_GRIP) | `grip.py:64-71` | Printed as text, not as a state |
| `GripReport.margin`, `.threshold` | `grip.py:59-60` | Printed as numbers, never as a bar |
| `Director.disloyal` → the `[skim]` betrayal flag | `grip.py:36` | A bracket inside a longer string |

The player's complaint that the game is opaque and shallow has a precise cause: you can see
your rival's **name** but not how you compare against them, while the comparison is loaded
in memory on every single turn.

This reframes the work. It is not "design a UI from nothing." It is **stop discarding the
read-model**, plus the one missing module that would let anyone render it.

## 3. Scope

**In scope:** `gilded/ui/` only — `broadsheet.py`, `atlas_view.py`, `app.py`, and a new
`widgets.py`. Plus one defect in `papers.py` (§4.2).

**Out of scope, explicitly:** no new game mechanics, no new read-model fields, no changes
to `chassis.py`, `market.py`, `grip.py`, `intel.py`, `dashboard.py` beyond nothing at all.
Every value this design renders is already computed today. If a wave finds it needs a new
number, that is a signal to stop and re-scope, not to reach into the simulation.

**Non-goal:** pixel-perfect visual polish. The bar is *legibility* — can the player see
what changed, how much, whether it is bad, and what they can do about it.

## 4. Wave 0 — the two hard bugs

Both are wrong under any design and ship ahead of the redesign, in their own commit.

### 4.1 The HUD's fifth line overflows its band on every tab

`broadsheet.py:187-222` draws five lines; the band is `HUD_H = 96`. Measured at font 15
(height 18, `line_h = 21`), starting at `y0 = TAB_H + 6`:

| line | content | top | bottom |
|---|---|---|---|
| 1 | four axes | 6 | 24 |
| 2 | legitimacy / treasury / tide / atrocities | 27 | 45 |
| 3 | era / next era / year | 48 | 66 |
| 4 | rival / rank | 69 | 87 |
| 5 | `Their design: <intent>` | 90 | **108 — 12px past 96** |

`draw()` (`:147-170`) fills `PAPER_BG`, draws the tab content, and only then calls
`_draw_hud`. `_draw_hud` paints its own background for 96px only, so line 5 renders on top
of the content area with no backing — a half-cut line of text on all ten tabs.

In absolute coordinates line 5's box runs y 130..148 against a band ending at y 136. The
*measured ink* reaches y 146 rather than 148, because that string has no descender filling
the last two pixels of the em box. The line box overflows by 12px; the drawn ink by 10px.
The gate measures ink, since ink is what the player sees.

**Requirement.** No HUD text may be drawn outside the HUD band. The band's height must be
derived from the content it holds rather than being a constant the content silently
outgrows. A test must assert the geometric property (every rendered line's bottom edge lies
within the band), not the current constant — a test pinning `HUD_H == 118` would pass while
a sixth line reintroduces the bug.

### 4.2 Two year functions, disagreeing on screen simultaneously

- `chassis.py:49` — `year_of(turn) = YEAR_START(1900) + round((turn - 1) * 100 / TURN_BUDGET(70))`.
  The century over 70 turns. Feeds `dashboard.scoreboard` (`dashboard.py:95`) → the HUD.
- `papers.py:16,82` — `YEAR_ZERO(1899) + game.turn`. One year per turn. Feeds the
  Gazette/Ledger/Letters masthead via `broadsheet.py:363`.

Measured drift: turn 1 → +0, turn 12 → **+5**, turn 35 → +15, turn 70 → **+30**
(HUD 1999 vs masthead 1969). At turn 12 the screenshot shows `THE LEDGER - 1911` under a
HUD reading `1916`.

**Requirement.** One function owns the year: `chassis.year_of`. `papers.py` uses it and
`YEAR_ZERO` is deleted. A test must assert agreement across the century at several turns
including the last, not at turn 1 where the two formulas coincide.

**In scope, measured against a reference implementation:** `gilded/tests/test_papers.py:5`
imports `YEAR_ZERO` from `gilded.papers`. Deleting the constant without editing that import
fails the suite at *collection* — `ImportError: cannot import name 'YEAR_ZERO'`, one error,
zero tests run. The import must be dropped and any assertion depending on it rethreaded
through `year_of` in the same commit.

## 5. Wave 1 — `gilded/ui/widgets.py`, the vocabulary that never existed

Every failure in §7 traces to the absence of this module. It is built first and alone, with
nothing consuming it yet, because it is the thing all later waves are made of.

- **`Table(columns, rows)`** — column specs carry a header, a width, and an alignment;
  numerics right-align, text left-aligns. Hairline rule under the header, optional rule
  every row. Returns per-cell rects so rows are clickable.
- **`Meter(label, value, lo, hi, delta=None, danger=None)`** — a labelled bar. Renders the
  fill proportionally, the number, and — when `delta` is given — a direction arrow tinted
  by tone. `danger` marks the band below/above which the tone flips.
- **`Chip(text, tone)`** — a small pill for discrete state: `IRON GRIP`, `IMPERILED`,
  `skim`, `rising`, `falling`.
- **`Panel(rect, title)`** — a bordered region with a titled rule, so content sits inside a
  frame instead of floating on background.
- **`columns(rect, n, gap)`** and **`rows(rect, heights)`** — rect splitters. The absence of
  these is literally why every screen is one flush-left column.
- **`TONES`** — one table mapping `good | bad | warn | neutral | dead` to a colour, read by
  every widget. Colour meaning is defined once. Today `_draw_enterprises` and `_draw_powers`
  each pick their own greys.

**Testing.** Headless, geometric, no pixel comparison: a table's columns do not overlap and
sum to its width; numeric cells right-align; a meter at `hi` fills its rect and at `lo`
fills none; a value inside a `danger` band selects the `bad` tone; `columns(rect, 3, gap)`
returns three non-overlapping rects inside `rect`. These are the assertions that survive
restyling.

## 6. Waves 2–5

**Wave 2 — the HUD earns its band.** The four axes become `Meter`s with delta arrows and
tone, driven by the `Delta` that is already computed. Your axes render beside the rival's,
using the `rival_axes` that no line of UI code currently reads. Legitimacy, treasury, tide
and atrocities become meters or chips rather than a run-on sentence. Because Wave 0 made the
band derive from content, this cannot re-clip.

**Wave 3 — the decision screens become tables.** Enterprises: `EnterpriseLine` → real
columns (venture, sector, tier, dividend, Δ, director, stake, top outside), dividend delta
toned, `[skim]` as a `Chip`, the grip band as a `Chip` and `margin` as a `Meter` against
`threshold`. Powers: the six rival houses as a table (house, intel *n*/3, ties, apparent
intent, threat rank) with clickable rows. Ledger: a period stock page — commodity prices
with direction, dividends per venture, treasury in and out.

**Wave 4 — Atlas legibility.** The Atlas has the most real craft in the build and is still
unreadable. It needs: a legend naming every house colour **including which one is the
player**, the one/two-letter province codes spelled out, and both link styles (solid red,
dashed orange) explained; label collision avoidance so `Ferburg Marches`/`Ravenmere`,
`Loxhaven Reach`/`Duncliff`, `Quillmoor`/`Holhaven Cross` and
`Brenshore`/`Quillmarch Marches`/`Loxmore Head` stop overprinting; and the map fitted to
the free rect instead of clipped under the HUD with a ~140px dead band beneath it.

**Wave 5 — the newspaper, executed.** The narrative register works and stays. Gazette,
Letters and the Briefing keep their prose voice but gain real columns at a ~66-character
measure instead of 1248px-wide lines, with rules and small-caps heads. Content that runs
past the bottom must not be silently dropped as `_draw_paper:372` does today.

## 7. The failures this design answers

From the pixels, at turn 12, seed 7. Screenshots in `C:/tmp/shots/`.

1. **Nothing is laid out.** Every tab is a 30px title at `PAD=16` then 18px prose at x=16,
   top to bottom, full width. `_draw_paper:370-376`, `_draw_powers`, `_draw_house` are the
   same `for line: blit; y += h` loop. → Waves 1, 3, 5.
2. **60–90% of a 1280x900 window is empty.** The Ledger — the financial screen — is two
   lines of text and ~700px of blank. Powers is six lines. → Waves 1, 3.
3. **Structured data ships as debug rows.**
   `Brenshore Mill | freight | tier 1 | div 116.8 (+9.6) | dir: Thea Ashworth [skim] | stake: 50.0% | top outside: Thea Ashworth 10.0%`
   — seven fields, pipe-delimited, unaligned, no headers. → Wave 3.
4. **Nothing encodes magnitude, direction or danger.** Capital fell 85 → 38 across twelve
   turns and renders in the same weight and colour as everything else. `You rank #4 of 7`
   gets no emphasis. `Atrocities 6` appears unhighlighted. The `Delta` needed to fix this is
   already computed. → Waves 1, 2.
5. **The Atlas is unreadable despite real craft.** → Wave 4.

Also observed and folded into the waves: three fighting visual languages (dark chrome, cream
body, navy Atlas) plus a lone purple `executor: default` button matching nothing; buttons
sized to their text so stacked buttons form a ragged edge; ten equal-weight tabs with no
badge indicating where the news is.

## 8. Ordering, and why

Wave 0 first — the bugs are wrong under every design and must not be entangled with a
restyle, or the diff that fixes them becomes unreviewable.

Wave 1 second and alone. It is the shared vocabulary; building it against a real consumer
would shape it around one screen's accident.

Waves 2 and 3 next, in that order — the HUD is on every screen, so its tone table and meter
sizing get exercised hardest and earliest.

Waves 4 and 5 last. Both are self-contained, and by then the widget module has been proven
by three consumers.

## 9. Verification

Each wave lands with pytest cases under `gilded/tests/`, and every wave's gate is run by
hand before it is accepted — a green claim from the implementing agent is not evidence.
The full suite floor is **553 passing, 0 skipped** as of `2f466db` and must not fall.

Two properties of the tests matter more than coverage:

- **Assert the rule, not the constant.** `HUD_H == 118` passes while a sixth line
  reintroduces §4.1. "Every rendered line's bottom lies inside the band" does not.
- **Assert at a fixture that can discriminate.** The year test must compare at a turn where
  the two formulas differ; at turn 1 they agree and the test would pass against the bug.

Each wave also carries a withheld mutation set, built after the harness is delivered, that
reintroduces the exact defect the wave removed. A wave is accepted only when the repo's own
tests go red under it — otherwise the rule is owned by the harness, and the next wave
re-breaks it.

## 10. Open, deliberately not decided

**Should the Atlas become the permanent left half of the screen** with panels docked beside
it, rather than one tab among ten? That is a stronger change than Wave 4 and was raised with
the player without being assumed. Wave 4 improves the Atlas where it stands; promoting it is
a separate decision, taken after the widget vocabulary exists and the cost is knowable.
