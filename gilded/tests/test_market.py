"""Stage 4 L1 — the market production chain (gilded/market.py).

The contract for the emergent-price economy: four commodities (coal, steel,
freight, farm), prices cleared each turn from real supply and demand over the
chain, threaded into the chassis dividend loop as an output multiplier and an
input cost, plus the activated tech_mod hook. Determinism: no game.rng in the
clearing. These tests are self-contained (build their own GildedGame)."""

import random

import gilded.market as market
from gilded.chassis import GildedGame
from gilded.enterprises import (Enterprise, ENTERPRISE_TYPES, found_enterprise,
                                tick_construction)


SEED = 7


# --- helpers ---------------------------------------------------------------

def _game():
    return GildedGame(SEED)


def _find_province(game, endowment):
    for pid in sorted(game.atlas.provinces):
        p = game.atlas.provinces[pid]
        if endowment in p.endowments:
            return p
    raise AssertionError(f"no province with endowment {endowment}")


def _build(game, kind, endowment, eid):
    """Found an enterprise on a matching province, complete it, register it."""
    prov = _find_province(game, endowment)
    house = sorted(game.houses)[0]
    ent = found_enterprise(kind, house, prov, eid, random.Random(eid))
    assert ent is not None
    while not tick_construction(ent):
        pass
    game.enterprises.append(ent)
    return ent


def _ent(kind):
    return Enterprise(eid=1, kind=kind, name="X", house="V", province=0)


# --- commodity constants + the price cell ----------------------------------

def test_commodities_are_the_four_chain_commodities():
    assert set(market.COMMODITIES) == {"coal", "steel", "freight", "farm"}


def test_fresh_market_prices_are_neutral():
    m = market.Market()
    for c in market.COMMODITIES:
        assert m.price(c) == 1.0


def test_clear_price_rises_when_demand_exceeds_supply():
    assert market.clear_price(prev=1.0, supply=10.0, demand=20.0) > 1.0


def test_clear_price_falls_when_supply_exceeds_demand():
    assert market.clear_price(prev=1.0, supply=20.0, demand=10.0) < 1.0


def test_clear_price_is_bounded_both_ends():
    hi = market.clear_price(prev=market.PRICE_MAX, supply=1.0, demand=1e9)
    lo = market.clear_price(prev=market.PRICE_MIN, supply=1e9, demand=0.0)
    assert lo >= market.PRICE_MIN
    assert hi <= market.PRICE_MAX
    assert market.PRICE_MIN < market.PRICE_MAX


def test_clear_price_zero_supply_pushes_up_and_caps_at_max():
    assert market.clear_price(prev=1.0, supply=0.0, demand=100.0) > 1.0
    assert market.clear_price(prev=market.PRICE_MAX, supply=0.0, demand=100.0) == market.PRICE_MAX


def test_clear_price_damps_partway_not_instant():
    # target demand/supply = 2.0; a single turn moves partway there, not all the way.
    p = market.clear_price(prev=1.0, supply=10.0, demand=20.0)
    assert 1.0 < p < 2.0


def test_clear_price_is_deterministic():
    a = market.clear_price(prev=1.0, supply=13.0, demand=27.0)
    b = market.clear_price(prev=1.0, supply=13.0, demand=27.0)
    assert a == b


# --- supply ----------------------------------------------------------------

def test_supply_has_all_commodities_and_is_nonnegative():
    g = _game()
    supply = market.supply_by_commodity(g)
    assert set(supply) == set(market.COMMODITIES)
    assert all(v >= 0.0 for v in supply.values())


def test_colliery_adds_coal_supply():
    g = _game()
    before = market.supply_by_commodity(g)["coal"]
    _build(g, "colliery", "coalfield", 9001)
    after = market.supply_by_commodity(g)["coal"]
    assert after > before


def test_estate_adds_farm_supply_despite_none_capacity_kind():
    # estates return capacity_out kind None, so farm supply must be sourced from
    # estate farmland richness explicitly.
    g = _game()
    before = market.supply_by_commodity(g)["farm"]
    _build(g, "estate", "farmland", 9002)
    after = market.supply_by_commodity(g)["farm"]
    assert after > before


# --- demand ----------------------------------------------------------------

def test_demand_has_all_commodities():
    g = _game()
    demand = market.demand_by_commodity(g)
    assert set(demand) == set(market.COMMODITIES)


def test_ironworks_adds_coal_demand():
    # ironworks burn coal to make steel.
    g = _game()
    before = market.demand_by_commodity(g)["coal"]
    _build(g, "ironworks", "iron", 9003)
    after = market.demand_by_commodity(g)["coal"]
    assert after > before


def test_construction_adds_steel_demand():
    g = _game()
    base = market.demand_by_commodity(g)["steel"]
    ent = g.enterprises[0]
    ent.under_construction = 2
    ent.target_tier = ent.tier + 1
    raised = market.demand_by_commodity(g)["steel"]
    assert raised > base


def test_population_creates_farm_demand():
    g = _game()
    assert market.demand_by_commodity(g)["farm"] > 0.0


# --- Market.clear over supply/demand ---------------------------------------

def test_clear_raises_a_sector_price_when_demand_is_added():
    g = _game()
    m = market.Market()
    m.clear(g)
    base = m.price("coal")
    for i in range(4):
        _build(g, "ironworks", "iron", 9100 + i)   # more coal demand, no coal supply
    m.clear(g)
    assert m.price("coal") > base


def test_overbuilding_a_sector_depresses_its_price():
    g = _game()
    m = market.Market()
    m.clear(g)
    base = m.price("coal")
    for i in range(5):
        _build(g, "colliery", "coalfield", 9200 + i)   # flood coal supply
    m.clear(g)
    assert m.price("coal") < base


def test_clear_is_deterministic_across_identical_games():
    g1, g2 = _game(), _game()
    m1, m2 = market.Market(), market.Market()
    m1.clear(g1)
    m2.clear(g2)
    assert m1.prices == m2.prices


# --- confidence, output multiplier, input cost, valuation ------------------

def test_confidence_is_mean_of_prices():
    m = market.Market()
    m.prices = {"coal": 1.0, "steel": 2.0, "freight": 0.5, "farm": 1.5}
    assert m.confidence() == (1.0 + 2.0 + 0.5 + 1.5) / 4.0


def test_output_mod_tracks_producing_commodity_price():
    m = market.Market()
    col = _ent("colliery")
    m.prices["coal"] = 2.0
    hi = m.output_mod(col)
    m.prices["coal"] = 0.5
    lo = m.output_mod(col)
    assert hi > lo


def test_ironworks_output_prices_off_steel_not_coal():
    m = market.Market()
    iron = _ent("ironworks")
    m.prices["steel"] = 2.0
    m.prices["coal"] = 1.0
    assert m.output_mod(iron) > 1.0


def test_bank_output_prices_off_market_confidence():
    m = market.Market()
    m.prices = {"coal": 2.0, "steel": 2.0, "freight": 2.0, "farm": 2.0}
    assert m.output_mod(_ent("bank")) == m.confidence()


def test_pure_producer_pays_no_input_cost():
    m = market.Market()
    assert m.input_cost(_ent("colliery")) == 0.0
    assert m.input_cost(_ent("estate")) == 0.0


def test_ironworks_input_cost_rises_with_coal_price():
    m = market.Market()
    iron = _ent("ironworks")
    m.prices["coal"] = 3.0
    dear = m.input_cost(iron)
    m.prices["coal"] = 0.5
    cheap = m.input_cost(iron)
    assert dear > cheap > 0.0


def test_value_rises_with_the_producing_commoditys_price():
    g = _game()
    m = market.Market()
    col = _build(g, "colliery", "coalfield", 9300)
    m.prices["coal"] = 1.0
    low = m.value(col, g)
    m.prices["coal"] = 2.0
    high = m.value(col, g)
    assert high > low > 0.0


# --- chassis threading: market lives on the game and advances each turn -----

def test_game_owns_a_market():
    g = _game()
    assert hasattr(g, "market")
    assert isinstance(g.market, market.Market)


def test_added_coal_demand_raises_coal_price_through_end_turn():
    control, heavy = _game(), _game()
    for i in range(6):
        _build(heavy, "ironworks", "iron", 9400 + i)
    control.end_turn()
    heavy.end_turn()
    assert heavy.market.price("coal") > control.market.price("coal")


def test_tech_mod_for_activates_development_hook():
    g = _game()
    prov = next(iter(g.atlas.provinces.values()))
    prov.development = 1
    base = g.tech_mod_for(prov)
    prov.development = 50
    developed = g.tech_mod_for(prov)
    assert developed > base
    assert base >= 1.0


# --- integration / soak: ripples, deflation, bounded over a century --------

def _force_strike(game, province):
    from gilded.society.labor import Movement
    mv = province.movement if province.movement is not None else Movement(province.pid)
    mv.state = "striking"
    province.movement = mv


def test_coal_strike_raises_coal_price_versus_control():
    control, struck = _game(), _game()
    coalp = _find_province(struck, "coalfield")
    for _ in range(4):
        _force_strike(struck, coalp)
        control.end_turn()
        struck.end_turn()
    assert struck.market.price("coal") > control.market.price("coal")


def test_prices_stay_bounded_over_a_century():
    g = _game()
    for _ in range(60):
        g.end_turn()
        for c in market.COMMODITIES:
            assert market.PRICE_MIN <= g.market.price(c) <= market.PRICE_MAX
