"""Extraction dial formulas (Gilded spec section 5, "The Squeeze").

Each Enterprise carries a dial 0-100 controlling how hard the House squeezes
labor: higher = more production and dividends now, more unrest and industrial
accidents later. This file holds the pure formulas (bodies byte-identical to
the root-game labor.py); the Movement layer arrives in mission G6.
"""

DIAL_MIN = 0.0
DIAL_MAX = 100.0
DIAL_DEFAULT = 50.0


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
