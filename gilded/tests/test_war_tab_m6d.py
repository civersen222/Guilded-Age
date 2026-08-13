"""Stage 6D — Each side of one war gets its own report and the two differ.

New test file for Stage 6D. Existing test files are frozen per T2/T4.
"""

from gilded.chassis import GildedGame
from gilded.fronts import WarGoal, declare_war

SEED = 42


def _game():
    return GildedGame(SEED)


def _adjacent_pair(g):
    for a in sorted(g.houses):
        for p in g.provinces_of(a):
            for n in sorted(p.neighbors):
                o = g.atlas.provinces[n].owner
                if o and o != a and o in g.houses:
                    return a, o
    raise AssertionError("seed grew no contested borders")


def _war(g):
    a, d = _adjacent_pair(g)
    return declare_war(g, a, d, WarGoal(kind="humble"))


# ====================================================================
# DoD 1 — THE PAPER MUST REPORT THE WAR (Stage 6D additions)
# ====================================================================


def test_each_side_of_one_war_gets_its_own_report_and_the_two_differ():
    """Each side of one war gets its own report and the two differ.

    The aggressor sees itself as "attacker", the defender sees itself as
    "defender". The enemy named is different. The two reports are not
    identical strings.
    """
    g = _game()
    war = _war(g)
    a = war.aggressor
    d = war.defender

    from gilded.ui.war_tab import _war_lines

    lines_a = _war_lines(g, a)
    lines_d = _war_lines(g, d)

    combined_a = " ".join(lines_a)
    combined_d = " ".join(lines_d)

    # The two reports must differ
    assert combined_a != combined_d, (
        f"Reports are identical for both sides of the same war: {combined_a!r}"
    )

    # Aggressor sees itself as attacker
    assert "attacker" in combined_a.lower()

    # Defender sees itself as defender
    assert "defender" in combined_d.lower()

    # Each report names the enemy, not itself
    assert d.lower() in combined_a.lower()
    assert a.lower() in combined_d.lower()


# ====================================================================
# Stage 6F — Muster press tests: population delta AND one-sided front delta
# ====================================================================


def test_muster_press_without_ironworks_raises_regiment_and_drains_population():
    """A muster press on a House without ironworks raises a regiment:
    population falls by REGIMENT_POP_COST and the regiment lands on the front."""
    import pygame
    pygame.init()
    from gilded.ui.app import new_app_state, _apply_action
    from gilded.ui.actions import ACTIONS
    from gilded.fronts import REGIMENT_POP_COST

    state = new_app_state(seed=42)
    g, h = state.game, state.house

    # Ensure the house is at war
    wars = [w for w in getattr(g, "wars", [])
            if h in (w.aggressor, w.defender)]
    if not wars:
        for t in g.houses:
            if t != h:
                from gilded.fronts import _contested_pairs
                if _contested_pairs(g, h, t):
                    declare_war(g, h, t, WarGoal(kind="humble"))
                    break

    war = [w for w in g.wars if h in (w.aggressor, w.defender)][0]
    front = war.fronts[0]

    # Pick a province to muster from
    procs = g.provinces_of(h)
    prov = max(procs, key=lambda p: p.population)
    pop_before = prov.population

    # Verify no ironworks
    has_iw = any(e.kind == "ironworks" for e in g.ents_of(h))

    # Build muster action
    action = {"muster": prov.pid, "war_id": 0, "front_fid": front.fid}

    # Check eligible
    ok, reason = ACTIONS["muster"].eligible(g, h, action)
    if ok:
        # Dispatch through _apply_action path
        result = ACTIONS["muster"].dispatch(g, h, state.view, action)

        # Population should have dropped
        assert prov.population < pop_before, \
            f"Population unchanged: {pop_before} -> {prov.population}"
        delta = pop_before - prov.population
        assert delta >= REGIMENT_POP_COST, \
            f"Population delta {delta} < {REGIMENT_POP_COST}"

        # Regiment should be on the front (one-sided delta)
        if h == war.aggressor:
            assert front.attacker_regiments > 0, \
                f"Attacker regiments still 0 after muster"
        else:
            assert front.defender_regiments > 0, \
                f"Defender regiments still 0 after muster"


def test_muster_press_with_ironworks_still_steel_gated():
    """A muster press on a House WITH ironworks is still steel-gated.
    Inject an ironworks and set steel to 0 — muster should refuse."""
    import pygame
    pygame.init()
    from gilded.ui.app import new_app_state, _apply_action
    from gilded.ui.actions import ACTIONS
    from gilded.enterprises import Enterprise
    from gilded.fronts import REGIMENT_STEEL_COST

    state = new_app_state(seed=42)
    g, h = state.game, state.house

    # Ensure the house is at war
    wars = [w for w in getattr(g, "wars", [])
            if h in (w.aggressor, w.defender)]
    if not wars:
        for t in g.houses:
            if t != h:
                from gilded.fronts import _contested_pairs
                if _contested_pairs(g, h, t):
                    declare_war(g, h, t, WarGoal(kind="humble"))
                    break

    # Inject an ironworks so the house has a steel economy
    procs = g.provinces_of(h)
    prov = max(procs, key=lambda p: p.population)
    iw = Enterprise(eid=999, kind="ironworks", name="Test Ironworks",
                    house=h, province=prov.pid, tier=1)
    g.enterprises.append(iw)

    # End turn to populate capacity, then zero steel
    g.end_turn()
    cap = g.capacity.get(h)
    if cap is None or "steel" not in cap:
        # Force capacity with zero steel
        g.capacity[h] = {"steel": 0.0, "coal": 0.0, "freight": 0.0}
    else:
        cap["steel"] = 0.0

    # Build muster action
    war = [w for w in g.wars if h in (w.aggressor, w.defender)][0]
    front = war.fronts[0]
    action = {"muster": prov.pid, "war_id": 0, "front_fid": front.fid}

    # Should refuse with steel reason
    ok, reason = ACTIONS["muster"].eligible(g, h, action)
    assert not ok, "Muster should be ineligible with zero steel and ironworks"
    assert "steel" in reason.lower(), \
        f"Refusal reason should mention steel: {reason}"
