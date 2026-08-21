"""Shared fixtures for UI tests — not a test module itself."""

import pygame
from gilded.chassis import GildedGame
from gilded.society.realm import (
    DISLOYAL_LOYALTY,
    DISLOYAL_OPINION,
    disloyal_shareholders,
)
from gilded.ui.broadsheet import BroadsheetView


def _enterprises_view(seed=42, turns=0):
    """Game with agendas, advanced `turns` turns, view on Enterprises tab."""
    from gilded import agenda
    pygame.init()
    g = GildedGame(seed=seed)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            agenda.ensure_agenda(g, h)
    for _ in range(turns):
        g.end_turn()
    v = BroadsheetView(g, player)
    v.active_tab = "Enterprises"
    return g, v


def make_one_seller(game, house_name):
    """Force House `house_name` to have EXACTLY ONE disloyal shareholder.

    Whether a generated world contains a shareholder willing to sell is a
    fact about the dice. Every takeover test in the scheme and broadsheet
    suites went looking for one and failed whenever the search came up
    empty. This builds it, so the tests measure the takeover rule instead
    of the weather.

    Returns the seller Character.
    """
    realm = game.realms[house_name]
    ents = [e for e in game.enterprises if e.house == house_name]
    assert ents, f"{house_name} holds no enterprise to be a shareholder of"
    ent = ents[0]

    # Stand down anyone who is ALREADY disloyal, so the count is exactly one
    # and the arithmetic downstream stays single-sourced — that is what the
    # fixture's `len(sellers) == 1` premise was really protecting.
    for ch in disloyal_shareholders(realm, game.enterprises):
        ch.loyalty = 100.0
        ch._society.opinions[(ch.id, realm.ruler.id)] = 0

    seller = next(ch for ch in realm.characters
                  if ch.is_alive and ch.id != realm.ruler.id)
    ent.ledger[seller.id] = max(ent.ledger.get(seller.id, 0.0), 10.0)
    seller.loyalty = DISLOYAL_LOYALTY - 1.0
    seller._society.opinions[(seller.id, realm.ruler.id)] = DISLOYAL_OPINION - 1

    got = disloyal_shareholders(realm, game.enterprises)
    assert [c.id for c in got] == [seller.id], (
        f"built {seller.id} but disloyal_shareholders says "
        f"{[c.id for c in got]}")
    return seller


def no_sellers(game, house_name):
    """Stand every shareholder of House `house_name` down so none is disloyal.

    The mirror of make_one_seller: it clears the reach a test needs to be
    zero (a House nobody will sell into), so a premise like 'the label
    quotes the TARGET not the player's own' can be established rather than
    hoped for.
    """
    realm = game.realms[house_name]
    for ch in disloyal_shareholders(realm, game.enterprises):
        ch.loyalty = 100.0
        ch._society.opinions[(ch.id, realm.ruler.id)] = 0
    assert not disloyal_shareholders(realm, game.enterprises), (
        f"{house_name} still has a disloyal shareholder after standing down")
