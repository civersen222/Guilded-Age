"""Top resource bar panel — displays civ yields, gold, and turn counter."""

from typing import Any, Dict, List

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_WIDTH, RESOURCE_BAR_HEIGHT, GOLD as GOLD_COLOR


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

    def refresh(self, game: Any) -> None:
        """Update all label text from current game state."""
        civ_name = game.player_civ.name
        yields = game.city_manager.get_total_yields(civ_name, game.map.tiles)
        gold_total = game.gold.get(civ_name, 0)
        gold_income = yields.get("gold", 0)
        turn = game.state.turn

        self._labels["civ_name"].set_text(f"Civ: {civ_name}")
        self._labels["food"].set_text(f"Food: {yields.get('food', 0):.1f}")
        self._labels["production"].set_text(f"Prod: {yields.get('production', 0):.1f}")
        self._labels["gold"].set_text(f"Gold: {gold_total} (+{int(gold_income)}/t)")
        self._labels["science"].set_text(f"Sci: {yields.get('science', 0):.1f}")
        self._labels["culture"].set_text(f"Culture: {yields.get('culture', 0):.1f}")
        self._labels["faith"].set_text(f"Faith: {yields.get('stability', 0):.1f}")
        self._labels["turn"].set_text(f"Turn {turn}")

    def destroy(self) -> None:
        """Kill all UI elements."""
        self._panel.kill()
        for label in self._labels.values():
            label.kill()
        self._labels.clear()
