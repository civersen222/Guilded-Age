"""Extraction, accidents and organized labor (Gilded spec section 5, "The Squeeze").

Each Enterprise carries a dial 0-100 controlling how hard the House squeezes
labor: higher = more production and dividends now, more unrest and industrial
accidents later. Unrest accrues on the enterprise's Province; past thresholds
it crystallizes into a Movement — a union that can strike. Formula bodies are
byte-identical to the root-game labor.py; the geography is provinces and
enterprises instead of cities.
"""

from typing import List

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


WORKFORCE_REF = 1.0       # accident risk scales with enterprise workforce (tiers)
MAIM_CHANCE = 0.25        # chance the Director is caught in the machinery
WITNESS_DRIFT = 8.0       # conviction shove per witnessed accident
COVERUP_STRESS = 20       # base stress of signing a suppression order
COVERUP_UNREST_RELIEF = 3.0


def _director_of(ent, realm):
    if realm is None or not ent.director_id:
        return None
    for c in getattr(realm, "characters", []):
        if c.id == ent.director_id:
            return c
    return None


def _tide_mult(tide, method: str) -> float:
    fn = getattr(tide, method, None) if tide is not None else None
    return fn() if callable(fn) else 1.0


def tick_extraction(ent, province, realm, rng, tide) -> List[str]:
    """One turn of the squeeze from one enterprise: accrue unrest on its
    province, roll accidents, and let the labor movement respond.

    Accident risk is dial x workforce (the grind scales with the bodies fed
    into it). Returns a list of event strings (empty on quiet turns). The
    ideological tide scales unrest growth; pass any object with
    movement_multiplier()/record_atrocity() (a stub is fine before G7).
    """
    events: List[str] = []
    province.unrest += unrest_gain(ent.extraction_dial) * _tide_mult(tide, "movement_multiplier")
    p = accident_chance(ent.extraction_dial) * max(0.25, min(2.0, (ent.tier) / WORKFORCE_REF))
    if rng.random() < p:
        events.extend(resolve_accident(ent, province, realm, rng, tide))
    events.extend(tick_movement(province, realm, rng))
    return events


def resolve_accident(ent, province, realm, rng, tide) -> List[str]:
    """An industrial accident: a worker dies, the province seethes, and the
    harm climbs the ladder - the Director is sometimes maimed, and witnesses
    drift Reformist or Callous by where they already stand."""
    from gilded.society.dispositions import witness_drift
    from gilded.society.event_engine import Situation, render
    events: List[str] = []
    if tide is not None and hasattr(tide, "record_atrocity"):
        tide.record_atrocity("accident", house=ent.house)
    if province.population > 1:
        province.population -= 1
    province.unrest += ACCIDENT_UNREST
    events.append(render(Situation("industrial_accident",
                                   data={"city": province.name,
                                         "house": ent.house})))
    if realm is None:
        return events
    director = _director_of(ent, realm)
    ruler = getattr(realm, "ruler", None)
    if (director is not None and getattr(director, "is_alive", False)
            and rng.random() < MAIM_CHANCE):
        director.add_trait("Maimed")
        events.append(f"{director.name} is maimed in the {province.name} accident!")
        msg = director.add_stress(30)
        if msg:
            events.append(msg)
    _drift = WITNESS_DRIFT * _tide_mult(tide, "drift_multiplier")
    for w in (director, ruler):
        if w is None or not getattr(w, "is_alive", False):
            continue
        line = witness_drift(w, "labor_capital", _drift,
                             f"the {province.name} accident")
        if line:
            events.append(line)
    return events


def cover_up(ruler, province, tide) -> List[str]:
    """The ruler signs the suppression order: unrest is smothered now; the
    signer pays in stress - more if Honest or Compassionate - and drifts
    toward the Cruel end. The lie feeds the tide harder than the accident."""
    from gilded.society.dispositions import apply_drift
    from gilded.society.event_engine import Situation, render
    events = [render(Situation("cover_up",
                               data={"ruler": getattr(ruler, "name", str(ruler)),
                                     "city": province.name}))]
    if tide is not None and hasattr(tide, "record_atrocity"):
        tide.record_atrocity("cover_up", house=province.owner)
    province.unrest = max(0.0, province.unrest - COVERUP_UNREST_RELIEF)
    if ruler is not None and getattr(ruler, "is_alive", False):
        msg = ruler.add_stress(COVERUP_STRESS + ruler.check_stress_action("cover_up"))
        if msg:
            events.append(msg)
        line = apply_drift(ruler, "cruel_compassionate", -4.0, "signed the cover-up")
        if line:
            events.append(line)
    return events


# -- Labor movements (spec 5.2) ----------------------------------------------

UNION_THRESHOLD = 25.0     # unrest at which a union crystallizes
STRIKE_THRESHOLD = 50.0    # militancy at which the strike fires
STRIKE_END = 20.0          # unrest at which a strike stands down
STRIKE_VENT = 6.0          # unrest vented per striking turn
STRIKE_OUTPUT_MULT = 0.25  # striking provinces' enterprises produce this fraction
MARTYR_MILITANCY = 40.0    # militancy surge when the leader is martyred
MARTYR_SPREAD_UNREST = 15.0
BUYOFF_RELIEF = 30.0       # militancy drop when the leader is bought

LEADER_NAMES_MALE = ["Anselm", "Bertrand", "Casimir", "Douglas", "Emil",
                     "Franek", "Gustave", "Howell", "Ivo", "Jorik"]
LEADER_NAMES_FEMALE = ["Agata", "Brida", "Celine", "Dagmar", "Edith",
                       "Freya", "Greta", "Hanne", "Ilsa", "Jenna"]


class Movement:
    """A province's organized labor (spec 5.2): a union that can strike.

    Leaders are real characters; martyrdom regionalizes."""

    def __init__(self, province_pid: int, leader=None):
        self.province_pid = province_pid
        self.leader = leader
        self.state = "union"       # "union" | "striking"
        self.militancy = 0.0
        self.martyr = None         # martyred leader's name, if it came to that


def _make_leader(province, realm, rng):
    """A firebrand organizer, created into the realm (spec 5.2). Returns
    None when no realm is wired (bare unit ticks)."""
    if realm is None:
        return None
    from gilded.society.characters import Character
    gender = "Female" if rng.random() < 0.5 else "Male"
    pool = LEADER_NAMES_FEMALE if gender == "Female" else LEADER_NAMES_MALE
    name = f"{rng.choice(pool)} of the {province.name} union"
    leader = Character(name, {"industry": 6, "statecraft": 10,
                              "command": 6, "intrigue": 8}, [],
                       age=int(25 + rng.random() * 15), gender=gender)
    leader.dispositions["labor_capital"] = -70.0   # a true believer
    realm.characters.append(leader)
    promoted = getattr(realm, "promoted_ids", None)
    if promoted is not None:
        promoted.add(leader.id)
    return leader


def tick_movement(province, realm, rng) -> List[str]:
    """Unrest crystallizes into organization (spec 5.2): union, then
    strike. A striking province vents unrest each turn but its enterprises
    produce almost nothing (chassis applies STRIKE_OUTPUT_MULT) until
    unrest falls to STRIKE_END."""
    events: List[str] = []
    mv = getattr(province, "movement", None)
    if mv is None:
        if realm is not None and province.unrest >= UNION_THRESHOLD:
            leader = _make_leader(province, realm, rng)
            province.movement = Movement(province.pid, leader)
            who = f" under {leader.name}" if leader is not None else ""
            events.append(f"The workers of {province.name} organize{who} - a union is born")
        return events
    if mv.leader is not None and not mv.leader.is_alive and mv.martyr is None:
        mv.leader = None   # a quietly dead leader just leaves; martyrs are made
    if mv.state == "striking":
        province.unrest = max(0.0, province.unrest - STRIKE_VENT)
        if province.unrest <= STRIKE_END:
            mv.state = "union"
            mv.militancy = province.unrest
            events.append(f"The {province.name} strike stands down; the works breathe again")
        return events
    mv.militancy = min(100.0, max(mv.militancy, province.unrest))
    if mv.militancy >= STRIKE_THRESHOLD:
        mv.state = "striking"
        events.append(f"STRIKE in {province.name}! The works fall silent")
    return events


def martyr_leader(mv, province, provinces, realm, rng, tide) -> List[str]:
    """Kill the movement's leader and reap the whirlwind (spec 5.2):
    martyrdom surges militancy and regionalizes - the nearest sister
    province of the same House organizes in the martyr's name. The loudest
    atrocity the tide knows."""
    events: List[str] = []
    leader = mv.leader
    if leader is None:
        return events
    leader.is_alive = False
    mv.martyr = leader.name
    mv.militancy = min(100.0, mv.militancy + MARTYR_MILITANCY)
    if tide is not None and hasattr(tide, "record_atrocity"):
        tide.record_atrocity("martyrdom", house=province.owner)
    events.append(f"{leader.name} is martyred - {province.name} will not forget")
    if not provinces:
        return events
    others = [p for p in provinces
              if p is not province and p.owner == province.owner
              and getattr(p, "movement", None) is None]
    if not others:
        return events
    cx, cy = province.center
    others.sort(key=lambda p: (abs(p.center[0] - cx) + abs(p.center[1] - cy), p.pid))
    target = others[0]
    target.unrest += MARTYR_SPREAD_UNREST
    target.movement = Movement(target.pid, _make_leader(target, realm, rng))
    events.append(f"The movement spreads: {target.name} organizes in {mv.martyr}'s name")
    return events


def buy_off_leader(mv, province) -> List[str]:
    """Gold quiets the firebrand (spec 5.2): militancy drops; a movement
    left leaderless and cold dissolves."""
    events: List[str] = []
    if mv.leader is not None:
        mv.leader.dispositions["labor_capital"] = 0.0
        events.append(f"{mv.leader.name} takes the House's money and softens")
        mv.leader = None
    mv.militancy = max(0.0, mv.militancy - BUYOFF_RELIEF)
    if mv.militancy < UNION_THRESHOLD and mv.state != "striking":
        province.movement = None
        events.append(f"The {province.name} union dissolves in recrimination")
    return events