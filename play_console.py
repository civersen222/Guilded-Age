"""play_console.py — stdin/stdout play protocol over the real engine (M83).

Boots the actual GameApp + GameScreen off-screen (SDL dummy drivers), reads
one command per stdin line, answers one JSON object per stdout line. Engine
prints are rerouted to <run-dir>/engine_stdout.log so the protocol channel
stays parseable. Every command is wrapped: a bad command returns
{"ok": false, "error": ...} and never kills the process.

Usage:
  python play_console.py --civ Rome --difficulty standard --map 96 --ais 7 \
      --seed 42 --run-dir C:/tmp/campaign_X [--resume .../autosave.pkl]
"""
import os
import sys
import json
import shlex
import argparse
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # keep stdout JSON-clean

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame  # noqa: E402  (after the dummy-driver env vars)


def _json_safe(v):
    if isinstance(v, (int, float, str, bool, type(None))):
        return v
    if isinstance(v, (list, tuple)):
        return [_json_safe(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _json_safe(x) for k, x in v.items()}
    return str(v)


class PlayConsole:
    def __init__(self, args):
        self.args = args
        self.run_dir = args.run_dir
        os.makedirs(self.run_dir, exist_ok=True)
        # Keep the protocol channel; send engine prints to a log file.
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        self.proto = sys.stdout
        sys.stdout = open(os.path.join(self.run_dir, "engine_stdout.log"),
                          "w", encoding="utf-8", errors="replace")
        self._quit = False
        self._boot()

    # ---------- boot ----------

    def _boot(self):
        import random
        from pygame_app.app import GameApp
        from pygame_app.screens.game_screen import GameScreen
        from game_data import CIVILIZATIONS
        from game import Game
        from ai import AIPlayer
        from tech import TechManager

        self.app = GameApp()
        if self.args.resume:
            game = Game.restore(self.args.resume)
        else:
            random.seed(self.args.seed)
            civ = CIVILIZATIONS[self.args.civ]
            others = [n for n in CIVILIZATIONS if n != self.args.civ]
            ai_names = random.sample(others, min(self.args.ais, len(others)))
            game = Game(civ, ai_civs=[CIVILIZATIONS[n] for n in ai_names],
                        map_width=self.args.map, map_height=self.args.map)
            for n in ai_names:
                game.ai_players[n] = AIPlayer(n, self.args.difficulty.lower())
                game.research[n] = TechManager()
        self.app.game = game
        self.game = game
        if 'game' not in self.app._screens:
            self.app.register_screen('game', GameScreen(self.app))
        self.app.switch_screen('game')
        self.screen = self.app._screens['game']
        self.step()

    def step(self, frames=3):
        """The audit-proven loop body, no display.flip needed for capture."""
        from pygame_app.constants import BG
        for _ in range(frames):
            dt = 0.033
            for event in pygame.event.get():
                self.app.ui_manager.process_events(event)
                scr = self.app._current_screen
                if scr:
                    scr.handle_event(event)
            self.app.ui_manager.update(dt)
            scr = self.app._current_screen
            if scr:
                scr.update(dt)
            self.app.screen.fill(BG)
            if scr:
                scr.draw(self.app.screen)
            self.app.ui_manager.draw_ui(self.app.screen)
            if scr and hasattr(scr, "draw_overlay"):
                scr.draw_overlay(self.app.screen)

    # ---------- helpers ----------

    @property
    def player(self):
        return self.game.player_civ.name

    def _unit(self, unit_id):
        u = self.game.units.get(unit_id)
        if u is None or not getattr(u, "is_alive", False):
            raise ValueError(f"no living unit {unit_id!r}")
        return u

    def _city(self, name):
        c = self.game.cities.get(name)
        if c is None:
            raise ValueError(f"no city {name!r}")
        return c

    def _pending_event(self):
        popup = getattr(self.screen, "_event_choice_popup", None)
        ev = getattr(popup, "_event", None) if popup is not None else None
        if ev is None:
            return None
        try:
            if not popup.is_visible:
                return None
        except Exception:
            pass
        return {"name": getattr(ev, "name", ""),
                "description": getattr(ev, "description", ""),
                "choices": [c.get("name", "") for c in getattr(ev, "choices", [])]}

    # ---------- commands ----------

    def cmd_state(self):
        g = self.game
        p = self.player
        tm = g.tech_manager
        dm = g.diplomacy_manager
        my_cities = [c for c in g.cities.values() if c.owner == p]
        my_units = [(k, u) for k, u in g.units.items()
                    if getattr(u, "owner", "") == p and getattr(u, "is_alive", False)]
        realm = (getattr(g, "realms", None) or {}).get(p)
        chars = []
        if realm is not None:
            roles = {}
            for pos, ch in realm.court.positions.items():
                if ch is not None:
                    roles[ch.id] = pos.value
            if realm.ruler is not None:
                roles[realm.ruler.id] = "Ruler"
            for c in realm.characters:
                if c.is_alive:
                    chars.append({"id": c.id, "name": c.name, "age": c.age,
                                  "role": roles.get(c.id),
                                  "traits": list(getattr(c, "traits", []) or [])})
        my_ids = {c["id"] for c in chars}
        schemes = []
        for s in getattr(g.scheme_manager, "schemes", []):
            if getattr(getattr(s, "agent", None), "id", None) in my_ids:
                schemes.append({"type": getattr(s, "scheme_type", "?"),
                                "target_civ": getattr(s, "target_civ", "?"),
                                "progress": getattr(s, "progress", 0)})
        civs = list(g.civilizations)
        vp = {}
        for n in civs:
            civ_obj = g.civilizations[n]
            rt = g.research.get(n) if n != p else tm
            vp[n] = {"culture": getattr(civ_obj, "culture", 0),
                     "prestige": getattr(civ_obj, "prestige", 0),
                     "techs": len(getattr(rt, "researched", {}) or {}) if rt else 0,
                     "legitimacy": (getattr(g, "legitimacy", {}) or {}).get(n)}
        return {
            "ok": True,
            "turn": g.state.turn,
            "budget": getattr(g.state, "turn_budget", None),
            "game_over": getattr(g.state, "game_over", False),
            "my": {
                "civ": p,
                "gold": g.gold.get(p, 0),
                "faith": g.faith_points.get(p, 0),
                "legitimacy": (getattr(g, "legitimacy", {}) or {}).get(p),
                "happiness": g.happiness.get(p, 0),
                "research": {
                    "current": getattr(tm, "current_research", None),
                    "progress": getattr(tm, "current_research_progress", 0),
                    "researched_count": len(getattr(tm, "researched", {}) or {}),
                    "available": [t.name for t in tm.get_available_techs()[:12]],
                },
                "cities": [{"name": c.name, "pos": list(c.position),
                            "pop": c.population,
                            "production": (c.production_queue[0]
                                           if getattr(c, "production_queue", None) else None),
                            "unrest": round(getattr(c, "unrest", 0.0), 1),
                            "dial": getattr(c, "extraction_dial", None)}
                           for c in my_cities],
                "units": [{"id": k, "type": u.unit_type, "pos": list(u.position),
                           "hp": getattr(u, "hp", None),
                           "moves": getattr(u, "moves_left", 0),
                           "fortified": getattr(u, "is_fortified", False),
                           "commander": getattr(getattr(u, "commander", None), "name", None)}
                          for k, u in my_units],
                "characters": chars,
                "schemes": schemes,
            },
            "world": {
                "relations": {f"{a}|{b}": v for (a, b), v in dm.relations.items()},
                "wars": {k: list(v) for k, v in dm.wars.items() if v},
                "truces": {f"{a}|{b}": v for (a, b), v in getattr(dm, "truces", {}).items()},
                "city_counts": {n: sum(1 for c in g.cities.values() if c.owner == n)
                                for n in civs},
                "victory_progress": vp,
            },
            "events": [str(e) for e in (g.state.turn_events or [])],
            "pending_event": self._pending_event(),
        }

    def cmd_build(self, city_name, item):
        c = self._city(city_name)
        if c.owner != self.player:
            raise ValueError(f"{city_name} is not your city")
        researched = set(getattr(self.game.tech_manager, "unlocked_techs", set()) or set())
        researched |= set((getattr(self.game.tech_manager, "researched", {}) or {}).keys())
        owned = self.game.get_owned_resources(self.player)
        ok = c.assign_production(item, researched_techs=researched, owned_resources=owned)
        return {"ok": bool(ok), "city": c.name, "item": item,
                "queue": list(getattr(c, "production_queue", []))}

    def cmd_research(self, tech_name):
        tm = self.game.tech_manager
        want = tech_name.casefold()
        tech = next((t for t in tm.get_available_techs()
                     if t.name.casefold() == want), None)
        if tech is None:
            raise ValueError(f"tech {tech_name!r} not available")
        tm.start_research(tech)
        return {"ok": True, "research": tech.name}

    def cmd_move(self, unit_id, x, y):
        u = self._unit(unit_id)
        if u.owner != self.player:
            raise ValueError(f"{unit_id} is not your unit")
        ok = self.game.military_manager.move_unit(u, (int(x), int(y)))
        return {"ok": bool(ok), "id": unit_id, "pos": list(u.position),
                "moves": getattr(u, "moves_left", 0)}

    def cmd_attack(self, unit_id, target_id):
        att = self._unit(unit_id)
        dfn = self._unit(target_id)
        if att.owner != self.player:
            raise ValueError(f"{unit_id} is not your unit")
        result = self.game.military_manager.combat(att, dfn)
        if result is None:
            return {"ok": False, "error": "combat refused (range/moves/target)"}
        return {"ok": True,
                "result": {k: _json_safe(v) for k, v in vars(result).items()},
                "attacker_hp": getattr(att, "hp", None),
                "defender_hp": getattr(dfn, "hp", None)}

    def cmd_fortify(self, unit_id):
        u = self._unit(unit_id)
        if u.owner != self.player:
            raise ValueError(f"{unit_id} is not your unit")
        u.is_fortified = True
        return {"ok": True, "id": unit_id}

    def cmd_found(self, unit_id):
        from game_data import TerrainType
        g = self.game
        u = self._unit(unit_id)
        if u.owner != self.player or getattr(u, "unit_type", "") != "Settler":
            raise ValueError(f"{unit_id} is not your Settler")
        pos = u.position
        if any(c.position == pos for c in g.cities.values()):
            raise ValueError("a city already exists here")
        tile = g.map.tiles.get(pos)
        if not tile or tile.terrain in (TerrainType.WATER_COAST, TerrainType.OCEAN):
            raise ValueError("cannot settle on water")
        city = g.found_city(u)
        g.city_manager.cities = list(g.cities.values())
        return {"ok": True, "city": city.name, "pos": list(city.position)}

    def cmd_war(self, civ):
        ok = self.game.diplomacy_manager.declare_war(self.player, civ)
        return {"ok": bool(ok), "war": [self.player, civ],
                "note": None if ok else "refused (truce binds or already at war)"}

    def cmd_peace(self, civ):
        dm = self.game.diplomacy_manager
        ruler = self.game.rulers.get(self.player)
        msg = dm.propose_peace(self.player, civ, ruler=ruler)
        at_war = civ in (dm.wars.get(self.player) or [])
        return {"ok": True, "message": msg, "still_at_war": at_war}

    def cmd_marry(self, civ):
        from marriages import arrange_match_between
        msg = arrange_match_between(self.game, self.player, civ)
        return {"ok": msg is not None, "message": msg}

    def cmd_scheme(self, kind, target_civ):
        from pygame_app.popups.scheme_menu import start_scheme_against
        msg = start_scheme_against(self.game, target_civ, kind)
        return {"ok": msg is not None, "message": msg}

    def cmd_appoint(self, position, char_id=None):
        from court import CourtPosition
        want = position.replace("_", " ").casefold()
        pos = next((cp for cp in CourtPosition
                    if cp.value.casefold() == want or cp.name.casefold() == want), None)
        if pos is None:
            raise ValueError(f"no position {position!r}; use one of "
                             f"{[cp.name for cp in CourtPosition]}")
        realm = (getattr(self.game, "realms", None) or {}).get(self.player)
        if realm is None:
            raise ValueError("no realm")
        if char_id is None:
            from pygame_app.popups.appointments import appoint_best
            msg = appoint_best(realm, pos, self.game.state.turn)
            return {"ok": msg is not None, "message": msg}
        ch = next((c for c in realm.characters
                   if c.id == char_id and c.is_alive), None)
        if ch is None:
            raise ValueError(f"no living character {char_id!r}")
        ok = realm.court.appoint(pos, ch, self.game.state.turn)
        return {"ok": bool(ok), "position": pos.value, "character": ch.name}

    def cmd_dial(self, city_name, value):
        from labor import clamp_dial
        c = self._city(city_name)
        if c.owner != self.player:
            raise ValueError(f"{city_name} is not your city")
        c.extraction_dial = clamp_dial(float(value))
        return {"ok": True, "city": c.name, "dial": c.extraction_dial}

    def cmd_choose(self, index):
        popup = getattr(self.screen, "_event_choice_popup", None)
        ev = getattr(popup, "_event", None) if popup is not None else None
        if ev is None:
            raise ValueError("no pending event")
        choices = getattr(ev, "choices", [])
        if choices:
            msg = ev.evaluate_choice(choices[int(index)])
        else:
            effects = getattr(ev, "effects", {})
            msg = ev.evaluate_choice({"effects": effects, "name": "OK"}) if effects else ""
        try:
            popup._kill()
        except Exception:
            pass
        return {"ok": True, "message": str(msg)}

    def cmd_end_turn(self):
        g = self.game
        self.screen._process_next_turn(g)
        self.step()
        g.checkpoint(os.path.join(self.run_dir, "autosave.pkl"))
        over = getattr(g.state, "game_over", False)
        victory = None
        if over:
            victory = (f"{getattr(g.state, 'winner', '?')} wins by "
                       f"{getattr(g.state, 'victory_type', '?')}")
        return {"ok": True, "turn": g.state.turn,
                "events": [str(e) for e in (g.state.turn_events or [])],
                "game_over": over, "victory": victory,
                "pending_event": self._pending_event()}

    def cmd_shot(self, name, popup_kind=None):
        if popup_kind:
            self.screen._open_popup(popup_kind, self.game)
        self.step()
        path = os.path.join(self.run_dir, f"{name}.png")
        pygame.image.save(self.app.screen, path)
        if popup_kind:
            active = getattr(self.screen, "_active_popup", None)
            if active is not None:
                try:
                    active._kill()
                except Exception:
                    pass
                self.screen._active_popup = None
            self.step()
        return {"ok": True, "path": path, "bytes": os.path.getsize(path)}

    def cmd_save(self, name):
        path = os.path.join(self.run_dir, f"{name}.pkl")
        self.game.checkpoint(path)
        return {"ok": True, "path": path}

    def cmd_quit(self):
        self._quit = True
        return {"ok": True, "bye": True}

    # ---------- dispatch ----------

    COMMANDS = {
        "state": (cmd_state, 0, 0), "build": (cmd_build, 2, 2),
        "research": (cmd_research, 1, 1), "move": (cmd_move, 3, 3),
        "attack": (cmd_attack, 2, 2), "fortify": (cmd_fortify, 1, 1),
        "found": (cmd_found, 1, 1), "war": (cmd_war, 1, 1),
        "peace": (cmd_peace, 1, 1), "marry": (cmd_marry, 1, 1),
        "scheme": (cmd_scheme, 2, 2), "appoint": (cmd_appoint, 1, 2),
        "dial": (cmd_dial, 2, 2), "choose": (cmd_choose, 1, 1),
        "end_turn": (cmd_end_turn, 0, 0), "shot": (cmd_shot, 1, 2),
        "save": (cmd_save, 1, 1), "quit": (cmd_quit, 0, 0),
    }

    def dispatch(self, line):
        parts = shlex.split(line)
        if not parts:
            return {"ok": False, "error": "empty command"}
        name, args = parts[0], parts[1:]
        entry = self.COMMANDS.get(name)
        if entry is None:
            return {"ok": False, "error": f"unknown command {name!r}; "
                                          f"commands: {sorted(self.COMMANDS)}"}
        fn, lo, hi = entry
        if not (lo <= len(args) <= hi):
            return {"ok": False,
                    "error": f"{name} takes {lo}-{hi} args, got {len(args)}"}
        return fn(self, *args)

    def reply(self, obj):
        self.proto.write(json.dumps(obj, default=str) + "\n")
        self.proto.flush()

    def run(self):
        self.reply({"ok": True, "ready": True, "turn": self.game.state.turn,
                    "civ": self.player, "run_dir": self.run_dir})
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                resp = self.dispatch(line)
            except SystemExit:
                raise
            except Exception:
                resp = {"ok": False, "error": traceback.format_exc()}
            self.reply(resp)
            if self._quit:
                break
        pygame.quit()


def main():
    ap = argparse.ArgumentParser(description="CivKings terminal play console (M83)")
    ap.add_argument("--civ", default="Rome")
    ap.add_argument("--difficulty", default="standard")
    ap.add_argument("--map", type=int, default=96)
    ap.add_argument("--ais", type=int, default=7)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--resume", default=None)
    args = ap.parse_args()
    PlayConsole(args).run()


if __name__ == "__main__":
    main()
