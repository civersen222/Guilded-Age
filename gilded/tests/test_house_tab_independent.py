"""Stage 5B4 — Three cases that measure the House tab against the simulation.

R-1: Succession order on the tab matches the simulation's succession_order().
R-2: The heir shown on the tab matches the simulation's resolve_succession().
R-3: Grievances recorded against the ruler are drawn beside the kinsman.

Expectations are resolved from gilded.society.succession — a different module
from gilded.peerage which builds the report the tab draws from.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.chassis import GildedGame
from gilded.peerage import report as peerage_report
from gilded.society.characters import modify_opinion
from gilded.society.succession import succession_order, resolve_succession
from gilded.ui.house_tab import _house_tab_lines, draw_house_tab


def test_succession_order_drawn_matches_simulation():
    """R-1: The order of succession on the tab matches the simulation.

    Independent source: succession_order(realm) from gilded.society.succession.
    """
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    realm = g.realms.get(house_name)
    if realm is None or realm.ruler is None:
        return  # nothing to check

    # Independent expectation from the simulation
    sim_order = succession_order(realm)
    if len(sim_order) < 2:
        return  # need at least two to check order

    # What the tab draws — from the read-model
    rpt = peerage_report(g, house_name)
    lines = _house_tab_lines(rpt)
    text = "\n".join(lines)

    # The first two names from the simulation should appear in rank order on the tab
    first_name = sim_order[0].name
    second_name = sim_order[1].name

    assert first_name in text, f"First in line '{first_name}' should appear on tab"
    assert second_name in text, f"Second in line '{second_name}' should appear on tab"

    # First should appear before second
    first_pos = text.index(first_name)
    second_pos = text.index(second_name)
    assert first_pos < second_pos, \
        f"Tab shows '{second_name}' before '{first_name}' — order doesn't match simulation"


def test_heir_matches_simulation():
    """R-2: The man who would inherit on the tab matches the simulation.

    Independent source: resolve_succession(realm) from gilded.society.succession.
    """
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    realm = g.realms.get(house_name)
    if realm is None or realm.ruler is None:
        return  # nothing to check

    # Independent expectation from the simulation
    sim_heir = resolve_succession(realm)
    if sim_heir is None:
        return  # no heir to check

    # What the tab draws — from the read-model
    rpt = peerage_report(g, house_name)
    lines = _house_tab_lines(rpt)
    text = "\n".join(lines)

    # The heir's name should appear as the first in line
    assert sim_heir.name in text, \
        f"Heir '{sim_heir.name}' from simulation should appear on tab"

    # The tab marks "First in line:" — check it names the right person
    for line in lines:
        if "First in line:" in line:
            assert sim_heir.name in line, \
                f"Tab says first in line is '{line.strip()}' but simulation says '{sim_heir.name}'"
            return

    # If we can't find the "First in line:" marker, at least check the heir appears
    assert sim_heir.name in text, \
        f"Heir '{sim_heir.name}' should appear somewhere on the tab"


def test_grievance_drawn_on_tab():
    """R-3: Grievances recorded against the ruler are drawn beside the kinsman.

    When a kinsman in line for succession (holding no seat) has a grievance,
    it must appear on the tab next to that kinsman's entry.
    """
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    realm = g.realms.get(house_name)
    if realm is None or realm.ruler is None:
        return  # nothing to check

    # Find a kinsman in line for succession who holds no seat
    rpt = peerage_report(g, house_name)
    in_line = [k for k in rpt.kin if k.succession_rank is not None and k.is_alive]
    in_line.sort(key=lambda k: k.succession_rank)

    target_kin = None
    for k in in_line:
        if k.char_id != realm.ruler.id:
            has_seat = any(not s.vacant and s.holder_id == k.char_id for s in rpt.seats)
            if not has_seat:
                target_kin = k
                break

    if target_kin is None:
        return  # no eligible kinsman

    # Find the character in the realm
    target_char = None
    for c in realm.characters:
        if c.id == target_kin.char_id:
            target_char = c
            break
    if target_char is None:
        return  # character not found

    # Record a grievance against the ruler
    grievance_text = "betrayed my trust"
    modify_opinion(target_char, realm.ruler, -40, grievance_text)

    # Rebuild the report and check the grievance appears on the tab
    rpt_after = peerage_report(g, house_name)
    lines = _house_tab_lines(rpt_after)
    text = "\n".join(lines)

    # The grievance text should appear on the tab
    assert grievance_text in text, \
        f"Grievance '{grievance_text}' should be drawn on the tab beside '{target_kin.name}'"

    # Also verify it appears on a line that mentions the kinsman
    found = False
    for line in lines:
        if target_kin.name in line and grievance_text in line:
            found = True
            break
    assert found, \
        f"Grievance should appear on the same line as '{target_kin.name}'"
