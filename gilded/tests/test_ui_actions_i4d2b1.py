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
    """Ladder returns ALL canonical sizes plus the seller's stake.
    Sizes larger than the stake are present but not offerable (R-1).
    The stake itself is always a rung (R-2)."""
    game, house = _fixture()
    eid = 1
    # Freydis Ashworth (000000b5) holds 20% in eid 1
    opts = share_size_ladder(game, house, eid, "000000b5")
    pcts = [o["pct"] for o in opts]
    # Canonical sizes present
    assert 1 in pcts
    assert 5 in pcts
    assert 10 in pcts
    # R-1: 25% is PRESENT (not dropped) but not offerable — seller only holds 20%
    assert 25 in pcts, "25% should be present even though seller only holds 20%"
    row_25 = next(o for o in opts if o["pct"] == 25)
    assert not row_25["offerable"], "25% should not be offerable for 20% holder"
    assert "Seller only holds" in row_25["reason"], "reason should name stake cap"
    # R-2: 20 (the whole stake) is a rung, exactly once
    assert pcts.count(20) == 1, "20% stake should appear exactly once"


def test_r3_buy_purse_blocked():
    """When house treasury is lowered, sizes within stake are blocked by purse.
    Sizes above stake are blocked by the stake check (R-1)."""
    game, house = _fixture()
    eid = 1
    house_obj = game.houses[house]
    # Save original treasury
    orig_treasury = house_obj.treasury
    # Set treasury very low — can't afford 1% (1.48 gold)
    house_obj.treasury = 0.5
    opts = share_size_ladder(game, house, eid, "000000b5")
    available = 20.0  # 000000b5 holds 20%
    # All sizes should be non-offerable
    for o in opts:
        assert not o["offerable"], f"{o['pct']}% should not be offerable with treasury={house_obj.treasury}"
        if o["pct"] <= available:
            # Within stake: blocked by purse
            assert "treasury" in o["reason"].lower() or "afford" in o["reason"].lower(), (
                f"reason should mention treasury/afford: {o['reason']!r}"
            )
        else:
            # Above stake: blocked by stake check
            assert "Seller only holds" in o["reason"], (
                f"reason should mention stake cap: {o['reason']!r}"
            )
    house_obj.treasury = orig_treasury


def test_r3_sell_purse_blocked():
    """When the buying character's gold_reserve is too low, sizes within stake
    are blocked by purse. Sizes above stake are blocked by the stake check (R-1)."""
    game, house = _fixture()
    eid = 1
    by_id = {c.id: c for r in game.realms.values() for c in r.characters}
    buyer_id = "000000ec"  # Ragnar, normally 152.88 gold
    buyer = by_id[buyer_id]
    orig_gold = buyer.gold_reserve
    buyer.gold_reserve = 0.5
    # Ruler sells to this buyer — ruler holds 35%
    opts = share_size_ladder(game, house, eid, "000000b3", buyer_id=buyer_id)
    available = 35.0  # 000000b3 (ruler) holds 35%
    for o in opts:
        assert not o["offerable"], f"{o['pct']}% should not be offerable with gold={buyer.gold_reserve}"
        if o["pct"] <= available:
            # Within stake: blocked by purse
            assert "afford" in o["reason"].lower() or "cannot" in o["reason"].lower(), (
                f"reason should mention affordability: {o['reason']!r}"
            )
        else:
            # Above stake: blocked by stake check
            assert "Seller only holds" in o["reason"], (
                f"reason should mention stake cap: {o['reason']!r}"
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


# ── R-1 / R-2: ladder completeness & whole-stake rung ─────────────────────────

def test_e37_ladder_has_non_offerable_row():
    """E37: for a 10.00% holder at full treasury, the ladder returns at least
    one row with offerable=False — treasury covers everything, so only the
    stake cap can refuse a row."""
    game, house = _fixture()
    opts = share_size_ladder(game, house, 1, "000000c4")
    non_offerable = [o for o in opts if not o["offerable"]]
    assert len(non_offerable) >= 1, "expected at least one non-offerable row (stake-blocked)"
    for o in non_offerable:
        assert "Seller only holds" in o["reason"], f"reason should name stake cap: {o['reason']!r}"


def test_e38_rung_25_present_for_10pct_holder():
    """E38: for a 10% holder, a rung of 25 is PRESENT and not offerable (R-1)."""
    game, house = _fixture()
    opts = share_size_ladder(game, house, 1, "000000c4")
    pcts = [o["pct"] for o in opts]
    assert 25 in pcts, "25% should be present even though seller only holds 10%"
    row = next(o for o in opts if o["pct"] == 25)
    assert not row["offerable"], "25% should not be offerable for 10% holder"


def test_e39_whole_stake_rung_for_temujin():
    """E39: for Temujin Mordaine (0000007b) holding 15.00%, a rung equal to his
    whole 15% is present and IS offerable (R-2)."""
    game, house = _fixture()
    opts = share_size_ladder(game, house, 1, "0000007b")
    pcts = [o["pct"] for o in opts]
    assert 15.0 in pcts, "15% (whole stake) should be a rung for 15% holder"
    row = next(o for o in opts if o["pct"] == 15.0)
    assert row["offerable"], "15% whole-stake rung should be offerable at full treasury"


def test_e40_no_duplicate_rung():
    """E40: for a holder on exactly 10.00%, the value 10 appears exactly once (T-1)."""
    game, house = _fixture()
    opts = share_size_ladder(game, house, 1, "000000c4")
    pcts = [o["pct"] for o in opts]
    assert pcts.count(10) == 1, "10% should appear exactly once (canonical + stake deduplicated)"


# ── R-4: ACTIONS registry unchanged ──────────────────────────────────────────

def test_r4_actions_registry_updated():
    """ACTIONS dict now has 18 keys, including buy_shares and sell_shares."""
    from gilded.ui.actions import ACTIONS, PlayerAction
    assert len(ACTIONS) == 19, f"ACTIONS has {len(ACTIONS)} keys, expected 19"
    assert "buy_shares" in ACTIONS, "buy_shares must be registered"
    assert "sell_shares" in ACTIONS, "sell_shares must be registered"
    assert isinstance(ACTIONS["buy_shares"], PlayerAction)
    assert isinstance(ACTIONS["sell_shares"], PlayerAction)
    assert ACTIONS["buy_shares"].key == "buy_shares"
    assert ACTIONS["sell_shares"].key == "sell_shares"
