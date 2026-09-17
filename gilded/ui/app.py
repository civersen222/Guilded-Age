"""The app (mission G23): the pygame loop that binds the client together.

run_app() opens the window "The Gilded Machine", holds a live GildedGame and a
BroadsheetView, and each frame turns the view's click-actions into moves on the
game - rule a petition, end the turn - exactly the levers the AI plays. Esc
quits; F5 drops a quicksave in gilded/save.py's format. step_once() is one
frame factored out so the loop is testable headless (SDL_VIDEODRIVER=dummy).

Importing this module must not open a display; all pygame surface work happens
inside the functions, never at import time.

Mission C6: the vertical slice — Menu -> Play -> Ending.

new_app_state(seed, start="menu") boots to the main menu (s.game is None,
s.view is a MenuView). new_app_state(seed, start="game") is the original
behaviour — boots straight into play. The menu has four verbs:
new_game, continue (disabled if no save), settings, quit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pygame

from gilded.chassis import GildedGame
from gilded.orders import init_orders
from gilded.save import save_game, load_game, quicksave_path
from gilded.saga.narrator import select_narrator
from gilded.ui.actions import ACTIONS
from gilded.ui.broadsheet import BroadsheetView
from gilded.ui.transitions import frames as transition_frames
from gilded.ui.widgets import (
    Region, RegionSet, RegionState,
    blit_text, font as _font, TYPE_TITLE, TYPE_TEXT,
    PAPER_BG, INK, FADED, MASK_BLACK,
)
from gilded.settings import Settings, load_settings, save_settings
from gilded import audio

WINDOW_TITLE = "CivKings: The Gilded Machine"
DEFAULT_SIZE = (1280, 900)
FPS = 30


# ── Menu view ────────────────────────────────────────────────────────────────

class MenuView:
    """The main menu: title + four verbs drawn as proper Regions."""

    def __init__(self, screen: pygame.Surface, settings: Settings):
        self.screen = screen
        self.settings = settings
        self.regions = RegionSet()
        self.text_rows: list[tuple[pygame.Rect, str]] = []
        self._menu_rects: dict[str, pygame.Rect] = {}
        self._settings_rects: dict[str, pygame.Rect] = {}
        self.showing_settings = False
        self.message = ""
        self._w, self._h = screen.get_size()

    def draw(self, surface: pygame.Surface) -> None:
        from gilded.ui.widgets import _text_rows, take_text_rows
        take_text_rows()
        surface.fill(PAPER_BG)
        self.regions.clear()
        w, h = self._w, self._h

        # Title
        title_font = _font(TYPE_TITLE, bold=True)
        title_img = title_font.render(WINDOW_TITLE, True, INK)
        surface.blit(title_img, (w // 2 - title_img.get_width() // 2, 60))
        _text_rows.append((title_img.get_rect(center=(w // 2, 60 + title_img.get_height() // 2)), WINDOW_TITLE))

        if self.showing_settings:
            self._draw_settings(surface)
        else:
            self._draw_menu(surface)

        if self.message:
            msg_font = _font(TYPE_TEXT)
            msg_img = msg_font.render(self.message, True, FADED)
            surface.blit(msg_img, (w // 2 - msg_img.get_width() // 2, h - 60))
            _text_rows.append((msg_img.get_rect(center=(w // 2, h - 60)), self.message))

    def _draw_menu(self, surface: pygame.Surface) -> None:
        from gilded.ui.widgets import _text_rows
        w, h = self._w, self._h
        btn_font = _font(TYPE_TEXT)
        btn_w = 240
        btn_h = 36
        cx = w // 2 - btn_w // 2
        start_y = 200
        gap = 52

        # Check if a save exists
        spath = quicksave_path()
        has_save = os.path.isfile(spath)

        buttons = [
            ("new_game", "New Game", True, ""),
            ("continue", "Continue", has_save, "No save found in current directory" if not has_save else ""),
            ("settings", "Settings", True, ""),
            ("quit", "Quit", True, ""),
        ]

        for i, (key, label, enabled, reason) in enumerate(buttons):
            y = start_y + i * gap
            rect = pygame.Rect(cx, y, btn_w, btn_h)
            if enabled:
                state = RegionState.ENABLED
                action = {"menu": key}
                reason_str = ""
                color = INK
                bg = PAPER_BG
            else:
                state = RegionState.DISABLED
                action = None
                reason_str = reason
                color = FADED
                bg = PAPER_BG
            # Draw button background
            pygame.draw.rect(surface, bg, rect, border_radius=4)
            pygame.draw.rect(surface, INK if enabled else FADED, rect, width=1, border_radius=4)
            # Draw button label
            img = btn_font.render(label, True, color)
            surface.blit(img, (rect.centerx - img.get_width() // 2,
                               rect.centery - img.get_height() // 2))
            _text_rows.append((img.get_rect(center=rect.center), label))
            # Register region
            if enabled:
                self.regions.add(Region(rect=rect, action=action,
                                         state=RegionState.ENABLED, hint=label,
                                         group="menu"))
            else:
                self.regions.add(Region(rect=rect, action={"menu": key},
                                         state=RegionState.DISABLED, reason=reason_str,
                                         group="menu"))

    def _draw_settings(self, surface: pygame.Surface) -> None:
        from gilded.ui.widgets import _text_rows
        w, h = self._w, self._h
        btn_font = _font(TYPE_TEXT)
        btn_w = 240
        btn_h = 36
        cx = w // 2 - btn_w // 2
        start_y = 200
        gap = 52

        s = self.settings

        # Title
        title_font = _font(TYPE_TITLE, bold=True)
        t_img = title_font.render("Settings", True, INK)
        surface.blit(t_img, (cx, start_y - 60))
        _text_rows.append((t_img.get_rect(topleft=(cx, start_y - 60)), "Settings"))

        settings_buttons = [
            ("mute", f"Mute: {'ON' if s.mute else 'OFF'}"),
            ("narrate", f"Narrate: {'ON' if s.narrate else 'OFF'}"),
            ("back", "Back"),
        ]

        for i, (key, label) in enumerate(settings_buttons):
            y = start_y + i * gap
            rect = pygame.Rect(cx, y, btn_w, btn_h)
            action = {"setting": key}
            pygame.draw.rect(surface, PAPER_BG, rect, border_radius=4)
            pygame.draw.rect(surface, INK, rect, width=1, border_radius=4)
            img = btn_font.render(label, True, INK)
            surface.blit(img, (rect.centerx - img.get_width() // 2,
                               rect.centery - img.get_height() // 2))
            _text_rows.append((img.get_rect(center=rect.center), label))
            self.regions.add(Region(rect=rect, action=action,
                                     hint=label, group="settings"))

    def handle_click(self, pos: tuple) -> Optional[dict]:
        region = self.regions.at(pos)
        if region is None:
            return None
        if region.state is RegionState.DISABLED:
            return None
        action = region.action
        if action.get("menu") == "quit":
            return action
        if action.get("menu") == "settings":
            self.showing_settings = True
            audio.play("ui_press", self.settings)
            return action
        if "setting" in action:
            audio.play("ui_press", self.settings)
            return action
        if action.get("menu") in ("new_game", "continue"):
            audio.play("ui_press", self.settings)
            return action
        return action


# ── AppState ─────────────────────────────────────────────────────────────────

@dataclass
class AppState:
    game: Optional[GildedGame]
    view: object
    screen: pygame.Surface
    house: str
    clock: pygame.time.Clock
    save_path: str
    narrator: object
    settings: Settings = None
    seed: int = 0
    start: str = "game"
    _beats_seen: int = 0
    _wars_seen: int = 0
    _ending_played: bool = False
    _bed_event: str = ""
    _pending_frames: object = None
    _pending_src: object = None
    _pending_steps: int = 0
    _transition_index: int = 0


def _build_menu_state(screen: pygame.Surface, seed: int, settings: Settings) -> AppState:
    view = MenuView(screen, settings)
    return AppState(
        game=None,
        view=view,
        screen=screen,
        house="",
        clock=pygame.time.Clock(),
        save_path=quicksave_path(),
        narrator=None,
        settings=settings,
        seed=seed,
        start="menu",
    )


def _boot_play(state: AppState, player_house: Optional[str] = None) -> AppState:
    """Boot a GildedGame and replace the menu view with BroadsheetView."""
    game = GildedGame(state.seed, player_house)
    house = player_house if player_house is not None else sorted(game.houses)[0]
    if player_house is None:
        game.houses[house].is_player = True
        init_orders(game)
    narrator = select_narrator()
    view = BroadsheetView(game, house, narrator)
    return AppState(
        game=game,
        view=view,
        screen=state.screen,
        house=house,
        clock=state.clock,
        save_path=state.save_path,
        narrator=narrator,
        settings=state.settings,
        seed=state.seed,
        start="game",
    )


def new_app_state(seed: int, player_house: Optional[str] = None,
                  size=DEFAULT_SIZE, start: str = "game") -> AppState:
    """Boot a game, a window, and the view - the loop's whole world.

    start="menu" boots to the main menu (s.game is None).
    start="game" (default) boots straight into play, as before.
    """
    pygame.init()
    settings = load_settings()
    size = settings.window_size if settings.window_size else size
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption(WINDOW_TITLE)
    pygame.event.clear()

    if start == "menu":
        return _build_menu_state(screen, seed, settings)

    # start="game" — original behaviour
    game = GildedGame(seed, player_house)
    house = player_house if player_house is not None else sorted(game.houses)[0]
    if player_house is None:
        game.houses[house].is_player = True
        init_orders(game)
    narrator = select_narrator()
    view = BroadsheetView(game, house, narrator)
    save_path = os.path.join(os.getcwd(), "gilded_quicksave.gsave")
    return AppState(
        game=game,
        view=view,
        screen=screen,
        house=house,
        clock=pygame.time.Clock(),
        save_path=save_path,
        narrator=narrator,
        settings=settings,
        seed=seed,
        start="game",
    )


def _apply_action(state: AppState, action: dict) -> None:
    """Turn one view action into a move on the game (the UI stays a client)."""
    if "setting" in action:
        _apply_setting_action(state, action)
        return

    if "menu" in action:
        _apply_menu_action(state, action)
        return

    key = None
    for k in action:
        if k not in ("menu", "setting"):
            key = k
            break
    if key is None:
        return

    if key == "zoom":
        # C8.1: view-internal tier switch (kept out of the ACTIONS registry).
        state.view.atlas_tier = action["zoom"]
        return

    if key == "adjust_garrison":
        from gilded.ui.actions import _adjust_garrison_eligible, _adjust_garrison_dispatch
        ok, _reason = _adjust_garrison_eligible(state.game, state.house, action)
        if not ok:
            if _reason:
                state.view._action_messages.append(str(_reason))
            return
        result = _adjust_garrison_dispatch(state.game, state.house, state.view, action)
    elif key == "set_dial":
        from gilded.ui import registry
        v = registry.VERBS["set_dial"]
        beat = state.game.acts.set_dial(action.get("eid", ""), action.get("value", 50))
        state.view._action_messages.append(v["what"])
        state.view._action_messages.append(beat.text)
        result = None
    else:
        act = ACTIONS.get(key)
        if act is None:
            return
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
        elif key == "quickload":
            state.game = result
            state.view.game = result


def _play_game_audio(state: AppState) -> None:
    """Fire the world sounds for what just happened: beat arrivals, war
    declarations, the ending. play() never raises and honors mute."""
    if state.game is None or state.settings is None:
        return
    game, s = state.game, state.settings
    if len(game.beats.log) > state._beats_seen:
        audio.play("beat", s)
    state._beats_seen = len(game.beats.log)
    if len(game.wars) > state._wars_seen:
        audio.play("war_declared", s)
    state._wars_seen = len(game.wars)
    if game.game_over is not None and not state._ending_played:
        audio.play("ending", s)
        state._ending_played = True


def _ensure_bed(state: AppState) -> None:
    """The ambient bed follows the act: switch it when the turn crosses an
    act boundary. The bed loops until the next switch."""
    if state.game is None or state.settings is None:
        return
    event = audio.ambient_event_for(state.game)
    if event != state._bed_event:
        state._bed_event = event
        try:
            snd = audio._loaded.get(event)
            if snd is None:
                snd = pygame.mixer.Sound(audio.resolve(event))
                audio._loaded[event] = snd
            if not getattr(state.settings, "mute", False):
                snd.set_num_repeats(-1)
                snd.play()
        except Exception:
            pass


def _apply_menu_action(state: AppState, action: dict) -> None:
    """Handle menu verbs when no game is running."""
    menu_key = action.get("menu")
    if menu_key == "new_game":
        _boot_play_into(state)
    elif menu_key == "continue":
        try:
            game = load_game(state.save_path)
            state.game = game
            # Find player house
            player_house = next((h for h in game.houses if game.houses[h].is_player), None)
            if player_house is None:
                player_house = sorted(game.houses)[0]
                game.houses[player_house].is_player = True
            state.house = player_house
            state.narrator = select_narrator()
            state.view = BroadsheetView(game, player_house, state.narrator)
            state.start = "game"
            audio.play("ui_press", state.settings)
        except Exception as e:
            if hasattr(state.view, 'message'):
                state.view.message = f"Could not load save: {e}"
    elif menu_key == "settings":
        if hasattr(state.view, 'showing_settings'):
            state.view.showing_settings = True
    elif menu_key == "quit":
        pass  # handled by the caller


def _boot_play_into(state: AppState) -> None:
    """Replace the menu view with a fresh game, in-place on state."""
    game = GildedGame(state.seed, None)
    house = sorted(game.houses)[0]
    game.houses[house].is_player = True
    init_orders(game)
    state.game = game
    state.house = house
    state.narrator = select_narrator()
    state.view = BroadsheetView(game, house, state.narrator)
    state.start = "game"
    audio.play("ui_press", state.settings)


def _apply_setting_action(state: AppState, action: dict) -> None:
    """Toggle a setting and persist."""
    key = action.get("setting")
    s = state.settings
    if s is None:
        s = state.settings = Settings()
    if key == "mute":
        s.mute = not s.mute
        audio.play("ui_press", s)
    elif key == "narrate":
        s.narrate = not s.narrate
    elif key == "back":
        if hasattr(state.view, "showing_settings"):
            state.view.showing_settings = False
        return
    save_settings(s)


def _quicksave(state: AppState) -> str:
    save_game(state.game, state.save_path)
    return state.save_path


def _report_frame_failure(state: AppState) -> None:
    """Print and reset after a draw failure; the loop must not die on a frame."""
    import traceback
    traceback.print_exc()
    state.view._action_messages.append("Frame failed; recovering.")


def step_once(state: AppState) -> bool:
    """One frame: poll events, apply clicks, advance the clock, draw.

    Returns False when the app should quit.
    """
    if state.game is None:
        return _step_menu(state)

    # C8.3: play a pending page transition, one cross-fade frame per tick.
    if state._pending_frames is not None:
        if state._transition_index < len(state._pending_frames):
            state.screen.blit(state._pending_frames[state._transition_index], (0, 0))
            state._transition_index += 1
            if state._transition_index == len(state._pending_frames):
                state._pending_frames = None
                state._transition_index = 0
        pygame.display.flip()
        state.clock.tick(FPS)
        return True

    running = True
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            elif event.key == pygame.K_F5:
                _quicksave(state)
        if event.type == pygame.MOUSEMOTION:
            state.view.handle_hover(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = state.view.handle_click(event.pos)
            if action is not None:
                _apply_action(state, action)
                if action.get("menu") == "quit":
                    return False
                if getattr(state.view, "last_transition", None) is not None:
                    # C8.3: cross-fade from the page just on screen to the
                    # new page, played one frame per tick at the frame clock.
                    steps = int(state.view.last_transition.get("steps", 6))
                    src = state.screen.copy()
                    tmp = pygame.Surface(state.screen.get_size())
                    tmp.fill(MASK_BLACK)
                    state.view.draw(tmp)
                    state._pending_frames = transition_frames(src, tmp, steps)
                    state._transition_index = 0
                    state.view.last_transition = None
                if action.get("end_turn"):
                    audio.play("end_turn", state.settings)
                    _ensure_bed(state)
    if state._beats_seen == 0 and state.game is not None:
        audio.play("ambient", state.settings)  # the century hums, once
        state._beats_seen = len(state.game.beats.log)
    if state.game is not None and state.game.game_over is None:
        pass  # no auto-advance; the player presses end turn
    _play_game_audio(state)
    state.view.draw(state.screen)
    pygame.display.flip()
    state.clock.tick(FPS)
    return True


def _step_menu(state: AppState) -> bool:
    """One frame while the main menu is showing (state.game is None)."""
    running = True
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = state.view.handle_click(event.pos)
            if action is not None:
                _apply_action(state, action)
                if action.get("menu") == "quit":
                    return False
    state.view.draw(state.screen)
    pygame.display.flip()
    state.clock.tick(FPS)
    return True


def run_app(seed: int, player_house: Optional[str] = None,
            start: str = "menu") -> None:
    """Open the window and play the century until the age closes or you quit."""
    state = new_app_state(seed, player_house, start=start)
    running = True
    while running:
        running = step_once(state)
    pygame.quit()
