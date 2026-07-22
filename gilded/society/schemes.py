
"""Schemes: the intrigue economy's working end (spec 6.1, mission G9).

A scheme is an agent moving against a target: it advances each turn on
the agent's Intrigue, risks discovery each turn against the target
court's counter-intrigue, and resolves at threshold - success, or a
scandal. Ported from root schemes.py onto realms dicts and enterprise
lists; ruler deaths surface as ("ruler_dead", house) markers on
SchemeManager.pending_successions for the chassis to consume."""

import random as _random
from typing import List

from gilded.society.characters import Secret, modify_opinion
from gilded.society.event_engine import Situation, render
from gilded.society.ideology import record_scandal
from gilded.society.dispositions import expose_persona
from gilded.society.shares import (
    extort_shares,
    transfer_shares,
    house_stake,
    seize_enterprises,
)

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

    def __init__(self, agent, target, scheme_type: str, target_house: str):
        self.agent = agent
        self.target = target
        self.scheme_type = scheme_type
        self.target_house = target_house
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
    """Owns every live scheme; advanced once per turn by the chassis."""

    def __init__(self):
        self.schemes: List[Scheme] = []
        self.pending_successions: List = []   # ("ruler_dead", house) markers

    def start_scheme(self, agent, target, scheme_type: str, target_house: str) -> Scheme:
        s = Scheme(agent, target, scheme_type, target_house)
        self.schemes.append(s)
        return s

    def scheming(self, char) -> bool:
        return any(s.agent is char for s in self.schemes)

    def advance_all(self, realms, legitimacy, rng=_random) -> List[str]:
        """One turn of every scheme: prune the moot, advance the live,
        roll discovery, resolve at threshold."""
        msgs: List[str] = []
        for s in list(self.schemes):
            trealm = realms.get(s.target_house)
            if trealm is None or not s.agent.is_alive or not s.target.is_alive:
                self.schemes.remove(s)
                continue
            if s.scheme_type == "coup" and trealm.ruler is not s.target:
                self.schemes.remove(s)   # the throne already changed hands
                continue
            s.advance()
            defense = max((ch.get_effective_stat("intrigue")
                           for ch in trealm.court.positions.values()
                           if ch and ch.is_alive), default=0)
            if rng.random() < (SCHEME_TYPES[s.scheme_type]["risk"]
                               + defense * DEFENSE_SHIELD):
                self.schemes.remove(s)
                msgs.extend(self._discover(realms, legitimacy, s, trealm, rng))
                continue
            if s.progress < SCHEME_THRESHOLD:
                continue
            self.schemes.remove(s)
            if rng.random() < s.success_chance(defense):
                msgs.extend(self._succeed(s, trealm))
            else:
                msgs.extend(self._discover(realms, legitimacy, s, trealm, rng))
        return msgs

    def _succeed(self, s, trealm) -> List[str]:
        msgs = []
        agent, targ = s.agent, s.target
        if s.scheme_type == "coup":
            for pos, ch in trealm.court.positions.items():
                if ch and ch.id == agent.id:
                    trealm.court.positions[pos] = None
            trealm.ruler = agent
            trealm.court.ruler = agent
            if agent.id not in trealm.dynasty.all_characters:
                trealm.dynasty.all_characters[agent.id] = agent
            note = agent.add_stress(20)
            msgs.append(render(Situation("plot_coup",
                                         {"mastermind": agent, "target": targ},
                                         data={"civ": trealm.house_name})))
            if note and "mental break" in note:
                msgs.append(render(Situation("mental_break", {"subject": agent})))
        else:
            targ.is_alive = False
            targ.age_progress.is_alive = False
            if trealm.ruler is targ:
                self.pending_successions.append(("ruler_dead", s.target_house))
            msgs.append(render(Situation("plot_assassination", {"target": targ},
                                         data={"civ": trealm.house_name})))
        return msgs

    def _discover(self, realms, legitimacy, s, trealm, rng=_random) -> List[str]:
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
        arealm = self._realm_of(realms, agent)
        if arealm is not None:
            record_scandal(legitimacy, arealm.house_name,
                           SCHEME_TYPES[s.scheme_type]["scandal"], msgs)
        if (arealm is not None and arealm.house_name == trealm.house_name
                and rng.random() < EXECUTION_CHANCE):
            agent.is_alive = False
            agent.age_progress.is_alive = False
            if arealm.ruler is agent:
                self.pending_successions.append(("ruler_dead", arealm.house_name))
            msgs.append(render(Situation("plot_executed", {"mastermind": agent},
                                         data={"civ": trealm.house_name})))
        else:
            msgs.append(render(Situation("plot_uncovered", {"target": targ},
                                         data={"civ": trealm.house_name})))
        return msgs

    @staticmethod
    def _realm_of(realms, char):
        for realm in realms.values():
            if any(c.id == char.id for c in realm.characters):
                return realm
        return None


# --- Spending secrets (spec 6): the knife and the newspaper ----------------

EXPOSE_SEVERITY = 0.04      # scandal severity per point of secret potency
PRESS_WEAPON = 0.05         # Master of the Press: +5% severity per Intrigue point
EXPOSE_OPINION = -40
BLACKMAIL_SHARE_PCT = 10.0  # extorted from every enterprise stake
BLACKMAIL_REFUSE = 0.25     # chance the victim calls the bluff
BLACKMAIL_STRESS = 10       # base stress of turning the screw


def expose_secret(publisher, secret, subject, house, legitimacy, tide=None,
                  press_bonus=0) -> List[str]:
    """Feed a rival's secret to the tabloids (spec 6): the persona gap
    collapses in public, the subject's House takes a potency-scaled
    scandal - weaponized by the Master of the Press - and the spent
    secret is a secret no more. tide is accepted for the press wave's
    hooks; the scandal itself books to legitimacy."""
    if not secret.is_known_by(publisher.id) or secret.subject_id != subject.id:
        return []
    msgs = [f"EXPOSED: {secret.description}!"]
    expose_persona(subject, secret.potency)
    severity = secret.potency * EXPOSE_SEVERITY * (1.0 + press_bonus * PRESS_WEAPON)
    record_scandal(legitimacy, house, severity, msgs)
    modify_opinion(subject, publisher, EXPOSE_OPINION, "exposed in the press")
    note = subject.add_stress(30)
    if note and "mental break" in note:
        msgs.append(render(Situation("mental_break", {"subject": subject})))
    if secret in subject.secrets:
        subject.secrets.remove(secret)
    return msgs


def blackmail(agent, secret, victim, realm, enterprises, rng=_random,
              legitimacy=None, tide=None, press_bonus=0) -> List[str]:
    """Hold the secret over the victim (spec 6): extort shares quietly -
    or have the bluff called and be forced to publish everything."""
    if not secret.is_known_by(agent.id) or secret.subject_id != victim.id:
        return []
    if rng.random() < BLACKMAIL_REFUSE:
        msgs = [f"{victim.name} calls the bluff - the tabloids get everything"]
        msgs.extend(expose_secret(agent, secret, victim, realm.house_name,
                                  legitimacy if legitimacy is not None else {},
                                  tide, press_bonus))
        return msgs
    moved = extort_shares(enterprises, victim.id, agent.id, BLACKMAIL_SHARE_PCT)
    line = f"{agent.name} turns the screw on {victim.name}"
    if moved:
        line += f": {moved:.0f}% in shares change hands quietly"
    msgs = [line]
    modify_opinion(victim, agent, -30, "blackmailed")
    victim.add_stress(20)
    note = agent.add_stress(BLACKMAIL_STRESS + agent.check_stress_action("blackmail"))
    if note and "mental break" in note:
        msgs.append(render(Situation("mental_break", {"subject": agent})))
    return msgs


# --- Leverage verbs (spec 6): the machine as a weapon ----------------------

SABOTAGE_RISK = 0.15        # base discovery chance
SABOTAGE_SCANDAL = 2.0
SABOTAGE_POTENCY = 40
SWAY_BASE = 0.6
SWAY_OPINION = 15
SEDUCE_BASE = 0.4
AFFAIR_POTENCY = 35
COMPROMISE_BASE = 0.5
COMPROMISE_POTENCY = 20


def sabotage(agent, ent, province, victim_realm, rng=_random, tide=None,
             legitimacy=None, agent_house=None) -> List[str]:
    """A deniable 'accident' at a rival work (spec 6): the machine grinds
    as a weapon - it kills THEIR workers, seethes THEIR province, and the
    atrocity books to THEIR House (the tide does not ask who loosened the
    bolt). Discovery pins a sabotage Secret on the agent and, when the
    agent's House is known, the scandal comes home."""
    from gilded.society.labor import resolve_accident
    msgs = [f"A mysterious accident strikes the {province.name} works..."]
    msgs.extend(resolve_accident(ent, province, victim_realm, rng, tide))
    defense = max((ch.get_effective_stat("intrigue")
                   for ch in victim_realm.court.positions.values()
                   if ch and ch.is_alive), default=0)
    risk = max(0.02, min(0.5, SABOTAGE_RISK
                         - agent.get_effective_stat("intrigue") * 0.005
                         + defense * 0.005))
    if rng.random() < risk:
        secret = Secret("sabotage", agent.id,
                        f"{agent.name} engineered the {province.name} accident",
                        SABOTAGE_POTENCY)
        vic_ruler = getattr(victim_realm, "ruler", None)
        if vic_ruler is not None:
            secret.holders.add(vic_ruler.id)
            modify_opinion(vic_ruler, agent, -50, "sabotage uncovered")
        agent.secrets.append(secret)
        if legitimacy is not None and agent_house is not None:
            record_scandal(legitimacy, agent_house, SABOTAGE_SCANDAL, msgs)
        msgs.append(f"The {province.name} 'accident' is traced to {agent.name}!")
    return msgs


def sway(agent, target, rng=_random) -> List[str]:
    """Work on a person (spec 6/4.3): flattery, favors, salons. Success
    builds real opinion leverage; a clumsy approach costs a little."""
    chance = min(0.95, SWAY_BASE + agent.get_effective_stat("statecraft") * 0.01)
    if rng.random() < chance:
        modify_opinion(target, agent, SWAY_OPINION, "swayed")
        return [f"{agent.name} wins ground with {target.name}"]
    modify_opinion(target, agent, -5, "clumsy flattery")
    return [f"{target.name} sees through {agent.name}'s flattery"]


def seduce(agent, target, rng=_random) -> List[str]:
    """Charm as leverage (spec 6/4.3): success starts an affair - a
    mutual Secret in the persona gap, potent enough to spend."""
    disp = agent.dispositions
    charm = (max(0.0, -disp.get("magnetic_repellent", 0.0))
             + max(0.0, -disp.get("comely_plain", 0.0)))
    warmth = max(0.0, -target.dispositions.get("romantic_cold", 0.0))
    chance = min(0.95, SEDUCE_BASE + charm * 0.002 + warmth * 0.002)
    if rng.random() < chance:
        secret = Secret("affair", target.id,
                        f"{target.name} and {agent.name} are entangled in an affair",
                        AFFAIR_POTENCY)
        secret.holders.add(agent.id)
        target.secrets.append(secret)
        modify_opinion(target, agent, 25, "the affair")
        modify_opinion(agent, target, 25, "the affair")
        return [f"{agent.name} and {target.name} begin an affair - leverage in the gap"]
    modify_opinion(target, agent, -20, "rebuffed advance")
    return [f"{target.name} rebuffs {agent.name}"]


def compromise(agent, target, rng=_random, legitimacy=None,
               agent_house=None) -> List[str]:
    """Manufacture a Secret (spec 6): stage the photograph, forge the
    ledger. Success mints leverage; getting caught fabricating is a
    scandal of its own."""
    chance = min(0.95, COMPROMISE_BASE + agent.get_effective_stat("intrigue") * 0.01)
    if rng.random() < chance:
        secret = Secret("compromise", target.id,
                        f"{target.name} was compromised by {agent.name}'s design",
                        COMPROMISE_POTENCY)
        secret.holders.add(agent.id)
        target.secrets.append(secret)
        return [f"{agent.name} manufactures leverage on {target.name}"]
    msgs = [f"{target.name} catches {agent.name} fabricating evidence"]
    modify_opinion(target, agent, -40, "caught fabricating")
    if legitimacy is not None and agent_house is not None:
        record_scandal(legitimacy, agent_house, 1.0, msgs)
    return msgs


# --- Hostile takeover (spec 6): the bloodless kill -------------------------

TAKEOVER_THRESHOLD = 50.0   # average portfolio stake that flips the House
TAKEOVER_PRICE = 2.0        # gold per 1% of one enterprise
TAKEOVER_TRANCHE = 15.0     # max pct bought per enterprise, per seller, per turn


class Takeover:
    """The signature bloodless kill (spec 6): quietly buy a rival House's
    shares via its disloyal holders - siblings, widows, denied heirs -
    until you own their company out from under them. Past the threshold
    the House's enterprises re-register under the buyer: the House
    survives as characters, but it has lost its base. No shot fired."""

    def __init__(self, buyer, buyer_house: str, target_house: str):
        self.buyer = buyer
        self.buyer_house = buyer_house
        self.target_house = target_house
        self.complete = False

    def advance(self, realms, enterprises, rng=_random) -> List[str]:
        """One turn of quiet buying: approach every disloyal holder and
        take up to a tranche of each stake, gold changing hands at
        TAKEOVER_PRICE. Completes when the average stake clears the
        threshold."""
        from gilded.society.realm import disloyal_shareholders
        if self.complete:
            return []
        target_realm = realms.get(self.target_house)
        buyer_realm = realms.get(self.buyer_house)
        if target_realm is None or buyer_realm is None:
            return []
        msgs: List[str] = []
        target_ents = [e for e in enterprises if e.house == self.target_house]
        for seller in disloyal_shareholders(target_realm, enterprises):
            for ent in target_ents:
                want = min(TAKEOVER_TRANCHE, self.buyer.gold_reserve / TAKEOVER_PRICE)
                if want <= 0:
                    break
                moved = transfer_shares(ent, seller.id, self.buyer.id, want)
                if moved > 0:
                    cost = moved * TAKEOVER_PRICE
                    self.buyer.gold_reserve -= cost
                    seller.gold_reserve += cost
                    modify_opinion(seller, self.buyer, 5, "a generous buyer")
        stake = house_stake(target_ents, self.buyer.id)
        if stake > 0:
            msgs.append(f"{self.buyer.name} quietly holds {stake:.0f}% of "
                        f"House {self.target_house}")
        if stake > TAKEOVER_THRESHOLD:
            n = seize_enterprises(enterprises, self.target_house,
                                  self.buyer_house, buyer_realm)
            self.complete = True
            vic_ruler = getattr(target_realm, "ruler", None)
            if vic_ruler is not None:
                modify_opinion(vic_ruler, self.buyer, -80,
                               "bought the House out from under them")
            msgs.append(f"HOSTILE TAKEOVER: {self.buyer.name} owns House "
                        f"{self.target_house} - {n} enterprises "
                        f"change hands without a shot")
        return msgs


# --- Assassination conspiracy (spec 6): everyone fears it ------------------

CONSPIRACY_COST = 100.0        # hired men, staged accidents, anarchist patsies
CONSPIRACY_TURNS = 3           # turns of preparation before the attempt
CONSPIRACY_BETRAYAL = 0.08     # per co-conspirator, per turn
CONSPIRACY_SUCCESS = 0.7       # the attempt itself, once prepared
CONSPIRACY_MIN = 2             # no lone knives - it takes a conspiracy
NUCLEAR_SCANDAL = 5.0          # the nuclear scandal: legitimacy collapse
CLOSED_RANKS_OPINION = -60     # every House turns on the exposed mastermind


def start_conspiracy(mastermind, target, target_house, conspirators):
    """Assemble the conspiracy (spec 6): expensive, deniable, dreaded.
    Returns the Conspiracy, or None if the mastermind cannot pay or
    cannot find enough co-conspirators."""
    if len(conspirators) < CONSPIRACY_MIN:
        return None
    if mastermind.gold_reserve < CONSPIRACY_COST:
        return None
    mastermind.gold_reserve -= CONSPIRACY_COST
    return Conspiracy(mastermind, target, target_house, conspirators)


class Conspiracy:
    """Assassination as a conspiracy (spec 6): hired men, a staged
    accident, and co-conspirators who are each a betrayal risk every
    turn. Success is a quiet 'accident' nobody can pin; exposure is the
    nuclear scandal - legitimacy collapse, every House closing ranks,
    and a trial. Everyone fears it; almost no one dares it."""

    def __init__(self, mastermind, target, target_house, conspirators):
        self.mastermind = mastermind
        self.target = target
        self.target_house = target_house
        self.conspirators = list(conspirators)
        self.turns = 0
        self.done = False
        self.exposed = False

    def advance(self, realms, rng=_random, tide=None, legitimacy=None) -> List[str]:
        """One turn in the dark: every living co-conspirator may lose
        their nerve and talk; if the plot holds through preparation,
        the accident is staged."""
        if self.done or not self.target.is_alive:
            self.done = True
            return []
        for ch in self.conspirators:
            if ch.is_alive and rng.random() < CONSPIRACY_BETRAYAL:
                return self._expose(realms, ch, rng, tide, legitimacy)
        self.turns += 1
        if self.turns < CONSPIRACY_TURNS:
            return []
        if rng.random() < CONSPIRACY_SUCCESS:
            self.done = True
            self.target.is_alive = False
            self.target.age_progress.is_alive = False
            return [render(Situation("staged_accident", {"target": self.target},
                                     data={"civ": self.target_house}))]
        return self._expose(realms, None, rng, tide, legitimacy)

    def _expose(self, realms, traitor, rng=_random, tide=None,
                legitimacy=None) -> List[str]:
        """The nuclear scandal (spec 6): the conspiracy comes to light -
        legitimacy collapses, the tide books the atrocity, every House
        closes ranks against the mastermind, and the trial begins."""
        self.done = True
        self.exposed = True
        m = self.mastermind
        msgs: List[str] = []
        if traitor is not None:
            msgs.append(f"{traitor.name} loses their nerve and talks - "
                        f"the conspiracy is blown open")
        arealm = SchemeManager._realm_of(realms, m)
        house = arealm.house_name if arealm is not None else None
        if house is not None and legitimacy is not None:
            record_scandal(legitimacy, house, NUCLEAR_SCANDAL, msgs)
        if tide is not None:
            tide.record_atrocity("assassination", house=house)
        for realm in realms.values():
            ruler = getattr(realm, "ruler", None)
            if ruler is not None and ruler.is_alive and ruler.id != m.id:
                modify_opinion(ruler, m, CLOSED_RANKS_OPINION,
                               "conspiracy to murder")
        msgs.append(render(Situation("conspiracy_trial", {"mastermind": m},
                                     data={"civ": self.target_house})))
        note = m.add_stress(40)
        if note and "mental break" in note:
            msgs.append(render(Situation("mental_break", {"subject": m})))
        if rng.random() < EXECUTION_CHANCE:
            m.is_alive = False
            m.age_progress.is_alive = False
            msgs.append(render(Situation("plot_executed", {"mastermind": m},
                                         data={"civ": self.target_house})))
        return msgs