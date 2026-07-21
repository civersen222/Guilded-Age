"""Popup — the Scheme menu and the Secrets ledger (M71, Wave UI)."""

from typing import Any, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from schemes import SCHEME_THRESHOLD, SCHEME_TYPES

WIDTH = 720
HEIGHT = 600
MARGIN = 8
BUTTON_H = 30
LIST_W = 180


def _player_realm(game: Any):
    realms = getattr(game, "realms", None) or {}
    return realms.get(game.player_civ.name)


def build_schemes_html(game: Any) -> str:
    """Every knife in motion, in one place."""
    parts: List[str] = [
        "<font size=5><b>=== Schemes in motion ===</b></font><br><br>"]
    mgr = getattr(game, "scheme_manager", None)
    schemes = list(getattr(mgr, "schemes", None) or [])
    if not schemes:
        parts.append("<i>No knives are out tonight.</i>")
        return "\n".join(parts)
    for s in schemes:
        parts.append(f"<b>{s.agent.name}</b> moves against <b>{s.target.name}</b> "
                     f"of {s.target_civ} ({s.scheme_type}) — "
                     f"progress {s.progress:.0f}/{SCHEME_THRESHOLD}, "
                     f"{len(s.participants)} fellow travellers<br>")
    return "\n".join(parts)


def build_secrets_html(game: Any) -> str:
    """The ledger: what the world holds on us, and what we hold on the world."""
    realm = _player_realm(game)
    parts: List[str] = [
        "<font size=5><b>=== The Secrets ledger ===</b></font><br>"]
    if realm is None:
        parts.append("<i>No realm established yet.</i>")
        return "\n".join(parts)
    ours = {c.id for c in realm.characters}
    parts.append("<br><b>Vulnerabilities (secrets about our House):</b><br>")
    n = 0
    for ch in realm.characters:
        for s in (getattr(ch, "secrets", None) or []):
            outside = any(h not in ours for h in s.holders)
            leak = (' — <font color="#ff4444">known outside the House!</font>'
                    if outside else "")
            parts.append(f"🔒 {s.description} (potency {s.potency}, "
                         f"{len(s.holders)} in the know){leak}<br>")
            n += 1
    if n == 0:
        parts.append("<i>The House's conscience is clean. Officially.</i><br>")
    parts.append("<br><b>Weapons (secrets we hold on others):</b><br>")
    n = 0
    for other in (getattr(game, "realms", None) or {}).values():
        if other is realm:
            continue
        for ch in other.characters:
            for s in (getattr(ch, "secrets", None) or []):
                if any(h in ours for h in s.holders):
                    parts.append(f"🗡 {s.description} (potency {s.potency}, "
                                 f"House {other.civ_name})<br>")
                    n += 1
    if n == 0:
        parts.append("<i>We hold nothing on anyone. Yet.</i><br>")
    return "\n".join(parts)


def start_scheme_against(game: Any, target_civ: str, kind: str) -> Optional[str]:
    """The player ruler sets a scheme in motion against a rival ruler,
    through the existing SchemeManager API. One knife at a time."""
    realm = _player_realm(game)
    realms = getattr(game, "realms", None) or {}
    trealm = realms.get(target_civ)
    if realm is None or trealm is None or kind not in SCHEME_TYPES:
        return None
    if target_civ == realm.civ_name:
        return None
    agent = realm.ruler
    target = getattr(trealm, "ruler", None)
    if agent is None or target is None or not target.is_alive:
        return None
    mgr = getattr(game, "scheme_manager", None)
    if mgr is None or mgr.scheming(agent):
        return None
    mgr.start_scheme(agent, target, kind, target_civ)
    return f"{agent.name} sets a {kind} in motion against {target.name} of {target_civ}"


class SchemeMenuPopup:
    """Popup showing schemes and the secrets ledger; same contract as the
    other popups."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.target_list: Optional[pygame_gui.elements.UISelectionList] = None
        self.textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.schemes_btn: Optional[pygame_gui.elements.UIButton] = None
        self.secrets_btn: Optional[pygame_gui.elements.UIButton] = None
        self.coup_btn: Optional[pygame_gui.elements.UIButton] = None
        self.assassinate_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None
        self._selected_civ: Optional[str] = None

    @property
    def is_visible(self) -> bool:
        return self.window is not None and self.window.alive()

    def _rival_civs(self) -> List[str]:
        realms = getattr(self._game, "realms", None) or {}
        me = self._game.player_civ.name
        return [name for name in realms if name != me]

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        self._game = game
        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2
        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title="Schemes",
        )
        content_height = HEIGHT - MARGIN * 2 - BUTTON_H * 3
        self.target_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect(MARGIN, MARGIN, LIST_W, content_height),
            item_list=self._rival_civs(),
            manager=ui_manager,
            container=self.window,
        )
        self.textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN * 2 + LIST_W, MARGIN,
                                      WIDTH - LIST_W - MARGIN * 3 - 30, content_height),
            html_text=build_schemes_html(game),
            manager=ui_manager,
            container=self.window,
        )
        y = MARGIN + content_height + 4
        self.schemes_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN, y, 120, BUTTON_H),
            text="Schemes", manager=ui_manager, container=self.window)
        self.secrets_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN * 2 + 120, y, 120, BUTTON_H),
            text="Secrets", manager=ui_manager, container=self.window)
        self.coup_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN * 3 + 240, y, 120, BUTTON_H),
            text="Plot Coup", manager=ui_manager, container=self.window)
        self.assassinate_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN * 4 + 360, y, 120, BUTTON_H),
            text="Assassinate", manager=ui_manager, container=self.window)

    def handle_event(self, event) -> bool:
        if self._game is None:
            return False
        if (event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION
                and event.ui_element == self.target_list):
            self._selected_civ = event.text
            return True
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.schemes_btn and self.textbox is not None:
                self.textbox.set_text(build_schemes_html(self._game))
                return True
            if event.ui_element == self.secrets_btn and self.textbox is not None:
                self.textbox.set_text(build_secrets_html(self._game))
                return True
            kind = None
            if event.ui_element == self.coup_btn:
                kind = "coup"
            elif event.ui_element == self.assassinate_btn:
                kind = "assassination"
            if kind is not None:
                if self._selected_civ is not None:
                    start_scheme_against(self._game, self._selected_civ, kind)
                if self.textbox is not None:
                    self.textbox.set_text(build_schemes_html(self._game))
                return True
        return False

    def _kill(self) -> None:
        for elem in [self.target_list, self.textbox, self.schemes_btn,
                     self.secrets_btn, self.coup_btn, self.assassinate_btn]:
            if elem is not None:
                elem.kill()
        if self.window is not None:
            self.window.kill()
            self.window = None
