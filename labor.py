"""Extraction dial (M55, deep-systems spec 5.1 "The Squeeze").

Each city has a dial 0-100 controlling how hard the House squeezes labor:
higher = more production and dividends now, more unrest and industrial
accidents later. Labor movements consume the unrest accumulator in M56+.
"""

import random as _random

DIAL_MIN = 0.0
DIAL_MAX = 100.0
DIAL_DEFAULT = 50.0
ACCIDENT_UNREST = 5.0


def clamp_dial(value: float) -> float:
    return max(DIAL_MIN, min(DIAL_MAX, float(value)))


def production_multiplier(dial: float) -> float:
    """0.75x at dial 0, 1.0x at 50, 1.25x at 100."""
    return 0.75 + 0.005 * clamp_dial(dial)


def dividend_multiplier(dial: float) -> float:
    """0.6x at dial 0, 1.0x at 50, 1.4x at 100 - owners gain most from the squeeze."""
    return 0.6 + 0.008 * clamp_dial(dial)


def unrest_gain(dial: float) -> float:
    """Per-turn unrest accrual: quadratic, so dial 90 is ~9x dial 30."""
    d = clamp_dial(dial)
    return d * d / 2000.0


def accident_chance(dial: float) -> float:
    """Industrial-accident probability per turn: zero at dial <= 40."""
    d = clamp_dial(dial)
    over = max(0.0, d - 40.0)
    return over * over / 18000.0


def dial_from_ruler(ruler) -> float:
    """Where an AI ruler sets the dial, from conviction dispositions.

    Capitalists/Robber Barons (labor_capital > 0) and Extractionists
    (preservationist_extractionist > 0) run hot; Labor Sympathizers and
    Preservationists run cool. No ruler = the neutral default.
    """
    if ruler is None:
        return DIAL_DEFAULT
    disp = getattr(ruler, "dispositions", None) or {}
    lc = disp.get("labor_capital", 0)
    pe = disp.get("preservationist_extractionist", 0)
    return clamp_dial(DIAL_DEFAULT + lc * 0.35 + pe * 0.15)


def tick_extraction(city, rng=_random) -> list:
    """One turn of the squeeze on one city: accrue unrest, roll accidents.

    Returns a list of event strings (empty on quiet turns). An accident
    kills a citizen and spikes unrest by ACCIDENT_UNREST.
    """
    events = []
    city.unrest += unrest_gain(city.extraction_dial)
    if rng.random() < accident_chance(city.extraction_dial):
        if city.population > 1:
            city.population -= 1
        city.unrest += ACCIDENT_UNREST
        events.append(
            f"Industrial accident in {city.name}! A worker is dead and the city seethes.")
    return events
