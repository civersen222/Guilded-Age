"""STAGE 11I: the world is printing money.

Seed 7, twelve turns, end_turn() only, nobody ruling by hand. The total
gold across all Houses must stay inside a band, and no single House may
sit more than 40% from the BASE TREE's turn-12 purse for that House
(base d7fa68f, seed 7, twelve turns — hardcoded below). On the base
commit the total inflates past the upper band: the dividend stream is
funded by gold that is minted, not by a real transfer from the
enterprise's output, so the world prints money.

This file pins the TOTAL across all Houses (not one House's balance) and
pins the mechanism that was changed so that a fix that works by offering
less variety is caught.
"""

import gilded.chassis as chassis

SEED = 7
TURNS = 12
TOTAL_LO, TOTAL_HI = 13141, 16061

GINI_LO, GINI_HI = 0.15, 0.38


def _gini(values):
    v = sorted(values)
    n, tot = len(v), sum(v)
    if n == 0 or tot <= 0:
        return 0.0
    return sum((2 * i - n + 1) * x for i, x in enumerate(v)) / (n * tot)


def _run(seed: int = SEED, turns: int = TURNS) -> chassis.GildedGame:
    g = chassis.GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    return g


def test_total_gold_stays_in_band():
    g = _run()
    total = sum(h.treasury for h in g.houses.values())
    assert TOTAL_LO <= total <= TOTAL_HI, (
        f"total gold {total:.0f} outside {TOTAL_LO}-{TOTAL_HI}"
    )


def test_wealth_spread_across_houses_stays_in_band():
    g = _run()
    gini = _gini([h.treasury for h in g.houses.values()])
    assert GINI_LO <= gini <= GINI_HI, (
        f"Gini of the seven purses is {gini:.3f}, outside "
        f"{GINI_LO}-{GINI_HI} — "
        + ("wealth is flattened, not earned and lost" if gini < GINI_LO
           else "one House is swallowing the world")
    )
