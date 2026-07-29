"""G18 AI tests: the AI ruler plays the same levers as the player."""

from gilded.ai import (_executor_for, _weaker_neighbor, ai_peace_check,
                       ai_turn)
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

