"""The Console (mission G19): the game as a file-bridge.

A headless driver for GildedGame that speaks the same file protocol the
old engine's play_console used: it watches <dir>/cmd_in.txt for appended
command lines and appends one JSON object per command to <dir>/replies.jsonl.
The player rules through the very same levers the AI plays - docket.rule and
docket.initiative, the standing directives, and end_turn - so a scripted
driver (or a person with two open files) plays the whole century. Every
command is wrapped: a bad command answers {"ok": false, "error": ...} and
never stops the loop.

  python -m gilded --console <dir> [--seed N] [--house NAME] [--ai-only]
"""

import json
import os
import pickle
import shlex
import time
import traceback
from typing import List, Optional

from gilded.ai import _executor_for
from gilded.chassis import ATTENTION_PER_TURN, GildedGame, year_of
from gilded.directives import DIRECTIVE_KEYS
from gilded.docket import DOMAIN_SEAT, initiative as docket_initiative, rule as docket_rule
from gilded.endings import judge
from gilded.papers import compose, format_broadsheet
from gilded.society.court import CourtPosition

POLL_SECONDS = 0.05
CMD_FILE = "cmd_in.txt"
REPLY_FILE = "replies.jsonl"


def _coerce(value: str):
    """A key=value initiative argument: int, then float, then the raw string."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


class Console:
    def __init__(self, bridge_dir: str, seed: int,
                 player_house: Optional[str] = None, ai_only: bool = False):
        self.bridge_dir = bridge_dir
        os.makedirs(bridge_dir, exist_ok=True)
        self.ai_only = ai_only
        effective = None if ai_only else player_house
        self.game = GildedGame(seed, effective)
        if effective is None:
            effective = sorted(self.game.houses)[0]
            if not ai_only:
                self.game.houses[effective].is_player = True
        self.house = effective
        self._quit = False

    # --- helpers -------------------------------------------------------------

    @property
    def realm(self):
        return self.game.realms[self.house]

    def _find_character(self, name: str):
        for c in self.realm.characters:
            if c.is_alive and c.name == name:
                return c
        raise ValueError(f"no living character named {name!r}")

    def _seat_of(self, realm, char_id: str) -> Optional[str]:
        for seat, holder in realm.court.positions.items():
            if holder is not None and holder.id == char_id:
                return seat.value
        if realm.ruler is not None and realm.ruler.id == char_id:
            return "Ruler"
        return None

    def _wars_brief(self) -> List[dict]:
        return [{"aggressor": w.aggressor, "defender": w.defender,
                 "score": round(w.war_score, 1)} for w in self.game.wars]

    # --- commands ------------------------------------------------------------

    def cmd_state(self, *args):
        g = self.game
        h = self.house
        return {"ok": True, "turn": g.turn, "year": year_of(g.turn),
                "house": h, "attention": g.attention.get(h, 0),
                "treasury": round(g.houses[h].treasury, 1),
                "legitimacy": round(g.legitimacy.get(h, 0.0), 1),
                "provinces": len(g.provinces_of(h)),
                "enterprises": len(g.ents_of(h)),
                "wars": self._wars_brief(),
                "game_over": g.game_over}

    def cmd_papers(self, *args):
        text = format_broadsheet(compose(self.game, self.house))
        return {"ok": True, "text": text}

    def cmd_docket(self, *args):
        petitions = []
        for i, p in enumerate(self.game.docket_by_house.get(self.house, []), 1):
            petitions.append({
                "n": i, "pid": p.pid, "kind": p.kind, "domain": p.domain,
                "escalated": p.escalated, "text": p.text,
                "options": [{"key": o.key, "text": o.text} for o in p.options]})
        return {"ok": True, "attention": self.game.attention.get(self.house, 0),
                "petitions": petitions}

    def cmd_rule(self, pid, option_key, *rest):
        g = self.game
        h = self.house
        if g.attention.get(h, 0) <= 0:
            raise ValueError("no attention left this turn")
        pid = int(pid)
        petition = next((p for p in g.docket_by_house.get(h, [])
                         if p.pid == pid), None)
        if petition is None:
            raise ValueError(f"no petition {pid} on the docket")
        if rest and rest[0] == "executor":
            executor = self._find_character(" ".join(rest[1:]))
        elif rest:
            raise ValueError("usage: rule <pid> <option_key> [executor <name>]")
        else:
            executor = _executor_for(g, self.realm, petition.domain)
        g.attention[h] -= 1
        msgs = docket_rule(g, petition, option_key, executor)
        g.docket_by_house[h].remove(petition)
        return {"ok": True, "executor": executor.name, "messages": msgs,
                "attention": g.attention.get(h, 0)}

    def cmd_initiative(self, verb, *pairs):
        g = self.game
        h = self.house
        if g.attention.get(h, 0) <= 0:
            raise ValueError("no attention left this turn")
        kwargs = {}
        for pair in pairs:
            if "=" not in pair:
                raise ValueError(f"initiative args are key=value, got {pair!r}")
            key, _, val = pair.partition("=")
            kwargs[key] = _coerce(val)
        from gilded.docket import INITIATIVES
        if verb not in INITIATIVES:
            raise ValueError(f"no such initiative {verb!r}; "
                             f"one of {sorted(INITIATIVES)}")
        domain, _handler = INITIATIVES[verb]
        executor = _executor_for(g, self.realm, domain)
        g.attention[h] -= 1
        msgs = docket_initiative(g, h, verb, executor, **kwargs)
        return {"ok": True, "executor": executor.name, "messages": msgs,
                "attention": g.attention.get(h, 0)}

    def cmd_dial(self, directive, value):
        if directive not in DIRECTIVE_KEYS:
            raise ValueError(f"no such directive {directive!r}; "
                             f"one of {list(DIRECTIVE_KEYS)}")
        self.game.directives[self.house].set_stance(directive, int(value))
        return {"ok": True, "directive": directive,
                "value": self.game.directives[self.house].stances[directive]}

    def cmd_atlas(self, *args):
        g = self.game
        if not args:
            provs = []
            for p in sorted(g.atlas.provinces.values(), key=lambda p: p.pid):
                provs.append({"pid": p.pid, "name": p.name,
                              "owner": p.owner or "(minor)",
                              "terrain": p.terrain, "pop": p.population,
                              "unrest": round(p.unrest, 1)})
            return {"ok": True, "provinces": provs}
        pid = int(args[0])
        p = g.atlas.provinces.get(pid)
        if p is None:
            raise ValueError(f"no province {pid}")
        ents = [{"name": e.name, "kind": e.kind, "tier": e.tier,
                 "dial": round(e.extraction_dial, 1), "director_id": e.director_id}
                for e in g.enterprises if e.province == pid]
        rails = [n for n in sorted(p.neighbors)
                 if (lk := g.atlas.link(pid, n)) is not None and lk.rail]
        return {"ok": True, "pid": pid, "name": p.name,
                "owner": p.owner or "(minor)", "terrain": p.terrain,
                "endowments": dict(p.endowments), "pop": p.population,
                "unrest": round(p.unrest, 1), "garrison": p.garrison,
                "development": p.development,
                "neighbors": sorted(p.neighbors), "rail_links": rails,
                "enterprises": ents}

    def cmd_house(self, *args):
        g = self.game
        name = args[0] if args else self.house
        if name not in g.houses:
            raise ValueError(f"no House {name!r}")
        house = g.houses[name]
        realm = g.realms.get(name)
        seats = {}
        heir = None
        ruler = None
        if realm is not None:
            for seat, holder in sorted(realm.court.positions.items(),
                                       key=lambda kv: kv[0].value):
                seats[seat.value] = holder.name if holder is not None else None
            ruler = realm.ruler.name if realm.ruler is not None else None
            others = [c for c in realm.dynasty.all_characters.values()
                      if c.is_alive and (realm.ruler is None
                                         or c.id != realm.ruler.id)]
            if others:
                heir = max(others, key=lambda c: (c.age, c.name)).name
        return {"ok": True, "name": name, "ruler": ruler, "heir": heir,
                "treasury": round(house.treasury, 1),
                "prestige": round(house.prestige, 1),
                "capital": g.atlas.provinces[house.capital].name,
                "seats": seats, "relations": dict(house.relations),
                "at_war_with": sorted(house.at_war_with),
                "truces": dict(house.truces)}

    def cmd_chars(self, *args):
        realm = self.realm
        living = [c for c in realm.characters if c.is_alive]
        living.sort(key=lambda c: (self._seat_of(realm, c.id) is None,
                                   -c.age, c.name))
        rows = []
        for c in living[:12]:
            rows.append({
                "id": c.id, "name": c.name, "age": c.age,
                "seat": self._seat_of(realm, c.id), "stress": c.stress,
                "stats": {a: c.get_effective_stat(a)
                          for a in ("statecraft", "command", "industry",
                                    "intrigue", "science", "resolve")},
                "traits": list(c.traits)})
        return {"ok": True, "house": self.house, "characters": rows}

    def cmd_end_turn(self, *args):
        g = self.game
        events = g.end_turn()
        return {"ok": True, "turn": g.turn, "game_over": g.game_over,
                "events": [{"text": e.text, "register": e.register,
                            "house": e.house} for e in events]}

    def cmd_run(self, count):
        g = self.game
        ran = 0
        for _ in range(int(count)):
            if g.game_over is not None:
                break
            g.end_turn()
            ran += 1
        return {"ok": True, "ran": ran, "turn": g.turn,
                "game_over": g.game_over}

    def cmd_epilogue(self, *args):
        if self.game.game_over is None:
            return {"ok": False, "error": "the age has not closed"}
        ep = judge(self.game, self.house)
        return {"ok": True, "ending": ep.ending_key,
                "axes": {k: round(v, 1) for k, v in ep.axes.items()},
                "text": ep.text}

    def cmd_save(self, name):
        # The docket carries petition options as live closures, which do not
        # pickle; drop it for the write and rebuild the morning's paper on load.
        path = os.path.join(self.bridge_dir, f"{name}.pkl")
        saved = self.game.docket_by_house
        self.game.docket_by_house = {}
        try:
            with open(path, "wb") as f:
                pickle.dump(self.game, f)
        finally:
            self.game.docket_by_house = saved
        return {"ok": True, "path": path}

    def cmd_load(self, name):
        path = os.path.join(self.bridge_dir, f"{name}.pkl")
        with open(path, "rb") as f:
            self.game = pickle.load(f)
        if self.house not in self.game.houses:
            self.house = sorted(self.game.houses)[0]
        self.game.open_turn()          # the paper the pickle could not carry
        return {"ok": True, "turn": self.game.turn, "house": self.house}

    def cmd_quit(self, *args):
        self._quit = True
        return {"ok": True, "bye": True}

    COMMANDS = {
        "state": cmd_state, "papers": cmd_papers, "docket": cmd_docket,
        "rule": cmd_rule, "initiative": cmd_initiative, "dial": cmd_dial,
        "atlas": cmd_atlas, "house": cmd_house, "chars": cmd_chars,
        "end_turn": cmd_end_turn, "run": cmd_run, "epilogue": cmd_epilogue,
        "save": cmd_save, "load": cmd_load, "quit": cmd_quit,
    }

    def dispatch(self, line: str) -> dict:
        parts = shlex.split(line)
        if not parts:
            return {"ok": False, "error": "empty command"}
        name, args = parts[0], parts[1:]
        fn = self.COMMANDS.get(name)
        if fn is None:
            return {"ok": False, "error": f"unknown command {name!r}; "
                    f"commands: {sorted(self.COMMANDS)}"}
        try:
            return fn(self, *args)
        except Exception:
            return {"ok": False, "error": traceback.format_exc()}

    # --- the bridge loop -----------------------------------------------------

    def serve(self) -> None:
        cmd_path = os.path.join(self.bridge_dir, CMD_FILE)
        reply_path = os.path.join(self.bridge_dir, REPLY_FILE)
        consumed = 0
        while not self._quit:
            complete: List[str] = []
            if os.path.exists(cmd_path):
                with open(cmd_path, encoding="utf-8") as f:
                    complete = f.read().split("\n")[:-1]   # drop trailing partial
            while consumed < len(complete) and not self._quit:
                line = complete[consumed].strip()
                consumed += 1
                if not line:
                    continue
                try:
                    resp = self.dispatch(line)
                except Exception:
                    resp = {"ok": False, "error": traceback.format_exc()}
                with open(reply_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(resp, default=str) + "\n")
            time.sleep(POLL_SECONDS)


def run_console(bridge_dir: str, seed: int,
                player_house: Optional[str] = None,
                ai_only: bool = False) -> None:
    """Boot a headless game and serve the file bridge until 'quit'."""
    Console(bridge_dir, seed, player_house, ai_only).serve()
