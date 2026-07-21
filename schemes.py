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
from dispositions import expose_persona
from shares import extort_shares, transfer_shares, house_stake, seize_enterprises

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


# --- Spending secrets (M63, spec 6): the knife and the newspaper -----------

EXPOSE_SEVERITY = 0.04      # scandal severity per point of secret potency
PRESS_WEAPON = 0.05         # Master of the Press: +5% severity per Intrigue point
EXPOSE_OPINION = -40
BLACKMAIL_SHARE_PCT = 10.0  # extorted from every enterprise stake
BLACKMAIL_REFUSE = 0.25     # chance the victim calls the bluff
BLACKMAIL_STRESS = 10       # base stress of turning the screw


def expose_secret(game, publisher, secret, subject, house, press_bonus=0) -> List[str]:
    """Feed a rival's secret to the tabloids (spec 6): the persona gap
    collapses in public, the subject's House takes a potency-scaled
    scandal - weaponized by the Master of the Press - and the spent
    secret is a secret no more."""
    if not secret.is_known_by(publisher.id) or secret.subject_id != subject.id:
        return []
    msgs = [f"📰 EXPOSED: {secret.description}!"]
    expose_persona(subject, secret.potency)
    severity = secret.potency * EXPOSE_SEVERITY * (1.0 + press_bonus * PRESS_WEAPON)
    record_scandal(game.legitimacy, house, severity, msgs)
    modify_opinion(subject, publisher, EXPOSE_OPINION, "exposed in the press")
    note = subject.add_stress(30)
    if note and "mental break" in note:
        msgs.append(render(Situation("mental_break", {"subject": subject})))
    if secret in subject.secrets:
        subject.secrets.remove(secret)
    return msgs


def blackmail(game, agent, secret, victim, realm, house, press_bonus=0,
              rng=_random) -> List[str]:
    """Hold the secret over the victim (spec 6): extort shares quietly -
    or have the bluff called and be forced to publish everything."""
    if not secret.is_known_by(agent.id) or secret.subject_id != victim.id:
        return []
    if rng.random() < BLACKMAIL_REFUSE:
        msgs = [f"{victim.name} calls the bluff - the tabloids get everything"]
        msgs.extend(expose_secret(game, agent, secret, victim, house, press_bonus))
        return msgs
    moved = extort_shares(realm, victim.id, agent.id, BLACKMAIL_SHARE_PCT)
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


# --- Leverage verbs (M64, spec 6): the machine as a weapon -----------------

SABOTAGE_RISK = 0.15        # base discovery chance
SABOTAGE_SCANDAL = 2.0
SABOTAGE_POTENCY = 40
SWAY_BASE = 0.6
SWAY_OPINION = 15
SEDUCE_BASE = 0.4
AFFAIR_POTENCY = 35
COMPROMISE_BASE = 0.5
COMPROMISE_POTENCY = 20


def sabotage(game, agent, city, victim_realm, rng=_random, tide=None) -> List[str]:
    """A deniable 'accident' at a rival work (spec 6): the machine grinds
    as a weapon - it kills THEIR workers, seethes THEIR city, and the
    atrocity books to THEIR House (the tide does not ask who loosened the
    bolt). Discovery pins a sabotage Secret on the agent and the scandal
    comes home."""
    from labor import resolve_accident
    msgs = [f"A mysterious accident strikes the {city.name} works..."]
    msgs.extend(resolve_accident(city, victim_realm, rng, tide))
    defense = max((ch.get_effective_stat("intrigue")
                   for ch in victim_realm.court.positions.values()
                   if ch and ch.is_alive), default=0)
    risk = max(0.02, min(0.5, SABOTAGE_RISK
                         - agent.get_effective_stat("intrigue") * 0.005
                         + defense * 0.005))
    if rng.random() < risk:
        secret = Secret("sabotage", agent.id,
                        f"{agent.name} engineered the {city.name} accident",
                        SABOTAGE_POTENCY)
        vic_ruler = getattr(victim_realm, "ruler", None)
        if vic_ruler is not None:
            secret.holders.add(vic_ruler.id)
            modify_opinion(vic_ruler, agent, -50, "sabotage uncovered")
        agent.secrets.append(secret)
        arealm = SchemeManager._realm_of(game, agent)
        if arealm is not None:
            record_scandal(game.legitimacy, arealm.civ_name,
                           SABOTAGE_SCANDAL, msgs)
        msgs.append(f"The {city.name} 'accident' is traced to {agent.name}!")
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


def compromise(game, agent, target, rng=_random) -> List[str]:
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
    arealm = SchemeManager._realm_of(game, agent)
    if arealm is not None:
        record_scandal(game.legitimacy, arealm.civ_name, 1.0, msgs)
    return msgs


# --- Hostile takeover (M65, spec 6): the bloodless kill --------------------

TAKEOVER_THRESHOLD = 50.0   # average portfolio stake that flips the House
TAKEOVER_PRICE = 2.0        # gold per 1% of one enterprise
TAKEOVER_TRANCHE = 15.0     # max pct bought per enterprise, per seller, per turn


class Takeover:
    """The signature bloodless kill (spec 6): quietly buy a rival House's
    shares via its disloyal holders - siblings, widows, denied heirs -
    until you own their company out from under them. Past the threshold
    the House's enterprises re-register under the buyer: the House
    survives as characters, but it has lost its base. No shot fired."""

    def __init__(self, buyer, buyer_realm, target_realm):
        self.buyer = buyer
        self.buyer_realm = buyer_realm
        self.target_realm = target_realm
        self.complete = False

    def advance(self) -> List[str]:
        """One turn of quiet buying: approach every disloyal holder and
        take up to a tranche of each stake, gold changing hands at
        TAKEOVER_PRICE. Completes when the average stake clears the
        threshold."""
        from realms import disloyal_shareholders
        if self.complete:
            return []
        msgs: List[str] = []
        for seller in disloyal_shareholders(self.target_realm):
            for ent in self.target_realm.enterprises:
                want = min(TAKEOVER_TRANCHE, self.buyer.gold_reserve / TAKEOVER_PRICE)
                if want <= 0:
                    break
                moved = transfer_shares(ent, seller.id, self.buyer.id, want)
                if moved > 0:
                    cost = moved * TAKEOVER_PRICE
                    self.buyer.gold_reserve -= cost
                    seller.gold_reserve += cost
                    modify_opinion(seller, self.buyer, 5, "a generous buyer")
        stake = house_stake(self.target_realm, self.buyer.id)
        if stake > 0:
            msgs.append(f"{self.buyer.name} quietly holds {stake:.0f}% of "
                        f"House {self.target_realm.civ_name}")
        if stake > TAKEOVER_THRESHOLD:
            n = seize_enterprises(self.target_realm, self.buyer_realm)
            self.complete = True
            vic_ruler = getattr(self.target_realm, "ruler", None)
            if vic_ruler is not None:
                modify_opinion(vic_ruler, self.buyer, -80,
                               "bought the House out from under them")
            msgs.append(f"HOSTILE TAKEOVER: {self.buyer.name} owns House "
                        f"{self.target_realm.civ_name} - {n} enterprises "
                        f"change hands without a shot")
        return msgs
