"""The Saves screen (mission C9, c9-saves-ui): numbered slots that save and
load the WHOLE game.

Reachable from the main menu and in play (a chrome button on the broadsheet)
via a {"menu": "saves"} region. The opener arms view.showing_saves on
whichever view is live — MenuView or BroadsheetView — and that view's draw()
delegates to draw_saves_screen(), so the SAME view object draws the slots;
the view is never swapped.

Each slot draws a Save region ({"menu": "save_slot", "slot": n}) that calls
gilded.save.save_game to <cwd>/saves/slot<n>.gsave — so
gilded.save.load_game on that file returns the GildedGame — and a Load region
({"menu": "load_slot", "slot": n}) that load_game()s it into state.game. A
slot file is a save of the game (a pickled GildedGame), never a record of
numbers. Empty slots draw their Load region DISABLED with a reason; they
still count as slots.
"""

from __future__ import annotations

import os

import pygame

from gilded.save import save_game, load_game
from gilded.ui.palette import INK, INK2, FADED, PAPER_BG
from gilded.ui.widgets import Region, RegionState, _text_rows

SLOT_COUNT = 4
SLOTS_DIR = "saves"


def slots_dir() -> str:
    """<cwd>/saves — slot files live under the working directory."""
    d = os.path.join(os.getcwd(), SLOTS_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def slot_path(slot: int) -> str:
    return os.path.join(slots_dir(), f"slot{slot}.gsave")


def slot_exists(slot: int) -> bool:
    return os.path.isfile(slot_path(slot))


def draw_saves_screen(view, surface: pygame.Surface, game=None) -> None:
    """Draw the slots screen into view.regions and the text-row ledger.

    `game` may be None (menu launch before any opener press): the slots are
    then read from the files on disk, Save regions are disabled, and Load
    regions are enabled for slots that exist.
    """
    from gilded.ui.app import _font, TYPE_TITLE, TYPE_TEXT
    from gilded.ui.widgets import blit_text

    surface.fill(PAPER_BG)
    view.regions.clear()
    w, h = surface.get_size()
    in_play = game is not None

    title_font = _font(TYPE_TITLE, bold=True)
    title_img = title_font.render("Saves", True, INK)
    surface.blit(title_img, (w // 2 - title_img.get_width() // 2, 50))
    _text_rows.append(
        (title_img.get_rect(center=(w // 2, 50 + title_img.get_height() // 2)),
         "Saves"))

    btn_font = _font(TYPE_TEXT)
    btn_w = 300
    btn_h = 44
    gap = 58
    start_y = 130
    save_cx = w // 2 - 40 - btn_w // 2
    load_cx = w // 2 + 40 + btn_w // 2

    for slot in range(1, SLOT_COUNT + 1):
        exists = slot_exists(slot)
        y = start_y + (slot - 1) * gap

        # Save region: writes the whole game to the slot. In play only; on
        # the menu (no game) it is DISABLED with a reason.
        save_rect = pygame.Rect(save_cx, y, btn_w, btn_h)
        save_label = f"Slot {slot} — save"
        if in_play:
            save_state = RegionState.ENABLED
            save_reason = ""
        else:
            save_state = RegionState.DISABLED
            save_reason = "in play only"
        _draw_slot_button(view, surface, btn_font, save_rect, save_label,
                          save_state, save_reason)
        view.regions.add(
            Region(rect=save_rect,
                   action={"menu": "save_slot", "slot": slot},
                   state=save_state, reason=save_reason,
                   hint=save_label, group="saves"))

        # Load region: loads the slot into state.game. DISABLED while the
        # slot is empty (with a reason; it still counts as a slot).
        load_rect = pygame.Rect(load_cx, y, btn_w, btn_h)
        load_label = f"Slot {slot} — load"
        if exists:
            load_state = RegionState.ENABLED
            load_reason = ""
        else:
            load_state = RegionState.DISABLED
            load_reason = "empty"
        _draw_slot_button(view, surface, btn_font, load_rect, load_label,
                          load_state, load_reason)
        view.regions.add(
            Region(rect=load_rect,
                   action={"menu": "load_slot", "slot": slot},
                   state=load_state, reason=load_reason,
                   hint=load_label, group="saves"))

    # Back
    back_rect = pygame.Rect(w // 2 - btn_w // 2, start_y + SLOT_COUNT * gap,
                            btn_w, btn_h)
    _draw_slot_button(view, surface, btn_font, back_rect, "back",
                      RegionState.ENABLED, "")
    view.regions.add(Region(rect=back_rect, action={"menu": "back"},
                            hint="back", group="saves"))


def _draw_slot_button(view, surface, font, rect: pygame.Rect, label: str,
                      state: RegionState, reason: str) -> None:
    from gilded.ui.widgets import blit_text
    from gilded.ui.palette import INK, FADED
    enabled = state is RegionState.ENABLED
    pygame.draw.rect(surface, PAPER_BG, rect, border_radius=4)
    pygame.draw.rect(surface, INK if enabled else FADED, rect, width=1,
                     border_radius=4)
    color = INK if enabled else FADED
    text = label if enabled else f"{label} ({reason})"
    blit_text(surface, font, text,
              (rect.centerx - font.size(text)[0] // 2,
               rect.centery - font.size(text)[1] // 2),
              color)


def _do_save_slot(state, slot: int) -> None:
    if state.game is None:
        return
    save_game(state.game, slot_path(slot))
    if hasattr(state.view, "message"):
        state.view.message = f"slot {slot} — saved"
    if hasattr(state.view, "showing_saves"):
        state.view.showing_saves = False


def _do_load_slot(state, slot: int) -> None:
    if slot_exists(slot):
        state.game = load_game(slot_path(slot))
        if hasattr(state.view, "game"):
            state.view.game = state.game
        if hasattr(state.view, "message"):
            state.view.message = f"slot {slot} — loaded"
    if hasattr(state.view, "showing_saves"):
        state.view.showing_saves = False
