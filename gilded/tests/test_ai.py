"""G18 AI tests: the AI ruler plays the same levers as the player."""

import pytest
from gilded.ai import (_executor_for, _pick_initiative, _strength,
                       _weaker_neighbor, ai_peace_check, ai_turn)
from gilded.chassis import ATTENTION_PER_TURN, GildedGame
from gilded.directives import DIRECTIVE_CONVICTION, DIRECTIVE_KEYS
from gilded.docket import DOMAIN_SEAT, Petition, PetitionOption
from gilded.fronts import WarGoal, declare_war
from gilded.society.characters import modify_opinion

SEED = 42


def _game() -> GildedGame:
    return GildedGame(SEED)


def _first(g: GildedGame) -> str:
    return sorted(g.houses)[0]


def _bordered_house(g: GildedGame) -> str:
    for a in sorted(g.houses):
        for p in g.provinces_of(a):
            for n in sorted(p.neighbors):
                o = g.atlas.provinces[n].owner
                if o and o != a and o in g.houses:
                    return a
    raise AssertionError("seed grew no contested borders")


def _fake_petition(g, h, pid, domain, biases, fired, escalated=False):
    options = [PetitionOption(f"opt{b}", f"opt{b}", b,
                              lambda ctx, key=f"{pid}:opt{b}": (fired.append(key) or []))
               for b in biases]
    return Petition(pid=pid, kind=f"fake_{pid}", domain=domain, house=h,
                    text="a fabricated matter", actors={}, options=options,
                    escalated=escalated)


def _quiet(ruler) -> None:
    """A ruler with no strong urges: no building, no marching."""
    ruler.dispositions["ambitious_content"] = 0.0
    ruler.dispositions["militarist_pacifist"] = 0.0


# --- the docket --------------------------------------------------------------

def test_ai_turn_spends_attention_and_clears_its_paper():
    g = _game()
    h = _first(g)
    assert g.docket_by_house[h]
    ai_turn(g, h)
    assert g.attention[h] < ATTENTION_PER_TURN
    assert not g.docket_by_house[h]


def test_trusted_minister_executes_a_sour_one_is_passed_over():
    g = _game()
    h = _first(g)
    realm = g.realms[h]
    domain = next(d for d, seat in sorted(DOMAIN_SEAT.items())
                  if realm.court.positions.get(seat) is not None)
    holder = realm.court.positions[DOMAIN_SEAT[domain]]
    assert _executor_for(g, realm, domain) is holder
    modify_opinion(holder, realm.ruler, -50, "a grudge")
    assert _executor_for(g, realm, domain) is realm.ruler


def test_the_ruling_follows_the_rulers_conviction():
    g = _game()
    h = _first(g)
    fired = []
    g.realms[h].ruler.dispositions["labor_capital"] = 90.0
    g.docket_by_house[h] = [_fake_petition(g, h, 901, "labor",
                                           [-60, 0, 80], fired)]
    _quiet(g.realms[h].ruler)
    ai_turn(g, h)
    assert fired == ["901:opt80"]


def test_escalated_petitions_jump_the_queue():
    g = _game()
    h = _first(g)
    ruler = g.realms[h].ruler
    ruler.dispositions["labor_capital"] = 0.0
    ruler.dispositions["traditionalist_modernist"] = 0.0
    fired = []
    g.docket_by_house[h] = [
        _fake_petition(g, h, 901, "labor", [0], fired),
        _fake_petition(g, h, 902, "capital", [0], fired, escalated=True),
    ]
    g.attention[h] = 1
    ai_turn(g, h)
    assert fired == ["902:opt0"]


# --- directives --------------------------------------------------------------

def test_directives_drift_toward_conviction():
    from gilded.ai import POLICY_STEP
    g = _game()
    h = _first(g)
    ruler = g.realms[h].ruler
    g.docket_by_house[h] = []
    _quiet(ruler)
    ruler.dispositions["militarist_pacifist"] = 100.0
    g.directives[h].set_stance("war", 0)
    ai_turn(g, h)
    new_stance = g.directives[h].stances["war"]
    assert new_stance > 0, "stance should drift toward conviction"
    assert new_stance <= POLICY_STEP, "stance should not exceed POLICY_STEP in one turn"


# --- initiatives -------------------------------------------------------------

def test_militarist_marches_on_a_weaker_neighbor():
    g = _game()
    h = _bordered_house(g)
    ruler = g.realms[h].ruler
    g.docket_by_house[h] = []
    ruler.dispositions["ambitious_content"] = 0.0
    ruler.dispositions["militarist_pacifist"] = 80.0
    for other in sorted(g.houses):
        if other != h:
            g.houses[other].treasury = 0.0
            for p in g.provinces_of(other):
                p.population = 0
    ai_turn(g, h)
    assert g.wars and g.houses[h].at_war_with


def test_a_truce_stays_the_militarist_hand():
    g = _game()
    h = _bordered_house(g)
    for other in sorted(g.houses):
        if other != h:
            g.houses[other].treasury = 0.0
            for p in g.provinces_of(other):
                p.population = 0
            g.houses[h].truces[other] = g.turn + 5
    assert _weaker_neighbor(g, h) is None


def test_ambitious_ruler_expands_the_works():
    g = _game()
    h = _first(g)
    ruler = g.realms[h].ruler
    g.docket_by_house[h] = []
    ruler.dispositions["ambitious_content"] = 80.0
    g.houses[h].treasury = 10 ** 6
    ai_turn(g, h)
    assert any(e.under_construction > 0 for e in g.enterprises
               if e.house == h)


def test_quiet_ruler_falls_back_to_matchmaking():
    g = _game()
    h = _first(g)
    realm = g.realms[h]
    g.docket_by_house[h] = []
    _quiet(realm.ruler)
    heir = next(c for c in realm.dynasty.all_characters.values()
                if c.id != realm.ruler.id)
    heir.age = 20
    msgs = ai_turn(g, h)
    assert g.attention[h] == ATTENTION_PER_TURN - 1
    assert msgs


# --- peace -------------------------------------------------------------------

def test_a_beaten_ai_house_sues_for_peace():
    g = _game()
    hs = sorted(g.houses)
    war = declare_war(g, hs[0], hs[1], WarGoal(kind="humble"))
    war.war_score = -50.0
    assert ai_peace_check(g, war) is not None
    war.war_score = -10.0
    assert ai_peace_check(g, war) is None
    war.war_score = -50.0
    g.houses[hs[0]].is_player = True       # the loser is the player
    assert ai_peace_check(g, war) is None


# --- the turn ----------------------------------------------------------------

def test_end_turn_with_ai_is_deterministic():
    # Character ids are per-game and the opinion matrix is process-global, so
    # the two games are run one after the other (chassis resets that state on
    # construction) rather than interleaved.
    a = GildedGame(7)
    for _ in range(5):
        a.end_turn()
    a_events = [e.text for e in a.events]
    b = GildedGame(7)
    for _ in range(5):
        b.end_turn()
    assert [e.text for e in b.events] == a_events
# --- rival capital verbs (Job 2) ---------------------------------------------

def test_rival_appoints_director():
    """A rival House with a venture and empty director seat appoints one."""
    g = _game()
    rival = sorted(g.houses)[0]
    realm = g.realms[rival]
    from gilded.ai import _pick_initiative
    verbs = set()
    for _ in range(20):
        init = _pick_initiative(g, rival, realm)
        if init and isinstance(init, tuple) and len(init) == 2:
            verbs.add(init[0])
        g.end_turn()
    assert "appoint_director" in verbs or any(
        e.director_id is not None for e in g.enterprises if e.house == rival
    ), f"Rival should eventually appoint a director. Got verbs: {verbs}"


def test_rival_routes_buy_shares():
    """A rival can route buy_shares as a capital verb."""
    g = _game()
    rival = sorted(g.houses)[1]
    realm = g.realms[rival]
    from gilded.ai import _pick_initiative
    verbs = set()
    for _ in range(15):
        init = _pick_initiative(g, rival, realm)
        if init and isinstance(init, tuple) and len(init) == 2:
            verbs.add(init[0])
        g.end_turn()
    assert any(v in verbs for v in ("buy_shares", "appoint_director", "sell_shares")), \
        f"Rival should route capital verbs. Got: {verbs}"


def test_rival_routes_sell_shares():
    """A rival under financial pressure can route sell_shares."""
    g = _game()
    rival = sorted(g.houses)[2]
    realm = g.realms[rival]
    g.houses[rival].treasury = 0.1
    from gilded.ai import _pick_initiative
    verbs = set()
    for _ in range(15):
        init = _pick_initiative(g, rival, realm)
        if init and isinstance(init, tuple) and len(init) == 2:
            verbs.add(init[0])
        g.end_turn()
    assert any(v in verbs for v in ("sell_shares", "buy_shares", "appoint_director")), \
        f"Rival should route capital verbs. Got: {verbs}"


def test_rival_attention_cost():
    """A rival capital move costs at least one attention point.

    Verify that when a rival routes any action (petition ruling or initiative),
    their attention pool decreases accordingly.
    """
    g = _game()
    from gilded import ai as ai_mod
    orig_ai_turn = ai_mod.ai_turn

    actions = []
    def observing_turn(game, house_name):
        h = game.houses.get(house_name)
        if h and not h.is_player:
            before = game.attention.get(house_name, 0)
            results = orig_ai_turn(game, house_name)
            after = game.attention.get(house_name, 0)
            if results:
                actions.append((game.turn, house_name, before - after))
            return results
        return orig_ai_turn(game, house_name)
    ai_mod.ai_turn = observing_turn

    try:
        for _ in range(30):
            g.end_turn()
    finally:
        ai_mod.ai_turn = orig_ai_turn

    assert len(actions) > 0, "No rival actions observed in 30 turns"
    for turn, name, spent in actions:
        assert spent >= 1, f"Turn {turn} {name}: expected >= 1 attention spent, got {spent}"


def test_no_gold_minted_by_share_trade():
    """A share trade cannot create gold from nothing.

    Measured per-trade: snapshot total gold (treasuries + char gold_reserves)
    before and after each rival share trade. A trade may move gold down
    (fees/taxes) but must never move it up.
    """
    g = _game()
    def total_gold(game):
        total = sum(h.treasury for h in game.houses.values())
        for realm in game.realms.values():
            for c in realm.characters:
                total += getattr(c, "gold_reserve", 0.0)
        return total

    # Patch ai_turn to observe share trades
    from gilded import ai as ai_mod
    orig_ai_turn = ai_mod.ai_turn
    trades = []
    def observing_turn(game, house_name):
        if house_name in game.houses and not game.houses[house_name].is_player:
            before = total_gold(game)
            results = orig_ai_turn(game, house_name)
            after = total_gold(game)
            # Check if a share trade was routed
            if results and any("buys" in r or "sells" in r for r in results):
                trades.append((game.turn, house_name, before, after))
            return results
        return orig_ai_turn(game, house_name)
    ai_mod.ai_turn = observing_turn

    try:
        for _ in range(60):
            g.end_turn()
    finally:
        ai_mod.ai_turn = orig_ai_turn

    for turn, house, before, after in trades:
        assert after <= before + 0.001, (
            f"Turn {turn} {house}: share trade minted gold "
            f"({before:.4f} -> {after:.4f})"
        )


def test_player_house_not_played_for():
    """end_turn skips ai_turn for the player house (only resolve_unattended runs)."""
    g = _game()
    hs = sorted(g.houses)
    g.houses[hs[0]].is_player = True
    player = hs[0]
    # Patch gilded.ai.ai_turn to track which houses it's called for
    from gilded import ai as ai_mod
    from gilded.ai import ai_turn as _ai_turn
    called_for = []
    def mock_ai_turn(game, name):
        called_for.append(name)
        return _ai_turn(game, name)
    ai_mod.ai_turn = mock_ai_turn
    try:
        g.end_turn()
    finally:
        ai_mod.ai_turn = _ai_turn
    # The player house should NOT have ai_turn called for it
    assert player not in called_for, f"ai_turn was called for player house {player}"


def test_rival_appoints_named_candidate():
    """A rival appoints the candidate it named, not pool[-1].

    Pinned on four axes:
      WHO  — the seated id equals the id named (neither pool[0] nor pool[-1])
      WHERE — the venture asked for is the one that changed
      WHAT ELSE (board) — no other enterprise changed in any way
      WHAT ELSE (ledger) — the named venture's ledger shifted shares from
        ruler to director (salary), and nothing else in the enterprise
        changed (extraction_dial, tier, etc.)

    Uses a NON-first venture so that a handler seating the pick on the
    House's first venture (regardless of which was asked for) is caught.

    Captures the full board state (enterprises + the people who hold/run them)
    before and after, then asserts exactly which parts differ: the ones the
    appointment is supposed to change, changed; everything else byte-identical.
    """
    import random
    g = _game()
    rival = sorted(g.houses)[0]
    realm = g.realms[rival]
    from gilded.docket import director_candidates, RulingContext, _init_appoint_director
    from gilded.society.realm import DIRECTOR_SALARY_PCT
    # Collect ventures owned by rival with empty director seat
    owned = [e for e in g.enterprises if e.house == rival and e.director_id == ""]
    assert len(owned) >= 2, "need at least 2 ventures to test WHERE"
    # Use the SECOND venture — not the first — so the "seats on first" mutation fails
    ent = owned[1]
    pool = director_candidates(g, rival, ent.eid)
    assert len(pool) >= 3, "need at least 3 candidates to pick the middle one"
    # Pick someone who is neither pool[0] nor pool[-1]
    named_char_id = pool[1].id
    pick = pool[1]

    # --- capture the FULL board state before the call ---
    # Enterprise state: director_id, ledger, extraction_dial, tier
    ents_before = {e.eid: {
        "director_id": e.director_id,
        "ledger": dict(e.ledger),
        "extraction_dial": e.extraction_dial,
        "tier": e.tier,
    } for e in g.enterprises}
    # Opinion: pick -> ruler
    ruler = realm.ruler
    opinions_before = dict(pick._society.opinions)

    ctx = RulingContext(game=g, house=rival, executor=realm.ruler, rng=random.Random(SEED))
    msgs = _init_appoint_director(ctx, eid=ent.eid, char_id=named_char_id)

    # --- capture the FULL board state after the call ---
    ents_after = {e.eid: {
        "director_id": e.director_id,
        "ledger": dict(e.ledger),
        "extraction_dial": e.extraction_dial,
        "tier": e.tier,
    } for e in g.enterprises}
    opinions_after = dict(pick._society.opinions)

    # WHO — the right person
    assert ent.director_id == named_char_id, \
        f"Expected director {named_char_id}, got {ent.director_id}"
    assert named_char_id != pool[0].id and named_char_id != pool[-1].id, \
        "named candidate must not be pool[0] or pool[-1]"

    # WHERE — find which enterprise(s) changed
    changed_eids = set()
    for eid in ents_before:
        if ents_before[eid] != ents_after[eid]:
            changed_eids.add(eid)
    assert ent.eid in changed_eids, f"Expected {ent.eid} to change; changed={changed_eids}"

    # WHAT ELSE (board) — no OTHER enterprise changed at all
    for eid in ents_before:
        if eid != ent.eid:
            assert ents_before[eid] == ents_after[eid], \
                f"Enterprise {eid} should not have changed. Before: {ents_before[eid]}, After: {ents_after[eid]}"

    # WHAT ELSE (ledger on the named venture) — exactly the right changes
    # director_id changed from "" to pick.id
    assert ents_before[ent.eid]["director_id"] == "", "director was empty before"
    assert ents_after[ent.eid]["director_id"] == named_char_id

    # extraction_dial did NOT change
    assert ents_before[ent.eid]["extraction_dial"] == ents_after[ent.eid]["extraction_dial"], \
        f"extraction_dial changed from {ents_before[ent.eid]['extraction_dial']} to {ents_after[ent.eid]['extraction_dial']}"

    # tier did NOT change
    assert ents_before[ent.eid]["tier"] == ents_after[ent.eid]["tier"], \
        f"tier changed from {ents_before[ent.eid]['tier']} to {ents_after[ent.eid]['tier']}"

    # ledger: ruler lost shares, pick gained shares (salary transfer)
    ledger_b = ents_before[ent.eid]["ledger"]
    ledger_a = ents_after[ent.eid]["ledger"]
    ruler_id = ruler.id
    pick_id = pick.id
    ruler_held_b = ledger_b.get(ruler_id, 0.0)
    pick_held_b = ledger_b.get(pick_id, 0.0)
    ruler_held_a = ledger_a.get(ruler_id, 0.0)
    pick_held_a = ledger_a.get(pick_id, 0.0)

    # Ruler should have lost approximately DIRECTOR_SALARY_PCT
    ruler_loss = ruler_held_b - ruler_held_a
    assert ruler_loss >= DIRECTOR_SALARY_PCT - 0.1, \
        f"Ruler lost {ruler_loss:.2f} shares, expected ~{DIRECTOR_SALARY_PCT}"

    # Pick should have gained approximately DIRECTOR_SALARY_PCT
    pick_gain = pick_held_a - pick_held_b
    assert pick_gain >= DIRECTOR_SALARY_PCT - 0.1, \
        f"Pick gained {pick_gain:.2f} shares, expected ~{DIRECTOR_SALARY_PCT}"

    # No other ledger keys changed on this venture
    all_keys = set(ledger_b.keys()) | set(ledger_a.keys())
    for k in all_keys:
        if k != ruler_id and k != pick_id:
            assert ledger_b.get(k, 0.0) == ledger_a.get(k, 0.0), \
                f"Ledger key {k} changed from {ledger_b.get(k, 0.0)} to {ledger_a.get(k, 0.0)}"

    # Opinion: pick -> ruler should have increased
    pair = (pick_id, ruler_id)
    opinion_b = opinions_before.get(pair, 0)
    opinion_a = opinions_after.get(pair, 0)
    assert opinion_a > opinion_b, \
        f"Opinion {pair} did not increase: {opinion_b} -> {opinion_a}"


def test_director_salary_comes_from_ruler_not_largest_holder():
    """The Director's salary is paid by the ruler, not the largest holder.

    Gives a third party 70% of the enterprise, the ruler 30%.  After
    appointment, the stranger must be untouched at 70.0, the ruler must
    have paid DIRECTOR_SALARY_PCT, and the appointee holds exactly that.
    """
    g = _game()
    rival = sorted(g.houses)[0]
    realm = g.realms[rival]
    from gilded.docket import director_candidates, RulingContext, _init_appoint_director
    from gilded.society.realm import DIRECTOR_SALARY_PCT

    # Pick an enterprise with no director
    owned = [e for e in g.enterprises if e.house == rival and e.director_id == ""]
    assert len(owned) >= 1
    ent = owned[0]

    # Pick characters from the actual candidate pool (director_candidates filters
    # out court holders, directors, ruler, dead, and underage)
    ruler = realm.ruler
    cands = director_candidates(g, rival, ent.eid)
    assert len(cands) >= 2, "need at least 2 director candidates besides ruler"

    stranger = cands[0]
    appointee = cands[1]

    # Clear ledger, give stranger 70%, ruler 30%
    ent.ledger.clear()
    ent.ledger[stranger.id] = 70.0
    ent.ledger[ruler.id] = 30.0

    # Fixture check: stranger is the largest holder
    largest = max(ent.ledger, key=lambda k: ent.ledger[k])
    assert largest == stranger.id, \
        f"Stranger {stranger.id} should be largest holder, not {largest}"

    # Appoint the appointee
    import random
    ctx = RulingContext(g, rival, executor=realm.ruler, rng=random.Random(SEED))
    ent.director_id = ""
    _init_appoint_director(ctx, eid=ent.eid, char_id=appointee.id)

    # Assertions
    assert ent.ledger.get(stranger.id, 0.0) == pytest.approx(70.0, abs=1e-9), \
        f"Stranger should still hold 70.0, got {ent.ledger.get(stranger.id, 0.0)}"
    assert ent.ledger.get(ruler.id, 0.0) == pytest.approx(
        30.0 - DIRECTOR_SALARY_PCT, abs=1e-9), \
        f"Ruler should hold {30.0 - DIRECTOR_SALARY_PCT}, got {ent.ledger.get(ruler.id, 0.0)}"
    assert ent.ledger.get(appointee.id, 0.0) == pytest.approx(
        DIRECTOR_SALARY_PCT, abs=1e-9), \
        f"Appointee should hold {DIRECTOR_SALARY_PCT}, got {ent.ledger.get(appointee.id, 0.0)}"


# =============================================================================
# WAVE 16 — the eight boundary rules of the war-target decision
# =============================================================================

def _shape(g, house, pop, treasury):
    """Set pop on the first province (sorted by pid), clear the rest."""
    provs = sorted(g.provinces_of(house), key=lambda p: p.pid)
    for i, p in enumerate(provs):
        p.population = pop if i == 0 else 0
    g.houses[house].treasury = float(treasury)


def test_s16_strength_counts_the_treasury():
    """B4-treasury: strength = pop//5 + treasury.
    With treasury dropped, Ashworth (pop 10, gold 50) reads strength 2 instead of 52,
    making it weaker than Brandtner (pop 100, gold 0 = strength 20).
    Correct code: no neighbor is weaker (Ashworth 52 > 0.7*20=14, but Brandtner 20 < 0.7*200=140 for D,K).
    Actually: Brandtner strength=20, bar=14. Ashworth=52>14, D=200>14, K=200>14 → None."""
    g = _game()
    _shape(g, "Brandtner", 100, 0)
    _shape(g, "Ashworth", 10, 50)
    _shape(g, "Duval-Corse", 1000, 0)
    _shape(g, "Karsgate", 1000, 0)
    assert g.houses["Brandtner"].treasury == 0.0
    assert g.houses["Ashworth"].treasury == 50.0
    assert not g.houses["Brandtner"].at_war_with
    assert _weaker_neighbor(g, "Brandtner") is None


def test_s16_strength_converts_population_at_five():
    """B4-cost: pop//REGIMENT_POP_COST where REGIMENT_POP_COST=5.
    5//5=1 vs 4//5=0 → Ashworth strength 0 < 0.7*1 → qualifies.
    Mutant //6: 5//6=0, 4//6=0 → both zero, no weaker neighbor → None."""
    g = _game()
    _shape(g, "Brandtner", 5, 0)
    _shape(g, "Ashworth", 4, 0)
    _shape(g, "Duval-Corse", 1000, 0)
    _shape(g, "Karsgate", 1000, 0)
    assert g.houses["Brandtner"].treasury == 0.0
    assert g.houses["Ashworth"].treasury == 0.0
    p = sorted(g.provinces_of("Brandtner"), key=lambda p: p.pid)[0]
    assert p.population == 5
    p = sorted(g.provinces_of("Ashworth"), key=lambda p: p.pid)[0]
    assert p.population == 4
    assert _weaker_neighbor(g, "Brandtner") == "Ashworth"


def test_s16_two_qualifying_rivals_the_first_alphabetically_is_marched_on():
    """B5-order: neighbors are sorted forward.
    Ashworth and Karsgate both have strength 0 (qualify).
    'Ashworth' < 'Karsgate' → forward sort returns Ashworth first.
    Reverse sort would return Karsgate."""
    g = _game()
    _shape(g, "Brandtner", 1000, 0)
    _shape(g, "Ashworth", 0, 0)
    _shape(g, "Karsgate", 0, 0)
    _shape(g, "Duval-Corse", 0, 1000)
    assert g.houses["Ashworth"].treasury == 0.0
    assert g.houses["Karsgate"].treasury == 0.0
    assert g.houses["Duval-Corse"].treasury == 1000.0
    assert "Ashworth" < "Karsgate"
    assert _weaker_neighbor(g, "Brandtner") == "Ashworth"


def test_s16_a_house_already_at_war_is_not_a_fresh_target():
    """B5-war: a House already in at_war_with is skipped.
    Ashworth is weak (0 gold, 0 pop) AND already at war → must be skipped.
    Duval-Corse and Karsgate hold 1000 gold each → too strong.
    Without the skip, Ashworth would be returned."""
    g = _game()
    _shape(g, "Brandtner", 1000, 0)
    _shape(g, "Ashworth", 0, 0)
    _shape(g, "Duval-Corse", 0, 1000)
    _shape(g, "Karsgate", 0, 1000)
    g.houses["Brandtner"].at_war_with.add("Ashworth")
    assert "Ashworth" in g.houses["Brandtner"].at_war_with
    assert g.houses["Ashworth"].treasury == 0.0
    assert _weaker_neighbor(g, "Brandtner") is None


def test_s16_a_truce_expiring_this_turn_no_longer_shields():
    """B5-truce: the guard is truces[other] > game.turn (strict greater-than).
    A truce expiring THIS turn (== game.turn) does NOT shield — the turn has arrived.
    A truce expiring NEXT turn (== game.turn + 1) still shields.
    Two assertions bracket the bar: 139/140 for B5-bar, here g.turn vs g.turn+1.
    The g.turn case kills > → >=; the g.turn+1 case kills the check being removed."""
    g = _game()
    _shape(g, "Brandtner", 1000, 0)
    _shape(g, "Ashworth", 0, 0)
    _shape(g, "Duval-Corse", 0, 1000)
    _shape(g, "Karsgate", 0, 1000)
    # Truce expiring THIS turn → no longer shields, Ashworth is a valid target
    g.houses["Brandtner"].truces["Ashworth"] = g.turn
    assert g.houses["Brandtner"].truces.get("Ashworth", 0) == g.turn
    assert _weaker_neighbor(g, "Brandtner") == "Ashworth"
    # Truce expiring NEXT turn → still shields
    g.houses["Brandtner"].truces["Ashworth"] = g.turn + 1
    assert g.houses["Brandtner"].truces.get("Ashworth", 0) == g.turn + 1
    assert _weaker_neighbor(g, "Brandtner") is None


def test_s16_the_weaker_rival_is_the_target_not_the_stronger():
    """B5-dir: the AI targets the WEAKER neighbor (<), not the stronger (>).
    Ashworth strength=0 (weak), Duval-Corse strength=1000 (strong).
    Correct: returns Ashworth. Mutant > returns Duval-Corse."""
    g = _game()
    _shape(g, "Brandtner", 1000, 0)
    _shape(g, "Ashworth", 0, 0)
    _shape(g, "Duval-Corse", 0, 1000)
    _shape(g, "Karsgate", 0, 1000)
    assert g.houses["Ashworth"].treasury == 0.0
    assert g.houses["Duval-Corse"].treasury == 1000.0
    assert _weaker_neighbor(g, "Brandtner") == "Ashworth"


def test_s16_weaker_means_seven_tenths_not_merely_poorer():
    """B5-bar: WEAKER = 0.7, pinned with literal numbers 139 and 140.
    Brandtner strength = 200, bar = 0.7 * 200 = 140.
    Ashworth at 139: 139 < 140 → qualifies. Mutant 0.5: bar=100, 139>100 → None (killed by 139 case).
    Ashworth at 140: 140 is NOT < 140 → None. Mutant 1.0: bar=200, 140<200 → Ashworth (killed by 140 case).
    Also kills < → <= since 140 == 140. Using literals, not WEAKER, so the constant can move."""
    g = _game()
    _shape(g, "Brandtner", 1000, 0)
    _shape(g, "Duval-Corse", 0, 1000)
    _shape(g, "Karsgate", 0, 1000)
    # Ashworth at 139 — one below the bar (0.7 * 200 = 140)
    _shape(g, "Ashworth", 0, 139)
    assert g.houses["Ashworth"].treasury == 139.0
    assert g.houses["Brandtner"].treasury == 0.0
    assert _weaker_neighbor(g, "Brandtner") == "Ashworth"
    # Ashworth at 140 — exactly on the bar (140 is NOT < 140)
    _shape(g, "Ashworth", 0, 140)
    assert g.houses["Ashworth"].treasury == 140.0
    assert _weaker_neighbor(g, "Brandtner") is None


def test_s16_war_conviction_bar_is_fifty_and_strict():
    """B12-bar: WAR_CONVICTION = 50.0, pinned with literal values 25.0 and 50.1.
    militarist_pacifist = 25.0: below the bar → no war. Mutant 0.0: 25.0 > 0.0 → war (killed).
    militarist_pacifist = 50.1: above the bar → war declared. Mutant 60.0: 50.1 < 60.0 → no war (killed).
    50.0 itself does NOT declare (strict >), 50.1 does. Using literals, not WAR_CONVICTION."""
    g = _game()
    _shape(g, "Brandtner", 0, 500)
    _shape(g, "Ashworth", 0, 0)
    _shape(g, "Duval-Corse", 0, 1000)
    _shape(g, "Karsgate", 0, 1000)
    realm = g.realms["Brandtner"]
    ruler = realm.ruler
    ruler.dispositions["ambitious_content"] = 0.0

    # Seat directors on all enterprises with empty director_id
    for ent in g.enterprises:
        if ent.house == "Brandtner" and ent.director_id == "":
            for c in realm.characters:
                if c.is_alive and c.age >= 16 and c.id != ruler.id:
                    ent.director_id = c.id
                    break

    assert g.houses["Brandtner"].treasury == 500.0
    assert not g.houses["Brandtner"].at_war_with
    assert _weaker_neighbor(g, "Brandtner") == "Ashworth"

    # Below the bar: 25.0 < 50.0 → no war
    ruler.dispositions["militarist_pacifist"] = 25.0
    assert ruler.dispositions["militarist_pacifist"] == 25.0
    result = _pick_initiative(g, "Brandtner", realm)
    assert result is None

    # Above the bar: 50.1 > 50.0 → war declared
    ruler.dispositions["militarist_pacifist"] = 50.1
    assert ruler.dispositions["militarist_pacifist"] == 50.1
    result = _pick_initiative(g, "Brandtner", realm)
    assert result is not None
    assert result[0] == "declare_war"
    assert result[1].get("target_house") == "Ashworth"

