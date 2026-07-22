"""The broadsheet screens (mission G22): the century read as a newspaper.

BroadsheetView renders one House's world across six tabs. The paper tabs
(Gazette, Ledger, Letters) set papers.compose() in wrapped serif columns; the
Docket tab lays each petition out as a card with option buttons, an executor
cycle, and the attention still in hand; the Atlas tab hands off to atlas_view;
the House tab shows the court and the standing of the realm.

The view is a CLIENT. handle_click() never touches the game - it returns an
action dict (or None) and lets app.py apply it. Executor cycling is the one
exception that stays inside the view: it only changes which name a future
rule-action will carry.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

from gilded.papers import compose
from gilded.ui.atlas_view import (
    OCEAN_COLOR, draw_atlas, pick_province, province_panel_lines)

TABS = ("Gazette", "Ledger", "Letters", "Docket", "Atlas", "House")

TAB_H = 40
BOTTOM_H = 56
PAD = 16

PAPER_BG = (238, 232, 218)
INK = (28, 24, 20)
FADED = (96, 88, 78)
TAB_BG = (54, 48, 42)
TAB_ACTIVE = (206, 176, 108)
TAB_TEXT = (232, 226, 210)
CARD_BG = (248, 244, 234)
CARD_EDGE = (120, 108, 92)
BUTTON_BG = (60, 82, 60)
BUTTON_EDGE = (30, 46, 30)
BUTTON_TEXT = (238, 240, 232)
EXEC_BG = (78, 66, 96)
ENDTURN_BG = (140, 60, 52)
ATTN_COLOR = (150, 110, 40)

_font_cache: Dict[Tuple[str, int], pygame.font.Font] = {}


def _font(size: int, bold: bool = False) -> pygame.font.Font:
    key = ("serif" if not bold else "serif-bold", size)
    f = _font_cache.get(key)
    if f is None:
        if not pygame.font.get_init():
            pygame.font.init()
        f = pygame.font.SysFont("georgia,serif", size, bold=bold)
        _font_cache[key] = f
    return f


def _wrap(text: str, font: pygame.font.Font, width: int) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    cur = words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if font.size(trial)[0] <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


class BroadsheetView:
    def __init__(self, game, house_name: str):
        self.game = game
        self.house = house_name
        self.active_tab = TABS[0]
        self.selected_pid: Optional[int] = None
        # per-petition executor choice: an index into that card's candidate
        # list, where index 0 means "let the game pick the seat's default".
        self._exec_idx: Dict[int, int] = {}
        # hit regions, rebuilt every draw:
        self._tab_rects: Dict[str, pygame.Rect] = {}
        self._end_turn_rect: Optional[pygame.Rect] = None
        self._option_hits: List[Tuple[pygame.Rect, tuple]] = []
        self._exec_hits: List[Tuple[pygame.Rect, int]] = []
        self._atlas_polys: Dict[int, List[Tuple[int, int]]] = {}
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

    # --- drawing -------------------------------------------------------------

    def draw(self, surface) -> None:
        self._w, self._h = surface.get_size()
        self._option_hits = []
        self._exec_hits = []
        surface.fill(PAPER_BG)
        content = pygame.Rect(0, TAB_H, self._w, self._h - TAB_H - BOTTOM_H)

        if self.active_tab == "Atlas":
            self._draw_atlas(surface)
        elif self.active_tab in ("Gazette", "Ledger", "Letters"):
            self._draw_paper(surface, content)
        elif self.active_tab == "Docket":
            self._draw_docket(surface, content)
        elif self.active_tab == "House":
            self._draw_house(surface, content)

        self._draw_tab_bar(surface)
        self._draw_bottom_bar(surface)

    def _draw_tab_bar(self, surface) -> None:
        pygame.draw.rect(surface, TAB_BG, (0, 0, self._w, TAB_H))
        tabw = self._w // len(TABS)
        font = _font(18, bold=True)
        self._tab_rects = {}
        for i, name in enumerate(TABS):
            rect = pygame.Rect(i * tabw, 0, tabw, TAB_H)
            self._tab_rects[name] = rect
            if name == self.active_tab:
                pygame.draw.rect(surface, TAB_ACTIVE, rect)
            label = font.render(name, True,
                                INK if name == self.active_tab else TAB_TEXT)
            surface.blit(label, (rect.centerx - label.get_width() / 2,
                                 rect.centery - label.get_height() / 2))

    def _draw_bottom_bar(self, surface) -> None:
        y = self._h - BOTTOM_H
        pygame.draw.rect(surface, TAB_BG, (0, y, self._w, BOTTOM_H))
        attn = self.game.attention.get(self.house, 0)
        font = _font(18, bold=True)
        label = font.render(f"Attention: {attn}", True, ATTN_COLOR)
        surface.blit(label, (PAD, y + (BOTTOM_H - label.get_height()) / 2))
        rect = pygame.Rect(self._w - 170, y + 10, 154, BOTTOM_H - 20)
        self._end_turn_rect = rect
        pygame.draw.rect(surface, ENDTURN_BG, rect)
        et = font.render("End Turn", True, BUTTON_TEXT)
        surface.blit(et, (rect.centerx - et.get_width() / 2,
                          rect.centery - et.get_height() / 2))

    def _draw_paper(self, surface, content: pygame.Rect) -> None:
        report = compose(self.game, self.house)
        items = {"Gazette": report.gazette, "Ledger": report.ledger,
                 "Letters": report.letters}[self.active_tab]
        head = _font(30, bold=True).render(
            f"THE {self.active_tab.upper()} - {report.year}", True, INK)
        surface.blit(head, (PAD, content.y + 6))
        body = _font(18)
        y = content.y + 6 + head.get_height() + 10
        width = content.width - 2 * PAD
        if not items:
            items = ["(nothing to report)"]
        for item in items:
            for line in _wrap(item, body, width):
                if y > content.bottom - 20:
                    return
                surface.blit(body.render(line, True, INK), (PAD, y))
                y += body.get_height() + 2
            y += 6

    def _draw_docket(self, surface, content: pygame.Rect) -> None:
        petitions = self.game.docket_by_house.get(self.house, [])
        title = _font(30, bold=True).render("THE DOCKET", True, INK)
        surface.blit(title, (PAD, content.y + 6))
        y = content.y + 6 + title.get_height() + 10
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
                bx += bw + 8
            ex = self._chosen_executor(p.pid)
            ex_name = "executor: default" if ex is None else f"executor: {ex.name}"
            elabel = small.render(ex_name, True, BUTTON_TEXT)
            erect = pygame.Rect(bx, hy + 4, elabel.get_width() + 20, 26)
            pygame.draw.rect(surface, EXEC_BG, erect)
            pygame.draw.rect(surface, BUTTON_EDGE, erect, 1)
            surface.blit(elabel, (erect.x + 10, erect.y + 5))
            self._exec_hits.append((erect, p.pid))
            y += card_h + 10

    def _draw_atlas(self, surface) -> None:
        surface.fill(OCEAN_COLOR)
        self._atlas_polys = draw_atlas(surface, self.game, self.selected_pid)
        if self.selected_pid is not None:
            self._draw_panel(surface,
                             province_panel_lines(self.game, self.selected_pid))

    def _draw_panel(self, surface, lines: List[str]) -> None:
        font = _font(16)
        w = max(font.size(l)[0] for l in lines) + 2 * PAD
        h = len(lines) * (font.get_height() + 2) + 2 * PAD
        rect = pygame.Rect(self._w - w - PAD, TAB_H + PAD, w, h)
        panel = pygame.Surface(rect.size)
        panel.set_alpha(225)
        panel.fill((18, 16, 14))
        surface.blit(panel, rect.topleft)
        y = rect.y + PAD
        for i, line in enumerate(lines):
            f = _font(18, bold=True) if i == 0 else font
            surface.blit(f.render(line, True, TAB_TEXT), (rect.x + PAD, y))
            y += font.get_height() + 2

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
        for name, rect in self._tab_rects.items():
            if rect.collidepoint(pos):
                self.active_tab = name
                return {"tab": name}
        if self._end_turn_rect is not None and self._end_turn_rect.collidepoint(pos):
            return {"end_turn": True}
        if self.active_tab == "Docket":
            for rect, pid in self._exec_hits:
                if rect.collidepoint(pos):
                    cands = self._candidates(pid)
                    self._exec_idx[pid] = (self._exec_idx.get(pid, 0) + 1) % len(cands)
                    return None
            for rect, action in self._option_hits:
                if rect.collidepoint(pos):
                    _, pid, key, exec_id = action
                    return {"rule": (pid, key, exec_id)}
        if self.active_tab == "Atlas":
            pid = pick_province(self.game.atlas, self._atlas_polys, pos)
            if pid is not None:
                self.selected_pid = pid
                return {"select_province": pid}
        return None