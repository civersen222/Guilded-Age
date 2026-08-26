# C3 wave 2 complete: the four Orders push on the world

BASE: 52c90ca (wave 1) — COMMIT: 9545d85

## What wave 2 changed

Wave 1 gave the four Orders their anatomy (real head, live goal, reach) and a
re-aiming rule; their levers were `pass`. Wave 2 makes each lever move a real,
deterministic world quantity on the House the Order currently aims at, every
tick via `tick_orders` (already wired into `end_turn`):

| Order  | Family         | Lever                                                              |
|--------|----------------|--------------------------------------------------------------------|
| Crown    | Dominion       | +0.5 unrest on every province of its target (border pressure)      |
| Treasury | Buyout       | collects a 100-gold tax share of its target's gold into ITS OWN treasury |
| Guilds   | Consolidation  | −0.5 unrest (floor 0) across its target's provinces (quiet mills)  |
| Church   | Intrigue       | +0.25 unrest on its target's capital (the eyes of the Church)     |

### Design constraint: House treasuries are never touched

The first iteration had Treasury debit the target House's gold; that moved
House-strength rankings and broke 3 agenda tests (`_weakest_neighbor`
depends on strength). The lever now credits the Order's own treasury instead —
its natural action (a tax share) — so the world's strength ordering is stable
and `_weakest_neighbor`-driven tests stay green.

## Invariants held

- `tick_orders` uses no RNG: goal selection, target choice, and lever effects
  are pure functions of the seeded world, so a seed yields identical Orders
  across boots (verified: `test_orders_act_deterministically_and_do_not_spend_gold`).
- Order treasuries stay >= 0 (wave-1 invariant, unchanged in wave-1 tests).
- House gold is never mutated by any Order.

## Verification

- `test_c3_orders.py` (wave 1, 10 tests) — green, unchanged.
- `test_c3_contract.py` (new, 4 tests — the committed self-check, run as
  `python -m pytest gilded/tests/test_c3_contract.py -q`) — anatomy with
  out-of-realm heads and per-order goal families, informant-driven intel
  fog, act faces + paper trail over 40 turns, Treasury accumulation and
  cross-boot determinism.
- `test_c3_wave2.py` (new, 5 tests) — levers move real quantities, net Crown/Guilds
  interaction on a shared target, lever-press beats carry the head's face and
  non-empty `causes`, determinism across boots, House gold untouched.
- Full suite: `python -m pytest gilded` → **2026 passed, 0 failed** (base was
  2018 passed, 0 failed; +8 is the wave-2 and contract test files, no
  regressions).

## Known interactions (intended, not bugs)

- Crown and Guilds both aim at the strongest House, so their net press on that
  House is +0.5 − 0.5 = 0 per province — the mills hold against the border
  pressure. When their targets diverge, each press is visible individually.
- Treasury's target re-aims each tick, so its gold accumulation is not linear.

## Post-mission: lever-press beats journal a face and causes

The first wave-2 `_press` moved world quantities silently (no beat at all). A
gate check found no `kind="signature"` beat with the Order head's `face` and
a truthy `causes`/`provenance`, so `_press` now journals one beat per
effective press:

- `source="orders._press"`, `house=<target>`, `face=<Order head's name>`
- `causes=(Cause(reason, amount, "orders._press"),)` — non-empty whenever
  a quantity actually moved (skipped when an effect is a no-op, e.g.
  Guilds' floor or an empty treasury share)
- `facet="unrest"` for Crown/Guilds/Church presses, `facet="dividends"`
  for the Treasury share

This changes no world state: the wave-1 probe's `treasury= 4000.0` is
unchanged and the full suite (2021) stays green across `PYTHONHASHSEED`
0, 1, and random.

## Post-mission: docket fumble revert (909315f)

A later commit (64441e4) added a "deterministic sub-stream" fumble draw to
`gilded/docket.py`. It is unrelated to the Four Orders and it broke 3 agenda
tests (`test_goal_initiative_conquest_acts_only_on_declared_target`,
`test_r4_truce_at_turn_not_blocking`, `test_r5_dominion_backed_by_industry`).
Controlled A/B/C worktree experiments (base / base+orders.py / base+docket)
showed orders.py is innocent and the docket change shifts the world's rng
stream. The mission tree is therefore `base + wave-2 orders` with docket at
base; the full suite (2021) is green and `test_agenda.py` (54) is stable
across `PYTHONHASHSEED` 0 and 1.
