"""Top resource bar panel — displays civ yields, gold, and turn counter."""

from typing import Any, Dict, List

import pygame
import pygame_gui

from pygame_app.constants import (
    SCREEN_WIDTH, RESOURCE_BAR_HEIGHT,
    GOLD as GOLD_COLOR, PANEL_BG, TEXT, GREEN, RED,
)


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


class ResourceBar:
    """Top bar showing civ name, yields, gold, and turn counter."""

    def __init__(self, ui_manager: pygame_gui.UIManager, game: Any):
        self.ui_manager = ui_manager
        self.game = game
        self._labels: Dict[str, pygame_gui.elements.UILabel] = {}
        self._panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, SCREEN_WIDTH, RESOURCE_BAR_HEIGHT),
            manager=ui_manager,
            start_surface=None,
        )
        self._panel.get_container().set_alpha(0.0)  # we draw our own bg
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
            label.set_alpha(0.0)  # we draw our own text
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
        civ_name = game.player_civ.name
        yields = game.city_manager.get_total_yields(civ_name, game.map.tiles)
        gold_total = game.gold.get(civ_name, 0)
        gold_income = yields.get("gold", 0)
        turn = game.state.turn

        self._labels["civ_name"].set_text(f"Civ: {civ_name}")
        self._labels["food"].set_text(self._format_yield(
            "Food", yields.get('food', 0), RESOURCE_ICONS.get("food", "")))
        self._labels["production"].set_text(self._format_yield(
            "Prod", yields.get('production', 0), RESOURCE_ICONS.get("production", "")))
        self._labels["gold"].set_text(
            f"{RESOURCE_ICONS.get('gold', '')} Gold: {gold_total} ({int(gold_income)}/t)")
        self._labels["science"].set_text(self._format_yield(
            "Sci", yields.get('science', 0), RESOURCE_ICONS.get("science", "")))
        self._labels["culture"].set_text(self._format_yield(
            "Culture", yields.get('culture', 0), RESOURCE_ICONS.get("culture", "")))
        self._labels["faith"].set_text(self._format_yield(
            "Faith", yields.get('stability', 0), RESOURCE_ICONS.get("faith", "")))
        self._labels["turn"].set_text(f"Turn {turn}")

    def draw(self, surface: pygame.Surface, game: Any) -> None:
        """Draw the polished resource bar background and text."""
        # Dark background
        surface.fill(PANEL_BG, pygame.Rect(0, 0, SCREEN_WIDTH, RESOURCE_BAR_HEIGHT))

        # Gold border at bottom
        pygame.draw.line(surface, GOLD_TEXT, (0, RESOURCE_BAR_HEIGHT - 1),
                         (SCREEN_WIDTH, RESOURCE_BAR_HEIGHT - 1))

        # Draw custom text with color coding
        yields = game.city_manager.get_total_yields(game.player_civ.name, game.map.tiles)
        gold_income = yields.get("gold", 0)

        bar_w = SCREEN_WIDTH
        keys = ["civ_name", "food", "production", "gold", "science", "culture", "faith", "turn"]
        spacing = bar_w // len(keys)

        for i, key in enumerate(keys):
            x = spacing * i + 8
            y = 10
            label_text = self._labels[key].get_text()

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
                    income_val = int(float(income_part.replace("+", "").replace(")", "").replace("/t", "")))
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
