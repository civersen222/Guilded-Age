"""Tests for share-trade helper functions (MISSION I4d2b1)."""

from gilded.chassis import GildedGame
from gilded.ui.actions import (
    buy_share_counterparties,
    sell_share_counterparties,
    share_size_ladder,
)


# ── §5 fixture helper ────────────────────────────────────────────────────────

def _fixture():
    """Build the §5 fixture: seed 99, Ashworth player, one end_turn."""
    house = sorted(GildedGame(99).houses)[0]
    game = GildedGame(99, house)
    game.end_turn()
    return game, house


# ── R-1: buy_share_counterparties ────────────────────────────────────────────

def test_r1_buy_counterparties_returns_ledger_holders():
    """At the §5 fixture, eid 1 ledger has 5 entries.
    Excluding the ruler (000000b3), we expect 4 counterparties."""
    game, house = _fixture()
    eid = 1
    opts = buy_share_counterparties(game, house, eid)
    ids = {o["id"] for o in opts}
    # Four non-ruler ledger holders
    assert len(opts) == 4, f"expected 4 counterparties, got {len(opts)}"
    # Ruler excluded
    ruler = game.realms[house].ruler
    assert ruler.id not in ids, "ruler should be excluded from buy counterparties"


def test_r1_out_of_realm_holder_present():
    """Temujin Mordaine (0000007b) holds 15% in eid 1 but is NOT in the
    Ashworth realm.  A realm-scoped list would silently drop him."""
    game, house = _fixture()
    eid = 1
    opts = buy_share_counterparties(game, house, eid)
    ids = {o["id"] for o in opts}
    assert "0000007b" in ids, (
        "Temujin Mordaine (0000007b) must appear — he is an out-of-realm "
        "ledger holder (15% stake).  If missing, the list was built from "
        "realm.characters instead of the ledger."
    )
    temujin = next(o for o in opts if o["id"] == "0000007b")
    assert temujin["stake_pct"] == 15.0, f"expected 15.0% stake, got {temujin['stake_pct']}"
    assert "cost" in temujin, "each option must carry the gold cost"


def test_r1_option_fields():
    """Each option carries id, name, stake_pct, cost."""
    game, house = _fixture()
    for o in buy_share_counterparties(game, house, 1):
        for key in ("id", "name", "stake_pct", "cost"):
            assert key in o, f"missing key {key!r} in buy option"


# ── R-2: sell_share_counterparties ───────────────────────────────────────────

def test_r2_sell_counterparties_non_empty():
    """At the §5 fixture, 0 of 55 adults in Ashworth can afford 1% (1.48 gold).
    All 9 solvent buyers are in OTHER houses.  A realm-scoped list is empty."""
    game, house = _fixture()
    eid = 1
    opts = sell_share_counterparties(game, house, eid)
    realm_ids = {c.id for c in game.realms[house].characters}
    assert len(opts) > 0, (
        "sell list is empty — likely built from realm.characters instead of "
        "all realms.  At seed 99, all 9 solvent buyers are outside Ashworth."
    )


def test_r2_richest_first():
    """Richest candidate (000000ec, Ragnar Ferrenholt, 152.88 gold) appears
    before 0000014f (Borte Brandtner, 138.92)."""
    game, house = _fixture()
    eid = 1
    opts = sell_share_counterparties(game, house, eid)
    ids = [o["id"] for o in opts]
    assert "000000ec" in ids, "richest candidate (000000ec) missing"
    assert "0000014f" in ids, "second richest (0000014f) missing"
    idx_ec = ids.index("000000ec")
    idx_14f = ids.index("0000014f")
    assert idx_ec < idx_14f, (
        f"000000ec (idx {idx_ec}) must come before 0000014f (idx {idx_14f}) "
        "— list must be sorted richest first."
    )


def test_r2_option_fields():
    """Each option carries id, name, gold."""
    game, house = _fixture()
    for o in sell_share_counterparties(game, house, 1):
        for key in ("id", "name", "gold"):
            assert key in o, f"missing key {key!r} in sell option"


# ── R-3: share_size_ladder ───────────────────────────────────────────────────

def test_r3_ladder_basic():
    """Basic ladder returns canonical sizes up to seller's stake."""
    game, house = _fixture()
    eid = 1
    # Freydis Ashworth (000000b5) holds 20% in eid 1
    opts = share_size_ladder(game, house, eid, "000000b5")
    pcts = [o["pct"] for o in opts]
    assert 1 in pcts
    assert 5 in pcts
    assert 10 in pcts
    assert 25 not in pcts, "25% should be excluded — seller only holds 20%"


def test_r3_buy_purse_blocked():
    """When house treasury is lowered, large sizes are blocked by the treasury purse."""
    game, house = _fixture()
    eid = 1
    house_obj = game.houses[house]
    # Save original treasury
    orig_treasury = house_obj.treasury
    # Set treasury very low — can't afford 1% (1.48 gold)
    house_obj.treasury = 0.5
    opts = share_size_ladder(game, house, eid, "000000b5")
    # All sizes should be blocked by purse
    for o in opts:
        assert not o["offerable"], f"{o['pct']}% should not be offerable with treasury={house_obj.treasury}"
        assert "treasury" in o["reason"].lower() or "afford" in o["reason"].lower(), (
            f"reason should mention treasury/afford: {o['reason']!r}"
        )
    house_obj.treasury = orig_treasury


def test_r3_sell_purse_blocked():
    """When the buying character's gold_reserve is too low, sizes are blocked."""
    game, house = _fixture()
    eid = 1
    # Use a buyer with very low gold — set a character's gold to 0
    by_id = {c.id: c for r in game.realms.values() for c in r.characters}
    buyer_id = "000000ec"  # Ragnar, normally 152.88 gold
    buyer = by_id[buyer_id]
    orig_gold = buyer.gold_reserve
    buyer.gold_reserve = 0.5
    # Ruler sells to this buyer
    opts = share_size_ladder(game, house, eid, "000000b3", buyer_id=buyer_id)
    for o in opts:
        assert not o["offerable"], f"{o['pct']}% should not be offerable with buyer gold={buyer.gold_reserve}"
        assert "afford" in o["reason"].lower() or "cannot" in o["reason"].lower(), (
            f"reason should mention affordability: {o['reason']!r}"
        )
    buyer.gold_reserve = orig_gold


def test_r3_offerable_when_affordable():
    """With sufficient purse, sizes within the seller's stake are offerable."""
    game, house = _fixture()
    eid = 1
    # Borte Ashworth (000000c4) holds 10%. Treasury is 2139.88 — plenty.
    opts = share_size_ladder(game, house, eid, "000000c4")
    offerable = [o for o in opts if o["offerable"]]
    pcts = [o["pct"] for o in offerable]
    assert 1 in pcts, "1% should be offerable"
    assert 5 in pcts, "5% should be offerable"
    assert 10 in pcts, "10% should be offerable"
    assert 25 not in pcts, "25% exceeds seller's 10% stake"


def test_r3_option_fields():
    """Each option carries pct, cost, offerable, reason."""
    game, house = _fixture()
    for o in share_size_ladder(game, house, 1, "000000b5"):
        for key in ("pct", "cost", "offerable", "reason"):
            assert key in o, f"missing key {key!r} in ladder option"


# ── R-4: ACTIONS registry unchanged ──────────────────────────────────────────

def test_r4_actions_registry_unchanged():
    """ACTIONS dict still has exactly 16 keys, no buy_shares or sell_shares."""
    from gilded.ui.actions import ACTIONS
    assert len(ACTIONS) == 16, f"ACTIONS has {len(ACTIONS)} keys, expected 16"
    assert "buy_shares" not in ACTIONS, "buy_shares must not be registered yet"
    assert "sell_shares" not in ACTIONS, "sell_shares must not be registered yet"
