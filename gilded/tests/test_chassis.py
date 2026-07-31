"""G13 chassis tests: wiring, determinism, and the turn's fixed order."""

import pytest
from gilded.chassis import (ATTENTION_PER_TURN, STARTING_ENTERPRISES,
                            GildedGame, TurnEvent)
from gilded.docket import MAX_PETITIONS, Petition, PetitionOption
from gilded.society.court import CourtPosition
from gilded.society.ideology import (COLLECTIVE_ID, REVOLUTION_OWNER,
                                     TRANSFORM_LEGITIMACY)
from gilded.society.labor import Movement

SEED = 42


def _game() -> GildedGame:
    return GildedGame(SEED)


def _first_house(g: GildedGame) -> str:
    return sorted(g.houses)[0]


# --- init --------------------------------------------------------------------

def test_init_seeds_seven_houses_two_ventures_each():
    g = _game()
    assert len(g.houses) == 7
    assert set(g.realms) == set(g.houses)
    assert len(g.enterprises) == 7 * STARTING_ENTERPRISES
    for h in g.houses:
        ents = g.ents_of(h)
        assert len(ents) == STARTING_ENTERPRISES
        for ent in ents:
            assert ent.under_construction == 0          # operating from turn one
            assert abs(sum(ent.ledger.values()) - 100.0) < 1e-6
    assert all(g.legitimacy[h] == 50.0 for h in g.houses)


def test_init_opens_first_turn():
    g = _game()
    assert g.turn == 1
    for h in g.houses:
        assert g.attention[h] == ATTENTION_PER_TURN
        assert len(g.docket_by_house[h]) <= MAX_PETITIONS
    assert g.game_over is None


def test_player_house_flagged():
    probe = GildedGame(SEED)
    h = _first_house(probe)
    g = GildedGame(SEED, player_house=h)
    assert g.houses[h].is_player
    assert not any(g.houses[o].is_player for o in g.houses if o != h)


# --- determinism -------------------------------------------------------------

def test_same_seed_same_century():
    g1 = GildedGame(SEED)
    for _ in range(3):
        g1.end_turn()
    g2 = GildedGame(SEED)
    for _ in range(3):
        g2.end_turn()
    assert [e.text for e in g1.events] == [e.text for e in g2.events]
    assert ({h: g1.houses[h].treasury for h in g1.houses}
            == {h: g2.houses[h].treasury for h in g2.houses})


# --- the turn ----------------------------------------------------------------

def test_end_turn_advances_and_registers_are_sane():
    g = _game()
    events = g.end_turn()
    assert g.turn == 2
    assert events, "a full turn of seven houses produces news"
    assert all(isinstance(e, TurnEvent) for e in events)
    assert {e.register for e in events} <= {"gazette", "ledger", "letters"}


def test_dividends_flow_to_treasuries():
    g = _game()
    before = {h: g.houses[h].treasury for h in g.houses}
    events = g.end_turn()
    divs = [e for e in events
            if e.register == "ledger" and e.text.startswith("Dividends:")]
    assert divs and all(e.house for e in divs)
    assert any(g.houses[h].treasury > before[h] for h in g.houses)


def test_construction_completes_and_reports():
    g = _game()
    ent = g.enterprises[0]
    ent.under_construction = 1
    ent.target_tier = 2
    events = g.end_turn()
    assert ent.tier == 2
    assert any(e.text == f"{ent.name} completes its works (tier 2)"
               and e.register == "ledger" and e.house == ent.house
               for e in events)


def test_strategic_capacity_tallied():
    g = _game()
    g.end_turn()
    assert set(g.capacity) == set(g.houses)
    total = sum(amt for by_kind in g.capacity.values()
                for amt in by_kind.values())
    assert total > 0.0


def test_friction_grinds_a_conflicted_chairman():
    g = _game()
    h = _first_house(g)
    chairman = g.realms[h].court.positions[CourtPosition.BOARD_CHAIRMAN]
    assert chairman is not None
    chairman.dispositions["traditionalist_modernist"] = -100.0
    g.directives[h].set_stance("capital", 100)
    stress_before = chairman.stress
    g.end_turn()
    assert g.directives[h].friction_turns.get("capital", 0) >= 1
    assert chairman.stress > stress_before


def test_attention_resets_each_morning():
    g = _game()
    h = _first_house(g)
    g.attention[h] = 0
    g.end_turn()
    assert g.attention[h] == ATTENTION_PER_TURN


# --- the docket across turns -------------------------------------------------

def test_seatless_paper_carries_then_festers():
    g = _game()
    h = _first_house(g)
    g.houses[h].is_player = True   # the AI would rule this paper; the player lets it fester
    fired = []

    def _apply(ctx):
        fired.append(ctx.scale)
        return ["the festered thing happened"]

    pet = Petition(pid=9999, kind="test_matter", domain="family", house=h,
                   text="a private matter awaits the ruler", actors={},
                   options=[PetitionOption("only", "settle it", 0, _apply)])
    g.docket_by_house[h].append(pet)
    g.end_turn()
    assert pet.turns_waiting == 1
    assert pet in g.docket_by_house[h], "waiting paper carries to the next docket"
    events = g.end_turn()
    assert pet.escalated
    assert fired == [0.5], "festered rulings land at half effect"
    assert any(e.text == "the festered thing happened" and e.register == "letters"
               and e.house == h for e in events)
    assert pet not in g.docket_by_house[h], "escalated paper leaves the docket"


# --- succession --------------------------------------------------------------

def test_ruler_death_partitions_shares():
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    old = realm.ruler
    old.is_alive = False
    g.end_turn()
    assert realm.ruler is not old and realm.ruler.is_alive
    for ent in g.ents_of(h):
        assert old.id not in ent.ledger
    assert any(realm.ruler.id in ent.ledger for ent in g.ents_of(h))


# --- revolution and transformation -------------------------------------------

def _prime_uprising(g: GildedGame, h: str):
    g.legitimacy[h] = 5.0
    # Steer the docket: a hard-line labor stance and a like-minded security
    # chief rule "break" on the union ultimatum, which is a no-op against a
    # leaderless movement - militancy stays at its peak. (A soft chief would
    # buy the leadership off and bleed the militancy below the uprising bar.)
    g.directives[h].set_stance("labor", 100)
    chief = g.realms[h].court.positions[CourtPosition.HEAD_OF_SECURITY]
    if chief is not None:
        chief.dispositions["labor_capital"] = 100.0
    province = g.provinces_of(h)[0]
    province.unrest = 100.0
    mv = Movement(province.pid, None)
    mv.state = "striking"
    mv.militancy = 80.0
    province.movement = mv
    return province


def test_revolution_raises_the_commune():
    g = _game()
    h = _first_house(g)
    g.houses[h].is_player = True   # an AI ruler would reset its own labor directive
    g.realms[h].ruler.dispositions["labor_capital"] = 0.0
    province = _prime_uprising(g, h)
    events = []
    for _ in range(3):
        events = g.end_turn()
    assert province.owner == REVOLUTION_OWNER
    assert any("REVOLUTION" in e.text for e in events)


def test_true_believer_transforms_instead():
    g = _game()
    h = _first_house(g)
    g.realms[h].ruler.dispositions["labor_capital"] = -80.0
    province = _prime_uprising(g, h)
    events = []
    for _ in range(3):
        events = g.end_turn()
    assert province.owner == h, "a transformed House keeps its provinces"
    assert g.legitimacy[h] == TRANSFORM_LEGITIMACY
    for ent in g.ents_of(h):
        assert ent.ledger == {COLLECTIVE_ID: 100.0}
    assert any("transforms" in e.text for e in events)


def test_labor_policy_drives_enterprise_extraction():
    from gilded.chassis import GildedGame
    g = GildedGame(seed=7)
    h = next(x for x in sorted(g.houses) if g.ents_of(x))
    # Enterprises founded mid-turn get the dial next turn; pin to standing ones.
    g.directives[h].set_stance("labor", 100)
    ids = {e.eid for e in g.ents_of(h)}
    g.end_turn()
    assert all(e.extraction_dial == 100.0 for e in g.ents_of(h) if e.eid in ids)
    g.directives[h].set_stance("labor", -100)
    ids = {e.eid for e in g.ents_of(h)}
    g.end_turn()
    assert all(e.extraction_dial == 0.0 for e in g.ents_of(h) if e.eid in ids)


def test_extractionist_labor_earns_more_and_strains_more():
    from gilded.chassis import GildedGame
    hard = GildedGame(seed=11)
    soft = GildedGame(seed=11)
    h = next(x for x in sorted(hard.houses) if hard.ents_of(x))
    hard.directives[h].set_stance("labor", 100)
    soft.directives[h].set_stance("labor", -100)
    hard.end_turn()
    soft.end_turn()
    hard_unrest = sum(p.unrest for p in hard.provinces_of(h))
    soft_unrest = sum(p.unrest for p in soft.provinces_of(h))
    assert hard.houses[h].treasury >= soft.houses[h].treasury
    assert hard_unrest >= soft_unrest


def test_industrialist_capital_lifts_dividends():
    from gilded.chassis import GildedGame
    ind = GildedGame(seed=13)
    trad = GildedGame(seed=13)
    h = next(x for x in sorted(ind.houses) if ind.ents_of(x))
    ind.directives[h].set_stance("capital", 100)
    trad.directives[h].set_stance("capital", -100)
    ind.end_turn()
    trad.end_turn()
    assert ind.houses[h].treasury > trad.houses[h].treasury


def test_expansionism_and_diplomacy_apply_standing_effects():
    from gilded.chassis import GildedGame
    g = GildedGame(seed=17)
    h = next(x for x in sorted(g.houses) if g.provinces_of(x))
    g.directives[h].set_stance("expansion", 100)   # +1 unrest/turn on worked provs
    g.directives[h].set_stance("diplomacy", 100)   # +trade income
    calm = GildedGame(seed=17)
    g.end_turn()
    calm.end_turn()
    assert (sum(p.unrest for p in g.provinces_of(h))
            >= sum(p.unrest for p in calm.provinces_of(h)))
    # cosmopolitan trade income lands in the treasury as a standing drip
    assert g.houses[h].treasury >= calm.houses[h].treasury


def test_input_cost_deducted_from_consumer_enterprise_dividend():
    """Regression: chassis subtracts market.input_cost() for consumer enterprises.

    A CONSUMER enterprise has its dividend reduced by the input cost.
    This test independently computes the gross dividend and asserts that
    _last_dividend equals gross minus input_cost.

    MUST fail if the input_cost deduction line is removed from chassis.end_turn().
    """
    from gilded.market import CONSUMES

    g = GildedGame(seed=42)
    consumer_ent = None
    for ent in g.enterprises:
        if ent.kind in CONSUMES:
            consumer_ent = ent
            break
    assert consumer_ent is not None

    house = consumer_ent.house
    realm = g.realms[house]
    ruler = realm.ruler

    # Give ruler 100% of this enterprise
    consumer_ent.ledger.clear()
    consumer_ent.ledger[ruler.id] = 100.0

    # Zero out all other enterprises for this house
    for ent in g.ents_of(house):
        if ent.eid != consumer_ent.eid:
            ent.ledger.clear()

    ruler_gold_before = ruler.gold_reserve

    g.end_turn()

    ruler_gold_after = ruler.gold_reserve
    ruler_delta = ruler_gold_after - ruler_gold_before

    input_cost = g.market.input_cost(consumer_ent)

    # _last_dividend = take - input_cost (where take = ruler's share from pay_dividends)
    # For 100% ownership, ruler_delta = take (the gross, before input_cost deduction)
    # So: ruler_delta - _last_dividend = input_cost
    assert consumer_ent._last_dividend < ruler_delta, \
        f"_last_dividend ({consumer_ent._last_dividend:.4f}) should be less than " \
        f"ruler's gold delta ({ruler_delta:.4f}) by input_cost ({input_cost:.4f})"
    expected_diff = abs(ruler_delta - consumer_ent._last_dividend)
    assert abs(expected_diff - input_cost) < 0.01, \
        f"Difference ({expected_diff:.4f}) should equal input_cost ({input_cost:.4f})"


# ── L4.7: strike-is-local ──────────────────────────────────────────────

def test_a_strike_where_there_is_no_colliery_pays_no_colliery(monkeypatch):
    """A strike in a province with no colliery does NOT pay every colliery.

    Neutralises market.STRIKE_SUPPLY_REDUCTION so the market channel
    cannot move dividends.  Without the fix, the map-wide multiplier
    makes every colliery 5% richer per striking province.
    """
    from copy import deepcopy
    import gilded.market as market

    g = GildedGame(seed=42)
    # Run enough turns for movements to spawn (seed 42: turn 9)
    for _ in range(9):
        g.end_turn()

    # Collect collieries and their last dividends
    collieries = [e for e in g.enterprises if e.kind == "colliery"]
    assert len(collieries) >= 1, "need at least one colliery"

    # Find a province with a movement NOT currently striking and no colliery
    calm_movements = [
        p for p in g.atlas.provinces.values()
        if getattr(p, "movement", None) is not None
        and p.movement.state != "striking"
    ]
    assert len(calm_movements) >= 1, "need at least one calm movement province"

    # Pick one that has no colliery
    target = None
    for p in calm_movements:
        has_colliery = any(e.kind == "colliery" and e.province == p.pid
                           for e in g.enterprises)
        if not has_colliery:
            target = p
            break

    assert target is not None, \
        "fixture: no calm movement province without a colliery — this test " \
        "cannot distinguish a remote strike from a local one without one"
    assert target.movement.state != "striking", "target should not be striking"

    # Deep copy into two branches
    calm = deepcopy(g)
    struck = deepcopy(g)

    # Force a strike in the struck branch — find matching province by pid
    struck_prov = struck.atlas.provinces[target.pid]
    struck_prov.movement.state = "striking"

    # Count striking provinces in each branch
    calm_striking = sum(
        1 for p in calm.atlas.provinces.values()
        if getattr(p, "movement", None) is not None
        and p.movement.state == "striking"
    )
    struck_striking = sum(
        1 for p in struck.atlas.provinces.values()
        if getattr(p, "movement", None) is not None
        and p.movement.state == "striking"
    )
    assert struck_striking == calm_striking + 1, \
        f"Fixture: expected {calm_striking + 1} striking, got {struck_striking}"

    # End turn in both branches, neutralising market channel
    monkeypatch.setattr(market, "STRIKE_SUPPLY_REDUCTION", 1.0)
    calm.end_turn()
    struck.end_turn()

    # Every colliery's _last_dividend must be identical
    for ce in collieries:
        calm_ent = next(e for e in calm.enterprises if e.eid == ce.eid)
        struck_ent = next(e for e in struck.enterprises if e.eid == ce.eid)
        assert calm_ent._last_dividend == pytest.approx(
            struck_ent._last_dividend, abs=1e-9), \
            f"Colliery {ce.name}: calm={calm_ent._last_dividend:.6f}, struck={struck_ent._last_dividend:.6f}"


def test_a_colliery_still_loses_output_when_its_own_province_strikes(monkeypatch):
    """Guard: STRIKE_OUTPUT_MULT must still cut output for a local strike."""
    from copy import deepcopy
    import gilded.market as market

    g = GildedGame(seed=42)
    # Run enough turns for a colliery province to have a movement
    # (seed 42: Ravnbourne Colliery gets one at turn 11)
    for _ in range(11):
        g.end_turn()

    # Find a colliery whose province has a movement
    collieries = [e for e in g.enterprises if e.kind == "colliery"]
    assert len(collieries) >= 1, "need at least one colliery"

    target_ent = None
    for ent in collieries:
        prov = g.atlas.provinces.get(ent.province)
        if prov and getattr(prov, "movement", None) is not None:
            if prov.movement.state != "striking":
                target_ent = ent
                break

    assert target_ent is not None, \
        "fixture: no colliery sits in a province with a non-striking movement"

    prov = g.atlas.provinces.get(target_ent.province)

    # Deepcopy into two branches
    calm = deepcopy(g)
    struck = deepcopy(g)

    # Force a strike in the struck branch
    struck_prov = struck.atlas.provinces.get(target_ent.province)
    assert struck_prov is not None
    assert getattr(struck_prov, "movement", None) is not None
    struck_prov.movement.state = "striking"

    # End turn in both branches, neutralising market channel
    monkeypatch.setattr(market, "STRIKE_SUPPLY_REDUCTION", 1.0)
    calm.end_turn()
    struck.end_turn()

    # The struck colliery's dividend must be lower (STRIKE_OUTPUT_MULT)
    calm_ent = next(e for e in calm.enterprises if e.eid == target_ent.eid)
    struck_ent = next(e for e in struck.enterprises if e.eid == target_ent.eid)
    assert struck_ent._last_dividend < calm_ent._last_dividend, \
        f"Colliery {target_ent.name}: calm={calm_ent._last_dividend:.6f}, " \
        f"struck={struck_ent._last_dividend:.6f} — should be lower"
