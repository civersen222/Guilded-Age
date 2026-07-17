"""Relationships that bite: rivals, grievances, plots, opinion-driven factions (Phase B3)."""

import random
from typing import List

from simulation import opinion_matrix, modify_opinion
from realms import _make_character, tick_loyalty
from dispositions import apply_drift
from event_engine import Situation, render

RIVAL_AT = -25
FRIEND_AT = 25
GRIEVANCE_CHANCE = 0.05
AMBITIOUS_GRIEVANCE_CHANCE = 0.15
PLOT_CHANCE = 0.06
FOREIGN_PLOT_CHANCE = 0.03
COURT_INTERVAL = 12
MAX_MESSAGES = 4

_last_rulers = {}


def opinion_of(a, b) -> int:
    return opinion_matrix.get((a.id, b.id), 0)


def get_relation(a, b) -> str:
    o = opinion_of(a, b)
    if o <= RIVAL_AT:
        return "rival"
    if o >= FRIEND_AT:
        return "friend"
    return "neutral"


def tick_relationships(game) -> List[str]:
    """Grievances, plots, and opinion-driven factions for every realm."""
    msgs: List[str] = []
    realms = getattr(game, "realms", None) or {}
    _fill_player_court(game, realms)
    msgs.extend(tick_loyalty(game))
    for civ_name, realm in realms.items():
        msgs.extend(_succession_grievances(civ_name, realm))
        msgs.extend(_grievances(realm))
        msgs.extend(_discover_secrets(realm))
        msgs.extend(_maybe_start_plot(game, civ_name, realm))
    msgs.extend(_advance_plots(game, realms))
    _factions_from_opinions(game)
    if len(msgs) > MAX_MESSAGES:
        msgs = random.sample(msgs, MAX_MESSAGES)
    return msgs


def _fill_player_court(game, realms):
    """The player's court gets the same staffing the AI realms get in character_ai."""
    pname = game.player_civ.name
    realm = realms.get(pname)
    if not realm:
        return
    realm.ruler = game.rulers.get(pname, realm.ruler)
    realm.court.ruler = realm.ruler
    if not realm.ruler.is_alive:
        # Safety net: the throne must never stay empty.
        kin = [c for c in realm.dynasty.all_characters.values() if c.is_alive and c.id != realm.ruler.id]
        adults = [c for c in kin if c.age >= 16]
        heir = max(adults, key=lambda c: c.age) if adults else (max(kin, key=lambda c: c.age) if kin else None)
        if heir is None:
            living = [c for c in realm.characters if c.is_alive and c.age >= 16]
            heir = max(living, key=lambda c: c.get_effective_stat("statecraft")) if living else None
        if heir is None:
            heir = _make_character(realm.civ_name, realm.ruler.base_stats, [], 20, 35)
            realm.characters.append(heir)
            game.characters.append(heir)
        for pos, ch in realm.court.positions.items():
            if ch and ch.id == heir.id:
                realm.court.positions[pos] = None
        realm.ruler = heir
        realm.court.ruler = heir
        game.rulers[pname] = heir
        if heir.id not in realm.dynasty.all_characters:
            realm.dynasty.all_characters[heir.id] = heir
    if game.state.turn % COURT_INTERVAL == 0:
        # The player's ruler holds court — the passive goodwill AI rulers get from feasts.
        for c in realm.characters:
            if c.is_alive and c.age >= 16 and c.id != realm.ruler.id:
                modify_opinion(c, realm.ruler, random.randint(2, 5), "holds court")
    for pos, ch in list(realm.court.positions.items()):
        if ch is not None and ch.is_alive:
            continue
        candidates = [c for c in realm.characters
                      if c.is_alive and c.age >= 16 and c.id != realm.ruler.id
                      and all(o is None or o.id != c.id for o in realm.court.positions.values())]
        pick = realm.court.get_best_candidate(candidates, pos)
        if pick is None:
            pick = _make_character(realm.civ_name, realm.ruler.base_stats, [], 18, 35)
            realm.characters.append(pick)
            game.characters.append(pick)
        realm.court.positions[pos] = None
        realm.court.appoint(pos, pick, game.state.turn)


def _succession_grievances(civ_name, realm) -> List[str]:
    """Passed-over kin resent the new ruler — the classic source of rivals."""
    msgs = []
    ruler = realm.ruler
    last = _last_rulers.get(civ_name)
    _last_rulers[civ_name] = ruler.id
    if last is None or last == ruler.id or not ruler.is_alive:
        return msgs
    for c in realm.dynasty.all_characters.values():
        if not c.is_alive or c.age < 16 or c.id == ruler.id:
            continue
        was_rival = get_relation(c, ruler) == "rival"
        modify_opinion(c, ruler, -random.randint(15, 30), "passed over")
        # Being passed over marks a person for life (spec 3.4 drift).
        for pk, amt in (("forgiving_vengeful", 12.0), ("ambitious_content", -8.0)):
            d = apply_drift(c, pk, amt, "passed over")
            if d:
                msgs.append(d)
        if not was_rival and get_relation(c, ruler) == "rival":
            msgs.append(f"{c.name} has become a rival of {ruler.name}")
    return msgs


def _grievances(realm) -> List[str]:
    msgs = []
    ruler = realm.ruler
    if not ruler.is_alive:
        return msgs
    for c in realm.characters:
        if not c.is_alive or c.age < 16 or c.id == ruler.id:
            continue
        ambitious = "Cunning" in c.traits or "Opportunistic" in c.traits or c.stress > 100
        chance = AMBITIOUS_GRIEVANCE_CHANCE if ambitious else GRIEVANCE_CHANCE
        if random.random() < chance:
            was_rival = get_relation(c, ruler) == "rival"
            modify_opinion(c, ruler, -random.randint(5, 12), "ambition")
            if not was_rival and get_relation(c, ruler) == "rival":
                msgs.append(f"{c.name} has become a rival of {ruler.name}")
    return msgs


def _discover_secrets(realm) -> List[str]:
    """Spec 3.5: courtiers sniff out the realm's secrets; discovery chance
    scales with the observer's Intrigue (1% per point per turn, cap 30%)."""
    msgs: List[str] = []
    observers = [c for c in realm.court.positions.values()
                 if c is not None and c.is_alive]
    ruler = realm.ruler
    if ruler is not None and ruler.is_alive and ruler not in observers:
        observers.append(ruler)
    subjects = list(observers)
    for c in realm.dynasty.all_characters.values():
        if c.is_alive and c not in subjects:
            subjects.append(c)
    for subject in subjects:
        for secret in subject.secrets:
            for obs in observers:
                if obs.id == subject.id or secret.is_known_by(obs.id):
                    continue
                chance = min(0.3, obs.get_effective_stat("intrigue") * 0.01)
                if random.random() < chance:
                    secret.holders.add(obs.id)
                    msgs.append(f"{obs.name} has uncovered a secret: "
                                f"{secret.description}")
    return msgs


def _maybe_start_plot(game, civ_name, realm) -> List[str]:
    msgs = []
    ruler = realm.ruler
    if not ruler.is_alive:
        return msgs
    pm = game.plot_manager
    masterminds = {p.mastermind for p in pm.plots}
    court_ids = {c.id for c in realm.court.positions.values() if c}
    for c in realm.characters:
        if not c.is_alive or c.age < 16 or c.id == ruler.id or c.id in masterminds:
            continue
        if get_relation(c, ruler) == "rival" and random.random() < PLOT_CHANCE:
            plot_type = "coup" if c.id in court_ids else "assassination"
            plot = pm.create_plot(f"{plot_type.title()} against {ruler.name}", c.id, ruler.id, plot_type)
            for ally in realm.characters:
                if ally.is_alive and ally.id not in (c.id, ruler.id) and get_relation(ally, ruler) == "rival":
                    plot.add_participant(ally.id)
            msgs.append(f"Whispers in {civ_name}: someone moves against {ruler.name}")
            break
    if ruler.id not in masterminds:
        targets = [r for n, r in game.rulers.items() if n != civ_name and r.is_alive and get_relation(ruler, r) == "rival"]
        if targets and random.random() < FOREIGN_PLOT_CHANCE:
            t = random.choice(targets)
            pm.create_plot(f"Assassination of {t.name}", ruler.id, t.id, "assassination")
            msgs.append(f"Agents of {civ_name} slip across the border...")
    return msgs


def _advance_plots(game, realms) -> List[str]:
    msgs = []
    pm = game.plot_manager
    chars = {}
    for realm in realms.values():
        for c in realm.characters:
            chars[c.id] = (c, realm)
    for n, r in game.rulers.items():
        if r.id not in chars and n in realms:
            chars[r.id] = (r, realms[n])
    for plot in list(pm.plots):
        m = chars.get(plot.mastermind)
        t = chars.get(plot.target)
        if not m or not t or not m[0].is_alive or not t[0].is_alive:
            pm.plots.remove(plot)
            continue
        mast, mrealm = m
        targ, trealm = t
        if game.rulers.get(trealm.civ_name) is not targ:
            pm.plots.remove(plot)
            continue
        plot.advance_plot(3 + mast.get_effective_stat("intrigue") // 2)
        if not plot.successful:
            continue
        pm.plots.remove(plot)
        defense = max((ch.get_effective_stat("intrigue") for ch in trealm.court.positions.values()
                       if ch and ch.is_alive), default=0)
        chance = plot.get_success_chance() * 0.5 + mast.get_effective_stat("intrigue") * 0.01 - defense * 0.01
        if random.random() < chance:
            if plot.plot_type == "coup":
                for pos, ch in trealm.court.positions.items():
                    if ch and ch.id == mast.id:
                        trealm.court.positions[pos] = None
                trealm.ruler = mast
                trealm.court.ruler = mast
                game.rulers[trealm.civ_name] = mast
                if mast.id not in trealm.dynasty.all_characters:
                    trealm.dynasty.all_characters[mast.id] = mast
                note = mast.add_stress(20)
                msgs.append(render(Situation("plot_coup", {"mastermind": mast, "target": targ},
                                             data={"civ": trealm.civ_name})))
                if note and "mental break" in note:
                    msgs.append(render(Situation("mental_break", {"subject": mast})))
            else:
                targ.is_alive = False
                targ.age_progress.is_alive = False
                msgs.append(render(Situation("plot_assassination", {"target": targ},
                                             data={"civ": trealm.civ_name})))
        else:
            modify_opinion(targ, mast, -40, "uncovered plot")
            note = mast.add_stress(30)
            if note and "mental break" in note:
                msgs.append(render(Situation("mental_break", {"subject": mast})))
            if random.random() < 0.3 and mrealm.civ_name == trealm.civ_name:
                mast.is_alive = False
                mast.age_progress.is_alive = False
                msgs.append(render(Situation("plot_executed", {"mastermind": mast},
                                             data={"civ": trealm.civ_name})))
            else:
                msgs.append(render(Situation("plot_uncovered", {"target": targ},
                                             data={"civ": trealm.civ_name})))
    return msgs


def _factions_from_opinions(game):
    """Faction influence follows how the realm feels about the player's ruler."""
    fm = getattr(game, "faction_manager", None)
    ruler = game.rulers.get(game.player_civ.name)
    if not fm or not getattr(fm, "factions", None) or not ruler:
        return
    vals = [v for (a, b), v in opinion_matrix.items() if b == ruler.id]
    avg = sum(vals) / len(vals) if vals else 0.0
    if avg <= -10 and fm.factions["nobles"].influence < 80:
        fm.adjust_influence("nobles", 2)
        fm.adjust_influence("popular", -1)
    elif avg >= 10 and fm.factions["popular"].influence < 80:
        fm.adjust_influence("popular", 1)
        fm.adjust_influence("nobles", -1)
