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

# Base tree d7fa68f, seed 7, twelve turns: each House's turn-12 purse.
# Houses are SUPPOSED to diverge from the starting 2000; the gate compares
# this tree against the base tree, not against the start.
BASE_TURN12 = {
    "Ashworth": 1834,
    "Brandtner": 1181,
    "Duval-Corse": 2277,
    "Ferrenholt": 3891,
    "Karsgate": 1692,
    "Mordaine": 2608,
    "Vantrell": 1117,
}


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


def test_no_house_more_than_40pct_from_base_purse():
    g = _run()
    for name, h in sorted(g.houses.items()):
        base = BASE_TURN12[name]
        drift = abs(h.treasury - base) / base
        assert drift <= 0.40, (
            f"{name} at {h.treasury:.0f} is {drift:.0%} from base tree's "
            f"turn-12 purse {base} (d7fa68f, seed 7)"
        )
