# Mission C1 — The Sim Becomes Visible — COMPLETE

BASE: 2092b0c (houses 7 | has ladder: False | has beats: False)

## Marker

Mission C1 is complete. The sim becomes visible: a player watching seed 7 can see
who is winning and why anything changed.

## Deliverables

| Deliverable | Location | Verified |
|---|---|---|
| Public ladder — all 7 houses ranked by the same 4-axis composite as `dashboard.scoreboard` / `endings.judge` | `gilded/ladder.py` (`ladder`, `leader`) | every axis's Causes sum exactly to its value |
| Consequence beats — strikes, strikes ending, movement hardening, dividends — each with `turn`, `source` rule, and journal-summed `causes` | `gilded/beats.py` (`beats`, `beats_for`) | fire across seed-7 turns 1–4 |
| Package exports | `gilded/__init__.py` | `gilded.ladder`, `gilded.beats`, `gilded.GildedGame` |
| Game methods | `gilded/chassis.py` | `GildedGame.ladder()`, `GildedGame.beats(house)` |
| Player visibility — Briefing tab renders the public ladder (top-5 + leader's winning cause) | `gilded/ui/broadsheet.py` | `test_briefing_shows_the_ladder` |
| Tests | `gilded/tests/test_c1_visibility.py` | 9/9 pass |

## Verification

- Full suite: `python -m pytest gilded` → **1987 passed, 0 failures**
- `probe.py` → all 5 bars pass (24/24, 24/24, 6/6, 4/4, OK)
- Seed 7, turn 1: ladder leader Ferrenholt (68.5); beats fire with provenance

## Commits

- f04904d the sim becomes visible — public ladder and consequence beats with provenance
- 011ddee expose ladder() and beats() on GildedGame, with test coverage
- a810dc8 Briefing tab shows the public ladder
- 9449914 export GildedGame at the package root
