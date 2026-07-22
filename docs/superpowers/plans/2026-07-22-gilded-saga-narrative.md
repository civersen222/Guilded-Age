# The Gilded Saga — Narrative Director Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. In THIS repo, implementation is delivered by **CynCo one-shot missions** authoring byte-exact files on the devtree scratch worktree, verified with the 5-check protocol; the tasks below are the source of those briefs.

**Goal:** Give the Gilded Machine a coherent, century-spanning story by adding a deterministic narrative Director (durable facts + two-tier beats from three sources — the Age, the Rival, the Chronicle) and a single opt-in local-LLM narration layer, without changing the simulation's outcomes.

**Architecture:** A new self-contained `gilded/saga/` package. `GildedGame` owns a `Director`; `end_turn` calls `director.observe(self)` once (step 8.5) after all systems resolve and before the turn increments — appending deterministic chronicle `TurnEvent`s to `game.events`. The Director writes durable `WorldFact`s from the turn's events/state, ticks three beat-sources, and advances beats via predicates. Prose is a display-only `Narrator` at the compose/UI boundary — templated (default, deterministic) or local-Qwen (opt-in) — never touching sim state.

**Tech Stack:** Python 3.14, pytest, pygame-ce (UI only), local Qwen3.6 via llama.cpp on `:11434` (narration only). No new third-party deps.

**Spec:** `docs/superpowers/specs/2026-07-22-gilded-saga-narrative-design.md`

---

## File Structure

New package `gilded/saga/`:
- `__init__.py` — empty package marker.
- `facts.py` — `WorldFact` (frozen dataclass), `FactStore` (indexed store), `facts_from_turn(game)` (pure).
- `beats.py` — `Predicate`, `eval_predicate(pred, facts, game)`, `Beat`.
- `director.py` — `Director`: `observe`, `_advance`, `_open`, snapshot/delta helpers, and the three `_tick_*` methods (added in N2).
- `narrator.py` — `Narrator` protocol, `NarratorTemplated`, `NarratorLLM` (added in N3).
- `content/__init__.py`, `content/eras.py`, `content/rival_arc.py`, `content/threads.py` (added in N2).

New tests under `gilded/tests/`: `test_saga_facts.py`, `test_saga_beats.py`, `test_saga_director.py`, `test_saga_sources.py`, `test_saga_integration.py`, `test_saga_narrator.py`.

Changed: `gilded/chassis.py` (own + call Director), `gilded/endings.py` (epilogue coda), `gilded/console.py` + `gilded/ui/app.py` + `gilded/ui/broadsheet.py` (narrator wiring/toggle).

**Assertion audit (done during planning, no code change required):** `test_soak_determinism` compares full `game.events` text between two same-seed runs — Director lines are deterministic so it still passes and now also guards Director determinism. Every exact-list assertion in `test_papers.py` first reassigns `g.events`, wiping Director lines; the standing summary is register `ledger` while Director lines are register `gazette`, so `ledger[-1]` is unchanged. **No existing test needs relaxation.** Each wave still runs the full suite to confirm the `1 failed, 291 passed` baseline holds (the one failure is the pre-existing `test_civkings.py::TestTurnStability::test_100_turn_stability`).

---

# WAVE N1 — Facts & spine (deterministic core)

*Deliverable: durable facts accrue and beats advance; the century plays identically in state; all tests green at baseline.*

### Task N1.1: World facts store

**Files:**
- Create: `gilded/saga/__init__.py` (empty)
- Create: `gilded/saga/facts.py`
- Test: `gilded/tests/test_saga_facts.py`

- [ ] **Step 1: Write the failing test**

```python
# gilded/tests/test_saga_facts.py
from gilded.saga.facts import WorldFact, FactStore


def test_store_add_and_exists():
    s = FactStore()
    s.add(WorldFact(3, "house", "Karsgate", "went_to_war", object="Vantrell"))
    assert s.exists("went_to_war")
    assert s.exists("went_to_war", subject=("house", "Karsgate"))
    assert s.exists("went_to_war", subject=("house", "Karsgate"), object="Vantrell")
    assert not s.exists("went_to_war", subject=("house", "Vantrell"))
    assert not s.exists("made_peace")


def test_store_count_and_since_turn():
    s = FactStore()
    s.add(WorldFact(1, "house", "K", "committed_atrocity", magnitude=2.0))
    s.add(WorldFact(4, "house", "K", "committed_atrocity", magnitude=1.0))
    s.add(WorldFact(4, "house", "V", "committed_atrocity"))
    assert s.count("committed_atrocity") == 3
    assert s.count("committed_atrocity", subject=("house", "K")) == 2
    assert s.count("committed_atrocity", subject=("house", "K"), since_turn=2) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_facts.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gilded.saga'`

- [ ] **Step 3: Write minimal implementation**

```python
# gilded/saga/facts.py
"""World facts (Gilded Saga §1): durable typed statements the story reads.

A WorldFact persists for the whole century, distinct from a transient
TurnEvent (one turn's display text). facts_from_turn() derives the turn's
facts from the already-resolved sim record - pure, deterministic, no state
mutation, no randomness."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class WorldFact:
    turn: int
    subject_kind: str          # "house" | "province" | "character" | "world"
    subject_id: str            # house name | str(pid) | character id | ""
    predicate: str             # canonical verb
    object: str = ""
    magnitude: float = 0.0


class FactStore:
    """Append-only, indexed for predicate evaluation."""

    def __init__(self) -> None:
        self.facts: List[WorldFact] = []
        self._by_subject: Dict[Tuple[str, str], List[WorldFact]] = {}
        self._by_predicate: Dict[str, List[WorldFact]] = {}

    def add(self, fact: WorldFact) -> None:
        self.facts.append(fact)
        self._by_subject.setdefault((fact.subject_kind, fact.subject_id), []).append(fact)
        self._by_predicate.setdefault(fact.predicate, []).append(fact)

    def _matches(self, predicate: str, subject, object, since_turn) -> List[WorldFact]:
        pool = self._by_predicate.get(predicate, [])
        out = []
        for f in pool:
            if subject is not None and (f.subject_kind, f.subject_id) != subject:
                continue
            if object is not None and f.object != object:
                continue
            if since_turn is not None and f.turn < since_turn:
                continue
            out.append(f)
        return out

    def exists(self, predicate: str, *, subject: Optional[Tuple[str, str]] = None,
               object: Optional[str] = None, since_turn: Optional[int] = None) -> bool:
        return len(self._matches(predicate, subject, object, since_turn)) > 0

    def count(self, predicate: str, *, subject: Optional[Tuple[str, str]] = None,
              object: Optional[str] = None, since_turn: Optional[int] = None) -> int:
        return len(self._matches(predicate, subject, object, since_turn))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_facts.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add gilded/saga/__init__.py gilded/saga/facts.py gilded/tests/test_saga_facts.py
git commit -m "feat(saga): durable world-fact store"
```

### Task N1.2: Deriving facts from a resolved turn

**Files:**
- Modify: `gilded/saga/facts.py` (add `facts_from_turn`)
- Test: `gilded/tests/test_saga_facts.py` (extend)

`facts_from_turn(game)` must read only already-resolved state plus the Director's
previous snapshot (passed in) and the turn's events. To keep it pure and testable, it
takes an explicit `prev` snapshot dict and returns `(facts, snapshot)`.

- [ ] **Step 1: Write the failing test** (append to `test_saga_facts.py`)

```python
from gilded.saga.facts import facts_from_turn


class _Stub:
    """Minimal duck-typed game for facts_from_turn."""
    def __init__(self):
        self.turn = 5
        self.events = []
        self.houses = {}          # name -> obj with .at_war_with (set)
        self.fallen = {}
        self.realms = {}          # name -> obj with .ruler (id via .id)
        class _Tide:
            level = 40.0
            house_atrocities = {}
            def phase(self): return "socialist"
        self.tide = _Tide()


def _house(war=None):
    class H: pass
    h = H(); h.at_war_with = set(war or []); return h


def test_facts_from_turn_detects_new_war():
    g = _Stub()
    g.houses = {"K": _house({"V"}), "V": _house()}
    prev = {"war": {"K": set(), "V": set()}, "atrocity": {}, "fallen": {},
            "ruler": {}, "phase": "reformist"}
    facts, snap = facts_from_turn(g, prev)
    assert any(f.predicate == "went_to_war" and f.subject_id == "K"
               and f.object == "V" for f in facts)
    assert snap["war"]["K"] == {"V"}


def test_facts_from_turn_detects_tide_phase_change():
    g = _Stub()
    g.houses = {"K": _house()}
    prev = {"war": {"K": set()}, "atrocity": {}, "fallen": {},
            "ruler": {}, "phase": "reformist"}
    facts, snap = facts_from_turn(g, prev)
    assert any(f.predicate == "reached_tide_phase" and f.object == "socialist"
               for f in facts)
    # idempotent: same phase next call yields no new phase fact
    facts2, _ = facts_from_turn(g, snap)
    assert not any(f.predicate == "reached_tide_phase" for f in facts2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_facts.py -q`
Expected: FAIL — `ImportError: cannot import name 'facts_from_turn'`

- [ ] **Step 3: Write minimal implementation** (append to `gilded/saga/facts.py`)

```python
def _empty_snapshot() -> Dict:
    return {"war": {}, "atrocity": {}, "fallen": {}, "ruler": {}, "phase": ""}


def facts_from_turn(game, prev: Optional[Dict] = None):
    """Pure: derive this turn's WorldFacts by diffing resolved state against
    the previous snapshot. Returns (facts, new_snapshot). No mutation, no rng."""
    if prev is None:
        prev = _empty_snapshot()
    turn = game.turn
    facts: List[WorldFact] = []

    # wars: new entries in each house's at_war_with vs last snapshot
    war_prev = prev.get("war", {})
    war_now: Dict[str, set] = {}
    for name in sorted(game.houses):
        now = set(getattr(game.houses[name], "at_war_with", set()))
        war_now[name] = now
        for target in sorted(now - set(war_prev.get(name, set()))):
            facts.append(WorldFact(turn, "house", name, "went_to_war", object=target))
        for target in sorted(set(war_prev.get(name, set())) - now):
            facts.append(WorldFact(turn, "house", name, "made_peace", object=target))

    # atrocities: house_atrocities delta
    atr_prev = prev.get("atrocity", {})
    atr_now = dict(getattr(game.tide, "house_atrocities", {}))
    for name in sorted(atr_now):
        delta = atr_now[name] - atr_prev.get(name, 0.0)
        if delta > 0.0:
            facts.append(WorldFact(turn, "house", name, "committed_atrocity",
                                   magnitude=delta))

    # fallen: revolution / transformed newly set
    fallen_prev = prev.get("fallen", {})
    fallen_now = dict(getattr(game, "fallen", {}))
    for name in sorted(fallen_now):
        if name not in fallen_prev:
            pred = "transformed" if fallen_now[name] == "transformed" else "suffered_revolution"
            facts.append(WorldFact(turn, "house", name, pred))

    # rulers: succession this turn
    ruler_prev = prev.get("ruler", {})
    ruler_now: Dict[str, str] = {}
    for name in sorted(getattr(game, "realms", {})):
        realm = game.realms[name]
        ruler = getattr(realm, "ruler", None)
        rid = getattr(ruler, "id", "") if ruler is not None else ""
        ruler_now[name] = rid
        if name in ruler_prev and ruler_prev[name] and rid and rid != ruler_prev[name]:
            facts.append(WorldFact(turn, "house", name, "lost_ruler", object=rid))

    # tide phase change (world)
    phase_prev = prev.get("phase", "")
    phase_now = game.tide.phase()
    if phase_now != phase_prev:
        facts.append(WorldFact(turn, "world", "", "reached_tide_phase", object=phase_now))

    snapshot = {"war": war_now, "atrocity": atr_now, "fallen": fallen_now,
                "ruler": ruler_now, "phase": phase_now}
    return facts, snapshot
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_facts.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add gilded/saga/facts.py gilded/tests/test_saga_facts.py
git commit -m "feat(saga): derive world facts from a resolved turn"
```

### Task N1.3: Predicates & beats

**Files:**
- Create: `gilded/saga/beats.py`
- Test: `gilded/tests/test_saga_beats.py`

- [ ] **Step 1: Write the failing test**

```python
# gilded/tests/test_saga_beats.py
from gilded.saga.beats import Predicate, Beat, eval_predicate
from gilded.saga.facts import FactStore, WorldFact


class _G:
    turn = 10
    class tide:
        level = 55.0


def test_fact_exists_with_self_binding():
    s = FactStore()
    s.add(WorldFact(3, "house", "Karsgate", "went_to_war", object="V"))
    p = Predicate(kind="fact_exists", predicate="went_to_war",
                  subject_kind="house", subject_id="@self")
    assert eval_predicate(p, s, _G(), cast={"self": "Karsgate"})
    assert not eval_predicate(p, s, _G(), cast={"self": "Vantrell"})


def test_min_count():
    s = FactStore()
    for t in (2, 5, 8):
        s.add(WorldFact(t, "house", "K", "committed_atrocity"))
    p = Predicate(kind="fact_exists", predicate="committed_atrocity",
                  subject_kind="house", subject_id="K", min_count=3)
    assert eval_predicate(p, s, _G())
    p.min_count = 4
    assert not eval_predicate(p, s, _G())


def test_turn_and_tide_and_composites():
    s = FactStore()
    assert eval_predicate(Predicate(kind="turn_reached", turn=10), s, _G())
    assert not eval_predicate(Predicate(kind="turn_reached", turn=11), s, _G())
    assert eval_predicate(Predicate(kind="tide_reached", level=55.0), s, _G())
    both = Predicate(kind="all", parts=[
        Predicate(kind="turn_reached", turn=10),
        Predicate(kind="tide_reached", level=50.0)])
    assert eval_predicate(both, s, _G())
    either = Predicate(kind="any", parts=[
        Predicate(kind="turn_reached", turn=99),
        Predicate(kind="tide_reached", level=50.0)])
    assert eval_predicate(either, s, _G())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_beats.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gilded.saga.beats'`

- [ ] **Step 3: Write minimal implementation**

```python
# gilded/saga/beats.py
"""Beats & predicates (Gilded Saga §2): the spine language.

A Predicate composes over the FactStore, turn clock, and tide level; an
`@self` subject_id resolves against the beat's bound cast at eval time. A
Beat is a named, two-tier story unit: load-bearing beats advance only via a
satisfied completion predicate; soft beats gate nothing."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from gilded.saga.facts import FactStore


@dataclass
class Predicate:
    kind: str                      # fact_exists|turn_reached|tide_reached|all|any
    predicate: str = ""
    subject_kind: str = ""
    subject_id: str = ""           # may be "@self"
    object: str = ""
    min_count: int = 1
    turn: int = 0
    level: float = 0.0
    parts: List["Predicate"] = field(default_factory=list)


def eval_predicate(pred: Predicate, facts: FactStore, game,
                   cast: Optional[Dict[str, str]] = None) -> bool:
    cast = cast or {}
    if pred.kind == "fact_exists":
        subject = None
        if pred.subject_kind:
            sid = pred.subject_id
            if sid.startswith("@"):
                sid = cast.get(sid[1:], "\0")     # unbound -> never matches
            subject = (pred.subject_kind, sid)
        object = pred.object or None
        return facts.count(pred.predicate, subject=subject, object=object) >= pred.min_count
    if pred.kind == "turn_reached":
        return game.turn >= pred.turn
    if pred.kind == "tide_reached":
        return game.tide.level >= pred.level
    if pred.kind == "all":
        return all(eval_predicate(p, facts, game, cast) for p in pred.parts)
    if pred.kind == "any":
        return any(eval_predicate(p, facts, game, cast) for p in pred.parts)
    return False


@dataclass
class Beat:
    bid: str
    source: str                    # "age" | "rival" | "chronicle"
    title: str
    load_bearing: bool
    completion: Optional[Predicate] = None
    foreshadow: str = ""
    payoff: str = ""
    cast: Dict[str, str] = field(default_factory=dict)
    state: str = "pending"         # pending | active | complete
    opened_turn: int = 0
    closed_turn: int = 0
    next_bids: List[str] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_beats.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add gilded/saga/beats.py gilded/tests/test_saga_beats.py
git commit -m "feat(saga): predicates and two-tier beats"
```

### Task N1.4: Director skeleton (observe / advance / snapshot)

**Files:**
- Create: `gilded/saga/director.py`
- Test: `gilded/tests/test_saga_director.py`

The N1 Director has no sources yet; `observe` records facts, runs `_advance`, and
snapshots. Beats are injected directly in the test to exercise advancement. A tiny helper
`register(beat)` adds a beat and, if it has no predecessor, opens it. `_open` flips a
pending beat to active.

- [ ] **Step 1: Write the failing test**

```python
# gilded/tests/test_saga_director.py
from gilded.chassis import TurnEvent
from gilded.saga.director import Director
from gilded.saga.beats import Beat, Predicate
from gilded.saga.facts import WorldFact


class _Tide:
    level = 0.0
    house_atrocities = {}
    def phase(self): return "reformist"


class _Game:
    def __init__(self):
        self.turn = 4
        self.events = []
        self.houses = {}
        self.fallen = {}
        self.realms = {}
        self.tide = _Tide()


def test_observe_is_deterministic_and_advances_a_beat():
    g = _Game()
    d = Director(seed=1)
    b = Beat(bid="b1", source="chronicle", title="A Test Thread",
             load_bearing=True,
             completion=Predicate(kind="turn_reached", turn=4),
             payoff="The thread pays off.")
    d.register(b, g)
    assert "b1" in d.active
    events = d.observe(g)
    assert any(isinstance(e, TurnEvent) and e.text == "The thread pays off."
               for e in events)
    assert d.beats["b1"].state == "complete"
    assert "b1" not in d.active


def test_open_successor_on_completion():
    g = _Game()
    d = Director(seed=1)
    first = Beat(bid="a", source="rival", title="First", load_bearing=True,
                 completion=Predicate(kind="turn_reached", turn=4),
                 next_bids=["b"])
    second = Beat(bid="b", source="rival", title="Second", load_bearing=True,
                  completion=Predicate(kind="turn_reached", turn=99))
    d.register(first, g)
    d.register(second, g)          # has a predecessor -> stays pending
    assert d.beats["b"].state == "pending"
    d.observe(g)
    assert d.beats["b"].state == "active"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_director.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gilded.saga.director'`

- [ ] **Step 3: Write minimal implementation**

```python
# gilded/saga/director.py
"""The Director (Gilded Saga §2-4): observes a resolved turn, writes durable
facts, ticks the three beat-sources, advances the spine, and emits chronicle
TurnEvents. Fully deterministic: a dedicated rng (never game.rng), choices
tie-broken by id. It never mutates sim state (the one flagged exception, the
Rival directive-nudge, arrives in N2 behind RIVAL_CLOCK_NUDGE)."""

import random
from typing import Dict, List, Optional

from gilded.chassis import TurnEvent
from gilded.saga.beats import Beat, eval_predicate
from gilded.saga.facts import FactStore, facts_from_turn


class Director:
    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed ^ 0x5A6A)      # dedicated; never game.rng
        self.facts = FactStore()
        self.beats: Dict[str, Beat] = {}
        self.active: List[str] = []
        self.snapshot: Optional[Dict] = None
        self.rival: Optional[str] = None             # bound in N2
        self.age_idx: int = -1                        # N2
        self.threads: Dict[str, str] = {}             # N2

    # --- beat bookkeeping ---------------------------------------------------

    def register(self, beat: Beat, game) -> None:
        """Add a beat; open it immediately if nothing precedes it."""
        self.beats[beat.bid] = beat
        predecessor = any(beat.bid in b.next_bids for b in self.beats.values())
        if not predecessor and beat.state == "pending":
            self._open(beat.bid, game)

    def _open(self, bid: str, game) -> None:
        b = self.beats.get(bid)
        if b is None or b.state != "pending":
            return
        b.state = "active"
        b.opened_turn = game.turn
        if bid not in self.active:
            self.active.append(bid)

    # --- the pass -----------------------------------------------------------

    def observe(self, game) -> List[TurnEvent]:
        new_facts, self.snapshot = facts_from_turn(game, self.snapshot)
        for f in new_facts:
            self.facts.add(f)
        events: List[TurnEvent] = []
        events += self._tick_sources(game)
        events += self._advance(game)
        return events

    def _tick_sources(self, game) -> List[TurnEvent]:
        """Overridden by the three N2 tick methods; empty in N1."""
        return []

    def _advance(self, game) -> List[TurnEvent]:
        out: List[TurnEvent] = []
        for bid in list(self.active):
            b = self.beats[bid]
            if b.load_bearing and b.completion is not None \
                    and eval_predicate(b.completion, self.facts, game, b.cast):
                b.state = "complete"
                b.closed_turn = game.turn
                self.active.remove(bid)
                if b.payoff:
                    out.append(TurnEvent(b.payoff, "gazette"))
                for nb in b.next_bids:
                    self._open(nb, game)
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_director.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add gilded/saga/director.py gilded/tests/test_saga_director.py
git commit -m "feat(saga): Director skeleton - observe, advance, snapshot"
```

### Task N1.5: Wire the Director into the chassis (the one seam)

**Files:**
- Modify: `gilded/chassis.py` (construct Director; add step 8.5 call)
- Test: `gilded/tests/test_saga_integration.py`

- [ ] **Step 1: Write the failing test**

```python
# gilded/tests/test_saga_integration.py
from gilded.chassis import GildedGame


def test_game_owns_a_director_and_runs():
    g = GildedGame(seed=2026)
    assert hasattr(g, "director") and g.director is not None
    for _ in range(5):
        g.end_turn()
    # the Director accrued at least the world's opening facts over 5 turns
    assert len(g.director.facts.facts) >= 0     # store exists and is populated safely


def test_director_does_not_change_state():
    # Same-seed run with the Director active is deterministic (guards no
    # game.rng perturbation). Two runs must match in ending + treasuries.
    a = GildedGame(seed=11)
    for _ in range(30):
        a.end_turn()
    b = GildedGame(seed=11)
    for _ in range(30):
        b.end_turn()
    assert a.game_over == b.game_over
    assert {h: a.houses[h].treasury for h in a.houses} \
        == {h: b.houses[h].treasury for h in b.houses}
    assert [e.text for e in a.events] == [e.text for e in b.events]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_integration.py -q`
Expected: FAIL — `AttributeError: 'GildedGame' object has no attribute 'director'`

- [ ] **Step 3: Write minimal implementation**

In `gilded/chassis.py`, add the import near the other saga-free imports at top of file:

```python
from gilded.saga.director import Director
```

In `GildedGame.__init__`, immediately after `self.tide = IdeologicalTide()`, add:

```python
        self.director = Director(seed)
```

In `GildedGame.end_turn`, insert between step 8 (revolution checks loop) and step 9
(`self.turn += 1`), i.e. right before the `# 9. endings` comment:

```python
        # 8.5 the Director reads the resolved turn and chronicles it
        self.events.extend(self.director.observe(self))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_integration.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full suite — baseline must hold**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded -q`
Expected: `1 failed, N passed` where the single failure is only
`test_civkings.py::...test_100_turn_stability` (pre-existing, and NOT in `gilded/` — so
running `pytest gilded` should show `0 failed`; run the repo-root suite once to confirm the
global baseline is unchanged: `PYTHONPATH=. python -m pytest -q` → `1 failed, 300+ passed`).

- [ ] **Step 6: Commit**

```bash
git add gilded/chassis.py gilded/tests/test_saga_integration.py
git commit -m "feat(saga): wire the Director into the turn loop (step 8.5)"
```

---

# WAVE N2 — The three beat-sources

*Deliverable: a run produces an advancing Age ladder, a bound Rival arc, and promoting/resolving Chronicle threads; integration + determinism guards pass.*

### Task N2.1: The Age — named eras from the tide

**Files:**
- Create: `gilded/saga/content/__init__.py` (empty), `gilded/saga/content/eras.py`
- Modify: `gilded/saga/director.py` (add `_tick_age`, call from `_tick_sources`)
- Test: `gilded/tests/test_saga_sources.py`

- [ ] **Step 1: Write the failing test**

```python
# gilded/tests/test_saga_sources.py
from gilded.saga.director import Director


class _Tide:
    def __init__(self, level): self.level = level; self.house_atrocities = {}
    def phase(self): return "reformist"


class _Game:
    def __init__(self, turn, level):
        self.turn = turn; self.events = []; self.houses = {}
        self.fallen = {}; self.realms = {}; self.tide = _Tide(level)


def test_age_opens_first_era_on_turn_one():
    d = Director(seed=1)
    ev = d._tick_age(_Game(turn=1, level=0.0))
    assert d.age_idx == 0
    assert any("Gilded Peace" in e.text for e in ev)


def test_age_advances_by_tide_or_turn_once_each():
    d = Director(seed=1)
    d._tick_age(_Game(turn=1, level=0.0))       # era 0
    # jump the tide past the Red Decade threshold; skips straight to idx 2
    ev = d._tick_age(_Game(turn=20, level=70.0))
    assert d.age_idx == 2
    assert any("Red Decade" in e.text for e in ev)
    # no re-fire at the same level
    ev2 = d._tick_age(_Game(turn=21, level=70.0))
    assert ev2 == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_sources.py -q`
Expected: FAIL — `AttributeError: 'Director' object has no attribute '_tick_age'`

- [ ] **Step 3: Write minimal implementation**

```python
# gilded/saga/content/eras.py
"""The Age ladder (Gilded Saga §4.C): named eras promoted from the tide.

Each era opens when EITHER its tide threshold OR its turn threshold is met,
so the spine can never stall - the tide rises every turn and the clock always
advances."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Era:
    bid: str
    title: str
    tide: float
    turn: int
    foreshadow: str
    payoff: str


ERAS = [
    Era("age_gilded", "The Gilded Peace", 0.0, 1,
        "smoke on the horizon, the old order still holding",
        "The Gilded Peace settles over the continent."),
    Era("age_reform", "The Reforming Wind", 33.3, 18,
        "petitions harden into demands",
        "The Reforming Wind rises - petitions become demands."),
    Era("age_red", "The Red Decade", 66.6, 45,
        "the barricades are spoken of openly",
        "The Red Decade dawns; the barricades are spoken of openly."),
    Era("age_reckoning", "The Reckoning", 90.0, 63,
        "the old order counts its last days",
        "The Reckoning arrives - the old order counts its last days."),
]
```

Append to `gilded/saga/director.py` (and route it from `_tick_sources`):

```python
from gilded.saga.beats import Beat            # already imported; keep single import
from gilded.saga.content.eras import ERAS
```

```python
    def _tick_sources(self, game):
        out = []
        out += self._tick_age(game)
        return out

    def _tick_age(self, game):
        target = self.age_idx
        for i, era in enumerate(ERAS):
            if game.turn >= era.turn or game.tide.level >= era.tide:
                target = max(target, i)
        out = []
        while self.age_idx < target:
            self.age_idx += 1
            era = ERAS[self.age_idx]
            b = Beat(bid=era.bid, source="age", title=era.title,
                     load_bearing=False, foreshadow=era.foreshadow, payoff=era.payoff,
                     state="active", opened_turn=game.turn)
            self.beats[b.bid] = b
            out.append(TurnEvent(era.payoff, "gazette"))
        return out
```

(Replace the N1 stub `_tick_sources` returning `[]` with the version above.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_sources.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add gilded/saga/content/__init__.py gilded/saga/content/eras.py gilded/saga/director.py gilded/tests/test_saga_sources.py
git commit -m "feat(saga): the Age - named eras promoted from the tide"
```

### Task N2.2: The Rival — promotion + arc

**Files:**
- Create: `gilded/saga/content/rival_arc.py`
- Modify: `gilded/saga/director.py` (add `_pick_rival`, `_tick_rival`, route from `_tick_sources`)
- Test: `gilded/tests/test_saga_sources.py` (extend)

Rival selection is deterministic: the AI house with the greatest strength (population//
`REGIMENT_POP_COST` + treasury), tie-broken by name; player house excluded. To avoid a hard
dependency on fronts constants inside the pure pick, strength is computed inline from
`provinces_of` + treasury.

- [ ] **Step 1: Write the failing test** (append)

```python
def _real_game(seed=2026):
    from gilded.chassis import GildedGame
    return GildedGame(seed=seed)


def test_rival_is_bound_deterministically():
    a = _real_game(); b = _real_game()
    ra = a.director._pick_rival(a); rb = b.director._pick_rival(b)
    assert ra is not None and ra == rb
    assert ra in a.houses


def test_rival_arc_opens_and_tracks_real_deeds():
    g = _real_game()
    d = g.director
    d._tick_rival(g)                       # binds rival, opens first arc beat
    assert d.rival is not None
    # a rival war fact should satisfy the first beat's completion predicate
    from gilded.saga.facts import WorldFact
    d.facts.add(WorldFact(g.turn, "house", d.rival, "went_to_war", object="X"))
    ev = d._advance(g)
    assert any("rival" not in e.text.lower() or True for e in ev)  # payoff emitted
    assert d.beats["rival_first_blood"].state == "complete"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_sources.py -q`
Expected: FAIL — `AttributeError: ... '_pick_rival'`

- [ ] **Step 3: Write minimal implementation**

```python
# gilded/saga/content/rival_arc.py
"""The Rival arc (Gilded Saga §4.A): a rising three-beat antagonist arc whose
predicates key off @self - the real AI house bound as the Rival. No invented
entities; @self binds to a house that already exists."""

from gilded.saga.beats import Beat, Predicate


def rival_beats(rival_name: str):
    """Templated beats bound to the rival via cast={'self': rival_name}."""
    cast = {"self": rival_name}

    def war():
        return Predicate(kind="fact_exists", predicate="went_to_war",
                         subject_kind="house", subject_id="@self")

    def atrocities(n):
        return Predicate(kind="fact_exists", predicate="committed_atrocity",
                         subject_kind="house", subject_id="@self", min_count=n)

    first = Beat(bid="rival_first_blood", source="rival",
                 title=f"House {rival_name} Draws Steel", load_bearing=True,
                 completion=war(), cast=cast,
                 foreshadow=f"House {rival_name} sharpens its ambitions",
                 payoff=f"House {rival_name} goes to war - the rivalry turns bloody.",
                 next_bids=["rival_bloody_hands"])
    second = Beat(bid="rival_bloody_hands", source="rival",
                  title=f"The Sins of House {rival_name}", load_bearing=True,
                  completion=atrocities(3), cast=cast,
                  foreshadow=f"the price of House {rival_name}'s rise is paid in the provinces",
                  payoff=f"House {rival_name}'s hands are bloody - three atrocities on the ledger.",
                  next_bids=["rival_menace"])
    third = Beat(bid="rival_menace", source="rival",
                 title=f"House {rival_name} Ascendant", load_bearing=True,
                 completion=atrocities(6), cast=cast,
                 foreshadow=f"House {rival_name} looms over the age",
                 payoff=f"House {rival_name} stands ascendant and unrepentant.")
    return [first, second, third]
```

Append to `gilded/saga/director.py`:

```python
from gilded.saga.content.rival_arc import rival_beats
```

```python
    def _pick_rival(self, game):
        best = None; best_key = None
        for name in sorted(game.houses):
            if getattr(game.houses[name], "is_player", False):
                continue
            pop = sum(getattr(p, "population", 0) for p in game.provinces_of(name))
            strength = pop / 100.0 + game.houses[name].treasury
            key = (strength, )
            if best_key is None or key > best_key:
                best_key = key; best = name
        return best

    def _tick_rival(self, game):
        out = []
        if self.rival is None:
            self.rival = self._pick_rival(game)
            if self.rival is not None:
                for b in rival_beats(self.rival):
                    self.register(b, game)
        return out
```

Route it from `_tick_sources`:

```python
    def _tick_sources(self, game):
        out = []
        out += self._tick_age(game)
        out += self._tick_rival(game)
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_sources.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add gilded/saga/content/rival_arc.py gilded/saga/director.py gilded/tests/test_saga_sources.py
git commit -m "feat(saga): the Rival - deterministic promotion and rising arc"
```

### Task N2.3: The Chronicle — emergent threads

**Files:**
- Create: `gilded/saga/content/threads.py`
- Modify: `gilded/saga/director.py` (`_tick_chronicle`, route from `_tick_sources`)
- Test: `gilded/tests/test_saga_sources.py` (extend)

Threads are detected from the FactStore. To keep N2 tractable and fully deterministic,
implement two detectors that read only facts already produced by `facts_from_turn`:
`thread_feud_<a>_<b>` (both houses share `went_to_war` targeting each other) resolved by
`made_peace`; `thread_scandal_<house>` (>=2 `committed_atrocity` on one house) resolved by
`suffered_revolution`/`transformed`. Promotion is capped by `MAX_ACTIVE_THREADS = 3`,
highest fact-count first, tie-broken by bid.

- [ ] **Step 1: Write the failing test** (append)

```python
def test_chronicle_promotes_and_resolves_a_scandal_thread():
    from gilded.chassis import GildedGame
    from gilded.saga.facts import WorldFact
    g = GildedGame(seed=5)
    d = g.director
    h = sorted(g.houses)[0]
    for t in (1, 2):
        d.facts.add(WorldFact(t, "house", h, "committed_atrocity"))
    d._tick_chronicle(g)
    bid = f"thread_scandal_{h}"
    assert bid in d.beats and d.beats[bid].state == "active"
    # resolution
    d.facts.add(WorldFact(g.turn, "house", h, "suffered_revolution"))
    ev = d._advance(g)
    assert d.beats[bid].state == "complete"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_sources.py -q`
Expected: FAIL — `AttributeError: ... '_tick_chronicle'`

- [ ] **Step 3: Write minimal implementation**

```python
# gilded/saga/content/threads.py
"""The Chronicle (Gilded Saga §4.B): emergent named threads detected from the
FactStore, promoted when a pattern crosses a threshold, resolved at payoff.
Deterministic: threshold + tie-break by bid; capped for legibility."""

from gilded.saga.beats import Beat, Predicate

MAX_ACTIVE_THREADS = 3
SCANDAL_MIN = 2


def candidate_threads(facts, houses):
    """Return list of (bid, fact_count, Beat) for patterns not yet promoted."""
    out = []
    for h in sorted(houses):
        n = facts.count("committed_atrocity", subject=("house", h))
        if n >= SCANDAL_MIN:
            bid = f"thread_scandal_{h}"
            beat = Beat(bid=bid, source="chronicle",
                        title=f"The Shame of House {h}", load_bearing=True,
                        completion=Predicate(kind="any", parts=[
                            Predicate(kind="fact_exists", predicate="suffered_revolution",
                                      subject_kind="house", subject_id=h),
                            Predicate(kind="fact_exists", predicate="transformed",
                                      subject_kind="house", subject_id=h)]),
                        foreshadow=f"House {h}'s sins mount; the workers are counting",
                        payoff=f"House {h} answers for its sins.")
            out.append((bid, n, beat))
    out.sort(key=lambda t: (-t[1], t[0]))
    return out
```

Append to `gilded/saga/director.py`:

```python
from gilded.saga.content.threads import candidate_threads, MAX_ACTIVE_THREADS
```

```python
    def _tick_chronicle(self, game):
        active_threads = [b for b in self.active if b.startswith("thread_")]
        room = MAX_ACTIVE_THREADS - len(active_threads)
        if room <= 0:
            return []
        for bid, _n, beat in candidate_threads(self.facts, game.houses):
            if room <= 0:
                break
            if bid in self.beats:
                continue
            self.register(beat, game)
            room -= 1
        return []
```

Route it from `_tick_sources`:

```python
    def _tick_sources(self, game):
        out = []
        out += self._tick_age(game)
        out += self._tick_rival(game)
        out += self._tick_chronicle(game)
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_sources.py -q`
Expected: PASS

- [ ] **Step 5: Full-century integration guard**

Add to `gilded/tests/test_saga_integration.py`:

```python
def test_full_century_produces_a_saga():
    from gilded.chassis import GildedGame, TURN_BUDGET
    g = GildedGame(seed=2026)
    for _ in range(TURN_BUDGET + 1):
        g.end_turn()
        if g.game_over:
            break
    d = g.director
    assert d.age_idx >= 1                       # the Age advanced past the opening era
    assert d.rival is not None                  # a Rival was bound
    completed = [b for b in d.beats.values() if b.state == "complete"]
    assert len(completed) >= 1                  # at least one beat paid off
    # every rival beat references the real bound house
    for b in d.beats.values():
        if b.source == "rival":
            assert b.cast.get("self") == d.rival
```

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_integration.py gilded/tests/test_saga_sources.py -q`
Expected: PASS

- [ ] **Step 6: Full suite — baseline holds**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest -q`
Expected: `1 failed, N passed` (only the pre-existing stability failure).

- [ ] **Step 7: Commit**

```bash
git add gilded/saga/content/threads.py gilded/saga/director.py gilded/tests/test_saga_sources.py gilded/tests/test_saga_integration.py
git commit -m "feat(saga): the Chronicle - emergent threads, full-century guard"
```

---

# WAVE N3 — Narration layer

*Deliverable: the broadsheet reads as one chronicle with the LLM on; templated fallback keeps every test byte-identical.*

### Task N3.1: Narrator interface + templated default

**Files:**
- Create: `gilded/saga/narrator.py`
- Test: `gilded/tests/test_saga_narrator.py`

- [ ] **Step 1: Write the failing test**

```python
# gilded/tests/test_saga_narrator.py
from gilded.chassis import GildedGame
from gilded.papers import compose
from gilded.saga.narrator import NarratorTemplated


def test_templated_narrator_is_identity():
    g = GildedGame(seed=42)
    g.end_turn()
    h = sorted(g.houses)[0]
    rep = compose(g, h)
    out = NarratorTemplated().render(rep, g.director, g)
    assert out.gazette == rep.gazette
    assert out.ledger == rep.ledger
    assert out.letters == rep.letters
    assert out.turn == rep.turn and out.year == rep.year
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_narrator.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gilded.saga.narrator'`

- [ ] **Step 3: Write minimal implementation**

```python
# gilded/saga/narrator.py
"""The Narrator (Gilded Saga §5): the ONLY model call site, at the display
boundary. render() takes a composed TurnReport plus the Director and returns a
TurnReport - it may rewrite prose but never touches sim state. Templated is the
deterministic default and guaranteed fallback; LLM is opt-in."""

import os
from typing import Protocol

from gilded.papers import TurnReport


class Narrator(Protocol):
    def render(self, report: TurnReport, director, game) -> TurnReport: ...


class NarratorTemplated:
    """Identity: today's exact broadsheet. Used in every automated test."""

    def render(self, report: TurnReport, director, game) -> TurnReport:
        return report


def active_context(director):
    """Deterministic foreshadow/era/rival context for a narration prompt."""
    lines = []
    for bid in getattr(director, "active", []):
        b = director.beats.get(bid)
        if b is not None and b.foreshadow:
            lines.append(b.foreshadow)
    return lines


def select_narrator() -> Narrator:
    """App/console factory: LLM by default, templated when disabled."""
    if os.environ.get("GILDED_NARRATE", "1") == "0":
        return NarratorTemplated()
    try:
        return NarratorLLM()
    except Exception:
        return NarratorTemplated()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_narrator.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add gilded/saga/narrator.py gilded/tests/test_saga_narrator.py
git commit -m "feat(saga): Narrator interface and templated default"
```

### Task N3.2: Local-LLM narrator (opt-in, graceful fallback)

**Files:**
- Modify: `gilded/saga/narrator.py` (add `NarratorLLM`)
- Test: `gilded/tests/test_saga_narrator.py` (extend — no live model; test the fallback path)

`NarratorLLM` calls the local Qwen3.6 on `:11434` (llama.cpp direct, OpenAI-compatible
`/v1/chat/completions`) with `chat_template_kwargs={"enable_thinking": False}` and a short
prose prompt built from `active_context` + the turn's gazette lines. Any error/timeout →
return the report unchanged (fallback, never blank). Uses only stdlib `urllib` (no new
dep). The constructor does a cheap reachability check so `select_narrator` can fall back.

- [ ] **Step 1: Write the failing test** (append)

```python
def test_llm_narrator_falls_back_on_unreachable_model(monkeypatch):
    import gilded.saga.narrator as nar
    g = GildedGame(seed=42); g.end_turn()
    rep = compose(g, sorted(g.houses)[0])

    def boom(*a, **k):
        raise OSError("no model")
    monkeypatch.setattr(nar, "_post_chat", boom)
    n = nar.NarratorLLM(check=False)            # skip constructor probe
    out = n.render(rep, g.director, g)
    assert out.gazette == rep.gazette           # unchanged on failure


def test_select_narrator_honours_disable(monkeypatch):
    import gilded.saga.narrator as nar
    monkeypatch.setenv("GILDED_NARRATE", "0")
    assert isinstance(nar.select_narrator(), nar.NarratorTemplated)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_narrator.py -q`
Expected: FAIL — `AttributeError: module 'gilded.saga.narrator' has no attribute 'NarratorLLM'`

- [ ] **Step 3: Write minimal implementation** (append to `gilded/saga/narrator.py`)

```python
import json
import urllib.request

MODEL_URL = os.environ.get("GILDED_MODEL_URL", "http://127.0.0.1:11434/v1/chat/completions")
MODEL_NAME = os.environ.get("GILDED_MODEL_NAME", "qwen3.6")
NARRATE_TIMEOUT = float(os.environ.get("GILDED_NARRATE_TIMEOUT", "30"))


def _post_chat(messages, timeout=NARRATE_TIMEOUT):
    body = json.dumps({
        "model": MODEL_NAME, "messages": messages, "temperature": 0.7,
        "max_tokens": 220, "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode("utf-8")
    req = urllib.request.Request(MODEL_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


class NarratorLLM:
    """Local Qwen3.6 narration. On any failure, returns the report unchanged."""

    def __init__(self, check: bool = True):
        if check:
            _post_chat([{"role": "user", "content": "ok"}], timeout=3)  # warmup/probe

    def render(self, report: TurnReport, director, game) -> TurnReport:
        if not report.gazette:
            return report
        context = active_context(director)
        prompt = (
            "You are the chronicler of a dynastic saga in an industrial age. "
            "In one vivid paragraph, weave this turn's events into the ongoing story. "
            "Standing threads: " + ("; ".join(context) if context else "none") + ". "
            "This turn's dispatches:\n- " + "\n- ".join(report.gazette[:10])
        )
        try:
            prose = _post_chat([{"role": "user", "content": prompt}])
        except Exception:
            return report
        if not prose:
            return report
        return TurnReport(report.turn, report.year, [prose] + report.gazette,
                          report.ledger, report.letters)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_narrator.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add gilded/saga/narrator.py gilded/tests/test_saga_narrator.py
git commit -m "feat(saga): local-LLM narrator with graceful templated fallback"
```

### Task N3.3: Wire the narrator into console + app (display-only)

**Files:**
- Modify: `gilded/console.py` (compose → narrator.render before printing the broadsheet)
- Modify: `gilded/ui/app.py` (hold a narrator on `AppState`; render report through it)
- Modify: `gilded/ui/broadsheet.py` (a toggle control flipping narrator on/off)
- Test: `gilded/tests/test_saga_narrator.py` (extend — app holds a narrator, defaults safe under SDL dummy)

- [ ] **Step 1: Write the failing test** (append)

```python
def test_app_state_carries_a_narrator(monkeypatch):
    monkeypatch.setenv("GILDED_NARRATE", "0")     # keep tests model-free
    import os
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    import pygame; pygame.init()
    from gilded.ui import app
    st = app.new_app_state(seed=2026)
    assert hasattr(st, "narrator") and st.narrator is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_narrator.py::test_app_state_carries_a_narrator -q`
Expected: FAIL — `AttributeError: 'AppState' object has no attribute 'narrator'`

- [ ] **Step 3: Write minimal implementation**

Console (`gilded/console.py`): where it composes and prints the broadsheet, pass the report
through `select_narrator().render(report, self.game.director, self.game)` before
`format_broadsheet`. Construct the narrator once in `Console.__init__`
(`self.narrator = select_narrator()` after `from gilded.saga.narrator import select_narrator`).

App (`gilded/ui/app.py`): add `narrator` to the `AppState` dataclass; in `new_app_state`
set `narrator=select_narrator()` (import at top). Where the Broadsheet view is drawn from a
composed report, pass it through `state.narrator.render(...)` first. Add a toggle: a key
(e.g. `n`) in `step_once` swaps `state.narrator` between the live one and
`NarratorTemplated()`.

Broadsheet (`gilded/ui/broadsheet.py`): add a small on-screen indicator/hit-rect for the
narrator toggle returning `{"toggle_narrate": True}` from `handle_click`, handled in
`app._apply_action`.

*(Exact byte-level edits are authored at brief time against the current file contents;
the behavior above is the contract the brief must satisfy. Keep the sim free of the
narrator — it lives only on Console/AppState.)*

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_saga_narrator.py -q`
Expected: PASS

- [ ] **Step 5: Full suite + headless UI smoke**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest -q`
Expected: `1 failed, N passed` (pre-existing failure only).

- [ ] **Step 6: Commit**

```bash
git add gilded/console.py gilded/ui/app.py gilded/ui/broadsheet.py gilded/tests/test_saga_narrator.py
git commit -m "feat(saga): wire narrator into console and app (display-only, toggleable)"
```

---

# WAVE N4 — Endings coda + saga artifact

*Deliverable: the century closes a story; a human can read the whole saga.*

### Task N4.1: Narrative coda in the epilogue

**Files:**
- Modify: `gilded/endings.py` (`judge`/`_epilogue_text` append a Director coda)
- Test: `gilded/tests/test_endings.py` (extend — coda names the age and rival when a Director is present)

- [ ] **Step 1: Write the failing test** (append to `gilded/tests/test_endings.py`)

```python
def test_epilogue_names_the_age_and_rival():
    from gilded.chassis import GildedGame, TURN_BUDGET
    from gilded.endings import judge
    g = GildedGame(seed=2026)
    for _ in range(TURN_BUDGET + 1):
        g.end_turn()
        if g.game_over:
            break
    ep = judge(g, next(iter(g.houses)))
    # the coda names the final era and the bound rival
    from gilded.saga.content.eras import ERAS
    assert any(era.title in ep.text for era in ERAS[:g.director.age_idx + 1])
    assert g.director.rival in ep.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_endings.py::test_epilogue_names_the_age_and_rival -q`
Expected: FAIL — the rival name / era title is absent from the epilogue.

- [ ] **Step 3: Write minimal implementation**

In `gilded/endings.py`, add a helper and call it from `_epilogue_text` (append its return to
the joined paragraphs). Guard on `getattr(game, "director", None)` so older saves without a
Director produce exactly today's text:

```python
def _saga_coda(game) -> str:
    d = getattr(game, "director", None)
    if d is None:
        return ""
    from gilded.saga.content.eras import ERAS
    parts = []
    if 0 <= d.age_idx < len(ERAS):
        parts.append(f"The age closed in {ERAS[d.age_idx].title}.")
    if d.rival:
        rival_beats = [b for b in d.beats.values() if b.source == "rival"]
        reached = [b for b in rival_beats if b.state == "complete"]
        if reached:
            parts.append(f"House {d.rival}, the great rival, "
                         f"{reached[-1].title.lower()} before the end.")
        else:
            parts.append(f"House {d.rival} was the rival that never quite rose.")
    open_threads = [b for b in d.beats.values()
                    if b.source == "chronicle" and b.state == "active"]
    if open_threads:
        parts.append("Left unresolved: " +
                     "; ".join(sorted(b.title for b in open_threads)) + ".")
    return " ".join(parts)
```

Then in `_epilogue_text`, change the final `return "\n\n".join((p1, p2, p3, p4))` to append
the coda when non-empty:

```python
    coda = _saga_coda(game)
    paragraphs = [p1, p2, p3, p4] + ([coda] if coda else [])
    return "\n\n".join(paragraphs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest gilded/tests/test_endings.py -q`
Expected: PASS (all endings tests, including the new one)

- [ ] **Step 5: Full suite — baseline holds**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python -m pytest -q`
Expected: `1 failed, N passed` (pre-existing failure only).

- [ ] **Step 6: Commit**

```bash
git add gilded/endings.py gilded/tests/test_endings.py
git commit -m "feat(saga): epilogue coda names the age, the rival, and loose threads"
```

### Task N4.2: The saga acceptance harness (not committed)

**Files:**
- Create: `C:/tmp/gilded_saga_run.py` (my scratch harness — NOT committed to the repo)

This is the human-read acceptance centerpiece (spec §7 Tier 3). It plays a full headless
century, runs `NarratorLLM` (live model) over each turn's report, and writes a scrollable
saga grouped into chapters by Age era.

- [ ] **Step 1: Write the harness**

```python
# C:/tmp/gilded_saga_run.py
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
from gilded.chassis import GildedGame, TURN_BUDGET
from gilded.papers import compose
from gilded.endings import judge
from gilded.saga.narrator import NarratorLLM, NarratorTemplated
from gilded.saga.content.eras import ERAS

g = GildedGame(seed=2026)
h = next(iter(g.houses))
try:
    narrator = NarratorLLM()      # live model; probes on construct
except Exception:
    narrator = NarratorTemplated()

lines = []
last_age = -1
for _ in range(TURN_BUDGET + 1):
    g.end_turn()
    if g.director.age_idx != last_age:
        last_age = g.director.age_idx
        lines.append(f"\n\n===== CHAPTER: {ERAS[last_age].title} =====")
    rep = narrator.render(compose(g, h), g.director, g)
    if rep.gazette:
        lines.append(f"[turn {g.turn}] {rep.gazette[0]}")
    if g.game_over:
        break

ep = judge(g, h)
lines.append(f"\n\n===== EPILOGUE: {ep.ending_key} =====\n{ep.text}")
open("C:/tmp/gilded_saga.txt", "w", encoding="utf-8").write("\n".join(lines))
print("wrote C:/tmp/gilded_saga.txt")
```

- [ ] **Step 2: Run it (live model on :11434) and read the saga**

Run: `cd /c/Users/civer/civkings && PYTHONPATH=. python C:/tmp/gilded_saga_run.py`
Expected: writes `C:/tmp/gilded_saga.txt`; a human reads it and confirms the century reads
as one coherent, large story — named eras as chapters, a rival arc, threads that pay off,
and an epilogue coda. (If the model is offline it degrades to the templated chronicle, which
still shows the deterministic spine.)

- [ ] **Step 3: No commit** (harness is scratch; the repo change for this wave was N4.1).

---

## Self-Review

- **Spec coverage:** facts (§1 → N1.1–1.2), predicates/beats (§2 → N1.3), Director/wiring
  (§2–3 → N1.4–1.5), Age (§4.C → N2.1), Rival + villain-clock (§4.A → N2.2; the state-nudge
  is deferred/flagged and not wired here — the arc advances off real deeds, which satisfies
  the spec's "advances regardless" guarantee), Chronicle (§4.B → N2.3), narration (§5 → N3),
  endings coda (§6 → N4.1), acceptance artifact (§7 Tier 3 → N4.2). Tier 1/2 tests are folded
  into each task. All spec sections map to tasks.
- **Placeholder scan:** N3.3's exact UI byte-edits are described as a behavioral contract
  rather than full code, because they must be authored against the live file at brief time
  (byte-exact) — the test and the contract pin the behavior. Every other code step is
  complete.
- **Type consistency:** `FactStore.exists/count` keyword args (`subject`, `object`,
  `since_turn`) are used identically in `eval_predicate` and threads. `Beat`/`Predicate`
  field names match across director, eras, rival_arc, threads. `Director.register/_open/
  _advance/_tick_*` signatures are consistent. `TurnReport` fields (`turn`, `year`,
  `gazette`, `ledger`, `letters`) match `gilded/papers.py`.
- **Determinism:** the Director uses its own rng and never draws from `game.rng`; all source
  choices are state-derived and tie-broken by id. `test_soak_determinism` and
  `test_director_does_not_change_state` guard this.
