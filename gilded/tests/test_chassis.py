"""G13 chassis tests: wiring, determinism, and the turn's fixed order."""

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
    """Regression: chassis must subtract market.input_cost() for consumer enterprises.

    A CONSUMER enterprise (ironworks, mill, rail_co — one that appears in CONSUMES)
    has its dividend reduced by the input cost.  This test verifies the deduction
    actually happens by independently computing the gross dividend and asserting
    that _last_dividend equals gross minus input_cost.  The test MUST fail if the
    input_cost deduction line is removed from chassis.end_turn().
    """
    from gilded.market import CONSUMES
    from gilded.society.shares import pay_dividends

    g = GildedGame(seed=42)

    # Find a consumer enterprise (one that appears in CONSUMES)
    consumer_ent = None
    for ent in g.enterprises:
        if ent.kind in CONSUMES:
            consumer_ent = ent
            break
    assert consumer_ent is not None, "Should have at least one consumer enterprise"

    house = consumer_ent.house
    realm = g.realms[house]
    provinces = g.atlas.provinces

    # Capture ruler's gold before end_turn
    ruler = realm.ruler
    ruler_gold_before = ruler.gold_reserve

    # Run end_turn so chassis computes dividends
    g.end_turn()

    ruler_gold_after = ruler.gold_reserve
    ruler_delta = ruler_gold_after - ruler_gold_before

    # pay_dividends returns the ruler's share (house_take).  The chassis then
    # subtracts input_cost from this.  Since pay_dividends adds directly to
    # gold_reserve, the ruler's gold delta equals the gross share.
    #
    # _last_dividend = take - input_cost (where take = ruler's share from pay_dividends)
    # ruler_delta from this one enterprise = take (the gross)
    #
    # But ruler_delta includes ALL enterprises.  We need to isolate this one.
    # Instead, compute the gross independently using pay_dividends on the ent
    # with mod=1.0 (no mods), then compare.
    #
    # Better approach: use the chassis's own computation.  The chassis calls
    # pay_dividends with the mod applied, then subtracts input_cost.
    # We can verify: _last_dividend + input_cost should equal the ruler's
    # share from this enterprise.
    #
    # Since we can't easily re-run pay_dividends with the same mod, use
    # the treasury delta as our independent measure.
    #
    # Treasury only gets dividends when take_total > 0.  take_total sums
    # _last_dividend for all enterprises.  Without input_cost deduction,
    # _last_dividend would be higher by input_cost.
    #
    # Simplest: verify _last_dividend < ruler_delta_for_this_ent.
    # We know pay_dividends adds take to ruler's gold_reserve.
    # The input_cost deduction only affects _last_dividend and treasury.
    #
    # For a 100%-owned enterprise: ruler_delta_from_ent = take = _last_dividend + input_cost
    # But other enterprises also contribute to ruler_delta.
    #
    # Use a controlled setup: give ruler 100% of one consumer ent, 0% of others.

    # Reset and use a fresh game
    g2 = GildedGame(seed=42)
    consumer_ent2 = None
    for ent in g2.enterprises:
        if ent.kind in CONSUMES:
            consumer_ent2 = ent
            break
    assert consumer_ent2 is not None

    house2 = consumer_ent2.house
    realm2 = g2.realms[house2]
    ruler2 = realm2.ruler

    # Give ruler 100% of this enterprise
    consumer_ent2.ledger.clear()
    consumer_ent2.ledger[ruler2.id] = 100.0

    # Zero out all other enterprises for this house (give to nobody)
    for ent in g2.ents_of(house2):
        if ent.eid != consumer_ent2.eid:
            ent.ledger.clear()

    ruler_gold_before2 = ruler2.gold_reserve
    treasury_before = g2.houses[house2].treasury

    g2.end_turn()

    ruler_gold_after2 = ruler2.gold_reserve
    ruler_delta2 = ruler_gold_after2 - ruler_gold_before2
    treasury_delta = g2.houses[house2].treasury - treasury_before

    input_cost = g2.market.input_cost(consumer_ent2)

    # Verify input_cost is non-zero (consumer enterprise)
    assert input_cost > 0, f"input_cost should be > 0 for {consumer_ent2.kind}"

    # With 100% ownership and no other enterprises paying:
    # ruler_delta2 = take (gross from pay_dividends)
    # _last_dividend = take - input_cost
    # treasury_delta = _last_dividend (if positive)
    assert consumer_ent2._last_dividend < ruler_delta2, \
        f"_last_dividend ({consumer_ent2._last_dividend:.4f}) should be less than " \
        f"ruler's gold delta ({ruler_delta2:.4f}) by input_cost ({input_cost:.4f})"
    expected_diff = abs(ruler_delta2 - consumer_ent2._last_dividend)
    assert abs(expected_diff - input_cost) < 0.01, \
        f"Difference ({expected_diff:.4f}) should equal input_cost ({input_cost:.4f})"
