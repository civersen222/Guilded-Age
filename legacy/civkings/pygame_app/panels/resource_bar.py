"""Top resource bar panel — displays civ yields, gold, and turn counter."""

from typing import Any, Dict, List

import pygame
import pygame_gui

from pygame_app.constants import (
    SCREEN_WIDTH, RESOURCE_BAR_HEIGHT,
    GOLD as GOLD_COLOR, PANEL_BG, TEXT, GREEN, RED,
)
from game_data import house_name


# Unicode icons for each resource type
RESOURCE_ICONS = {
    "food": "\u2630",          # wheat-like
    "production": "\u2699",     # gear
    "gold": "\u26C5",           # coin/diamond
    "science": "\u2697",        # flask
    "culture": "\u263A",        # smiling face (closest to masks)
    "faith": "\u271D",          # cross
}

# Resource display labels (key → display name)
RESOURCE_LABELS = {
    "food": "Food",
    "production": "Prod",
    "gold": "Gold",
    "science": "Sci",
    "culture": "Culture",
    "faith": "Faith",
}

GOLD_TEXT = (197, 160, 89)
WHITE_TEXT = (255, 255, 255)
POS_COLOR = (58, 178, 78)
NEG_COLOR = (178, 58, 58)


def turn_to_year(turn: int) -> str:
    """Calendar for the fictional industrial century (M52): the game opens
    in 1900 and each turn spans ~1.5 years."""
    return str(1900 + (turn * 3) // 2)


class ResourceBar:
    """Top bar showing civ name, yields, gold, and turn counter."""

    def __init__(self, ui_manager: pygame_gui.UIManager, game: Any):
        self.ui_manager = ui_manager
        self.game = game
        self._labels: Dict[str, pygame_gui.elements.UILabel] = {}
        self._panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, SCREEN_WIDTH, RESOURCE_BAR_HEIGHT),
            manager=ui_manager,
        )
        self._create_labels()
        self._font = pygame.font.SysFont("consolas", 12, bold=True)
        self.refresh(game)

    def _create_labels(self):
        """Create evenly-spaced UILabels for each resource."""
        keys = ["civ_name", "food", "production", "gold", "science", "culture", "faith", "turn"]
        bar_w = SCREEN_WIDTH
        spacing = bar_w // len(keys)

        for i, key in enumerate(keys):
            rect = pygame.Rect(spacing * i + 5, 5, spacing - 10, RESOURCE_BAR_HEIGHT - 10)
            label = pygame_gui.elements.UILabel(
                relative_rect=rect,
                text="",
                manager=self.ui_manager,
            )
            self._labels[key] = label

    def _yield_color(self, value: float) -> tuple:
        """Return text color based on yield sign."""
        if value > 0:
            return POS_COLOR
        elif value < 0:
            return NEG_COLOR
        return WHITE_TEXT

    def _format_yield(self, label: str, value: float, icon: str = "") -> str:
        """Format a yield value with icon and color-coded sign."""
        sign = ""
        if value > 0:
            sign = "+"
        elif value < 0:
            sign = "-"
        return f"{icon} {label}: {sign}{value:.1f}"

    def refresh(self, game: Any) -> None:
        """Update all label text from current game state."""
        try:
            turn = getattr(getattr(game, 'state', None), 'turn', 1)
        except Exception:
            turn = 1
        try:
            player_civ = getattr(game, 'player_civ', None)
            civ_name = getattr(player_civ, 'name', 'Unknown') if player_civ else 'Unknown'
        except Exception:
            civ_name = 'Unknown'

        # Gold from game.gold dict
        try:
            gold_dict = getattr(game, 'gold', {})
            gold_total = gold_dict.get(civ_name, 0) if isinstance(gold_dict, dict) else 0
        except Exception:
            gold_total = 0

        # Science and culture from city yields
        try:
            yields = game.city_manager.get_total_yields(civ_name, game.map.tiles)
            science = yields.get('science', 0.0)
            culture = yields.get('culture', 0.0)
        except Exception:
            science = 0.0
            culture = 0.0

        # Culture safe default
        culture = 0

        # Faith from game.faith_points dict
        try:
            faith_dict = getattr(game, 'faith_points', {})
            faith = faith_dict.get(civ_name, 0) if isinstance(faith_dict, dict) else 0
        except Exception:
            faith = 0

        # Yields from city manager (food, production, gold income)
        try:
            city_manager = getattr(game, 'city_manager', None)
            if city_manager is not None:
                yields = city_manager.get_total_yields(civ_name, getattr(game, 'map', None))
            else:
                yields = {}
        except Exception:
            yields = {}

        gold_income = yields.get('gold', 0)

        # Update each label individually with try/except
        try:
            self._labels["civ_name"].set_text(house_name(civ_name))
        except Exception:
            pass
        try:
            self._labels["food"].set_text(self._format_yield(
                "Food", yields.get('food', 0), RESOURCE_ICONS.get("food", "")))
        except Exception:
            pass
        try:
            self._labels["production"].set_text(self._format_yield(
                "Prod", yields.get('production', 0), RESOURCE_ICONS.get("production", "")))
        except Exception:
            pass
        try:
            self._labels["gold"].set_text(
                f"{RESOURCE_ICONS.get('gold', '')} Gold: {gold_total} ({int(gold_income)}/t)")
        except Exception:
            pass
        try:
            self._labels["science"].set_text(self._format_yield(
                "Sci", science, RESOURCE_ICONS.get("science", "")))
        except Exception:
            pass
        try:
            self._labels["culture"].set_text(self._format_yield(
                "Culture", culture, RESOURCE_ICONS.get("culture", "")))
        except Exception:
            pass
        try:
            self._labels["faith"].set_text(self._format_yield(
                "Faith", faith, RESOURCE_ICONS.get("faith", "")))
        except Exception:
            pass
        try:
            self._labels["turn"].set_text(f"Turn {turn} | {turn_to_year(turn)}")
        except Exception:
            pass

    def draw(self, surface: pygame.Surface, game: Any) -> None:
        """Draw the polished resource bar background and text."""
        # Dark background
        surface.fill(PANEL_BG, pygame.Rect(0, 0, SCREEN_WIDTH, RESOURCE_BAR_HEIGHT))

        # Gold border at bottom
        pygame.draw.line(surface, GOLD_TEXT, (0, RESOURCE_BAR_HEIGHT - 1),
                         (SCREEN_WIDTH, RESOURCE_BAR_HEIGHT - 1))

        # Draw custom text with color coding
        civ_name = getattr(game, 'player_civ', None)
        if civ_name:
            civ_name = getattr(civ_name, 'name', 'Unknown')
        else:
            civ_name = 'Unknown'
        city_manager = getattr(game, 'city_manager', None)
        if city_manager is not None:
            yields = city_manager.get_total_yields(civ_name, getattr(game, 'map', None))
        else:
            yields = {"food": 0, "production": 0, "gold": 0, "science": 0, "culture": 0}
        gold_income = yields.get("gold", 0)

        bar_w = SCREEN_WIDTH
        keys = ["civ_name", "food", "production", "gold", "science", "culture", "faith", "turn"]
        spacing = bar_w // len(keys)

        for i, key in enumerate(keys):
            x = spacing * i + 8
            y = 10
            label_text = self._labels[key].text

            # Color coding for yield values
            if key == "civ_name":
                color = WHITE_TEXT
            elif key == "turn":
                color = GOLD_TEXT
            elif key == "gold":
                # Show gold total in white, income in yield color
                parts = label_text.split("(")
                base = parts[0] if parts else label_text
                income_part = f"({parts[1]}" if len(parts) > 1 else ""
                if income_part:
                    income_val = int(float(income_part.replace("+", "").replace(")", "").replace("(", "").replace("/t", "")))
                    inc_color = self._yield_color(income_val)
                    rendered = self._font.render(base.strip(), True, WHITE_TEXT)
                    surface.blit(rendered, (x, y))
                    x += rendered.get_width() + 2
                    rendered2 = self._font.render(income_part, True, inc_color)
                    surface.blit(rendered2, (x, y))
                    continue
                color = WHITE_TEXT
            else:
                yield_val = yields.get(key, 0)
                color = self._yield_color(yield_val)

            rendered = self._font.render(label_text, True, color)
            surface.blit(rendered, (x, y))

    def destroy(self) -> None:
        """Kill all UI elements."""
        self._panel.kill()
        for label in self._labels.values():
            label.kill()
        self._labels.clear()
