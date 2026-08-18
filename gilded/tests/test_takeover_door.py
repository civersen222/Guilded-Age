"""Stage 11K: the takeover's door.

Seed 7, twelve turns, driven by end_turn() ONLY. The signature verb
(quiet share purchase via a House's disloyal holders) must actually
fire: the door must open for at least one House a live campaign is
targeting, advance() must find sellers on at least five separate
calls, and the "share purchase" label must debit real gold.
"""

import gilded.society.realm as realm_mod
from gilded.chassis import GildedGame


def _run(seed=7, turns=12):
    """Play *turns* of seed *seed* with end_turn() only.

    Returns (game, track) where track records, per Takeover.advance
    call, whether the targeted House had at least one disloyal
    shareholder and which targeted Houses the door opened for.
    """
    game = GildedGame(seed=seed)
    track = {"calls": 0, "found": 0, "houses": set()}
    orig = realm_mod.disloyal_shareholders

    def counting(realm, *rest, **kwargs):
        sellers = orig(realm, *rest, **kwargs)
        targets = {tk.target_house for tk in game.takeovers if not tk.complete}
        if realm is not None and getattr(realm, "house_name", None) in targets:
            track["calls"] += 1
            if sellers:
                track["found"] += 1
                track["houses"].add(realm.house_name)
        return sellers

    realm_mod.disloyal_shareholders = counting
    try:
        for _ in range(turns):
            game.end_turn()
    finally:
        realm_mod.disloyal_shareholders = orig
    return game, track


def _label_debits(game, label):
    return -sum(amt for h in game.houses.values()
                for (_t, l, amt) in h.journal if l == label)


def test_seed7_share_purchase_debits_at_least_100():
    game, _track = _run()
    spent = _label_debits(game, "share purchase")
    assert spent >= 100, f"share purchase debited {spent:.1f}, need >= 100"


def test_advance_finds_sellers_on_at_least_five_calls():
    _game, track = _run()
    assert track["found"] >= 5, (
        f"advance found sellers on {track['found']} of {track['calls']} "
        f"calls, need >= 5")


def test_door_opens_for_a_live_target_house():
    _game, track = _run()
    assert len(track["houses"]) >= 1, (
        "disloyal_shareholders was empty for every House a live "
        "takeover was targeting")
