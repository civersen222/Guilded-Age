"""Ideological tide (M58, character-society spec 5.2).

A single world-wide meter rising across the century: reformism ->
socialism -> revolutionary pressure. Every atrocity ANY House commits
anywhere accelerates it; the tide in turn scales movement growth and
conviction-drift pressure world-wide. Legitimacy (M59) and revolution
(M60) read from it.
"""

TIDE_BASE_RISE = 0.25          # per turn: ~25 points over a 100-turn century
ATROCITY_TIDE = 0.15           # tide points per unit of atrocity weight
ATROCITY_WEIGHTS = {
    "accident": 1.0,
    "cover_up": 2.0,
    "martyrdom": 4.0,
}


class IdeologicalTide:
    """The century's rising water (spec 5.2): 0 is quiet reformism,
    100 is revolutionary pressure everywhere."""

    def __init__(self):
        self.level = 0.0        # 0-100
        self.atrocities = 0.0   # lifetime weighted atrocity count
        self.house_atrocities = {}   # house -> lifetime weighted count (M59)
        self.fresh_atrocities = {}   # house -> weight since last legitimacy tick

    def tick(self):
        """One turn of history grinding forward."""
        self.level = min(100.0, self.level + TIDE_BASE_RISE)

    def record_atrocity(self, kind: str, house=None) -> float:
        """An atrocity anywhere feeds the tide everywhere; the House that
        committed it also carries the stain (M59 legitimacy)."""
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


# --- Legitimacy (M59, spec 5.3): a House's mandate to rule -----------------

LEGITIMACY_START = 70.0           # every House begins with a workable mandate
LEGITIMACY_MAX = 100.0
LEGITIMACY_HAPPY_RECOVERY = 0.4   # per turn while the realm is content
LEGITIMACY_UNHAPPY_DRAIN = 0.2    # per point of negative happiness, per turn
LEGITIMACY_ATROCITY_DRAIN = 3.0   # per unit of fresh atrocity weight
LEGITIMACY_TIDE_DRAIN = 0.6       # per turn at full tide (scales linearly)
LEGITIMACY_SCANDAL_DRAIN = 8.0    # per unit of scandal severity
LEGITIMACY_VICTORY_FLOOR = 40.0   # no accumulation victory below this


def tick_legitimacy(current: float, happiness: int, tide=None,
                    fresh_atrocities: float = 0.0) -> float:
    """One turn of a House's mandate: contentment slowly rebuilds it;
    misery, fresh atrocities and the rising tide all drain it."""
    if happiness >= 0:
        current += LEGITIMACY_HAPPY_RECOVERY
    else:
        current -= LEGITIMACY_UNHAPPY_DRAIN * float(-happiness)
    current -= LEGITIMACY_ATROCITY_DRAIN * fresh_atrocities
    if tide is not None:
        current -= LEGITIMACY_TIDE_DRAIN * (tide.level / 100.0)
    return max(0.0, min(LEGITIMACY_MAX, current))


def record_scandal(legitimacy: dict, house: str, severity: float = 1.0,
                   events=None) -> float:
    """A scandal breaks over a House (exposes and trials - M63/M66 feed
    this). Returns the legitimacy actually lost."""
    loss = LEGITIMACY_SCANDAL_DRAIN * severity
    cur = legitimacy.get(house, LEGITIMACY_START)
    legitimacy[house] = max(0.0, cur - loss)
    if events is not None:
        events.append(f"📰 Scandal rocks {house}: legitimacy falls "
                      f"{loss:.0f} to {legitimacy[house]:.0f}")
    return loss
