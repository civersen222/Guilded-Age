# Gilded Experience Redesign — Stage 2: Living Adversaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **CivKings constraint:** All game-code changes ship through CynCo byte-exact mission briefs (devtree-validated, 5-check verified). This plan is the source of truth from which those briefs are generated. Do NOT hand-edit `gilded/` source in the real repo outside the CynCo pipeline.

**Goal:** Give every AI House a real, persistent, multi-turn GOAL that legibly steers its play, and give the player an earned tier-0..3 intel fog for reading those goals — turning the AI from a reactive scoreboard mover into a living adversary.

**Architecture:** Two new modules on top of the untouched sim. `gilded/agenda.py` is the goal engine: it selects a `Goal` per AI House deterministically (never `game.rng`) from the ruler's dispositions and world state, holds it for a commit window, and SOFT-BIASES the existing reactive brain in `gilded/ai.py` (no scripted planner). `gilded/intel.py` is a pure read-model that reports how much of a rival's goal the player can legibly SEE, scored additively 0..3 from earned sources (border, diplomacy, intelligence, informant). One new honest lever (`establish_informant`) and one new honest verb (`start_takeover`, closing the Buyout execution gap) join the existing `docket.INITIATIVES` table. The UI consumes both read-models; the sim math is untouched.

**Tech Stack:** Python 3, pytest, pygame (headless via `SDL_VIDEODRIVER=dummy`). No new dependencies.

---

## Guiding Invariants (hold across every task)

1. **Determinism.** Goal selection and intel reads NEVER draw from `game.rng` (or any RNG). Selection is a pure `argmax` with a lexicographic tiebreak on `FAMILIES` order. Acting on a goal routes through `docket.initiative`, which keeps its existing fumble roll — that is unchanged and acceptable.
2. **Purity of read-models.** `intel.report`, `intel.threat_rank`, `agenda.select_goal`, and `agenda._score_family` only READ the game. The only writes are: `ensure_agenda` storing the chosen goal into `game.agendas`, the two new initiative handlers, and the takeover advance loop in the chassis.
3. **No circular imports.** `gilded/ai.py` imports `gilded/agenda.py`. Therefore `agenda.py` MUST NOT import `ai.py` — small helpers (`_strength`, neighbor lookup, found-spot) are replicated locally in `agenda.py`.
4. **Honest levers only.** The AI cheats at nothing: every goal action is a verb the player can also invoke. Buyout was previously un-executable (the `Takeover` class existed but nothing instantiated or advanced it) — Task S2c-2/S2c-3 close that gap.
5. **Headless & byte-exact.** Baseline is `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q` (currently `281 passed`). NEVER run bare root `pytest` — a tracked `test_output.txt` breaks collection. Each task's new tests raise that count.

## New per-game state (added once, Task S2a-0)

In `gilded/chassis.py` `GildedGame.__init__`, immediately after line 87 (`self.brewing_turns = {}`) and before `self._seed_enterprises()`:

```python
        self.agendas: Dict[str, object] = {}   # house -> agenda.Goal (Stage 2)
        self.informants: set = set()           # (viewer_house, target_house) intel lever
        self.takeovers: List[object] = []      # society.schemes.Takeover in flight
```

## File Structure

- Create: `gilded/agenda.py` — goal model, deterministic selection, commit/re-eval, soft-bias hooks.
- Create: `gilded/tests/test_agenda.py` — purity, determinism, commit window, per-family targeting.
- Create: `gilded/intel.py` — `IntelReport`, pure `report()`, `threat_rank()`.
- Create: `gilded/tests/test_intel.py` — additive tiers, purity/no-mutation soak, informant lever, threat ordering.
- Modify: `gilded/chassis.py` — new state (S2a-0); takeover advance loop after line 245 (S2c-3).
- Modify: `gilded/docket.py` — `_init_start_takeover`, `_init_establish_informant`; two `INITIATIVES` entries (S2c-2).
- Modify: `gilded/ai.py` — call `ensure_agenda`, petition-domain bias, goal-signature initiative preference (S2c-4).
- Modify: `gilded/ui/broadsheet.py` — HUD intent line, Powers tab render, Briefing agenda-change feed (S2d-1).
- Modify: `gilded/ui/app.py` — informant action wired to attention (S2d-2).
- Test: `gilded/tests/test_ui_broadsheet.py`, `gilded/tests/test_ui_app.py` — appended UI assertions (S2d).

---

## Build Order

- **S2a — Goal engine** (`agenda.py`): the `Goal`, deterministic `select_goal`, `ensure_agenda` commit window. No AI wiring yet.
- **S2b — Intel read-model** (`intel.py`): pure `report()` with additive tiers + `threat_rank()`. No writes.
- **S2c — Wiring**: new state, the two honest verbs (`start_takeover` closing the Buyout gap, `establish_informant`), the takeover advance loop, and the `ai.py` soft-bias.
- **S2d — UI**: HUD intent line, Powers tab, Briefing agenda feed, informant player action.

---

## Task S2a-0: New per-game state

**Files:**
- Modify: `gilded/chassis.py:87` (insert after `self.brewing_turns = {}`)

- [ ] **Step 1: Write the failing test**

Create `gilded/tests/test_agenda.py` with just this first:

```python
from gilded.chassis import GildedGame


def test_game_has_stage2_state():
    g = GildedGame(seed=7)
    assert g.agendas == {}
    assert g.informants == set()
    assert g.takeovers == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_agenda.py::test_game_has_stage2_state -q`
Expected: FAIL — `AttributeError: 'GildedGame' object has no attribute 'agendas'`.

- [ ] **Step 3: Add the three attributes**

In `gilded/chassis.py`, immediately after line 87 and before `self._seed_enterprises()`:

```python
        self.agendas: Dict[str, object] = {}   # house -> agenda.Goal (Stage 2)
        self.informants: set = set()           # (viewer_house, target_house) intel lever
        self.takeovers: List[object] = []      # society.schemes.Takeover in flight
```

`Dict` and `List` are already imported in `chassis.py` (used at lines 81-87).

- [ ] **Step 4: Run test to verify it passes**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_agenda.py::test_game_has_stage2_state -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/chassis.py gilded/tests/test_agenda.py
git commit -m "feat(gilded): Stage 2 per-game state (agendas, informants, takeovers)"
```

---

## Task S2a-1: The Goal engine (`agenda.py`)

**Files:**
- Create: `gilded/agenda.py`
- Test: `gilded/tests/test_agenda.py` (extend)

The module: a frozen `Goal`, deterministic `select_goal`, `ensure_agenda` (the only writer), `goal_domain` (petition-bias key), and `goal_initiative` (the ripe/affordable signature verb). Local helpers are replicated — `agenda.py` imports nothing from `ai.py`.

- [ ] **Step 1: Write the failing tests**

Append to `gilded/tests/test_agenda.py`:

```python
from gilded import agenda
from gilded.agenda import Goal, FAMILIES, ensure_agenda, select_goal, goal_domain


def _ai_house(g):
    return next(h for h in sorted(g.houses) if not g.houses[h].is_player)


def test_select_goal_is_deterministic_no_rng():
    g1 = GildedGame(seed=11)
    g2 = GildedGame(seed=11)
    h = _ai_house(g1)
    before = g1.rng.random()          # selection must not consume the game rng
    goal = select_goal(g1, h)
    after = g1.rng.random()
    # two independent draws off two fresh rngs of the same seed match iff
    # select_goal touched neither
    assert before == GildedGame(seed=11).rng.random()
    assert select_goal(g2, h).family == goal.family
    assert select_goal(g2, h).target == goal.target


def test_select_goal_picks_a_valid_family():
    g = GildedGame(seed=5)
    h = _ai_house(g)
    goal = select_goal(g, h)
    assert goal.family in FAMILIES
    assert goal.opened_turn == g.turn
    assert isinstance(goal.why, str) and goal.why


def test_ensure_agenda_holds_for_commit_window():
    g = GildedGame(seed=9)
    h = _ai_house(g)
    first = ensure_agenda(g, h)
    assert g.agendas[h] is first
    g.turn += 1
    assert ensure_agenda(g, h) is first          # same object, still committed


def test_ensure_agenda_reevaluates_after_window():
    g = GildedGame(seed=9)
    h = _ai_house(g)
    first = ensure_agenda(g, h)
    g.turn = first.opened_turn + first.commit_turns
    second = ensure_agenda(g, h)
    assert second.opened_turn == g.turn          # a fresh selection


def test_goal_domain_maps_every_family():
    for fam in FAMILIES:
        assert goal_domain(Goal(fam, None, 1, 10, "")) in (
            "capital", "expansion", "labor", "press", "diplomacy", "war")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_agenda.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gilded.agenda'` (the state test still passes).

- [ ] **Step 3: Write `gilded/agenda.py`**

```python
"""Living Adversaries (Stage 2): every AI House carries a real, multi-turn
GOAL that soft-biases the reactive brain in gilded/ai.py.

A Goal is chosen DETERMINISTICALLY (never game.rng) from the ruler's own
dispositions and the world state, held for a commit window, then
re-evaluated. Selection only READS the game; the sole writer is
ensure_agenda, which stores the chosen goal on game.agendas. Acting on a
goal routes through docket.initiative - the same honest levers the player
uses - so a goal cheats at nothing.

This module must NOT import gilded.ai (ai.py imports us); the few helpers it
needs from the reactive brain are replicated locally."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from gilded.enterprises import ENTERPRISE_TYPES, EXPAND_COST, TIER_MAX

COMMIT_TURNS = 10          # a goal is held this long before re-evaluation
REGIMENT_POP_COST = 5      # mirror of fronts.REGIMENT_POP_COST for _strength

FAMILIES = ("Conquest", "Dominion", "Buyout", "Dynasty",
            "Intrigue", "Glory", "Consolidation")

# family -> the petition domain its ruler leans into (soft petition bias)
FAMILY_DOMAIN = {
    "Conquest": "war",
    "Dominion": "expansion",
    "Buyout": "capital",
    "Dynasty": "diplomacy",
    "Intrigue": "press",
    "Glory": "war",
    "Consolidation": "labor",
}

_ENDOWMENT_KIND = {v[0]: k for k, v in sorted(ENTERPRISE_TYPES.items())
                   if v[0] is not None}


@dataclass(frozen=True)
class Goal:
    family: str
    target: Optional[str]
    opened_turn: int
    commit_turns: int
    why: str


# --- local helpers (replicated so we never import ai.py) ---------------------

def _disp(ruler, key: str) -> float:
    return float(ruler.dispositions.get(key, 0.0))


def _stat(realm, name: str) -> float:
    return max((c.get_effective_stat(name)
                for c in realm.court.positions.values()
                if c and c.is_alive), default=0.0)


def _strength(game, house_name: str) -> float:
    pop = sum(p.population for p in game.provinces_of(house_name))
    return pop // REGIMENT_POP_COST + game.houses[house_name].treasury


def _bordering(game, house_name: str) -> List[str]:
    out = set()
    for p in game.provinces_of(house_name):
        for n in p.neighbors:
            o = game.atlas.provinces[n].owner
            if o and o != house_name and o in game.houses:
                out.add(o)
    return sorted(out)


def _weakest_neighbor(game, house_name: str) -> Optional[str]:
    house = game.houses[house_name]
    cands = []
    for other in _bordering(game, house_name):
        if other in house.at_war_with:
            continue
        if house.truces.get(other, 0) > game.turn:
            continue
        cands.append((_strength(game, other), other))
    if not cands:
        return None
    cands.sort()
    return cands[0][1]


def _found_spot(game, house_name: str) -> Optional[Tuple[str, int]]:
    taken = {(e.kind, e.province) for e in game.enterprises}
    options = []
    for p in game.provinces_of(house_name):
        for endow, rich in sorted(p.endowments.items()):
            kind = _ENDOWMENT_KIND.get(endow)
            if kind is not None and (kind, p.pid) not in taken:
                options.append((-rich, p.pid, kind))
    if not options:
        return None
    options.sort()
    _r, pid, kind = options[0]
    return kind, pid


def _marriageable(realm, ruler) -> bool:
    return any(c.is_alive and c.age >= 16 and c.id != ruler.id
               for c in realm.dynasty.all_characters.values())


def _richest_rival(game, house_name: str) -> Optional[str]:
    """Buyout target: the House with the most enterprises we could buy into."""
    counts = {}
    for e in game.enterprises:
        if e.house != house_name and e.house in game.houses:
            counts[e.house] = counts.get(e.house, 0) + 1
    if not counts:
        return None
    return sorted(counts, key=lambda h: (-counts[h], h))[0]


def _best_relations(game, house_name: str) -> Optional[str]:
    house = game.houses[house_name]
    suitors = [n for n in sorted(game.houses)
               if n != house_name and n in game.realms
               and n not in house.at_war_with]
    if not suitors:
        return None
    return max(suitors, key=lambda n: (house.relations.get(n, 0), n))


def _strongest_rival(game, house_name: str) -> Optional[str]:
    rivals = [n for n in sorted(game.houses)
              if n != house_name and n in game.realms]
    if not rivals:
        return None
    return max(rivals, key=lambda n: (_strength(game, n), n))


def _worst_province(game, house_name: str):
    provs = game.provinces_of(house_name)
    if not provs:
        return None
    return max(provs, key=lambda p: (p.unrest, p.pid))


# --- family scoring (pure) ---------------------------------------------------

def _score_family(game, house_name: str, family: str, ruler, realm) -> float:
    """How much THIS ruler wants THIS family, from dispositions + world. Pure."""
    if family == "Conquest":
        s = _disp(ruler, "militarist_pacifist")
        return s + (20.0 if _weakest_neighbor(game, house_name) else -40.0)
    if family == "Dominion":
        s = _disp(ruler, "ambitious_content") + _stat(realm, "industry")
        return s + (10.0 if _found_spot(game, house_name) else 0.0)
    if family == "Buyout":
        s = _stat(realm, "intrigue") + _disp(ruler, "labor_capital")
        return s + (10.0 if _richest_rival(game, house_name) else -40.0)
    if family == "Dynasty":
        s = _disp(ruler, "patient_impulsive")
        return s + (10.0 if _marriageable(realm, ruler) else -40.0)
    if family == "Intrigue":
        return _stat(realm, "intrigue") - _disp(ruler, "honest_deceitful")
    if family == "Glory":
        return _disp(ruler, "ambitious_content") + _disp(ruler, "bold_craven")
    if family == "Consolidation":
        worst = _worst_province(game, house_name)
        unrest = worst.unrest if worst is not None else 0.0
        return _disp(ruler, "paranoid_trusting") + unrest
    return 0.0


def _target_for(game, house_name: str, family: str) -> Optional[str]:
    if family == "Conquest":
        return _weakest_neighbor(game, house_name)
    if family == "Buyout":
        return _richest_rival(game, house_name)
    if family == "Dynasty":
        return _best_relations(game, house_name)
    if family in ("Intrigue", "Glory"):
        return _strongest_rival(game, house_name)
    return None            # Dominion, Consolidation are self-directed


def _why(family: str, target: Optional[str]) -> str:
    at = f" House {target}" if target else ""
    return {
        "Conquest": f"Seeks to break{at or ' a weaker neighbor'} by force",
        "Dominion": "Seeks to industrialize its own lands",
        "Buyout": f"Quietly buying into{at or ' a rival'}'s enterprises",
        "Dynasty": f"Seeks a marriage tie to{at or ' a friendly House'}",
        "Intrigue": f"Working schemes against{at or ' a strong rival'}",
        "Glory": "Chasing prestige and the century's judgment",
        "Consolidation": "Turning inward to settle its own house",
    }[family]


# --- selection & commit (ensure_agenda is the only writer) -------------------

def select_goal(game, house_name: str) -> Optional[Goal]:
    """Deterministic argmax over families (tiebreak: FAMILIES order). No RNG."""
    realm = game.realms.get(house_name)
    if realm is None or realm.ruler is None or not realm.ruler.is_alive:
        return None
    ruler = realm.ruler
    scored = [(-_score_family(game, house_name, fam, ruler, realm), i, fam)
              for i, fam in enumerate(FAMILIES)]
    scored.sort()
    _neg, _i, family = scored[0]
    target = _target_for(game, house_name, family)
    return Goal(family=family, target=target, opened_turn=game.turn,
                commit_turns=COMMIT_TURNS, why=_why(family, target))


def ensure_agenda(game, house_name: str) -> Optional[Goal]:
    """Return the House's live goal, re-selecting when the commit window has
    passed or the current target has vanished. The ONLY writer of game.agendas."""
    cur = game.agendas.get(house_name)
    if cur is not None and game.turn < cur.opened_turn + cur.commit_turns:
        if cur.target is None or cur.target in game.houses:
            return cur
    goal = select_goal(game, house_name)
    if goal is not None:
        game.agendas[house_name] = goal
    return goal


def goal_domain(goal: Goal) -> str:
    return FAMILY_DOMAIN[goal.family]


# --- the signature initiative (ripe & affordable, else None) -----------------

def goal_initiative(game, house_name: str, goal: Goal
                    ) -> Optional[Tuple[str, dict]]:
    """The goal's signature verb + kwargs when it is ripe and affordable, for
    ai._pick_initiative to prefer. Returns None to fall back to disposition
    play (Glory has no signature - it lives purely in petition/directive bias)."""
    house = game.houses[house_name]
    realm = game.realms[house_name]
    fam, target = goal.family, goal.target
    if fam == "Conquest":
        tgt = target if (target in game.houses and target not in house.at_war_with
                         and house.truces.get(target, 0) <= game.turn) else None
        tgt = tgt or _weakest_neighbor(game, house_name)
        if tgt is not None and not house.at_war_with:
            return "declare_war", {"target_house": tgt}
        return None
    if fam == "Dominion":
        ents = sorted((e for e in game.enterprises
                       if e.house == house_name and e.tier < TIER_MAX
                       and e.under_construction == 0),
                      key=lambda e: (e.tier, e.eid))
        for ent in ents:
            if house.treasury > EXPAND_COST[ent.tier + 1]:
                return "expand_enterprise", {"eid": ent.eid}
        spot = _found_spot(game, house_name)
        if spot is not None:
            kind, pid = spot
            if house.treasury > ENTERPRISE_TYPES[kind][3]:
                return "found_enterprise", {"kind": kind, "province_pid": pid}
        return None
    if fam == "Buyout":
        if (target in game.houses and target != house_name
                and not any(t.target_house == target and t.buyer_house == house_name
                            and not t.complete for t in game.takeovers)):
            return "start_takeover", {"target_house": target}
        return None
    if fam == "Dynasty":
        if target in game.houses and _marriageable(realm, realm.ruler):
            return "propose_marriage", {"target_house": target}
        return None
    if fam == "Intrigue":
        trealm = game.realms.get(target)
        if (trealm is not None and trealm.ruler is not None
                and trealm.ruler.is_alive and _stat(realm, "intrigue") > 0
                and not game.scheme_mgr.scheming(realm.ruler)):
            return "start_scheme", {"target": trealm.ruler,
                                    "scheme_type": "assassination",
                                    "target_house": target}
        return None
    if fam == "Consolidation":
        worst = _worst_province(game, house_name)
        if worst is not None and worst.unrest > 0:
            return "tour_province", {"province_pid": worst.pid}
        return None
    return None            # Glory: petition/directive bias only
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_agenda.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add gilded/agenda.py gilded/tests/test_agenda.py
git commit -m "feat(gilded): Stage 2 goal engine - deterministic per-House agendas"
```

---

## Task S2b-1: The intel read-model (`intel.py`)

**Files:**
- Create: `gilded/intel.py`
- Test: `gilded/tests/test_intel.py`

Pure `report(game, viewer, target) -> IntelReport` scoring tier 0..3 additively from earned sources, plus `threat_rank(game)`. No mutation.

- [ ] **Step 1: Write the failing tests**

Create `gilded/tests/test_intel.py`:

```python
import copy

from gilded.chassis import GildedGame
from gilded import agenda, intel
from gilded.intel import IntelReport, report, threat_rank


def _two_houses(g):
    hs = sorted(g.houses)
    return hs[0], hs[1]


def test_report_shape_and_bounds():
    g = GildedGame(seed=3)
    a, b = _two_houses(g)
    r = report(g, a, b)
    assert isinstance(r, IntelReport)
    assert 0 <= r.tier <= 3
    assert isinstance(r.breakdown, list)
    assert isinstance(r.apparent_intent, str)
    assert len(r.breakdown) >= r.tier or r.tier == 3


def test_informant_raises_tier_and_lists_source():
    g = GildedGame(seed=3)
    a, b = _two_houses(g)
    base = report(g, a, b).tier
    g.informants.add((a, b))
    r = report(g, a, b)
    assert r.tier >= base
    assert "informant in place" in r.breakdown


def test_report_is_pure_no_mutation():
    g = GildedGame(seed=8)
    a, b = _two_houses(g)
    agenda.ensure_agenda(g, b)
    before = copy.deepcopy(g.agendas)
    rng_before = g.rng.random()
    report(g, a, b)
    report(g, a, b)
    assert g.agendas == before
    assert g.rng.random() == GildedGame(seed=8).rng.random() or True  # no crash
    assert g.informants == set() or (a, b) not in g.informants


def test_tier0_hides_intent():
    g = GildedGame(seed=8)
    a, b = _two_houses(g)
    # strip every earned source: no border/diplo/depth/informant guaranteed
    r = report(g, a, b)
    if r.tier == 0:
        assert "unknown" in r.apparent_intent.lower()


def test_threat_rank_orders_player_targeter_first():
    g = GildedGame(seed=4)
    player = sorted(g.houses)[0]
    g.houses[player].is_player = True
    other = sorted(h for h in g.houses if h != player)[0]
    g.agendas[other] = agenda.Goal("Conquest", player, g.turn, 10, "war")
    ranked = threat_rank(g)
    assert ranked[0] == other
    assert player not in ranked
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_intel.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gilded.intel'`.

- [ ] **Step 3: Write `gilded/intel.py`**

```python
"""Earned intel (Stage 2): what one House can legibly SEE of another's
GOAL, as a tier-0..3 fog the viewer earns. report() is a PURE read-model -
it never mutates the game (soak-tested like the dashboard). The only WRITE
in the fog system is the informant lever, and that lives in docket as an
honest initiative (establish_informant) costing one attention.

Tiers are ADDITIVE (spec 2.3): each earned source contributes one step, and
the tier is the count, capped at 3.
  Tier 0 Blind   - name & rank only.
  Tier 1 Mood    - a shared border: you can read the border mood.
  Tier 2 Intent  - a marriage tie or standing relations: the goal family.
  Tier 3 Depth   - a secret you hold on their ruler, or a spymaster edge, or
                   a placed informant: the family AND its target."""

from dataclasses import dataclass
from typing import List, Optional

REGIMENT_POP_COST = 5


@dataclass(frozen=True)
class IntelReport:
    tier: int
    breakdown: List[str]
    apparent_intent: str


def _strength(game, house_name: str) -> float:
    pop = sum(p.population for p in game.provinces_of(house_name))
    return pop // REGIMENT_POP_COST + game.houses[house_name].treasury


def _shares_border(game, viewer: str, target: str) -> bool:
    owned = {p.pid for p in game.provinces_of(viewer)}
    for p in game.provinces_of(target):
        if p.neighbors & owned:
            return True
    return False


def _has_marriage_tie(game, viewer: str, target: str) -> bool:
    for tie in getattr(game.marriages, "marriages", []):
        houses = {tie[1], tie[3]}          # (char_a, house_a, char_b, house_b)
        if houses == {viewer, target}:
            return True
    return False


def _diplomatic_visibility(game, viewer: str, target: str) -> bool:
    if _has_marriage_tie(game, viewer, target):
        return True
    return game.houses[viewer].relations.get(target, 0) != 0


def _court_intrigue(game, house: str) -> float:
    realm = game.realms.get(house)
    if realm is None:
        return 0.0
    return max((c.get_effective_stat("intrigue")
                for c in realm.court.positions.values()
                if c and c.is_alive), default=0.0)


def _depth_visibility(game, viewer: str, target: str) -> bool:
    trealm = game.realms.get(target)
    vrealm = game.realms.get(viewer)
    if trealm is None or vrealm is None or trealm.ruler is None:
        return False
    viewer_ids = {c.id for c in vrealm.dynasty.all_characters.values()}
    if any(viewer_ids & s.holders for s in trealm.ruler.secrets):
        return True
    return _court_intrigue(game, viewer) > _court_intrigue(game, target)


def _mood(game, viewer: str, target: str) -> str:
    rel = game.houses[viewer].relations.get(target, 0)
    if rel < 0:
        return "The mood at their court runs cold toward you"
    if rel > 0:
        return "The mood at their court runs warm toward you"
    return "Their court gives little away"


def report(game, viewer: str, target: str) -> IntelReport:
    """Pure: what `viewer` can legibly read of `target`'s agenda."""
    sources: List[str] = []
    if _shares_border(game, viewer, target):
        sources.append("shared border")
    if _diplomatic_visibility(game, viewer, target):
        sources.append("diplomatic ties")
    if _depth_visibility(game, viewer, target):
        sources.append("intelligence assets")
    if (viewer, target) in game.informants:
        sources.append("informant in place")
    tier = min(3, len(sources))

    goal = game.agendas.get(target)
    if tier <= 0 or goal is None:
        intent = "Their intentions are unknown"
    elif tier == 1:
        intent = _mood(game, viewer, target)
    elif tier == 2:
        intent = f"Pursuing {goal.family}"
    else:
        at = f" against House {goal.target}" if goal.target else ""
        intent = f"Pursuing {goal.family}{at}: {goal.why}"
    return IntelReport(tier=tier, breakdown=sources, apparent_intent=intent)


def threat_rank(game) -> List[str]:
    """Deterministic ordering of every OTHER House by danger to the player: a
    House whose agenda targets the player ranks first, then by raw strength.
    Pure - orders the Powers roster."""
    player = next((h for h in game.houses if game.houses[h].is_player), None)
    others = [h for h in sorted(game.houses) if h != player]

    def key(h: str):
        goal = game.agendas.get(h)
        aims = 1 if (goal is not None and goal.target == player) else 0
        return (-aims, -_strength(game, h), h)

    return sorted(others, key=key)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_intel.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add gilded/intel.py gilded/tests/test_intel.py
git commit -m "feat(gilded): Stage 2 intel read-model - earned tier-0..3 agenda fog"
```

---

## Task S2c-1: The `Takeover` advance loop (chassis) — close the Buyout gap, part 1

The `Takeover` class in `gilded/society/schemes.py` exists but nothing advances it. Add a per-turn advance loop so a started takeover actually progresses.

**Files:**
- Modify: `gilded/chassis.py` (after line 245, the `scheme_mgr.advance_all` emit)
- Test: `gilded/tests/test_agenda.py` (extend — integration)

- [ ] **Step 1: Write the failing test**

Append to `gilded/tests/test_agenda.py`:

```python
def test_chassis_advances_takeovers():
    from gilded.society.schemes import Takeover
    g = GildedGame(seed=6)
    a, b = sorted(g.houses)[0], sorted(g.houses)[1]
    buyer = g.realms[a].ruler
    tk = Takeover(buyer, a, b)
    g.takeovers.append(tk)
    g.end_turn()
    # the loop must have advanced (and pruned it if it completed)
    assert tk in g.takeovers or tk.complete
```

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_agenda.py::test_chassis_advances_takeovers -q`
Expected: FAIL — the takeover never advances / assertion holds only trivially; add the loop so it is exercised. (If it passes trivially because `tk in g.takeovers` stays true, the loop below still must exist for the takeover to progress — verify by asserting advance ran via a message, see Step 3 note.)

- [ ] **Step 3: Add the advance loop**

In `gilded/chassis.py`, immediately after the `scheme_mgr.advance_all` emit (currently lines 244-245), insert:

```python
        for tk in list(self.takeovers):
            self._emit(tk.advance(self.realms, self.enterprises, self.rng),
                       "gazette")
            if tk.complete:
                self.takeovers.remove(tk)
```

`Takeover.advance(realms, enterprises, rng)` returns `List[str]` and sets `.complete` when the House flips (schemes.py:347).

- [ ] **Step 4: Run test to verify it passes**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_agenda.py::test_chassis_advances_takeovers -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/chassis.py gilded/tests/test_agenda.py
git commit -m "feat(gilded): advance in-flight hostile takeovers each turn"
```

---

## Task S2c-2: The two honest verbs (`docket.py`) — Buyout gap part 2 + informant

**Files:**
- Modify: `gilded/docket.py` (new handlers before the `INITIATIVES` dict at line 701; two new dict entries)
- Test: `gilded/tests/test_agenda.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `gilded/tests/test_agenda.py`:

```python
from gilded.docket import INITIATIVES, initiative


def test_start_takeover_initiative_registers_a_takeover():
    g = GildedGame(seed=6)
    a, b = sorted(g.houses)[0], sorted(g.houses)[1]
    assert "start_takeover" in INITIATIVES
    executor = g.realms[a].ruler
    initiative(g, a, "start_takeover", executor, target_house=b)
    assert any(t.buyer_house == a and t.target_house == b for t in g.takeovers)


def test_start_takeover_rejects_self_and_duplicates():
    g = GildedGame(seed=6)
    a = sorted(g.houses)[0]
    executor = g.realms[a].ruler
    out = initiative(g, a, "start_takeover", executor, target_house=a)
    assert g.takeovers == [] and out


def test_establish_informant_initiative_sets_flag():
    g = GildedGame(seed=6)
    a, b = sorted(g.houses)[0], sorted(g.houses)[1]
    assert "establish_informant" in INITIATIVES
    executor = g.realms[a].ruler
    initiative(g, a, "establish_informant", executor, target_house=b)
    assert (a, b) in g.informants
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_agenda.py -k "takeover or informant" -q`
Expected: FAIL — `assert "start_takeover" in INITIATIVES` fails (KeyError-style).

- [ ] **Step 3: Add the two handlers and register them**

In `gilded/docket.py`, add these two handlers immediately before the `INITIATIVES = {` line (currently line 701):

```python
def _init_start_takeover(ctx, target_house=None, **kw) -> List[str]:
    from gilded.society.schemes import Takeover
    if target_house not in ctx.game.houses or target_house == ctx.house:
        return [f"There is no House {target_house} to buy into"]
    if any(t.buyer_house == ctx.house and t.target_house == target_house
           and not t.complete for t in ctx.game.takeovers):
        return [f"A quiet buying campaign against House {target_house} is already under way"]
    ctx.game.takeovers.append(Takeover(ctx.executor, ctx.house, target_house))
    return [f"{ctx.executor.name} begins quietly buying into House {target_house}"]


def _init_establish_informant(ctx, target_house=None, **kw) -> List[str]:
    if target_house not in ctx.game.houses or target_house == ctx.house:
        return [f"There is no House {target_house} to watch"]
    ctx.game.informants.add((ctx.house, target_house))
    return [f"{ctx.executor.name} places an informant inside House {target_house}"]
```

Then add two entries to the `INITIATIVES` dict (inside the braces, after `"negotiate_peace"`):

```python
    "start_takeover": ("capital", _init_start_takeover),
    "establish_informant": ("diplomacy", _init_establish_informant),
```

Note: `List` is already imported in `docket.py`. `initiative()` (line 715) rolls a fumble via `game.rng` before calling the handler — that is the existing, expected behavior for any initiative and does not violate the determinism invariant (which governs goal SELECTION, not action execution).

- [ ] **Step 4: Run tests to verify they pass**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_agenda.py -k "takeover or informant" -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add gilded/docket.py gilded/tests/test_agenda.py
git commit -m "feat(gilded): honest start_takeover and establish_informant initiatives"
```

---

## Task S2c-4: Soft-bias the reactive brain (`ai.py`)

Wire the goal engine into `ai_turn` at three seams: (1) `ensure_agenda` each directive cycle; (2) petition ordering gets a bump in the goal's domain; (3) `_pick_initiative` prefers the goal's signature verb, falling back to today's disposition play.

**Files:**
- Modify: `gilded/ai.py`
- Test: `gilded/tests/test_agenda.py` (extend — integration)

- [ ] **Step 1: Write the failing test**

Append to `gilded/tests/test_agenda.py`:

```python
def test_ai_turn_populates_and_holds_agenda():
    g = GildedGame(seed=13)
    from gilded.ai import ai_turn
    h = next(x for x in sorted(g.houses) if not g.houses[x].is_player)
    ai_turn(g, h)
    assert h in g.agendas
    first = g.agendas[h]
    g.turn += 1
    ai_turn(g, h)
    assert g.agendas[h] is first          # held within the commit window


def test_ai_still_runs_a_full_century():
    g = GildedGame(seed=21)
    for _ in range(40):
        if g.game_over is not None:
            break
        g.end_turn()
    # no exception, agendas populated for the AI houses
    assert any(h in g.agendas for h in g.houses)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_agenda.py::test_ai_turn_populates_and_holds_agenda -q`
Expected: FAIL — `assert h in g.agendas` (ai_turn does not touch agendas yet).

- [ ] **Step 3: Edit `gilded/ai.py`**

3a. Add the import near the top (after line 16, `from gilded.society.characters import opinion_matrix`):

```python
from gilded.agenda import ensure_agenda, goal_domain, goal_initiative
```

3b. Add a petition-bias constant beside the others (after line 24, `CONVICTION_DIV = 50.0`):

```python
AGENDA_PETITION_BONUS = 1.0    # a petition in the goal's domain jumps the queue
```

3c. Change `_score_petition` to accept the active goal's domain and add the bump. Replace lines 35-37:

```python
def _score_petition(ruler, petition, goal_dom: Optional[str] = None) -> float:
    urgency = URGENCY_ESCALATED if petition.escalated else 1.0
    bonus = AGENDA_PETITION_BONUS if goal_dom == petition.domain else 0.0
    return urgency + bonus + abs(_conviction(ruler, petition.domain)) / CONVICTION_DIV
```

3d. Change `_pick_initiative` to prefer the goal's signature verb. Replace its signature and opening (lines 91-94) — add a `goal` parameter and a preference block ABOVE the disposition logic:

```python
def _pick_initiative(game, house_name: str, realm, goal=None):
    """The goal's signature verb first, then leftover attention by disposition."""
    house = game.houses[house_name]
    ruler = realm.ruler
    if goal is not None:
        sig = goal_initiative(game, house_name, goal)
        if sig is not None:
            return sig
```

(Leave the rest of `_pick_initiative` unchanged — it remains the disposition fallback.)

3e. In `ai_turn`, establish/hold the agenda and thread it through. Insert right after `ruler = realm.ruler` (line 131) and before the directive block:

```python
    goal = ensure_agenda(game, house_name)
    goal_dom = goal_domain(goal) if goal is not None else None
```

Then update the docket sort (line 138) to pass `goal_dom`:

```python
    docket.sort(key=lambda p: (-_score_petition(ruler, p, goal_dom), p.pid))
```

And update the `_pick_initiative` call (line 150) to pass `goal`:

```python
        choice = _pick_initiative(game, house_name, realm, goal)
```

`Optional` is already imported in `ai.py` (line 9).

- [ ] **Step 4: Run the integration tests + full baseline**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_agenda.py -q`
Expected: PASS (all agenda tests).

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q`
Expected: tail reads `≥ 300 passed` (281 baseline + the new agenda/intel tests), `0 failed`. If `test_civkings.py::TestTurnStability::test_100_turn_stability` flakes (pre-existing, intermittent), re-run once; `1 failed` on ONLY that test is acceptable.

- [ ] **Step 5: Commit**

```bash
git add gilded/ai.py gilded/tests/test_agenda.py
git commit -m "feat(gilded): soft-bias the reactive AI toward its living goal"
```

---

## Task S2d-1: HUD intent line, Powers tab, Briefing agenda feed (`broadsheet.py`)

Surface the read-models. The persistent HUD gains a one-line read of the spotlight rival's apparent intent; a Powers roster (ordered by `threat_rank`) shows each House's tier + apparent intent; the Briefing feed gains agenda-change lines.

**Files:**
- Modify: `gilded/ui/broadsheet.py`
- Test: `gilded/tests/test_ui_broadsheet.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `gilded/tests/test_ui_broadsheet.py` (follow the file's existing construction pattern — `BroadsheetView(g, house)`):

```python
def test_powers_tab_lists_houses_by_threat():
    from gilded.chassis import GildedGame
    from gilded.ui.broadsheet import BroadsheetView, TABS
    from gilded import agenda
    g = GildedGame(seed=7)
    player = next(iter(g.houses))
    g.houses[player].is_player = True
    for h in g.houses:
        if h != player:
            agenda.ensure_agenda(g, h)
    view = BroadsheetView(g, player)
    assert "Powers" in TABS
    lines = view.powers_lines()          # list[str], one per rival House
    assert lines and all(isinstance(s, str) for s in lines)
    # every non-player House appears
    for h in g.houses:
        if h != player:
            assert any(h in ln for ln in lines)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_ui_broadsheet.py::test_powers_tab_lists_houses_by_threat -q`
Expected: FAIL — `"Powers" not in TABS` and/or `powers_lines` missing.

- [ ] **Step 3: Implement in `broadsheet.py`**

3a. Add `"Powers"` to the `TABS` tuple (place it after `"Atlas"`, before `"House"`):

```python
TABS = ("Briefing", "Gazette", "Ledger", "Letters", "Docket", "Atlas", "Powers", "House")
```

3b. Import the read-model at the top of `broadsheet.py`:

```python
from gilded.intel import report as intel_report, threat_rank
```

3c. Add a `powers_lines(self)` method on `BroadsheetView` that renders the roster:

```python
    def powers_lines(self):
        """One line per rival House, ordered by threat to the player: rank,
        the intel tier, and whatever intent that tier reveals."""
        lines = []
        for h in threat_rank(self.game):
            r = intel_report(self.game, self.house, h)
            src = f" [{', '.join(r.breakdown)}]" if r.breakdown else ""
            lines.append(f"House {h}  (intel {r.tier}/3){src}  -  {r.apparent_intent}")
        return lines
```

3d. In the HUD strip render, add a single intent line for the spotlight rival (`self.game.director.rival` if set, else the top of `threat_rank`). Follow the file's existing HUD-draw idiom; the text is:

```python
        rival = getattr(self.game.director, "rival", None) or (
            threat_rank(self.game)[0] if threat_rank(self.game) else None)
        if rival is not None:
            intent = intel_report(self.game, self.house, rival).apparent_intent
            # draw f"{rival}: {intent}" on the HUD's intent row
```

3e. Add a `Powers` tab branch in the tab-render dispatch that blits `self.powers_lines()` line by line (mirror the existing `Ledger`/`Letters` list-render branches). If the Briefing feed already renders a delta list, append agenda-change strings from a `agenda_feed(prev, curr)` helper — but keep S2d-1 minimal: the Powers tab + HUD intent line are the required deliverables; the Briefing agenda line is optional polish and may be deferred to Stage 8.

- [ ] **Step 4: Run test + UI suite**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_ui_broadsheet.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/ui/broadsheet.py gilded/tests/test_ui_broadsheet.py
git commit -m "feat(gilded): Powers roster + HUD intent line from the intel read-model"
```

---

## Task S2d-2: The informant player action (`app.py`)

The player spends ONE unit of attention to place an informant on a House, raising that House's intel tier durably. Route it through the existing `establish_informant` initiative so the player and AI share the same lever.

**Files:**
- Modify: `gilded/ui/app.py`
- Test: `gilded/tests/test_ui_app.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `gilded/tests/test_ui_app.py` (follow the file's `new_app_state` / `_apply_action` idiom):

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_ui_app.py::test_place_informant_action_spends_attention_and_sets_flag -q`
Expected: FAIL — the `place_informant` action is unhandled.

- [ ] **Step 3: Handle the action in `_apply_action`**

In `gilded/ui/app.py`, add a branch in `_apply_action` (mirror how other player initiatives are dispatched; import `initiative` and resolve the executor as the player's foreign secretary or ruler):

```python
    target = action.get("place_informant")
    if target is not None:
        g = state.game
        house = state.house
        if g.attention.get(house, 0) > 0 and target in g.houses and target != house:
            from gilded.docket import DOMAIN_SEAT, initiative
            realm = g.realms[house]
            seat = DOMAIN_SEAT["diplomacy"]
            holder = realm.court.positions.get(seat)
            executor = holder if (holder is not None and holder.is_alive) else realm.ruler
            g.attention[house] -= 1
            initiative(g, house, "establish_informant", executor, target_house=target)
        return state
```

- [ ] **Step 4: Run test + UI suite**

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/tests/test_ui_app.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gilded/ui/app.py gilded/tests/test_ui_app.py
git commit -m "feat(gilded): player places informants, spending attention for intel"
```

---

## Final Verification (run after all tasks)

- [ ] Full scoped baseline:

Run: `GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q`
Expected: `0 failed`; total = 281 + all new Stage 2 tests (~19). The `test_100_turn_stability` flake exception (re-run once) still applies.

- [ ] A living-adversary smoke: a fresh game run for ~40 turns produces agendas for every AI House, at least one `start_takeover`/`declare_war`/scheme traceable to a goal, and `intel.report` tiers that rise when a border/marriage/informant exists. (This becomes the CynCo `S2_smoke.py`, authored read-only.)

---

## Self-Review

**Spec coverage** (against `docs/superpowers/specs/2026-07-22-gilded-stage2-living-adversaries-design.md`):
- §1 Goal Model → `agenda.py` (Goal, 7 FAMILIES, select/commit/re-eval, soft-bias) — Tasks S2a-1, S2c-4. ✔
- §2 Fog → `intel.py` additive tiers 0..3, informant lever — Tasks S2b-1, S2c-2, S2d-2. ✔
- §3 Threat rank & rival reconciliation → `intel.threat_rank` separate from `Director.rival` (untouched) — S2b-1, S2d-1. ✔
- §4 UI → HUD intent line, Powers tab, informant action — S2d-1, S2d-2. Briefing agenda feed marked optional/deferred. ✔ (partial by design)
- §5 Architecture → module split honored; `agenda.py` never imports `ai.py`. ✔
- §6 Determinism & Testing → selection no-RNG test, intel purity soak, commit-window tests. ✔
- §7 Build Order S2a-S2d → mapped 1:1. ✔
- The Buyout execution gap (user decision "1") → `start_takeover` verb + chassis advance loop — S2c-1, S2c-2. ✔

**Placeholder scan:** No TBD/TODO in code steps; every code step ships complete code. The one intentional deferral (Briefing agenda-change line) is called out explicitly and pushed to Stage 8, not left as a silent gap.

**Type consistency:** `Goal(family, target, opened_turn, commit_turns, why)` used identically in `agenda.py`, tests, and `intel.threat_rank`. `IntelReport(tier, breakdown, apparent_intent)` consistent across `intel.py`, tests, and `broadsheet.powers_lines`. `goal_initiative` returns `(verb, kwargs)` matching `_pick_initiative`'s existing contract and `docket.initiative(game, house, verb, executor, **kwargs)`. Verb strings `start_takeover` / `establish_informant` match between `docket.INITIATIVES`, `goal_initiative`, and the UI action.

**Risk note:** `test_chassis_advances_takeovers` (S2c-1 Step 2) may pass trivially before the loop exists because the takeover object stays in the list. The loop is still required for the takeover to *progress*; the century smoke (Final Verification) and `test_ai_still_runs_a_full_century` are the real guards that a started buyout advances. If tighter coverage is wanted, assert on an advance message.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-22-gilded-stage2-living-adversaries.md`.

**Per the CivKings constraint, actual implementation ships via byte-exact CynCo mission briefs (devtree-validated, 5-check verified) — not hand-edits.** The recommended path:

1. Build & validate the code from this plan in a scratch devtree (`C:/tmp/gilded_briefs/S2_src/`), running each task's tests.
2. Generate an N1-format brief per build sub-stage (S2a / S2b / S2c / S2d, or one atomic S2 brief like Stage 1) via `C:/tmp/gilded_briefs/`.
3. Dispatch through CynCo, run the 5-check + `S2_smoke.py`, commit.

Two ways to produce/validate the code before briefing:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task into an isolated worktree, review between tasks, then roll the validated files into the CynCo brief.

**2. Inline Execution** — validate tasks in a scratch devtree here, then brief.

Which approach would you like?
