"""I5a — numbers travel with their causes; the secret revolution counter becomes visible.

Three things:
  1. Attributed values — every number carries its causes (provenance.Cause + Attributed)
  2. Causes explain deltas — causes.sum(amount) == value - previous
  3. Secret revolution counter visible — brewing_turns appears in the scoreboard/dashboard
"""

import pytest
from gilded.provenance import Cause, Attributed
from gilded.society.ideology import IdeologicalTide, tick_legitimacy
from gilded.chassis import GildedGame
from gilded.dashboard import scoreboard

# ─── 1. Attributed values carry causes ────────────────────────────────

def test_attributed_carries_value_and_previous():
    a = Attributed(value=120, previous=100, causes=(Cause("mint", 20, "treasury"),))
    assert a.value == 120
    assert a.previous == 100

def test_attributed_delta():
    a = Attributed(value=120, previous=100, causes=())
    assert a.delta == 20

def test_attributed_negative_delta():
    a = Attributed(value=90, previous=100, causes=(Cause("tax", -10, "govt"),))
    assert a.delta == -10

# ─── 2. Causes explain deltas ────────────────────────────────────────

def test_cause_fields():
    c = Cause(label="gold_mint", amount=20, source="treasury")
    assert c.label == "gold_mint"
    assert c.amount == 20
    assert c.source == "treasury"

def test_attributed_check_passes_when_causes_sum_to_delta():
    a = Attributed(
        value=120, previous=100,
        causes=(Cause("mint", 15, "treasury"), Cause("trade", 5, "market"))
    )
    assert a.check() is True

def test_attributed_check_fails_when_causes_dont_sum():
    a = Attributed(
        value=120, previous=100,
        causes=(Cause("mint", 5, "treasury"),)
    )
    assert a.check() is False

def test_attributed_check_empty_causes_for_zero_delta():
    a = Attributed(value=100, previous=100, causes=())
    assert a.check() is True

def test_attributed_check_tolerance():
    a = Attributed(
        value=120, previous=100,
        causes=(Cause("mint", 19.999999, "treasury"), Cause("trade", 0.000001, "market"))
    )
    assert a.check() is True

# ─── 3. tick_legitimacy returns Attributed ────────────────────────────

def test_tick_legitimacy_returns_attributed():
    result = tick_legitimacy(current=50.0, happiness=8, tide=None, fresh_atrocities=0.0)
    assert isinstance(result, Attributed)

def test_tick_legitimacy_attributed_has_delta():
    result = tick_legitimacy(current=50.0, happiness=8, tide=None, fresh_atrocities=0.0)
    assert hasattr(result, 'delta')
    assert isinstance(result.delta, (int, float))

def test_tick_legitimacy_attributed_has_causes():
    result = tick_legitimacy(current=50.0, happiness=8, tide=None, fresh_atrocities=0.0)
    assert hasattr(result, 'causes')
    assert isinstance(result.causes, tuple)

# ─── 4. Secret revolution counter becomes visible ────────────────────

def test_brewing_turns_in_scoreboard():
    game = GildedGame(seed=42)
    sb = scoreboard(game, list(game.houses)[0])
    assert hasattr(sb, 'brewing_turns')

def test_brewing_turns_is_int():
    game = GildedGame(seed=42)
    sb = scoreboard(game, list(game.houses)[0])
    assert isinstance(sb.brewing_turns, int)

def test_tide_level_in_scoreboard():
    game = GildedGame(seed=42)
    sb = scoreboard(game, list(game.houses)[0])
    assert hasattr(sb, 'tide_level')
    assert isinstance(sb.tide_level, float)

def test_tide_phase_in_scoreboard():
    game = GildedGame(seed=42)
    sb = scoreboard(game, list(game.houses)[0])
    assert hasattr(sb, 'tide_phase')
    assert isinstance(sb.tide_phase, str)

# ─── 5. Integration: numbers travel with causes through the game ──────

def test_tide_tick_rises():
    tide = IdeologicalTide()
    initial = tide.level
    tide.tick()
    assert tide.level > initial

def test_tide_atrocity_records_in_atrocities():
    tide = IdeologicalTide()
    tide.record_atrocity("martyrdom", house="House A")
    assert tide.atrocities > 0
    assert "House A" in tide.house_atrocities

def test_tide_phase_progression():
    tide = IdeologicalTide()
    assert tide.phase() == "reformist"
    tide.level = 40.0
    assert tide.phase() == "socialist"
    tide.level = 70.0
    assert tide.phase() == "revolutionary"

# ─── 6. Measurement: dashboard shows the revolution counter ───────────

def test_scoreboard_shows_brewing_turns_from_game():
    game = GildedGame(seed=42)
    house_name = list(game.houses)[0]
    game.brewing_turns[house_name] = 5
    sb = scoreboard(game, house_name)
    assert sb.brewing_turns == 5

def test_scoreboard_brewing_zero_when_not_brewing():
    game = GildedGame(seed=42)
    house_name = list(game.houses)[0]
    game.brewing_turns[house_name] = 0
    sb = scoreboard(game, house_name)
    assert sb.brewing_turns == 0

def test_scoreboard_tide_reflects_game_tide():
    game = GildedGame(seed=42)
    game.tide.level = 45.0
    sb = scoreboard(game, list(game.houses)[0])
    assert sb.tide_level == 45.0


# ─── 7. Measurement: revolution explanation names its causes ──────────

def test_revolution_explanation_empty_when_not_brewing():
    """When brewing_turns is 0, the explanation is empty."""
    game = GildedGame(seed=42)
    house_name = list(game.houses)[0]
    game.brewing_turns[house_name] = 0
    game.legitimacy[house_name] = 5.0  # below floor
    sb = scoreboard(game, house_name)
    assert sb.revolution_explanation == "", \
        f"Expected empty explanation when brewing=0, got '{sb.revolution_explanation}'"


def test_revolution_explanation_names_low_legitimacy():
    """When legitimacy is below floor, explanation mentions mandate collapsed."""
    game = GildedGame(seed=42)
    house_name = list(game.houses)[0]
    game.brewing_turns[house_name] = 1
    game.legitimacy[house_name] = 5.0  # below REVOLUTION_LEGITIMACY_FLOOR
    # Ensure no province is striking at peak militancy
    provs = game.provinces_of(house_name)
    for p in provs:
        mv = getattr(p, "movement", None)
        if mv is not None:
            mv.militancy = 0.0
    sb = scoreboard(game, house_name)
    assert "mandate collapsed" in sb.revolution_explanation, \
        f"Expected 'mandate collapsed' in explanation, got '{sb.revolution_explanation}'"


def test_revolution_explanation_names_striking_province():
    """When a province is striking at peak militancy, explanation names it."""
    game = GildedGame(seed=42)
    house_name = list(game.houses)[0]
    game.brewing_turns[house_name] = 1
    game.legitimacy[house_name] = 50.0  # above floor — legitimacy NOT a cause
    provs = game.provinces_of(house_name)
    # Make the first province striking at peak militancy
    target = provs[0]
    mv = getattr(target, "movement", None)
    if mv is None:
        pytest.skip("No movement on province")
    mv.state = "striking"
    mv.militancy = 70.0  # above REVOLUTION_MILITANCY_PEAK
    # Ensure other provinces are not striking
    for p in provs[1:]:
        other_mv = getattr(p, "movement", None)
        if other_mv is not None:
            other_mv.militancy = 0.0
    sb = scoreboard(game, house_name)
    assert target.name in sb.revolution_explanation, \
        f"Expected province name '{target.name}' in explanation, got '{sb.revolution_explanation}'"
    assert "striking" in sb.revolution_explanation, \
        f"Expected 'striking' in explanation, got '{sb.revolution_explanation}'"


def test_revolution_explanation_severed_wire():
    """Severing revolution_explanation in scoreboard() is caught."""
    game = GildedGame(seed=42)
    house_name = list(game.houses)[0]
    game.brewing_turns[house_name] = 1
    game.legitimacy[house_name] = 5.0
    sb = scoreboard(game, house_name)
    # If the field is missing or not populated, this assertion fails
    assert hasattr(sb, "revolution_explanation"), \
        "Scoreboard must have revolution_explanation field"
    assert sb.revolution_explanation != "", \
        "With brewing_turns=1 and low legitimacy, explanation must not be empty"
