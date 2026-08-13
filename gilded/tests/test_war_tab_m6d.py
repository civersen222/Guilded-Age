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
