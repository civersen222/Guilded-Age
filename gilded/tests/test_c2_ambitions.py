"""Mission C2 - the player has a stake.

Covers gilded/ambitions.py and gilded/ui/house.py: the set_ambition
facade, the status clock, the court's private wants (stance derived
from dispositions, deterministic across boots), and the House-screen
read-models (banner + court_cards mirroring the model exactly).
"""
import os
import sys

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from gilded.ambitions import (
    FAMILY_DISPOSITION, STANCE_BACKS_AT, STANCE_OPPOSES_AT,
)
from gilded.chassis import GildedGame
from gilded.intel import report as intel_report
from gilded.ui.house import banner, court_cards


def _new(seed=7):
    g = GildedGame(seed=seed, player_house="Vantrell")
    player = next(h for h in g.houses if g.houses[h].is_player)
    return g, player


# --- the stake --------------------------------------------------------

def test_set_ambition_writes_the_goal_store():
    g, player = _new()
    beat = g.set_ambition(player, "Consolidation")
    assert beat is not None
    goal = g.agendas.get(player)
    assert goal.family == "Consolidation"
    assert goal.commit_turns == 10


def test_set_ambition_rejects_unknown_family():
    g, player = _new()
    with pytest.raises(ValueError):
        g.set_ambition(player, "NotAFamily")


def test_set_ambition_targeted_family_gets_target():
    g, player = _new()
    rivals = sorted(h for h in g.houses if h != player)
    g.set_ambition(player, "Buyout")
    assert g.agendas.get(player).target == rivals[0]


# --- the clock ---------------------------------------------------------

def test_status_clock_counts_down():
    g, player = _new()
    g.set_ambition(player, "Consolidation")
    st = g.ambitions.status(player)
    assert st["turns_left"] == 10 and st["fulfilled"] is None
    assert banner(g, player)["clock"] == "turn 1 of 10"
    for _ in range(3):
        g.end_turn()
    st = g.ambitions.status(player)
    assert st["turns_left"] == 7 and st["fulfilled"] is None
    assert banner(g, player)["clock"] == "turn 4 of 10"


def test_status_without_stake():
    g, player = _new()
    st = g.ambitions.status(player)
    assert st["family"] is None and st["turns_left"] == 0
    assert st["fulfilled"] is None and st["clock"] is None


# --- resolution --------------------------------------------------------

def test_resolution_evaluates_and_beat_carries_ambition():
    g, player = _new()
    g.set_ambition(player, "Consolidation")
    for _ in range(10):
        g.end_turn()
    st = g.ambitions.status(player)
    assert st["fulfilled"] in (True, False)
    assert st["turns_left"] == 0
    assert any("ambition" in (b.text or "").lower() for b in g.beats.log)


def test_fulfilled_ambition_pays_journal_label_ambition():
    g, player = _new(13)
    rivals = sorted(h for h in g.houses if h != player)
    g.set_ambition(player, "Buyout", rivals[0])
    for _ in range(10):
        g.end_turn()
    st = g.ambitions.status(player)
    if st["fulfilled"]:
        deltas = g.beats.deltas(g.resolved_turn)
        assert any("ambition" in c.label.lower()
                   for _lbl, att in deltas for c in att.causes)


# --- the court's wants -------------------------------------------------

def test_wants_derived_deterministic_and_stances():
    g, player = _new()
    g.set_ambition(player, "Glory")
    realm = g.realms[player]
    adults = [c for c in realm.characters if c.age >= 16]
    assert adults
    for c in adults:
        w = c.want
        assert w["text"] and w["disposition"] in c.dispositions
        assert w["stance"] in ("backs", "wary", "opposes")
        key, polarity = FAMILY_DISPOSITION["Glory"]
        assert w["disposition"] == key
        value = float(c.dispositions[key]) * polarity
        if value > STANCE_BACKS_AT:
            assert w["stance"] == "backs"
        elif value < STANCE_OPPOSES_AT:
            assert w["stance"] == "opposes"
        else:
            assert w["stance"] == "wary"
    # second boot of the same seed: byte-identical wants
    g2, player2 = _new()
    g2.set_ambition(player2, "Glory")
    w1 = sorted((c.name, c.want["text"], c.want["disposition"],
                 c.want["stance"]) for c in
                g.realms[player].characters if c.age >= 16)
    w2 = sorted((c.name, c.want["text"], c.want["disposition"],
                 c.want["stance"]) for c in
                g2.realms[player2].characters if c.age >= 16)
    assert w1 == w2


def test_stances_occur_across_the_grid():
    seen = set()
    for seed, family in ((7, "Consolidation"), (11, "Glory"),
                         (13, "Buyout")):
        g, player = _new(seed)
        g.set_ambition(player, family)
        for w in g.ambitions.wants(player):
            seen.add(w["stance"])
    assert {"backs", "wary", "opposes"} <= seen


def test_wants_without_stake_are_empty():
    g, player = _new()
    assert g.ambitions.wants(player) == []
    assert g.ambitions.cards(player) == []


# --- intel symmetry (fog reads the stake through UNCHANGED intel) -----

def test_intel_reads_the_players_stake():
    g, player = _new()
    rivals = sorted(h for h in g.houses if h != player)
    rival = rivals[0]
    g.set_ambition(player, "Glory")
    g.informants.add((rival, player))
    g.houses[rival].relations[player] = 5
    rep = intel_report(g, rival, player)
    assert rep.tier >= 2
    assert "Pursuing Glory" in rep.apparent_intent


# --- the House screen ----------------------------------------------------

def test_banner_fields():
    g, player = _new()
    b = banner(g, player)
    assert b["family"] is None and b["clock"] is None
    g.set_ambition(player, "Dynasty")
    b = banner(g, player)
    assert b["family"] == "Dynasty"
    assert b["clock"] == "turn 1 of 10"
    assert b["turns_left"] == 10
    assert b["fulfilled"] is None


def test_court_cards_mirror_the_model():
    g, player = _new()
    g.set_ambition(player, "Glory")
    adults = [c for c in g.realms[player].characters if c.age >= 16]
    cards = court_cards(g, player)
    assert {c["cid"] for c in cards} == {c.id for c in adults}
    by_id = {c.id: c for c in adults}
    for card in cards:
        ch = by_id[card["cid"]]
        assert card["traits"] == ch.traits
        assert card["stance"] == ch.want["stance"]
        assert card["want_text"] == ch.want["text"]


def test_cards_are_adults_only():
    g, player = _new()
    g.set_ambition(player, "Glory")
    cards = court_cards(g, player)
    assert all(c["age"] >= 16 for c in cards)
