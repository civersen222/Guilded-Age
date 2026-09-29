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


def test_buyers_own_stake_below_threshold_but_coalition_completes():
    """11R: the buyer alone may never clear the threshold - the House falls
    to the buyer and the House's own defectors together. A buyer capped by
    a thin treasury far below the threshold still completes the campaign
    while the disloyal holders stand behind them; under the old
    buyer-alone check this campaign could never finish."""
    random.seed(47)
    rng = random.Random(47)
    society = SocietyState(rng)
    buyer = _char(society, "Buyer")
    ra = create_house_realm("Vantrell", society)
    target = create_house_realm("Karsgate", society)
    seller = _char(society, "Seller")
    target.characters.append(seller)
    seller.loyalty = 0.0  # disloyal: the door stays open
    ent = Enterprise(eid=11, kind="bank", name="K Mill",
                     house=target.house_name, province=0)
    ent.ledger = {seller.id: 100.0}
    ent.director_id = seller.id

    class _Thin(_House):
        def __init__(self):
            # Enough for exactly two tranches: the buyer tops out at
            # 10% of the portfolio - nowhere near the threshold alone.
            self.treasury = 20.0

    game = _Game(_Thin())
    realms = {ra.house_name: ra, target.house_name: target}
    tk = Takeover(buyer, "Vantrell", target.house_name)

    for _ in range(60):
        tk.advance(realms, [ent], rng, game)
        if tk.complete:
            break
    assert tk.complete, (
        f"the buyer alone holds far below {TAKEOVER_THRESHOLD} - the "
        f"House must fall to the buyer and its defectors together")
    assert ent.house == "Vantrell"


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


def test_dead_buyer_lapses_the_campaign():
    """11R: a campaign dies with its buyer. A dead buyer cannot keep buying
    shares turn after turn - the campaign lapses and stays closed."""
    random.seed(47)
    rng = random.Random(47)
    society = SocietyState(rng)
    buyer = _char(society, "Buyer")
    ra = create_house_realm("Vantrell", society)
    target = create_house_realm("Karsgate", society)
    seller = _char(society, "Seller")
    target.characters.append(seller)
    seller.loyalty = 0.0  # disloyal: the door would stay open without this
    ent = Enterprise(eid=10, kind="bank", name="K Mill",
                     house=target.house_name, province=0)
    ent.ledger = {seller.id: 100.0}
    ent.director_id = seller.id

    game = _Game(_House())
    realms = {ra.house_name: ra, target.house_name: target}
    tk = Takeover(buyer, "Vantrell", target.house_name)

    buyer.is_alive = False
    assert tk.advance(realms, [ent], rng, game) == []
    assert tk.lapsed, "a dead buyer's campaign must lapse"
    assert not tk.complete
    # A later call cannot resurrect it - and nothing moved.
    assert tk.advance(realms, [ent], rng, game) == []
    assert tk.lapsed
    assert ent.house == "Karsgate"
    assert ent.ledger.get(seller.id, 0.0) == 100.0
