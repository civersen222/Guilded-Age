"""Mission C4 wave 3 — folded-in C3 residuals.

Committed pins that must not drift:
  1. Order rows are not houses — power_row_title never prefixes an Order
     with "House ".
  2. The Powers layout never overlaps — no two row/dossier rects intersect
     on the fullest state we can construct.
  3. The C3 balance constants are pinned exactly (ambitions.FAMILY_DISPOSITION
     Order entries, orders lever constants, _head_stats bonuses).
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from gilded.ui.broadsheet import (
    power_row_title, powers_report, powers_model, powers_layout,
    ORDER_NAMES,
)
from gilded.ambitions import FAMILY_DISPOSITION
from gilded import orders as orders_mod


class _Line:
    def __init__(self, house):
        self.house = house


# ── 1. Order rows are not houses ────────────────────────────────────────────

def test_order_rows_do_not_read_as_houses():
    for order in ("Combine", "Bank", "Church", "Gazette"):
        assert order in ORDER_NAMES
        assert power_row_title(_Line(order)) == order
        assert not power_row_title(_Line(order)).startswith("House ")


def test_rival_rows_keep_the_house_prefix():
    assert power_row_title(_Line("Aldermoor")) == "House Aldermoor"


# ── 2. Powers layout must not overlap ───────────────────────────────────────

def _rects_overlap(a, b):
    return a.left < b.right and b.left < a.right \
        and a.top < b.bottom and b.top < a.bottom


def test_powers_layout_rows_do_not_overlap():
    from gilded.ui.app import new_app_state
    s = new_app_state(seed=7)
    for _ in range(3):
        s.game.end_turn()
    v = s.view if hasattr(s, "view") else None
    g, house = s.game, s.house
    lines = powers_report(g, house)
    model = powers_model(lines, selected=None)
    layout = powers_layout(model, pygame.Rect(0, 40, 420, 860))
    tbl = model.table
    tl = tbl.layout(layout["table"])
    detail = layout["detail"]
    rects = list(tl.row_rects) + [detail]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            assert not _rects_overlap(rects[i], rects[j]), \
                f"rect {i} overlaps rect {j}: {rects[i]} / {rects[j]}"


# ── 3. C3 balance constants pinned exactly ──────────────────────────────────

_ORDER_DISPOSITIONS = {
    "Organize": ("bold_craven", 1.0),
    "Recognition": ("ambitious_content", 1.0),
    "General Strike": ("cruel_compassionate", -1.0),
    "Purge Scabs": ("cruel_compassionate", 1.0),
    "Solvency": ("trusting_paranoid", 1.0),
    "Expansion": ("ambitious_content", 1.0),
    "Receivership": ("generous_greedy", 1.0),
    "King-making": ("ambitious_content", 1.0),
    "Endowment": ("generous_greedy", 1.0),
    "Crusade of Morals": ("pious_secular", 1.0),
    "Sanctuary": ("honest_deceitful", 1.0),
    "Schism": ("pious_secular", -1.0),
    "Circulation War": ("traditionalist_modernist", 1.0),
    "Expose": ("honest_deceitful", 1.0),
    "Respectability": ("honest_deceitful", 1.0),
    "Patronage": ("generous_greedy", 1.0),
}


def test_family_disposition_order_entries_pinned():
    for family, val in _ORDER_DISPOSITIONS.items():
        assert family in FAMILY_DISPOSITION, family
        assert FAMILY_DISPOSITION[family] == val, \
            (family, FAMILY_DISPOSITION[family], val)


def test_orders_lever_constants_pinned():
    assert orders_mod._BANK_DEBT == 50.0
    assert orders_mod._BANK_SEAT_LOAN == 25.0
    assert orders_mod._CHURCH_EYES == 0.25
    assert orders_mod._CHURCH_SEAT_RELIEF == 5.0
    assert orders_mod._GAZETTE_EYES == 0.25
    assert orders_mod._GAZETTE_SEAT_PRESTIGE == 0.5
    assert orders_mod._COMBINE_STRIKE == 0.5
    assert orders_mod._COMBINE_SEAT_PRESTIGE == 0.5


def test_head_stats_base_sevens_and_order_bonuses():
    # base 7s across the board
    for name in ("Combine", "Bank", "Church", "Gazette"):
        for axis in ("statecraft", "command", "industry", "intrigue",
                     "science", "resolve"):
            assert orders_mod._head_stats(name)[axis] >= 7, (name, axis)
    # the one bonus per Order
    assert orders_mod._head_stats("Combine")["command"] == 10
    assert orders_mod._head_stats("Bank")["industry"] == 10
    assert orders_mod._head_stats("Church")["intrigue"] == 10
    assert orders_mod._head_stats("Gazette")["science"] == 10
    # no cross-contamination
    assert orders_mod._head_stats("Combine")["industry"] == 7
    assert orders_mod._head_stats("Bank")["command"] == 7
    assert orders_mod._head_stats("Church")["science"] == 7
    assert orders_mod._head_stats("Gazette")["intrigue"] == 7
