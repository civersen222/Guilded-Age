"""Ideological tide (Gilded spec section 5, "the rising water").

A single world-wide meter rising across the century: reformism ->
socialism -> revolutionary pressure. Every atrocity ANY House commits
anywhere accelerates it; the tide in turn scales movement growth and
conviction-drift pressure world-wide. Legitimacy and revolution read
from it. Tide/legitimacy/scandal bodies are byte-identical to the root
ideology.py; revolution and transformation run over provinces and
enterprise lists instead of cities.
"""

from typing import List, Tuple

from gilded.society.labor import DIAL_DEFAULT

TIDE_BASE_RISE = 0.25          # per turn: ~25 points over a 100-turn century
ATROCITY_TIDE = 0.15           # tide points per unit of atrocity weight
ATROCITY_WEIGHTS = {
    "accident": 1.0,
    "cover_up": 2.0,
    "martyrdom": 4.0,
    "assassination": 6.0,
}


class IdeologicalTide:
    """The century's rising water (spec 5.2): 0 is quiet reformism,
    100 is revolutionary pressure everywhere."""

    def __init__(self):
        self.level = 0.0        # 0-100
        self.atrocities = 0.0   # lifetime weighted atrocity count
        self.house_atrocities = {}   # house -> lifetime weighted count
        self.fresh_atrocities = {}   # house -> weight since last legitimacy tick

    def tick(self):
        """One turn of history grinding forward."""
        self.level = min(100.0, self.level + TIDE_BASE_RISE)

    def record_atrocity(self, kind: str, house=None) -> float:
        """An atrocity anywhere feeds the tide everywhere; the House that
        committed it also carries the stain."""
        w = ATROCITY_WEIGHTS.get(kind, 1.0)
        self.atrocities += w
        self.level = min(100.0, self.level + w * ATROCITY_TIDE)
        if house is not None:
            self.house_atrocities[house] = self.house_atrocities.get(house, 0.0) + w
            self.fresh_atrocities[house] = self.fresh_atrocities.get(house, 0.0) + w
        return w

    def consume_fresh(self, house) -> float:
        """Pop the atrocity weight a House accrued since the last tick."""
        return self.fresh_atrocities.pop(house, 0.0)

    def movement_multiplier(self) -> float:
        """Scales unrest accrual and movement growth (1.0x -> 2.0x)."""
        return 1.0 + self.level / 100.0

    def drift_multiplier(self) -> float:
        """Scales witness conviction drift (1.0x -> 2.0x)."""
        return 1.0 + self.level / 100.0

    def phase(self) -> str:
        """reformist -> socialist -> revolutionary, by thirds."""
        if self.level >= 200.0 / 3.0:
            return "revolutionary"
        if self.level >= 100.0 / 3.0:
            return "socialist"
        return "reformist"


# --- Legitimacy (spec 5.3): a House's mandate to rule -----------------------

LEGITIMACY_START = 70.0           # every House begins with a workable mandate
LEGITIMACY_MAX = 100.0
LEGITIMACY_HAPPY_RECOVERY = 0.4   # base per-turn recovery while content
LEGITIMACY_HAPPY_BONUS = 0.6      # extra recovery at contentment >= 20 (scales linearly)
LEGITIMACY_UNHAPPY_DRAIN = 0.2    # per point of negative contentment, per turn
LEGITIMACY_ATROCITY_DRAIN = 3.0   # per unit of fresh atrocity weight
LEGITIMACY_TIDE_DRAIN = 0.35      # per turn at full tide (recovery can win)
LEGITIMACY_SCANDAL_DRAIN = 8.0    # per unit of scandal severity
LEGITIMACY_VICTORY_FLOOR = 40.0   # no accumulation victory below this


def tick_legitimacy(current: float, happiness: int, tide=None,
                    fresh_atrocities: float = 0.0) -> float:
    """One turn of a House's mandate: contentment slowly rebuilds it;
    misery, fresh atrocities and the rising tide all drain it."""
    if happiness >= 0:
        current += (LEGITIMACY_HAPPY_RECOVERY
                    + LEGITIMACY_HAPPY_BONUS * min(happiness, 20) / 20.0)
    else:
        current -= LEGITIMACY_UNHAPPY_DRAIN * float(-happiness)
    current -= LEGITIMACY_ATROCITY_DRAIN * fresh_atrocities
    if tide is not None:
        current -= LEGITIMACY_TIDE_DRAIN * (tide.level / 100.0)
    return max(0.0, min(LEGITIMACY_MAX, current))


def record_scandal(legitimacy: dict, house: str, severity: float = 1.0,
                   events=None) -> float:
    """A scandal breaks over a House (exposes and trials feed this).
    Returns the legitimacy actually lost."""
    loss = LEGITIMACY_SCANDAL_DRAIN * severity
    cur = legitimacy.get(house, LEGITIMACY_START)
    legitimacy[house] = max(0.0, cur - loss)
    if events is not None:
        events.append(f"Scandal rocks {house}: legitimacy falls "
                      f"{loss:.0f} to {legitimacy[house]:.0f}")
    return loss


# --- Revolution (spec 5.3): the wall ----------------------------------------

REVOLUTION_LEGITIMACY_FLOOR = 15.0   # below this the mandate is effectively gone
REVOLUTION_MILITANCY_PEAK = 60.0     # a movement this militant smells blood
REVOLUTION_BREWING_TURNS = 3         # consecutive turns of both before it fires
REVOLUTION_OWNER = "The Commune"     # who defected provinces answer to


def revolution_brewing(legitimacy_value: float, provinces) -> bool:
    """True while a House's mandate is gone AND at least one of its
    movements is striking at peak militancy - the preconditions of
    uprising."""
    if legitimacy_value >= REVOLUTION_LEGITIMACY_FLOOR:
        return False
    for p in provinces:
        mv = getattr(p, "movement", None)
        if (mv is not None and mv.state == "striking"
                and mv.militancy >= REVOLUTION_MILITANCY_PEAK):
            return True
    return False


def trigger_revolution(house: str, provinces, enterprises) -> Tuple[List[str], List[int]]:
    """The uprising (spec 5.3): every organized province defects to the
    Commune. Its enterprises' ledgers are torn up and dials reset - the
    workers hold the works now. Returns (messages, flipped_pids)."""
    flipped: List[int] = []
    events = [f"REVOLUTION against House {house}! The {REVOLUTION_OWNER} rises"]
    for p in provinces:
        mv = getattr(p, "movement", None)
        if mv is None:
            continue
        p.owner = REVOLUTION_OWNER
        p.movement = None          # the movement IS the province now
        p.unrest = 0.0
        flipped.append(p.pid)
        events.append(f"{p.name} defects to the {REVOLUTION_OWNER}; "
                      f"worker militias man the barricades")
    for ent in enterprises:
        if ent.province in flipped:
            ent.ledger = {}            # nobody grinds the Commune's own
            ent.extraction_dial = DIAL_DEFAULT
    return events, flipped


# --- Transformation (spec 5.3): riding the wave -----------------------------

TRANSFORM_CONVICTION = -40.0    # true labor_capital at/below this is genuine
TRANSFORM_LEGITIMACY = 55.0     # a fresh mandate from the workers themselves
COLLECTIVE_ID = "COLLECTIVE"    # sentinel ledger holder: the workers themselves


def can_transform(ruler) -> bool:
    """Genuine Labor-ward conviction (spec 5.3): the TRUE spectrum value
    is checked - dispositions are the private self; a cultivated persona
    does not fool the movement."""
    if ruler is None or not getattr(ruler, "is_alive", False):
        return False
    return ruler.dispositions.get("labor_capital", 0.0) <= TRANSFORM_CONVICTION


def transform_house(house: str, ruler, provinces, enterprises, realm,
                    legitimacy: float) -> Tuple[List[str], float]:
    """Break with the Great Houses (spec 5.3): concede the enterprises to
    their workers, stand the movements down, smash the dials - and survive
    as People's Chairman of a transformed state. Returns
    (messages, new_legitimacy)."""
    events = [f"{ruler.name} breaks with the Great Houses - House {house} "
              f"transforms! The People's Chairman rises"]
    conceded = 0
    for ent in enterprises:
        if ent.house != house:
            continue
        ent.ledger = {COLLECTIVE_ID: 100.0}   # the workers hold the works now
        ent.extraction_dial = DIAL_DEFAULT
        conceded += 1
    for p in provinces:
        if getattr(p, "movement", None) is not None:
            p.movement = None        # the strikers are armed, not fought
        p.unrest = 0.0
    if conceded:
        events.append(f"{conceded} enterprises conceded to their workers; "
                      f"shares become political capital")
    return events, TRANSFORM_LEGITIMACY