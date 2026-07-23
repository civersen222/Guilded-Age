"""G23 the app: the loop, factored for a headless step_once."""

import inspect
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from gilded.ui import app


def _state():
    return app.new_app_state(seed=42)


def test_run_app_signature():
    assert callable(app.run_app)
    params = inspect.signature(app.run_app).parameters
    assert "seed" in params and "player_house" in params


def test_step_once_runs_and_continues():
    state = _state()
    assert app.step_once(state) is True


def test_quit_event_stops_the_loop():
    state = _state()
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    assert app.step_once(state) is False


def test_escape_stops_the_loop():
    state = _state()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.step_once(state) is False


def test_end_turn_action_advances_the_game():
    state = _state()
    turn = state.game.turn
    app._apply_action(state, {"end_turn": True})
    assert state.game.turn == turn + 1


def test_rule_action_spends_attention_and_clears_paper():
    state = _state()
    g, h = state.game, state.house
    p = g.docket_by_house[h][0]
    before = g.attention[h]
    app._apply_action(state, {"rule": (p.pid, p.options[0].key, None)})
    assert g.attention[h] == before - 1
    assert all(x.pid != p.pid for x in g.docket_by_house[h])


def test_quicksave_writes_a_file(tmp_path):
    state = _state()
    state.save_path = str(tmp_path / "quick.pkl")
    path = app._quicksave(state)
    assert os.path.exists(path)
    assert state.game.docket_by_house      # the docket is restored after saving


def test_end_turn_lands_on_briefing_and_records_prev_board():
    state = _state()
    state.view.active_tab = "House"
    turn = state.game.turn
    app._apply_action(state, {"end_turn": True})
    assert state.game.turn == turn + 1
    assert state.view.active_tab == "Briefing"
    assert state.view.prev_board is not None


def test_place_informant_action_spends_attention_and_sets_flag():
    import gilded.ui.app as gapp
    state = gapp.new_app_state(seed=7)
    g = state.game
    player = state.house
    g.houses[player].is_player = True
    target = next(h for h in sorted(g.houses) if h != player)
    before = g.attention.get(player, 0)
    gapp._apply_action(state, {"place_informant": target})
    assert (player, target) in g.informants
    assert g.attention.get(player, 0) == before - 1