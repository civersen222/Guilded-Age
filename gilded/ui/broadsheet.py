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

from typing import Dict, List, Optional, Tuple

import pygame

from gilded.dashboard import delta, scoreboard
from gilded.grip import report as grip_report
from gilded.intel import report as intel_report, threat_rank
from gilded.market import COMMODITIES
from gilded.papers import compose
from gilded.saga.narrator import NarratorTemplated
from gilded.ui.atlas_view import (
    OCEAN_COLOR, draw_atlas, pick_province, province_panel_lines)

TABS = ("Briefing", "Gazette", "Ledger", "Letters", "Docket", "Policies", "Enterprises", "Atlas", "Powers", "House")

TAB_H = 40
HUD_H = 96
BOTTOM_H = 56
PAD = 16

PAPER_BG = (238, 232, 218)
INK = (28, 24, 20)
FADED = (96, 88, 78)
TAB_BG = (54, 48, 42)
TAB_ACTIVE = (206, 176, 108)
TAB_TEXT = (232, 226, 210)
HUD_BG = (44, 40, 34)
HUD_INK = (232, 226, 210)
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
        self._dial_hits = []
        surface.fill(PAPER_BG)
        content = pygame.Rect(0, TAB_H + HUD_H, self._w,
                              self._h - TAB_H - HUD_H - BOTTOM_H)

        if self.active_tab == "Briefing":
            self._draw_briefing(surface, content)
        elif self.active_tab == "Atlas":
            self._draw_atlas(surface)
        elif self.active_tab in ("Gazette", "Ledger", "Letters"):
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
        for i, name in enumerate(TABS):
            rect = pygame.Rect(i * tabw, 0, tabw, TAB_H)
            self._tab_rects[name] = rect
            if name == self.active_tab:
                pygame.draw.rect(surface, TAB_ACTIVE, rect)
            label = font.render(name, True,
                                INK if name == self.active_tab else TAB_TEXT)
            surface.blit(label, (rect.centerx - label.get_width() / 2,
                                 rect.centery - label.get_height() / 2))

    def _draw_hud(self, surface) -> None:
        b = scoreboard(self.game, self.house)
        y0 = TAB_H
        pygame.draw.rect(surface, HUD_BG, (0, y0, self._w, HUD_H))
        strong = _font(16, bold=True)
        fs = _font(15)
        line_h = fs.get_height() + 3
        x = PAD
        y = y0 + 6
        axis_str = "    ".join(
            f"{name.capitalize()} {b.axes[name]:.0f}"
            for name in ("capital", "standing", "blood", "world"))
        surface.blit(strong.render(axis_str, True, HUD_INK), (x, y))
        y += line_h
        surface.blit(fs.render(
            f"Legitimacy {b.legitimacy:.0f}    Treasury {b.treasury:.0f}    "
            f"Tide {b.tide_level:.0f} ({b.tide_phase})    "
            f"Atrocities {b.atrocities:.0f}", True, HUD_INK), (x, y))
        y += line_h
        surface.blit(fs.render(
            f"{b.era_title}   -   {b.next_era}   -   "
            f"{b.year} ({b.century_pct * 100:.0f}% of the century)",
            True, HUD_INK), (x, y))
        y += line_h
        rival = (f"Rival: House {b.rival_name}" if b.rival_name
                 else "Rival: none yet")
        surface.blit(fs.render(
            f"{rival}    You rank #{b.rank} of {len(self.game.houses)}",
            True, HUD_INK), (x, y))
        y += line_h
        spotlight = b.rival_name or (
            threat_rank(self.game)[0] if threat_rank(self.game) else None)
        if spotlight is not None:
            intent = intel_report(self.game, self.house, spotlight).apparent_intent
            surface.blit(fs.render(f"Their design: {intent}", True, HUD_INK),
                         (x, y))

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
        pygame.draw.rect(surface, EXEC_BG, nrect)
        surface.blit(nlabel, (nrect.centerx - nlabel.get_width() / 2,
                              nrect.centery - nlabel.get_height() / 2))
        rect = pygame.Rect(self._w - 170, y + 10, 154, BOTTOM_H - 20)
        self._end_turn_rect = rect
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
                out.append(f"{name.capitalize()} {cue(md)} {abs(md.change):.0f}")
        pairs = (("Legitimacy", d.legitimacy), ("Treasury", d.treasury),
                 ("Tide", d.tide_level), ("Unrest", d.unrest_avg))
        for label, md in pairs:
            if md.direction:
                out.append(f"{label} {cue(md)} {abs(md.change):.0f}")
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
            y += card_h + 10

    def _draw_paper(self, surface, content: pygame.Rect) -> None:
        report = compose(self.game, self.house)
        if self.narrate_on and self.active_tab == "Gazette":
            report = self.narrator.render(report, self.game.director, self.game)
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
            self._dial_hits.append((track_rect, key))
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
        rect = pygame.Rect(self._w - w - PAD, TAB_H + HUD_H + PAD, w, h)
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
        title = _font(30, bold=True).render("THE POWERS", True, INK)
        surface.blit(title, (PAD, content.y + 6))
        y = content.y + 6 + title.get_height() + 10
        body = _font(18)
        width = content.width - 2 * PAD
        lines = self.powers_lines()
        if not lines:
            lines = ["(no rival House stands against you)"]
        for ln in lines:
            for wln in _wrap(ln, body, width):
                if y > content.bottom - 20:
                    return
                surface.blit(body.render(wln, True, INK), (PAD, y))
                y += body.get_height() + 2
            y += 6

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
        return lines

    def _draw_enterprises(self, surface, content) -> None:
        title = _font(30, bold=True).render("ENTERPRISES", True, INK)
        surface.blit(title, (PAD, content.y + 6))
        y = content.y + 6 + title.get_height() + 10
        body = _font(18)
        width = content.width - 2 * PAD
        lines = self.enterprises_lines()
        for ln in lines:
            for wln in _wrap(ln, body, width):
                if y > content.bottom - 20:
                    return
                surface.blit(body.render(wln, True, INK), (PAD, y))
                y += body.get_height() + 2
            y += 6

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
        if self._narrate_rect is not None and self._narrate_rect.collidepoint(pos):
            return {"toggle_narrate": True}
        if self.active_tab in ("Docket", "Briefing"):
            for rect, pid in self._exec_hits:
                if rect.collidepoint(pos):
                    cands = self._candidates(pid)
                    self._exec_idx[pid] = (self._exec_idx.get(pid, 0) + 1) % len(cands)
                    return None
            for rect, action in self._option_hits:
                if rect.collidepoint(pos):
                    _, pid, key, exec_id = action
                    return {"rule": (pid, key, exec_id)}
        if self.active_tab == "Policies":
            for rect, key in self._dial_hits:
                if rect.collidepoint(pos):
                    frac = (pos[0] - rect.x) / rect.width
                    value = int(round((frac * 200 - 100) / 10.0)) * 10
                    value = max(-100, min(100, value))
                    return {"set_stance": (key, value)}
        if self.active_tab == "Atlas":
            pid = pick_province(self.game.atlas, self._atlas_polys, pos)
            if pid is not None:
                self.selected_pid = pid
                return {"select_province": pid}
        return None
