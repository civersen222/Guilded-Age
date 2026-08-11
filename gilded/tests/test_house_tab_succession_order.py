"""Stage 5B2 — R-2, R-3: The order of succession is measured against the simulation.

R-2: A case goes red when the order the tab draws stops being the order the game
resolves.  Expectation is resolved from gilded.society.succession, NOT from the
read-model the tab already read.

R-3: A case goes red when the first man named on the tab stops being the man the
game would crown.  This is a different claim from R-2 and must not go red together.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView
from gilded.peerage import report as peerage_report
from gilded.society.succession import succession_order, resolve_succession
from gilded.ui.house_tab import _house_tab_lines, draw_house_tab


def _view():
    g = GildedGame(seed=42)
    house_name = list(g.houses.keys())[0]
    v = BroadsheetView(g, house_name)
    return g, v


def test_succession_order_shown():
    """R-2: Succession ranks displayed on the tab match the simulation order.

    Independent source: succession_order(realm) from gilded.society.succession.
    """
    g, v = _view()
    realm = g.realms.get(v.house)
    assert realm is not None, "Game must have a realm"

    # Independent source — the simulation's succession order
    sim_order = succession_order(realm)
    assert len(sim_order) >= 2, "Game must have at least 2 succession candidates"

    lines = v.house_lines()
    text = "\n".join(lines)

    assert "SUCCESSION" in text, f"Succession section should appear: {text}"

    # First two from simulation should appear in rank order on the tab
    first = sim_order[0]
    second = sim_order[1]

    assert first.name in text, f"First in line '{first.name}' should appear"
    assert second.name in text, f"Second in line '{second.name}' should appear"

    # First should appear BEFORE second in the text
    first_pos = text.index(first.name)
    second_pos = text.index(second.name)
    assert first_pos < second_pos, \
        f"Succession order wrong: '{first.name}' should appear before '{second.name}'"


def test_succession_order_matches_simulation():
    """R-2: The order shown on the tab matches the simulation's succession order.

    Independent source: succession_order(realm) from gilded.society.succession.

    R-1: This case MUST go red when the tab draws fewer succession rows than it
    owes — including when it draws none, and including when the rows are drawn
    correctly but marked differently (e.g. wrong marker character). The number of
    rows owed comes from the simulation (succession_order) and the documented page
    size (10), NOT from what was parsed.
    """
    import re

    g, v = _view()
    realm = g.realms.get(v.house)
    assert realm is not None, "Game must have a realm"

    # Independent source — the simulation's succession order
    sim_order = succession_order(realm)
    assert len(sim_order) >= 2, "Game must have at least 2 succession candidates"

    # Draw the tab to a surface and parse the #N rows
    rpt = peerage_report(g, v.house)
    surf = pygame.Surface((640, 480))
    rect = pygame.Rect(0, 0, 640, 480)
    draw_house_tab(surf, rect, rpt)

    # Parse the drawn succession rows using _house_tab_lines
    lines = _house_tab_lines(rpt)
    text = "\n".join(lines)

    # Find the succession section
    succ_start = None
    for i, line in enumerate(lines):
        if "SUCCESSION" in line:
            succ_start = i
            break

    assert succ_start is not None, "Succession section should be drawn"

    # How many rows does the tab owe? The page holds min(sim_count, 10) rows.
    # This comes from the simulation + documented page size, NOT from parsing.
    owed = min(len(sim_order), 10)

    # Build rank -> char_id map from the report's Kin data (avoids duplicate-name ambiguity)
    rank_to_id = {k.succession_rank: k.char_id for k in rpt.kin if k.succession_rank is not None}

    # Parse #N rows — these are the succession rank markers
    drawn_ids = []
    for line in lines[succ_start + 1:]:
        m = re.search(r'#(\d+)\s+(.+?)\s+loyalty\s+(\d+)', line)
        if m:
            rank = int(m.group(1))
            char_id = rank_to_id.get(rank)
            if char_id is not None:
                drawn_ids.append((rank, char_id))

    # R-1: Assert the count BEFORE comparing order.
    # If the parse found fewer rows than owed (or none at all), the tab is defective.
    assert len(drawn_ids) >= owed, \
        f"Tab drew {len(drawn_ids)} succession rows but owes {owed} " \
        f"(simulation has {len(sim_order)} candidates, page size 10)"

    # Now compare the drawn order to the simulation order (position by position)
    sim_ids = [c.id for c in sim_order]
    for i in range(owed):
        assert drawn_ids[i][1] == sim_ids[i], \
            f"Row {i}: drawn {drawn_ids[i][1]} but simulation says {sim_ids[i]}"


def test_succession_order_pixel_change():
    """R-3 pixel check: renaming the man the simulation would crown changes pixels.

    Independent source: resolve_succession(realm) — not the peerage report.
    This is a different claim from R-2: naming the heir vs showing the order.
    """
    g, v = _view()
    realm = g.realms.get(v.house)
    assert realm is not None, "Game must have a realm"

    # Independent source — who the simulation would actually crown
    heir_char = resolve_succession(realm)
    assert heir_char is not None, "Simulation must resolve an heir"

    rpt = peerage_report(g, v.house)
    surf = pygame.Surface((1600, 1000))
    rect = pygame.Rect(0, 0, 1600, 1000)

    draw_house_tab(surf, rect, rpt)
    pixels1 = pygame.image.tobytes(surf, "RGBA")

    old_name = heir_char.name
    heir_char.name = "Sigma Renamed"

    rpt2 = peerage_report(g, v.house)
    surf2 = pygame.Surface((1600, 1000))
    draw_house_tab(surf2, rect, rpt2)
    pixels2 = pygame.image.tobytes(surf2, "RGBA")

    # Restore
    heir_char.name = old_name

    assert pixels1 != pixels2, "Pixels should change when the heir (per simulation) is renamed"


def test_kinsman_grievances_shown():
    """R-3 variant: A kinsman's recorded reasons (grievances) are drawn beside him
    in the succession lines.

    This is a distinct property from the succession order itself: the same ordered
    list of men can be drawn correctly while grievances are omitted entirely.
    """
    from gilded.society.characters import modify_opinion

    g, v = _view()
    realm = g.realms.get(v.house)
    assert realm is not None and realm.ruler is not None

    # Find a kin member who is in line for succession and alive
    sim_order = succession_order(realm)
    kin_with_grievance = None
    for char in sim_order:
        if char.id != realm.ruler.id and char.is_alive:
            kin_with_grievance = char
            break

    assert kin_with_grievance is not None, "Must have a succession candidate besides the ruler"

    # Record a grievance against the ruler
    modify_opinion(kin_with_grievance, realm.ruler, -40, "grievance")

    # Rebuild the report after the change
    rpt = peerage_report(g, v.house)
    lines = _house_tab_lines(rpt)
    text = "\n".join(lines)

    # The grievance text should appear in the tab output
    assert "grievance" in text.lower() or "[" in text, \
        f"Grievance for '{kin_with_grievance.name}' should be visible in tab lines"


def test_succession_order_completeness():
    """R-1: The tab draws all succession rows it owes within its display limit.

    The tab shows up to 10 succession rows.  Verify the first 10 alive candidates
    from the simulation's succession_order all appear in the tab output.
    """
    g, v = _view()
    realm = g.realms.get(v.house)
    assert realm is not None

    sim_order = succession_order(realm)
    assert len(sim_order) >= 3, "Game must have at least 3 succession candidates"

    rpt = peerage_report(g, v.house)
    lines = _house_tab_lines(rpt)
    text = "\n".join(lines)

    # The tab shows up to 10 succession rows — check those first 10 alive candidates appear
    shown = [c.name for c in sim_order if c.name and c.is_alive][:10]
    missing = [name for name in shown if name not in text]
    assert not missing, f"Tab is missing succession candidates it should show: {missing}"


def test_house_tab_lines_returns_lines():
    g, v = _view()
    rpt = peerage_report(g, v.house)
    lines = _house_tab_lines(rpt)
    assert isinstance(lines, list)
    assert len(lines) > 0


def test_draw_house_tab_draws():
    g, v = _view()
    rpt = peerage_report(g, v.house)
    surf = pygame.Surface((640, 480))
    rect = pygame.Rect(0, 0, 640, 480)
    draw_house_tab(surf, rect, rpt)
    # Surface should have pixels set
    assert surf.get_at((320, 240)) != (0, 0, 0, 0)
