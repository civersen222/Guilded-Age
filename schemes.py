"""Schemes: the intrigue economy's working end (M62, spec 6.1).

A scheme is an agent moving against a target: it advances each turn on
the agent's Intrigue, risks discovery each turn against the target
court's counter-intrigue, and resolves at threshold - success, or a
scandal. Evolves the plots.py concepts into the live character layer;
game_manager.py keeps the old PlotManager for its legacy path."""

import random as _random
from typing import List

from simulation import Secret, modify_opinion
from event_engine import Situation, render
from ideology import record_scandal

SCHEME_TYPES = {
    "coup":          {"risk": 0.03, "scandal": 1.5, "success_bonus": 0.15},
    "assassination": {"risk": 0.04, "scandal": 2.0, "success_bonus": 0.10},
}
SCHEME_THRESHOLD = 100
BASE_SUCCESS = 0.3
PARTICIPANT_BONUS = 0.05
DEFENSE_SHIELD = 0.002      # per point of best court Intrigue, per turn
SECRET_POTENCY = 30
EXECUTION_CHANCE = 0.3


class Scheme:
    """One agent moving against one target (both live Characters)."""

    def __init__(self, agent, target, scheme_type: str, target_civ: str):
        self.agent = agent
        self.target = target
        self.scheme_type = scheme_type
        self.target_civ = target_civ
        self.participants = []      # fellow travellers (Characters)
        self.progress = 0.0

    def add_participant(self, char) -> None:
        if (char is not self.agent and char is not self.target
                and char not in self.participants):
            self.participants.append(char)

    def advance(self) -> None:
        self.progress += 3 + self.agent.get_effective_stat("intrigue") // 2

    def success_chance(self, defense: int) -> float:
        chance = (BASE_SUCCESS + SCHEME_TYPES[self.scheme_type]["success_bonus"]
                  + PARTICIPANT_BONUS * len(self.participants)) * 0.5
        chance += self.agent.get_effective_stat("intrigue") * 0.01
        chance -= defense * 0.01
        return max(0.0, min(0.9, chance))


class SchemeManager:
    """Owns every live scheme; advanced once per turn from tick_relationships."""

    def __init__(self):
        self.schemes: List[Scheme] = []

    def start_scheme(self, agent, target, scheme_type: str, target_civ: str) -> Scheme:
        s = Scheme(agent, target, scheme_type, target_civ)
        self.schemes.append(s)
        return s

    def scheming(self, char) -> bool:
        return any(s.agent is char for s in self.schemes)

    def advance_all(self, game, rng=_random) -> List[str]:
        """One turn of every scheme: prune the moot, advance the live,
        roll discovery, resolve at threshold."""
        msgs: List[str] = []
        realms = getattr(game, "realms", None) or {}
        for s in list(self.schemes):
            trealm = realms.get(s.target_civ)
            if trealm is None or not s.agent.is_alive or not s.target.is_alive:
                self.schemes.remove(s)
                continue
            if (s.scheme_type == "coup"
                    and game.rulers.get(s.target_civ) is not s.target):
                self.schemes.remove(s)   # the throne already changed hands
                continue
            s.advance()
            defense = max((ch.get_effective_stat("intrigue")
                           for ch in trealm.court.positions.values()
                           if ch and ch.is_alive), default=0)
            if rng.random() < (SCHEME_TYPES[s.scheme_type]["risk"]
                               + defense * DEFENSE_SHIELD):
                self.schemes.remove(s)
                msgs.extend(self._discover(game, s, trealm, rng))
                continue
            if s.progress < SCHEME_THRESHOLD:
                continue
            self.schemes.remove(s)
            if rng.random() < s.success_chance(defense):
                msgs.extend(self._succeed(game, s, trealm))
            else:
                msgs.extend(self._discover(game, s, trealm, rng))
        return msgs

    def _succeed(self, game, s, trealm) -> List[str]:
        msgs = []
        agent, targ = s.agent, s.target
        if s.scheme_type == "coup":
            for pos, ch in trealm.court.positions.items():
                if ch and ch.id == agent.id:
                    trealm.court.positions[pos] = None
            trealm.ruler = agent
            trealm.court.ruler = agent
            game.rulers[trealm.civ_name] = agent
            if agent.id not in trealm.dynasty.all_characters:
                trealm.dynasty.all_characters[agent.id] = agent
            note = agent.add_stress(20)
            msgs.append(render(Situation("plot_coup",
                                         {"mastermind": agent, "target": targ},
                                         data={"civ": trealm.civ_name})))
            if note and "mental break" in note:
                msgs.append(render(Situation("mental_break", {"subject": agent})))
        else:
            targ.is_alive = False
            targ.age_progress.is_alive = False
            msgs.append(render(Situation("plot_assassination", {"target": targ},
                                         data={"civ": trealm.civ_name})))
        return msgs

    def _discover(self, game, s, trealm, rng=_random) -> List[str]:
        """The scheme comes to light: the plotter is marked, the plotter's
        House is shamed, and a Secret of the attempt enters the economy."""
        msgs = []
        agent, targ = s.agent, s.target
        secret = Secret("scheme", agent.id,
                        f"{agent.name} schemed against {targ.name}",
                        SECRET_POTENCY)
        secret.holders.add(targ.id)
        agent.secrets.append(secret)
        modify_opinion(targ, agent, -40, "uncovered scheme")
        note = agent.add_stress(30)
        if note and "mental break" in note:
            msgs.append(render(Situation("mental_break", {"subject": agent})))
        arealm = self._realm_of(game, agent)
        if arealm is not None:
            record_scandal(game.legitimacy, arealm.civ_name,
                           SCHEME_TYPES[s.scheme_type]["scandal"], msgs)
        if (arealm is not None and arealm.civ_name == trealm.civ_name
                and rng.random() < EXECUTION_CHANCE):
            agent.is_alive = False
            agent.age_progress.is_alive = False
            msgs.append(render(Situation("plot_executed", {"mastermind": agent},
                                         data={"civ": trealm.civ_name})))
        else:
            msgs.append(render(Situation("plot_uncovered", {"target": targ},
                                         data={"civ": trealm.civ_name})))
        return msgs

    @staticmethod
    def _realm_of(game, char):
        for realm in (getattr(game, "realms", None) or {}).values():
            if any(c.id == char.id for c in realm.characters):
                return realm
        return None
