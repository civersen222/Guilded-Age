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


def tick_extraction(city, realm=None, rng=_random, tide=None) -> list:
    """One turn of the squeeze on one city: accrue unrest, roll accidents,
    and let the labor movement respond (spec 5.1/5.2).

    Accident risk is dial x workforce (spec 5.1: the grind scales with the
    bodies fed into it). Returns a list of event strings (empty on quiet
    turns). Pass the owning realm to let accidents maim the Director,
    drift witnesses, and let unrest crystallize into a movement - with no
    realm wired, the tick stays movement-free. Pass the world's
    IdeologicalTide (M58) and the rising water scales unrest growth.
    """
    events = []
    _mult = tide.movement_multiplier() if tide is not None else 1.0
    city.unrest += unrest_gain(city.extraction_dial) * _mult
    p = accident_chance(city.extraction_dial) * max(0.25, min(2.0, city.population / POP_REF))
    if rng.random() < p:
        events.extend(resolve_accident(city, realm, rng, tide))
    events.extend(tick_movement(city, realm, rng))
    return events


def resolve_accident(city, realm=None, rng=_random, tide=None) -> list:
    """An industrial accident: a worker dies, the city seethes, and the harm
    climbs the ladder (spec 5.1) - the Director is sometimes maimed, and
    witnesses drift Reformist or Callous by where they already stand.
    Feeds the ideological tide (M58); a high tide drifts witnesses harder."""
    from event_engine import Situation, render
    from game_data import house_name
    events = []
    if tide is not None:
        tide.record_atrocity("accident")
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
    _drift = WITNESS_DRIFT * (tide.drift_multiplier() if tide is not None else 1.0)
    for w in (director, ruler):
        if w is None or not getattr(w, "is_alive", False):
            continue
        line = witness_drift(w, "labor_capital", _drift,
                             f"the {city.name} accident")
        if line:
            events.append(line)
    return events


def cover_up(ruler, city, tide=None) -> list:
    """The ruler signs the suppression order (spec 5.1: the cost climbs the
    ladder). Unrest is smothered now; the signer pays in stress - more if
    Honest or Compassionate - and drifts toward the Cruel end. The lie
    feeds the ideological tide (M58) harder than the accident did."""
    from event_engine import Situation, render
    from dispositions import apply_drift
    events = [render(Situation("cover_up",
                               data={"ruler": getattr(ruler, "name", str(ruler)),
                                     "city": city.name}))]
    if tide is not None:
        tide.record_atrocity("cover_up")
    city.unrest = max(0.0, city.unrest - COVERUP_UNREST_RELIEF)
    if ruler is not None and getattr(ruler, "is_alive", False):
        msg = ruler.add_stress(COVERUP_STRESS + ruler.check_stress_action("cover_up"))
        if msg:
            events.append(msg)
        line = apply_drift(ruler, "cruel_compassionate", -4.0, "signed the cover-up")
        if line:
            events.append(line)
    return events


# ── Labor movements (M57, spec 5.2) ─────────────────────────────────────────

UNION_THRESHOLD = 25.0     # unrest at which a union crystallizes
STRIKE_THRESHOLD = 50.0    # militancy at which the strike fires
STRIKE_END = 20.0          # unrest at which a strike stands down
STRIKE_VENT = 6.0          # unrest vented per striking turn
MARTYR_MILITANCY = 40.0    # militancy surge when the leader is martyred
MARTYR_SPREAD_UNREST = 15.0
BUYOFF_RELIEF = 30.0       # militancy drop when the leader is bought


class Movement:
    """A city's organized labor (spec 5.2): a union that can strike.

    Leaders are real Tier-1 characters; martyrdom regionalizes."""

    def __init__(self, city_name: str, leader=None):
        self.city_name = city_name
        self.leader = leader
        self.state = "union"       # "union" | "striking"
        self.militancy = 0.0
        self.martyr = None         # martyred leader's name, if it came to that


def _make_leader(city, realm, rng=_random):
    """A firebrand organizer, created into the realm and pinned Tier-1
    (spec 5.2/3.1). Returns None when no realm is wired (bare unit ticks)."""
    if realm is None:
        return None
    from simulation import Character
    from population import promote
    from realms import MALE_NAMES, FEMALE_NAMES
    gender = "Female" if rng.random() < 0.5 else "Male"
    pool = FEMALE_NAMES if gender == "Female" else MALE_NAMES
    name = f"{rng.choice(pool)} of the {city.name} union"
    leader = Character(name, {"stewardship": 6, "diplomacy": 10,
                              "martial": 6, "intrigue": 8}, [],
                       age=int(25 + rng.random() * 15), gender=gender)
    leader.dispositions["labor_capital"] = -70.0   # a true believer
    realm.characters.append(leader)
    promote(realm, leader)
    return leader


def tick_movement(city, realm=None, rng=_random) -> list:
    """Unrest crystallizes into organization (spec 5.2): union, then
    strike. A striking works vents unrest each turn but produces nothing
    (city.calculate_yields) until unrest falls to STRIKE_END."""
    events = []
    mv = getattr(city, "movement", None)
    if mv is None:
        if realm is not None and city.unrest >= UNION_THRESHOLD:
            leader = _make_leader(city, realm, rng)
            city.movement = Movement(city.name, leader)
            who = f" under {leader.name}" if leader is not None else ""
            events.append(f"The workers of {city.name} organize{who} - a union is born")
        return events
    if mv.leader is not None and not mv.leader.is_alive and mv.martyr is None:
        mv.leader = None   # a quietly dead leader just leaves; martyrs are made
    if mv.state == "striking":
        city.unrest = max(0.0, city.unrest - STRIKE_VENT)
        if city.unrest <= STRIKE_END:
            mv.state = "union"
            mv.militancy = city.unrest
            events.append(f"The {city.name} strike stands down; the works breathe again")
        return events
    mv.militancy = min(100.0, max(mv.militancy, city.unrest))
    if mv.militancy >= STRIKE_THRESHOLD:
        mv.state = "striking"
        events.append(f"STRIKE in {city.name}! The works fall silent")
    return events


def martyr_leader(mv, city, cities=None, realm=None, rng=_random, tide=None) -> list:
    """Kill the movement's leader and reap the whirlwind (spec 5.2):
    martyrdom surges militancy and regionalizes - the nearest sister city
    of the same House organizes in the martyr's name. The loudest atrocity
    the tide knows (M58)."""
    events = []
    leader = mv.leader
    if leader is None:
        return events
    leader.is_alive = False
    mv.martyr = leader.name
    mv.militancy = min(100.0, mv.militancy + MARTYR_MILITANCY)
    if tide is not None:
        tide.record_atrocity("martyrdom")
    events.append(f"{leader.name} is martyred - {city.name} will not forget")
    if not cities:
        return events
    others = [c for c in cities
              if c is not city and c.owner == city.owner
              and getattr(c, "movement", None) is None]
    if not others:
        return events
    cx, cy = city.position
    others.sort(key=lambda c: abs(c.position[0] - cx) + abs(c.position[1] - cy))
    target = others[0]
    target.unrest += MARTYR_SPREAD_UNREST
    target.movement = Movement(target.name, _make_leader(target, realm, rng))
    events.append(f"The movement spreads: {target.name} organizes in {mv.martyr}'s name")
    return events


def buy_off_leader(mv, city) -> list:
    """Gold quiets the firebrand (spec 5.2): militancy drops; a movement
    left leaderless and cold dissolves."""
    events = []
    if mv.leader is not None:
        mv.leader.dispositions["labor_capital"] = 0.0
        events.append(f"{mv.leader.name} takes the House's money and softens")
        mv.leader = None
    mv.militancy = max(0.0, mv.militancy - BUYOFF_RELIEF)
    if mv.militancy < UNION_THRESHOLD and mv.state != "striking":
        city.movement = None
        events.append(f"The {city.name} union dissolves in recrimination")
    return events
