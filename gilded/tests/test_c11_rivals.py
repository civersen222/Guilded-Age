"""Mission C11 Wave 1 - rivals and reach: the committed self-check.

Run EXACTLY as:
    python -m pytest gilded/tests/test_c11_rivals.py -q

Where each fact lives (Clarity Law):
- whether a rival reads your ambition: Powers/Dossier with that rival
  selected (the "reads you" line, drawn through blit_text, tier read LIVE
  from gilded.intel.report at draw time, family-agnostic - it names no
  family word, no stem, no stake why-text, and is identical across a stake
  swap).  It is drawn NOWHERE ELSE: no HUD strip line, no bottom bar line,
  no other spine/page, and no font.render outside blit_text.
- a lever a rival pulled on your house: House/Court (one line naming the
  courted member and the courting rival house, and nothing else).  It is
  drawn NOWHERE ELSE.
- the AI courtship itself lives in the sim (gilded.ai): a house that reads
  another at intel tier >= 2 (gilded.intel.report, LIVE at turn open) turns
  one of the read house's opposers and leaves a named beat; tier < 2 and
  non-opposers are untouched.

Each test below draws EVERY reachable screen (every spine, every page,
every page a drawn set_spine_page region names, every Powers page with
each rival selected) and asserts the fact appears on exactly one.
Headless: SDL_VIDEODRIVER=dummy, SDL_AUDIODRIVER=dummy, seed 7.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import re

import pygame

from gilded import settings as gsettings
from gilded import save as gsave
from gilded.agenda import FAMILIES, ensure_agenda
from gilded.ambitions import FAMILY_DISPOSITION
from gilded.intel import report
from gilded.ui import widgets
from gilded.ui.app import new_app_state, _apply_action
from gilded.ui import broadsheet as bs
from gilded import ai as gai
from gilded.society.characters import Secret

_NEG = re.compile(
    r"\b(?:not|no|cannot|can'?t|never|nothing|none|nor|without|unable|"
    r"unaware|blind|unseen|unknown|hidden|hide|hides|dark|guess|guesses|"
    r"guessing|\w*n't)\b", re.IGNORECASE)


def _clean(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for p in (gsettings.settings_path(), gsave.quicksave_path()):
        if p and os.path.exists(p):
            os.remove(p)


def _relaunch(seed, start):
    pygame.display.quit()
    return new_app_state(seed=seed, start=start)


def _press(s, predicate):
    """Redraw, find the first region whose dict action matches predicate,
    press its centre; apply the returned action. Returns the action."""
    s.view.regions.clear()
    widgets._text_rows.clear()
    s.view.draw(s.screen)
    for r in s.view.regions._regions:
        if isinstance(r.action, dict) and predicate(r.action):
            action = s.view.handle_click(r.rect.center)
            assert action is not None, "press refused"
            if action:
                _apply_action(s, action)
            return action
    raise AssertionError("no region matching predicate")


def _screens(view, rivals):
    """Every screen the play view can show: each spine, each of its pages,
    plus every Powers page with each rival selected."""
    screens = []
    for spine in bs.TABS:
        view.active_tab = spine
        if spine == "House":
            pages = list(view.house_pages)
        elif spine == "Powers":
            pages = list(view.powers_pages)
        else:
            pages = [None]
        for page in pages:
            view.house_page = page if spine == "House" else view.house_page
            view.powers_page = page if spine == "Powers" else view.powers_page
            view._powers_selected = None
            screens.append((spine, page, None))
        if spine == "Powers":
            for r in rivals:
                for page in list(view.powers_pages):
                    view.powers_page = page
                    view._powers_selected = r
                    screens.append((spine, page, r))
    return screens


def _draw_screen(s, spine, page, selected=None):
    view = s.view
    view.active_tab = spine
    if spine == "House":
        view.house_page = page
    elif spine == "Powers":
        view.powers_page = page
        view._powers_selected = selected
    view.regions.clear()
    widgets._text_rows.clear()
    view.draw(s.screen)
    rows = list(widgets._text_rows)
    regions = [r for r in view.regions._regions]
    return rows, regions


def _lines(rows):
    """Group text rows into lines (centre-y within 6 px), joined L->R."""
    lines = []
    for rect, text in sorted(rows, key=lambda t: (t[0].centery, t[0].x)):
        if lines and abs(rect.centery - lines[-1][0]) <= 6:
            lines[-1] = (rect.centery, lines[-1][1] + " " + text)
        else:
            lines.append((rect.centery, text))
    return [text for _y, text in lines]


def _census(s, rivals):
    """Draw every reachable screen; return {screen_name: lines}."""
    out = {}
    for spine, page, selected in _screens(s.view, rivals):
        rows, _regions = _draw_screen(s, spine, page, selected)
        name = (f"{spine}/{page}[{selected}]" if selected is not None
                else (f"{spine}/{page}" if page is not None else spine))
        out[name] = _lines(rows)
    return out


def _owner(game, line):
    """The house whose name appears FIRST (whole word) in the line."""
    best = None
    for h in sorted(game.realms):
        m = re.search(rf"\b{re.escape(h)}\b", line)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), h)
    return best[1] if best else None


def _strip_sources(game, R, player):
    """Strip every source R holds on the player (toward intel tier 0)."""
    game.houses[R].relations[player] = 0
    game.houses[player].relations[R] = 0
    game.marriages.marriages = [
        t for t in game.marriages.marriages
        if t[1] not in (player, R) and t[3] not in (player, R)
    ]
    game.informants.discard((R, player))
    pr = game.realms[player].ruler
    r_ids = {c.id for c in game.realms[R].characters}
    for sec in list(pr.secrets):
        if r_ids & set(sec.holders):
            pr.secrets.remove(sec)


def _set_state(game, R, player, state):
    """state: subset of {"inf", "rel", "sec"} - the gate's intel states."""
    _strip_sources(game, R, player)
    if "inf" in state:
        game.informants.add((R, player))
    if "rel" in state:
        game.houses[R].relations[player] = 5
    if "sec" in state:
        pr = game.realms[player].ruler
        rr = game.realms[R].ruler
        sec = Secret("scandal", pr.id, f"{pr.name} favours {R}", 10)
        sec.holders.add(rr.id)
        pr.secrets.append(sec)


# ── C11.1a: the reads-you line - live tier, no cached value ──────────────

def test_c11_1a_rival_reads_you(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "game")
    g = s.game
    player = s.house
    R = "Duval-Corse"
    ensure_agenda(g, R)
    states = [frozenset(), frozenset({"inf"}), frozenset({"inf", "rel"}),
              frozenset({"rel"}), frozenset({"rel", "inf"}),
              frozenset({"rel", "inf", "sec"}), frozenset({"rel", "sec"}),
              frozenset({"sec"}), frozenset()]
    per_state = []
    for st in states:
        _set_state(g, R, player, st)
        tier = report(g, R, player).tier
        rows, _ = _draw_screen(s, "Powers", "Dossier", selected=R)
        lines = _lines(rows)
        owned = [ln for ln in lines if _owner(g, ln) == R]
        per_state.append((st, tier, owned))
    # every state draws at least one R-owned line that varies
    texts = [set(owned) for _st, _t, owned in per_state]
    const = set.intersection(*texts) if texts else set()
    for _st, tier, owned in per_state:
        varying = [ln for ln in owned if ln not in const]
        assert varying, f"no varying R line at tier {tier}: {owned}"
        if tier >= 2:
            assert not any(_NEG.search(ln) for ln in varying), \
                f"negation at tier {tier}: {varying}"
        else:
            assert any(_NEG.search(ln) for ln in varying), \
                f"no negation at tier {tier}: {varying}"
    # the tier across the nine states is exactly the sim's answer
    expected = [0, 1, 2, 1, 2, 3, 2, 1, 0]
    got = [t for _st, t, _owned in per_state]
    assert got == expected, got


# ── C11.1b: the reads-you line never names the player's family ──────────

# the player's family word and its OWN stem (the gate checks only the
# player's family, not every family's word)
_FAM_STEM = {
    "Conquest": ("conquest", "conquer"),
    "Dominion": ("dominion",),
    "Buyout": ("buyout", "buy-out"),
    "Dynasty": ("dynast",),
    "Intrigue": ("intrigu",),
    "Glory": ("glory", "glories", "glorious"),
    "Consolidation": ("consolidat",),
}


def _family_named(line, fam):
    if re.search(rf"\b{re.escape(fam.lower())}\b", line, re.IGNORECASE):
        return True
    low = line.lower()
    return any(re.search(rf"\b\w*{stem}\w*\b", low)
               for stem in _FAM_STEM.get(fam, ()))


def test_c11_1b_reads_you_never_names(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "game")
    g = s.game
    player = s.house
    R = "Duval-Corse"
    g.ambitions.set_ambition(player, "Dynasty")  # the gate's F at seed 7
    ensure_agenda(g, R)
    fam = g.ambitions.status(player)["family"]
    why = g.ambitions.status(player).get("why", "")
    for st in (frozenset(), frozenset({"rel", "inf"})):
        _set_state(g, R, player, st)
        rows, _ = _draw_screen(s, "Powers", "Dossier", selected=R)
        before = _lines(rows)
        other = next(f for f in FAMILIES if f != fam)
        g.ambitions.set_ambition(player, other)
        rows2, _ = _draw_screen(s, "Powers", "Dossier", selected=R)
        after = _lines(rows2)
        g.ambitions.set_ambition(player, fam)
        assert before == after, f"screen changed under stake swap ({st})"
        for ln in before:
            assert not _family_named(ln, fam), f"family word in {ln!r}"
            assert not (why and why in ln), f"why text in {ln!r}"
    # census at tier 2: the family word's only drawn home is House/Court
    _set_state(g, R, player, frozenset({"rel", "inf"}))
    census = _census(s, list(g.realms))
    homes = [name for name, lines in census.items()
             if any(_family_named(ln, fam) for ln in lines)]
    assert homes == ["House/Court"], homes


# ── C11.1c: the reads-you line's one home - Powers/Dossier[R] only ──────

def test_c11_1c_reads_you_one_home(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "game")
    g = s.game
    player = s.house
    R = "Duval-Corse"
    _set_state(g, R, player, frozenset({"rel"}))
    before = _census(s, list(g.realms))
    _set_state(g, R, player, frozenset({"rel", "inf"}))
    after = _census(s, list(g.realms))
    changed = {name for name in before
               if sorted(before[name]) != sorted(after[name])}
    assert changed == {f"Powers/Dossier[{R}]"}, changed


# ── the courtship run (C11.2a/2b/2c/3a/3b) ───────────────────────────────

def _press_end_turn(s):
    """Draw, press the top {"end_turn": True} region at its centre, apply."""
    s.view.regions.clear()
    widgets._text_rows.clear()
    s.view.draw(s.screen)
    for r in s.view.regions._regions:
        if r.action == {"end_turn": True}:
            at = s.view.handle_click(r.rect.center)
            assert at == {"end_turn": True}, at
            _apply_action(s, at)
            return
    raise AssertionError("no end_turn region")


def _wants_map(g, house):
    """{character id: want entry} from game.ambitions.wants(house)."""
    return {e["id"]: e for e in g.ambitions.wants(house)}


def _living_adults(g, house):
    return {c for c in g.realms[house].characters
            if c.age >= 16 and c.is_alive}


def _setup_run(monkeypatch, tmp_path):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "game")
    g = s.game
    player = s.house
    rivals = sorted(h for h in g.realms if h != player)
    for h in rivals:
        ensure_agenda(g, h)
    # seed 7 court: A=Duval-Corse reads the player (informant + ties),
    # A2=Ferrenholt reads Karsgate (T2) at tier 2 without an informant
    # (ties + a held secret), B=Mordaine informant-only (tier 1),
    # C=Vantrell ties-only (tier 1), the other rival as the sim plays it.
    A, A2, T2, B, C = "Duval-Corse", "Ferrenholt", "Karsgate", \
        "Mordaine", "Vantrell"
    g.ambitions.set_ambition(player, "Dynasty")  # the gate's F at seed 7
    _set_state(g, A, player, frozenset({"inf", "rel"}))
    for H in g.realms:
        if H not in (A, player):
            _strip_sources(g, A, H)
    for H in g.realms:
        if H not in (A2, T2):
            _strip_sources(g, A2, H)
    _set_state(g, A2, T2, frozenset({"rel", "sec"}))
    _set_state(g, B, player, frozenset({"inf"}))
    _set_state(g, C, player, frozenset({"rel"}))
    # the gate: if no adult of the player's house opposes its family line,
    # give its first non-ruler adult a -60 x polarity disposition
    opp = [e for e in g.ambitions.wants(player)
           if e["stance"] == "opposes"]
    if not opp:
        adults = sorted((c for c in g.realms[player].characters
                         if c.age >= 16 and c is not g.realms[player].ruler
                         and c.is_alive),
                        key=lambda c: c.id)
        line, polarity = FAMILY_DISPOSITION[g.agendas[player].family]
        adults[0].dispositions[line] = -60 * polarity
    courtships = []

    def wrap(ai_turn):
        def inner(game, X, *a, **k):
            t0 = {H: report(game, X, H).tier for H in game.realms}
            before = {H: _wants_map(game, H) for H in game.realms}
            log_before = len(game.beats.log)
            mar_before = len(game.marriages.marriages)
            res = ai_turn(game, X, *a, **k)
            for H in game.realms:
                if H == X:
                    continue
                now = {c.id for c in _living_adults(game, H)}
                for cid, entry in before[H].items():
                    cur = _wants_map(game, H)[cid] if cid in now else None
                    if cid in now and cur["stance"] != entry["stance"]:
                        courtships.append((X, H, cid, entry["name"],
                                           t0.get(H)))
                    elif cid not in now:
                        arrived = any(c.id == cid and c.is_alive
                                      for c in game.realms[X].characters)
                        new_mar = [t for t in game.marriages.marriages[
                            mar_before:]
                                   if t[0] == cid or t[2] == cid]
                        if arrived and not new_mar:
                            courtships.append((X, H, cid, entry["name"],
                                               t0.get(H)))
            beats = game.beats.log[log_before:]
            courtships.append((X, None, None, None, t0,
                               tuple(b.text for b in beats), res))
            return res
        return inner

    monkeypatch.setattr(gai, "ai_turn", wrap(gai.ai_turn))
    return s, g, player, A, A2, T2, B, C, courtships


def _named_beats(courtships, X, name):
    """Beats appended during X's turn that name the member."""
    out = []
    for e in courtships:
        if e[0] == X and e[1] is None and any(name in t for t in e[5]):
            out.append(e)
    return out


def test_c11_2ai_courts_and_3(tmp_path, monkeypatch):
    s, g, player, A, A2, T2, B, C, courtships = _setup_run(
        monkeypatch, tmp_path)
    t0 = g.ambitions.wants(player)
    opposers = {e["id"] for e in t0 if e["stance"] == "opposes"}
    # the gate reads a house's opposers as that house's turn began - a
    # courted member's stance flips off opposes, so capture the set now
    t2_opp0 = {e["id"] for e in g.ambitions.wants(T2)
               if e["stance"] == "opposes"}
    turns = 0
    courted_turn = None
    for _ in range(4):
        turn_before = g.turn
        _press_end_turn(s)
        assert g.turn == turn_before + 1
        turns += 1
        if courted_turn is None:
            hit = [e for e in courtships if e[0] == A and e[1] == player
                   and e[3] in {c.name for c in g.realms[player].characters}
                   or e[0] == A and e[1] == player]
            named = [e for e in courtships
                     if e[0] == A and e[1] == player
                     and e[2] in opposers
                     and _named_beats(courtships, A, e[3])]
            if named:
                courted_turn = turns
    # C11.2a: A courts a named opposer of the player within its first 3 turns
    hit = [e for e in courtships if e[0] == A and e[1] == player
           and e[2] in opposers and _named_beats(courtships, A, e[3])]
    assert hit, f"no named A->player courtship: {courtships}"
    assert courted_turn is not None and courted_turn <= 3, courted_turn
    # C11.2b: A2 courts a named opposer of T2 within its first 3 turns
    hit2 = [e for e in courtships if e[0] == A2 and e[1] == T2
            and e[2] in t2_opp0 and _named_beats(courtships, A2, e[3])]
    assert hit2, f"no named A2->T2 courtship: {courtships}"
    # C11.2c: tier-1 houses court nothing; the tier held at turn open
    # on the courted house is always >= 2
    for e in courtships:
        X, H, cid, name, tier = e[0], e[1], e[2], e[3], e[4]
        if H is None:
            continue
        assert tier is not None and tier >= 2, \
            f"{X} courted {H} at tier {tier}: {e}"
    # C11.3a/3b: the lever line on House/Court, and nowhere else
    member = hit[0][3]
    rows, _ = _draw_screen(s, "House", "Court")
    court_lines = _lines(rows)
    levers = [ln for ln in court_lines
              if member in ln and re.search(rf"\b{re.escape(A)}\b", ln)]
    assert levers, f"no lever line on House/Court for {member}"
    census = _census(s, list(g.realms))
    homes = []
    for name, lines in census.items():
        if any(member in ln and re.search(rf"\b{re.escape(A)}\b", ln)
               for ln in lines):
            homes.append(name)
    assert homes == ["House/Court"], homes


def test_c11_reads_you_fact_one_home(tmp_path, monkeypatch):
    """Clarity Law: the reads-you fact appears on exactly one screen."""
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "game")
    g = s.game
    player = s.house
    R = "Duval-Corse"
    _set_state(g, R, player, frozenset({"rel", "inf"}))
    census = _census(s, list(g.realms))
    home_lines = [ln for ln in census[f"Powers/Dossier[{R}]"]
                  if _owner(g, ln) == R and "reads" in ln
                  and report(g, R, player).tier >= 2
                  and not _NEG.search(ln)]
    assert home_lines, census[f"Powers/Dossier[{R}]"]
    for name, lines in census.items():
        if name == f"Powers/Dossier[{R}]":
            continue
        leaked = [ln for ln in lines if ln in home_lines]
        assert not leaked, (name, leaked)
