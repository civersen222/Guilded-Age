"""Popup — the character sheet and dynasty tree (M67, Wave UI)."""

from typing import Any, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from dispositions import PAIRS
from simulation import opinion_matrix

WIDTH = 760
HEIGHT = 620
MARGIN = 8
BUTTON_H = 30
LIST_W = 210
GAP_ALERT = 20.0      # persona-truth divergence worth flagging
NOTABLE = 20.0        # spectrum strength worth a label
ATTR_COLORS = {
    "statecraft": "#4499ff",
    "command": "#ff4444",
    "industry": "#44cc44",
    "intrigue": "#aa44ff",
    "science": "#44cccc",
    "resolve": "#ffaa44",
}


def _player_realm(game: Any):
    realms = getattr(game, "realms", None) or {}
    return realms.get(game.player_civ.name)


def _spectrum_label(pair: Any, value: float) -> Optional[str]:
    if value <= -NOTABLE:
        return pair.low_label
    if value >= NOTABLE:
        return pair.high_label
    return None


def build_character_html(char: Any, game: Any) -> str:
    """One person, whole: attributes, reputation vs truth, secrets, standing."""
    parts: List[str] = []
    alive = "" if char.is_alive else " ✗ (deceased)"
    parts.append(f"<font size=5><b>=== {char.name}{alive} ===</b></font><br>")
    parts.append(f"Age {char.age} — {char.gender}<br><br>")
    parts.append("<b>Attributes:</b><br>")
    for attr in ["statecraft", "command", "industry", "intrigue", "science", "resolve"]:
        color = ATTR_COLORS.get(attr, "#cccccc")
        parts.append(f'<font color="{color}">{attr.capitalize()}:</font> {char.get_effective_stat(attr)}<br>')
    parts.append("<br><b>Traits:</b> " + (", ".join(char.traits) if char.traits else "None") + "<br>")
    parts.append(f"<b>Gold:</b> {char.gold_reserve:.0f} — <b>Stress:</b> {getattr(char, 'stress', 0)}<br>")
    focus = getattr(char, "focus", None)
    if focus is not None:
        parts.append(f"<b>Focus:</b> {getattr(focus, 'name', focus)}<br>")
    loyalty = getattr(char, "loyalty", None)
    if loyalty is not None:
        parts.append(f"<b>Loyalty:</b> {loyalty:.0f}<br>")

    disp = getattr(char, "dispositions", None) or {}
    persona = getattr(char, "persona", None) or {}
    lines: List[str] = []
    for key, pair in PAIRS.items():
        true_v = disp.get(key, 0.0)
        seen_v = persona.get(key, true_v)
        seen_l = _spectrum_label(pair, seen_v)
        true_l = _spectrum_label(pair, true_v)
        if abs(true_v - seen_v) >= GAP_ALERT:
            seen_s = seen_l or "unremarkable"
            true_s = true_l or "unremarkable"
            lines.append(f'<font color="#ffaa44">⚠ {seen_s} to society - {true_s} in truth</font><br>')
        elif true_l:
            lines.append(f"{true_l}<br>")
    if lines:
        parts.append("<br><b>Reputation:</b><br>")
        parts.extend(lines)

    secrets = getattr(char, "secrets", None) or []
    if secrets:
        parts.append(f"<br><b>Secrets ({len(secrets)}):</b><br>")
        for s in secrets[:6]:
            parts.append(f"🔒 {s.description} (potency {s.potency}, {len(s.holders)} in the know)<br>")

    realm = _player_realm(game)
    if realm is not None and realm.ruler is not None and char.id != realm.ruler.id:
        parts.append(f"<br><b>Standing:</b> thinks {opinion_matrix.get((char.id, realm.ruler.id), 0):+d} "
                     f"of {realm.ruler.name}, who thinks {opinion_matrix.get((realm.ruler.id, char.id), 0):+d} back<br>")
    return "\n".join(parts)


def build_dynasty_tree_html(realm: Any) -> str:
    """The House as a family tree: the org chart of the whole game."""
    dyn = realm.dynasty
    parts: List[str] = [
        f"<font size=5><b>=== House {realm.civ_name}: the {dyn.root.name} line ===</b></font><br>",
        f"<b>Dynastic Prestige:</b> {dyn.calculate_dynastic_prestige():.0f}<br><br>",
    ]
    visited = set()

    def walk(ch: Any, depth: int) -> None:
        if ch.id in visited:
            return
        visited.add(ch.id)
        pad = "&nbsp;" * 4 * depth
        alive = "✓" if ch.is_alive else "✗"
        crown = " ♔" if ch.id == realm.ruler.id else ""
        parts.append(f"{pad}{alive} <b>{ch.name}</b>{crown} (Age {ch.age})<br>")
        for cid in ch.children_ids:
            child = dyn.all_characters.get(cid)
            if child is not None:
                walk(child, depth + 1)

    walk(dyn.root, 0)
    return "\n".join(parts)


def _roster(realm: Any) -> List[Any]:
    """Who the sheet lists: living dynasty first, then the court."""
    seen = set()
    out: List[Any] = []
    for ch in realm.dynasty.all_characters.values():
        if ch.is_alive and ch.id not in seen:
            seen.add(ch.id)
            out.append(ch)
    for ch in realm.court.positions.values():
        if ch is not None and ch.is_alive and ch.id not in seen:
            seen.add(ch.id)
            out.append(ch)
    return out[:30]


class CharacterSheetPopup:
    """Popup showing character sheets and the dynasty tree; same contract
    as the other popups."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.roster_list: Optional[pygame_gui.elements.UISelectionList] = None
        self.sheet_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.tree_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None
        self._roster_chars: List[Any] = []

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
            window_display_title="Characters",
        )
        realm = _player_realm(game)
        self._roster_chars = _roster(realm) if realm else []
        content_height = HEIGHT - MARGIN * 2 - BUTTON_H * 3
        self.roster_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect(MARGIN, MARGIN, LIST_W, content_height),
            item_list=[ch.name for ch in self._roster_chars],
            manager=ui_manager,
            container=self.window,
        )
        first = realm.ruler if realm else None
        html = build_character_html(first, game) if first else "<i>No realm established yet.</i>"
        self.sheet_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN * 2 + LIST_W, MARGIN,
                                      WIDTH - LIST_W - MARGIN * 3 - 30, content_height),
            html_text=html,
            manager=ui_manager,
            container=self.window,
        )
        self.tree_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN, MARGIN + content_height + 4, 150, BUTTON_H),
            text="Dynasty Tree", manager=ui_manager, container=self.window)

    def handle_event(self, event) -> bool:
        if self._game is None:
            return False
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.tree_btn:
            realm = _player_realm(self._game)
            if realm is not None and self.sheet_textbox is not None:
                self.sheet_textbox.set_text(build_dynasty_tree_html(realm))
            return True
        if (event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION
                and event.ui_element == self.roster_list):
            pick = next((ch for ch in self._roster_chars if ch.name == event.text), None)
            if pick is not None and self.sheet_textbox is not None:
                self.sheet_textbox.set_text(build_character_html(pick, self._game))
            return True
        return False

    def _kill(self) -> None:
        for elem in [self.roster_list, self.sheet_textbox, self.tree_btn]:
            if elem is not None:
                elem.kill()
        if self.window is not None:
            self.window.kill()
            self.window = None
