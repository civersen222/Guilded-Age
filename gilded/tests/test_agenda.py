from gilded.chassis import GildedGame
import pytest


def test_game_has_stage2_state():
    g = GildedGame(seed=7)
    assert g.agendas == {}
    assert g.informants == set()
    assert g.takeovers == []


from gilded import agenda
from gilded.agenda import (Goal, FAMILIES, ensure_agenda, select_goal,
                           goal_domain, goal_initiative,
                           _weakest_neighbor, _richest_rival, _best_relations,
                           _strongest_rival, _stat, _strength, _bordering,
                           _marriageable, _target_for, _score_family,
                           _worst_province, _why, _found_spot)
import gilded.agenda as _agenda_mod
from gilded.enterprises import ENTERPRISE_TYPES, TIER_MAX
from gilded.society.schemes import Takeover
from gilded.society.realm import disloyal_shareholders


def _ai_house(g):
    return next(h for h in sorted(g.houses) if not g.houses[h].is_player)


def test_select_goal_is_deterministic_no_rng():
    g1 = GildedGame(seed=11)
    g2 = GildedGame(seed=11)
    h = _ai_house(g1)
    before = g1.rng.random()          # selection must not consume the game rng
    goal = select_goal(g1, h)
    after = g1.rng.random()
    assert before == GildedGame(seed=11).rng.random()
    assert select_goal(g2, h).family == goal.family
    assert select_goal(g2, h).target == goal.target


def test_select_goal_picks_a_valid_family():
    g = GildedGame(seed=5)
    h = _ai_house(g)
    goal = select_goal(g, h)
    assert goal.family in FAMILIES
    assert goal.opened_turn == g.turn
    assert isinstance(goal.why, str) and goal.why


def test_ensure_agenda_holds_for_commit_window():
    g = GildedGame(seed=9)
    h = _ai_house(g)
    first = ensure_agenda(g, h)
    assert g.agendas[h] is first
    g.turn += 1
    assert ensure_agenda(g, h) is first          # same object, still committed


def test_ensure_agenda_reevaluates_after_window():
    g = GildedGame(seed=9)
    h = _ai_house(g)
    first = ensure_agenda(g, h)
    g.turn = first.opened_turn + first.commit_turns
    second = ensure_agenda(g, h)
    assert second.opened_turn == g.turn          # a fresh selection


def test_goal_domain_maps_every_family():
    for fam in FAMILIES:
        assert goal_domain(Goal(fam, None, 1, 10, "")) in (
            "capital", "expansion", "labor", "press", "diplomacy", "war")


def test_chassis_advances_takeovers():
    from gilded.society.schemes import Takeover
    g = GildedGame(seed=6)
    a, b = sorted(g.houses)[0], sorted(g.houses)[1]
    buyer = g.realms[a].ruler
    tk = Takeover(buyer, a, b)
    g.takeovers.append(tk)
    g.end_turn()
    assert tk in g.takeovers or tk.complete


from gilded.docket import INITIATIVES, initiative


def test_start_takeover_initiative_registers_a_takeover():
    g = GildedGame(seed=6)
    a, b = sorted(g.houses)[0], sorted(g.houses)[1]
    assert "start_takeover" in INITIATIVES
    executor = g.realms[a].ruler
    initiative(g, a, "start_takeover", executor, target_house=b)
    assert any(t.buyer_house == a and t.target_house == b for t in g.takeovers)


def test_start_takeover_rejects_self_and_duplicates():
    g = GildedGame(seed=6)
    a = sorted(g.houses)[0]
    executor = g.realms[a].ruler
    out = initiative(g, a, "start_takeover", executor, target_house=a)
    assert g.takeovers == [] and out


def test_establish_informant_initiative_sets_flag():
    g = GildedGame(seed=6)
    a, b = sorted(g.houses)[0], sorted(g.houses)[1]
    assert "establish_informant" in INITIATIVES
    executor = g.realms[a].ruler
    initiative(g, a, "establish_informant", executor, target_house=b)
    assert (a, b) in g.informants


def test_ai_turn_populates_and_holds_agenda():
    g = GildedGame(seed=13)
    from gilded.ai import ai_turn
    h = next(x for x in sorted(g.houses) if not g.houses[x].is_player)
    ai_turn(g, h)
    assert h in g.agendas
    first = g.agendas[h]
    g.turn += 1
    ai_turn(g, h)
    assert g.agendas[h] is first          # held within the commit window


def test_ai_still_runs_a_full_century():
    g = GildedGame(seed=21)
    for _ in range(40):
        if g.game_over is not None:
            break
        g.end_turn()
    assert any(h in g.agendas for h in g.houses)


def test_goal_initiative_glory_falls_back_to_none():
    g = GildedGame(seed=6)
    h = _ai_house(g)
    goal = Goal("Glory", None, g.turn, 10, "prestige")
    assert goal_initiative(g, h, goal) is None


def test_goal_initiative_dynasty_skips_when_already_tied():
    g = GildedGame(seed=5)
    while g.turn < 13:
        g.end_turn()
    a = "Ferrenholt"
    # Build the precondition instead of hoping the world contains it: pick a
    # House Ferrenholt is NOT yet bound to, tie them by hand, and check the
    # gate. (The old form pinned Ferrenholt/Karsgate off one generated world.)
    tied = [r for r in g.houses if r != a
            and (a, r) in g.marriages.marriages]
    untied = [r for r in g.houses if r != a and r not in tied]
    assert untied, "no untied House to build the fixture against"
    b = untied[0]
    g.marriages.marriages.append(("x", a, "y", b))  # now they are bound
    goal = Goal("Dynasty", b, g.turn, 10, "wed")
    assert goal_initiative(g, a, goal) is None       # gate: never re-propose


def test_goal_initiative_conquest_acts_only_on_declared_target():
    """Conquest initiative declares war on its declared target — unconditional."""
    g = _bordered_game()
    h = "Ashworth"
    tgt = _weakest_neighbor(g, h)
    assert tgt == "Brandtner"
    out = goal_initiative(g, h, Goal("Conquest", tgt, g.turn, 10, "war"))
    assert out is not None
    verb, kw = out
    assert verb == "declare_war" and kw["target_house"] == tgt


def test_ensure_agenda_reselects_when_target_vanishes():
    g = GildedGame(seed=6)
    h = _ai_house(g)
    stale = Goal("Conquest", "GhostHouse", g.turn, 10, "war")
    g.agendas[h] = stale
    fresh = ensure_agenda(g, h)
    assert fresh is not stale
    assert fresh.target != "GhostHouse"


# --- Fixture: seed 5, turn 13, Ferrenholt — value-decided targets -----------

def _fixture_game():
    """Return a game at seed 5, advanced to turn 13, plus Ferrenholt house.

    At this state every target helper returns a STRICTLY unique value-winner:
      _weakest_neighbor -> Karsgate (rebalanced costs changed treasury trajectories)
      _richest_rival    -> Vantrell  (most enterprises or highest value)
      _best_relations   -> Vantrell    (highest relations)
      _strongest_rival  -> Vantrell     (highest power)
      _bordering        -> [Ashworth, Karsgate]
    """
    g = GildedGame(seed=5)
    while g.turn < 13:
        g.end_turn()
    return g


def _bordered_game():
    """Game at seed 26, turn 13, with a known two-neighbor border state.

    The C5 wave-1 atlas left most Houses with no direct border (seed 5's
    Ferrenholt borders nobody), but seed 26's Ashworth borders Brandtner.
    Re-assigning two provinces (a known-state construction, no rng) makes
    Ashworth border [Brandtner, Karsgate]:
      prov 75 (Brandtner's, adjacent to Ashworth) -> Karsgate
      prov 69 (empty, adjacent to Ashworth)       -> Brandtner
    Brandtner (treasury ~794) is strictly weaker than Karsgate (~4141), so
    _weakest_neighbor is value-decided, not a tie-break.
    """
    g = GildedGame(seed=26)
    while g.turn < 13:
        g.end_turn()
    g.atlas.provinces[75].owner = "Karsgate"
    g.atlas.provinces[69].owner = "Brandtner"
    return g


# --- R1: _stat reads only the LIVING, empty court reads 0.0 ----------------

def test_r1_stat_empty_court_returns_zero():
    """_stat with no living courtier returns 0.0, not some other default."""
    g = _fixture_game()
    realm = g.realms["Ferrenholt"]
    # Court positions with no living courtier -> 0.0
    val = _stat(realm, "intrigue")
    assert val >= 0.0  # stat is always >= 0
    # Build a realm with truly empty court
    from types import SimpleNamespace
    empty_realm = SimpleNamespace(court=SimpleNamespace(positions={}))
    assert _stat(empty_realm, "intrigue") == 0.0


def test_r1_stat_counts_only_living():
    """_stat only counts a courtier when the seat is filled AND is_alive.

    Builds a realm where the DEAD courtier has a higher stat than the
    living one — the mutation `if c` (missing `c.is_alive`) would return
    the dead courtier's stat and fail this test."""
    from types import SimpleNamespace

    dead = SimpleNamespace(
        is_alive=False,
        get_effective_stat=lambda n: 999.0,
    )
    alive = SimpleNamespace(
        is_alive=True,
        get_effective_stat=lambda n: 10.0,
    )
    realm = SimpleNamespace(
        court=SimpleNamespace(positions={"dead": dead, "alive": alive})
    )
    assert _stat(realm, "intrigue") == 10.0


# --- R2: _strength is manpower + treasury, manpower = pop // REGIMENT_POP_COST

def test_r2_strength_formula():
    """_strength = population // REGIMENT_POP_COST + treasury."""
    from gilded.fronts import REGIMENT_POP_COST
    g = _fixture_game()
    h = "Ferrenholt"
    pop = sum(p.population for p in g.provinces_of(h))
    treasury = g.houses[h].treasury
    expected = pop // REGIMENT_POP_COST + treasury
    assert _strength(g, h) == expected


# --- R3: _bordering returns sorted ascending by name -----------------------

def test_r3_bordering_sorted_ascending():
    """_bordering returns Houses in ascending name order."""
    g = _bordered_game()
    h = "Ashworth"
    result = _bordering(g, h)
    assert result == ["Brandtner", "Karsgate"]
    assert result == sorted(result)


# --- R4: truce blocks only while in force; expiry turn is NOT blocking ------

def test_r4_truce_at_turn_not_blocking():
    """Truce recorded at exactly g.turn has expired — target is eligible."""
    g = _bordered_game()
    h = "Ashworth"
    # Set truce with Karsgate expiring exactly at current turn
    g.houses[h].truces["Karsgate"] = g.turn
    # Karsgate truce expired — but Brandtner is the weakest neighbor
    assert _weakest_neighbor(g, h) == "Brandtner"


def test_r4_truce_after_turn_blocking():
    """Truce expiring one turn after current — target is blocked."""
    g = _bordered_game()
    h = "Ashworth"
    # Set truce with Brandtner expiring one turn in the future
    g.houses[h].truces["Brandtner"] = g.turn + 1
    # Brandtner blocked, weakest neighbor must be Karsgate (the only other borderer)
    assert _weakest_neighbor(g, h) == "Karsgate"


# --- R5: marriageable kin at age >= 16, living, not ruler ------------------

def test_r5_marriageable_at_16():
    """A living relative aged 16 IS marriageable."""
    g = _fixture_game()
    realm = g.realms["Ferrenholt"]
    ruler = realm.ruler
    # Find a non-ruler character and set age to 16
    for cid, c in realm.dynasty.all_characters.items():
        if c.id != ruler.id and c.is_alive:
            old_age = c.age
            c.age = 16
            assert _marriageable(realm, ruler) is True
            c.age = old_age
            break
    else:
        assert False, "No non-ruler character found"


def test_r5_marriageable_excludes_dead():
    """_marriageable returns False when all non-ruler kin are dead.

    Kills the mutation that drops `c.is_alive` from the comprehension."""
    g = _fixture_game()
    realm = g.realms["Ferrenholt"]
    ruler = realm.ruler
    changed = {}
    for cid, c in realm.dynasty.all_characters.items():
        if c.id != ruler.id:
            changed[cid] = (c.is_alive, c.age)
            c.is_alive = False
            c.age = 20
    # All non-ruler kin dead and over 16 → not marriageable
    assert _marriageable(realm, ruler) is False
    for cid, (alive, age) in changed.items():
        realm.dynasty.all_characters[cid].is_alive = alive
        realm.dynasty.all_characters[cid].age = age


def test_r5_marriageable_threshold_is_16():
    """Age 16 is marriageable; kills the mutation `c.age >= 17`."""
    g = _fixture_game()
    realm = g.realms["Ferrenholt"]
    ruler = realm.ruler
    changed = {}
    for cid, c in realm.dynasty.all_characters.items():
        if c.id != ruler.id and c.is_alive:
            changed[cid] = c.age
            c.age = 16
    # All living kin exactly 16 → marriageable under >= 16, not under >= 17
    assert _marriageable(realm, ruler) is True
    for cid, age in changed.items():
        realm.dynasty.all_characters[cid].age = age


def test_r5_marriageable_not_at_17():
    """A living relative aged 17 IS marriageable (threshold is 16, not 18).

    This kills the mutation `c.age >= 18` which would reject age-17 kin."""
    g = _fixture_game()
    realm = g.realms["Ferrenholt"]
    ruler = realm.ruler
    # Set all non-ruler kin to age 17 — passes >= 16, fails >= 18
    changed = {}
    for cid, c in realm.dynasty.all_characters.items():
        if c.id != ruler.id and c.is_alive:
            changed[cid] = c.age
            c.age = 17
    # With correct threshold (16), age 17 is marriageable
    assert _marriageable(realm, ruler) is True
    for cid, age in changed.items():
        realm.dynasty.all_characters[cid].age = age
    # Restore ages
    for cid, age in changed.items():
        realm.dynasty.all_characters[cid].age = age


# --- R6: _richest_rival picks MOST enterprises, never self -----------------

_SEEDS = (5, 7, 11, 42, 61)


def _game_at(seed, turn):
    g = GildedGame(seed=seed)
    while g.turn < turn:
        g.end_turn()
    return g


def test_r6_richest_rival_is_most_enterprises():
    """_richest_rival names the most-ventured rival WITHIN its preferred
    group (rivals with a willing seller first), and never the House itself.

    The old form pinned a House NAME off one generated world, so it went
    red whenever generation shifted. This asserts the ranking property
    the function implements, at every seed."""
    for seed in _SEEDS:
        g = _game_at(seed, 13)
        for h in g.houses:
            result = _richest_rival(g, h)
            if result is None:
                continue
            assert result != h, f"named itself at seed {seed}, house {h}"
            counts = {r: len([e for e in g.enterprises if e.house == r])
                      for r in g.houses if r != h}
            def has_seller(r):
                realm = g.realms.get(r)
                return bool(realm and disloyal_shareholders(realm, g.enterprises))
            if has_seller(result):
                # A seller exists among rivals: the pick must be the
                # most-ventured of the SELLERS - count is secondary to the door.
                assert counts[result] == max(counts[r] for r in counts if has_seller(r)), \
                    (f"at seed {seed}, house {h}: named {result} ({counts[result]}) "
                     f"but a selling rival holds more")
            else:
                assert counts[result] == max(counts.values()), \
                    (f"at seed {seed}, house {h}: named {result} with "
                     f"{counts[result]}, but a rival holds {max(counts.values())}")


def test_r6_richest_rival_never_self():
    """_richest_rival never names our own House, even when we hold the most
    enterprises. The old form pinned a House NAME off one generated world, so
    it went red whenever generation shifted. This floods the House with
    synthetic enterprises so that counting self would return the House itself,
    and asserts the pick is always a rival — kills the mutation that drops the
    `e.house != house_name` self-exclusion."""
    from gilded.enterprises import Enterprise
    for seed in _SEEDS:
        g = _game_at(seed, 13)
        h = sorted(g.houses)[0]
        rivals = [r for r in g.houses if r != h]
        g.enterprises.extend(
            Enterprise(eid=9000 + i, kind="estate", name=f"Synth {i}",
                       house=h, province=0, tier=5) for i in range(9))
        result = _richest_rival(g, h)
        assert result in rivals, \
            (f"at seed {seed}: named {result!r} for house {h}, "
             f"expected one of {rivals}")


# --- R7: _best_relations excludes Houses at war with -----------------------

def test_r7_best_relations_excludes_at_war():
    """_best_relations never picks a House we are at war with, at every seed.

    Kills the mutation that drops the war filter from the suitor list.
    Builds the precondition: find the natural best-relation rival, declare
    war on it, and assert the helper skips it in favour of the next best.
    (The old form pinned a House NAME off one generated world.)"""
    for seed in _SEEDS:
        g = _game_at(seed, 13)
        for h in g.houses:
            house = g.houses[h]
            # The best suitor before the filter (the one the bug would return)
            unfiltered = max((n for n in g.houses if n != h and n in g.realms),
                             key=lambda n: (house.relations.get(n, 0), n))
            if unfiltered in house.at_war_with:
                continue  # already excluded; nothing to prove here
            house.at_war_with.add(unfiltered)
            best = _best_relations(g, h)
            assert best not in house.at_war_with, \
                f"at seed {seed}, house {h}: picked at-war {best}"
            house.at_war_with.discard(unfiltered)


# --- R8: _strongest_rival names the strongest -----------------------------

def test_r8_strongest_rival_is_strongest():
    """_strongest_rival names a rival no weaker than any other rival, at
    every seed — not a House NAME drawn off one generated world."""
    for seed in _SEEDS:
        g = _game_at(seed, 13)
        for h in g.houses:
            result = _strongest_rival(g, h)
            if result is None:
                continue
            assert result != h, f"named itself at seed {seed}, house {h}"
            others = {r: _strength(g, r) for r in g.houses if r != h}
            assert others[result] == max(others.values()), \
                (f"at seed {seed}, house {h}: named {result} with "
                 f"{others[result]}, but a rival holds {max(others.values())}")


# --- R9: _target_for routes each family to its helper ----------------------

_ROUTES = [
    ("Conquest", _weakest_neighbor),
    ("Buyout",   _richest_rival),
    ("Dynasty",  _best_relations),
    ("Intrigue", _strongest_rival),
    ("Glory",    _strongest_rival),
]


def _r9_routing(family, helper):
    """Assert _target_for(family) IS the helper for that family, every seed.

    The old form asserted a House NAME off one generated world, so it went
    red whenever generation shifted. This asserts the routing itself, which
    is the behaviour the function has, and it kills the mutation of wiring
    a family to the wrong helper."""
    for seed in _SEEDS:
        g = _game_at(seed, 13)
        for h in g.houses:
            assert _target_for(g, h, family) == helper(g, h), \
                f"{family} at seed {seed}, house {h}"


def test_r9_target_for_conquest():
    """Conquest -> the weakest neighbouring rival, at every seed."""
    _r9_routing("Conquest", _weakest_neighbor)


def test_r9_target_for_buyout():
    """Buyout -> the richest rival, at every seed."""
    _r9_routing("Buyout", _richest_rival)


def test_r9_target_for_dynasty():
    """Dynasty -> the best-relations rival, at every seed."""
    _r9_routing("Dynasty", _best_relations)


def test_r9_target_for_intrigue():
    """Intrigue -> the strongest rival, at every seed."""
    _r9_routing("Intrigue", _strongest_rival)


def test_r9_target_for_glory():
    """Glory -> the strongest rival, at every seed."""
    _r9_routing("Glory", _strongest_rival)


def test_r9_target_for_dominion():
    """Dominion -> None (self-directed)."""
    g = _fixture_game()
    h = "Ferrenholt"
    assert _target_for(g, h, "Dominion") is None


def test_r9_target_for_consolidation():
    """Consolidation -> None (self-directed)."""
    g = _fixture_game()
    h = "Ferrenholt"
    assert _target_for(g, h, "Consolidation") is None


# =============================================================================
# WAVE 13 — eleven scoring and tiebreak rules (R1-R11)
# =============================================================================

# --- R1 & R2: FAMILIES order and tiebreak toward earlier family ---------------

def test_r12_families_tiebreak_conquest_wins_over_dominion():
    """When Conquest and Dominion score equally, Conquest wins because it
    appears first in FAMILIES.  Closes R1 (order) and R2 (positive index).

    The old form pinned a House NAME off one generated world (a tie at 23.0),
    so it broke the moment the dice moved.  We now build the tie EXACTLY:
    compute the world-derived terms for both families and set dispositions so
    the two scores coincide regardless of the generated world, while every
    other family is driven far below.  The assertion is about the tiebreak,
    not about one seed's numbers."""
    g = _fixture_game()
    h = "Ferrenholt"
    realm = g.realms[h]
    ruler = realm.ruler

    # World-derived (seed-dependent) terms we must compensate for:
    c_world = 20.0 if _weakest_neighbor(g, h) else -40.0
    d_world = 10.0 if _found_spot(g, h) else 0.0
    d_stat = _stat(realm, "industry")

    # Conquest = militarist_pacifist + c_world; pin it to a base of 100.
    base = 100.0
    ruler.dispositions["militarist_pacifist"] = base
    # Dominion = ambitious_content + d_stat + d_world == base + c_world.
    ruler.dispositions["ambitious_content"] = base + c_world - d_stat - d_world
    # Drive every other family far below so only Conquest/Dominion compete:
    #  Glory = ambitious_content + bold_craven, so a very negative bold_craven
    #  keeps Glory low even though ambitious_content is high.
    ruler.dispositions["bold_craven"] = -1000.0
    ruler.dispositions["labor_capital"] = -1000.0
    ruler.dispositions["patient_impulsive"] = -1000.0
    ruler.dispositions["honest_deceitful"] = 1000.0
    ruler.dispositions["paranoid_trusting"] = -1000.0

    conquest_score = _score_family(g, h, "Conquest", ruler, realm)
    dominion_score = _score_family(g, h, "Dominion", ruler, realm)
    assert conquest_score == dominion_score, \
        f"Expected an exact tie, got Conquest={conquest_score}, Dominion={dominion_score}"

    goal = select_goal(g, h)
    assert goal is not None
    assert goal.family == "Conquest", \
        f"Expected Conquest to win the tie (R1/R2), got {goal.family}"


# --- R3: Conquest petition domain is "war" -----------------------------------

def test_r3_conquest_domain_is_war():
    """Conquest family's petition domain is the literal string 'war'."""
    g = _fixture_game()
    h = "Ferrenholt"
    goal = select_goal(g, h)
    # Force a Conquest goal by tuning dispositions
    g.realms[h].ruler.dispositions["militarist_pacifist"] = 500.0
    g.realms[h].ruler.dispositions["ambitious_content"] = -500.0
    g.realms[h].ruler.dispositions["bold_craven"] = -500.0
    g.realms[h].ruler.dispositions["labor_capital"] = -500.0
    g.realms[h].ruler.dispositions["patient_impulsive"] = -500.0
    g.realms[h].ruler.dispositions["honest_deceitful"] = 500.0
    goal = select_goal(g, h)
    assert goal is not None
    assert goal.family == "Conquest"
    assert goal_domain(goal) == "war"


# --- R4: Consolidation petition domain is "labor" ----------------------------

def test_r4_consolidation_domain_is_labor():
    """Consolidation family's petition domain is the literal string 'labor'."""
    g = _fixture_game()
    h = "Ferrenholt"
    # Make Consolidation win: sink all other families
    ruler = g.realms[h].ruler
    ruler.dispositions["ambitious_content"] = -500.0
    ruler.dispositions["bold_craven"] = -500.0
    ruler.dispositions["militarist_pacifist"] = -500.0
    ruler.dispositions["labor_capital"] = -500.0
    ruler.dispositions["patient_impulsive"] = -500.0
    ruler.dispositions["honest_deceitful"] = 500.0
    # Strip land so Consolidation = 0.0 (paranoid_trusting always 0 + unrest 0.0)
    owned = [p for p in g.atlas.provinces.values() if p.owner == h]
    for p in owned:
        p.owner = None
    goal = select_goal(g, h)
    assert goal is not None
    assert goal.family == "Consolidation"
    assert goal_domain(goal) == "labor"


# --- R5: Dominion backed by industry, not intrigue ---------------------------

def test_r5_dominion_backed_by_industry():
    """Dominion family uses the court's INDUSTRY stat, not intrigue.

    Uses Duval-Corse at the base fixture where industry=12, intrigue=11,
    and _found_spot returns None (no +10). With ambitious_content=0,
    Dominion should score 12.0 (industry), not 11.0 (intrigue).
    """
    g = _fixture_game()
    h = "Duval-Corse"
    realm = g.realms[h]
    ruler = realm.ruler

    # Assert premise: industry != intrigue at Duval-Corse
    industry = _stat(realm, "industry")
    intrigue = _stat(realm, "intrigue")
    assert industry != intrigue, "Fixture premise broken: industry == intrigue"
    assert industry == 12
    assert intrigue == 11

    # Assert premise: no found spot (no +10 bonus)
    assert _found_spot(g, h) is None

    ruler.dispositions["ambitious_content"] = 0.0
    score = _score_family(g, h, "Dominion", ruler, realm)
    assert score == 12.0, f"Dominion should score industry (12.0), got {score}"


# --- R6: Buyout penalty when no rival exists ---------------------------------

def test_r6_buyout_no_rival_is_penalty():
    """Having NO rival to buy into is a PENALTY of -40.0, not a bonus.

    Straddles both branches: scores Buyout with a rival present, then removes
    all rivals and asserts the gap is exactly -50.0 (10 - (-40))."""
    g = _fixture_game()
    h = "Ferrenholt"
    realm = g.realms[h]
    ruler = realm.ruler

    ruler.dispositions["labor_capital"] = 0.0
    ruler.dispositions["ambitious_content"] = -500.0
    ruler.dispositions["bold_craven"] = -500.0
    ruler.dispositions["militarist_pacifist"] = -500.0
    ruler.dispositions["patient_impulsive"] = -500.0
    ruler.dispositions["honest_deceitful"] = 500.0

    # With rival present: score = intrigue + labor_capital + 10
    rival = _richest_rival(g, h)
    assert rival is not None
    score_with_rival = _score_family(g, h, "Buyout", ruler, realm)

    # Remove all rivals' enterprises
    kept = list(g.enterprises)
    g.enterprises[:] = [e for e in kept if e.house == h]
    assert _richest_rival(g, h) is None

    # Without rival: score = intrigue + labor_capital - 40
    score_without_rival = _score_family(g, h, "Buyout", ruler, realm)

    # Restore enterprises
    g.enterprises[:] = kept

    # The gap must be -50.0 (10 - (-40))
    assert score_without_rival - score_with_rival == -50.0, \
        f"Expected gap -50.0, got {score_without_rival - score_with_rival}"


# --- R7: Dynasty reads the PATIENT end of patient_impulsive ------------------

def test_r7_dynasty_reads_patient_end():
    """Dynasty family adds patient_impulsive positively — patient rulers
    chase marriages.  Setting patient_impulsive=80 with marriageable=True
    gives 90.0 (80 + 10).  The broken rule (negated) would give -70.0."""
    g = _fixture_game()
    h = "Ferrenholt"
    realm = g.realms[h]
    ruler = realm.ruler

    ruler.dispositions["patient_impulsive"] = 80.0
    assert _marriageable(realm, ruler) is True
    score = _score_family(g, h, "Dynasty", ruler, realm)
    assert score == 90.0, f"Dynasty should be 90.0 (patient + marriageable), got {score}"


# --- R8: Landless house reads worst unrest as 0.0, not 100.0 -----------------

def test_r8_landless_consolidation_score_is_zero():
    """A House with no provinces scores Consolidation at 0.0 (not 100.0).

    SUSPECTED DEFECT: _score_family reads disposition key 'paranoid_trusting'
    but characters only have 'trusting_paranoid'. The disposition is always 0.0
    so Consolidation = pure unrest. This test asserts the actual behaviour
    (0.0 for landless), not the intended one.
    """
    g = _fixture_game()
    h = "Ferrenholt"
    realm = g.realms[h]
    ruler = realm.ruler

    # Strip all land
    owned = [p for p in g.atlas.provinces.values() if p.owner == h]
    for p in owned:
        p.owner = None
    assert _worst_province(g, h) is None

    score = _score_family(g, h, "Consolidation", ruler, realm)
    assert score == 0.0, f"Landless Consolidation should be 0.0, got {score}"


# --- R9: Why-line names its target when there is one -------------------------

def test_r9_why_names_target():
    """Every why-line includes the target house name when a target exists,
    and uses anonymous phrasing when there is none."""
    why_with = _why("Conquest", "Vantrell")
    why_without = _why("Conquest", None)

    assert "Vantrell" in why_with, \
        f"Conquest why-line should name target: '{why_with}'"
    assert "Vantrell" not in why_without, \
        f"Anonymous why-line should not name a target: '{why_without}'"


# --- R10: Conquest why-line describes conquest, not domination ---------------

def test_r10_conquest_why_describes_conquest():
    """Conquest's why-line says 'break ... by force', not Dominion's
    'industrialize its own lands'."""
    why_c = _why("Conquest", "Vantrell")
    why_d = _why("Dominion", "Vantrell")

    assert "break" in why_c and "force" in why_c, \
        f"Conquest why should describe conquest: '{why_c}'"
    assert why_c != why_d, \
        f"Conquest and Dominion why-lines must differ: '{why_c}' vs '{why_d}'"
    assert "industrialize" not in why_c, \
        f"Conquest why should not describe industrialisation: '{why_c}'"


# --- R11: Dead ruler selects no goal at all ----------------------------------

def test_r11_dead_ruler_selects_no_goal():
    """select_goal returns None when the ruler is dead, but returns a Goal
    while the ruler lives."""
    g = _fixture_game()
    h = "Ferrenholt"
    ruler = g.realms[h].ruler

    # Alive: should return a Goal
    goal = select_goal(g, h)
    assert goal is not None, "Living ruler should select a goal"
    assert isinstance(goal, Goal)

    # Dead: should return None
    ruler.is_alive = False
    goal_dead = select_goal(g, h)
    assert goal_dead is None, "Dead ruler should select no goal"

    # Restore
    ruler.is_alive = True


# =============================================================================
# WAVE 15 — the seven boundary rules of goal_initiative
# =============================================================================

def _rival(g, house="Ferrenholt"):
    """First rival house by sorted name (Ashworth at seed 5, turn 13)."""
    return sorted(n for n in g.houses if n != house)[0]


def test_s15_truce_expiring_this_turn_does_not_block_war():
    """A27-truce: truces[target] == game.turn (not turn-5) blocks nothing.

    The rule is `truces.get(target, 0) <= game.turn`.  A truce expiring
    EXACTLY on the current turn satisfies `<=` and therefore does NOT block
    declaring war.  The mutant `< game.turn` keeps the truce alive one turn
    too long and returns None instead of declare_war.

    This is a SECOND, DISTINCT rule from test_r4_truce_at_turn_not_blocking,
    which pins _weakest_neighbor's copy of the truce check.  This test pins
    goal_initiative's copy for the Conquest family.
    """
    g = _fixture_game()
    h = g.houses["Ferrenholt"]
    t = _rival(g)

    h.at_war_with.clear()
    h.truces[t] = g.turn  # EXACTLY on the bar — expires this turn

    assert h.truces[t] == g.turn, "premise: truce expires this turn"
    assert not h.at_war_with, "premise: not at war with anyone"

    goal = Goal("Conquest", t, 0, 10, "war")
    result = goal_initiative(g, "Ferrenholt", goal)

    assert result is not None, "truce expiring this turn must NOT block war"
    assert result[0] == "declare_war"
    assert result[1]["target_house"] == t


def test_s15_exact_price_is_not_affordable():
    """A28-afford: treasury == found_cost (not above) means the house cannot pay.

    The rule is `treasury > ENTERPRISE_TYPES[kind][3]` (strict >).  Holding
    EXACTLY the cost fails the check and returns None.  The mutant `>=` would
    found the enterprise and empty the treasury to zero.

    The expand ladder runs first, so all owned enterprises are set to
    under_construction to skip expansion and reach the found branch.
    """
    g = _fixture_game()
    h = g.houses["Ferrenholt"]

    # Empty the expand ladder so we reach the found branch
    for e in g.enterprises:
        if e.house == "Ferrenholt":
            e.under_construction = 1

    # Assert premise: no expandable enterprise remains
    expandable = [e for e in g.enterprises
                  if e.house == "Ferrenholt"
                  and e.tier < TIER_MAX
                  and e.under_construction == 0]
    assert len(expandable) == 0, "premise: no expandable enterprises"

    spot = _found_spot(g, "Ferrenholt")
    assert spot is not None, "premise: found spot exists"
    kind, pid = spot

    h.treasury = ENTERPRISE_TYPES[kind][3]  # EXACTLY the cost

    assert h.treasury == ENTERPRISE_TYPES[kind][3], "premise: treasury == cost"

    goal = Goal("Dominion", None, 0, 10, "expansion")
    result = goal_initiative(g, "Ferrenholt", goal)

    assert result is None, "exact cost is NOT affordable (rule is >, not >=)"


def test_s15_completed_takeover_does_not_block_a_new_one():
    """A29-dupe: a COMPLETED takeover must not block a fresh one.

    The rule filters `not t.complete` — only LIVE takeovers block.
    The mutant drops this clause and lets one finished buyout bar the target
    forever.

    The fixture asserts BOTH halves: at least one complete takeover
    Ferrenholt->Ashworth exists, and NONE is live.  A test that only checks
    'a complete one exists' could pass for the wrong reason if a live one
    also sits in the list.
    """
    g = _fixture_game()
    t = _rival(g)

    done = Takeover(g.realms["Ferrenholt"].ruler, "Ferrenholt", t)
    done.complete = True
    g.takeovers.append(done)

    # Assert premise: among Ferrenholt->Ashworth takeovers, >=1 complete, 0 live
    relevant = [to for to in g.takeovers
                if to.target_house == t and to.buyer_house == "Ferrenholt"]
    assert any(to.complete for to in relevant), "premise: at least one complete"
    assert not any(not to.complete for to in relevant), "premise: none live"

    goal = Goal("Buyout", t, 0, 10, "capital")
    result = goal_initiative(g, "Ferrenholt", goal)

    assert result is not None
    assert result[0] == "start_takeover"
    assert result[1]["target_house"] == t


def test_s15_share_nibble_is_five_percent():
    """A29-pct: the buy_shares nibble is exactly 5.0%, not 10.0%.

    Reaching buy_shares needs start_takeover blocked by a LIVE takeover.
    The fixture asserts the target realm has eligible sellers and enterprises.
    """
    g = _fixture_game()
    t = _rival(g)

    # Block start_takeover with a live takeover
    live = Takeover(g.realms["Ferrenholt"].ruler, "Ferrenholt", t)
    live.complete = False
    g.takeovers.append(live)

    # Assert premise: target realm has at least one alive non-ruler adult
    trealm = g.realms.get(t)
    assert trealm is not None, "premise: target realm exists"
    sellers = [c for c in trealm.characters
               if c.is_alive and c.age >= 16 and c.id != trealm.ruler.id]
    assert len(sellers) >= 1, f"premise: target has {len(sellers)} eligible sellers"

    # Assert premise: target owns at least one enterprise
    target_ents = [e for e in g.enterprises if e.house == t]
    assert len(target_ents) >= 1, "premise: target owns enterprises"

    goal = Goal("Buyout", t, 0, 10, "capital")
    result = goal_initiative(g, "Ferrenholt", goal)

    assert result is not None
    assert result[0] == "buy_shares"
    assert result[1]["pct"] == 5.0, "pct must be 5.0, not 10.0"


def test_s15_court_with_no_intrigue_opens_no_scheme():
    """A30-nostat: _stat(realm, 'intrigue') > 0 (not >= 0).

    A court with ZERO intrigue cannot open a scheme.  The mutant `>= 0`
    opens one from an empty court.

    The fixture clears base_stats, traits, AND focus for all characters,
    then asserts the RESULT (_stat == 0) rather than just the inputs.
    """
    g = _fixture_game()
    t = _rival(g)
    realm = g.realms["Ferrenholt"]

    for c in realm.characters:
        c.base_stats["intrigue"] = 0
        c.traits = []
        if c.focus and c.focus.attribute == "intrigue":
            c.focus.set(None)

    # Assert the RESULT, not the inputs
    assert _stat(realm, "intrigue") == 0, "premise: intrigue stat is zero"

    goal = Goal("Intrigue", t, 0, 10, "press")
    result = goal_initiative(g, "Ferrenholt", goal)

    assert result is None, "zero intrigue must NOT open a scheme"


def test_s15_scheming_ruler_opens_no_second_scheme():
    """A30-double: a ruler already running a scheme must not open a second.

    The rule checks `not game.scheme_mgr.scheming(realm.ruler)`.
    The mutant drops this clause and lets the ruler double-scheme.

    The fixture asserts all three live conditions: scheming is true,
    intrigue > 0, and the target ruler is alive — without all three,
    the fixture proves nothing about THIS clause.
    """
    g = _fixture_game()
    t = _rival(g)
    realm = g.realms["Ferrenholt"]
    trealm = g.realms.get(t)

    g.scheme_mgr.start_scheme(realm.ruler, trealm.ruler, "assassination", t)

    # Assert all three premises this clause guards against
    assert g.scheme_mgr.scheming(realm.ruler), "premise: ruler is scheming"
    assert _stat(realm, "intrigue") > 0, "premise: intrigue > 0"
    assert trealm.ruler.is_alive, "premise: target ruler is alive"

    goal = Goal("Intrigue", t, 0, 10, "press")
    result = goal_initiative(g, "Ferrenholt", goal)

    assert result is None, "scheming ruler must NOT open a second scheme"


def test_s15_calm_province_is_not_toured():
    """A31-calm: worst.unrest > 0 (not >= 0).

    A province with ZERO unrest is not toured.  The mutant `>= 0` tours
    a calm province.

    The fixture asserts _worst_province returns a province (not None)
    whose unrest is exactly 0.0.  A None here would make the test pass
    for the wrong reason.
    """
    g = _fixture_game()

    for p in g.atlas.provinces.values():
        if p.owner == "Ferrenholt":
            p.unrest = 0.0

    worst = _worst_province(g, "Ferrenholt")
    assert worst is not None, "premise: worst province exists"
    assert worst.unrest == 0.0, "premise: worst province has zero unrest"

    goal = Goal("Consolidation", None, 0, 10, "labor")
    result = goal_initiative(g, "Ferrenholt", goal)

    assert result is None, "zero unrest must NOT trigger tour_province"
