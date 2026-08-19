"""STAGE 11Q: the invariant that pins the conclusion of the takeover.

Two ends of the campaign must close it:

1. A campaign against an enterprise-less House has nothing left to buy -
   it does not stay live forever; it lapses and stays closed.
2. A completed takeover (average stake past the threshold) actually moves
   the target House's enterprises under the buyer's House.
"""

import random

from gilded.enterprises import Enterprise
from gilded.society.characters import Character, SocietyState
from gilded.society.realm import create_house_realm
from gilded.society.schemes import TAKEOVER_THRESHOLD, Takeover


class _Game:
    """Minimal game stand-in: a buyer House with a treasury and a market."""

    def __init__(self, house):
        self.turn = 1
        self.houses = {"Vantrell": house}

    class _Mkt:
        @staticmethod
        def value(ent, game):
            return 4.2

    market = _Mkt()


class _House:
    def __init__(self):
        self.treasury = 100000.0

    def debit(self, turn, label, amount):
        self.treasury -= amount


def _char(society, name):
    c = Character(name=name, stats={}, traits=[], age=40,
                  gender="Female", society=society)
    c.loyalty = 0.0
    return c


def test_enterpriseless_campaign_does_not_stay_live():
    random.seed(47)
    rng = random.Random(47)
    society = SocietyState(rng)
    buyer = _char(society, "Buyer")
    ra = create_house_realm("Vantrell", society)
    target = create_house_realm("Karsgate", society)
    # The target House holds no enterprises at all - nothing to buy.
    game = _Game(_House())
    tk = Takeover(buyer, "Vantrell", "Karsgate")
    realms = {ra.house_name: ra, target.house_name: target}
    assert tk.advance(realms, [], rng, game) == []
    assert tk.lapsed, "campaign against an enterprise-less House must lapse"
    assert not tk.complete
    # A later call cannot resurrect it.
    assert tk.advance(realms, [], rng, game) == []
    assert tk.lapsed


def test_completed_takeover_moves_the_enterprises():
    random.seed(47)
    rng = random.Random(47)
    society = SocietyState(rng)
    buyer = _char(society, "Buyer")
    ra = create_house_realm("Vantrell", society)
    target = create_house_realm("Karsgate", society)
    seller = _char(society, "Seller")
    target.characters.append(seller)
    seller.loyalty = 0.0  # disloyal: the door stays open

    ent = Enterprise(eid=9, kind="bank", name="K Mill",
                     house=target.house_name, province=0)
    ent.ledger = {seller.id: 100.0}
    ent.director_id = seller.id

    game = _Game(_House())
    realms = {ra.house_name: ra, target.house_name: target}
    tk = Takeover(buyer, "Vantrell", target.house_name)

    for _ in range(60):
        tk.advance(realms, [ent], rng, game)
        if tk.complete:
            break
    assert tk.complete, (
        f"takeover must complete against a fully disloyal holder "
        f"(threshold {TAKEOVER_THRESHOLD})")
    # The enterprise moved under the buyer's House.
    assert ent.house == "Vantrell", f"enterprise still under {ent.house}"
    # The seller was stripped of the portfolio.
    assert ent.ledger.get(seller.id, 0.0) == 0.0
