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


POP_REF = 10.0            # accident risk scales with workforce size
MAIM_CHANCE = 0.25        # chance the city's Director is caught in the machinery
WITNESS_DRIFT = 8.0       # conviction shove per witnessed accident
COVERUP_STRESS = 20       # base stress of signing a suppression order
COVERUP_UNREST_RELIEF = 3.0


def tick_extraction(city, realm=None, rng=_random) -> list:
    """One turn of the squeeze on one city: accrue unrest, roll accidents.

    Accident risk is dial x workforce (spec 5.1: the grind scales with the
    bodies fed into it). Returns a list of event strings (empty on quiet
    turns). Pass the owning realm to let accidents maim the Director and
    drift witnesses (Callous or Reformist).
    """
    events = []
    city.unrest += unrest_gain(city.extraction_dial)
    p = accident_chance(city.extraction_dial) * max(0.25, min(2.0, city.population / POP_REF))
    if rng.random() < p:
        events.extend(resolve_accident(city, realm, rng))
    return events


def resolve_accident(city, realm=None, rng=_random) -> list:
    """An industrial accident: a worker dies, the city seethes, and the harm
    climbs the ladder (spec 5.1) - the Director is sometimes maimed, and
    witnesses drift Reformist or Callous by where they already stand."""
    from event_engine import Situation, render
    from game_data import house_name
    events = []
    if city.population > 1:
        city.population -= 1
    city.unrest += ACCIDENT_UNREST
    events.append(render(Situation("industrial_accident",
                                   data={"city": city.name,
                                         "house": house_name(city.owner)})))
    if realm is None:
        return events
    from dispositions import witness_drift
    director = getattr(city, "director", None)
    ruler = getattr(realm, "ruler", None)
    if (director is not None and getattr(director, "is_alive", False)
            and rng.random() < MAIM_CHANCE):
        director.add_trait("Maimed")
        events.append(f"{director.name} is maimed in the {city.name} accident!")
        msg = director.add_stress(30)
        if msg:
            events.append(msg)
    for w in (director, ruler):
        if w is None or not getattr(w, "is_alive", False):
            continue
        line = witness_drift(w, "labor_capital", WITNESS_DRIFT,
                             f"the {city.name} accident")
        if line:
            events.append(line)
    return events


def cover_up(ruler, city) -> list:
    """The ruler signs the suppression order (spec 5.1: the cost climbs the
    ladder). Unrest is smothered now; the signer pays in stress - more if
    Honest or Compassionate - and drifts toward the Cruel end."""
    from event_engine import Situation, render
    from dispositions import apply_drift
    events = [render(Situation("cover_up",
                               data={"ruler": getattr(ruler, "name", str(ruler)),
                                     "city": city.name}))]
    city.unrest = max(0.0, city.unrest - COVERUP_UNREST_RELIEF)
    if ruler is not None and getattr(ruler, "is_alive", False):
        msg = ruler.add_stress(COVERUP_STRESS + ruler.check_stress_action("cover_up"))
        if msg:
            events.append(msg)
        line = apply_drift(ruler, "cruel_compassionate", -4.0, "signed the cover-up")
        if line:
            events.append(line)
    return events
