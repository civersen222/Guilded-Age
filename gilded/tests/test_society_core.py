"""Tests for the transplanted society core (mission G3)."""

import random

from gilded.society.characters import (
    ATTRIBUTES,
    COPING_VICES,
    Character,
    Dynasty,
    Secret,
    generate_child,
    normalize_stats,
)
from gilded.society.court import Court, CourtPosition
from gilded.society.dispositions import PAIRS, apply_drift, initial_dispositions
from gilded.society.event_engine import Situation, render


def _char(name="Elias Vantrell", age=40, gender="Male"):
    return Character(name=name, stats={}, traits=[], age=age, gender=gender)


def test_normalize_stats_covers_six_attributes():
    random.seed(3)
    norm = normalize_stats({"diplomacy": 12, "martial": 9})
    assert set(ATTRIBUTES) <= set(norm)
    assert norm["statecraft"] == 12 and norm["command"] == 9


def test_character_has_thirty_dispositions_and_persona():
    random.seed(4)
    c = _char()
    assert len(PAIRS) == 30
    assert len(c.dispositions) == 30
    assert c.persona == c.dispositions and c.persona is not c.dispositions
    assert c.secrets == [] and c.is_alive


def test_generate_child_links_parents():
    random.seed(5)
    a, b = _char("Elias"), _char("Mara", age=36, gender="Female")
    kid = generate_child("Corin", a, b)
    assert kid.age == 0
    assert set(ATTRIBUTES) <= set(kid.base_stats)
    assert kid.parent_ids == [a.id, b.id]
    assert kid.id in a.children_ids and kid.id in b.children_ids
    assert len(kid.dispositions) == 30


def test_court_has_six_gilded_seats():
    assert len(CourtPosition) == 6
    members = CourtPosition.__members__
    for seat in ("BOARD_CHAIRMAN", "CHIEF_ENGINEER", "HEAD_OF_SECURITY",
                 "MASTER_OF_PRESS", "FOREIGN_SECRETARY", "MARSHAL"):
        assert seat in members
    assert "CHIEF_STEWARD" not in members
    assert Court.POSITION_STATS[CourtPosition.MARSHAL] == "command"
    assert Court.POSITION_STATS[CourtPosition.BOARD_CHAIRMAN] == "industry"


def test_court_appoint_dismiss_bonus():
    random.seed(6)
    ruler, aide = _char("Ruler"), _char("Aide")
    court = Court(ruler)
    assert not court.appoint(CourtPosition.MARSHAL, ruler, turn=1)
    assert court.appoint(CourtPosition.MARSHAL, aide, turn=1)
    assert not court.appoint(CourtPosition.CHIEF_ENGINEER, aide, turn=1)
    assert court.get_bonus(CourtPosition.MARSHAL) == aide.get_effective_stat("command")
    assert court.filled_count == 1
    assert court.dismiss(CourtPosition.MARSHAL) is aide
    assert court.filled_count == 0


def test_mental_break_creates_vice_and_secret():
    random.seed(7)
    c = _char()
    msg = c.add_stress(250)
    assert msg is not None and "mental break" in msg
    assert any(v in c._explicit_traits for v in COPING_VICES)
    assert len(c.secrets) == 1 and isinstance(c.secrets[0], Secret)
    assert c.secrets[0].kind == "vice"


def test_render_known_and_unknown_kinds():
    random.seed(8)
    a, b = _char("Old King"), _char("New King")
    txt = render(Situation("succession", {"old": a, "new": b},
                           data={"civ": "Vantrell"}))
    assert isinstance(txt, str) and len(txt) > 0
    assert render(Situation("no_such_kind")) == "no_such_kind"


def test_apply_drift_moves_disposition():
    random.seed(9)
    c = _char()
    before = c.dispositions["labor_capital"]
    apply_drift(c, "labor_capital", 10, "test")
    assert c.dispositions["labor_capital"] != before


def test_dynasty_prestige_counts_living():
    random.seed(10)
    root = _char("Root")
    all_chars = {root.id: root}
    dyn = Dynasty(root, all_chars)
    kid = generate_child("Kid", root, _char("Consort", gender="Female"))
    dyn.add_member(kid, root.id)
    assert kid in dyn.get_all_members()
    assert dyn.calculate_dynastic_prestige() > 0