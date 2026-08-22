"""S14B: standing pacts of alliance.

A founding board-seat marriage seals a scarce pact between two Houses (capped
at 8 standing and 2 per House). A pact binds: neither House may name the other
as a war target (both AI pickers gate on may_declare_war), and when one side is
attacked the defender's allies are called to arms and must join within a few
turns or record a refusal in the world log naming both it and the aggressor.
"""
from gilded import ai, agenda
from gilded.chassis import GildedGame
from gilded.fronts import War, WarGoal
from gilded.pacts import (CALL_TO_ARMS_DEADLINE, MAX_PACTS,
                          MAX_PACTS_PER_HOUSE, allies_of, are_allies,
                          call_to_arms, form_pact, may_declare_war,
                          pact_tick, standing_pacts)


def test_exports_and_empty_game():
    g = GildedGame(seed=7)
    assert standing_pacts(g) == []
    assert allies_of(g, "Brandtner") == set()
    # a House may declare war on a House it is not at war with or allied to
    assert may_declare_war(g, "Brandtner", "Karsgate")


def test_form_pact_and_invariants():
    g = GildedGame(seed=7)
    msg = form_pact(g, "Brandtner", "Ashworth")
    assert msg is not None and "pact" in msg
    assert len(standing_pacts(g)) == 1
    assert allies_of(g, "Brandtner") == {"Ashworth"}
    assert allies_of(g, "Ashworth") == {"Brandtner"}
    assert are_allies(g, "Brandtner", "Ashworth") is True
    # symmetric: neither may declare war on the other
    assert may_declare_war(g, "Brandtner", "Ashworth") is False
    assert may_declare_war(g, "Ashworth", "Brandtner") is False
    # a non-ally is still a legal target
    assert may_declare_war(g, "Brandtner", "Karsgate") is True
    # idempotent: re-forming the same pact is refused
    assert form_pact(g, "Brandtner", "Ashworth") is None
    assert form_pact(g, "Ashworth", "Brandtner") is None
    assert len(standing_pacts(g)) == 1
    # self-pact impossible, unknown House impossible
    assert form_pact(g, "Brandtner", "Brandtner") is None
    assert form_pact(g, "Brandtner", "Nobody") is None


def test_per_house_cap():
    g = GildedGame(seed=7)
    assert form_pact(g, "Brandtner", "Ashworth") is not None
    assert form_pact(g, "Brandtner", "Karsgate") is not None
    assert MAX_PACTS_PER_HOUSE == 2
    # Brandtner now holds two pacts; a third is refused
    assert form_pact(g, "Brandtner", "Ferrenholt") is None
    # a House with no pacts can still take two
    assert form_pact(g, "Ferrenholt", "Mordaine") is not None
    assert form_pact(g, "Ferrenholt", "Vantrell") is not None
    assert form_pact(g, "Ferrenholt", "Ashworth") is None


def test_global_cap(monkeypatch):
    from gilded import pacts as _p
    g = GildedGame(seed=7)
    assert MAX_PACTS == 8
    # lower the standing cap so the global ceiling binds first
    monkeypatch.setattr(_p, "MAX_PACTS", 3)
    assert _p.form_pact(g, "Brandtner", "Ashworth") is not None
    assert _p.form_pact(g, "Karsgate", "Ferrenholt") is not None
    assert _p.form_pact(g, "Mordaine", "Vantrell") is not None
    assert _p.form_pact(g, "Brandtner", "Karsgate") is None
    assert len(_p.standing_pacts(g)) == 3


def test_pact_blocks_both_pickers():
    g = GildedGame(seed=7)
    form_pact(g, "Brandtner", "Ashworth")
    # the AI picker must never name the ally (None or another target is fine)
    assert ai._weaker_neighbor(g, "Brandtner") not in allies_of(g, "Brandtner")
    # the Conquest picker must not name the ally
    goal = agenda.Goal(family="Conquest", target="Ashworth",
                       opened_turn=g.turn, commit_turns=0, why="test")
    assert agenda.goal_initiative(g, "Brandtner", goal) is None


def test_call_to_arms_answered_or_refused():
    """A war against an allied House pledges the defender's allies; each
    pledge is answered by a join within the deadline or by a refusal recorded
    in game.events naming both the ally and the aggressor."""
    g = GildedGame(seed=7)
    form_pact(g, "Brandtner", "Ashworth")
    # a constructed war: Karsgate (not an ally of Ashworth) attacks Ashworth
    war = War(aggressor="Karsgate", defender="Ashworth",
              goal=WarGoal(kind="humble"), fronts=[], war_score=0.0,
              started_turn=g.turn)
    g.wars.append(war)
    g.houses["Karsgate"].at_war_with.add("Ashworth")
    g.houses["Ashworth"].at_war_with.add("Karsgate")
    log = list(call_to_arms(g, war))
    g._emit(log, "gazette")
    assert any("House Brandtner" in m and "to arms" in m for m in log), log
    assert "Brandtner" in g.pact_pledges
    # drive the tick until Brandtner answers: join or refuse
    for _ in range(CALL_TO_ARMS_DEADLINE + 2):
        if "Brandtner" not in g.pact_pledges:
            break
        g.turn += 1
        g._emit(pact_tick(g), "gazette")
    # the pledge must have resolved and be logged
    joined = any("House Brandtner" in e.text and
                 "joins House Ashworth" in e.text for e in g.events)
    refused = any("House Brandtner refuses" in e.text for e in g.events)
    assert joined or refused, "pledge neither joined nor refused"
    if refused:
        # a refusal names both the ally and the aggressor
        assert any("House Brandtner refuses" in e.text and
                   "House Karsgate" in e.text for e in g.events)
    # the pact itself survives: the ally was not the one who broke it
    assert are_allies(g, "Brandtner", "Ashworth")
