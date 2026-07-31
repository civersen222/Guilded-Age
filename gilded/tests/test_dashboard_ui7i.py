"""UI7i: own Scoreboard.turn as a rule (two distinct inputs), not an example."""

from __future__ import annotations

from gilded.chassis import GildedGame
from gilded.dashboard import scoreboard


def _game():
    g = GildedGame(seed=42)
    h = sorted(g.houses)[0]
    g.houses[h].is_player = True
    return g, h


def test_scoreboard_turn_at_turn_5():
    """Scoreboard.turn must track game.turn — exercised at turn 5."""
    g, h = _game()
    g.turn = 5
    b = scoreboard(g, h)
    assert b.turn == 5


def test_scoreboard_turn_at_turn_42():
    """Scoreboard.turn must track game.turn — exercised at turn 42."""
    g, h = _game()
    g.turn = 42
    b = scoreboard(g, h)
    assert b.turn == 42
