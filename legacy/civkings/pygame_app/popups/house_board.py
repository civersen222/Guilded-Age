"""Popup — the House Board: ledgers, stakes, and marriage mergers (M68, Wave UI)."""

from typing import Any, Dict, List, Optional, Tuple

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from shares import house_stake
from realms import disloyal_shareholders
from marriages import MarriageContract, _contracts, _marriages

WIDTH = 720
HEIGHT = 600
MARGIN = 8
BUTTON_H = 30


def _player_realm(game: Any):
    realms = getattr(game, "realms", None) or {}
    return realms.get(game.player_civ.name)


def _char_index(game: Any) -> Dict[str, Tuple[Any, str]]:
    """Every character in the world, with the House they answer to."""
    out: Dict[str, Tuple[Any, str]] = {}
    for realm in (getattr(game, "realms", None) or {}).values():
        for ch in realm.characters:
            out[ch.id] = (ch, realm.civ_name)
    return out


def build_board_html(realm: Any, game: Any) -> str:
    """The House Board: every enterprise, every ledger line, every seller."""
    by_id = _char_index(game)
    parts: List[str] = [
        f"<font size=5><b>=== House {realm.civ_name}: the Board ===</b></font><br>"]
    ents = realm.enterprises
    if not ents:
        parts.append("<i>The House holds no enterprises.</i>")
        return "\n".join(parts)
    total = sum(e.base_yield for e in ents)
    parts.append(f"<b>Enterprises:</b> {len(ents)} — "
                 f"<b>Combined yield:</b> {total}g/turn<br><br>")
    for ent in ents:
        parts.append(f"<b>{ent.name}</b> ({ent.sector}, {ent.city_name}) — "
                     f"{ent.base_yield}g/turn<br>")
        for cid, pct in sorted(ent.ledger.items(), key=lambda kv: -kv[1]):
            ch, civ = by_id.get(cid, (None, None))
            if ch is None:
                name, mark = "Unknown", ""
            else:
                name = ch.name
                mark = "" if ch.is_alive else " ✗"
                if civ != realm.civ_name:
                    mark += f" (House {civ})"
            parts.append(f"&nbsp;&nbsp;{name}: {pct:.0f}%{mark}<br>")
        parts.append("<br>")
    holders = {cid for ent in ents for cid in ent.ledger}
    ranked = sorted(holders, key=lambda cid: -house_stake(realm, cid))
    parts.append("<b>Controlling stakes:</b><br>")
    for cid in ranked[:5]:
        ch, _civ = by_id.get(cid, (None, None))
        name = ch.name if ch is not None else "Unknown"
        parts.append(f"{name}: {house_stake(realm, cid):.0f}% of the portfolio<br>")
    sellers = disloyal_shareholders(realm)
    if sellers:
        parts.append("<br><b>⚠ Disloyal shareholders:</b><br>")
        for ch in sellers:
            parts.append(f'<font color="#ffaa44">⚠ {ch.name} holds '
                         f"{house_stake(realm, ch.id):.0f}% and would sell</font><br>")
    return "\n".join(parts)


def build_marriages_html(game: Any) -> str:
    """Marriage as merger, on the record: every match and its terms."""
    parts: List[str] = [
        "<font size=5><b>=== Marriage Contracts: the mergers ===</b></font><br><br>"]
    by_id = _char_index(game)
    shown = 0
    for (id_a, civ_a, id_b, civ_b) in _marriages:
        a = by_id.get(id_a, (None, None))[0]
        b = by_id.get(id_b, (None, None))[0]
        if a is None or b is None:
            continue
        parts.append(f"<b>{a.name}</b> of {civ_a} ⚭ <b>{b.name}</b> of {civ_b}<br>")
        contract = _contracts.get((id_a, id_b)) or MarriageContract()
        terms: List[str] = []
        if contract.alliance:
            terms.append("alliance")
        if contract.dowry_gold > 0:
            terms.append(f"dowry {contract.dowry_gold:.0f}g")
        if contract.dowry_shares_pct > 0:
            terms.append(f"{contract.dowry_shares_pct:.0f}% shares")
        if contract.matrilineal:
            terms.append("matrilineal")
        if contract.board_seat:
            terms.append("board seat")
        parts.append("&nbsp;&nbsp;Terms: "
                     + (", ".join(terms) if terms else "a traditional match")
                     + "<br>")
        shown += 1
    if shown == 0:
        parts.append("<i>No marriages bind the Houses yet.</i>")
    return "\n".join(parts)


class HouseBoardPopup:
    """Popup showing the House Board and the marriage register; same
    contract as the other popups."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.board_btn: Optional[pygame_gui.elements.UIButton] = None
        self.marriages_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None

    @property
    def is_visible(self) -> bool:
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        self._game = game
        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2
        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title="House Board",
        )
        realm = _player_realm(game)
        html = (build_board_html(realm, game) if realm is not None
                else "<i>No realm established yet.</i>")
        content_height = HEIGHT - MARGIN * 2 - BUTTON_H * 3
        self.textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN, MARGIN,
                                      WIDTH - MARGIN * 2 - 30, content_height),
            html_text=html,
            manager=ui_manager,
            container=self.window,
        )
        self.board_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN, MARGIN + content_height + 4,
                                      150, BUTTON_H),
            text="Board", manager=ui_manager, container=self.window)
        self.marriages_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN * 2 + 150, MARGIN + content_height + 4,
                                      150, BUTTON_H),
            text="Marriages", manager=ui_manager, container=self.window)

    def handle_event(self, event) -> bool:
        if self._game is None:
            return False
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.marriages_btn and self.textbox is not None:
                self.textbox.set_text(build_marriages_html(self._game))
                return True
            if event.ui_element == self.board_btn and self.textbox is not None:
                realm = _player_realm(self._game)
                if realm is not None:
                    self.textbox.set_text(build_board_html(realm, self._game))
                return True
        return False

    def _kill(self) -> None:
        for elem in [self.textbox, self.board_btn, self.marriages_btn]:
            if elem is not None:
                elem.kill()
        if self.window is not None:
            self.window.kill()
            self.window = None
