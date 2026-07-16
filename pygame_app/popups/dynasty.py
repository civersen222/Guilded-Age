"""Popup — dynasty ruler, heirs, traits, and court."""

from typing import Any, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH

WIDTH = 600
HEIGHT = 550
MARGIN = 8
BUTTON_H = 30
STAT_COLORS = {
    "diplomacy": "#4499ff",
    "martial": "#ff4444",
    "stewardship": "#44cc44",
    "intrigue": "#aa44ff",
}


class DynastyPopup:
    """Popup showing current ruler, heirs, traits, and court."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.info_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.close_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None
        self.status_label: Optional[pygame_gui.elements.UILabel] = None
        self.host_feast_btn: Optional[pygame_gui.elements.UIButton] = None
        self.appoint_btn: Optional[pygame_gui.elements.UIButton] = None
        self.marriage_btn: Optional[pygame_gui.elements.UIButton] = None

    @property
    def is_visible(self) -> bool:
        """Return whether the popup window exists and is alive."""
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        """Show the dynasty popup."""
        self._game = game

        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2

        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title="Dynasty",
        )

        html = self._build_html(game)
        # Leave room for buttons and status bar at bottom
        content_height = HEIGHT - MARGIN * 2 - BUTTON_H * 4
        self.info_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN, MARGIN, WIDTH - MARGIN * 2, content_height),
            html_text=html,
            manager=ui_manager,
            container=self.window,
        )

        # Action buttons row
        btn_w = 140
        total_btns_w = btn_w * 3 + MARGIN * 4
        start_x = (WIDTH - total_btns_w) // 2
        btn_y = MARGIN + content_height + 4

        self.host_feast_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(start_x, btn_y, btn_w, BUTTON_H),
            text="Host Feast",
            manager=ui_manager,
            container=self.window,
        )
        self.appoint_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(start_x + btn_w + MARGIN, btn_y, btn_w, BUTTON_H),
            text="Appoint to Court",
            manager=ui_manager,
            container=self.window,
        )
        self.marriage_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(start_x + (btn_w + MARGIN) * 2, btn_y, btn_w, BUTTON_H),
            text="Arrange Marriage",
            manager=ui_manager,
            container=self.window,
        )

        # Status label
        self.status_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(MARGIN, btn_y + BUTTON_H + 4, WIDTH - MARGIN * 2, BUTTON_H),
            text="",
            manager=ui_manager,
            container=self.window,
        )

        # Close button
        self.close_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WIDTH - 100) // 2, btn_y + BUTTON_H + 4 + BUTTON_H, 100, BUTTON_H),
            text="Close",
            manager=ui_manager,
            container=self.window,
        )


    def _build_html(self, game: Any) -> str:
        """Build HTML content for the dynasty popup."""
        parts: List[str] = []

        # Dynasty section
        dynasty = getattr(game, "dynasty", None)
        if dynasty and getattr(dynasty, "root", None):
            ruler = dynasty.root
            parts.append(f"<h2>=== {ruler.name} ===</h2><br>")

            # Age
            parts.append(f"Age: {ruler.age}<br>")

            # Stats
            parts.append("<br><b>Stats:</b><br>")
            for stat in ["diplomacy", "martial", "stewardship", "intrigue"]:
                val = ruler.get_effective_stat(stat)
                color = STAT_COLORS.get(stat, "#cccccc")
                parts.append(f'<font color="{color}">{stat.capitalize()}:</font> {val}<br>')

            # Traits
            parts.append("<br><b>Traits:</b><br>")
            if ruler.traits:
                for trait in ruler.traits:
                    parts.append(f"• {trait}<br>")
            else:
                parts.append("None<br>")

            # Prestige
            prestige = dynasty.calculate_dynastic_prestige()
            parts.append(f"<br><b>Dynasty Prestige:</b> {prestige}<br>")

            # Members / Heirs
            members = dynasty.get_all_members()
            parts.append(f"<br><b>Dynasty Members ({len(members)}):</b><br>")
            for m in members:
                alive = "✓" if m.is_alive else "✗"
                is_ruler = (m == ruler)
                relation = "Ruler" if is_ruler else ("Heir" if m.is_heir else "Member")
                parts.append(f"{alive} <b>{m.name}</b> (Age {m.age}) — {relation}<br>")
                parts.append(f"   Stats: D:{m.get_effective_stat('diplomacy')} M:{m.get_effective_stat('martial')} S:{m.get_effective_stat('stewardship')} I:{m.get_effective_stat('intrigue')}<br>")
                if m.traits:
                    parts.append(f"   Traits: {', '.join(m.traits)}<br>")
                parts.append("<br>")

        else:
            parts.append("<i>No dynasty established yet.</i><br>")

        # Court section
        court = getattr(game, "court", None)
        if court:
            parts.append("<br><h2>=== Royal Court ===</h2><br>")
            parts.append(f"{court.filled_count}/5 positions filled<br><br>")
            from court import CourtPosition
            for pos in CourtPosition:
                char = court.positions.get(pos)
                if char and char.is_alive:
                    bonus = court.get_bonus(pos)
                    parts.append(f"<b>{pos.value}:</b> {char.name} (+{bonus})<br>")
                else:
                    parts.append(f"<b>{pos.value}:</b> VACANT<br>")

        return "\n".join(parts)

    def _refresh(self) -> None:
        """Refresh the popup content."""
        if self.is_visible and self._game is not None:
            html = self._build_html(self._game)
            if self.info_textbox is not None:
                self.info_textbox.set_text(html)
            self.window.rebuild()

    def _set_status(self, message: str) -> None:
        """Set the status label text."""
        if self.status_label is not None:
            self.status_label.set_text(message)

    def handle_host_feast(self) -> None:
        """Handle the Host Feast button action."""
        if self._game is None:
            self._set_status("No game data available.")
            return
        dynasty = getattr(self._game, "dynasty", None)
        if not dynasty or not getattr(dynasty, "root", None):
            self._set_status("No dynasty established yet.")
            return

        player_civ_name = self._game.player_civ.name if hasattr(self._game, "player_civ") else None
        if not player_civ_name:
            self._set_status("Could not determine player civilization.")
            return

        gold = self._game.gold.get(player_civ_name, 0)
        if gold < 50:
            self._set_status(f"Not enough gold! Need 50, have {gold}.")
            return

        self._game.gold[player_civ_name] -= 50
        dynasty.add_prestige(10)
        self._set_status(f"Feast hosted! -50 gold, +10 prestige.")
        self._refresh()

    def handle_appoint_court(self) -> None:
        """Handle the Appoint to Court button action."""
        if self._game is None:
            self._set_status("No game data available.")
            return

        dynasty = getattr(self._game, "dynasty", None)
        court = getattr(self._game, "court", None)
        if not dynasty or not court or not getattr(dynasty, "root", None):
            self._set_status("No dynasty or court available.")
            return

        # Find vacant positions
        from court import CourtPosition
        vacant = []
        for pos in CourtPosition:
            char = court.positions.get(pos)
            if char is None:
                vacant.append(pos)
        if not vacant:
            self._set_status("All court positions are filled.")
            return

        # Find dynasty member not already in court
        members = dynasty.get_all_members()
        ruler = dynasty.root
        already_in_court = {char.id for char in court.positions.values() if char is not None}
        available = [m for m in members if m.is_alive and m.id != ruler.id and m.id not in already_in_court]

        if not available:
            self._set_status("No available dynasty members to appoint.")
            return

        # Appoint the first available member to the first vacant position
        position = vacant[0]
        character = available[0]
        turn = getattr(self._game, "turn", 0)
        success = court.appoint(position, character, turn)
        if success:
            self._set_status(f"{character.name} appointed as {position.value}!")
        else:
            self._set_status(f"Failed to appoint {character.name}.")
        self._refresh()

    def handle_arrange_marriage(self) -> None:
        """Handle the Arrange Marriage button action."""
        if self._game is None:
            self._set_status("No game data available.")
            return

        dynasty = getattr(self._game, "dynasty", None)
        if not dynasty or not getattr(dynasty, "root", None):
            self._set_status("No dynasty established yet.")
            return

        # Find the heir
        members = dynasty.get_all_members()
        heir = None
        for m in members:
            if m.is_heir and m.is_alive:
                heir = m
                break

        if not heir:
            # Fallback: pick first alive non-ruler
            ruler = dynasty.root
            for m in members:
                if m.is_alive and m != ruler:
                    heir = m
                    break
        if not heir:
            self._set_status("No living heir to arrange marriage for.")
            return

        # Add "Betrothed" trait if not already present
        if "Betrothed" not in heir.traits:
            heir.add_trait("Betrothed")
        dynasty.add_prestige(5)
        self._set_status(f"Marriage arranged for {heir.name}! +5 prestige.")
        self._refresh()

    def _kill(self) -> None:
        if self.window is not None:
            self.window.kill()
            self.window = None

    def handle_event(self, event) -> bool:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.host_feast_btn:
                self.handle_host_feast()
                return True
            if event.ui_element == self.appoint_btn:
                self.handle_appoint_court()
                return True
            if event.ui_element == self.marriage_btn:
                self.handle_arrange_marriage()
                return True
            if event.ui_element == self.close_btn:
                self.kill()
                return True
        return False

    def handle_action(self, action_id: str) -> None:
        """Route action IDs to handlers."""
        if action_id == "host_feast":
            self.handle_host_feast()
        elif action_id == "appoint_court":
            self.handle_appoint_court()
        elif action_id == "arrange_marriage":
            self.handle_arrange_marriage()
        elif action_id == "close_dynasty":
            self.kill()

    def kill(self) -> None:
        """Kill all UI elements and close the popup."""
        for elem in [self.info_textbox, self.close_btn, self.status_label,
                     self.host_feast_btn, self.appoint_btn, self.marriage_btn]:
            if elem is not None:
                elem.kill()
        self.info_textbox = None
        self.close_btn = None
        self.status_label = None
        self.host_feast_btn = None
        self.appoint_btn = None
        self.marriage_btn = None
        if self.window is not None:
            self.window.kill()
            self.window = None
