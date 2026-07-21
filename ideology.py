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

    def tick(self):
        """One turn of history grinding forward."""
        self.level = min(100.0, self.level + TIDE_BASE_RISE)

    def record_atrocity(self, kind: str) -> float:
        """An atrocity anywhere feeds the tide everywhere."""
        w = ATROCITY_WEIGHTS.get(kind, 1.0)
        self.atrocities += w
        self.level = min(100.0, self.level + w * ATROCITY_TIDE)
        return w

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
