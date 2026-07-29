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


def test_set_stance_action_moves_the_dial_for_free():
    state = _state()
    g, h = state.game, state.house
    attn_before = g.attention.get(h, 0)
    app._apply_action(state, {"set_stance": ("labor", 40)})
    assert g.directives[h].stances["labor"] == 40
    assert g.attention.get(h, 0) == attn_before   # free — no attention spent


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


def test_expand_enterprise_own_venture_costs_attention():
    """Expanding a venture the House owns costs exactly one attention."""
    import gilded.ui.app as gapp
    state = gapp.new_app_state(seed=42)
    g, h = state.game, state.house
    own = next(e for e in g.enterprises if e.house == h)
    pre_attention = g.attention[h]
    pre_uc = own.under_construction
    gapp._apply_action(state, {"expand_enterprise": own.eid})
    assert g.attention[h] == pre_attention - 1
    assert own.under_construction != pre_uc


def test_expand_enterprise_foreign_venture_changes_nothing():
    """A venture belonging to another House costs nothing and changes nothing."""
    import gilded.ui.app as gapp
    state = gapp.new_app_state(seed=42)
    g, h = state.game, state.house
    other = next((e for e in g.enterprises if e.house != h), None)
    if other is None:
        return  # skip if no foreign ventures exist
    pre_attention = g.attention[h]
    pre_uc = other.under_construction
    gapp._apply_action(state, {"expand_enterprise": other.eid})
    assert g.attention[h] == pre_attention
    assert other.under_construction == pre_uc


def test_expand_enterprise_nonexistent_eid_changes_nothing():
    """An eid that matches no venture at all costs nothing and changes nothing."""
    import gilded.ui.app as gapp
    state = gapp.new_app_state(seed=42)
    g, h = state.game, state.house
    pre_attention = g.attention[h]
    gapp._apply_action(state, {"expand_enterprise": 99999})
    assert g.attention[h] == pre_attention


def test_expand_enterprise_zero_attention_refuses():
    """Zero attention refuses the action and leaves the venture untouched."""
    import gilded.ui.app as gapp
    state = gapp.new_app_state(seed=42)
    g, h = state.game, state.house
    own = next(e for e in g.enterprises if e.house == h)
    pre_uc = own.under_construction
    g.attention[h] = 0
    gapp._apply_action(state, {"expand_enterprise": own.eid})
    assert own.under_construction == pre_uc


def test_expand_enterprise_lines_land_in_events():
    """The lines initiative returns land in game.events with register 'ledger'."""
    import gilded.ui.app as gapp
    state = gapp.new_app_state(seed=42)
    g, h = state.game, state.house
    own = next(e for e in g.enterprises if e.house == h)
    pre_count = len(g.events)
    gapp._apply_action(state, {"expand_enterprise": own.eid})
    new_events = g.events[pre_count:]
    assert len(new_events) > 0
    for ev in new_events:
        assert ev.register == "ledger"
        assert ev.house == h


def test_expand_enterprise_ghost_eid_appends_nothing():
    """A click naming an eid that matches no venture appends nothing to events."""
    import gilded.ui.app as gapp
    state = gapp.new_app_state(seed=42)
    g, h = state.game, state.house
    pre_count = len(g.events)
    pre_attention = g.attention.get(h, 0)
    gapp._apply_action(state, {"expand_enterprise": 1013})
    assert len(g.events) == pre_count, (
        f"Ghost eid appended {len(g.events) - pre_count} event(s)"
    )
    assert g.attention.get(h, 0) == pre_attention, (
        f"Ghost eid cost {pre_attention - g.attention.get(h, 0)} attention"
    )


def test_expand_enterprise_real_vs_ghost_in_same_file():
    """Real expansion writes lines; ghost eid writes nothing — in one test."""
    import gilded.ui.app as gapp
    state = gapp.new_app_state(seed=42)
    g, h = state.game, state.house
    own = next(e for e in g.enterprises if e.house == h)
    # Real expansion should write lines
    pre_count = len(g.events)
    gapp._apply_action(state, {"expand_enterprise": own.eid})
    real_lines = len(g.events) - pre_count
    assert real_lines > 0, "Real expansion wrote no events"
    # Ghost eid should write nothing
    pre_count2 = len(g.events)
    gapp._apply_action(state, {"expand_enterprise": 1013})
    ghost_lines = len(g.events) - pre_count2
    assert ghost_lines == 0, f"Ghost eid wrote {ghost_lines} event(s)"
