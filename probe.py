"""Probe: Stage 14B gate — pacts that bind, measured over a played century
(halt at turn 70, TURN_BUDGET) at seeds 7/42/61.

Checks, per seed:
  * 1..8 pacts standing at halt, <= 2 per House at every turn
  * zero betrayals (no House at war with a standing pact ally)
  * BOTH pickers probed by construction on a target each was willing to name
    first: with the pact formed the picker no longer names the target; with
    the pact removed it does. A picker that returns None for unrelated reasons
    proves nothing, so the willing-target premise is verified first.
  * every call to arms answered by the ally joining the war within
    CALL_TO_ARMS_DEADLINE turns, or a refusal logged naming ally + aggressor
  * 14A numbers re-asserted: wars declared / ended / active / endpeak / truces
"""
import re

from gilded import agenda, pacts
from gilded.ai import WEAKER, _strength
from gilded.chassis import GildedGame
from gilded.agenda import Goal


def _pact_between(game, a, b):
    for p in game.pacts:
        if {p.house_a, p.house_b} == {a, b}:
            return p
    return None


def _neighbors(game, h):
    out = set()
    for p in game.provinces_of(h):
        for n in p.neighbors:
            o = game.atlas.provinces[n].owner
            if o and o != h and o in game.houses:
                out.add(o)
    return out


def _probe_ai_picker(game):
    """Find a (h, target) where target was WILLING to be named — the unguarded
    picker names it — then prove the guard is what stops it. Returns a
    description of the probe, or None if no willing candidate exists."""
    from gilded import ai
    for h in sorted(game.houses):
        if game.houses[h].at_war_with:
            continue
        cands = []
        for c in sorted(_neighbors(game, h)):
            if c in game.houses[h].at_war_with:
                continue
            if game.houses[h].truces.get(c, 0) > game.turn:
                continue
            if _strength(game, c) >= WEAKER * _strength(game, h):
                continue
            cands.append(c)
        if not cands:
            continue
        target = cands[0]
        # premise: unguarded picker names this target
        had_pact = _pact_between(game, h, target) is not None
        if had_pact:
            game.pacts.remove(_pact_between(game, h, target))
        assert ai._weaker_neighbor(game, h) == target, \
            f"AI picker unwilling: names {ai._weaker_neighbor(game, h)!r} not {target}"
        # form the pact (retry on a different house if caps block)
        if pacts.form_pact(game, h, target) is None:
            continue
        assert ai._weaker_neighbor(game, h) != target, \
            f"AI picker still names ally {target} after pact"
        # leave the game in the no-pact state for the rest of the loop
        game.pacts.remove(_pact_between(game, h, target))
        return f"{h} -> {target}"
    return None


def _probe_conquest_picker(game):
    """Construct a Conquest goal aimed at a target the actor is NOT at war
    with, so the picker is willing to name it; prove the guard is what
    stops it. Returns a description, or None if no such target exists."""
    for h in sorted(game.houses):
        if game.houses[h].at_war_with:
            continue
        for target in sorted(game.houses):
            if target == h or target in game.houses[h].at_war_with:
                continue
            if game.houses[h].truces.get(target, 0) > game.turn:
                continue
            goal = Goal(family="Conquest", target=target,
                       opened_turn=game.turn, commit_turns=0, why="probe")
            # premise: the picker is willing to name this target
            got = agenda.goal_initiative(game, h, goal)
            if got != ("declare_war", {"target_house": target}):
                continue
            if pacts.form_pact(game, h, target) is None:
                continue
            assert agenda.goal_initiative(game, h, goal) is None, \
                f"Conquest picker still fires at ally {target} after pact"
            game.pacts.remove(_pact_between(game, h, target))
            return f"{h} -> {target}"
    return None


def _pledge_from(msg):
    m = re.match(r"House (\S+) calls House (\S+) to arms against House (\S+)", msg)
    return (m.group(2), m.group(3)) if m else None


def measure(seed):
    g = GildedGame(seed=seed)
    betrayals = 0
    max_per_house = 0
    seen = set()
    declared = 0
    active_peak = 0
    pledges = []
    resolved = []
    truces = 0
    probe_ai = None
    probe_conq = None
    for i in range(120):
        if g.game_over:
            break
        g.end_turn()
        for w in g.wars:
            key = (w.aggressor, w.defender, w.started_turn)
            if key not in seen:
                seen.add(key)
                declared += 1
        active_peak = max(active_peak, len(g.wars))
        for ev in g.events:
            t = ev.text
            m = _pledge_from(t)
            if m:
                pledges.append((g.turn, m[0], m[1]))
                continue
            m = re.match(r"House (\S+) refuses House (\S+)'s call against House (\S+)", t)
            if m:
                resolved.append((g.turn, m.group(1), m.group(3), "refusal"))
                continue
            m = re.match(r"House (\S+) answers the call to arms and joins House (\S+) against House (\S+)", t)
            if m:
                resolved.append((g.turn, m.group(1), m.group(3), "joined"))
                continue
            if "truce" in t.lower():
                truces += 1
        for p in g.pacts:
            a, b = p.house_a, p.house_b
            if a in g.houses and b in g.houses and b in g.houses[a].at_war_with:
                betrayals += 1
        counts = {}
        for p in g.pacts:
            counts[p.house_a] = counts.get(p.house_a, 0) + 1
            counts[p.house_b] = counts.get(p.house_b, 0) + 1
        max_per_house = max(max_per_house, max(counts.values(), default=0))
        if probe_ai is None:
            probe_ai = _probe_ai_picker(g)
        if probe_conq is None:
            probe_conq = _probe_conquest_picker(g)
    for turn, ally, aggr in pledges:
        hit = any(rally == ally and ragr == aggr and turn <= rturn
                 <= turn + pacts.CALL_TO_ARMS_DEADLINE
                 for rturn, rally, ragr, _how in resolved)
        if not hit:
            raise AssertionError(
                f"seed {seed}: call to arms (turn {turn}: {ally} vs {aggr}) "
                f"unanswered and unrefused within {pacts.CALL_TO_ARMS_DEADLINE} turns")
    return {
        "pacts_at_halt": len(g.pacts),
        "wars_declared": declared,
        "wars_ended": declared - len(g.wars),
        "active_at_halt": len(g.wars),
        "endpeak": active_peak,
        "truces": truces,
        "max_per_house": max_per_house,
        "betrayals": betrayals,
        "pledges": [(t, a, g2) for t, a, g2 in pledges],
        "probe_ai": probe_ai,
        "probe_conq": probe_conq,
        "final": [(p.house_a, p.house_b, p.formed_turn) for p in g.pacts],
    }


for seed in (7, 42, 61):
    r = measure(seed)
    print(f"seed {seed}:")
    print(f"   pacts@halt={r['pacts_at_halt']} max/house={r['max_per_house']} betrayals={r['betrayals']}")
    print(f"   14A: declared={r['wars_declared']} ended={r['wars_ended']} "
          f"active={r['active_at_halt']} endpeak={r['endpeak']} truces={r['truces']}")
    print(f"   pledges={r['pledges']}")
    print(f"   probe_ai={r['probe_ai']} probe_conq={r['probe_conq']}")
    print(f"   pacts={r['final']}")
    assert 1 <= r["pacts_at_halt"] <= 8, "pact count out of bounds"
    assert r["max_per_house"] <= 2, "per-house cap exceeded"
    assert r["betrayals"] == 0, "betrayal detected"
    assert r["probe_ai"] is not None, "AI picker not probed by construction"
    assert r["probe_conq"] is not None, "Conquest picker not probed by construction"
    # 14A re-asserted in the same century: war still happens and still ends
    assert r["wars_declared"] >= 1, "war stopped happening"
    assert r["active_at_halt"] == 0, "wars not ending"
print("\nALL SEEDS PASS")
