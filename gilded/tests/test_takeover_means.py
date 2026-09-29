"""STAGE 11P: the invariant that pins the means of the takeover door.

The takeover route runs through disloyal_shareholders — the only door the
Buyout can walk through. This test pins that door shut when it must be
shut: a House whose share-holding characters are ALL loyal has no sellers.
"""

import random

from gilded.enterprises import Enterprise
from gilded.society.characters import SocietyState
from gilded.society.realm import (
    create_house_realm,
    disloyal_shareholders,
)


def _realm():
    random.seed(47)
    rng = random.Random(47)
    society = SocietyState(rng)
    ra = create_house_realm("Vantrell", society)
    return ra


def test_loyal_shareholders_never_sell():
    ra = _realm()
    # A character who is NOT the ruler, alive, and holds House shares.
    sellers = [ch for ch in ra.characters
               if ch.is_alive and ch.id != ra.ruler.id][:1]
    assert sellers, "need at least one non-ruler character in the House"
    holder = sellers[0]

    ent = Enterprise(eid=1, kind="bank", name="V Bank",
                     house=ra.house_name, province=0)
    ent.ledger = {holder.id: 30.0}

    # Fully loyal, no grudge against the ruler.
    holder.loyalty = 95.0
    holder._society.opinions[(holder.id, ra.ruler.id)] = 50.0

    assert disloyal_shareholders(ra, [ent]) == []


def test_loyal_shareholders_never_sell_house_only_default():
    """Even with other houses' enterprises in the mix, a House whose own
    share-holders are all loyal has no sellers on the default (house_only)
    path the takeover route uses."""
    ra = _realm()
    holders = [ch for ch in ra.characters
               if ch.is_alive and ch.id != ra.ruler.id]
    for ch in holders:
        ch.loyalty = 90.0
        ch._society.opinions[(ch.id, ra.ruler.id)] = 40.0

    own = Enterprise(eid=1, kind="mill", name="V Mill",
                     house=ra.house_name, province=0)
    own.ledger = {holders[0].id: 25.0}
    rival = Enterprise(eid=2, kind="bank", name="K Bank",
                       house="Karsgate", province=0)
    rival.ledger = {holders[1].id: 25.0}
    holders[1].loyalty = 10.0   # disloyal, but to another house

    assert disloyal_shareholders(ra, [own, rival]) == []
