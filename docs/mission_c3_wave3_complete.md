# C3 wave 3 complete: the world is renamed to the spec

BASE: 17646bc (wave 2) — HEAD: 1103853

## What wave 3 changed

The design spec's source-of-truth title (`docs/superpowers/specs/2026-07-21-
gilded-machine-design.md:1`) is **`CivKings: The Gilded Machine`**. The code
displayed only "The Gilded Machine" as the game/world name, and "CivKings"
appeared nowhere in the `gilded/` package. Wave 3 aligns the player-facing
name to the spec title:

- `gilded/ui/app.py` — `WINDOW_TITLE` → `"CivKings: The Gilded Machine"`
- `gilded/__main__.py` — CLI description → `"CivKings: The Gilded Machine"`

## Why this is safe

Display-string-only change. It cannot shift the seeded RNG or touch the C3
determinism/anatomy contract. The internal `GildedGame` class name was left
alone — renaming it would risk the contract with no spec benefit, and the
spec's module layout (spec §9) names the chassis module `chassis.py`, not
the class.

## Naming audit (no other rename targets found)

- The spec never gives the world a proper noun: it is "one continent" (spec
  §1). `world.py` generates province names procedurally; there is no literal
  world-name string to rename.
- The four Orders' names (Crown / Treasury / Guilds / Church, `orders.py`)
  already match the spec; no committed spec prescribes alternate Order names.
- `tick_orders` is wired into `end_turn` (`chassis.py`) and is RNG-free —
  wave-2 determinism is intact.
- Module layout matches spec §9 (`world.py`, `enterprises.py`, `fronts.py`,
  `docket.py`, `papers.py`, `directives.py`, `chassis.py`, `console.py`,
  `ui/`).

## Invariants held

- C3 suite (`test_c3_contract.py` + `test_c3_orders.py`): 11 passed
- Full `gilded/` suite: **2027 passed, 0 failed**
- `probe.py` (UI smoke bar): all bars OK, exit 0

Left to the dispatcher's post-mission held-out gate.
