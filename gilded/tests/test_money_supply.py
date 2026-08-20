"""STAGE 11I: the world is printing money - pin the capital levy.

The levy takes a share of each House's treasury above the starting
purse at the end of every turn. Without it, seed 7 twelve turns of
end_turn() mints money: the total treasury inflates past the band and
three Houses drift more than 40% from their base purse.
"""

import gilded.chassis as chassis
from gilded.ai import ai_turn
from gilded.chassis import CAPITAL_LEVY_RATE, GildedGame
from gilded.houses import STARTING_TREASURY

SEED = 7
TURNS = 12
TOTAL_LO, TOTAL_HI = 13141, 16061


def _run(seed: int = SEED, turns: int = TURNS) -> GildedGame:
    g = GildedGame(seed=seed)
    for _ in range(turns):
        for h in sorted(g.houses):
            ai_turn(g, h)
        g.end_turn()
    return g


def test_levy_rate_is_set():
    # the mechanism exists and is a genuine share of the excess
    assert 0.0 < CAPITAL_LEVY_RATE < 1.0


def test_total_treasury_stays_in_band():
    g = _run()
    total = sum(h.treasury for h in g.houses.values())
    assert TOTAL_LO <= total <= TOTAL_HI, f"total {total} outside {TOTAL_LO}-{TOTAL_HI}"


def test_every_house_within_40pct_of_base_purse():
    g = _run()
    for name, h in g.houses.items():
        drift = abs(h.treasury - STARTING_TREASURY) / STARTING_TREASURY
        assert drift <= 0.40, f"{name} drift {drift:.2f} exceeds 40% of base purse"


def test_levy_drains_excess_not_base():
    # a house above its base purse is levied; a house at or below it is not
    g = _run(turns=1)
    levied = {name for name, h in g.houses.items()
              if any(note == "capital levy" for _, note, _ in h.journal)}
    for name, h in g.houses.items():
        if h.treasury > STARTING_TREASURY:
            assert name in levied, f"{h.name} above base purse must be levied"
        else:
            assert name not in levied, f"{h.name} at or below base purse must not be levied"


def test_levy_absent_inflates_total():
    # the pinned mechanism: with the levy zeroed, the total inflates
    # out of the band - the fix is the levy, not a coincidence of the seed
    old = chassis.CAPITAL_LEVY_RATE
    try:
        chassis.CAPITAL_LEVY_RATE = 0.0
        g = _run()
    finally:
        chassis.CAPITAL_LEVY_RATE = old
    total = sum(h.treasury for h in g.houses.values())
    assert total > TOTAL_HI, f"without the levy the world prints money: {total}"
