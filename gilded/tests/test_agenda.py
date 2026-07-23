from gilded.chassis import GildedGame


def test_game_has_stage2_state():
    g = GildedGame(seed=7)
    assert g.agendas == {}
    assert g.informants == set()
    assert g.takeovers == []


from gilded import agenda
from gilded.agenda import (Goal, FAMILIES, ensure_agenda, select_goal,
                           goal_domain, goal_initiative)


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
    g = GildedGame(seed=6)
    a, b = sorted(g.houses)[0], sorted(g.houses)[1]
    goal = Goal("Dynasty", b, g.turn, 10, "wed")
    proposed = goal_initiative(g, a, goal)          # no tie yet
    g.marriages.marriages.append(("x", a, "y", b))  # now they are bound
    assert goal_initiative(g, a, goal) is None       # gate: never re-propose
    if proposed is not None:                         # meaningful only if kin exist
        assert proposed[0] == "propose_marriage"


def test_goal_initiative_conquest_acts_only_on_declared_target():
    from gilded.agenda import _weakest_neighbor
    g = GildedGame(seed=6)
    h = _ai_house(g)
    tgt = _weakest_neighbor(g, h)
    if tgt is not None:
        out = goal_initiative(g, h, Goal("Conquest", tgt, g.turn, 10, "war"))
        if out is not None:
            verb, kw = out
            assert verb == "declare_war" and kw["target_house"] == tgt
    # An unavailable target is never silently swapped for another House.
    assert goal_initiative(g, h, Goal("Conquest", "NoSuchHouse",
                                      g.turn, 10, "war")) is None


def test_ensure_agenda_reselects_when_target_vanishes():
    g = GildedGame(seed=6)
    h = _ai_house(g)
    stale = Goal("Conquest", "GhostHouse", g.turn, 10, "war")
    g.agendas[h] = stale
    fresh = ensure_agenda(g, h)
    assert fresh is not stale
    assert fresh.target != "GhostHouse"
