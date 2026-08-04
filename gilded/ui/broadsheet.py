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
from gilded.papers import compose
from gilded.saga.narrator import NarratorTemplated
from gilded.ui.atlas_view import (
    OCEAN_COLOR, draw_atlas, pick_province, province_panel_lines)
from gilded.ui.widgets import (
    CARD_BG, CARD_EDGE, FADED, INK, PAPER_BG,
    Chip, Column, Meter, Table, TableLayout, font as _font, wrap as _wrap,
    column_plan, flow_columns, FlowResult,
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
from gilded.ui.widgets import Region, RegionSet, RegionState

TABS = ("Briefing", "Gazette", "Ledger", "Letters", "Docket", "Policies", "Enterprises", "Atlas", "Powers", "House")

TAB_H = 40
BOTTOM_H = 56

# Danger thresholds
LEGIT_DANGER = 20.0
TIDE_DANGER = 70.0

# HUD geometry: 3 rows (axes + legitimacy/tide, chips + texts, rival row always reserved)
_HUD_ROWS = 3
_METER_BAR_H = 14
_CHIP_H = 18
_TEXT_PT = 13
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

    # Texts
    texts["era"] = f"{board.era_title} · {board.year} ({board.century_pct * 100:.0f}%)"
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

    # --- Row 3: chips (treasury, atrocities, phase) + era text ---
    chip_specs = []
    for key in ["treasury", "atrocities", "phase"]:
        surf = fs.render(model.chips[key].text, True, INK)
        w = surf.get_width() + 16
        chip_specs.append((key, w))
    surf_era = fs.render(model.texts["era"], True, INK)
    era_w = surf_era.get_width() + 8
    chip_specs.append(("era", era_w))

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
    surf_rival = fs.render(model.texts["rival"], True, INK)
    rival_w = surf_rival.get_width() + 8
    surf_rank = fs.render(model.texts["rank"], True, INK)
    rank_w = surf_rank.get_width() + 8
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

TAB_BG = (54, 48, 42)
TAB_ACTIVE = (206, 176, 108)
TAB_TEXT = (232, 226, 210)
HUD_BG = (44, 40, 34)
HUD_INK = (232, 226, 210)
BUTTON_BG = (60, 82, 60)
BUTTON_EDGE = (30, 46, 30)
BUTTON_TEXT = (238, 240, 232)
EXEC_BG = (78, 66, 96)
ENDTURN_BG = (140, 60, 52)
ATTN_COLOR = (150, 110, 40)

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
            row_h = available_data_h // row_count
            row_rects = []
            y = data_top
            for i in range(row_count):
                h = row_h
                if i == row_count - 1:
                    h = data_bottom - y
                row_rects.append(pygame.Rect(rect.left, y, rect.width, h))
                y += h + 2

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

        return TableLayout(
            header_rects=header_rects,
            rule_y=rule_y,
            row_rects=row_rects,
            cell_rects=cell_rects,
            text_rects=text_rects,
        )

    @staticmethod
    def _fit(text: str, f: pygame.font.Font, cell: pygame.Rect) -> str:
        if not text.strip():
            return text
        max_w = cell.width - 8
        surf = f.render(text, True, (0, 0, 0))
        if surf.get_width() <= max_w:
            return text  # fits, no truncation needed
        # Text is too long — shorten and append ellipsis
        ellipsis = "…"
        while len(text) > 1:
            candidate = text + ellipsis
            surf = f.render(candidate, True, (0, 0, 0))
            if surf.get_width() <= max_w:
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
            _clean(f"House {ln.house}"),
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
    f_title = _font(24, bold=True)
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
        f = _font(14)
        body_h = f.get_linesize()
        header_h = _font(14, bold=True).get_linesize()
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
    def __init__(self, game, house_name: str, narrator=None):
        self.game = game
        self.house = house_name
        # the narrator rewrites the Gazette's prose only; templated is identity.
        self.narrator = narrator if narrator is not None else NarratorTemplated()
        self.narrate_on = True
        self.active_tab = TABS[0]
        self.selected_pid: Optional[int] = None
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
        # director picker state: None or eid whose picker is open
        self._director_picker: Optional[int] = None
        self._director_picker_hits: List[Tuple[pygame.Rect, dict]] = []
        self.hover_pos: Tuple[int, int] | None = None
        self.regions = RegionSet()
        self.hovered: Optional[Region] = None
        self._w = 0
        self._h = 0

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
        self._informant_hits = []
        self._director_picker_hits = []
        surface.fill(PAPER_BG)
        hud_h = _hud_height()
        content = pygame.Rect(0, TAB_H + hud_h, self._w,
                              self._h - TAB_H - hud_h - BOTTOM_H)

        if self.active_tab == "Briefing":
            self._draw_briefing(surface, content)
        elif self.active_tab == "Atlas":
            self._draw_atlas(surface)
        elif self.active_tab == "Gazette":
            self._draw_paper(surface, content)
        elif self.active_tab == "Ledger":
            self._draw_ledger(surface, content)
        elif self.active_tab == "Letters":
            self._draw_paper(surface, content)
        elif self.active_tab == "Docket":
            self._draw_docket(surface, content)
        elif self.active_tab == "Policies":
            self._draw_policies(surface, content)
        elif self.active_tab == "Powers":
            self._draw_powers(surface, content)
        elif self.active_tab == "Enterprises":
            self._draw_enterprises(surface, content)
        elif self.active_tab == "House":
            self._draw_house(surface, content)

        self._draw_tab_bar(surface)
        self._draw_hud(surface)
        self._draw_bottom_bar(surface)

    def _draw_tab_bar(self, surface) -> None:
        pygame.draw.rect(surface, TAB_BG, (0, 0, self._w, TAB_H))
        tabw = self._w // len(TABS)
        font = _font(18, bold=True)
        self._tab_rects = {}
        TAB_HINTS = {
            "Briefing": "Your command post — see what changed and act on it.",
            "Gazette": "Read the world's news in full prose.",
            "Ledger": "Track your money, income, and spending.",
            "Letters": "Private correspondence from your network.",
            "Docket": "Standing rules and appointments before the council.",
            "Policies": "Set your house's five standing directives.",
            "Enterprises": "Manage your ventures and their directors.",
            "Atlas": "Survey the realm's map and your territory.",
            "Powers": "See the other houses, their axes, and their moves.",
            "House": "Your court, your people, and your standing.",
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
            label = font.render(name, True,
                                INK if name == self.active_tab else TAB_TEXT)
            surface.blit(label, (rect.centerx - label.get_width() / 2,
                                 rect.centery - label.get_height() / 2))

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
                chip_surf = fs.render(chip.text, True, INK)
                pygame.draw.rect(surface, chip.bg(), rect, border_radius=4)
                surface.blit(chip_surf, (rect.left + 6, rect.centery - chip_surf.get_height() // 2))
            elif key in model.texts:
                text = model.texts[key]
                text_surf = fs.render(text, True, HUD_INK)
                surface.blit(text_surf, (rect.left, rect.centery - text_surf.get_height() // 2))

        # Draw intent text in row 5
        spotlight = b.rival_name or (
            threat_rank(self.game)[0] if threat_rank(self.game) else None)
        if spotlight is not None:
            intent = intel_report(self.game, self.house, spotlight).apparent_intent
            intent_text = f"Their design: {intent}"
        else:
            intent_text = "No clear threat"
        intent_rect = layout["intent"]
        intent_surf = fs.render(intent_text, True, HUD_INK)
        surface.blit(intent_surf, (intent_rect.left, intent_rect.centery - intent_surf.get_height() // 2))

    def _draw_bottom_bar(self, surface) -> None:
        y = self._h - BOTTOM_H
        pygame.draw.rect(surface, TAB_BG, (0, y, self._w, BOTTOM_H))
        attn = self.game.attention.get(self.house, 0)
        font = _font(18, bold=True)
        label = font.render(f"Attention: {attn}", True, ATTN_COLOR)
        surface.blit(label, (PAD, y + (BOTTOM_H - label.get_height()) / 2))
        nlabel = font.render(
            f"Narrate: {'on' if self.narrate_on else 'off'}", True, TAB_TEXT)
        nrect = pygame.Rect(self._w - 170 - nlabel.get_width() - 36,
                            y + 10, nlabel.get_width() + 20, BOTTOM_H - 20)
        self._narrate_rect = nrect
        self.regions.add(Region(rect=nrect,
                                action={"toggle_narrate": True},
                                hint="Turn the narrator's prose on or off.",
                                group="chrome"))
        pygame.draw.rect(surface, EXEC_BG, nrect)
        surface.blit(nlabel, (nrect.centerx - nlabel.get_width() / 2,
                              nrect.centery - nlabel.get_height() / 2))
        rect = pygame.Rect(self._w - 170, y + 10, 154, BOTTOM_H - 20)
        self._end_turn_rect = rect
        self.regions.add(Region(rect=rect,
                                action={"end_turn": True},
                                hint="Close the session and let the world move.",
                                group="chrome"))
        pygame.draw.rect(surface, ENDTURN_BG, rect)
        et = font.render("End Turn", True, BUTTON_TEXT)
        surface.blit(et, (rect.centerx - et.get_width() / 2,
                          rect.centery - et.get_height() / 2))

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
        title = _font(30, bold=True).render(
            f"COUNCIL BRIEFING - {board.year}", True, INK)
        surface.blit(title, (PAD, content.y + 6))
        y = content.y + 6 + title.get_height() + 8
        head = _font(19, bold=True)
        body = _font(17)
        width = content.width - 2 * PAD

        surface.blit(head.render("Since last session", True, INK), (PAD, y))
        y += head.get_height() + 4
        for line in self._delta_lines(d, board):
            surface.blit(body.render(line, True, INK), (PAD + 10, y))
            y += body.get_height() + 2
        y += 8

        report = compose(self.game, self.house)
        events = report.gazette[:2] + report.ledger[:2] + report.letters[:1]
        if events:
            surface.blit(head.render("What the papers say", True, INK), (PAD, y))
            y += head.get_height() + 4
            for ev in events:
                for line in _wrap(ev, body, width - 10):
                    if y > content.bottom - 170:
                        break
                    surface.blit(body.render(line, True, INK), (PAD + 10, y))
                    y += body.get_height() + 2
                y += 4
        y += 8

        surface.blit(head.render("The Agenda", True, INK), (PAD, y))
        y += head.get_height() + 6
        self._draw_petition_cards(surface, content, y)

    # --- shared petition renderer (Docket + Agenda) --------------------------

    def _draw_petition_cards(self, surface, content: pygame.Rect,
                             y: int) -> None:
        petitions = self.game.docket_by_house.get(self.house, [])
        body = _font(17)
        small = _font(15, bold=True)
        width = content.width - 2 * PAD
        for p in petitions:
            lines = _wrap(p.text, body, width - 20)
            card_h = 30 + len(lines) * (body.get_height() + 2) + 44
            if y + card_h > content.bottom - 10:
                break
            card = pygame.Rect(PAD, y, width, card_h)
            pygame.draw.rect(surface, CARD_BG, card)
            pygame.draw.rect(surface, CARD_EDGE, card, 1)
            hy = y + 8
            surface.blit(small.render(f"[{p.domain}] {p.kind}", True, FADED),
                         (PAD + 10, hy))
            hy += small.get_height() + 4
            for line in lines:
                surface.blit(body.render(line, True, INK), (PAD + 10, hy))
                hy += body.get_height() + 2
            bx = PAD + 10
            for opt in p.options:
                blabel = small.render(opt.text, True, BUTTON_TEXT)
                bw = blabel.get_width() + 20
                brect = pygame.Rect(bx, hy + 4, bw, 26)
                pygame.draw.rect(surface, BUTTON_BG, brect)
                pygame.draw.rect(surface, BUTTON_EDGE, brect, 1)
                surface.blit(blabel, (brect.x + 10, brect.y + 5))
                ex = self._chosen_executor(p.pid)
                exec_id = None if ex is None else ex.id
                self._option_hits.append(
                    (brect, ("rule", p.pid, opt.key, exec_id)))
                self.regions.add(Region(rect=brect,
                                        action={"rule": (p.pid, opt.key, exec_id)},
                                        hint=opt.text,
                                        group=f"petition:{p.pid}"))
                bx += bw + 8
            ex = self._chosen_executor(p.pid)
            ex_name = ("executor: default" if ex is None
                       else f"executor: {ex.name}")
            elabel = small.render(ex_name, True, BUTTON_TEXT)
            erect = pygame.Rect(bx, hy + 4, elabel.get_width() + 20, 26)
            pygame.draw.rect(surface, EXEC_BG, erect)
            pygame.draw.rect(surface, BUTTON_EDGE, erect, 1)
            surface.blit(elabel, (erect.x + 10, erect.y + 5))
            self._exec_hits.append((erect, p.pid))
            self.regions.add(Region(rect=erect,
                                    action={"cycle_exec": p.pid},
                                    hint="Choose who carries out this ruling.",
                                    group=f"petition:{p.pid}"))
            y += card_h + 10

    def _draw_paper(self, surface, content: pygame.Rect) -> None:
        report = compose(self.game, self.house)
        if self.narrate_on and self.active_tab == "Gazette":
            report = self.narrator.render(report, self.game.director, self.game)
        items = {"Gazette": report.gazette, "Ledger": report.ledger,
                 "Letters": report.letters}[self.active_tab]
        head_font = _font(30, bold=True)
        head = head_font.render(
            f"THE {self.active_tab.upper()} - {report.year}", True, INK)
        surface.blit(head, (PAD, content.y + 6))
        # Horizontal rule under the head, in the gap before body text
        rule_y = content.y + 6 + head.get_height() + 4
        pygame.draw.line(surface, INK,
                         (PAD, rule_y),
                         (content.width - PAD, rule_y), 1)
        body = _font(18)
        # Content area for columns: below the rule
        body_top = rule_y + 6
        body_rect = pygame.Rect(content.x, body_top,
                                content.width, content.bottom - body_top)
        if not items:
            items = ["(nothing to report)"]

        result = flow_columns(items, body, body_rect, line_gap=4)

        for (text, x, y, _ci) in result.placements:
            surface.blit(body.render(text, True, INK), (x, y))

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
        f_title = _font(26, bold=True)
        f_body = _font(14)
        f_small = _font(12)
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
            tbl = Table(cols, data, size=14)
            tbl_h = tbl.height()
            tbl_rect = pygame.Rect(PAD, y, content.width - 2 * PAD, tbl_h)
            tbl_layout = tbl.layout(tbl_rect)

            # Draw table header
            f_h = _font(tbl.size, bold=True)
            for i, col in enumerate(tbl.cols):
                txt = f_h.render(col.header, True, INK)
                text_rect = tbl_layout.text_rects[0][i]
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
            h_tbl = Table(h_cols, h_data, size=12)
            h_tbl_h = h_tbl.height()
            h_tbl_rect = pygame.Rect(PAD, y, content.width - 2 * PAD, h_tbl_h)
            h_tbl_layout = h_tbl.layout(h_tbl_rect)

            f_h = _font(h_tbl.size, bold=True)
            for i, col in enumerate(h_tbl.cols):
                txt = f_h.render(col.header, True, INK)
                text_rect = h_tbl_layout.text_rects[0][i]
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
            s_tbl = Table(s_cols, s_data, size=14)
            s_tbl_h = s_tbl.height()
            s_tbl_rect = pygame.Rect(PAD, y, content.width - 2 * PAD, s_tbl_h)
            s_tbl_layout = s_tbl.layout(s_tbl_rect)

            f_h = _font(s_tbl.size, bold=True)
            for i, col in enumerate(s_tbl.cols):
                txt = f_h.render(col.header, True, INK)
                text_rect = s_tbl_layout.text_rects[0][i]
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
        title = _font(30, bold=True).render("THE DOCKET", True, INK)
        surface.blit(title, (PAD, content.y + 6))
        y = content.y + 6 + title.get_height() + 10
        self._draw_petition_cards(surface, content, y)

    def _draw_policies(self, surface, content) -> None:
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
        title = _font(22, bold=True)
        label = _font(17, bold=True)
        small = _font(15)
        x = content.x + PAD
        w = content.width - 2 * PAD
        y = content.y + PAD
        surface.blit(title.render("Standing Policy", True, INK), (x, y))
        y += title.get_height() + 12
        track_w = w - 240
        for key in DIRECTIVE_KEYS:
            left, right = POLES[key]
            stance = directives.stances.get(key, 0)
            # label row
            surface.blit(label.render(f"{left}", True, FADED), (x, y))
            rlabel = label.render(right, True, FADED)
            surface.blit(rlabel, (x + track_w - rlabel.get_width(), y))
            sign = f"(+{stance})" if stance > 0 else f"({stance})"
            surface.blit(label.render(sign, True, INK), (x + track_w + 16, y))
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
            surface.blit(small.render(line, True, INK), (x, y))
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
                    surface.blit(small.render(flag, True, FADED), (x, y))
                    y += small.get_height() + 4
            y += 16

    def _draw_atlas(self, surface, rect: pygame.Rect = None) -> None:
        if rect is None:
            hud_h = _hud_height()
            rect = pygame.Rect(0, TAB_H + hud_h, self._w,
                               self._h - TAB_H - hud_h - BOTTOM_H)
        self._atlas_polys = draw_atlas(surface, self.game, rect, self.selected_pid)
        self.regions.add(Region(rect=rect,
                                action={"select_province": None},
                                hint="Click a province to inspect it.",
                                group="atlas"))
        if self.selected_pid is not None:
            self._draw_panel(surface,
                             province_panel_lines(self.game, self.selected_pid))

    def _draw_panel(self, surface, lines: List[str]) -> None:
        font = _font(16)
        w = max(font.size(l)[0] for l in lines) + 2 * PAD
        h = len(lines) * (font.get_height() + 2) + 2 * PAD
        rect = pygame.Rect(self._w - w - PAD, TAB_H + _hud_height() + PAD, w, h)
        panel = pygame.Surface(rect.size)
        panel.set_alpha(225)
        panel.fill((18, 16, 14))
        surface.blit(panel, rect.topleft)
        y = rect.y + PAD
        for i, line in enumerate(lines):
            f = _font(18, bold=True) if i == 0 else font
            surface.blit(f.render(line, True, TAB_TEXT), (rect.x + PAD, y))
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
        """Draw the Powers tab: model -> layout -> draw."""
        g, name = self.game, self.house
        lines = powers_report(g, name)
        model = powers_model(lines, selected=None)
        layout = powers_layout(model, content)

        title_rect = layout["title"]
        tbl_rect = layout["table"]
        detail_rect = layout["detail"]

        # Title
        f_title = _font(24, bold=True)
        title_surf = f_title.render("THE POWERS", True, INK)
        surface.blit(title_surf, (title_rect.left, title_rect.top))

        # Table
        tbl = model.table
        tbl_layout = tbl.layout(tbl_rect)

        # Draw header
        f_h = _font(tbl.size, bold=True)
        for i, col in enumerate(tbl.cols):
            if i < len(tbl_layout.header_rects):
                h_rect = tbl_layout.header_rects[i]
                txt = f_h.render(col.header, True, INK)
                text_rect = tbl_layout.text_rects[0][i] if i < len(tbl_layout.text_rects[0]) else h_rect
                surface.blit(txt, text_rect)

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
                txt = f_b.render(cell, True, INK)
                surface.blit(txt, text_rect)

        # Overflow warning
        if model.overflow_name is not None:
            warn = f_b.render(f"⚠ {model.overflow_name}", True, TONES.get("warn", INK))
            surface.blit(warn, (tbl_rect.left, tbl_rect.bottom + 4))

        # Empty roster message
        if not lines:
            empty_text = model.texts.get("empty", "(no rival House stands against you)")
            empty_surf = f_b.render(empty_text, True, INK)
            surface.blit(empty_surf, (detail_rect.left + 8, detail_rect.top + 4))

        # Informant buttons
        self._informant_hits.clear()
        btn_rect = layout["buttons"]
        btn_y = btn_rect.top
        for ri in model.informant_rows:
            house = model.row_houses[ri]
            btn_label = f"Place informant: {house}"
            btn_surf = f_b.render(btn_label, True, INK)
            btn_x = btn_rect.left + 8
            btn_h = btn_surf.get_height() + 4
            btn_r = pygame.Rect(btn_x, btn_y, btn_surf.get_width() + 12, btn_h)
            pygame.draw.rect(surface, CARD_BG, btn_r)
            pygame.draw.rect(surface, CARD_EDGE, btn_r, 1)
            surface.blit(btn_surf, (btn_r.left + 6, btn_r.top + 2))
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
        actions.append({"label": "Found Enterprise", "action": {"found_enterprise": True}, "eid": None})
        # Defend buyouts — for each venture with outside holders
        for el in r.enterprises:
            if el.top_outside is not None:
                outside_id, outside_pct = el.top_outside
                ent = next((e for e in g.enterprises if e.eid == el.eid), None)
                if ent is not None:
                    price = share_price(ent, g) * outside_pct
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
            actions.append({
                "label": f"Hostile Takeover of {target_house}",
                "action": {"attack_takeover": target_house},
                "eid": None
            })
        return actions

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
                text_rect = tbl_layout.text_rects[0][i] if i < len(tbl_layout.text_rects[0]) else h_rect
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
                pygame.draw.rect(surface, (240, 220, 210), row_rect)
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
                continue
            ent = next((e for e in self.game.enterprises if e.eid == eid), None)
            if ent is None:
                continue

            if verb == "expand_enterprise":
                # Skip expand if under construction or at max tier
                if ent.under_construction > 0 or ent.target_tier >= TIER_MAX:
                    if ent.under_construction > 0:
                        reason = f"{ent.name} is still building; it cannot expand until the work is finished."
                    else:
                        reason = f"{ent.name} is already at its greatest extent."
                    btn_text = act.get("label", f"Expand {ent.name}")
                    btn_surf = body.render(btn_text, True, FADED)
                    btn_w = btn_surf.get_width() + 16
                    btn_h = body.get_height() + 8
                    btn_rect = pygame.Rect(action_rect.left, y, btn_w, btn_h)
                    if y + btn_h > content.bottom:
                        return
                    pygame.draw.rect(surface, BUTTON_BG, btn_rect)
                    pygame.draw.rect(surface, BUTTON_EDGE, btn_rect, 2)
                    surface.blit(btn_surf, (action_rect.left + 8, y + 4))
                    self.regions.add(Region(rect=btn_rect, action=act.get("action", act), state=RegionState.DISABLED, reason=reason, group=f"venture:{eid}"))
                    y += btn_h + 4
                    continue
                btn_text = act.get("label", f"Expand {ent.name}")
                btn_surf = body.render(btn_text, True, INK)
                btn_w = btn_surf.get_width() + 16
                btn_h = body.get_height() + 8
                btn_rect = pygame.Rect(action_rect.left, y, btn_w, btn_h)
                if y + btn_h > content.bottom:
                    return
                pygame.draw.rect(surface, BUTTON_BG, btn_rect)
                pygame.draw.rect(surface, BUTTON_EDGE, btn_rect, 2)
                surface.blit(btn_surf, (action_rect.left + 8, y + 4))
                self._enterprise_hits.append((btn_rect, act))
                self.regions.add(Region(rect=btn_rect, action=act.get("action", act), hint=act.get("label", ""), group=f"venture:{eid}"))
                y += btn_h + 4

            elif verb == "appoint_director":
                pool = director_candidates(self.game, self.house, eid)
                if not pool:
                    reason = f"No one in the house pool is fit to direct {ent.name}."
                    btn_text = act.get("label", f"Appoint Director for {ent.name}")
                    btn_surf = body.render(btn_text, True, FADED)
                    btn_w = btn_surf.get_width() + 16
                    btn_h = body.get_height() + 8
                    btn_rect = pygame.Rect(action_rect.left, y, btn_w, btn_h)
                    if y + btn_h > content.bottom:
                        return
                    pygame.draw.rect(surface, BUTTON_BG, btn_rect)
                    pygame.draw.rect(surface, BUTTON_EDGE, btn_rect, 2)
                    surface.blit(btn_surf, (action_rect.left + 8, y + 4))
                    self.regions.add(Region(rect=btn_rect, action=act.get("action", act), state=RegionState.DISABLED, reason=reason, group=f"venture:{eid}"))
                    y += btn_h + 4
                    continue
                btn_text = act.get("label", f"Appoint Director for {ent.name}")
                btn_surf = body.render(btn_text, True, INK)
                btn_w = btn_surf.get_width() + 16
                btn_h = body.get_height() + 8
                btn_rect = pygame.Rect(action_rect.left, y, btn_w, btn_h)
                if y + btn_h > content.bottom:
                    return
                pygame.draw.rect(surface, (50, 50, 70), btn_rect)
                pygame.draw.rect(surface, INK, btn_rect, 2)
                surface.blit(btn_surf, (action_rect.left + 8, y + 4))
                self._appoint_hits.append((btn_rect, act))
                self.regions.add(Region(rect=btn_rect, action=act.get("action", act), hint=act.get("label", ""), group=f"venture:{eid}"))
                y += btn_h + 4

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
        pygame.draw.rect(surface, (70, 70, 50), back_rect)
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
        small = _font(16)
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
            pygame.draw.rect(surface, (60, 60, 60), ln_rect)
            pygame.draw.rect(surface, INK, ln_rect, 1)
            surface.blit(ln_surf, (PAD + 8, y + 4))
            self._director_picker_hits.append((ln_rect, {
                "appoint_director": eid, "char_id": c.id
            }))
            self.regions.add(Region(rect=ln_rect, action={"appoint_director": eid, "char_id": c.id}, hint=f"Appoint {c.name} to direct {ent.name}.", group="picker"))
            y += ln_h + 2

    def _draw_house(self, surface, content: pygame.Rect) -> None:
        g, name = self.game, self.house
        house = g.houses[name]
        realm = g.realms.get(name)
        title = _font(30, bold=True).render(f"HOUSE {name.upper()}", True, INK)
        surface.blit(title, (PAD, content.y + 6))
        y = content.y + 6 + title.get_height() + 10
        body = _font(18)
        rows = [
            f"treasury {house.treasury:.0f} gold   prestige {house.prestige:.0f}",
            f"legitimacy {g.legitimacy.get(name, 0.0):.0f}",
            f"capital {g.atlas.provinces[house.capital].name}",
            f"at war with: {', '.join(sorted(house.at_war_with)) or 'no one'}",
        ]
        if realm is not None:
            rows.append(f"ruler: {realm.ruler.name if realm.ruler else '(vacant)'}")
            for seat, holder in sorted(realm.court.positions.items(),
                                       key=lambda kv: kv[0].value):
                rows.append(f"  {seat.value}: "
                            f"{holder.name if holder is not None else '(vacant)'}")
        for row in rows:
            if y > content.bottom - 20:
                return
            surface.blit(body.render(row, True, INK), (PAD, y))
            y += body.get_height() + 4

    # --- clicking ------------------------------------------------------------

    def handle_click(self, pos: Tuple[int, int]) -> Optional[dict]:
        region = self.regions.at(pos)
        if region is not None:
            if region.state is RegionState.DISABLED:
                return None
            action = region.action
            if "tab" in action:
                self.active_tab = action["tab"]
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
            if "appoint_director" in action:
                if "char_id" not in action:
                    eid = action["appoint_director"]
                    self._director_picker = eid
                    self._director_picker_hits.clear()
                    return {"open_director_picker": eid}
            if "close_director_picker" in action:
                self._director_picker = None
                self._director_picker_hits.clear()
            return action
        for name, rect in self._tab_rects.items():
            if rect.collidepoint(pos):
                self.active_tab = name
                return {"tab": name}
        if self._end_turn_rect is not None and self._end_turn_rect.collidepoint(pos):
            return {"end_turn": True}
        if self._narrate_rect is not None and self._narrate_rect.collidepoint(pos):
            return {"toggle_narrate": True}
        if self.active_tab == "Enterprises":
            if self._director_picker is not None:
                for rect, action in self._director_picker_hits:
                    if rect.collidepoint(pos):
                        if "close_director_picker" in action:
                            self._director_picker = None
                            self._director_picker_hits.clear()
                        return action
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
