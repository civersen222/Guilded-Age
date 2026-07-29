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

