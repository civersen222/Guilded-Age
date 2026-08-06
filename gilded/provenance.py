from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Cause:
    """One named contribution to a change."""
    label: str
    amount: float
    source: str


@dataclass(frozen=True)
class Attributed:
    """A value, the value it came from, and the causes that explain the difference."""
    value: float
    previous: float
    causes: Tuple['Cause', ...]

    @property
    def delta(self) -> float:
        return self.value - self.previous

    def check(self, tol: float = 1e-6) -> bool:
        """Return True when the causes sum to the delta within tolerance."""
        return abs(sum(c.amount for c in self.causes) - self.delta) <= tol
