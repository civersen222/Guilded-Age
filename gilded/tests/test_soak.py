"""G20 the century soak: the standing regression - a full seeded AI-only
century, checked for invariants every turn, plus a determinism replay.

There is no pytest-timeout plugin in this repo, so each test asserts its own
wall time with time.monotonic(); the two together must finish well under the
120-second budget the plan sets."""

import time

from gilded.chassis import GildedGame, TURN_BUDGET
from gilded.endings import judge

WALL_BUDGET = 120.0        # seconds; the two tests together stay well under this


def test_century_soak():
    t0 = time.monotonic()
    g = GildedGame(seed=2026)
    for _ in range(TURN_BUDGET + 1):
        g.end_turn()
        # invariants every turn:
        for h, house in g.houses.items():
            assert house.treasury == house.treasury          # no NaN
            assert 0.0 <= g.legitimacy[h] <= 100.0
        for p in g.atlas.provinces.values():
            assert p.population >= 0 and p.unrest >= 0.0
        for e in g.enterprises:
            assert 0.0 <= e.extraction_dial <= 100.0
            assert abs(e.ledger_total() - 100.0) < 1.0 or e.ledger == {}
        if g.game_over:
            break
    assert g.turn >= 30                                       # world survives to mid-game
    ep = judge(g, next(iter(g.houses)))
    assert ep.ending_key and len(ep.text) > 200
    assert time.monotonic() - t0 < WALL_BUDGET


def test_soak_determinism():
    # Character ids are per-game and the opinion matrix is process-global, so
    # the two games run one after the other (chassis resets that state on
    # construction) rather than interleaved - the same shape as
    # test_ai.test_end_turn_with_ai_is_deterministic.
    t0 = time.monotonic()
    a = GildedGame(seed=7)
    for _ in range(25):
        a.end_turn()
    a_events = [e.text for e in a.events]
    b = GildedGame(seed=7)
    for _ in range(25):
        b.end_turn()
    assert [e.text for e in b.events] == a_events
    assert time.monotonic() - t0 < WALL_BUDGET
