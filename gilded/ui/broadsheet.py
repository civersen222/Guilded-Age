"""The broadsheet screens (mission G22, Stage 1 reframe): the century read as a
newspaper, fronted by a persistent scoreboard HUD, Council briefing, and Enterprises banner.

BroadsheetView renders one House's world across seven tabs. A HUD strip (the
Stage 1 read-model) rides above every tab so the four axes, the Tide, the era,
and the House's rank are always on screen. The Briefing tab is the landing view
each turn: the "Since last session" delta feed, the turn's papers, and the
docket surfaced as an Agenda. The paper tabs (Gazette, Ledger, Letters) set
papers.compose() in wrapped serif columns; the Docket tab and the Agenda share
one petition-card renderer; the Policies tab reads and sets the five standing
directive dials; the Atlas tab hands off to atlas_view; the House tab shows the
court and the standing of the realm.

The view is a CLIENT. handle_click() never touches the game - it returns an
action dict (or None) and lets app.py apply it. Executor cycling is the one
exception that stays inside the view: it only changes which name a future
rule-action will carry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame

from gilded.dashboard import Delta, delta, scoreboard
from gilded.grip import _name_for, report as grip_report
from gilded.intel import report as intel_report, threat_rank
from gilded.market import COMMODITIES


def _buyout_price(ent, owner_id, game):
    """Price to buy out a rival's stake in an enterprise."""
    from gilded.society.shares import stake_cost
    pct = ent.ledger.get(owner_id, 0.0)
    if pct <= 0:
        return 0
    return stake_cost(ent, pct, game)


import os

from gilded.papers import compose
from gilded.saga.narrator import NarratorTemplated
from gilded.ui.atlas_view import (
    OCEAN_COLOR, draw_atlas, pick_province, province_panel_lines)
from gilded.ui.widgets import (
    CARD_BG, CARD_EDGE, FADED, INK, PAPER_BG,
    Chip, Column, Meter, Table, TableLayout, blit_text, font as _font, wrap as _wrap,
    column_plan, flow_columns, FlowResult,
    TYPE_CAPTION, TYPE_BODY, TYPE_TEXT, TYPE_SUBTITLE, TYPE_HEADING, TYPE_TITLE,
)
from gilded.grip import (
    BAND_CONTESTED, BAND_IMPERILED, BAND_IRON_GRIP, BAND_SEIZED,
)
from gilded.ui.ledger import (
    LedgerModel, LedgerRow, TurnLine,
    money, gold, ledger_model, HISTORY_SPAN,
    totals_line, history_cells,
)
from gilded.ui.figures import figure
from gilded.ui.house_tab import draw_house_tab, _house_tab_lines
from gilded.endings import judge as _judge_ending
from gilded.ui.widgets import (
    INK, Region, RegionSet, RegionState,
    BLACK, PANEL_BG, TAB_BG, TAB_ACTIVE, TAB_TEXT, HUD_BG, HUD_INK,
    BUTTON_BG, BUTTON_EDGE, BUTTON_TEXT, DISABLED_BUTTON_BG, DISABLED_BUTTON_EDGE,
    EXEC_BG, ENDTURN_BG, ATTN_COLOR,
    SKIM_HIGHLIGHT, PICKER_BACK_BG, PICKER_ROW_BG,
    DISABLED_FILL, DISABLED_EDGE, DISABLED_TEXT,
    PICKER_SUBTITLE, PICKER_ROW_ALT_BG, OFFERABLE_BG, OFFERABLE_EDGE,
    GUIDE_BG, GUIDE_EDGE,
)

TABS = ("House", "Powers", "Atlas")

# spec §2 fate table — the dissolved 11-tab names still address their re-homed
# content: (spine, House page or Powers page).  Assigning a dissolved name
# to BroadsheetView.active_tab navigates to the home the content moved to.
LEGACY_TABS = {
    "Briefing": ("House", "Overview"),      # agenda card -> House ambition banner; alerts -> desk letters
    "Gazette": ("Atlas", None),            # the End Turn beat over the map; archived at the desk
    "Ledger": ("House", "Ledger"),
    "Letters": ("Atlas", None),            # desk strip on the Atlas
    "Docket": ("House", "Overview"),       # its decisions are the desk strip
    "Policies": ("House", "Overview"),     # edicts signed from the Court in Session
    "Enterprises": ("House", "Governance"),
    "War": ("Atlas", None),                # wars are drawn on the map
}

# The paper sections of the Atlas desk/archive: the dissolved Gazette and
# Letters tabs and the House Ledger page all render through _draw_paper, which
# is addressed by these section keys — a separate axis from the spine.
PAPER_SECTIONS = {"Gazette", "Ledger", "Letters"}

TAB_H = 40
BOTTOM_H = 56

# Danger thresholds
LEGIT_DANGER = 20.0
TIDE_DANGER = 70.0

# S17: the guide strip — a teaching statement and one next-step button drawn
# on every frame so a stranger's first click has a target. (GUIDE_BG and
# GUIDE_EDGE live in widgets.py with the rest of the palette.)
def guide_statement() -> str:
    """The opening guide text, built from the live TURN_BUDGET constant."""
    from gilded.chassis import TURN_BUDGET
    return (
        f"Your aim this century: raise your house to victory. "
        f"You win by keeping your capital and your standing high. "
        f"Your gold lives in the treasury; spend your attention wisely. "
        f"The century ends after {TURN_BUDGET} turns, or sooner in ruin — then the game ends."
    )

# HUD geometry: 3 rows (axes + legitimacy/tide, chips + texts, rival row always reserved)
_HUD_ROWS = 3
_METER_BAR_H = 14
_CHIP_H = 18
_TEXT_PT = TYPE_CAPTION
_ROW_GAP = 4
_PAD = 6


def _hud_height() -> int:
    """Fixed band height derived from row structure and widget metrics."""
    fs = _font(_TEXT_PT)
    text_h = fs.get_height()

    row1_h = max(_METER_BAR_H, text_h) + 2
    row2_h = max(_METER_BAR_H, text_h) + 2
    row3_h = max(_CHIP_H, text_h) + 2
    row4_h = max(_METER_BAR_H, text_h) + 2
    row5_h = text_h + 2

    return _PAD + row1_h + _ROW_GAP + row2_h + _ROW_GAP + row3_h + _ROW_GAP + row4_h + _ROW_GAP + row5_h + _PAD


@dataclass(frozen=True)
class HudModel:
    meters: Dict[str, Meter]
    chips: Dict[str, Chip]
    texts: Dict[str, str]


def hud_model(board, d: Delta) -> HudModel:
    """Pure builder: Scoreboard + Delta -> HudModel."""
    meters: Dict[str, Meter] = {}
    chips: Dict[str, Chip] = {}
    texts: Dict[str, str] = {}

    # Axis meters
    for name in ("capital", "standing", "blood", "world"):
        value = board.axes[name]
        delta_val = None if d.first_session else d.axes[name].change
        meters[name] = Meter(
            label=name.capitalize(),
            value=value,
            lo=0,
            hi=100,
            delta=delta_val,
            fmt="{:.0f}",
        )

    # Legitimacy meter
    legit_delta = None if d.first_session else d.legitimacy.change
    meters["legitimacy"] = Meter(
        label="Legitimacy",
        value=board.legitimacy,
        lo=0,
        hi=100,
        delta=legit_delta,
        danger=("below", LEGIT_DANGER),
        fmt="{:.0f}",
    )

    # Tide meter
    tide_delta = None if d.first_session else d.tide_level.change
    meters["tide"] = Meter(
        label="Tide",
        value=board.tide_level,
        lo=0,
        hi=100,
        delta=tide_delta,
        invert=True,
        danger=("above", TIDE_DANGER),
        fmt="{:.0f}",
    )

    # Rival axis meters (only when rival_axes exists)
    if board.rival_axes is not None:
        rival_label = board.rival_name or "Rival"
        for name in ("capital", "standing", "blood", "world"):
            meters[f"rival:{name}"] = Meter(
                label=f"{rival_label} {name.capitalize()}",
                value=board.rival_axes[name],
                lo=0,
                hi=100,
                delta=None,
                fmt="{:.0f}",
            )
        texts["rival"] = f"Rival: House {board.rival_name}"
    else:
        texts["rival"] = "No rival has emerged"

    # Chips
    treasury_dir = d.treasury.direction if not d.first_session else 0
    treasury_tone = "good" if treasury_dir > 0 else ("bad" if treasury_dir < 0 else "neutral")
    chips["treasury"] = Chip(
        text=f"Treasury {board.treasury:.0f}",
        tone=treasury_tone,
    )

    chips["atrocities"] = Chip(
        text=f"Atrocities {board.atrocities:.0f}",
        tone="bad" if board.atrocities > 0 else "neutral",
    )

    chips["phase"] = Chip(
        text=board.tide_phase,
        tone="neutral",
    )

    # Revolution countdown — only visible when brewing_turns > 0
    if board.brewing_turns > 0:
        from gilded.society.ideology import REVOLUTION_BREWING_TURNS
        rev_text = f"Revolution: {board.brewing_turns}/{REVOLUTION_BREWING_TURNS}"
        if board.revolution_explanation:
            rev_text += f" — {board.revolution_explanation}"
        chips["revolution"] = Chip(
            text=rev_text,
            tone="bad",
        )

    # Texts
    texts["era"] = f"{board.era_title} ·"
    texts["era_sub"] = f" {board.year} ({board.century_pct * 100:.0f}%)"
    texts["rank"] = f"Rank #{board.rank}"
    # intent placeholder — filled by _draw_hud when game object is available
    texts["intent"] = ""

    return HudModel(meters=meters, chips=chips, texts=texts)


def hud_layout(model: HudModel, band: pygame.Rect) -> Dict[str, pygame.Rect]:
    """Pure layout: assign a pygame.Rect to every key in the model, 5 rows."""
    result: Dict[str, pygame.Rect] = {}
    fs = _font(_TEXT_PT)
    text_h = fs.get_height()

    margin = 8
    x0 = band.left + margin
    y0 = band.top + _PAD
    usable_w = band.width - 2 * margin

    rh = max(_METER_BAR_H, text_h) + 2  # standard row height

    # --- Row 1: 4 axis meters ---
    y = y0
    meter_w = (usable_w - 3 * _ROW_GAP) // 4
    for i, name in enumerate(("capital", "standing", "blood", "world")):
        rx = x0 + i * (meter_w + _ROW_GAP)
        result[name] = pygame.Rect(rx, y, meter_w, rh)

    y += rh + _ROW_GAP

    # --- Row 2: legitimacy + tide meters ---
    half_w = (usable_w - _ROW_GAP) // 2
    result["legitimacy"] = pygame.Rect(x0, y, half_w, rh)
    result["tide"] = pygame.Rect(x0 + half_w + _ROW_GAP, y, half_w, rh)

    y += rh + _ROW_GAP

    # --- Row 3: chips (treasury, atrocities, phase + revolution if brewing) + era text ---
    chip_specs = []
    row3_keys = ["treasury", "atrocities", "phase"]
    if "revolution" in model.chips:
        row3_keys.append("revolution")
    for key in row3_keys:
        w = fs.size(model.chips[key].text)[0] + 16
        chip_specs.append((key, w))
    chip_specs.append(("era", fs.size(model.texts["era"])[0] + 8))
    chip_specs.append(("era_sub", fs.size(model.texts["era_sub"])[0] + 4))

    n_items = len(chip_specs)
    total_gap = (n_items - 1) * 12
    total_needed = sum(w for _, w in chip_specs) + total_gap
    if total_needed > usable_w:
        scale = usable_w / total_needed
        chip_specs = [(key, int(w * scale)) for key, w in chip_specs]

    cx = x0
    row3_h = max(_CHIP_H, text_h) + 2
    for key, w in chip_specs:
        result[key] = pygame.Rect(cx, y, w, row3_h)
        cx += w + 12

    y += row3_h + _ROW_GAP

    # --- Row 4: rival label + rank (both text, drawn in HUD_INK) ---
    rival_w = fs.size(model.texts["rival"])[0] + 8
    rank_w = fs.size(model.texts["rank"])[0] + 8
    result["rival"] = pygame.Rect(x0, y, rival_w, rh)
    result["rank"] = pygame.Rect(x0 + rival_w + 12, y, rank_w, rh)

    y += rh + _ROW_GAP

    # --- Row 5: rival meters (if any) + intent ---
    rival_keys = [k for k in model.meters if k.startswith("rival:")]
    row5_h = max(_METER_BAR_H, text_h) + 2

    if rival_keys:
        n = len(rival_keys)
        intent_min = 40
        space_for_rivals = usable_w - intent_min - (n - 1) * _ROW_GAP - 12
        rival_meter_w = max(40, space_for_rivals // n)
        for i, key in enumerate(rival_keys):
            rx = x0 + i * (rival_meter_w + _ROW_GAP)
            result[key] = pygame.Rect(rx, y, rival_meter_w, row5_h)
        used = n * rival_meter_w + (n - 1) * _ROW_GAP
        intent_w = max(intent_min, usable_w - used - 12)
        intent_x = x0 + used + 12
        if intent_x + intent_w > band.right - margin:
            intent_w = band.right - margin - intent_x
        result["intent"] = pygame.Rect(intent_x, y, intent_w, row5_h)
    else:
        result["intent"] = pygame.Rect(x0, y, usable_w, row5_h)

    return result

PAD = 16
TOOLTIP_MAX_WIDTH = 300  # maximum tooltip panel content width

# Re-exported from widgets.py for backward compatibility (imported at module level above)

# ── Enterprises table ─────────────────────────────────────────────────

_BAND_TONE = {
    BAND_SEIZED: "bad",
    BAND_IMPERILED: "bad",
    BAND_CONTESTED: "warn",
    BAND_IRON_GRIP: "good",
}

_BAND_DISPLAY = {
    BAND_SEIZED: "Seized",
    BAND_IMPERILED: "Imperiled",
    BAND_CONTESTED: "Contested",
    BAND_IRON_GRIP: "Iron Grip",
}

ENT_COLS: Tuple[Column, ...] = (
    Column("Venture", width=2.0, align="left"),
    Column("Sector", width=1.0, align="left"),
    Column("Tier", width=0.8, align="right"),
    Column("Dividend", width=1.0, align="right"),
    Column("Δ", width=0.8, align="right"),
    Column("Director", width=1.5, align="left"),
    Column("Stake", width=0.8, align="right"),
    Column("Top outside", width=1.2, align="left"),
)
DELTA_COL = 4

_ENT_TABLE_H_MAX = 600  # max pixel height for the table before overflow

# ────────────────────────────────────────────────────────────────────────────
# Powers table
# ────────────────────────────────────────────────────────────────────────────

POWER_COLS: Tuple[Column, ...] = (
    Column("House", width=1.0, align="left"),
    Column("Threat", width=0.6, align="right"),
    Column("Intel", width=0.6, align="right"),
    Column("Ties", width=3.0, align="left"),
    Column("Apparent intent", width=5.0, align="left"),
)
INTEL_COL = 2


class PowersTable(Table):
    """Table subclass that truncates cell text to fit pixel widths."""

    def layout(self, rect: pygame.Rect) -> TableLayout:
        from gilded.ui.widgets import (
            TableLayout,
            _weighted_columns,
            _place_text,
            font,
        )

        f_header = font(self.size, bold=True)
        f_body = font(self.size)
        header_h = f_header.get_linesize()
        body_h = f_body.get_linesize()
        gap = 2
        rule_h = 1 if self.row_rule else 1

        weights = [c.width for c in self.cols]
        col_rects = _weighted_columns(rect, weights, gap=0)
        header_rects = [r.copy() for r in col_rects]
        for r in header_rects:
            r.height = header_h

        rule_y = rect.top + header_h + rule_h

        data_top = rule_y + gap
        data_bottom = rect.bottom
        available_data_h = data_bottom - data_top
        row_count = len(self.data)
        if row_count == 0:
            row_rects: list[pygame.Rect] = []
            cell_rects: list[list[pygame.Rect]] = []
            text_rects: list[list[pygame.Rect]] = []
        else:
            # C6: never squeeze rows below the rendered text height —
            # adjacent text rects would overlap.  Rows that don't fit are
            # omitted from the layout (the powers model's overflow warning
            # already names the first omitted house).
            # C6: every data row gets a constant height at least tall enough
            # for its text (body linesize + the rendered glyph height), so two
            # adjacent text rects can never overlap.  Rows that would be
            # clipped at the bottom are omitted — the powers model's overflow
            # warning already names the first omitted house.
            # row_h already includes the inter-row gap (rows step by row_h)
            row_h = max(body_h, f_body.get_height()) + gap
            n_rows = min(row_count, max(0, available_data_h // row_h))
            row_rects = []
            y = data_top
            for i in range(n_rows):
                row_rects.append(pygame.Rect(rect.left, y, rect.width, row_h - gap))
                y += row_h

            cell_rects = []
            text_rects = []
            for row_idx, row_rect in enumerate(row_rects):
                row = self.data[row_idx] if row_idx < len(self.data) else []
                row_cells = _weighted_columns(row_rect, weights, gap=0)
                cell_rects.append(list(row_cells))
                row_text_rects: list[pygame.Rect] = []
                for col_idx in range(len(self.cols)):
                    cell = row[col_idx] if col_idx < len(row) else ""
                    align = self._resolve_align(col_idx)
                    cell = self._fit(cell, f_body, row_cells[col_idx])
                    text_rect = _place_text(
                        cell, f_body, row_cells[col_idx], align, body_h
                    )
                    row_text_rects.append(text_rect)
                text_rects.append(row_text_rects)

        header_text_rects = []
        for col_idx in range(len(self.cols)):
            align = self._resolve_align(col_idx)
            h_rect = header_rects[col_idx]
            header_text = self.cols[col_idx].header
            text_rect = _place_text(header_text, f_header, h_rect, align, header_h)
            header_text_rects.append(text_rect)

        return TableLayout(
            header_rects=header_rects,
            rule_y=rule_y,
            row_rects=row_rects,
            cell_rects=cell_rects,
            text_rects=text_rects,
            header_text_rects=header_text_rects,
        )

    @staticmethod
    def _fit(text: str, f: pygame.font.Font, cell: pygame.Rect) -> str:
        if not text.strip():
            return text
        max_w = cell.width - 8
        if f.size(text)[0] <= max_w:
            return text  # fits, no truncation needed
        # Text is too long — shorten and append ellipsis
        ellipsis = "…"
        while len(text) > 1:
            candidate = text + ellipsis
            if f.size(candidate)[0] <= max_w:
                return candidate
            text = text[:-1]
        return text + ellipsis

_POW_TABLE_H_MAX = 600  # max pixel height for the powers table before overflow


@dataclass(frozen=True)
class PowerLine:
    house: str
    tier: int
    breakdown: Tuple[str, ...]
    apparent_intent: str
    can_place_informant: bool


@dataclass(frozen=True)
class PowersModel:
    table: Table
    row_houses: Tuple[str, ...]
    intel_tones: Tuple[str, ...]
    blind_rows: Tuple[int, ...]
    informant_rows: Tuple[int, ...]
    selected_row: Optional[int]
    texts: Dict[str, str]
    overflow_name: Optional[str]
    overflow_count: int


def powers_report(game, house) -> Tuple[PowerLine, ...]:
    """Impure: collect intel data for every rival house, return PowerLines."""
    lines: List[PowerLine] = []
    attention = game.attention.get(house, 0)
    for h in threat_rank(game):
        r = intel_report(game, house, h)
        can_place = (attention > 0 and (house, h) not in game.informants)
        lines.append(PowerLine(
            house=h,
            tier=r.tier,
            breakdown=tuple(r.breakdown),
            apparent_intent=r.apparent_intent,
            can_place_informant=can_place,
        ))
    # the four Orders: a head (face) the player knows, and a goal the fog
    # gates - an informant within an Order reads its pursuit
    for name in sorted(getattr(game, "orders", {})):
        r = intel_report(game, house, name)
        lines.append(PowerLine(
            house=name,
            tier=r.tier,
            breakdown=tuple(r.breakdown),
            apparent_intent=r.apparent_intent,
            can_place_informant=(attention > 0
                                 and (house, name) not in game.informants),
        ))
    return tuple(lines)


def _intel_tone(tier: int) -> str:
    if tier == 0:
        return "dead"
    elif tier == 1:
        return "warn"
    elif tier == 2:
        return "neutral"
    else:
        return "good"


# The four Orders. A Powers row whose name is an Order is titled by its own
# name (no "House" prefix) so Order rows never read "House Combine".
ORDER_NAMES = frozenset({"Combine", "Bank", "Church", "Gazette"})


def power_row_title(line) -> str:
    """The rendered title cell for a Powers row: rival houses keep a
    "House " prefix; Orders are named as themselves (never "House Combine")."""
    name = line.house
    if name in ORDER_NAMES:
        return name
    return f"House {name}"


def powers_model(lines, selected=None) -> PowersModel:
    """Build a pure PowersModel from a tuple of PowerLine objects."""
    rows: List[List[str]] = []
    row_houses: List[str] = []
    intel_tones: List[str] = []
    blind_rows: List[int] = []
    informant_rows: List[int] = []

    for i, ln in enumerate(lines):
        # Threat = 1-based rank
        threat_str = str(i + 1)
        # Intel = "{tier}/3"
        intel_str = f"{ln.tier}/3"
        # Ties cell — truncate long lists
        if ln.breakdown:
            ties_str = ", ".join(ln.breakdown)
        else:
            ties_str = "—"
        # ties_str used as-is; _fit handles truncation
        # Apparent intent — _fit handles truncation
        intent_str = ln.apparent_intent or "—"

        def _clean(s: str) -> str:
            return s.replace("|", "")

        rows.append([
            _clean(power_row_title(ln)),
            threat_str,
            intel_str,
            _clean(ties_str),
            _clean(intent_str),
        ])
        row_houses.append(ln.house)
        intel_tones.append(_intel_tone(ln.tier))
        if ln.tier == 0:
            blind_rows.append(i)
        if ln.can_place_informant:
            informant_rows.append(i)

    # Selection
    selected_row = None
    if selected is not None:
        try:
            selected_row = row_houses.index(selected)
        except ValueError:
            pass

    # Build table
    tbl = PowersTable(POWER_COLS, rows)

    # Overflow
    overflow_name = None
    overflow_count = 0
    max_h = _POW_TABLE_H_MAX
    needed_h = tbl.height()
    if needed_h > max_h:
        # Count rows that won't fit
        row_h_pixels = tbl.height() / max(1, len(lines)) if lines else 0
        rows_fit = int(max_h / row_h_pixels) if row_h_pixels > 0 else len(lines)
        overflow_count = max(0, len(lines) - rows_fit)
        if overflow_count > 0 and lines:
            overflow_name = row_houses[rows_fit] if rows_fit < len(row_houses) else None

    # Texts
    texts: Dict[str, str] = {}
    if not lines:
        texts["empty"] = "(no rival House stands against you)"
    if selected_row is not None and selected_row < len(lines):
        texts[f"intent_{selected_row}"] = lines[selected_row].apparent_intent

    return PowersModel(
        table=tbl,
        row_houses=tuple(row_houses),
        intel_tones=tuple(intel_tones),
        blind_rows=tuple(blind_rows),
        informant_rows=tuple(informant_rows),
        selected_row=selected_row,
        texts=texts,
        overflow_name=overflow_name,
        overflow_count=overflow_count,
    )


def powers_layout(model, content: pygame.Rect) -> Dict[str, pygame.Rect]:
    """Compute layout rects for the Powers tab."""
    margin = 4
    x = content.left + margin
    y = content.top + margin
    w = content.width - 2 * margin
    bottom_limit = content.bottom - margin

    # Title
    f_title = _font(TYPE_HEADING, bold=True)
    title_h = f_title.get_linesize()
    title_rect = pygame.Rect(x, y, w, title_h)
    y += title_h + 8

    # Reserve space for detail + buttons at bottom
    detail_reserve = 36
    btn_reserve = 28 if model.informant_rows else 0
    bottom_reserve = detail_reserve + btn_reserve

    # Table height: what's left after title and bottom reserve
    tbl_max_h = bottom_limit - bottom_reserve - y
    tbl = model.table
    tbl_h = min(tbl.height(), max(40, tbl_max_h))
    tbl_rect = pygame.Rect(x, y, w, tbl_h)

    # Detail area (below table)
    detail_y = y + tbl_h + 4
    detail_rect = pygame.Rect(x, detail_y, w, detail_reserve)

    # Informant buttons area (below detail)
    btn_y = min(detail_rect.bottom + 4, bottom_limit - btn_reserve)
    btn_rect = pygame.Rect(x, btn_y, w, min(btn_reserve, bottom_limit - btn_y))

    return {
        "title": title_rect,
        "table": tbl_rect,
        "detail": detail_rect,
        "buttons": btn_rect,
    }


@dataclass(frozen=True)
class EnterprisesModel:
    table: Table
    row_eids: Tuple[int, ...]
    delta_tones: Tuple[str, ...]
    skim_rows: Tuple[int, ...]
    band_chip: Chip
    margin_meter: Meter
    texts: Dict[str, str]
    overflow_name: Optional[str]
    overflow_count: int


def enterprises_model(report) -> EnterprisesModel:
    """Build a pure EnterprisesModel from a GripReport."""
    rows: List[List[str]] = []
    eids: List[int] = []
    deltas: List[str] = []
    skims: List[int] = []

    for el in report.enterprises:
        # Director cell
        if el.director is not None:
            dir_name = el.director.name
            if el.director.disloyal:
                dir_name = f"{dir_name} [skim]"
        else:
            dir_name = "Vacant"

        # Delta cell
        if el.dividend_delta is None:
            delta_str = ""
        else:
            delta_str = f"{el.dividend_delta:+.1f}"

        # Top outside cell
        if el.top_outside is None:
            outside_str = "—"
        else:
            outside_str = f"{el.top_outside[0]} {el.top_outside[1]:.1f}%"

        def _clean(s: str) -> str:
            """Strip pipe characters from cell values."""
            return s.replace("|", "")

        rows.append([
            _clean(el.name),
            _clean(el.sector),
            str(el.tier),
            f"{el.dividend:.1f}",
            delta_str,
            _clean(dir_name),
            f"{el.your_stake:.1f}%",
            _clean(outside_str),
        ])
        eids.append(el.eid)
        deltas.append(delta_str)

        # Skim tracking
        if el.director is not None and el.director.disloyal:
            skims.append(len(rows) - 1)

    # Delta tones
    delta_tones = []
    for el in report.enterprises:
        if el.dividend_delta is None:
            delta_tones.append("neutral")
        elif el.dividend_delta > 0:
            delta_tones.append("good")
        elif el.dividend_delta < 0:
            delta_tones.append("bad")
        else:
            delta_tones.append("neutral")

    tbl = Table(ENT_COLS, rows)
    tbl_h = tbl.height()

    # Overflow detection
    if tbl_h > _ENT_TABLE_H_MAX:
        # Estimate how many rows fit
        f = _font(TYPE_BODY)
        body_h = f.get_linesize()
        header_h = _font(TYPE_BODY, bold=True).get_linesize()
        gap = 2
        rule_h = 1
        available_data_h = _ENT_TABLE_H_MAX - header_h - rule_h - gap
        rows_fit = available_data_h // (body_h + gap)
        overflow_count = max(0, len(rows) - rows_fit)
        overflow_name = f"{overflow_count} ventures did not fit"
    else:
        overflow_name = None
        overflow_count = 0

    # Band chip
    band_text = _BAND_DISPLAY.get(report.band, report.band.replace("_", " "))
    band_tone = _BAND_TONE.get(report.band, "neutral")
    band_chip = Chip(band_text, tone=band_tone)

    # Margin meter
    margin_meter = Meter(
        label="Margin",
        value=report.margin,
        lo=-30.0,
        hi=30.0,
        danger=("below", 0.0),
        fmt="{:.1f}",
    )

    # Texts
    texts: Dict[str, str] = {}
    if report.top_predator is not None:
        texts["predator"] = (
            f"Top threat: {report.top_predator.name} "
            f"({report.top_predator.stake:.1f}%)"
        )
    texts["stake"] = f"Controlling stake: {report.controlling_stake:.1f}%"

    return EnterprisesModel(
        table=tbl,
        row_eids=tuple(eids),
        delta_tones=tuple(delta_tones),
        skim_rows=tuple(skims),
        band_chip=band_chip,
        margin_meter=margin_meter,
        texts=texts,
        overflow_name=overflow_name,
        overflow_count=overflow_count,
    )


def enterprises_layout(model, content: pygame.Rect) -> Dict[str, pygame.Rect]:
    """Lay out the enterprises table and controls inside content."""
    margin = 4
    x = content.left + margin
    y = content.top + margin
    w = content.width - 2 * margin

    # Top row: band chip + margin meter
    chip_size = model.band_chip.size()
    chip_rect = pygame.Rect(x, y, chip_size[0], chip_size[1])
    meter_w = w - chip_size[0] - 8
    meter_rect = pygame.Rect(x + chip_size[0] + 8, y, meter_w, chip_size[1])

    # Table
    tbl_y = y + chip_size[1] + 8
    tbl_h = min(model.table.height(), _ENT_TABLE_H_MAX)
    tbl_rect = pygame.Rect(x, tbl_y, w, tbl_h)

    # Action area (below table)
    action_y = tbl_y + tbl_h + 8
    action_h = content.bottom - action_y - margin
    action_rect = pygame.Rect(x, action_y, w, max(action_h, 50))

    return {
        "chip": chip_rect,
        "meter": meter_rect,
        "table": tbl_rect,
        "action": action_rect,
    }


class BroadsheetView:
    _found_picker: Optional[bool]

    @property
    def text_rows(self) -> list:
        """(pygame.Rect, str) per text line drawn on the last draw pass."""
        from gilded.ui.widgets import _text_rows
        return list(_text_rows)

    @property
    def active_tab(self) -> str:
        return self._active_tab

    @active_tab.setter
    def active_tab(self, name: str) -> None:
        # spec §2 fate table: a dissolved tab name navigates to the home its
        # content moved to (spine + inner page).  "House"/"Powers"/"Atlas"
        # stay the three spines.
        if name in LEGACY_TABS:
            spine, page = LEGACY_TABS[name]
            self._active_tab = spine
            if page == "Ledger":
                self.house_page = "Ledger"
            elif page == "Governance":
                self.house_page = "Governance"
            else:
                self.house_page = "Overview"
            if spine == "Atlas":
                self.atlas_desk = True
            self.paper_section = name if name in PAPER_SECTIONS else None
        else:
            self._active_tab = name
            self.paper_section = None

    def __init__(self, game, house_name: str, narrator=None):
        self.game = game
        self.house = house_name
        # the narrator rewrites the Gazette's prose only; templated is identity.
        self.narrator = narrator if narrator is not None else NarratorTemplated()
        self.narrate_on = True
        # Inner pages of the three spines (spec §2 fate table): the dissolved
        # tabs' content re-homed as pages.  The Atlas desk strip (Letters)
        # and the End Turn gazette are drawn on the Atlas itself.
        self.house_page = "Overview"
        self.house_pages = ["Overview", "Policies", "Ledger", "Governance"]
        self.powers_page = "Overview"
        self.powers_pages = ["Overview", "Dossier"]
        self.atlas_desk = False
        # C4 residual (C5): the war panel left the map field.  The desk strip
        # carries a War toggle; when open it draws the war panel as a
        # right-column drawer that can never shadow a province centroid.
        self.war_drawer = False
        self.paper_section = None
        self.active_tab = TABS[0]
        self.gazette_page = None
        # Accent ledger (registry.ACCENTS): entries ("vermillion", is_player)
        # or ("gold", is_player) that THIS draw pass actually made.  Cleared
        # at the start of every draw(); registry/probe count what is drawn.
        self._accent_log: List[tuple] = []
        self._ladder_rows = None
        self.selected_pid: Optional[int] = None
        self._powers_selected: Optional[str] = None
        # the previous turn's board, retained by app.py across end_turn so the
        # briefing can show "since last session"; None means first session.
        self.prev_board = None
        # per-petition executor choice: an index into that card's candidate
        # list, where index 0 means "let the game pick the seat's default".
        self._exec_idx: Dict[int, int] = {}
        # hit regions, rebuilt every draw:
        self._tab_rects: Dict[str, pygame.Rect] = {}
        self._end_turn_rect: Optional[pygame.Rect] = None
        self._narrate_rect: Optional[pygame.Rect] = None
        self._option_hits: List[Tuple[pygame.Rect, tuple]] = []
        self._exec_hits: List[Tuple[pygame.Rect, int]] = []
        self._dial_hits: List[Tuple[pygame.Rect, str]] = []
        self._atlas_polys: Dict[int, List[Tuple[int, int]]] = {}
        self._enterprise_hits: List[Tuple[pygame.Rect, dict]] = []
        self._appoint_hits: List[Tuple[pygame.Rect, dict]] = []
        self._informant_hits: List[Tuple[pygame.Rect, dict]] = []

        # court appointment picker state: None or position_key
        self._court_picker: Optional[str] = None
        self._ambition_picker: bool = False
        # heir picker state: None or True (picker open)
        self._heir_picker: Optional[bool] = None
        # director picker state: None or eid whose picker is open
        self._director_picker: Optional[int] = None
        self._director_picker_hits: List[Tuple[pygame.Rect, dict]] = []
        self._found_picker: Optional[bool] = None
        self._found_picker_hits: List[Tuple[pygame.Rect, dict]] = []
        # share picker state: None or {"direction": "buy"/"sell", "eid": int}
        self._share_picker: Optional[dict] = None
        self._share_picker_hits: List[Tuple[pygame.Rect, dict]] = []
        # garrison picker state: None or True (picker open)
        self._garrison_picker: Optional[bool] = None
        self._garrison_picker_hits: List[Tuple[pygame.Rect, dict]] = []
        # scheme picker state: None or True (picker open)
        self._scheme_picker: Optional[bool] = None
        self._scheme_picker_hits: List[Tuple[pygame.Rect, dict]] = []
        self._action_messages: List[str] = []
        self.hover_pos: Tuple[int, int] | None = None
        self.regions = RegionSet()
        self.hovered: Optional[Region] = None
        self.tooltip_text: str | None = None
        self.tooltip_rect: pygame.Rect | None = None
        self._w = 0
        self._h = 0
        # epilogue cache — computed once when game_over is set
        self._epilogue = None

    # --- executor candidates -------------------------------------------------

    def _candidates(self, pid: int) -> List[Optional[object]]:
        """None (the default) followed by the realm's living characters."""
        realm = self.game.realms.get(self.house)
        chars = []
        if realm is not None:
            chars = sorted((c for c in realm.characters if c.is_alive),
                           key=lambda c: c.name)
        return [None] + chars

    def _chosen_executor(self, pid: int):
        cands = self._candidates(pid)
        idx = self._exec_idx.get(pid, 0) % len(cands)
        return cands[idx]

    def handle_hover(self, pos: Tuple[int, int]) -> None:
        self.hover_pos = pos
        self.hovered = self.regions.at(pos)

    # --- drawing -------------------------------------------------------------

    def draw(self, surface) -> None:
        self._w, self._h = surface.get_size()
        self.regions.clear()
        self._option_hits = []
        self._exec_hits = []
        self._dial_hits = []
        self._enterprise_hits = []
        self._appoint_hits = []
        self._share_picker_hits = []
        self._informant_hits = []

        self._director_picker_hits = []
        self._found_picker_hits = []
        self._accent_log = []
        from gilded.ui.widgets import take_text_rows as _take_text_rows
        _take_text_rows()  # clear the C6.5 ledger before this pass
        surface.fill(PAPER_BG)
        hud_h = _hud_height()
        content = pygame.Rect(0, TAB_H + hud_h, self._w,
                              self._h - TAB_H - hud_h - BOTTOM_H)
        content.height -= self._guide_text_height() + 4

        if self.active_tab == "House":
            if self.house_page == "Ledger":
                self._draw_house_page_header(surface, content, "Ledger")
                self._draw_ledger(surface, content)
            elif self.house_page == "Policies":
                self._draw_house_page_header(surface, content, "Policies")
                self._draw_policies(surface, content)
            elif self.house_page == "Governance":
                self._draw_house_page_header(surface, content, "Governance")
                self._draw_enterprises(surface, content)
            else:
                self._draw_house(surface, content)
        elif self.active_tab == "Powers":
            if self.powers_page == "Dossier":
                self._draw_house_page_header(surface, content, "Dossier")
                self._draw_powers_dossier(surface, content)
            else:
                self._draw_powers(surface, content)
        elif self.active_tab == "Atlas":
            self._draw_atlas(surface)
            # spec §2: the War tab dies — wars are drawn on the map; the
            # garrison/raise controls ride in a right-column drawer so the
            # panel never shadows a province centroid (C4 residual).
            if self.war_drawer:
                self._draw_war(surface, self._war_drawer_rect(content))
            self._draw_war_toggle(surface, content)

        # ── Ending overlay when the age closes ──────────────────────────────
        if self.game.game_over is not None:
            if self._epilogue is None:
                self._epilogue = _judge_ending(self.game, self.house)
            self._draw_ending_overlay(surface, content)
            return  # skip tab bar, hud, bottom bar — ending is the page

        self._draw_tab_bar(surface)
        self._draw_hud(surface)
        self._draw_action_messages(surface)
        self._action_messages.clear()
        self._draw_bottom_bar(surface)
        self._draw_guide(surface)

        # ── I3e: re-resolve hover and draw tooltip ──────────────────────────
        self.tooltip_text = None
        self.tooltip_rect = None
        if self.hover_pos is not None:
            self.hovered = self.regions.at(self.hover_pos)
        if self.hovered is not None:
            r = self.hovered
            if r.state is RegionState.DISABLED:
                text = r.reason
            else:
                text = r.hint
            if text:
                pygame.draw.rect(surface, INK, r.rect, 2)
                font = _font(TYPE_BODY)
                words = text.split()
                lines = []
                current_line = ""
                max_w = TOOLTIP_MAX_WIDTH
                ellipsis = "..."
                for word in words:
                    # Truncate words wider than the cap so they don't overflow the panel
                    if font.size(word)[0] > max_w:
                        while font.size(word + ellipsis)[0] >= max_w and len(word) > 1:
                            word = word[:-1]
                        word += ellipsis
                    test = (current_line + " " + word).strip()
                    if font.size(test)[0] <= max_w:
                        current_line = test
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                line_h = font.get_linesize()
                pad = 4
                content_w = max(font.size(line)[0] for line in lines) if lines else 0
                panel_w = min(content_w + 2 * pad, max_w + 2 * pad)
                panel_h = len(lines) * line_h + 2 * pad
                x = self.hover_pos[0] + 12
                y = self.hover_pos[1] + 12
                screen = surface.get_rect()
                if x + panel_w > screen.right:
                    x = self.hover_pos[0] - panel_w - 12
                if y + panel_h > screen.bottom:
                    y = self.hover_pos[1] - panel_h - 12
                if x < 0:
                    x = 4
                if y < 0:
                    y = 4
                rect = pygame.Rect(x, y, panel_w, panel_h)
                # Clamp drawing to tooltip rect so no pixel outside is changed
                old_clip = surface.get_clip()
                surface.set_clip(rect)
                surface.fill(INK, rect)
                pygame.draw.rect(surface, CARD_EDGE, rect, 1)
                cy = rect.top + pad
                for line in lines:
                    blit_text(surface, font, line, (rect.left + pad, cy), PAPER_BG)
                    cy += line_h
                surface.set_clip(old_clip)
                self.tooltip_text = text
                self.tooltip_rect = rect

    def _draw_tab_bar(self, surface) -> None:
        pygame.draw.rect(surface, TAB_BG, (0, 0, self._w, TAB_H))
        tabw = self._w // len(TABS)
        font = _font(TYPE_TEXT, bold=True)
        self._tab_rects = {}
        TAB_HINTS = {
            "House": "Your court, your people, your ledger, and your ventures.",
            "Powers": "See the other houses, their axes, and their moves.",
            "Atlas": "Survey the realm's map, its wars, and your letters.",
        }
        for i, name in enumerate(TABS):
            rect = pygame.Rect(i * tabw, 0, tabw, TAB_H)
            self._tab_rects[name] = rect
            self.regions.add(Region(
                rect=rect,
                action={"tab": name},
                state=(RegionState.ACTIVE if name == self.active_tab
                       else RegionState.ENABLED),
                hint=TAB_HINTS[name],
                group="tabs",
            ))
            if name == self.active_tab:
                pygame.draw.rect(surface, TAB_ACTIVE, rect)
            blit_text(surface, font, name,
                     (rect.centerx - font.size(name)[0] / 2,
                      rect.centery - font.size(name)[1] / 2),
                     INK if name == self.active_tab else TAB_TEXT)

    def _draw_hud(self, surface) -> None:
        b = scoreboard(self.game, self.house)
        d = delta(self.prev_board, b)
        model = hud_model(b, d)
        y0 = TAB_H
        hud_h = _hud_height()
        band = pygame.Rect(0, y0, self._w, hud_h)
        pygame.draw.rect(surface, HUD_BG, band)
        layout = hud_layout(model, band)
        fs = _font(_TEXT_PT)

        # Draw meters
        for key, rect in layout.items():
            if key in model.meters:
                model.meters[key].draw(surface, rect)
            elif key in model.chips:
                chip = model.chips[key]
                pygame.draw.rect(surface, chip.bg(), rect, border_radius=4)
                blit_text(surface, fs, chip.text,
                          (rect.left + 6,
                           rect.centery - fs.size(chip.text)[1] // 2), INK)
            elif key in model.texts:
                text = model.texts[key]
                blit_text(surface, fs, text,
                          (rect.left,
                           rect.centery - fs.size(text)[1] // 2), HUD_INK)

        # Draw intent text in row 5
        spotlight = b.rival_name or (
            threat_rank(self.game)[0] if threat_rank(self.game) else None)
        if spotlight is not None:
            intent = intel_report(self.game, self.house, spotlight).apparent_intent
            intent_text = f"Their design: {intent}"
        else:
            intent_text = "No clear threat"
        intent_rect = layout["intent"]
        blit_text(surface, fs, intent_text,
                  (intent_rect.left,
                   intent_rect.centery - fs.size(intent_text)[1] // 2),
                  HUD_INK)

    def _draw_action_messages(self, surface) -> None:
        """Draw action result messages in the bottom bar area above the turn button."""
        msgs = list(self._action_messages) if self._action_messages else []
        if not msgs:
            return
        font = _font(TYPE_TEXT)
        y = self._h - BOTTOM_H - 10
        max_w = self._w - 2 * PAD
        for msg in reversed(msgs):
            parts = []
            current = ""
            for word in msg.split():
                test = (current + " " + word).strip() if current else word
                if font.size(test)[0] <= max_w:
                    current = test
                else:
                    if current:
                        parts.append(current)
                    current = word
            if current:
                parts.append(current)
            for line in reversed(parts):
                h = font.size(line)[1]
                blit_text(surface, font, line, (PAD, y - h), INK)
                y -= h + 2
            break  # Show only the most recent message

    def _draw_ending_overlay(self, surface, content) -> None:
        """Draw the ending overlay when the age closes."""
        epilogue = self._epilogue
        PAD = 40
        w, h = self._w, self._h

        # Semi-transparent overlay
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((245, 240, 230, 200))
        surface.blit(overlay, (0, 0))

        # Border
        pygame.draw.rect(surface, INK, (0, 0, w, h), 3)

        y = TAB_H + 20
        f_title = _font(TYPE_TITLE, bold=True)
        ending_name = epilogue.ending_key
        title_rect = blit_text(surface, f_title, ending_name, (PAD, y), INK)
        y = title_rect.bottom + 10

        # Four axis scores
        f_axis = _font(TYPE_SUBTITLE, bold=True)
        for axis_name in ("capital", "standing", "blood", "world"):
            score = epilogue.axes[axis_name]
            label = f"{axis_name.title()}: {score:.2f}"
            blit_text(surface, f_axis, label, (PAD, y), INK)
            y += f_axis.get_height() + 6

        # Divider
        y += 10
        pygame.draw.line(surface, INK, (PAD, y), (w - PAD, y))
        y += 20

        # Epilogue paragraphs
        f_body = _font(TYPE_BODY)
        line_h = f_body.get_linesize()
        max_w = w - 2 * PAD
        paragraphs = epilogue.text.strip().split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            wrapped = _wrap(para, f_body, max_w)
            for line in wrapped:
                if y + line_h > h - BOTTOM_H - 20:
                    break
                blit_text(surface, f_body, line, (PAD, y), INK)
                y += line_h
            y += 10  # paragraph gap
            if y + line_h > h - BOTTOM_H - 20:
                break

    def _draw_guide(self, surface) -> None:
        """Persistent guide strip above the bottom bar: a teaching statement
        (objective, ender, attention, gold, standing) wrapped to fit, beside a
        single next-step button (group="guide") that a stranger can click."""
        from gilded.ui.actions import next_step
        g, name = self.game, self.house
        y = self._h - BOTTOM_H
        body = _font(TYPE_BODY)
        label, action, hint = next_step(g, name)
        btn = pygame.Rect(self._w - 560, y + 8, 156, 40)
        if btn.x < PAD:
            return
        # Fit the label into the button; trim from the right if too wide.
        while body.size(label)[0] > 138:
            label = label[:-6].rstrip(" ,.:") + "…"
        pygame.draw.rect(surface, GUIDE_BG, btn)
        pygame.draw.rect(surface, GUIDE_EDGE, btn, 2)
        blit_text(surface, body, label,
                  (btn.x + 10, btn.centery - body.size(label)[1] // 2),
                  BUTTON_TEXT)
        self.regions.add(Region(rect=btn,
                                action=action,
                                hint=hint,
                                group="guide",
                                state=RegionState.ENABLED))
    def _guide_text_height(self) -> int:
        """Height of the wrapped guide statement block above the bottom bar."""
        body = _font(TYPE_BODY)
        max_w = self._w - 2 * PAD
        if max_w < 200:
            return 0
        lines = _wrap(guide_statement(), body, max_w)
        line_h = body.get_height() + 4
        return line_h * len(lines) + 12

    def _draw_bottom_bar(self, surface) -> None:
        y = self._h - BOTTOM_H
        pygame.draw.rect(surface, TAB_BG, (0, y, self._w, BOTTOM_H))
        attn = self.game.attention.get(self.house, 0)
        font = _font(TYPE_TEXT, bold=True)
        attn_label = f"Attention: {attn}"
        blit_text(surface, font, attn_label,
                  (PAD, y + (BOTTOM_H - font.size(attn_label)[1]) / 2),
                  ATTN_COLOR)
        from gilded.save import quicksave_path
        save_x = PAD + max(font.size(attn_label)[0], 118) + 14
        for action_key, btn_label in (("quicksave", "Save"),
                                      ("quickload", "Open")):
            disabled = action_key == "quickload" and not os.path.exists(quicksave_path())
            bwidth = font.size(btn_label)[0] + 20
            rect = pygame.Rect(save_x, y + 10, bwidth, BOTTOM_H - 20)
            hint = ("Write the century down so it can be picked up again."
                    if action_key == "quicksave"
                    else "Pick the written-down century up again.")
            if disabled:
                # nothing written down yet: the door is there but shut
                self.regions.add(Region(
                    rect=rect,
                    action={action_key: True},
                    hint=hint,
                    group="chrome",
                    state=RegionState.DISABLED,
                    reason="There is nothing to open yet — put a century down first."))
            else:
                self.regions.add(Region(rect=rect,
                                        action={action_key: True},
                                        hint=hint,
                                        group="chrome"))
            pygame.draw.rect(surface,
                           DISABLED_FILL if disabled else EXEC_BG, rect)
            blit_text(surface, font, btn_label,
                      (rect.centerx - font.size(btn_label)[0] // 2,
                       rect.centery - font.size(btn_label)[1] // 2),
                      DISABLED_TEXT if disabled else TAB_TEXT)
            save_x += bwidth + 8
        narrate_label = f"Narrate: {'on' if self.narrate_on else 'off'}"
        nlabel_w, nlabel_h = font.size(narrate_label)
        nrect = pygame.Rect(self._w - 170 - nlabel_w - 36,
                            y + 10, nlabel_w + 20, BOTTOM_H - 20)
        self._narrate_rect = nrect
        self.regions.add(Region(rect=nrect,
                                action={"toggle_narrate": True},
                                hint="Turn the narrator's prose on or off.",
                                group="chrome"))
        pygame.draw.rect(surface, EXEC_BG, nrect)
        blit_text(surface, font, narrate_label,
                  (nrect.centerx - nlabel_w / 2,
                   nrect.centery - nlabel_h / 2), TAB_TEXT)
        rect = pygame.Rect(self._w - 170, y + 10, 154, BOTTOM_H - 20)
        self._end_turn_rect = rect
        self.regions.add(Region(rect=rect,
                                action={"end_turn": True},
                                hint="Close the session and let the world move.",
                                group="chrome"))
        pygame.draw.rect(surface, ENDTURN_BG, rect)
        blit_text(surface, font, "End Turn",
                  (rect.centerx - font.size("End Turn")[0] / 2,
                   rect.centery - font.size("End Turn")[1] / 2), BUTTON_TEXT)

    # --- the Council briefing ------------------------------------------------

    def _delta_lines(self, d, board) -> List[str]:
        if d.first_session:
            return ["The century opens; there is no prior "
                    "session to weigh against."]
        out: List[str] = []

        def cue(md):
            return "rose" if md.direction > 0 else "fell"

        for name in ("capital", "standing", "blood", "world"):
            md = d.axes[name]
            if md.direction:
                out.append(f"{name.capitalize()} {cue(md)} {figure(md.change)}")
        pairs = (("Legitimacy", d.legitimacy), ("Treasury", d.treasury),
                 ("Tide", d.tide_level), ("Unrest", d.unrest_avg))
        for label, md in pairs:
            if md.direction:
                out.append(f"{label} {cue(md)} {figure(md.change)}")
        if d.rank.direction:
            moved = "improved" if d.rank.change < 0 else "slipped"
            out.append(f"Your standing {moved} to rank #{board.rank}")
        if not out:
            out.append("A quiet turn; nothing of note moved.")
        return out

    def _draw_briefing(self, surface, content: pygame.Rect) -> None:
        board = scoreboard(self.game, self.house)
        d = delta(self.prev_board, board)
        title = _font(TYPE_TITLE, bold=True).render(
            f"COUNCIL BRIEFING - {board.year}", True, INK)
        surface.blit(title, (PAD, content.y + 6))
        y = content.y + 6 + title.get_height() + 8
        head = _font(TYPE_SUBTITLE, bold=True)
        body = _font(TYPE_TEXT)
        width = content.width - 2 * PAD

        blit_text(surface, head, "Since last session", (PAD, y), INK)
        y += head.get_height() + 4
        for line in self._delta_lines(d, board):
            blit_text(surface, body, line, (PAD + 10, y), INK)
            y += body.get_height() + 2
        y += 8

        report = compose(self.game, self.house)
        events = report.gazette[:2] + report.ledger[:2] + report.letters[:1]
        if events:
            blit_text(surface, head, "What the papers say", (PAD, y), INK)
            y += head.get_height() + 4
            for ev in events:
                for line in _wrap(ev, body, width - 10):
                    if y > content.bottom - 170:
                        break
                    blit_text(surface, body, line, (PAD + 10, y), INK)
                    y += body.get_height() + 2
                y += 4
        y += 8
        self._draw_ladder_and_agenda(surface, content, y)

    # --- the public ladder + the docket's agenda (House's ambition banner) --

    def _draw_ladder_and_agenda(self, surface, content: pygame.Rect,
                                y: int, bottom: int = None) -> int:
        """spec §2: the Briefing's ladder and Agenda re-homed to the House
        spine — the ladder stays public, the docket's decisions are the
        agenda cards (its old tab dies; its content lives here and at the
        Atlas desk strip)."""
        head = _font(TYPE_SUBTITLE, bold=True)
        body = _font(TYPE_TEXT)
        bottom = bottom if bottom is not None else content.bottom
        rows = self.game.ladder()
        self._ladder_rows = rows
        if y > bottom - 120:
            return y
        body_h = body.get_height()
        width = content.width - 2 * PAD
        petitions = self.game.docket_by_house.get(self.house, [])
        # The agenda is the spine's action content: reserve its room first so
        # it always draws (its cycle_exec registers), then give the public
        # ladder only the space that remains above it.  On a tall column the
        # ladder keeps all four rows; on a short one it yields rows (and its
        # why-line) so the docket's decisions stay visible.
        if petitions:
            card_h = (6 + _font(TYPE_CAPTION, bold=True).get_height() + 2
                      + len(_wrap(petitions[0].text, body, width - 20))
                      * (body_h + 1) + 2 + 20 + 4)
        else:
            card_h = 0
        # Two section headers + n ladder rows + why-line (only if >=2 rows)
        # + 4px gap + card_h must fit before bottom-10.
        space = (bottom - 10) - y
        ladder_rows = 0
        for n in range(4, 0, -1):
            need = (2 * (head.get_height() + 4)
                    + n * body_h + (body_h if n >= 2 else 0)
                    + 4 + card_h)
            if need <= space:
                ladder_rows = n
                break
        if ladder_rows > 0:
            blit_text(surface, head, "The Ladder", (PAD, y), INK)
            y += head.get_height() + 4
            for row in rows[:ladder_rows]:
                who = row.house + (" (you)" if row.house == self.house else "")
                line = f"{row.rank}. {who}  {row.composite:.0f}"
                blit_text(surface, body, line, (PAD + 10, y),
                          INK if row.rank == 1 else FADED)
                y += body_h
            if ladder_rows >= 2:
                top = rows[0]
                axis = max(top.axes.values(), key=lambda a: a.value)
                if axis.causes:
                    why_line = f"{top.house} leads on {axis.causes[0].label}."
                    blit_text(surface, body, why_line, (PAD + 10, y), FADED)
                    y += body_h
            y += 4

        blit_text(surface, head, "The Agenda", (PAD, y), INK)
        y += head.get_height() + 4
        y = self._draw_petition_cards(surface, content, y)
        return y

    # --- shared petition renderer (Docket + Agenda) --------------------------

    def _draw_petition_cards(self, surface, content: pygame.Rect,
                             y: int) -> int:
        from gilded.docket import DOMAIN_PRIORITY
        petitions = sorted(
            self.game.docket_by_house.get(self.house, []),
            key=lambda p: (DOMAIN_PRIORITY.get(p.domain, 9), p.pid))
        body = _font(TYPE_TEXT)
        small = _font(TYPE_CAPTION, bold=True)
        width = content.width - 2 * PAD
        def _heights(p, force_compact=False):
            lines = _wrap(p.text, body, width - 20)
            # Header + wrapped text + wrapped button rows (height 20 each) +
            # padding.  The button row wraps inside the column width so the
            # options never spill into the right column (dials / intrigue).
            avail = width - 20
            bw_list = [small.render(opt.text, True, BUTTON_TEXT).get_width()
                       + 20 for opt in p.options]
            ex_pre = self._chosen_executor(p.pid)
            ex_name_pre = ("executor: default" if ex_pre is None
                           else f"executor: {ex_pre.name}")
            ew = small.render(ex_name_pre, True, BUTTON_TEXT).get_width() + 20
            n_btn_rows, cur = 1, 0
            for bw in bw_list + [ew]:
                if cur and cur + 8 + bw > avail:
                    n_btn_rows += 1
                    cur = bw
                else:
                    cur += 8 + bw
            n_opt_rows, cur = 1, 0
            for bw in bw_list:
                if cur and cur + 8 + bw > avail:
                    n_opt_rows += 1
                    cur = bw
                else:
                    cur += 8 + bw
            full_h = (6 + small.get_height() + 2
                      + len(lines) * (body.get_height() + 1)
                      + 2 + n_btn_rows * 20 + (n_btn_rows - 1) * 4 + 4)
            compact_h = (6 + small.get_height() + 2
                         + 2 + n_opt_rows * 20 + (n_opt_rows - 1) * 4 + 4)
            return (lines, bw_list, ex_pre, ex_name_pre, ew,
                    full_h, compact_h, force_compact)

        def _fits(h, yy, limit):
            card_h = h[5]
            compact = h[7]
            if not compact and yy + card_h > limit:
                compact_h = h[6]
                if yy + compact_h > limit:
                    return None
                card_h, compact = compact_h, True
            return card_h, compact

        limit = content.bottom - 10
        layouts = []
        dropped = False
        yy = y
        for p in petitions:
            h = _heights(p)
            res = _fits(h, yy, limit)
            if res is None:
                dropped = True
                break
            card_h, compact = res
            layouts.append((p, h, card_h, compact))
            yy += card_h + 6
        if dropped:
            # A chain petition is the desk's most urgent paper: never let one
            # fall off the band. Retry the whole stack in the compact form
            # (header + option buttons only) so the rule regions stay
            # pressable.
            layouts = []
            yy = y
            for p in petitions:
                h = _heights(p, force_compact=True)
                res = _fits(h, yy, limit)
                if res is None:
                    break
                card_h, compact = res
                layouts.append((p, h, card_h, compact))
                yy += card_h + 6
        for p, (lines, bw_list, ex_pre, ex_name_pre, ew,
                _full_h, _compact_h, _fc), card_h, compact in layouts:
            card = pygame.Rect(PAD, y, width, card_h)
            pygame.draw.rect(surface, CARD_BG, card)
            pygame.draw.rect(surface, CARD_EDGE, card, 1)
            hy = y + 6
            blit_text(surface, small, f"[{p.domain}] {p.kind}", (PAD + 10, hy), FADED)
            hy += small.get_height() + 2
            if not compact:
                for line in lines:
                    blit_text(surface, body, line, (PAD + 10, hy), INK)
                    hy += body.get_height() + 1
            bx = PAD + 10
            by = hy + 2
            max_x = PAD + width - 10
            for opt in p.options:
                blabel = small.render(opt.text, True, BUTTON_TEXT)
                bw = blabel.get_width() + 20
                if bx + bw > max_x:
                    bx = PAD + 10
                    by += 24
                brect = pygame.Rect(bx, by, bw, 20)
                pygame.draw.rect(surface, BUTTON_BG, brect)
                pygame.draw.rect(surface, BUTTON_EDGE, brect, 1)
                blit_text(surface, small, opt.text, (brect.x + 10, brect.y + 5),
                         BUTTON_TEXT)
                exec_id = None if ex_pre is None else ex_pre.id
                self._option_hits.append(
                    (brect, ("rule", p.pid, opt.key, exec_id)))
                self.regions.add(Region(rect=brect,
                                        action={"rule": (p.pid, opt.key, exec_id)},
                                        hint=opt.text,
                                        group=f"petition:{p.pid}"))
                bx += bw + 8
            if not compact:
                ex = ex_pre
                ex_name = ex_name_pre
                if bx + ew > max_x:
                    bx = PAD + 10
                    by += 24
                erect = pygame.Rect(bx, by, ew, 20)
                pygame.draw.rect(surface, EXEC_BG, erect)
                pygame.draw.rect(surface, BUTTON_EDGE, erect, 1)
                blit_text(surface, small, ex_name, (erect.x + 10, erect.y + 5),
                          BUTTON_TEXT)
                self._exec_hits.append((erect, p.pid))
                self.regions.add(Region(rect=erect,
                                        action={"cycle_exec": p.pid},
                                        hint="Choose who carries out this ruling.",
                                        group=f"petition:{p.pid}"))
            y += card_h + 6
        return y

    def _draw_paper(self, surface, content: pygame.Rect,
                    section: str = None) -> None:
        # Paper sections are the desk/archive axis, not the spine: the spine
        # alone has no paper section, so fall back to the desk default.
        section = section or self.paper_section or "Gazette"
        report = compose(self.game, self.house)
        if self.narrate_on and section == "Gazette":
            report = self.narrator.render(report, self.game.director, self.game)
        items = {"Gazette": report.gazette, "Ledger": report.ledger,
                 "Letters": report.letters}[section]
        head_font = _font(TYPE_TITLE, bold=True)
        head = head_font.render(
            f"THE {section.upper()} - {report.year}", True, INK)
        surface.blit(head, (PAD, content.y + 6))
        # Horizontal rule under the head, in the gap before body text
        rule_y = content.y + 6 + head.get_height() + 4
        pygame.draw.line(surface, INK,
                         (PAD, rule_y),
                         (content.width - PAD, rule_y), 1)
        body = _font(TYPE_TEXT)
        # Content area for columns: below the rule
        body_top = rule_y + 6
        body_rect = pygame.Rect(content.x, body_top,
                                content.width, content.bottom - body_top)
        if not items:
            items = ["(nothing to report)"]

        result = flow_columns(items, body, body_rect, line_gap=4)

        for (text, x, y, _ci) in result.placements:
            blit_text(surface, body, text, (x, y), INK)

        # Continuation marker when overflow > 0
        if result.overflow > 0:
            marker_text = f"+ {result.overflow} more"
            marker = body.render(marker_text, True, FADED)
            # Place marker at bottom of last column that has content
            last_ci = max(p[3] for p in result.placements) if result.placements else 0
            cols = column_plan(body_rect, body)
            mx = cols[last_ci].x
            my = content.bottom - marker.get_height() - 8
            surface.blit(marker, (mx, my))

    def _draw_ledger(self, surface, content: pygame.Rect) -> None:
        """Draw the Ledger tab: financial page built on the house journal."""
        g, name = self.game, self.house
        resolved_turn = g.turn - 1
        report = compose(g, name)
        notices = tuple(report.ledger) if report.ledger else ()
        house = g.houses[name]
        model = ledger_model(house, resolved_turn, notices)

        surface.set_clip(content)
        f_title = _font(TYPE_HEADING, bold=True)
        f_body = _font(TYPE_BODY)
        f_small = _font(TYPE_CAPTION)
        y = content.y + 8
        bottom = content.bottom
        overflow_items = 0

        # Title
        title = f_title.render("LEDGER", True, INK)
        surface.blit(title, (PAD, y))
        y += title.get_height() + 6

        # Turn and treasury line
        turn_line = f_body.render(
            f"Turn {model.turn}  |  Treasury: {gold(model.treasury)} gold",
            True, INK,
        )
        surface.blit(turn_line, (PAD, y))
        y += turn_line.get_height() + 10

        # Totals bar
        totals_text = f_body.render(
            totals_line(model),
            True, INK,
        )
        surface.blit(totals_text, (PAD, y))
        y += totals_text.get_height() + 8

        # Horizontal rule
        pygame.draw.line(surface, INK,
                         (PAD, y),
                         (content.width - PAD, y))
        y += 10

        # Flows table
        if model.rows:
            cols = [Column("Label", width=2.0, align="left"),
                    Column("Amount", width=1.0, align="right")]
            data = [[r.label, money(r.amount)] for r in model.rows]
            tbl = Table(cols, data, size=TYPE_BODY)
            tbl_h = tbl.height()
            tbl_rect = pygame.Rect(PAD, y, content.width - 2 * PAD, tbl_h)
            tbl_layout = tbl.layout(tbl_rect)

            # Draw table header
            f_h = _font(tbl.size, bold=True)
            for i, col in enumerate(tbl.cols):
                txt = f_h.render(col.header, True, INK)
                text_rect = tbl_layout.header_text_rects[i]
                surface.blit(txt, text_rect)

            # Draw rule
            pygame.draw.line(surface, INK,
                             (tbl_rect.left, tbl_layout.rule_y),
                             (tbl_rect.right, tbl_layout.rule_y))

            # Draw rows (check each row fits)
            f_b = _font(tbl.size)
            drawn_rows = 0
            for row_idx, row in enumerate(tbl.data):
                row_bottom = tbl_layout.cell_rects[row_idx][0].bottom
                if row_bottom > bottom:
                    overflow_items += len(tbl.data) - row_idx
                    break
                for col_idx, cell in enumerate(row):
                    cell_rect = tbl_layout.cell_rects[row_idx][col_idx]
                    text_rect = tbl_layout.text_rects[row_idx][col_idx]
                    txt = f_b.render(cell, True, INK)
                    surface.blit(txt, text_rect)
                drawn_rows += 1
            if drawn_rows > 0:
                y = tbl_layout.cell_rects[drawn_rows - 1][0].bottom + 10
            else:
                y = tbl_layout.rule_y + 10
        else:
            # Empty turn placeholder
            placeholder = f_small.render("No financial activity this turn.", True, FADED)
            surface.blit(placeholder, (PAD, y))
            y += placeholder.get_height() + 10

        # History table
        if model.history and y < bottom:
            hist_title = f_title.render("HISTORY", True, INK)
            hist_title_h = hist_title.get_height() + 6
            if y + hist_title_h < bottom:
                surface.blit(hist_title, (PAD, y))
                y += hist_title_h

            h_cols = [Column("Turn", width=0.8, align="right"),
                      Column("Income", width=1.0, align="right"),
                      Column("Outlay", width=1.0, align="right"),
                      Column("Net", width=1.0, align="right")]
            h_data = [history_cells(tl) for tl in model.history]
            h_tbl = Table(h_cols, h_data, size=TYPE_CAPTION)
            h_tbl_h = h_tbl.height()
            h_tbl_rect = pygame.Rect(PAD, y, content.width - 2 * PAD, h_tbl_h)
            h_tbl_layout = h_tbl.layout(h_tbl_rect)

            f_h = _font(h_tbl.size, bold=True)
            for i, col in enumerate(h_tbl.cols):
                txt = f_h.render(col.header, True, INK)
                text_rect = h_tbl_layout.header_text_rects[i]
                surface.blit(txt, text_rect)

            pygame.draw.line(surface, INK,
                             (h_tbl_rect.left, h_tbl_layout.rule_y),
                             (h_tbl_rect.right, h_tbl_layout.rule_y))

            f_b = _font(h_tbl.size)
            drawn_rows = 0
            for row_idx, row in enumerate(h_tbl.data):
                row_bottom = h_tbl_layout.cell_rects[row_idx][0].bottom
                if row_bottom > bottom:
                    overflow_items += len(h_tbl.data) - row_idx
                    break
                for col_idx, cell in enumerate(row):
                    cell_rect = h_tbl_layout.cell_rects[row_idx][col_idx]
                    text_rect = h_tbl_layout.text_rects[row_idx][col_idx]
                    txt = f_b.render(cell, True, INK)
                    surface.blit(txt, text_rect)
                drawn_rows += 1
            if drawn_rows > 0:
                y = h_tbl_layout.cell_rects[drawn_rows - 1][0].bottom + 10
            else:
                y = h_tbl_layout.rule_y + 10
        elif model.history:
            overflow_items += len(model.history)

        # Summary table
        if model.summary and y < bottom:
            sum_title = f_title.render("SUMMARY", True, INK)
            sum_title_h = sum_title.get_height() + 6
            if y + sum_title_h < bottom:
                surface.blit(sum_title, (PAD, y))
                y += sum_title_h

            s_cols = [Column("Label", width=2.0, align="left"),
                      Column("Amount", width=1.0, align="right")]
            s_data = [[r.label, money(r.amount)] for r in model.summary]
            s_tbl = Table(s_cols, s_data, size=TYPE_BODY)
            s_tbl_h = s_tbl.height()
            s_tbl_rect = pygame.Rect(PAD, y, content.width - 2 * PAD, s_tbl_h)
            s_tbl_layout = s_tbl.layout(s_tbl_rect)

            f_h = _font(s_tbl.size, bold=True)
            for i, col in enumerate(s_tbl.cols):
                txt = f_h.render(col.header, True, INK)
                text_rect = s_tbl_layout.header_text_rects[i]
                surface.blit(txt, text_rect)

            pygame.draw.line(surface, INK,
                             (s_tbl_rect.left, s_tbl_layout.rule_y),
                             (s_tbl_rect.right, s_tbl_layout.rule_y))

            f_b = _font(s_tbl.size)
            drawn_rows = 0
            for row_idx, row in enumerate(s_tbl.data):
                row_bottom = s_tbl_layout.cell_rects[row_idx][0].bottom
                if row_bottom > bottom:
                    overflow_items += len(s_tbl.data) - row_idx
                    break
                for col_idx, cell in enumerate(row):
                    cell_rect = s_tbl_layout.cell_rects[row_idx][col_idx]
                    text_rect = s_tbl_layout.text_rects[row_idx][col_idx]
                    txt = f_b.render(cell, True, INK)
                    surface.blit(txt, text_rect)
                drawn_rows += 1
            if drawn_rows > 0:
                y = s_tbl_layout.cell_rects[drawn_rows - 1][0].bottom + 10
            else:
                y = s_tbl_layout.rule_y + 10
        elif model.summary:
            overflow_items += len(model.summary)

        # Notices
        if model.notices and y < bottom:
            notice_title = f_title.render("NOTICES", True, INK)
            notice_title_h = notice_title.get_height() + 6
            if y + notice_title_h < bottom:
                surface.blit(notice_title, (PAD, y))
                y += notice_title_h

            for notice in model.notices:
                if notice:
                    n_surf = f_small.render(notice, True, INK)
                    if y + n_surf.get_height() > bottom:
                        overflow_items += 1
                        break
                    surface.blit(n_surf, (PAD, y))
                    y += n_surf.get_height() + 3
        elif model.notices:
            overflow_items += len([n for n in model.notices if n])

        # Overflow marker — always placed at the bottom of the content area
        if overflow_items > 0:
            marker = f_small.render(f"+ {overflow_items} more", True, FADED)
            my = bottom - marker.get_height() - 4
            if my >= content.y:
                surface.blit(marker, (PAD, my))

        surface.set_clip(None)

    def _draw_docket(self, surface, content: pygame.Rect) -> None:
        title = _font(TYPE_TITLE, bold=True).render("THE DOCKET", True, INK)
        surface.blit(title, (PAD, content.y + 6))
        y = content.y + 6 + title.get_height() + 10
        self._draw_petition_cards(surface, content, y)

    def _draw_policies(self, surface, content, y: int = None,
                        bottom: int = None) -> int:
        from gilded import policy
        from gilded.society import labor
        from gilded.directives import (DIRECTIVE_KEYS, DIRECTIVE_CONVICTION,
                                        friction, FRICTION_THRESHOLD)
        from gilded.docket import DOMAIN_SEAT

        POLES = {
            "capital": ("traditionalist", "industrialist"),
            "labor": ("protective", "extractionist"),
            "expansion": ("consolidation", "expansionism"),
            "diplomacy": ("nationalist", "cosmopolitan"),
            "war": ("pacifist", "militarist"),
        }
        h = self.house
        eff = policy.effects(self.game, h)
        directives = self.game.directives[h]
        realm = self.game.realms[h]
        title = _font(TYPE_SUBTITLE, bold=True)
        label = _font(TYPE_TEXT, bold=True)
        small = _font(TYPE_BODY)
        x = content.x + PAD
        w = content.width - 2 * PAD
        if y is None:
            y = content.y + PAD
        if bottom is not None and y > bottom - 120:
            return y
        blit_text(surface, title, "Standing Policy", (x, y), INK)
        y += title.get_height() + 12
        track_w = w - 240
        for key in DIRECTIVE_KEYS:
            if bottom is not None and y > bottom - 24:
                break
            left, right = POLES[key]
            stance = directives.stances.get(key, 0)
            # label row
            blit_text(surface, label, f"{left}", (x, y), FADED)
            blit_text(surface, label, right, (x + track_w - label.size(right)[0], y), FADED)
            sign = f"(+{stance})" if stance > 0 else f"({stance})"
            blit_text(surface, label, sign, (x + track_w + 16, y), INK)
            y += label.get_height() + 6
            # track + marker
            track_y = y + 8
            pygame.draw.line(surface, CARD_EDGE, (x, track_y),
                             (x + track_w, track_y), 3)
            frac = (stance + 100) / 200.0
            mx = int(x + frac * track_w)
            pygame.draw.circle(surface, INK, (mx, track_y), 7)
            track_rect = pygame.Rect(x, track_y - 12, track_w, 24)
            left, right = POLES[key]
            self._dial_hits.append((track_rect, key))
            self.regions.add(Region(rect=track_rect,
                                    action={"set_stance": (key, None)},
                                    hint=f"Set your stance on {key}: {left} vs {right}.",
                                    group="policy"))
            y += 22
            # live effect line (displayed == applied)
            if key == "labor":
                lvl = eff.extraction_level
                line = (f"extraction {lvl} · dividends x"
                        f"{labor.dividend_multiplier(lvl):.2f} · output x"
                        f"{labor.production_multiplier(lvl):.2f} · unrest +"
                        f"{labor.unrest_gain(lvl):.1f}/turn")
            elif key == "capital":
                line = (f"output x{eff.output_mod:.2f} · build x"
                        f"{eff.build_speed_mod:.2f}")
            elif key == "expansion":
                line = (f"expansion cost x{eff.expand_cost_mod:.2f} · unrest +"
                        f"{max(0.0, eff.unrest_add):.1f}/turn")
            elif key == "war":
                line = (f"strength x{eff.strength_mod:.2f} · happiness "
                        f"{eff.happiness_mod:+.1f}")
            else:  # diplomacy
                line = (f"relations {eff.relations_drift:+.1f}/turn · trade +"
                        f"{eff.trade_income:.1f} · legitimacy "
                        f"{eff.legitimacy_mod:+.1f}")
            blit_text(surface, small, line, (x, y), INK)
            y += small.get_height() + 4
            # friction flag
            seat = realm.court.positions.get(DOMAIN_SEAT[key])
            if seat is not None and getattr(seat, "is_alive", False):
                conviction = seat.dispositions.get(DIRECTIVE_CONVICTION[key], 0.0)
                if friction(stance, conviction) > 0:
                    turns = directives.friction_turns.get(key, 0)
                    flag = (f"! {seat.name} leans "
                            f"{left if conviction < 0 else right} — straining "
                            f"{turns}/4")
                    blit_text(surface, small, flag, (x, y), FADED)
                    y += small.get_height() + 4
            y += 16
        return y

    def _draw_atlas(self, surface, rect: pygame.Rect = None) -> None:
        if rect is None:
            hud_h = _hud_height()
            rect = pygame.Rect(0, TAB_H + hud_h, self._w,
                               self._h - TAB_H - hud_h - BOTTOM_H)
        self._atlas_polys = draw_atlas(surface, self.game, rect, self.selected_pid,
                                       accent_log=self._accent_log)
        self.regions.add(Region(rect=rect,
                                action={"select_province": None},
                                hint="Click a province to inspect it.",
                                group="atlas"))
        if self.selected_pid is not None:
            self._draw_panel(surface,
                             province_panel_lines(self.game, self.selected_pid))
        # Draw action rows on the right side panel
        self._draw_atlas_actions(surface, rect)

    def _draw_atlas_actions(self, surface, rect: pygame.Rect) -> None:
        """Draw interactive rows for acquire_minor, build_rail, tour_province on the atlas tab."""
        from gilded.world import MINOR_OWNER
        from gilded.docket import RAIL_COST
        from gilded.ui.actions import ACTIONS
        BUTTON_H = 26
        game = self.game
        house = self.house
        atlas = game.atlas
        house_obj = game.houses[house]

        def _draw_btn(surf, text, btn_rect, enabled):
            if enabled:
                bg, edge = BUTTON_BG, BUTTON_EDGE
            else:
                bg, edge = DISABLED_BUTTON_BG, DISABLED_BUTTON_EDGE
            pygame.draw.rect(surf, bg, btn_rect)
            pygame.draw.rect(surf, edge, btn_rect, 2)
            blit_text(surf, _font(TYPE_TEXT), text,
                      (btn_rect.x + 8, btn_rect.y + 4), BUTTON_TEXT)

        panel_x = rect.right - 260
        panel_w = 250
        # Start below the War toggle button (top+8, 30 px tall) so the panel
        # title never collides with it.
        y = rect.top + 46

        body = _font(TYPE_TEXT)
        title = _font(TYPE_CAPTION, bold=True)

        # Title
        blit_text(surface, title, "PEACE TIME ACTIONS", (panel_x + 4, y), INK)
        y += title.get_height() + 6

        # Separator
        pygame.draw.line(surface, INK, (panel_x, y), (panel_x + panel_w, y))
        y += 8

        # --- Acquire Minor section ---
        blit_text(surface, body, "Acquire Minor:", (panel_x + 4, y), INK)
        y += body.get_height() + 2

        # Find bordering minors
        owned = {p.pid for p in atlas.provinces.values() if p.owner == house}
        bordering_minors = []
        for pid, prov in atlas.provinces.items():
            if prov.owner == MINOR_OWNER and prov.neighbors & owned:
                bordering_minors.append(pid)
        bordering_minors.sort(key=lambda pid: atlas.provinces[pid].name)

        for pid in bordering_minors:
            if y + BUTTON_H > rect.bottom:
                break
            prov = atlas.provinces[pid]
            richness = sum(prov.endowments.values())
            cost = 300.0 * prov.development + 100.0 * richness
            action_dict = {"acquire_minor": pid}
            act = ACTIONS.get("acquire_minor")
            ok, reason = act.eligible(game, house, action_dict) if act else (False, "Unknown action")

            btn_label = f"{prov.name} ({cost:.0f}g)"
            btn_rect = pygame.Rect(panel_x + 4, y, panel_w - 8, BUTTON_H)
            _draw_btn(surface, btn_label, btn_rect, ok)

            state = RegionState.ENABLED if ok else RegionState.DISABLED
            self.regions.add(Region(
                rect=btn_rect,
                action=action_dict,
                hint=btn_label if ok else reason,
                reason=reason if not ok else None,
                state=state,
                group="atlas_actions",
            ))
            y += BUTTON_H + 2

        y += 4

        # --- Build Rail section ---
        blit_text(surface, body, "Build Rail:", (panel_x + 4, y), INK)
        y += body.get_height() + 2

        # Find rail-less links between owned provinces
        rail_links = []
        for link in atlas.links.values():
            if not link.rail and link.a in owned and link.b in owned:
                pa = atlas.provinces[link.a].name
                pb = atlas.provinces[link.b].name
                rail_links.append((link.a, link.b, pa, pb))
        rail_links.sort(key=lambda t: t[2] + t[3])

        for a, b, pa, pb in rail_links:
            if y + BUTTON_H > rect.bottom:
                break
            action_dict = {"build_rail": True, "build_rail_a": a, "build_rail_b": b}
            act = ACTIONS.get("build_rail")
            ok, reason = act.eligible(game, house, action_dict) if act else (False, "Unknown action")

            btn_label = f"{pa}-{pb} ({RAIL_COST:.0f}g)"
            btn_rect = pygame.Rect(panel_x + 4, y, panel_w - 8, BUTTON_H)
            _draw_btn(surface, btn_label, btn_rect, ok)

            state = RegionState.ENABLED if ok else RegionState.DISABLED
            self.regions.add(Region(
                rect=btn_rect,
                action=action_dict,
                hint=btn_label if ok else reason,
                reason=reason if not ok else None,
                state=state,
                group="atlas_actions",
            ))
            y += BUTTON_H + 2

        y += 4

        # --- Tour Province section ---
        blit_text(surface, body, "Tour Province:", (panel_x + 4, y), INK)
        y += body.get_height() + 2

        # Find owned provinces
        owned_provinces = [(pid, atlas.provinces[pid])
                           for pid in owned]
        owned_provinces.sort(key=lambda t: t[1].name)

        for pid, prov in owned_provinces:
            if y + BUTTON_H > rect.bottom:
                break
            action_dict = {"tour_province": pid}
            act = ACTIONS.get("tour_province")
            ok, reason = act.eligible(game, house, action_dict) if act else (False, "Unknown action")

            unrest_str = f"unrest={prov.unrest:.1f}"
            btn_label = f"{prov.name} ({unrest_str})"
            btn_rect = pygame.Rect(panel_x + 4, y, panel_w - 8, BUTTON_H)
            _draw_btn(surface, btn_label, btn_rect, ok)

            state = RegionState.ENABLED if ok else RegionState.DISABLED
            self.regions.add(Region(
                rect=btn_rect,
                action=action_dict,
                hint=btn_label if ok else reason,
                reason=reason if not ok else None,
                state=state,
                group="atlas_actions",
            ))
            y += BUTTON_H + 2

    def _draw_panel(self, surface, lines: List[str]) -> None:
        font = _font(TYPE_TEXT)
        w = max(font.size(l)[0] for l in lines) + 2 * PAD
        h = len(lines) * (font.get_height() + 2) + 2 * PAD
        rect = pygame.Rect(self._w - w - PAD, TAB_H + _hud_height() + PAD, w, h)
        panel = pygame.Surface(rect.size)
        panel.set_alpha(225)
        panel.fill(PANEL_BG)
        surface.blit(panel, rect.topleft)
        y = rect.y + PAD
        for i, line in enumerate(lines):
            f = _font(TYPE_TEXT, bold=True) if i == 0 else font
            blit_text(surface, f, line, (rect.x + PAD, y), TAB_TEXT)
            y += font.get_height() + 2

    def powers_lines(self) -> List[str]:
        """One line per rival House, ordered by threat to the player: the
        House, its earned intel tier, the sources, and whatever intent that
        tier reveals."""
        lines: List[str] = []
        for h in threat_rank(self.game):
            r = intel_report(self.game, self.house, h)
            src = f" [{', '.join(r.breakdown)}]" if r.breakdown else ""
            lines.append(
                f"House {h}  (intel {r.tier}/3){src}  -  {r.apparent_intent}")
        return lines

    def _draw_powers(self, surface, content) -> None:
        """Draw the Powers spine: model -> layout -> draw.  The selected
        rival/Order (self._powers_selected) is highlighted and its dossier
        opens on the inner page."""
        g, name = self.game, self.house
        lines = powers_report(g, name)
        model = powers_model(lines, selected=self._powers_selected)
        layout = powers_layout(model, content)

        title_rect = layout["title"]
        tbl_rect = layout["table"]
        detail_rect = layout["detail"]

        # Title
        f_title = _font(TYPE_HEADING, bold=True)
        blit_text(surface, f_title, "THE POWERS", (title_rect.left, title_rect.top), INK)

        # Table
        tbl = model.table
        tbl_layout = tbl.layout(tbl_rect)

        # Draw header
        f_h = _font(tbl.size, bold=True)
        for i, col in enumerate(tbl.cols):
            if i < len(tbl_layout.header_rects):
                h_rect = tbl_layout.header_rects[i]
                text_rect = tbl_layout.header_text_rects[i]
                blit_text(surface, f_h, col.header, text_rect.topleft, INK)

        # Draw rule
        pygame.draw.line(surface, INK,
                         (tbl_rect.left, tbl_layout.rule_y),
                         (tbl_rect.right, tbl_layout.rule_y))

        # Draw rows
        f_b = _font(tbl.size)
        from gilded.ui.widgets import TONES
        for ri, row in enumerate(tbl.data):
            if ri >= len(tbl_layout.row_rects):
                break
            row_rect = tbl_layout.row_rects[ri]
            for ci, cell in enumerate(row):
                if ci >= len(tbl_layout.cell_rects[ri]):
                    continue
                cell_rect = tbl_layout.cell_rects[ri][ci]
                text_rect = tbl_layout.text_rects[ri][ci]
                blit_text(surface, f_b, cell, text_rect.topleft, INK)

        # Overflow warning
        if model.overflow_name is not None:
            blit_text(surface, f_b, f"⚠ {model.overflow_name}",
                      (tbl_rect.left, tbl_rect.bottom + 4), TONES.get("warn", INK))

        # Empty roster message
        if not lines:
            empty_text = model.texts.get("empty", "(no rival House stands against you)")
            blit_text(surface, f_b, empty_text, (detail_rect.left + 8, detail_rect.top + 4), INK)

        # Informant buttons
        self._informant_hits.clear()
        btn_rect = layout["buttons"]
        btn_y = btn_rect.top
        for ri in model.informant_rows:
            house = model.row_houses[ri]
            btn_label = f"Place informant: {house}"
            btn_w, btn_h = f_b.size(btn_label)
            btn_x = btn_rect.left + 8
            btn_r = pygame.Rect(btn_x, btn_y, btn_w + 12, btn_h + 4)
            pygame.draw.rect(surface, CARD_BG, btn_r)
            pygame.draw.rect(surface, CARD_EDGE, btn_r, 1)
            blit_text(surface, f_b, btn_label, (btn_r.left + 6, btn_r.top + 2), INK)
            self._informant_hits.append((btn_r, {"place_informant": house}))
            self.regions.add(Region(rect=btn_r,
                                    action={"place_informant": house},
                                    hint=f"Place an informant inside {house}.",
                                    group="powers"))
            btn_y += btn_h + 4

    def enterprises_lines(self) -> List[str]:
        """Return the Grip banner lines for the Enterprises tab."""
        g, name = self.game, self.house
        r = grip_report(g, name)
        lines = []
        # Grip band (A1: display as words a player reads, not enum spelling)
        band_display = r.band.replace("_", " ")
        # A2: margin between stake and threshold
        lines.append(
            f"Grip: {band_display}  —  stake {r.controlling_stake:.1f}% "
            f"vs threshold {r.threshold:.1f}%  —  margin {r.margin:.1f}%"
        )
        # Top predator
        if r.top_predator is not None:
            pred = r.top_predator
            kin = ""
            # Check if the predator is kin (belongs to the same house)
            realm = g.realms.get(name)
            if realm is not None:
                for char in realm.characters:
                    if char.id == pred.id:
                        kin = " (kin)"
                        break
            # A3: what the predator still needs to reach threshold
            shortfall = r.threshold - pred.stake
            lines.append(
                f"Top predator: {pred.name} ({pred.stake:.1f}%, needs {shortfall:.1f}% more){kin}"
            )
        else:
            lines.append("Top predator: none")
        # Market ticker
        ticker_parts = []
        for commodity in COMMODITIES:
            price = g.market.price(commodity)
            d = g.market.delta(commodity)
            if d is None:
                ticker_parts.append(f"{commodity} {price:.2f}")
            # A4: tolerance of 1e-9 on either side of zero
            elif d > 1e-9:
                ticker_parts.append(f"{commodity} {price:.2f} rising")
            elif d < -1e-9:
                ticker_parts.append(f"{commodity} {price:.2f} falling")
            else:
                ticker_parts.append(f"{commodity} {price:.2f} steady")
        lines.append(" | ".join(ticker_parts))
        # Venture count
        lines.append(f"Enterprises: {len(r.enterprises)}")
        # Per-venture ledger rows
        for el in r.enterprises:
            # Director name or "vacant"
            if el.director is not None:
                dir_label = el.director.name
            else:
                dir_label = "vacant"
            # Skim marker — use the row's own disloyal flag, not the name
            skim = " [skim]" if (el.director is not None and el.director.disloyal) else ""
            # Dividend delta
            if el.dividend_delta is None:
                delta_str = "new"
            else:
                sign = "+" if el.dividend_delta >= 0 else "-"
                delta_str = f"{sign}{abs(el.dividend_delta):.1f}"
            # Top outside holder — resolve ID to name
            if el.top_outside is not None:
                outside_id, outside_pct = el.top_outside
                outside_name = _name_for(g, outside_id)
                outside_str = f"{outside_name} {outside_pct:.1f}%"
            else:
                outside_str = "none"
            lines.append(
                f"  {el.name} | {el.sector} | tier {el.tier} | "
                f"div {el.dividend:.1f} ({delta_str}) | "
                f"dir: {dir_label}{skim} | "
                f"stake: {el.your_stake:.1f}% | "
                f"top outside: {outside_str}"
            )
        return lines

    def enterprise_actions(self) -> List[dict]:
        g = self.game
        r = grip_report(g, self.house)
        from gilded.society.schemes import share_price
        actions = []
        # Per-venture actions
        for el in r.enterprises:
            eid = el.eid
            actions.append({"label": f"Expand {el.name}", "action": {"expand_enterprise": eid}, "eid": eid})
            actions.append({"label": f"Appoint Director for {el.name}", "action": {"appoint_director": eid}, "eid": eid})
            actions.append({"label": f"Buy Shares in {el.name}", "action": {"buy_shares": eid}, "eid": eid})
            actions.append({"label": f"Sell Shares in {el.name}", "action": {"sell_shares": eid}, "eid": eid})
        # Found enterprise (page-level)
        from gilded.ui.actions import _get_available_charters
        charters = _get_available_charters(self.game, self.house)
        actions.append({"label": f"Found Enterprise ({len(charters)} charters)", "action": {"found_enterprise": True}, "eid": None})
        # Defend buyouts — for each venture with outside holders
        for el in r.enterprises:
            if el.top_outside is not None:
                outside_id, outside_pct = el.top_outside
                ent = next((e for e in g.enterprises if e.eid == el.eid), None)
                if ent is not None:
                    price = _buyout_price(ent, outside_id, g)
                    actions.append({
                        "label": f"Buy out {_name_for(g, outside_id)}'s stake in {el.name}",
                        "action": {"defend_buyout": (el.eid, outside_id)},
                        "eid": el.eid,
                        "price": price
                    })
        # Attack takeover — targeting the top threat
        threats = threat_rank(g)
        if threats:
            target_house = threats[0]
            from gilded.ui.actions import _running_takeover, _takeover_reach
            from gilded.society.schemes import TAKEOVER_THRESHOLD
            from gilded.society.shares import house_stake
            running = _running_takeover(g, self.house, target_house)
            if running is None:
                label = (f"Hostile Takeover of {target_house} — "
                         f"{_takeover_reach(g, target_house):.1f}% for sale, "
                         f"{TAKEOVER_THRESHOLD:.0f}% needed")
            else:
                held = house_stake(
                    [e for e in g.enterprises if e.house == target_house],
                    running.buyer.id)
                label = (f"Takeover of {target_house} — holding "
                         f"{held:.1f}% of {TAKEOVER_THRESHOLD:.0f}% needed")
            actions.append({
                "label": label,
                "action": {"attack_takeover": target_house},
                "eid": None
            })
        return actions

    def _action_button(self, surface, content, action_rect, y, act, body, group, default_label, reason=None, hit_list=None, fill=None, edge=None):
        """Draw a single action button.  Returns next `y`, or `None` if content would overflow."""
        if fill is None:
            fill = DISABLED_BUTTON_BG if reason else BUTTON_BG
        if edge is None:
            edge = DISABLED_BUTTON_EDGE if reason else BUTTON_EDGE
        btn_text = act.get("label", default_label)
        text_color = BUTTON_TEXT
        btn_surf = body.render(btn_text, True, text_color)
        btn_w = btn_surf.get_width() + 16
        btn_h = body.get_height() + 8
        btn_rect = pygame.Rect(action_rect.left, y, btn_w, btn_h)
        if y + btn_h > content.bottom:
            return None
        pygame.draw.rect(surface, fill, btn_rect)
        pygame.draw.rect(surface, edge, btn_rect, 2)
        surface.blit(btn_surf, (action_rect.left + 8, y + 4))
        if reason:
            self.regions.add(Region(rect=btn_rect, action=act.get("action", act), state=RegionState.DISABLED, reason=reason, group=group))
        else:
            if hit_list is not None:
                hit_list.append((btn_rect, act))
            self.regions.add(Region(rect=btn_rect, action=act.get("action", act), hint=act.get("label", ""), group=group))
        return y + btn_h + 4

    def _draw_enterprises(self, surface, content) -> None:
        """Draw the Enterprises tab: model → layout → draw."""
        g, name = self.game, self.house
        r = grip_report(g, name)
        model = enterprises_model(r)
        layout = enterprises_layout(model, content)

        chip_rect = layout["chip"]
        meter_rect = layout["meter"]
        tbl_rect = layout["table"]
        action_rect = layout["action"]

        # Band chip
        model.band_chip.draw(surface, (chip_rect.left, chip_rect.top))

        # Margin meter — draw as a bar
        from gilded.ui.widgets import TONES
        meter = model.margin_meter
        f = _font(meter.size)
        label_surf = f.render(f"{meter.label}: {meter.value_text()}%", True, INK)
        surface.blit(label_surf, (meter_rect.left, meter_rect.top))
        bar_h = 8
        bar_y = meter_rect.top + meter_rect.height - bar_h
        bar_rect = pygame.Rect(meter_rect.left + label_surf.get_width() + 8, bar_y,
                               meter_rect.width - label_surf.get_width() - 12, bar_h)
        pygame.draw.rect(surface, CARD_EDGE, bar_rect)
        frac = meter.fraction()
        fill_w = max(2, int(bar_rect.width * frac))
        tone = meter.tone()
        fill_color = TONES.get(tone, INK) if tone in TONES else INK
        fill_rect = pygame.Rect(bar_rect.left, bar_rect.top, fill_w, bar_h)
        pygame.draw.rect(surface, fill_color, fill_rect)

        # Table
        tbl = model.table
        tbl_layout = tbl.layout(tbl_rect)

        # Draw header
        f_h = _font(tbl.size, bold=True)
        for i, col in enumerate(tbl.cols):
            if i < len(tbl_layout.header_rects):
                h_rect = tbl_layout.header_rects[i]
                text_rect = tbl_layout.header_text_rects[i]
                txt = f_h.render(col.header, True, INK)
                surface.blit(txt, text_rect)

        # Draw rule
        pygame.draw.line(surface, INK,
                         (tbl_rect.left, tbl_layout.rule_y),
                         (tbl_rect.right, tbl_layout.rule_y))

        # Draw rows
        f_b = _font(tbl.size)
        for ri, row in enumerate(tbl.data):
            if ri >= len(tbl_layout.row_rects):
                break
            row_rect = tbl_layout.row_rects[ri]
            # Highlight skim rows
            if ri in model.skim_rows:
                pygame.draw.rect(surface, SKIM_HIGHLIGHT, row_rect)
            for ci, cell in enumerate(row):
                if ci >= len(tbl_layout.cell_rects[ri]):
                    continue
                cell_rect = tbl_layout.cell_rects[ri][ci]
                text_rect = tbl_layout.text_rects[ri][ci]
                # Delta column tone
                if ci == DELTA_COL and cell != "" and ri < len(model.delta_tones):
                    tone = model.delta_tones[ri]
                    color = TONES.get(tone, INK)
                else:
                    color = INK
                txt = f_b.render(cell, True, color)
                surface.blit(txt, text_rect)

        # Overflow warning
        if model.overflow_name is not None:
            warn = f_b.render(f"⚠ {model.overflow_name}", True, TONES["warn"])
            surface.blit(warn, (tbl_rect.left, tbl_rect.bottom + 4))

        # Predator / stake text
        y = tbl_rect.bottom + 4
        if model.overflow_name is not None:
            y += f_b.get_height() + 4
        for key in ("predator", "stake"):
            if key in model.texts and y < action_rect.top - 4:
                txt = f_b.render(model.texts[key], True, INK)
                surface.blit(txt, (action_rect.left, y))
                y += f_b.get_height() + 2

        # If a director picker is open, draw it instead of buttons
        if self._director_picker is not None:
            self._draw_director_picker(surface, content, action_rect.top, f_b)
            return

        # If the found picker is open, draw it instead of buttons
        if self._found_picker is not None:
            self._draw_found_picker(surface, content, action_rect.top, f_b)
            return

        # If the share picker is open, draw it instead of buttons
        if self._share_picker is not None:
            self._draw_share_picker(surface, content, action_rect.top, f_b)
            return

        # Draw Expand and Appoint buttons for eligible ventures
        from gilded.enterprises import TIER_MAX
        from gilded.docket import director_candidates
        actions = self.enterprise_actions()
        y = action_rect.top + 4
        body = f_b
        for act in actions:
            action_dict = act.get("action", {})
            verb = list(action_dict.keys())[0] if action_dict else None
            eid = act.get("eid")
            if eid is None:
                if verb == "attack_takeover":
                    from gilded.ui.actions import ACTIONS
                    ok, why = ACTIONS["attack_takeover"].eligible(
                        self.game, self.house, action_dict)
                    y = self._action_button(
                        surface, content, action_rect, y, act, body, "house",
                        "Hostile Takeover", None if ok else why, None)
                    if y is None:
                        return
                elif verb == "found_enterprise":
                    from gilded.ui.actions import ACTIONS
                    ok, why = ACTIONS["found_enterprise"].eligible(
                        self.game, self.house, action_dict)
                    y = self._action_button(
                        surface, content, action_rect, y, act, body, "house",
                        None, None if ok else why, None)
                    if y is None:
                        return
                continue
            ent = next((e for e in self.game.enterprises if e.eid == eid), None)
            if ent is None:
                continue

            if verb == "expand_enterprise":
                # Skip expand if under construction or at max tier
                reason = None
                if ent.under_construction > 0 or ent.target_tier >= TIER_MAX:
                    if ent.under_construction > 0:
                        reason = f"{ent.name} is still building; it cannot expand until the work is finished."
                    else:
                        reason = f"{ent.name} is already at its greatest extent."
                y = self._action_button(surface, content, action_rect, y, act, body, f"venture:{eid}", f"Expand {ent.name}", reason, self._enterprise_hits)
                if y is None:
                    return

            elif verb == "appoint_director":
                pool = director_candidates(self.game, self.house, eid)
                reason = None
                if not pool:
                    reason = f"No one in your house is qualified to direct {ent.name}."
                y = self._action_button(surface, content, action_rect, y, act, body, f"venture:{eid}", f"Appoint Director for {ent.name}", reason, self._appoint_hits)
                if y is None:
                    return

            elif verb == "defend_buyout":
                from gilded.ui.actions import ACTIONS
                ok, why = ACTIONS["defend_buyout"].eligible(self.game, self.house, action_dict)
                y = self._action_button(surface, content, action_rect, y, act, body, f"venture:{eid}", act.get("label", f"Buy out stake in {ent.name}"), None if ok else why, self._enterprise_hits)
                if y is None:
                    return

            elif verb == "buy_shares":
                from gilded.ui.actions import ACTIONS
                ok, why = ACTIONS["buy_shares"].eligible(self.game, self.house, action_dict)
                y = self._action_button(surface, content, action_rect, y, act, body, f"buy_shares:{eid}", f"Buy Shares in {ent.name}", None if ok else why, self._share_picker_hits)
                if y is None:
                    return

            elif verb == "sell_shares":
                from gilded.ui.actions import ACTIONS
                ok, why = ACTIONS["sell_shares"].eligible(self.game, self.house, action_dict)
                y = self._action_button(surface, content, action_rect, y, act, body, f"sell_shares:{eid}", f"Sell Shares in {ent.name}", None if ok else why, self._share_picker_hits)
                if y is None:
                    return

    def _draw_director_picker(self, surface, content, y, body) -> None:
        """Draw the director candidate picker for the open venture."""
        eid = self._director_picker
        ent = next((e for e in self.game.enterprises if e.eid == eid), None)
        if ent is None:
            return
        from gilded.docket import director_candidates
        pool = director_candidates(self.game, self.house, eid)
        if not pool:
            return

        # Back button
        back_text = "Back"
        back_surf = body.render(back_text, True, INK)
        back_w = back_surf.get_width() + 16
        back_h = body.get_height() + 8
        back_rect = pygame.Rect(PAD, y, back_w, back_h)
        pygame.draw.rect(surface, PICKER_BACK_BG, back_rect)
        pygame.draw.rect(surface, INK, back_rect, 2)
        surface.blit(back_surf, (PAD + 8, y + 4))
        self._director_picker_hits.append((back_rect, {"close_director_picker": True}))
        self.regions.add(Region(rect=back_rect, action={"close_director_picker": True}, hint="Return to the ventures without appointing anyone.", group="picker"))
        y += back_h + 4

        # Header showing venture name and pool count
        cap = 8
        shown = min(cap, len(pool))
        header = body.render(f"Directors for {ent.name} ({shown} of {len(pool)})", True, INK)
        surface.blit(header, (PAD, y))
        y += body.get_height() + 8

        # Draw top N candidates
        small = _font(TYPE_TEXT)
        for c in pool[:cap]:
            if y > content.bottom - 20:
                return
            name = c.name
            industry = c.get_effective_stat("industry")
            line = f"{name} (industry {industry})"
            ln_surf = small.render(line, True, INK)
            ln_w = ln_surf.get_width() + 16
            ln_h = small.get_height() + 8
            ln_rect = pygame.Rect(PAD, y, ln_w, ln_h)
            pygame.draw.rect(surface, PICKER_ROW_BG, ln_rect)
            pygame.draw.rect(surface, INK, ln_rect, 1)
            surface.blit(ln_surf, (PAD + 8, y + 4))
            self._director_picker_hits.append((ln_rect, {
                "appoint_director": eid, "char_id": c.id
            }))
            self.regions.add(Region(rect=ln_rect, action={"appoint_director": eid, "char_id": c.id}, hint=f"Appoint {c.name} to direct {ent.name}.", group="picker"))
            y += ln_h + 2

    def _draw_found_picker(self, surface, content: pygame.Rect, y, body) -> None:
        """Draw the charter chooser for founding an enterprise."""
        from gilded.ui.actions import _get_available_charters
        from gilded.enterprises import ENTERPRISE_TYPES, KIND_TITLES
        charters = _get_available_charters(self.game, self.house)
        treasury = self.game.houses[self.house].treasury

        # Back button
        back_text = "Back"
        back_surf = body.render(back_text, True, INK)
        back_w = back_surf.get_width() + 16
        back_h = body.get_height() + 8
        back_rect = pygame.Rect(PAD, y, back_w, back_h)
        pygame.draw.rect(surface, PICKER_BACK_BG, back_rect)
        pygame.draw.rect(surface, INK, back_rect, 2)
        surface.blit(back_surf, (PAD + 8, y + 4))
        self._found_picker_hits.append((back_rect, {"close_found_picker": True}))
        self.regions.add(Region(rect=back_rect, action={"close_found_picker": True}, hint="Return to the ventures without founding.", group="picker"))
        y += back_h + 4

        # Header
        header = body.render(f"Available Charters ({len(charters)})", True, INK)
        surface.blit(header, (PAD, y))
        y += body.get_height() + 6

        # Charter rows — all of them, no cap
        for kind, pid, pname, cost in charters:
            if y > content.bottom - 20:
                return
            title = KIND_TITLES[kind]
            article = "an" if title[0] in "AEIOUaeiou" else "a"
            label = f"{pname} {title} — {cost:.0f} gold"
            txt_surf = body.render(label, True, INK)
            txt_w = txt_surf.get_width() + 16
            txt_h = body.get_height() + 8
            txt_rect = pygame.Rect(PAD, y, txt_w, txt_h)

            affordable = treasury >= cost
            if affordable:
                pygame.draw.rect(surface, BUTTON_BG, txt_rect)
                pygame.draw.rect(surface, BUTTON_EDGE, txt_rect, 1)
                surface.blit(txt_surf, (PAD + 8, y + 4))
                self._found_picker_hits.append((txt_rect, {"found_enterprise": (kind, pid)}))
                hint = f"Found {article} {title.lower()} in {pname} for {cost:.0f} gold."
                self.regions.add(Region(rect=txt_rect, action={"found_enterprise": (kind, pid)}, hint=hint, group="picker"))
            else:
                pygame.draw.rect(surface, DISABLED_FILL, txt_rect)
                pygame.draw.rect(surface, DISABLED_EDGE, txt_rect, 1)
                disabled_surf = body.render(label, True, DISABLED_TEXT)
                surface.blit(disabled_surf, (PAD + 8, y + 4))
                reason = f"Cannot afford {cost:.0f} gold (treasury {treasury:.0f})"
                self.regions.add(Region(rect=txt_rect, action=None, state=RegionState.DISABLED, reason=reason, hint=reason, group="picker"))
            y += txt_h + 2

    def _draw_share_picker(self, surface, content: pygame.Rect, y, body) -> None:
        """Draw the share trade picker (buyer/seller selection, then size)."""
        picker = self._share_picker
        direction = picker["direction"]
        eid = picker["eid"]
        ent = next((e for e in self.game.enterprises if e.eid == eid), None)
        if ent is None:
            return
        from gilded.ui.actions import buy_share_counterparties, sell_share_counterparties, share_size_ladder
        from gilded.society.shares import stake_cost
        from gilded.docket import _fmt_gold

        # Back button
        back_text = "Back"
        back_surf = body.render(back_text, True, INK)
        back_w = back_surf.get_width() + 16
        back_h = body.get_height() + 8
        back_rect = pygame.Rect(PAD, y, back_w, back_h)
        pygame.draw.rect(surface, PICKER_BACK_BG, back_rect)
        pygame.draw.rect(surface, INK, back_rect, 2)
        surface.blit(back_surf, (PAD + 8, y + 4))
        self._share_picker_hits.append((back_rect, {"close_share_picker": True}))
        self.regions.add(Region(rect=back_rect, action={"close_share_picker": True}, hint="Return to the ventures.", group="picker"))
        y += back_h + 4

        # Header
        verb = "Buy" if direction == "buy" else "Sell"
        header = body.render(f"{verb} Shares in {ent.name}", True, INK)
        surface.blit(header, (PAD, y))
        y += body.get_height() + 6

        if direction == "buy":
            counterparties = buy_share_counterparties(self.game, self.house, eid)
        else:
            counterparties = sell_share_counterparties(self.game, self.house, eid)

        if not counterparties:
            no_cp_surf = body.render("No counterparties available.", True, INK)
            surface.blit(no_cp_surf, (PAD, y))
            return

        # Collect all ladder data per counterparty to check for uniform refusal
        ladder_data = []
        for cp in counterparties:
            cid = cp["id"]
            if direction == "buy":
                ladder = share_size_ladder(self.game, self.house, eid, cid)
            else:
                ladder = share_size_ladder(self.game, self.house, eid, self.game.realms[self.house].ruler.id, cid)
            ladder_data.append((cp, ladder))

        # Check if ALL rungs across ALL counterparties are refused for the SAME reason
        all_rungs = []
        all_reasons = set()
        for cp, ladder in ladder_data:
            for rung in ladder:
                all_rungs.append(rung)
                if not rung.get("offerable", True):
                    reason = rung.get("reason", "")
                    if reason:
                        all_reasons.add(reason)

        all_refused = all(not rung.get("offerable", True) for rung in all_rungs)
        same_reason = len(all_reasons) == 1
        refusal_msg = all_reasons.pop() if same_reason and all_refused else None

        if all_refused and same_reason:
            # Draw single refusal region — one line, not one per counterparty
            sub_surf = body.render(refusal_msg, True, PICKER_SUBTITLE)
            txt_w = max(sub_surf.get_width() + 16, content.right - PAD * 2)
            txt_h = body.get_height() + 8
            txt_rect = pygame.Rect(PAD, y, txt_w, txt_h)
            pygame.draw.rect(surface, DISABLED_FILL, txt_rect)
            pygame.draw.rect(surface, DISABLED_EDGE, txt_rect, 1)
            disabled_surf = body.render(refusal_msg, True, DISABLED_TEXT)
            surface.blit(disabled_surf, (PAD + 8, y + 4))
            self.regions.add(Region(rect=txt_rect, action=None, state=RegionState.DISABLED, reason=refusal_msg, hint=refusal_msg, group="picker"))
            return

        # Draw per-counterparty picker (normal case — at least some rungs are offerable)
        house_name = self.house
        sub = body.render(f"Choose a counterparty:", True, PICKER_SUBTITLE)
        surface.blit(sub, (PAD, y))
        y += body.get_height() + 4

        treasury = self.game.houses[self.house].treasury
        shown = len(counterparties)
        sub = body.render(f"{shown} counterparties:", True, PICKER_SUBTITLE)
        surface.blit(sub, (PAD, y))
        y += body.get_height() + 4

        for cp, ladder in ladder_data:
            if y > content.bottom - 80:
                break
            cid = cp["id"]
            cname = cp["name"]
            if direction == "buy":
                pct = cp["stake_pct"]
                cost = cp["cost"]
                label = f"{cname} ({pct:.1f}% — {_fmt_gold(cost)})"
            else:
                gold = cp["gold"]
                label = f"{cname} ({_fmt_gold(gold)} gold)"

            txt_surf = body.render(label, True, INK)
            txt_w = max(txt_surf.get_width() + 16, content.right - PAD * 2)
            txt_h = body.get_height() + 8
            txt_rect = pygame.Rect(PAD, y, txt_w, txt_h)

            pygame.draw.rect(surface, PICKER_ROW_ALT_BG, txt_rect)
            pygame.draw.rect(surface, INK, txt_rect, 2)
            surface.blit(txt_surf, (PAD + 8, y + 4))

            # Draw size ladder options for this counterparty
            # Per-rung affordability (from share_size_ladder) replaces the
            # per-counterparty treasury check — a rung that is affordable must
            # show even if the full stake is not.
            lx = PAD + 12
            rung_base_y = y + txt_h + 2
            rung_y = rung_base_y
            for rung in ladder:
                pct = rung["pct"]
                btn_label = f"{pct:g}%"
                btn_surf = body.render(btn_label, True, INK)
                btn_w = btn_surf.get_width() + 10
                btn_h = body.get_height() + 4
                btn_rect = pygame.Rect(lx, rung_y, btn_w, btn_h)

                if rung.get("offerable", True):
                    pygame.draw.rect(surface, OFFERABLE_BG, btn_rect)
                    pygame.draw.rect(surface, OFFERABLE_EDGE, btn_rect, 1)
                    surface.blit(btn_surf, (lx + 5, rung_y + 2))

                    action_key = "buy_shares" if direction == "buy" else "sell_shares"
                    action_payload = (eid, cid, pct)
                    self.regions.add(Region(rect=btn_rect, action={action_key: action_payload}, hint=f"{verb} {pct:g}% shares with {cname}.", group="picker"))
                else:
                    pygame.draw.rect(surface, DISABLED_FILL, btn_rect)
                    pygame.draw.rect(surface, DISABLED_EDGE, btn_rect, 1)
                    disabled_surf = body.render(btn_label, True, DISABLED_TEXT)
                    surface.blit(disabled_surf, (lx + 5, rung_y + 2))
                    reason = rung.get("reason", "Not available")
                    if reason:
                        self.regions.add(Region(rect=btn_rect, action=None, state=RegionState.DISABLED, reason=reason, hint=reason, group="picker"))

                lx += btn_w + 4
            # Advance y below the ladder buttons
            btn_h = body.get_height() + 4
            y = rung_y + btn_h + 6

    def house_lines(self) -> List[str]:
        """Build text lines for the House tab from the peerage read-model."""
        from gilded.peerage import report as peerage_report
        rpt = peerage_report(self.game, self.house)
        lines = _house_tab_lines(rpt)
        lines.extend(self._ambition_banner_lines())
        lines.extend(self._court_want_lines())
        return lines

    def _ambition_banner_lines(self) -> List[str]:
        """C2: the House's stake - the banner's family, target, clock."""
        lines: List[str] = []
        st = self.game.ambitions.status(self.house)
        if st["family"] is None:
            lines.append("")
            lines.append("AMBITION: (none set - use Set Ambition below)")
            return lines
        lines.append("")
        target = f" against House {st['target']}" if st["target"] else ""
        lines.append(f"AMBITION: {st['family']}{target}  [{st['clock']}]")
        lines.append(f"  {st['why']}")
        if st["fulfilled"] is not None:
            lines.append("  " + ("FULFILLED" if st["fulfilled"]
                                 else "fell short"))
        return lines

    def _court_want_lines(self) -> List[str]:
        """C2: the court's private wants - one card per adult member."""
        lines: List[str] = []
        cards = self.game.ambitions.cards(self.house)
        if not cards:
            return lines
        lines.append("COURT WANTS")
        for c in cards:
            traits = ", ".join(c["traits"]) if c["traits"] else "no mark"
            lines.append(f"  {c['name']} ({c['age']}, {traits}): "
                         f"{c['stance']} - {c['want_text']}")
        return lines

    def _draw_house(self, surface, content: pygame.Rect) -> None:
        from gilded.peerage import report as peerage_report
        from gilded.ui.court_actions import _get_appointment_pool
        rpt = peerage_report(self.game, self.house)
        y = draw_house_tab(surface, content, rpt, self)
        # C6C: two-column layout — the spine text (ladder + agenda + intrigue)
        # in the left column, the interactive controls (policies dials) in the
        # right column at band top. Both share the content bottom, so
        # everything ends <= content.bottom (the 45px spill healed; the
        # set_stance dials register inside the band).
        left = pygame.Rect(content.x, y + 2, 400, content.bottom - (y + 2))
        right = pygame.Rect(content.x + 414, content.y + 40,
                            content.width - 414,
                            content.bottom - (content.y + 40))
        # spec §2: the Briefing's ladder + agenda re-homed here (the House
        # spine is their home now); the agenda cards are the docket's
        # decisions. The left column carries only the spine text so it stays
        # short enough to fit the band.
        self._draw_ladder_and_agenda(surface, left, left.y,
                                     bottom=content.bottom - 40)
        # spec §2: the dissolved Policies tab is re-homed onto the House
        # spine — the five standing directive dials (set_stance) draw on the
        # Overview page (right column at band top), not a separate tab.
        y_right = self._draw_policies(surface, right, right.y,
                                      bottom=content.bottom - 40)
        # The intrigue section (plot visibility) stacks under the policies
        # dials in the right column so the left column never overflows the band.
        self._draw_intrigue(surface, right, y_right,
                            bottom=content.bottom - 40)
        # C2: the Set Ambition button, then the family picker when open
        self._draw_ambition_controls(surface, content)
        if self._ambition_picker:
            self._draw_ambition_picker(surface, content)
        # If court picker is open, draw candidates
        if self._court_picker is not None:
            self._draw_court_picker(surface, content, rpt)
        # If scheme picker is open, draw it
        if self._scheme_picker is not None:
            self._draw_scheme_picker(surface, content)
 
    def _draw_ambition_controls(self, surface, content: pygame.Rect) -> None:
        """C2: the Set Ambition button under the court section."""
        from gilded.ui.widgets import INK, Region, RegionState, TONES
        from gilded.ui.house_tab import _draw_button
        PAD = 12
        body = _font(TYPE_TEXT)
        game = self.game
        house = self.house
        st = game.ambitions.status(house)
        sy = content.bottom - 10
        btn_w = 140
        btn_h = body.get_height() + 4
        bx = content.width - PAD - btn_w
        if sy - 60 <= content.bottom - 10:
            label = f"Ambition: {st['family']}" if st["family"] else "Set Ambition"
            btn_rect = _draw_button(surface, label, bx, sy - 20, btn_w, btn_h, True)
            self.regions.add(Region(
                rect=btn_rect,
                action={"open_ambition_picker": True},
                hint="Set the House's stake - the goal the court backs or opposes",
                group="ambition_picker",
            ))

    def _draw_ambition_picker(self, surface, content: pygame.Rect) -> None:
        """C2: the family picker overlay - click a family to set the stake."""
        from gilded.agenda import FAMILIES
        from gilded.ui.widgets import INK, Region, TONES
        from gilded.ui.house_tab import _draw_button
        PAD = 12
        body = _font(TYPE_TEXT)
        btn_h = body.get_height() + 6
        x = PAD
        y = content.y + 8
        for family in FAMILIES:
            btn = pygame.Rect(x, y, 150, btn_h)
            _draw_button(surface, family, x, y, 150, btn_h, True)
            self.regions.add(Region(
                rect=btn,
                action={"set_ambition": {"family": family}},
                hint=f"Set the House's ambition to {family}",
                group="ambition_picker",
            ))
            y += btn_h + 2
            if y > content.bottom - 40:
                break
        _draw_button(surface, "Cancel", x, content.bottom - 40,
                     150, btn_h, True)
        self.regions.add(Region(
            rect=pygame.Rect(PAD + 168, content.bottom - 40, 150, btn_h),
            action={"close_ambition_picker": True},
            hint="Cancel - spends nothing",
            group="ambition_picker",
        ))

    def _draw_intrigue(self, surface, content: pygame.Rect,
                        y: int = None, bottom: int = None) -> int:
        """Draw intrigue section: plots affecting the played House.

        Starts at *y* (or the bottom of *content* when omitted) and returns
        the y after the section so callers can chain below it.
        """
        from gilded.ui.widgets import INK, Region, RegionState, TONES
        from gilded.ui.house_tab import _draw_button
        from gilded.ui.actions import _open_scheme_picker_eligible, _start_scheme_eligible
        # C6C two-column: the section is passed the right-column rect, so
        # x offsets are relative to content.x (same as _draw_policies).
        PAD = content.x + 12
        body = _font(TYPE_TEXT)
        game = self.game
        house = self.house
        realm = game.realms[house]
        our_ids = {c.id for c in realm.characters}
        # Find plots: against us (target is ours) and by us (agent is ours)
        schemes = getattr(game, 'scheme_mgr', None)
        if y is None:
            y = content.bottom - 20
        if not schemes:
            return y
        lines = []
        for s in schemes.schemes:
            target_is_ours = s.target.id in our_ids
            agent_is_ours = s.agent.id in our_ids
            if target_is_ours:
                lines.append(f"⚠ {s.agent.name} plots a {s.scheme_type} against {s.target.name}")
            elif agent_is_ours:
                lines.append(f"→ {s.agent.name} schemes against {s.target.name} ({s.scheme_type})")
        # Draw section — button is unconditional (conduct), lines are conditional (sight).
        # C6: flow the section DOWN from y (vertical chaining) so it never draws
        # above the previous section's end — the old upward anchor overwrote the
        # ladder/succession rows.
        header_h = body.get_height() + 4
        btn_h = body.get_height() + 8
        line_h = body.get_height() + 2
        sy = y + 4
        # Header
        blit_text(surface, body, "INTRIGUE", (PAD, sy), TONES.get("bad", INK))
        sy += header_h
        for line in lines:
            color = TONES.get("warn", INK) if line.startswith("⚠") else INK
            blit_text(surface, body, line, (PAD, sy), color)
            sy += line_h
        # Button to open scheme picker — always drawn (conduct, not sight)
        btn_w = 160
        if True:
            ok, reason = _open_scheme_picker_eligible(game, house, {})
            btn_rect = _draw_button(surface, "Start Scheme", PAD, sy, btn_w, btn_h, ok)
            if ok:
                self.regions.add(Region(
                    rect=btn_rect,
                    action={"open_scheme_picker": True},
                    hint="Open the intrigue picker",
                    group="intrigue",
                ))
            else:
                self.regions.add(Region(
                    rect=btn_rect,
                    action={"open_scheme_picker": True},
                    state=RegionState.DISABLED,
                    reason=reason,
                    hint="Open the intrigue picker",
                    group="intrigue",
                ))
            sy += btn_h + 6
        return sy

    def _draw_house_page_header(self, surface, content: pygame.Rect,
                                title: str) -> None:
        """Header strip for a House/Powers inner page (the dissolved tab's
        content re-homed).  Page-switch buttons let the player move between
        the spine's inner pages."""
        from gilded.ui.widgets import font as _font, TYPE_TITLE, TYPE_TEXT, INK
        from gilded.ui import palette
        INK2 = palette.rgb(palette.INK2)
        pages = (self.powers_pages if self.active_tab == "Powers"
                 else self.house_pages)
        cur = (self.powers_page if self.active_tab == "Powers"
               else self.house_page)
        head_font = _font(TYPE_TITLE, bold=True)
        blit_text(surface, head_font, title, (PAD, content.y + 6), INK)
        y = content.y + 30
        body = _font(TYPE_TEXT)
        x = PAD
        for p in pages:
            label = body.render(p, True, INK if p == cur else INK2)
            rect = pygame.Rect(x, y, label.get_width() + 16, body.get_height() + 8)
            if p == cur:
                pygame.draw.rect(surface, palette.rgb(palette.SAGE), rect)
            blit_text(surface, body, p, (rect.x + 8, rect.y + 4),
                      INK if p == cur else INK2)
            self.regions.add(Region(
                rect=rect,
                action={"set_spine_page": p},
                hint=f"Open the {p} page.",
                group=f"page:{self.active_tab}",
            ))
            x += rect.w + 10
        content.y += 44

    def _draw_powers_dossier(self, surface, content: pygame.Rect) -> None:
        """Powers inner page: the dossier for the selected rival/Order.
        Declaring war is a verb inside the dossier (the War tab dissolved)."""
        from gilded.ui.house_tab import _draw_button
        from gilded.ui.widgets import font as _font, TYPE_TEXT, INK
        if self._powers_selected is None:
            # No selection yet — show the roster so a row can be picked.
            self._draw_powers(surface, content)
            return
        # Draw the full Powers table (with the selected row highlighted),
        # then the dossier body for the selected power in the detail area
        # below the table (clear of the table title and rows).
        layout = powers_layout(powers_model(
            powers_report(self.game, self.house),
            selected=self._powers_selected), content)
        detail_rect = layout["detail"]
        lines = self.powers_lines()
        font = _font(TYPE_TEXT)
        x = detail_rect.left + 8
        y = detail_rect.top + 2
        head_rect = blit_text(surface, _font(TYPE_HEADING, bold=True),
                              f"DOSSIER - {self._powers_selected}",
                              (x, y), INK)
        y = head_rect.bottom + 4
        for line in lines:
            if line.startswith(self._powers_selected) or line.startswith(f"House {self._powers_selected}"):
                blit_text(surface, font, line, (x, y), INK)
                y += font.get_height() + 6
                break
        btn_rect = layout["buttons"]
        war = _draw_button(
            surface, "Declare War", btn_rect.right - 140, btn_rect.top,
            140, font.get_height() + 8, True)
        self.regions.add(Region(
            rect=war,
            action={"declare_war": self._powers_selected},
            hint=f"Declare war on {self._powers_selected}.",
            group="war",
        ))

    def _war_drawer_rect(self, content: pygame.Rect) -> pygame.Rect:
        # Right-column drawer: sits in the actions column (x >= content.right -
        # 260), clear of every province centroid (all at x < content.right -
        # 420 at every supported window size).
        return pygame.Rect(content.right - 260, content.y, 250, content.h)

    def _draw_war(self, surface, content: pygame.Rect) -> None:
        from gilded.ui.war_tab import draw_war_tab
        draw_war_tab(surface, self.game, self.house,
                     content.x, content.y, content.w, content.h,
                     self.regions,
                     font_text=None)
        if self._garrison_picker is not None:
            self._draw_garrison_picker(surface, content)

    def _draw_war_toggle(self, surface, content: pygame.Rect) -> None:
        # Desk-strip toggle: top-right when closed (the atlas's centroid-free
        # zone, measured C4 diagnosis: all centroids at x < right - 164);
        # just left of the drawer when open so it stays reachable.
        from gilded.ui.house_tab import _draw_button
        label = "Close war" if self.war_drawer else "War"
        if self.war_drawer:
            btn_x = content.right - 260 - 160
        else:
            btn_x = content.right - 150
        btn = _draw_button(surface, label, btn_x,
                           content.y + 8, 150, 30, True)
        self.regions.add(Region(
            rect=btn,
            action={"toggle_war_drawer": True},
            hint="Toggle the War drawer (right column).",
            group="war",
        ))

    def _draw_court_picker(self, surface, content, report):
        """Draw the appointment picker for a vacant court seat using Regions."""
        from gilded.ui.court_actions import _get_appointment_pool
        from gilded.ui.widgets import font as _font, TYPE_TEXT, INK
        from gilded.ui.house_tab import _draw_button
        PAD = 12
        body = _font(TYPE_TEXT)
        pk = self._court_picker
        pos_name = pk.replace("_", " ").title()
        y = content.y + 100
        btn_h = body.get_height() + 8
        btn_w = 200

        blit_text(surface, body, f"Select appointee for {pos_name}:", (PAD, y), INK)
        y += body.get_height() + 8

        # Back button
        back_rect = _draw_button(surface, "Cancel", PAD, y, btn_w, btn_h, True)
        self.regions.add(Region(
            rect=back_rect,
            action={"close_appointment_picker": True},
            hint="Cancel appointment",
            group="picker",
        ))
        y += btn_h + 8

        # Draw candidate buttons
        realm = self.game.realms[self.house]
        pool = _get_appointment_pool(realm)
        for ch in pool:
            if y + btn_h > content.bottom:
                break
            btn_text = f"{ch.name}"
            btn_rect = _draw_button(surface, btn_text, PAD, y, btn_w, btn_h, True)

            self.regions.add(Region(
                rect=btn_rect,
                action={"appoint_to_seat": pk, "char_id": ch.id},
                hint=f"Appoint {ch.name} as {pos_name}",
                group="picker",
            ))
            y += btn_h + 4

    # --- clicking ------------------------------------------------------------

    def _draw_garrison_picker(self, surface, content: pygame.Rect) -> None:
        """Draw the garrison picker: one row per owned province with population to spare."""
        from gilded.ui.widgets import font as _font, TYPE_TEXT, INK, CARD_BG, BUTTON_BG, BUTTON_EDGE, BUTTON_TEXT, DISABLED_BUTTON_BG, DISABLED_BUTTON_EDGE
        from gilded.ui.house_tab import _draw_button
        from gilded.fronts import REGIMENT_POP_COST
        PAD = 12
        body = _font(TYPE_TEXT)
        y = content.y + 100
        btn_h = body.get_height() + 8
        btn_w = content.w - 2 * PAD

        # Background overlay
        overlay_h = content.bottom - y - 20
        if overlay_h > 0:
            surface.fill(CARD_BG, (content.x, y, content.w, overlay_h))

        blit_text(surface, body, "Select province to raise regiments from:", (content.x + PAD, y), INK)
        y += body.get_height() + 8

        # Back button
        back_rect = _draw_button(surface, "Cancel", content.x + PAD, y, btn_w, btn_h, True)
        self.regions.add(Region(
            rect=back_rect,
            action={"close_garrison_picker": True},
            hint="Cancel garrison adjustment",
            group="picker",
        ))
        self._garrison_picker_hits.append((back_rect, {"close_garrison_picker": True}))
        y += btn_h + 8

        # Province rows
        provinces = self.game.provinces_of(self.house)
        for prov in provinces:
            if y + btn_h > content.bottom:
                break
            pop_available = prov.population // REGIMENT_POP_COST
            enabled = pop_available > 0
            label = f"{prov.name} (pop {prov.population}, {pop_available} regiment{'s' if pop_available != 1 else ''})"
            if not enabled:
                label += f" — insufficient population (need {REGIMENT_POP_COST})"

            if enabled:
                btn_rect = _draw_button(surface, label, content.x + PAD, y, btn_w, btn_h, True)
                action = {"adjust_garrison": {"province_pid": prov.pid, "count": 1}}
            else:
                btn_rect = pygame.Rect(content.x + PAD, y, btn_w, btn_h)
                pygame.draw.rect(surface, DISABLED_BUTTON_BG, btn_rect)
                pygame.draw.rect(surface, DISABLED_BUTTON_EDGE, btn_rect, 1)
                txt = body.render(label, True, DISABLED_BUTTON_EDGE)
                surface.blit(txt, (btn_rect.x + 4, btn_rect.y + 4))
                action = None

            if action is not None:
                self._garrison_picker_hits.append((btn_rect, action))
                self.regions.add(Region(
                    rect=btn_rect,
                    action=action,
                    state=RegionState.ENABLED,
                    hint=label,
                    group="picker",
                ))
            else:
                self.regions.add(Region(
                    rect=btn_rect,
                    action=action or {"adjust_garrison": {"province_pid": prov.pid, "count": 1}},
                    state=RegionState.DISABLED,
                    reason=f"Insufficient population (need {REGIMENT_POP_COST})",
                    hint=label,
                    group="picker",
                ))
            y += btn_h + 4

    def _draw_scheme_picker(self, surface, content: pygame.Rect) -> None:
        """Draw the scheme picker overlay with target+kind buttons."""
        from gilded.ui.widgets import INK, Region, RegionState, TONES
        from gilded.ui.house_tab import _draw_button
        from gilded.ui.actions import _start_scheme_eligible
        PAD = 12
        body = _font(TYPE_TEXT)
        btn_h = body.get_height() + 8
        btn_w = 280
        y = content.y + 120
        blit_text(surface, body, "INTRIGUE — Select target and scheme type:", (PAD, y), INK)
        y += body.get_height() + 10
        # Collect potential targets (living characters not in played House's court)
        game = self.game
        house = self.house
        realm = game.realms[house]
        our_ids = {c.id for c in realm.characters}
        targets = []
        for h in game.houses:
            if h == house:
                continue
            other_realm = game.realms[h]
            for c in other_realm.characters:
                if c.is_alive and c not in targets:
                    targets.append((c, h))
        if not targets:
            targets = []
        for c, target_house in targets[:6]:
            if y + btn_h > content.bottom:
                break
            for scheme_type in ("coup", "assassination"):
                if y + btn_h > content.bottom:
                    return
                label = f"{c.name} — {scheme_type}"
                ok, reason = _start_scheme_eligible(game, house, {
                    "target_id": c.id, "scheme_type": scheme_type
                })
                btn_rect = _draw_button(surface, label, PAD, y, btn_w, btn_h, ok)
                if ok:
                    self.regions.add(Region(
                        rect=btn_rect,
                        action={"start_scheme": True, "target_id": c.id,
                                "scheme_type": scheme_type},
                        hint=label,
                        group="scheme_picker",
                    ))
                else:
                    self.regions.add(Region(
                        rect=btn_rect,
                        action={"start_scheme": True, "target_id": c.id,
                                "scheme_type": scheme_type},
                        state=RegionState.DISABLED,
                        reason=reason,
                        hint=label,
                        group="scheme_picker",
                    ))
                y += btn_h + 2
        # Close button
        if y + btn_h <= content.bottom:
            close_rect = _draw_button(surface, "Cancel", PAD, y, btn_w, btn_h, True)
            self.regions.add(Region(
                rect=close_rect,
                action={"close_scheme_picker": True},
                hint="Cancel — spends nothing",
                group="scheme_picker",
            ))

    def handle_click(self, pos: Tuple[int, int]) -> Optional[dict]:
        region = self.regions.at(pos)
        if region is not None:
            if region.state is RegionState.DISABLED:
                return None
            action = region.action
            if "toggle_war_drawer" in action:
                self.war_drawer = not self.war_drawer
                return None
            if "tab" in action:
                self.active_tab = action["tab"]
            if "set_spine_page" in action:
                page = action["set_spine_page"]
                if self.active_tab == "Powers":
                    self.powers_page = page
                else:
                    self.house_page = page
                return {"set_spine_page": page}
            if "cycle_exec" in action:
                pid = action["cycle_exec"]
                cands = self._candidates(pid)
                self._exec_idx[pid] = (self._exec_idx.get(pid, 0) + 1) % len(cands)
                return None
            if "set_stance" in action:
                key, _ = action["set_stance"]
                frac = (pos[0] - region.rect.x) / region.rect.width
                value = int(round((frac * 200 - 100) / 10.0)) * 10
                value = max(-100, min(100, value))
                return {"set_stance": (key, value)}
            if "select_province" in action:
                pid = pick_province(self.game.atlas, self._atlas_polys, pos)
                if pid is not None:
                    self.selected_pid = pid
                    return {"select_province": pid}
                return None
            if "open_appointment_picker" in action:
                pk = action["open_appointment_picker"]
                self._court_picker = pk
                return {"open_appointment_picker": pk}
            if "close_appointment_picker" in action:
                self._court_picker = None
            if "open_heir_picker" in action:
                self._heir_picker = True
                return {"open_heir_picker": True}
            if "open_ambition_picker" in action:
                self._ambition_picker = True
                return None
            if "close_ambition_picker" in action:
                self._ambition_picker = False
                return None
            if "set_ambition" in action:
                self._ambition_picker = False
                return {"set_ambition": action["set_ambition"]}
            if "close_heir_picker" in action:
                self._heir_picker = None
            if "designate_heir" in action:
                self._heir_picker = None
                return action
            if "appoint_director" in action:
                if "char_id" not in action:
                    eid = action["appoint_director"]
                    self._director_picker = eid
                    self._director_picker_hits.clear()
                    return {"open_director_picker": eid}
            if "close_director_picker" in action:
                self._director_picker = None
                self._director_picker_hits.clear()
            if "buy_shares" in action:
                eid = action["buy_shares"]
                if isinstance(eid, int):
                    self._share_picker = {"direction": "buy", "eid": eid}
                    self._share_picker_hits.clear()
                    return {"open_share_picker": eid}
            if "sell_shares" in action:
                eid = action["sell_shares"]
                if isinstance(eid, int):
                    self._share_picker = {"direction": "sell", "eid": eid}
                    self._share_picker_hits.clear()
                    return {"open_share_picker": eid}
            if "close_found_picker" in action:
                self._found_picker = None
                self._found_picker_hits.clear()
            if "close_share_picker" in action:
                self._share_picker = None
                self._share_picker_hits.clear()
            if "open_garrison_picker" in action:
                self._garrison_picker = True
                self._garrison_picker_hits.clear()
                return None
            if "close_garrison_picker" in action:
                self._garrison_picker = None
                self._garrison_picker_hits.clear()
                return None
            if "open_scheme_picker" in action:
                self._scheme_picker = True
                self._scheme_picker_hits.clear()
                return action
            if "close_scheme_picker" in action:
                self._scheme_picker = None
                self._scheme_picker_hits.clear()
                return None
            if "start_scheme" in action:
                from gilded.ui.actions import ACTIONS
                act = ACTIONS.get("start_scheme")
                if act is not None:
                    ok, _ = act.eligible(self.game, self.house, action)
                    if ok:
                        act.dispatch(self.game, self.house, self, action)
                return action
            return action
        for name, rect in self._tab_rects.items():
            if rect.collidepoint(pos):
                self.active_tab = name
                return {"tab": name}
        if self._end_turn_rect is not None and self._end_turn_rect.collidepoint(pos):
            return {"end_turn": True}
        if self._narrate_rect is not None and self._narrate_rect.collidepoint(pos):
            return {"toggle_narrate": True}
        # Picker hit detection — must be reachable regardless of active tab
        if self._director_picker is not None:
            for rect, action in self._director_picker_hits:
                if rect.collidepoint(pos):
                    if "select_director" in action:
                        self._director_picker = None
                        self._director_picker_hits.clear()
                        return action
                    if "close_director_picker" in action:
                        self._director_picker = None
                        self._director_picker_hits.clear()
                    return action
        if self._found_picker is not None:
            for rect, action in self._found_picker_hits:
                if rect.collidepoint(pos):
                    if "close_found_picker" in action:
                        self._found_picker = None
                        self._found_picker_hits.clear()
                    return action
        if self._share_picker is not None:
            for rect, action in self._share_picker_hits:
                if rect.collidepoint(pos):
                    if "close_share_picker" in action:
                        self._share_picker = None
                        self._share_picker_hits.clear()
                    return action
        if self._scheme_picker is not None:
            for rect, action in self._scheme_picker_hits:
                if rect.collidepoint(pos):
                    if "close_scheme_picker" in action:
                        self._scheme_picker = None
                        self._scheme_picker_hits.clear()
                    return action
        if self.active_tab == "House" and self.house_page == "Governance":
            for rect, act in self._enterprise_hits:
                if rect.collidepoint(pos):
                    return act.get("action", act)
            for rect, act in self._appoint_hits:
                if rect.collidepoint(pos):
                    action = act.get("action", act)
                    if "appoint_director" in action and "char_id" not in action:
                        eid = action["appoint_director"]
                        self._director_picker = eid
                        self._director_picker_hits.clear()
                        return {"open_director_picker": eid}
                    return action
        return None
