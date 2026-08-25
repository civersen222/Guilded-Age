# Mission C1 Wave 2 — Same Contract, Exact API Shape — COMPLETE

BASE: 185e9ec (wave 1 head). No source changes were required: wave 2 re-verifies
the exact API shape against the contract and commits the marker.

## Marker

Mission C1 wave 2 holds. The public API is exactly the contracted shape, verified
on a clean checkout at 185e9ec.

## API shape (verified by probe against seed 7, 12 turns)

| Contract point | Where | Verified |
|---|---|---|
| `ladder(game)` / `game.ladder()` → `List[LadderRow]`, all 7 houses, ranks 1..N by descending composite | `gilded/ladder.py` | `sorted(r.house for r in rows) == sorted(game.houses)`, `r.rank == i+1` |
| `LadderRow.composite` — float, equals `dashboard._composite(_axes_for(...))` | `gilded/ladder.py` | `test_ladder_composite_matches_scoreboard` |
| `LadderRow.axes` — `Dict[str, Attributed]`, each `Attributed(value, previous, causes)` with `check()` holding | `gilded/provenance.py` | every axis's Causes sum exactly to the delta |
| Every `Cause(label, amount, source)` names the rule that produced it | `gilded/provenance.py` | `test_ladder_causes_sum_to_their_axis` |
| `leader(game)` — rank-1 row with a named top cause per axis | `gilded/ladder.py` | `test_leader_is_the_winning_house` |
| `beats(game, house=None, turn=None)` — optional house; no-arg is the public view across every House; every beat names a real house | `gilded/beats.py` | `test_beats_public_view_without_a_house` |
| `Beat(turn, source, text, causes, kind, house)` — provenance per beat; dividend beats carry Causes summing to the turn's treasury net | `gilded/beats.py` | `test_beats_carry_provenance` |
| `game.beats(house) == beats_for(game, house)`, `game.ladder() == ladder(game)` | `gilded/chassis.py` | `test_game_exposes_ladder_and_beats` |
| Pure and deterministic — `beats`/`ladder` mutate nothing; identical on identical seeds | `gilded/beats.py`, `gilded/ladder.py` | `test_beats_deterministic`, `test_beats_pure_no_mutation` |
| Package exports `GildedGame`, `ladder`, `beats` | `gilded/__init__.py` | importable as `gilded.GildedGame` |
| Briefing tab renders the public ladder (top-5 + leader's winning cause) | `gilded/ui/broadsheet.py` | `test_briefing_shows_the_ladder` |

## Verification (this wave, on a clean tree at 185e9ec)

- `python -m pytest gilded/tests/test_c1_visibility.py` → **10/10 pass**
- `python -m pytest gilded` → **1988 passed, 0 failures** (matches the learning: no pre-existing failures at this base)
- API-shape probe (seed 7, 12 turns): 7 LadderRows, rank 1 present, every axis `Attributed.check()` true, every Cause sourced, 11 public beats all naming real houses, `game.ladder() == ladder(game)`, `leader(g).house == rows[0].house`
