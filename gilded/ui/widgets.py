"""Gilded UI – widget vocabulary.

Bottom of the UI stack: pygame + stdlib only.  No imports of
other gilded.ui modules.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Sequence

import pygame


# ────────────────────────────────────────────────────────────────────────────
# Palette
# ────────────────────────────────────────────────────────────────────────────

INK = (28, 24, 20)
FADED = (96, 88, 78)
PAPER_BG = (238, 232, 218)
CARD_BG = (248, 244, 234)
CARD_EDGE = (120, 108, 92)

# ────────────────────────────────────────────────────────────────────────────
# Screen palette — colours shared across all rendered screens
# ────────────────────────────────────────────────────────────────────────────

BLACK = (0, 0, 0)
PANEL_BG = (18, 16, 14)
TAB_BG = (54, 48, 42)
TAB_ACTIVE = (206, 176, 108)
TAB_TEXT = (232, 226, 210)
HUD_BG = (44, 40, 34)
HUD_INK = (232, 226, 210)
BUTTON_BG = (60, 82, 60)
BUTTON_EDGE = (30, 46, 30)
BUTTON_TEXT = (238, 240, 232)
DISABLED_BUTTON_BG = (30, 30, 30)
DISABLED_BUTTON_EDGE = (35, 35, 35)
EXEC_BG = (78, 66, 96)
ENDTURN_BG = (140, 60, 52)
ATTN_COLOR = (150, 110, 40)
SKIM_HIGHLIGHT = (240, 220, 210)
PICKER_BACK_BG = (70, 70, 50)
PICKER_ROW_BG = (60, 60, 60)
DISABLED_FILL = (60, 60, 50)
DISABLED_EDGE = (100, 80, 60)
DISABLED_TEXT = (140, 120, 100)
PICKER_SUBTITLE = (160, 160, 140)
PICKER_ROW_ALT_BG = (60, 60, 40)
OFFERABLE_BG = (50, 50, 35)
OFFERABLE_EDGE = (120, 120, 100)
HOUSE_COLORS = [(122, 74, 58), (58, 90, 122), (74, 106, 74), (140, 120, 60),
                (110, 70, 110), (70, 110, 110), (150, 90, 70), (95, 95, 130)]
MINOR_COLOR = (90, 90, 90)
OCEAN_COLOR = (26, 35, 51)
FRONT_COLOR = (208, 64, 64)
BORDER_COLOR = (12, 12, 12)
NAME_COLOR = (232, 226, 210)
GLYPH_COLOR = (250, 240, 200)
RAIL_COLOR = (198, 164, 84)
SELECT_COLOR = (245, 245, 235)

# ────────────────────────────────────────────────────────────────────────────
# Typographic constants (Wave 5)
# ────────────────────────────────────────────────────────────────────────────

MEASURE_CHARS = 66   # comfortable line length at 18pt
COLUMN_GAP = 24      # gutter between columns in pixels


# ────────────────────────────────────────────────────────────────────────────
# Interaction regions — WAVE I1
# ────────────────────────────────────────────────────────────────────────────

from enum import Enum


class RegionState(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    ACTIVE = "active"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class Region:
    rect: pygame.Rect
    action: dict | None
    state: RegionState = RegionState.ENABLED
    reason: str = ""
    hint: str = ""
    group: str = ""

    def __post_init__(self) -> None:
        if self.state is RegionState.DISABLED and not self.reason:
            raise ValueError(
                "A DISABLED Region must carry a non-empty reason"
            )
        if self.state is RegionState.ENABLED and self.action is None:
            raise ValueError(
                "An ENABLED Region must carry an action"
            )


class RegionSet:
    """Collects interactive regions in draw order; hit-tests scan in reverse."""

    def __init__(self) -> None:
        self._regions: list[Region] = []

    def add(self, region: Region) -> None:
        self._regions.append(region)

    def at(self, pos: tuple[int, int]) -> Region | None:
        for region in reversed(self._regions):
            if region.rect.collidepoint(pos):
                return region
        return None

    def clear(self) -> None:
        self._regions.clear()

    def __len__(self) -> int:
        return len(self._regions)


# ────────────────────────────────────────────────────────────────────────────
# TONES – colour meaning
# ────────────────────────────────────────────────────────────────────────────

TONES: dict[str, tuple[int, int, int]] = {
    "good": (34, 120, 68),
    "bad": (180, 50, 40),
    "warn": (200, 150, 30),
    "neutral": (97, 97, 106),
    "dead": (160, 160, 165),
}


# ────────────────────────────────────────────────────────────────────────────
# Font helpers
# ────────────────────────────────────────────────────────────────────────────

_font_cache: dict[tuple[int, bool], pygame.font.Font] = {}


def font(size: int, bold: bool = False) -> pygame.font.Font:
    """Cached SysFont("georgia,serif"), lazily calling pygame.font.init()."""
    key = (size, bold)
    if key not in _font_cache:
        if not pygame.font.get_init():
            pygame.font.init()
        _font_cache[key] = pygame.font.SysFont("georgia,serif", size, bold)
    return _font_cache[key]


def wrap(text: str, f: pygame.font.Font, width: int) -> list[str]:
    """Word-wrap *text* into lines that fit within *width* pixels."""
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    for words_in_line in _word_groups(words, f, width):
        lines.append(" ".join(words_in_line))
    return lines


def _word_groups(words: list[str], f: pygame.font.Font, width: int) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    for word in words:
        test = current + [word]
        surf = f.render(" ".join(test), False, (0, 0, 0))
        if surf.get_width() <= width:
            current.append(word)
        else:
            if current:
                groups.append(current)
            # single word wider than width → it still goes in on its own line
            if surf.get_width() <= width:
                current = [word]
            else:
                groups.append(current)
                current = [word]
                # force-break the long word if needed
                if f.render(word, False, (0, 0, 0)).get_width() > width:
                    groups.append([word])
                    current = []
    if current:
        groups.append(current)
    return groups


# ────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ────────────────────────────────────────────────────────────────────────────


def columns(rect: pygame.Rect, n: int, gap: int = 0) -> list[pygame.Rect]:
    """n equal-width, full-height, non-overlapping rects tiling rect horizontally.

    For weighted columns use _weighted_columns instead.
    """
    if n <= 0:
        return []
    total_gap = gap * max(n - 1, 0)
    total_width = rect.width - total_gap
    base_width = total_width // n
    remainder = total_width - base_width * n  # goes to the last column
    cols: list[pygame.Rect] = []
    x = rect.left
    for i in range(n):
        w = base_width + (remainder if i == n - 1 else 0)
        cols.append(pygame.Rect(x, rect.top, w, rect.height))
        x += w + gap
    return cols


def _weighted_columns(
    rect: pygame.Rect, weights: Sequence[float], gap: int = 0
) -> list[pygame.Rect]:
    """Weighted horizontal columns.  Last column ends on rect.right."""
    if not weights:
        return []
    n = len(weights)
    total_weight = sum(weights)
    total_gap = gap * max(n - 1, 0)
    available = rect.width - total_gap
    base_width = available / total_weight
    cols: list[pygame.Rect] = []
    x = rect.left
    for i, weight in enumerate(weights):
        w = int(weight * base_width)
        if i == n - 1:
            w = rect.right - x
        cols.append(pygame.Rect(x, rect.top, w, rect.height))
        x += w + gap
    return cols


def rows(rect: pygame.Rect, heights: Sequence[float], gap: int = 0) -> list[pygame.Rect]:
    """Weighted vertical rows.  Last row ends on rect.bottom."""
    if not heights:
        return []
    n = len(heights)
    total_weight = sum(heights)
    total_gap = gap * max(n - 1, 0)
    available = rect.height - total_gap
    base_height = available / total_weight
    row_rects: list[pygame.Rect] = []
    y = rect.top
    for i, weight in enumerate(heights):
        h = int(weight * base_height)
        if i == n - 1:
            # last row fills to the bottom
            h = rect.bottom - y - (0 if i == n - 1 else 0)
        row_rects.append(pygame.Rect(rect.left, y, rect.width, h))
        y += h + gap
    return row_rects


# ────────────────────────────────────────────────────────────────────────────
# Column layout helpers (Wave 5)
# ────────────────────────────────────────────────────────────────────────────


@dataclass
class FlowResult:
    """Result of flowing items into columns."""
    placements: list  # list of (text, x, y, col_index)
    overflow: int     # number of lines that did not fit


def column_plan(
    rect: pygame.Rect,
    font: pygame.font.Font,
    *,
    chars: int = MEASURE_CHARS,
    gap: int = COLUMN_GAP,
) -> list[pygame.Rect]:
    """Compute column rects: measure-capped, centred in *rect*.

    Returns a list of non-overlapping rects left-to-right, all inside *rect*,
    horizontally centred (left/right margins differ by at most 1px).
    """
    measure_px = font.size("x" * chars)[0]
    n = max(1, (rect.width + gap) // (measure_px + gap))
    col_w = min(measure_px, (rect.width - gap * (n - 1)) // n)
    block = col_w * n + gap * (n - 1)
    margin = (rect.width - block) // 2
    # Shift rect right by margin, then use columns() to tile
    shifted = pygame.Rect(rect.left + margin, rect.top, block, rect.height)
    raw = columns(shifted, n, gap)
    # Cap each column to col_w (columns() may give the last one extra for remainder)
    return [pygame.Rect(c.x, c.y, col_w, c.height) for c in raw]


def flow_columns(
    items: list[str],
    font: pygame.font.Font,
    rect: pygame.Rect,
    line_gap: int,
) -> FlowResult:
    """Flow *items* into columns, column-major order.

    Each item is wrapped to the column width.  Lines fill column 0, then column 1, etc.
    Returns a FlowResult with placements and overflow count.
    """
    cols = column_plan(rect, font)
    if not cols:
        return FlowResult(placements=[], overflow=0)

    col_w = cols[0].width
    line_h = font.size("x")[1]

    # Pre-wrap all items to column width
    all_lines = []
    for item in items:
        lines = wrap(item, font, col_w)
        all_lines.extend(lines)

    # Calculate capacity per column
    capacity = 0
    y = rect.top
    while y + line_h <= rect.bottom:
        capacity += 1
        y += line_h + line_gap

    # Flow column-major: fill col 0, then col 1, etc.
    placements = []
    idx = 0
    for ci, col in enumerate(cols):
        y = col.top
        for _ in range(capacity):
            if idx >= len(all_lines):
                break
            line_text = all_lines[idx]
            idx += 1
            placements.append((line_text, col.x, y, ci))
            y += line_h + line_gap

    overflow = len(all_lines) - len(placements)
    return FlowResult(placements=placements, overflow=max(0, overflow))


# ────────────────────────────────────────────────────────────────────────────
# Column / Table
# ────────────────────────────────────────────────────────────────────────────

_NUMBER_RE = re.compile(r"^[+-]?[$]?[0-9,]+(\.[0-9]+)?%?$")


@dataclass(frozen=True)
class Column:
    header: str
    width: float = 1.0
    align: str | None = None  # "left", "right", or None → INFER


@dataclass
class TableLayout:
    header_rects: list[pygame.Rect]
    rule_y: int
    row_rects: list[pygame.Rect]
    cell_rects: list[list[pygame.Rect]]
    text_rects: list[list[pygame.Rect]]


class Table:
    def __init__(
        self,
        cols: Sequence[Column],
        data: Sequence[Sequence[str]],
        size: int = 14,
        row_rule: bool = False,
    ):
        self.cols = list(cols)
        self.data = list(data)
        self.size = size
        self.row_rule = row_rule

    def height(self) -> int:
        """Pixel height needed for the table."""
        f = font(self.size, bold=True)
        header_h = f.get_linesize()
        f_body = font(self.size)
        body_h = f_body.get_linesize()
        row_count = len(self.data)
        gap = 2
        rule_h = 1 if self.row_rule else 0
        return header_h + rule_h + gap + row_count * (body_h + gap)

    def _resolve_align(self, col_idx: int) -> str:
        col = self.cols[col_idx]
        if col.align is not None:
            return col.align
        # infer: if every non-blank cell parses as a number → right
        for row in self.data:
            if col_idx < len(row):
                cell = row[col_idx].strip()
                if cell and not _NUMBER_RE.match(cell):
                    return "left"
        return "right"

    def layout(self, rect: pygame.Rect) -> TableLayout:
        f_header = font(self.size, bold=True)
        f_body = font(self.size)
        header_h = f_header.get_linesize()
        body_h = f_body.get_linesize()
        gap = 2
        rule_h = 1 if self.row_rule else 1  # always draw a rule

        # header row — weighted by Column.width
        weights = [c.width for c in self.cols]
        col_rects = _weighted_columns(rect, weights, gap=0)
        header_rects = [r.copy() for r in col_rects]
        for r in header_rects:
            r.height = header_h

        rule_y = rect.top + header_h + rule_h

        # data rows
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
            row_gap = 2
            row_rects = []
            y = data_top
            for i in range(row_count):
                h = row_h
                if i == row_count - 1:
                    h = data_bottom - y
                row_rects.append(pygame.Rect(rect.left, y, rect.width, h))
                y += h + row_gap

            # cell rects & text rects
            cell_rects = []
            text_rects = []
            for row_idx, row_rect in enumerate(row_rects):
                row = self.data[row_idx] if row_idx < len(self.data) else []
                weights = [c.width for c in self.cols]
                row_cells = _weighted_columns(row_rect, weights, gap=0)
                cell_rects.append(list(row_cells))
                row_text_rects: list[pygame.Rect] = []
                for col_idx in range(len(self.cols)):
                    cell = row[col_idx] if col_idx < len(row) else ""
                    align = self._resolve_align(col_idx)
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

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> TableLayout:
        lay = self.layout(rect)
        f_header = font(self.size, bold=True)
        f_body = font(self.size)

        # draw headers
        for i, col in enumerate(self.cols):
            hr = lay.header_rects[i]
            text = f_header.render(col.header, True, INK)
            x = hr.left + 4
            y = hr.centery - text.get_height() // 2
            surface.blit(text, (x, y))

        # draw rule
        if self.row_rule:
            pygame.draw.line(surface, CARD_EDGE, (rect.left, lay.rule_y), (rect.right, lay.rule_y))

        # draw data
        for row_idx, row_rect in enumerate(lay.row_rects):
            row = self.data[row_idx] if row_idx < len(self.data) else []
            for col_idx in range(len(self.cols)):
                cell = row[col_idx] if col_idx < len(row) else ""
                tr = lay.text_rects[row_idx][col_idx]
                text = f_body.render(cell, True, INK)
                surface.blit(text, (tr.x, tr.y))

        return lay


def _place_text(
    text: str,
    f: pygame.font.Font,
    cell: pygame.Rect,
    align: str,
    line_h: int,
) -> pygame.Rect:
    if not text.strip():
        return pygame.Rect(cell.x + 4, cell.centery - line_h // 2, 0, line_h)
    surf = f.render(text, True, (0, 0, 0))
    tw = surf.get_width()
    th = surf.get_height()
    inset = 4
    y = cell.centery - th // 2
    if align == "right":
        x = cell.right - tw - inset
    else:
        x = cell.left + inset
    return pygame.Rect(x, y, tw, th)


# ────────────────────────────────────────────────────────────────────────────
# Meter
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class MeterLayout:
    label_rect: pygame.Rect
    bar_rect: pygame.Rect
    fill_rect: pygame.Rect
    value_rect: pygame.Rect
    arrow_rect: pygame.Rect | None


class Meter:
    def __init__(
        self,
        label: str,
        value: float,
        lo: float,
        hi: float,
        delta: float | None = None,
        danger: tuple[str, float] | None = None,
        invert: bool = False,
        size: int = 14,
        fmt: str = "{:.0f}",
    ):
        self.label = label
        self.value = value
        self.lo = lo
        self.hi = hi
        self.delta = delta
        self.danger = danger
        self.invert = invert
        self.size = size
        self.fmt = fmt

    def value_text(self) -> str:
        return self.fmt.format(self.value)

    def fraction(self) -> float:
        if self.hi == self.lo:
            return 1.0
        frac = (self.value - self.lo) / (self.hi - self.lo)
        return max(0.0, min(1.0, frac))

    def tone(self) -> str:
        # danger check
        if self.danger:
            direction, threshold = self.danger
            if direction == "below" and self.value <= threshold:
                return "bad"
            if direction == "above" and self.value >= threshold:
                return "bad"
        return "neutral"

    def arrow(self) -> str:
        if self.delta is None:
            return ""
        if self.delta == 0:
            return "—"
        if self.delta > 0:
            return "▲" if not self.invert else "▼"
        return "▼" if not self.invert else "▲"

    def delta_tone(self) -> str:
        if self.delta is None:
            return "neutral"
        if self.delta == 0:
            return "neutral"
        if self.delta > 0:
            return "bad" if self.invert else "good"
        return "good" if self.invert else "bad"

    def layout(self, rect: pygame.Rect) -> MeterLayout:
        f = font(self.size)
        label_surf = f.render(self.label, True, INK)
        value_surf = f.render(self.value_text(), True, INK)
        arrow_surf = None
        if self.delta is not None:
            arrow_surf = f.render(self.arrow(), True, TONES.get(self.delta_tone(), INK))

        label_w = label_surf.get_width()
        label_h = label_surf.get_height()
        value_w = value_surf.get_width()
        value_h = value_surf.get_height()
        arrow_w = arrow_surf.get_width() if arrow_surf else 0
        arrow_h = arrow_surf.get_height() if arrow_surf else 0

        gap = 6
        # horizontal: label | bar | arrow | value
        # arrow sits inline between bar and value when present
        arrow_reserve = (arrow_w + gap) if arrow_surf else 0
        right_reserve = arrow_reserve + value_w
        available = rect.width - label_w - gap - right_reserve
        if available < 0:
            available = 0

        bar_h = max(12, min(20, rect.height))
        bar_top = rect.top + (rect.height - bar_h) // 2
        bar_left = rect.left + label_w + gap
        bar_rect = pygame.Rect(bar_left, bar_top, max(0, available), bar_h)

        frac = self.fraction()
        fill_w = int(bar_rect.width * frac)
        fill_rect = pygame.Rect(bar_rect.left, bar_rect.top, fill_w, bar_rect.height)

        label_rect = pygame.Rect(rect.left, rect.top, label_w, label_h)

        arrow_rect: pygame.Rect | None = None
        if arrow_surf:
            # place arrow inline between bar and value
            ax = bar_rect.right + gap
            ay = bar_top + (bar_h - arrow_h) // 2
            # if arrow doesn't fit horizontally, try to squeeze it in
            if ax + arrow_w > rect.right - value_w:
                # clamp: put it right after bar, value may need to move
                ax = bar_rect.right + gap
                ay = bar_top + (bar_h - arrow_h) // 2
            arrow_rect = pygame.Rect(ax, ay, arrow_w, arrow_h)

        # Place value after arrow (or after bar if no arrow)
        if arrow_rect:
            val_x = arrow_rect.right + gap
        else:
            val_x = bar_rect.right + gap
        # clamp value to rect
        val_x = min(val_x, rect.right - value_w)
        value_rect = pygame.Rect(val_x, bar_top, value_w, value_h)

        return MeterLayout(
            label_rect=label_rect,
            bar_rect=bar_rect,
            fill_rect=fill_rect,
            value_rect=value_rect,
            arrow_rect=arrow_rect,
        )

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> MeterLayout:
        lay = self.layout(rect)
        f = font(self.size)

        # label
        label_surf = f.render(self.label, True, INK)
        surface.blit(label_surf, lay.label_rect.topleft)

        # bar outline
        pygame.draw.rect(surface, CARD_EDGE, lay.bar_rect, 1)

        # fill
        tone_color = TONES.get(self.tone(), INK)
        if lay.fill_rect.width > 0:
            pygame.draw.rect(surface, tone_color, lay.fill_rect)

        # value
        value_surf = f.render(self.value_text(), True, INK)
        surface.blit(value_surf, lay.value_rect.topleft)

        # arrow
        if lay.arrow_rect is not None:
            arrow_color = TONES.get(self.delta_tone(), INK)
            arrow_surf = f.render(self.arrow(), True, arrow_color)
            surface.blit(arrow_surf, lay.arrow_rect.topleft)

        return lay


# ────────────────────────────────────────────────────────────────────────────
# Chip
# ────────────────────────────────────────────────────────────────────────────

_CHIP_PAD_X = 8
_CHIP_PAD_Y = 4


class Chip:
    def __init__(self, text: str, tone: str = "neutral", pt: int = 13):
        if tone not in TONES:
            raise ValueError(f"unknown tone: {tone!r}")
        self.text = text
        self.tone = tone
        self.pt = pt

    def bg(self) -> tuple[int, int, int]:
        return TONES[self.tone]

    def ink(self) -> tuple[int, int, int]:
        bg_lum = _luminance(self.bg())
        # pick ink that contrasts by at least 90
        if bg_lum > 128:
            return (0, 0, 0)
        return (255, 255, 255)

    def size(self) -> tuple[int, int]:
        f = font(self.pt)
        surf = f.render(self.text, True, (0, 0, 0))
        return (surf.get_width() + _CHIP_PAD_X * 2, surf.get_height() + _CHIP_PAD_Y * 2)

    def draw(self, surface: pygame.Surface, pos: tuple[int, int]) -> pygame.Rect:
        s = self.size()
        rect = pygame.Rect(pos[0], pos[1], s[0], s[1])
        pygame.draw.rect(surface, self.bg(), rect, border_radius=6)
        f = font(self.pt)
        text_surf = f.render(self.text, True, self.ink())
        tx = rect.left + _CHIP_PAD_X
        ty = rect.centery - text_surf.get_height() // 2
        surface.blit(text_surf, (tx, ty))
        return rect


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (v / 255.0 for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ────────────────────────────────────────────────────────────────────────────
# Panel
# ────────────────────────────────────────────────────────────────────────────

_PANEL_PAD = 8
_PANEL_BORDER = 1
_TITLE_GAP = 4


class Panel:
    def __init__(self, rect: pygame.Rect, title: str = "", size: int = 14):
        self.rect = rect
        self.title = title
        self.size = size

    def inner(self) -> pygame.Rect:
        r = pygame.Rect(
            self.rect.left + _PANEL_PAD + _PANEL_BORDER,
            self.rect.top + _PANEL_PAD + _PANEL_BORDER,
            self.rect.width - 2 * (_PANEL_PAD + _PANEL_BORDER),
            self.rect.height - 2 * (_PANEL_PAD + _PANEL_BORDER),
        )
        if self.title:
            f = font(self.size, bold=True)
            title_h = f.get_linesize() + _TITLE_GAP
            r.top += title_h
            r.height -= title_h
        # clamp to non-negative
        if r.width < 0:
            r.width = 0
        if r.height < 0:
            r.height = 0
        return r

    def draw(self, surface: pygame.Surface) -> pygame.Rect:
        # draw border
        pygame.draw.rect(surface, CARD_EDGE, self.rect, width=_PANEL_BORDER * 2)
        # draw title
        if self.title:
            f = font(self.size, bold=True)
            title_surf = f.render(self.title, True, INK)
            tx = self.rect.left + _PANEL_PAD + _PANEL_BORDER
            ty = self.rect.top + _PANEL_PAD + _PANEL_BORDER
            surface.blit(title_surf, (tx, ty))
        return self.inner()
