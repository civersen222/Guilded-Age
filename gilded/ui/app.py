"""The app (mission G23): the pygame loop that binds the client together.

run_app() opens the window "The Gilded Machine", holds a live GildedGame and a
BroadsheetView, and each frame turns the view's click-actions into moves on the
game - rule a petition, end the turn - exactly the levers the AI plays. Esc
quits; F5 drops a quicksave in gilded/save.py's format. step_once() is one
frame factored out so the loop is testable headless (SDL_VIDEODRIVER=dummy).

Importing this module must not open a display; all pygame surface work happens
inside the functions, never at import time.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pygame

from gilded.chassis import GildedGame
from gilded.save import save_game
from gilded.saga.narrator import select_narrator
from gilded.ui.actions import ACTIONS
from gilded.ui.broadsheet import BroadsheetView

WINDOW_TITLE = "The Gilded Machine"
DEFAULT_SIZE = (1280, 900)
FPS = 30


@dataclass
class AppState:
    game: GildedGame
    view: BroadsheetView
    screen: pygame.Surface
    house: str
    clock: pygame.time.Clock
    save_path: str
    narrator: object


def new_app_state(seed: int, player_house: Optional[str] = None,
                  size=DEFAULT_SIZE) -> AppState:
    """Boot a game, a window, and the view - the loop's whole world."""
    pygame.init()
    game = GildedGame(seed, player_house)
    house = player_house if player_house is not None else sorted(game.houses)[0]
    if player_house is None:
        game.houses[house].is_player = True
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption(WINDOW_TITLE)
    pygame.event.clear()
    narrator = select_narrator()            # LLM in play; templated under test
    view = BroadsheetView(game, house, narrator)
    save_path = os.path.join(os.getcwd(), "gilded_quicksave.gsave")
    return AppState(game, view, screen, house, pygame.time.Clock(), save_path,
                    narrator)


def _apply_action(state: AppState, action: dict) -> None:
    """Turn one view action into a move on the game (the UI stays a client)."""
    for key in action:
        if key == "adjust_garrison":
            from gilded.ui.actions import _adjust_garrison_eligible, _adjust_garrison_dispatch
            ok, _reason = _adjust_garrison_eligible(state.game, state.house, action)
            if not ok:
                if _reason:
                    state.view._action_messages.append(str(_reason))
                return
            result = _adjust_garrison_dispatch(state.game, state.house, state.view, action)
        else:
            act = ACTIONS.get(key)
            if act is None:
                continue
            ok, _reason = act.eligible(state.game, state.house, action)
            if not ok:
                if _reason:
                    state.view._action_messages.append(str(_reason))
                return
            result = act.dispatch(state.game, state.house, state.view, action)
        if result:
            if isinstance(result, dict):
                for k, value in result.items():
                    if isinstance(value, str):
                        state.view._action_messages.append(f"{k}: {value}")
            elif isinstance(result, str):
                state.view._action_messages.append(result)
            elif isinstance(result, list):
                for item in result:
                    if isinstance(item, str):
                        state.view._action_messages.append(item)
        return


def _quicksave(state: AppState) -> str:
    save_game(state.game, state.save_path)
    return state.save_path


def step_once(state: AppState) -> bool:
    """Pump events, apply actions, draw one frame. False means quit."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_F5:
                _quicksave(state)
            if event.key == pygame.K_n:
                state.view.narrate_on = not state.view.narrate_on
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = state.view.handle_click(event.pos)
            if action:
                _apply_action(state, action)
        if event.type == pygame.MOUSEMOTION:
            state.view.handle_hover(event.pos)
    state.view.draw(state.screen)
    pygame.display.flip()
    state.clock.tick(FPS)
    return True


def run_app(seed: int, player_house: Optional[str] = None) -> None:
    """Open the window and play the century until the age closes or you quit."""
    state = new_app_state(seed, player_house)
    running = True
    while running:
        running = step_once(state)
    pygame.quit()
