"""Popup — Appointments: council seats, Directors, Commanders (M69, Wave UI)."""

from typing import Any, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from court import Court, CourtPosition
from realms import DOMAIN_CAP
from simulation import opinion_matrix

WIDTH = 760
HEIGHT = 620
MARGIN = 8
BUTTON_H = 30
LIST_W = 210


def _player_realm(game: Any):
    realms = getattr(game, "realms", None) or {}
    return realms.get(game.player_civ.name)


def build_appointments_html(game: Any) -> str:
    """The whole org chart: council, Directors, Commanders."""
    realm = _player_realm(game)
    if realm is None:
        return "<i>No realm established yet.</i>"
    court = realm.court
    parts: List[str] = [
        f"<font size=5><b>=== Appointments of House {realm.civ_name} ===</b></font><br>",
        f"<b>Council ({court.filled_count}/5 seats filled):</b><br>",
    ]
    for pos in CourtPosition:
        ch = court.positions.get(pos)
        stat = Court.POSITION_STATS.get(pos)
        if ch is not None and ch.is_alive:
            parts.append(f"{pos.value}: <b>{ch.name}</b> (+{court.get_bonus(pos)} {stat})<br>")
        else:
            parts.append(f'{pos.value}: <font color="#ffaa44">VACANT</font> (needs {stat})<br>')
    parts.append(f"<br><b>Directors (domain cap {DOMAIN_CAP}):</b><br>")
    listed = 0
    for city in (getattr(game, "cities", None) or {}).values():
        d = getattr(city, "director", None)
        if city.owner == realm.civ_name and d is not None and d.is_alive:
            parts.append(f"{city.name}: <b>{d.name}</b> "
                         f"(industry {d.get_effective_stat('industry')}, "
                         f"loyalty {getattr(d, 'loyalty', 50.0):.0f})<br>")
            listed += 1
    if listed == 0:
        parts.append("<i>Every city sits inside the personal domain.</i><br>")
    parts.append("<br><b>Commanders in the field:</b><br>")
    listed = 0
    for unit in (getattr(game, "units", None) or {}).values():
        cmd = getattr(unit, "commander", None)
        if (unit.owner == realm.civ_name and unit.is_alive
                and cmd is not None and cmd.is_alive):
            parts.append(f"{unit.name}: <b>{cmd.name}</b> "
                         f"(command {cmd.get_effective_stat('command')})<br>")
            listed += 1
    if listed == 0:
        parts.append("<i>No Commanders are posted.</i><br>")
    return "\n".join(parts)


def council_candidates(realm: Any, position: CourtPosition) -> List[Any]:
    """Everyone who could hold the seat, best first by its attribute."""
    stat = Court.POSITION_STATS.get(position)
    seated = {ch.id for ch in realm.court.positions.values() if ch is not None}
    pool = [ch for ch in realm.characters
            if ch.is_alive and ch.age >= 16 and ch.id != realm.ruler.id
            and ch.id not in seated]
    return sorted(pool, key=lambda ch: -ch.get_effective_stat(stat))


def build_compare_html(realm: Any, position: CourtPosition) -> str:
    """The candidate compare: the number, the loyalty, the grudge."""
    stat = Court.POSITION_STATS.get(position)
    parts: List[str] = [
        f"<font size=5><b>=== Candidates: {position.value} ===</b></font><br>",
        f"Governing attribute: <b>{stat}</b><br><br>",
    ]
    cands = council_candidates(realm, position)
    if not cands:
        parts.append("<i>No eligible candidates.</i>")
        return "\n".join(parts)
    ruler = realm.ruler
    for i, ch in enumerate(cands[:10]):
        star = "★ " if i == 0 else ""
        parts.append(f"{star}<b>{ch.name}</b> — {stat} {ch.get_effective_stat(stat)}, "
                     f"loyalty {getattr(ch, 'loyalty', 50.0):.0f}, "
                     f"thinks {opinion_matrix.get((ch.id, ruler.id), 0):+d} "
                     f"of {ruler.name}<br>")
    return "\n".join(parts)


def appoint_best(realm: Any, position: CourtPosition, turn: int) -> Optional[str]:
    """Fill the seat with the top candidate through the Court API."""
    cands = council_candidates(realm, position)
    if not cands:
        return None
    pick = cands[0]
    if realm.court.appoint(position, pick, turn):
        return f"{pick.name} is appointed {position.value}"
    return None


class AppointmentsPopup:
    """Popup showing the org chart with a candidate compare; same contract
    as the other popups."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.seats_list: Optional[pygame_gui.elements.UISelectionList] = None
        self.textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.overview_btn: Optional[pygame_gui.elements.UIButton] = None
        self.appoint_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None
        self._selected_pos: Optional[CourtPosition] = None

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
            window_display_title="Appointments",
        )
        content_height = HEIGHT - MARGIN * 2 - BUTTON_H * 3
        self.seats_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect(MARGIN, MARGIN, LIST_W, content_height),
            item_list=[pos.value for pos in CourtPosition],
            manager=ui_manager,
            container=self.window,
        )
        self.textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN * 2 + LIST_W, MARGIN,
                                      WIDTH - LIST_W - MARGIN * 3 - 30, content_height),
            html_text=build_appointments_html(game),
            manager=ui_manager,
            container=self.window,
        )
        self.overview_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN, MARGIN + content_height + 4,
                                      150, BUTTON_H),
            text="Overview", manager=ui_manager, container=self.window)
        self.appoint_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN * 2 + 150, MARGIN + content_height + 4,
                                      150, BUTTON_H),
            text="Appoint Best", manager=ui_manager, container=self.window)

    def handle_event(self, event) -> bool:
        if self._game is None:
            return False
        realm = _player_realm(self._game)
        if (event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION
                and event.ui_element == self.seats_list):
            pick = next((p for p in CourtPosition if p.value == event.text), None)
            if pick is not None and realm is not None and self.textbox is not None:
                self._selected_pos = pick
                self.textbox.set_text(build_compare_html(realm, pick))
            return True
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.overview_btn and self.textbox is not None:
                self.textbox.set_text(build_appointments_html(self._game))
                return True
            if (event.ui_element == self.appoint_btn and realm is not None
                    and self._selected_pos is not None and self.textbox is not None):
                turn = getattr(getattr(self._game, "state", None), "turn", 0)
                appoint_best(realm, self._selected_pos, turn)
                self.textbox.set_text(build_appointments_html(self._game))
                return True
        return False

    def _kill(self) -> None:
        for elem in [self.seats_list, self.textbox, self.overview_btn, self.appoint_btn]:
            if elem is not None:
                elem.kill()
        if self.window is not None:
            self.window.kill()
            self.window = None
