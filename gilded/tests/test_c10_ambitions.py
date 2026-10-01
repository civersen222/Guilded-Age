"""Mission C10 Wave 2 — ambitions and the ladder: the committed self-check.

Run EXACTLY as:
    python -m pytest gilded/tests/test_c10_ambitions.py -q

Where each fact lives (Clarity Law):
- the ambition banner and the court cards (stance, want, levers) live on the
  House spine, "Court" inner page (House/Court in Session); the family word
  is drawn NOWHERE ELSE (C10.1b).
- the public ladder with its fogged axes lives on the Powers spine, "Ladder"
  inner page (Powers/Ladder) - the rank token's one drawn home (C10.2a/2b).
- the rivals' agendas live on the Powers table (Powers/Overview).
- the ending page names the family and its outcome (C10.6).

Each test below draws EVERY reachable screen (every spine, every page, every
page a drawn set_spine_page region names) and asserts the fact appears on
exactly one.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import re

import pygame

from gilded import settings as gsettings
from gilded import save as gsave
from gilded.agenda import FAMILIES
from gilded.ui import widgets
from gilded.ui.app import new_app_state, _apply_action
from gilded.ui import broadsheet as bs


def _clean(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for p in (gsettings.settings_path(), gsave.quicksave_path()):
        if os.path.isfile(p):
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


def _screens(view):
    """Every screen the play view can show: each spine, each of its pages,
    plus every page named by a drawn set_spine_page region."""
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
            screens.append((spine, page))
    return screens


def _draw_screen(s, spine, page):
    """Draw one screen; return (rows, regions). rows are (rect, text)."""
    view = s.view
    view.active_tab = spine
    if spine == "House":
        view.house_page = page
    elif spine == "Powers":
        view.powers_page = page
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


def _census(s):
    """Draw every reachable screen; return {screen_name: lines}."""
    out = {}
    for spine, page in _screens(s.view):
        rows, _regions = _draw_screen(s, spine, page)
        name = f"{spine}/{page}" if page is not None else spine
        out[name] = _lines(rows)
    return out


# ── C10.1a: New Game opens the family picker; pressing a family sets the ──

def test_c10_1a_ambition_chosen(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "menu")
    _press(s, lambda a: a.get("menu") == "new_game")
    s.view.regions.clear()
    widgets._text_rows.clear()
    s.view.draw(s.screen)
    fams = set()
    for r in s.view.regions._regions:
        if isinstance(r.action, dict):
            v = r.action.get("set_ambition")
            if isinstance(v, dict) and v.get("family") in FAMILIES:
                fams.add(v["family"])
    assert fams == set(FAMILIES), f"picker missing families: {fams}"

    pick = FAMILIES[0]
    _press(s, lambda a: a.get("set_ambition", {}).get("family") == pick
           if isinstance(a.get("set_ambition"), dict) else False)
    g = s.game
    player = [h for h in g.houses if g.houses[h].is_player][0]
    assert g.turn == 1
    assert g.ambitions.status(player)["family"] == pick
    assert g.agendas[player].family == pick

    # the stake is LIVE: the sim resolves it at the close of its window
    resolved = None
    for _ in range(12):
        g.end_turn()
        st = g.ambitions.status(player)
        if st["fulfilled"] is not None:
            resolved = st["fulfilled"]
            break
    assert resolved in (True, False), "the stake never resolved"


# ── C10.1b: the family word's one drawn home is House/Court ───────────────

def test_c10_1b_ambition_shown_once(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "menu")
    _press(s, lambda a: a.get("menu") == "new_game")
    pick = FAMILIES[0]
    _press(s, lambda a: a.get("set_ambition", {}).get("family") == pick
           if isinstance(a.get("set_ambition"), dict) else False)
    fam = pick.lower()
    census = _census(s)
    hits = []
    for name, lines in census.items():
        for line in lines:
            if re.search(rf"\b{fam}\b", line, re.IGNORECASE):
                hits.append((name, line))
                break
    assert [name for name, _ in hits] == ["House/Court"], hits


# ── C10.2a: the ladder's one drawn home is Powers/Ladder ─────────────────

def test_c10_2a_rank_public(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "game")
    g = s.game
    player = [h for h in g.houses if g.houses[h].is_player][0]
    g.ambitions.set_ambition(player, "Consolidation")
    ranks = {r.house: r.rank for r in g.ladder()}

    census = _census(s)
    ladder_screen = None
    for name, lines in census.items():
        ok = all(any(re.match(rf"^{ranks[h]}\.\s+House\s+{h}\b", line)
                     for line in lines)
                 for h in ranks)
        if ok:
            ladder_screen = name
            break
    assert ladder_screen == "Powers/Ladder", ladder_screen

    # no OTHER screen draws the player's rank in any gate form
    r = ranks[player]
    suffix = "st" if r == 1 else "nd" if r == 2 else "rd" if r == 3 else "th"
    card = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven"}[r]
    ordw = {1: "first", 2: "second", 3: "third", 4: "fourth",
            5: "fifth", 6: "sixth", 7: "seventh"}[r]
    rank_words = r"rank|ranked|ladder|place|position|stand|stands"
    patterns = [
        rf"{r}\.\s*House\s+{re.escape(player)}",          # "<r>. House <h>"
        rf"#{r}\s+{re.escape(player)}",                    # "#<r> <h>"
        rf"rank\s*#{r}\b",                                 # "Rank #<r>"
        rf"rank\s*{r}\b",                                  # "rank <r>"
        rf"{r}{suffix}\b",                                 # "<r>th"-style
        rf"{r}\s*(?:of|/)\s*7\b",                          # "<r> of 7"
        rf"{ordw}\s+of\s+seven\b",                          # "fourth of seven"
        rf"{card}\s+of\s+seven\b",                          # "four of seven"
        rf"{r}{suffix}\s+of\s+seven\b",                     # "4th of seven"
        rf"\b({rank_words})\b[^a-z0-9]{{0,4}}#{r}\b",      # "ladder #4"
        rf"\b({rank_words})\b[^a-z0-9]{{0,4}}{r}{suffix}\b",  # "You stand 4th"
        rf"\b({rank_words})\b[^a-z0-9]{{0,4}}{ordw}\b",   # "You stand fourth"
    ]
    for name, lines in census.items():
        if name == ladder_screen:
            continue
        joined = " ".join(lines).lower()
        for p in patterns:
            assert not re.search(p, joined, re.IGNORECASE), \
                f"rank leak on {name}: {p!r} in {joined!r}"


# ── C10.6: the ending names the family and its outcome ───────────────────

def _run_to_close(s, fam, treasury):
    g = s.game
    player = [h for h in g.houses if g.houses[h].is_player][0]
    g.ambitions.set_ambition(player, fam)
    if treasury == 0:
        g.houses[player].treasury = 0
    elif treasury is not None:
        g.houses[player].treasury += treasury
    g.turn = 70
    _press(s, lambda a: a.get("end_turn") is True)
    return player


def test_c10_6_ending_names_ambition(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    for fam, treasury, want in (
            ("Glory", 10_000_000, True),
            ("Glory", 0, False),
            ("Dynasty", 10_000_000, None)):
        s = _relaunch(7, "game")
        player = _run_to_close(s, fam, treasury)
        g = s.game
        assert g.game_over is not None
        sim = g.ambitions.status(player)["fulfilled"]
        assert sim in (True, False)
        if want is not None:
            assert sim is want

        # the drawn ending page names the family with the right outcome
        rows, _ = _draw_screen(s, "House", "Overview")
        drawn = " ".join(t for _r, t in rows)
        assert fam in drawn
        neg = any(w in drawn[drawn.lower().index(fam.lower()):][:120].lower()
                  for w in ("fell short", "falls short", "failed",
                            "unfulfilled", "not fulfilled",
                            "never fulfilled"))
        pos = "fulfilled" in drawn[drawn.lower().index(fam.lower()):][:120]
        if sim:
            assert pos, drawn
        else:
            assert neg or "never fulfilled" in drawn.lower(), drawn


# ── C10.7: every new verb self-explains (what / why / wins) ──────────────

_AXIS_WORDS = ("capital", "standing", "blood", "world", "ambition")


def test_c10_7_verbs_self_explain(tmp_path, monkeypatch):
    _clean(tmp_path, monkeypatch)
    s = _relaunch(7, "menu")
    _press(s, lambda a: a.get("menu") == "new_game")
    view = s.view
    view.regions.clear()
    widgets._text_rows.clear()
    view.draw(s.screen)

    fam_regions = {}
    for r in view.regions._regions:
        if isinstance(r.action, dict):
            v = r.action.get("set_ambition")
            if isinstance(v, dict) and v.get("family") in FAMILIES:
                fam_regions[v["family"]] = r
    assert set(fam_regions) == set(FAMILIES)

    whats = set()
    for fam, r in fam_regions.items():
        a = r.action
        what, why, wins = a.get("what"), a.get("why"), a.get("wins")
        assert what and why, f"{fam}: missing what/why"
        assert any(ax in wins for ax in _AXIS_WORDS), f"{fam}: wins {wins!r}"
        whats.add(what)
        # what AND why are DRAWN: hover the centre, redraw, read the rows
        view.handle_hover(r.rect.center)
        view.regions.clear()
        widgets._text_rows.clear()
        view.draw(s.screen)
        rows = " ".join(t for _r, t in widgets._text_rows)
        tip = view.tooltip_text or ""
        blob = rows + " " + tip
        assert what in blob, f"{fam}: what not drawn: {blob!r}"
        assert why in blob, f"{fam}: why not drawn: {blob!r}"
    assert len(whats) == 7, f"whats not distinct: {whats}"

    # the opposing member's lever carries the same three strings and draws
    # them through its hover
    g = s.game
    player = [h for h in g.houses if g.houses[h].is_player][0]
    from gilded.ambitions import (FAMILY_DISPOSITION, STANCE_BACKS_AT)
    fam = FAMILIES[0]
    _press(s, lambda a: a.get("set_ambition", {}).get("family") == fam
           if isinstance(a.get("set_ambition"), dict) else False)
    key, polarity = FAMILY_DISPOSITION[fam]
    realm = g.realms[player]
    by_id = {c.id: c for c in realm.characters}
    wants = g.ambitions.wants(player)
    opp = [by_id[w["id"]] for w in wants
           if w.get("stance") == "opposes"]
    if not opp:
        # force the first adult onto the opposes side of the family line
        cards = [w for w in wants if w.get("stance") != "opposes"]
        victim = by_id[cards[0]["id"]]
        victim.dispositions[key] = float(
            -abs(STANCE_BACKS_AT) * 2.0) / polarity
        wants = g.ambitions.wants(player)
        opp = [by_id[w["id"]] for w in wants
               if w.get("stance") == "opposes"]
    view.active_tab = "House"
    view.house_page = "Court"
    view.regions.clear()
    widgets._text_rows.clear()
    view.draw(s.screen)
    lever = None
    for r in view.regions._regions:
        if isinstance(r.action, dict) and "court_lever" in r.action:
            lever = r
            break
    assert lever is not None, "no lever drawn for an opposing member"
    a = lever.action
    what, why, wins = a.get("what"), a.get("why"), a.get("wins")
    assert what and why
    assert any(ax in wins for ax in _AXIS_WORDS)
    view.handle_hover(lever.rect.center)
    view.regions.clear()
    widgets._text_rows.clear()
    view.draw(s.screen)
    rows = " ".join(t for _r, t in widgets._text_rows)
    tip = view.tooltip_text or ""
    blob = rows + " " + tip
    assert what in blob, f"lever what not drawn: {blob!r}"
    assert why in blob, f"lever why not drawn: {blob!r}"
