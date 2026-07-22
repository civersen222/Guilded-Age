"""The Age ladder (Gilded Saga §4.C): named eras promoted from the tide.

Each era opens when EITHER its tide threshold OR its turn threshold is met,
so the spine can never stall - the tide rises every turn and the clock always
advances."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Era:
    bid: str
    title: str
    tide: float
    turn: int
    foreshadow: str
    payoff: str


ERAS = [
    Era("age_gilded", "The Gilded Peace", 0.0, 1,
        "smoke on the horizon, the old order still holding",
        "The Gilded Peace settles over the continent."),
    Era("age_reform", "The Reforming Wind", 33.3, 18,
        "petitions harden into demands",
        "The Reforming Wind rises - petitions become demands."),
    Era("age_red", "The Red Decade", 66.6, 45,
        "the barricades are spoken of openly",
        "The Red Decade dawns; the barricades are spoken of openly."),
    Era("age_reckoning", "The Reckoning", 90.0, 63,
        "the old order counts its last days",
        "The Reckoning arrives - the old order counts its last days."),
]
