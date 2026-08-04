"""Stage 4 L3 — priced_transfer (gilded/society/shares.py).

Covers every numbered behaviour in the contract:
1. Price = market.value(ent, game) * pct / 100.0
2. dry_run=True returns a quote without side effects
3. Non-positive price is a no-op returning 0.0
4. Broke buyer gets nothing
5. Settlement order: shares first, then charge for what actually moved
6. Gold flows buyer → seller
7. Opinion +5 when shares moved; no opinion when nothing moved
8. No consumption of game.rng
9. Returns gold actually paid
"""

import random

from gilded.chassis import GildedGame
from gilded.market import PRODUCES
from gilded.society.shares import priced_transfer, stake_cost

SEED = 7


# --- helpers ----------------------------------------------------------------

def _game():
    return GildedGame(SEED)


def _setup():
    """Return (game, ent, seller, buyer) with a completed enterprise that has
    a positive market value, its majority shareholder, and a buyer who holds
    no stake."""
    g = _game()
    ent = next(e for e in g.enterprises
               if e.under_construction == 0 and PRODUCES.get(e.kind))
    holders = sorted(ent.ledger.items(), key=lambda kv: -kv[1])
    seller_id = holders[0][0]
    by_id = {c.id: c for r in g.realms.values() for c in r.characters}
    seller = by_id[seller_id]
    buyer = next(c for c in by_id.values()
                 if c.id != seller_id and c.id not in ent.ledger and c.is_alive)
    return g, ent, seller, buyer


# --- tests ------------------------------------------------------------------

def test_quote_is_correct():
    """Behaviour #1 — price = market.value * pct / 100."""
    g, ent, seller, buyer = _setup()
    quote = priced_transfer(ent, seller, buyer, 5.0, g.market, g, dry_run=True)
    expected = g.market.value(ent, g) * 5.0 / 100.0
    assert abs(quote - expected) < 1e-6, f"quote {quote} != expected {expected}"


def test_dry_run_does_nothing():
    """Behaviour #2 — dry_run returns a quote without touching state."""
    g, ent, seller, buyer = _setup()
    buyer.gold_reserve = 10_000.0
    ledger_before = dict(ent.ledger)
    seller_gold_before = seller.gold_reserve
    buyer_gold_before = buyer.gold_reserve
    quote = priced_transfer(ent, seller, buyer, 5.0, g.market, g, dry_run=True)
    assert quote > 0.0, "dry_run should return a positive quote"
    assert dict(ent.ledger) == ledger_before, "ledger must not change on dry_run"
    assert seller.gold_reserve == seller_gold_before, "seller gold must not change"
    assert buyer.gold_reserve == buyer_gold_before, "buyer gold must not change"


def test_zero_price_is_no_op():
    """Behaviour #3 — non-positive price returns 0.0 and moves nothing."""
    g, ent, seller, buyer = _setup()
    ent.under_construction = 2
    assert g.market.value(ent, g) == 0.0
    buyer.gold_reserve = 0.0
    ledger_before = dict(ent.ledger)
    paid = priced_transfer(ent, seller, buyer, 5.0, g.market, g)
    assert paid == 0.0, f"zero-valued trade must return 0.0, got {paid}"
    assert dict(ent.ledger) == ledger_before, "shares must not move for free"


def test_broke_buyer_gets_nothing():
    """Behaviour #4 — buyer who can't afford the tranche gets nothing."""
    g, ent, seller, buyer = _setup()
    buyer.gold_reserve = 0.0
    quote = priced_transfer(ent, seller, buyer, 5.0, g.market, g, dry_run=True)
    assert quote > 0.0, "precondition: enterprise has positive value"
    ledger_before = dict(ent.ledger)
    paid = priced_transfer(ent, seller, buyer, 5.0, g.market, g)
    assert paid == 0.0, f"broke buyer must pay 0.0, got {paid}"
    assert dict(ent.ledger) == ledger_before, "shares must not move"


def test_shares_move_and_gold_flows():
    """Behaviours #5 & #6 — shares move first, gold flows buyer → seller."""
    g, ent, seller, buyer = _setup()
    quote = priced_transfer(ent, seller, buyer, 5.0, g.market, g, dry_run=True)
    buyer.gold_reserve = quote * 4
    before_seller_pct = ent.ledger.get(seller.id, 0.0)
    before_buyer_gold = buyer.gold_reserve
    before_seller_gold = seller.gold_reserve
    paid = priced_transfer(ent, seller, buyer, 5.0, g.market, g)
    assert paid > 0.0, f"funded buyer must pay something, got {paid}"
    assert abs(ent.ledger.get(buyer.id, 0.0) - 5.0) < 1e-6
    assert abs(ent.ledger.get(seller.id, 0.0) - (before_seller_pct - 5.0)) < 1e-6
    assert abs(buyer.gold_reserve - (before_buyer_gold - paid)) < 1e-6
    assert abs(seller.gold_reserve - (before_seller_gold + paid)) < 1e-6


def test_opinion_rises_on_success():
    """Behaviour #7a — seller thinks better of the buyer after a successful trade."""
    g, ent, seller, buyer = _setup()
    pair = (seller.id, buyer.id)
    before = g.society.opinions.get(pair, 0)
    buyer.gold_reserve = 10_000.0
    priced_transfer(ent, seller, buyer, 5.0, g.market, g)
    after = g.society.opinions.get(pair, 0)
    assert after > before, f"opinion must rise: {before} -> {after}"


def test_opinion_not_on_failure():
    """Behaviour #7b — no goodwill when nothing moved."""
    g, ent, seller, buyer = _setup()
    pair = (seller.id, buyer.id)
    before = g.society.opinions.get(pair, 0)
    buyer.gold_reserve = 0.0
    priced_transfer(ent, seller, buyer, 5.0, g.market, g)
    assert g.society.opinions.get(pair, 0) == before, \
        "refused trade must not buy goodwill"


def test_no_rng_consumption():
    """Behaviour #8 — priced_transfer must not consume game.rng."""
    g, ent, seller, buyer = _setup()
    buyer.gold_reserve = 10_000.0
    rng_state = random.getstate()
    priced_transfer(ent, seller, buyer, 5.0, g.market, g)
    assert random.getstate() == rng_state, "random state must not change"


def test_returns_gold_actually_paid():
    """Behaviour #9 — return value is the gold actually transferred."""
    g, ent, seller, buyer = _setup()
    quote = priced_transfer(ent, seller, buyer, 5.0, g.market, g, dry_run=True)
    buyer.gold_reserve = quote * 4
    paid = priced_transfer(ent, seller, buyer, 5.0, g.market, g)
    assert paid > 0.0, "return value must be the gold paid"


def test_seller_receives_gold():
    """Behaviour #6 — gold goes to the seller, not a sink."""
    g, ent, seller, buyer = _setup()
    quote = priced_transfer(ent, seller, buyer, 5.0, g.market, g, dry_run=True)
    buyer.gold_reserve = quote * 4
    seller_gold_before = seller.gold_reserve
    paid = priced_transfer(ent, seller, buyer, 5.0, g.market, g)
    assert abs(seller.gold_reserve - (seller_gold_before + paid)) < 1e-6


def test_all_or_nothing_no_clamp():
    """Behaviour #4 — does not clamp tranche to what buyer can afford."""
    g, ent, seller, buyer = _setup()
    quote = priced_transfer(ent, seller, buyer, 50.0, g.market, g, dry_run=True)
    buyer.gold_reserve = quote * 0.5  # can only afford half
    paid = priced_transfer(ent, seller, buyer, 50.0, g.market, g)
    assert paid == 0.0, "partial affordability must still return 0.0"


# --- stake_cost tests -------------------------------------------------------

def test_stake_cost_returns_float():
    """stake_cost returns a numeric float."""
    g, ent, _, _ = _setup()
    cost = stake_cost(ent, 10.0, g)
    assert isinstance(cost, float)


def test_stake_cost_matches_share_price_formula():
    """stake_cost equals share_price(ent, game) * pct"""
    from gilded.society.schemes import share_price
    g, ent, _, _ = _setup()
    expected = share_price(ent, g) * 10.0
    assert abs(stake_cost(ent, 10.0, g) - expected) < 1e-6


def test_stake_cost_zero_pct_returns_zero():
    """Zero percent stake costs zero."""
    g, ent, _, _ = _setup()
    assert stake_cost(ent, 0.0, g) == 0.0


def test_stake_cost_full_hundred_equals_share_price_times_100():
    """100% stake costs share_price * 100."""
    from gilded.society.schemes import share_price
    g, ent, _, _ = _setup()
    expected = share_price(ent, g) * 100.0
    assert abs(stake_cost(ent, 100.0, g) - expected) < 1e-6


def test_stake_cost_linear_scaling():
    """Price scales linearly: cost(20) == 2 * cost(10)."""
    g, ent, _, _ = _setup()
    c10 = stake_cost(ent, 10.0, g)
    c20 = stake_cost(ent, 20.0, g)
    assert abs(c20 - 2 * c10) < 1e-6


def test_stake_cost_negative_pct_returns_negative():
    """Negative percentage produces a negative cost (symmetric formula)."""
    g, ent, _, _ = _setup()
    pos = stake_cost(ent, 10.0, g)
    neg = stake_cost(ent, -10.0, g)
    assert abs(neg - (-pos)) < 1e-6


def test_stake_cost_positive_for_valid_enterprise():
    """A completed enterprise with positive market value yields positive cost."""
    g, ent, _, _ = _setup()
    assert stake_cost(ent, 10.0, g) > 0


def test_stake_cost_no_rng_consumption():
    """stake_cost must not consume game.rng."""
    g, ent, _, _ = _setup()
    rng_state = random.getstate()
    stake_cost(ent, 10.0, g)
    assert random.getstate() == rng_state, "stake_cost must not touch RNG"
