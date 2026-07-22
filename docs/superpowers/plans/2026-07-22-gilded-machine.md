# The Gilded Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Repo-specific override:** per the spec (§9) and standing project rules, every repo code change lands via a **CynCo mission brief** — the planning assistant never edits game source directly. Each Task below IS one CynCo mission. The "steps" are the brief-author/validate/dispatch/verify cycle defined in the Delivery Protocol section. CynCo commits each mission itself.

**Goal:** Build `gilded/` — a dynasty-management game (fictional 1900, ~70-turn century) on a fresh chassis: organic-province atlas, enterprise economy, front-model war, petition docket with a 3-attention mortal ruler, transplanted character-society layer, headless console first, pygame broadsheet last.

**Architecture:** New top-level package `gilded/` beside the untouched old game. Pure-stdlib deterministic world generator; society modules copied from repo root into `gilded/society/` with import surgery (city → province/enterprise); a lean `chassis.GildedGame` orchestrator; file-bridge console identical in design to `play_console.py`; pygame UI as a client of the sim.

**Tech Stack:** Python 3.14 stdlib (random, math, dataclasses) for the sim; pytest for tests; pygame only inside `gilded/ui/`; CynCo (llama.cpp Qwen3.6-27B) for mission execution.

**Spec:** `docs/superpowers/specs/2026-07-21-gilded-machine-design.md` (source of truth for all mechanics).

---

## Delivery Protocol (applies to every mission)

**Paths.** Briefs and smokes live in `C:/tmp/gilded_briefs/` (create once). Brief = `GN_brief.md` (byte-for-byte file contents, full-file replacements only — new files here, so every brief is "create file X with exactly this content"). Smoke = `GN_smoke.py` (stdlib-only script, exits non-zero on failure). Task JSON = `GN_task.json`.

**Task JSON shape** (matches M86/M87 dispatches):

```json
{
  "missionId": "G1",
  "context": "CivKings repo at C:/Users/civer/civkings. Create the files exactly as the brief specifies, byte-for-byte. Run the smoke and pytest before committing.",
  "prompt": "Follow C:/tmp/gilded_briefs/G1_brief.md exactly.",
  "allowedTools": ["read", "write", "bash"],
  "timeoutMs": 1800000,
  "outcomePath": "C:/tmp/gilded_briefs/G1_outcome.json"
}
```

**Per-mission cycle** (the checklist steps in each Task reference these by name):

1. **Author** — write `GN_brief.md` with the complete file contents (the Contract blocks below are the authoritative interfaces; the brief author expands them into full working code), `GN_smoke.py` with the Smoke block, `GN_task.json`.
2. **Pre-validate** in a scratch worktree:
   ```bash
   git -C /c/Users/civer/civkings worktree add /c/tmp/gilded_wt master
   python /c/tmp/apply_brief.py /c/tmp/gilded_briefs/GN_brief.md /c/tmp/gilded_wt
   cd /c/tmp/gilded_wt && python /c/tmp/gilded_briefs/GN_smoke.py && python -m pytest -q --ignore=test_output.txt 2>&1 | tail -1
   git -C /c/Users/civer/civkings worktree remove --force /c/tmp/gilded_wt
   ```
   Smoke must pass; pytest tail must be `1 failed, N passed` where the 1 failure is only the pre-existing `test_civkings.py::TestTurnStability::test_100_turn_stability`. Fix the brief until clean.
3. **Dispatch** one-shot:
   ```bash
   cd /c/Users/civer/localcode && LOCALCODE_APPROVE_ALL=true LOCALCODE_S5_ENFORCE=false bun engine/main.ts --run-task /c/tmp/gilded_briefs/GN_task.json
   ```
4. **Verify** (all five, every mission):
   - `GN_outcome.json` has `ok: true`.
   - `git -C /c/Users/civer/civkings show --stat HEAD` shows exactly the brief's files.
   - CRLF-normalized byte-diff: apply the brief to a fresh worktree of HEAD~1 and compare every file against HEAD's version — zero differences.
   - Smoke tamper check (`GN_smoke.py` mtime unchanged since authoring) then re-run the smoke against the real repo.
   - `python -m pytest -q --ignore=test_output.txt | tail -1` → `1 failed, N passed` (N = previous N + this mission's new tests).
5. **Log** the mission result (commit hash, N) in `C:/tmp/gilded_briefs/LOG.md`, then proceed to the next mission.

**Test convention.** Every sim mission ships pytest tests in `gilded/tests/test_<module>.py` (plus `gilded/tests/__init__.py` in G1). pytest discovers them automatically with the baseline command. UI missions (G21–G23) ship import-smoke tests only (no display required: set `SDL_VIDEODRIVER=dummy`).

**Determinism rule.** All sim randomness flows from `random.Random(seed)` instances passed explicitly. No module-level `random.*` calls anywhere in `gilded/` outside `ui/`.

---

## File Structure

```
gilded/
  __init__.py                  # empty marker
  world.py                     # G1  Province, Link, Atlas, generate_atlas(seed)
  houses.py                    # G2  House, assign_houses(atlas, seed)
  enterprises.py               # G4  Enterprise, output/dividends/capacity, construction
  directives.py                # G5  five stance dials + conviction friction
  docket.py                    # G12 Petition, generation, attention, unattended resolution
  chassis.py                   # G13 GildedGame turn orchestrator
  papers.py                    # G14 Gazette/Ledger/Letters composition
  fronts.py                    # G15 War, Front, resolution; G16 peace deals
  endings.py                   # G17 hard stops + Judgment of the Age epilogue
  ai.py                        # G18 AI-house ruling loop (dispositions pick rulings)
  console.py                   # G19 file-bridge headless protocol
  __main__.py                  # G19 python -m gilded --console <dir> [--seed N]
  society/                     # transplants (import surgery: city -> province/enterprise)
    __init__.py                # G3
    characters.py              # G3  Character, Secret, Dynasty, generate_child (from simulation.py)
    dispositions.py            # G3  verbatim copy
    character_deepening.py     # G3  verbatim copy
    court.py                   # G3  6 seats (+FOREIGN_SECRETARY, +MARSHAL, -CHIEF_STEWARD)
    event_engine.py            # G3  verbatim copy
    event_chains.py            # G3  verbatim copy
    event_content/             # G3  package copy (core_pools, chains_pack1, chains_pack2)
    shares.py                  # G4  ledger on gilded Enterprise; partition succession
    labor.py                   # G6  dial on Enterprise, Movement on Province
    ideology.py                # G7  tide/legitimacy/revolution over provinces
    realm.py                   # G8  Realm + create_house_realm; population tick
    population.py              # G8  tiered-LOD bulk pass (surgery: no game global)
    schemes.py                 # G9  scheme verbs (surgery: legitimacy/enterprise params)
    marriages.py               # G10 MarriageRegistry class (surgery: house relations)
    relationships.py           # G11 opinions/grievances/plot starts (surgery)
    house_ai.py                # G11 character actions tick (from character_ai.py, surgery)
  tests/                       # pytest per module, G1 onward
  ui/                          # G21-G23 pygame broadsheet client
    __init__.py
    atlas_view.py              # province polygon renderer
    broadsheet.py              # papers + docket screens
    app.py                     # client wiring, python -m gilded (no --console)
```

Old game files at repo root are **never modified** by any mission in this plan.

---

## Shared Contracts (authoritative names — later missions must match these exactly)

```python
# gilded/world.py
TERRAINS = ("coast", "plains", "highlands", "marsh")
ENDOWMENT_KINDS = ("coalfield", "iron", "timber", "farmland", "harbor")

# gilded/houses.py
GREAT_HOUSE_COUNT = 7
MINOR_OWNER = ""                      # provinces with owner "" are minor holders

# gilded/directives.py
DIRECTIVE_KEYS = ("capital", "labor", "expansion", "diplomacy", "war")

# gilded/docket.py
ATTENTION_PER_TURN = 3

# gilded/chassis.py
TURN_BUDGET = 70
YEAR_START = 1900
def year_of(turn): return YEAR_START + round((turn - 1) * 100 / TURN_BUDGET)

# gilded/society/court.py — seat -> attribute (six attributes from characters.py:
# statecraft, command, industry, intrigue, science, resolve)
POSITION_STATS = {
    BOARD_CHAIRMAN: "industry", CHIEF_ENGINEER: "science",
    HEAD_OF_SECURITY: "intrigue", MASTER_OF_PRESS: "statecraft",
    FOREIGN_SECRETARY: "statecraft", MARSHAL: "command",
}

# gilded/docket.py — petition domain -> ruling seat
DOMAIN_SEAT = {
    "capital": BOARD_CHAIRMAN, "labor": HEAD_OF_SECURITY,
    "expansion": CHIEF_ENGINEER, "diplomacy": FOREIGN_SECRETARY,
    "war": MARSHAL, "press": MASTER_OF_PRESS,
}   # domain "family" has no seat: unattended family petitions always fester

# gilded/directives.py — directive -> conviction spectrum consulted for friction
DIRECTIVE_CONVICTION = {
    "capital": "traditionalist_modernist",      # +100 = modernize/invest hard
    "labor": "labor_capital",                   # +100 = break them
    "expansion": "preservationist_extractionist",  # +100 = acquire/extract
    "diplomacy": "nationalist_cosmopolitan",    # +100 = confront
    "war": "militarist_pacifist",               # +100 = escalate
}
```

A `TurnEvent` is the universal record every system emits; `papers.py` composes the report from them:

```python
# gilded/chassis.py
@dataclass
class TurnEvent:
    kind: str            # "war_report", "dividend", "strike", "scandal", "letter", ...
    register: str        # "gazette" | "ledger" | "letters"
    house: str           # whose ledger/letters it belongs to; "" = world news
    text: str            # already-rendered prose (society.event_engine.render output ok)
```

---

## Wave A — World & Money

### Task G1: The Atlas (`gilded/world.py`)

**Files:**
- Create: `gilded/__init__.py`, `gilded/world.py`, `gilded/tests/__init__.py`
- Test: `gilded/tests/test_world.py`

**Contract:**

```python
GRID_W, GRID_H = 96, 96          # generation lattice; cells stored for the renderer
SEED_POINTS = 78                 # Voronoi seeds; ocean carve trims to 50-70 land provinces
PROVINCE_MIN, PROVINCE_MAX = 50, 70
RAIL_HOP_COST, ROAD_HOP_COST = 1.0, 2.0

@dataclass
class Province:
    pid: int
    name: str                    # seeded syllable generator, e.g. "Karvess", "Dunmore Vale"
    terrain: str                 # one of TERRAINS
    endowments: Dict[str, int]   # kind -> richness 1..3 (absent key = none)
    cells: List[Tuple[int, int]] # lattice cells (UI derives polygon later)
    center: Tuple[float, float]  # mean cell position
    neighbors: Set[int]
    owner: str = MINOR_OWNER     # house name
    population: int = 0          # workforce pool, thousands
    development: int = 1
    unrest: float = 0.0
    garrison: int = 0
    movement: object = None      # society.labor.Movement (attached in G6)

@dataclass
class Link:
    a: int                       # a < b always
    b: int
    rail: bool = False

class Atlas:
    provinces: Dict[int, Province]
    links: Dict[Tuple[int, int], Link]        # key (min, max)
    def link(self, a, b) -> Optional[Link]
    def distance(self, a, b) -> float         # Dijkstra over links, rail/road hop costs
    def neighbors(self, pid) -> List[Province]

def generate_atlas(seed: int) -> Atlas
```

Generation (pure stdlib, `rng = random.Random(seed)`; retry with `seed*1000+i` until land count in [50, 70], max 50 retries then raise):
1. Sample SEED_POINTS points on the lattice; assign every cell to nearest seed (discrete Voronoi).
2. Ocean mask: cell is ocean when `dist_from_center / max_radius + 0.25*noise(rng) > 0.82` (noise = per-seed-point uniform, so whole regions sink together at the fringe). Regions with >50% ocean cells are removed; their land cells become ocean.
3. Terrain: `coast` if any cell borders ocean; else `highlands` if region center in the top-third of distance-from-coast; `marsh` with 8% chance for coast-adjacent plains; else `plains`.
4. Endowments (rng-weighted): coalfield/iron favor highlands, timber highlands+plains, farmland plains, harbor coast only. Each province rolls 0–2 kinds, richness 1–3. Post-pass guarantees global minimums: ≥6 coalfield, ≥6 iron, ≥8 farmland, ≥4 harbor (upgrade random eligible provinces).
5. Population by terrain: plains 80–160, coast 60–140, highlands 30–90, marsh 20–50 (thousands), +25% if farmland present.
6. Adjacency from lattice cell borders between regions; every adjacent land pair gets a road Link.

**Smoke (`G1_smoke.py`) and the same asserts as pytest tests:**

```python
from gilded.world import generate_atlas, PROVINCE_MIN, PROVINCE_MAX
a1, a2 = generate_atlas(42), generate_atlas(42)
assert [p.name for p in a1.provinces.values()] == [p.name for p in a2.provinces.values()]  # deterministic
assert PROVINCE_MIN <= len(a1.provinces) <= PROVINCE_MAX
for p in a1.provinces.values():
    for n in p.neighbors: assert p.pid in a1.provinces[n].neighbors      # symmetric
    assert p.population > 0 and p.terrain in ("coast","plains","highlands","marsh")
kinds = [k for p in a1.provinces.values() for k in p.endowments]
assert kinds.count("coalfield") >= 6 and kinds.count("iron") >= 6
assert kinds.count("farmland") >= 8 and kinds.count("harbor") >= 4
a3 = generate_atlas(7)
assert [p.name for p in a3.provinces.values()] != [p.name for p in a1.provinces.values()]  # seeds differ
d = a1.distance(min(a1.provinces), max(a1.provinces)); assert d > 0
print("G1 smoke OK")
```

**Steps:**
- [ ] Author `C:/tmp/gilded_briefs/G1_brief.md` (full contents of all 4 files), `G1_smoke.py`, `G1_task.json`
- [ ] Pre-validate in scratch worktree (protocol step 2); pytest tail `1 failed, N passed`
- [ ] Dispatch (protocol step 3)
- [ ] Verify all five checks (protocol step 4)
- [ ] Log to `C:/tmp/gilded_briefs/LOG.md`

### Task G2: Great Houses (`gilded/houses.py`)

**Files:**
- Create: `gilded/houses.py`
- Test: `gilded/tests/test_houses.py`

**Contract:**

```python
HOUSE_NAMES = ["Vantrell", "Karsgate", "Mordaine", "Ashworth", "Ferrenholt",
               "Duval-Corse", "Brandtner", "Ostreval"]     # first GREAT_HOUSE_COUNT used
STARTING_TREASURY = 2000.0
CLUSTER_MIN, CLUSTER_MAX = 5, 7

@dataclass
class House:
    name: str
    capital: int                      # pid
    treasury: float = STARTING_TREASURY
    is_player: bool = False
    legitimacy: float = 50.0
    prestige: float = 0.0
    at_war_with: Set[str] = field(default_factory=set)
    truces: Dict[str, int] = field(default_factory=dict)   # house -> expiry turn
    relations: Dict[str, int] = field(default_factory=dict) # house -> -100..100
    # realm (society characters) attached in G8; directives attached in G5 via chassis

def assign_houses(atlas: Atlas, seed: int) -> Dict[str, House]
```

Assignment: greedy farthest-point pick of GREAT_HOUSE_COUNT capitals among land provinces; BFS-grow each cluster to 5–7 contiguous provinces (round-robin so growth is fair); set `province.owner`; everything left keeps `owner == MINOR_OWNER`. Relations init 0; capital province gets `garrison = 2`, others 1, minors 1.

**Smoke:**

```python
from gilded.world import generate_atlas
from gilded.houses import assign_houses, GREAT_HOUSE_COUNT
atlas = generate_atlas(42); houses = assign_houses(atlas, 42)
assert len(houses) == GREAT_HOUSE_COUNT
for h in houses.values():
    owned = [p for p in atlas.provinces.values() if p.owner == h.name]
    assert 5 <= len(owned) <= 7 and atlas.provinces[h.capital].owner == h.name
    # contiguity: BFS within owned set reaches all owned
minors = [p for p in atlas.provinces.values() if p.owner == ""]
assert len(minors) >= 5
h2 = assign_houses(generate_atlas(42), 42)
assert {h.capital for h in houses.values()} == {h.capital for h in h2.values()}  # deterministic
print("G2 smoke OK")
```

**Steps:**
- [ ] Author `G2_brief.md`, `G2_smoke.py`, `G2_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G3: Society Transplant I — the self-contained organs (`gilded/society/`)

**Files:**
- Create: `gilded/society/__init__.py`, `gilded/society/characters.py`, `gilded/society/dispositions.py`, `gilded/society/character_deepening.py`, `gilded/society/court.py`, `gilded/society/event_engine.py`, `gilded/society/event_chains.py`, `gilded/society/event_content/__init__.py`, `gilded/society/event_content/core_pools.py`, `gilded/society/event_content/chains_pack1.py`, `gilded/society/event_content/chains_pack2.py`
- Test: `gilded/tests/test_society_core.py`
- Sources (read-only): repo root `dispositions.py`, `character_deepening.py`, `court.py`, `event_engine.py`, `event_chains.py`, `event_content/*`, `simulation.py`

**Contract:**
- `dispositions.py`, `character_deepening.py`, `event_engine.py`, `event_chains.py`, `event_content/*`: verbatim copies except intra-package imports become relative-style package imports (`from gilded.society.dispositions import ...`; `event_engine` pulls pools from `gilded.society.event_content.core_pools`).
- `characters.py`: extract from root `simulation.py` the classes/functions `Character`, `Secret`, `Dynasty`, `generate_child`, `normalize_stats`, `ATTRIBUTES`, `STAT_COMPAT` and every private helper they call — byte-identical bodies, imports repointed at `gilded.society.dispositions` / `character_deepening`. Nothing 4X (no City/unit references exist in these; verify while extracting).
- `court.py`: copy, then replace the enum with the six Gilded seats and stats per Shared Contracts:
  `BOARD_CHAIRMAN, CHIEF_ENGINEER, HEAD_OF_SECURITY, MASTER_OF_PRESS, FOREIGN_SECRETARY, MARSHAL` (CHIEF_STEWARD removed). All Court methods unchanged.

**Smoke:**

```python
from gilded.society.characters import Character, generate_child, ATTRIBUTES
from gilded.society.court import Court, CourtPosition
from gilded.society.dispositions import initial_dispositions, apply_drift, PAIRS
from gilded.society.event_engine import Situation, render
import random
random.seed(1)
a = Character(name="Elias Vantrell", stats={}, traits=[], age=40, gender="Male")
b = Character(name="Mara Vantrell", stats={}, traits=[], age=36, gender="Female")
kid = generate_child("Corin Vantrell", a, b)
assert kid.age == 0 and set(ATTRIBUTES) <= set(kid.base_stats)
assert len(PAIRS) == 30 and len(a.dispositions) == 30
court = Court(a); assert len(CourtPosition) == 6
assert "FOREIGN_SECRETARY" in CourtPosition.__members__ and "MARSHAL" in CourtPosition.__members__
assert "CHIEF_STEWARD" not in CourtPosition.__members__
txt = render(Situation("death", {"target": b}, data={"house": "Vantrell"}))
assert isinstance(txt, str) and len(txt) > 0
apply_drift(a, "labor_capital", 10, "test")
print("G3 smoke OK")
```

**Steps:**
- [ ] Author `G3_brief.md` (brief includes the exact extracted `characters.py` content, produced by reading root `simulation.py` fresh at authoring time), `G3_smoke.py`, `G3_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G4: Enterprises & Shares (`gilded/enterprises.py`, `gilded/society/shares.py`)

**Files:**
- Create: `gilded/enterprises.py`, `gilded/society/shares.py`
- Test: `gilded/tests/test_enterprises.py`
- Sources (read-only): repo root `shares.py`, `labor.py` (for multiplier formulas)

**Contract:**

```python
# gilded/enterprises.py
ENTERPRISE_TYPES = {
    #  type        needs-endowment  capacity  base_gold  found_cost
    "colliery":   ("coalfield",     "coal",    30.0,      400.0),
    "ironworks":  ("iron",          "steel",   40.0,      600.0),
    "mill":       ("timber",        "freight", 25.0,      300.0),
    "estate":     ("farmland",      None,      20.0,      250.0),
    "rail_co":    ("harbor",        "freight", 35.0,      500.0),
    "bank":       (None,            None,      50.0,      800.0),
}
WORKFORCE_PER_TIER = 10          # thousands employed per capital tier
TIER_MAX = 5
EXPAND_COST = {2: 300.0, 3: 500.0, 4: 800.0, 5: 1200.0}   # gold to reach tier
EXPAND_TURNS = {2: 2, 3: 2, 4: 3, 5: 3}

@dataclass
class Enterprise:
    eid: int
    kind: str                      # key of ENTERPRISE_TYPES
    name: str                      # e.g. "Karvess Colliery"
    house: str
    province: int                  # pid
    tier: int = 1
    extraction_dial: float = 50.0  # society.labor DIAL range 0..100
    director_id: str = ""          # Character.id
    ledger: Dict[str, float] = field(default_factory=dict)  # char_id -> pct, sums 100
    under_construction: int = 0    # turns remaining (founding or expansion)
    target_tier: int = 1
    def workforce(self) -> int: return self.tier * WORKFORCE_PER_TIER
    def assign_share(self, char_id, pct); def ledger_total(self) -> float

def output_gold(ent, province, director, tech_mod=1.0) -> float
    # base_gold * richness * tier * (workforce staffed? min(1, prov.population/needed))
    #   * labor.production_multiplier(dial) * (1 + director.get_effective_stat("industry")/40) * tech_mod
def capacity_out(ent, province) -> Tuple[Optional[str], float]   # (kind, tier * richness) or (None, 0)
def found_enterprise(kind, house, province, eid, rng) -> Optional[Enterprise]
    # None if endowment missing; under_construction = EXPAND_TURNS[2], tier starts 1 when done
def tick_construction(ent) -> bool                               # True when it completes this turn
```

```python
# gilded/society/shares.py — port of root shares.py onto gilded Enterprise
def initial_ledger(ent, realm)          # ruler 60%, living dynasty kin split 40% evenly
def pay_dividends(realm, enterprises, provinces, tech_mod=1.0) -> Tuple[float, List[str]]
    # per ent: gold = output_gold(...) * labor.dividend_multiplier(ent.extraction_dial)
    # split by ledger to living characters' gold_reserve; house share (ruler share) returned
def partition_shares(realm, enterprises, old_ruler, new_ruler, law) -> List[str]  # body ported verbatim
def transfer_shares(ent, from_id, to_id, pct) -> float                            # ported verbatim
def extort_shares(enterprises, from_id, to_id, pct) -> float                      # ported, takes list
def house_stake(enterprises, char_id) -> float                                    # ported, takes list
def seize_enterprises(enterprises, from_house, to_house, to_realm) -> int         # re-register house + ledger to victors
```

**Smoke:**

```python
import random
from gilded.world import generate_atlas
from gilded.houses import assign_houses
from gilded.enterprises import Enterprise, found_enterprise, output_gold, capacity_out, tick_construction, ENTERPRISE_TYPES
from gilded.society import shares
from gilded.society.characters import Character
atlas = generate_atlas(42); houses = assign_houses(atlas, 42)
prov = next(p for p in atlas.provinces.values() if "coalfield" in p.endowments)
ent = found_enterprise("colliery", "Vantrell", prov, 1, random.Random(1))
assert ent and ent.under_construction > 0
while not tick_construction(ent): pass
d = Character(name="Dir", stats={"industry": 12}, traits=[], age=40, gender="Male")
g = output_gold(ent, prov, d); assert g > 0
kind, amt = capacity_out(ent, prov); assert kind == "coal" and amt >= 1
ent.ledger = {"a": 60.0, "b": 40.0}
assert abs(shares.transfer_shares(ent, "a", "b", 10.0) - 10.0) < 1e-6
assert abs(ent.ledger["a"] - 50.0) < 1e-6 and abs(ent.ledger_total() - 100.0) < 1e-6
assert found_enterprise("colliery", "X", next(p for p in atlas.provinces.values() if "coalfield" not in p.endowments), 2, random.Random(1)) is None
print("G4 smoke OK")
```

**Steps:**
- [ ] Author `G4_brief.md` (read root `shares.py` fresh; port bodies with the new signatures), `G4_smoke.py`, `G4_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G5: Standing Directives (`gilded/directives.py`)

**Files:**
- Create: `gilded/directives.py`
- Test: `gilded/tests/test_directives.py`

**Contract:**

```python
FRICTION_THRESHOLD = 60.0     # |stance - conviction| beyond this generates friction
FRICTION_STRESS = 8           # stress per turn on a conflicted executor
RESIGN_FRICTION_TURNS = 4     # consecutive conflicted turns before resignation risk
RESIGN_CHANCE = 0.25

@dataclass
class Directives:
    stances: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in DIRECTIVE_KEYS})
    friction_turns: Dict[str, int] = field(default_factory=dict)   # key -> consecutive turns
    def set_stance(self, key, value)          # clamp -100..100; resets friction counter
def friction(stance: int, conviction: float) -> float
    # conviction = executor.dispositions[DIRECTIVE_CONVICTION[key]], looked up by caller;
    # returns max(0, abs(stance - conviction) - FRICTION_THRESHOLD)
def tick_friction(directives, seats: Dict[str, object], rng) -> List[Tuple[str, str]]
    # seats: directive key -> seated Character (or None). Applies FRICTION_STRESS via
    # char.add_stress, counts consecutive turns, rolls resignation after
    # RESIGN_FRICTION_TURNS. Returns [(key, "stress"|"resigned"), ...]
```

**Smoke:**

```python
import random
from gilded.directives import Directives, friction, tick_friction, DIRECTIVE_KEYS
from gilded.society.characters import Character
d = Directives(); assert set(d.stances) == set(DIRECTIVE_KEYS) and all(v == 0 for v in d.stances.values())
d.set_stance("labor", 250); assert d.stances["labor"] == 100
c = Character(name="Sec", stats={}, traits=[], age=45, gender="Male")
c.dispositions["labor_capital"] = -80.0
assert friction(100, -80.0) > 0 and friction(0, -80.0) > 0 and friction(-60, -80.0) == 0
before = c.stress
events = tick_friction(d, {"labor": c}, random.Random(1))
assert c.stress > before and any(k == "labor" for k, _ in events)
print("G5 smoke OK")
```

Note: `friction(stance, conviction_value)` takes the numeric conviction (caller looks it up); the smoke reflects the final signature — keep it `friction(stance: int, conviction: float) -> float`.

**Steps:**
- [ ] Author `G5_brief.md`, `G5_smoke.py`, `G5_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

---

## Wave B — People & Trouble

### Task G6: Labor (`gilded/society/labor.py`)

**Files:**
- Create: `gilded/society/labor.py`
- Test: `gilded/tests/test_labor.py`
- Sources (read-only): repo root `labor.py`

**Contract:** Port root `labor.py` with this surgery — the dial lives on `Enterprise.extraction_dial`; unrest and `Movement` live on `Province`. Formula bodies (`production_multiplier`, `dividend_multiplier`, `unrest_gain`, `accident_chance`, `dial_from_ruler`, all constants) are byte-identical to root.

```python
DIAL_MIN, DIAL_MAX, DIAL_DEFAULT = 0.0, 100.0, 50.0     # unchanged
class Movement:            # ported; field city_name -> province_pid: int
def tick_extraction(ent, province, realm, rng, tide) -> List[str]
    # unrest_gain(ent.extraction_dial) accrues to province.unrest (scaled by
    # tide.movement_multiplier()); accident roll per enterprise
def resolve_accident(ent, province, realm, rng, tide) -> List[str]
    # province.population -= 1; director maim via realm character lookup by ent.director_id
def tick_movement(province, realm, rng) -> List[str]      # union -> strike; strike halts
    # (chassis multiplies striking provinces' enterprise output by STRIKE_OUTPUT_MULT)
STRIKE_OUTPUT_MULT = 0.25
def martyr_leader(mv, province, provinces, realm, rng, tide) -> List[str]
    # spread to nearest same-owner province by atlas center distance (caller passes list)
def buy_off_leader(mv, province) -> List[str]
def cover_up(ruler, province, tide) -> List[str]
```

**Smoke** (G6 precedes G7, so the tide is a stub — labor takes any object with the two methods):

```python
import random
class StubTide:
    def movement_multiplier(self): return 1.0
    def record_atrocity(self, kind, house): pass
from gilded.world import generate_atlas
from gilded.enterprises import Enterprise
from gilded.society import labor
from gilded.society.characters import Character
atlas = generate_atlas(42); prov = next(iter(atlas.provinces.values()))
ent = Enterprise(eid=1, kind="colliery", name="Test Colliery", house="Vantrell", province=prov.pid)
ent.extraction_dial = 95.0
assert labor.production_multiplier(95.0) > labor.production_multiplier(20.0)
assert labor.accident_chance(30.0) == 0.0 and labor.accident_chance(95.0) > 0.0
class R: characters = []; ruler = None; civ_name = "Vantrell"
r = R(); rng = random.Random(3); tide = StubTide()
u0 = prov.unrest
for _ in range(12): labor.tick_extraction(ent, prov, r, rng, tide)
assert prov.unrest > u0
prov.unrest = 100.0
r.characters = [Character(name="W", stats={}, traits=[], age=30, gender="Male")]
msgs = labor.tick_movement(prov, r, rng)
assert prov.movement is not None
print("G6 smoke OK")
```

**Steps:**
- [ ] Author `G6_brief.md` (read root `labor.py` fresh; keep formula bodies byte-identical), `G6_smoke.py`, `G6_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G7: Ideology (`gilded/society/ideology.py`)

**Files:**
- Create: `gilded/society/ideology.py`
- Test: `gilded/tests/test_ideology.py`
- Sources (read-only): repo root `ideology.py`

**Contract:** Port root `ideology.py`. `IdeologicalTide`, `tick_legitimacy`, `record_scandal` are byte-identical. Surgery on the province-facing functions:

```python
REVOLUTION_OWNER = "The Commune"
def revolution_brewing(legitimacy: float, provinces: List[Province]) -> bool
    # legitimacy <= threshold AND any province.movement striking with militancy over bar
def trigger_revolution(house: str, provinces, enterprises) -> Tuple[List[str], List[int]]
    # organized provinces flip owner to REVOLUTION_OWNER; their enterprises' dials to
    # DIAL_DEFAULT and ledgers cleared; returns (messages, flipped_pids)
def can_transform(ruler) -> bool                              # byte-identical
def transform_house(house, ruler, provinces, enterprises, realm, legitimacy) -> Tuple[List[str], float]
    # concede: all house enterprises' ledgers redistributed 100% to "workers" sentinel id
    # "COLLECTIVE", dials to DIAL_DEFAULT, unrest zeroed; returns (messages, new_legitimacy)
```

Happiness input to `tick_legitimacy` becomes **house contentment** = `50 - mean(province.unrest for owned provinces)`, computed by the caller (chassis) — the function signature is unchanged.

**Smoke:**

```python
from gilded.society.ideology import IdeologicalTide, tick_legitimacy, revolution_brewing, trigger_revolution, can_transform, REVOLUTION_OWNER
from gilded.world import generate_atlas
from gilded.houses import assign_houses
from gilded.society.labor import Movement
tide = IdeologicalTide()
for _ in range(10): tide.tick()
assert tide.level > 0 and tide.phase() in ("reformist", "socialist", "revolutionary")
tide.record_atrocity("massacre", "Vantrell")
assert tide.movement_multiplier() >= 1.0 and tide.drift_multiplier() >= 1.0
l1 = tick_legitimacy(50.0, -30.0, tide, 0.0); assert l1 < 50.0
atlas = generate_atlas(42); houses = assign_houses(atlas, 42)
hname = next(iter(houses)); owned = [p for p in atlas.provinces.values() if p.owner == hname]
assert not revolution_brewing(80.0, owned)
mv = Movement(province_pid=owned[0].pid, leader=None); mv.state = "striking"; mv.militancy = 90.0
owned[0].movement = mv
assert revolution_brewing(0.0, owned)
msgs, flipped = trigger_revolution(hname, owned, [])
assert owned[0].pid in flipped and owned[0].owner == REVOLUTION_OWNER
print("G7 smoke OK")
```

**Steps:**
- [ ] Author `G7_brief.md` (read root `ideology.py` fresh), `G7_smoke.py`, `G7_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G8: Realms & Population (`gilded/society/realm.py`, `gilded/society/population.py`)

**Files:**
- Create: `gilded/society/realm.py`, `gilded/society/population.py`
- Test: `gilded/tests/test_realm.py`
- Sources (read-only): repo root `realms.py`, `population.py`

**Contract:**

```python
# gilded/society/realm.py — ported from root realms.py, no game/civ objects
@dataclass
class Realm:
    house_name: str
    ruler: Character
    dynasty: Dynasty
    court: Court
    characters: List[Character] = field(default_factory=list)
    promoted_ids: set = field(default_factory=set)
def create_house_realm(house_name: str, rng: random.Random) -> Realm
    # port of create_realm: ruler 28-45, spouse, 1-2 children, 40-60 courtiers,
    # all six seats staffed by get_best_candidate. Names from the root name pools
    # plus surname = house_name ("Elias Vantrell"). Uses rng, not module random —
    # wrap: temporarily seed module-level via local Random for jitter helpers, or
    # thread rng through the ported helpers (thread it; helpers take rng).
def tick_directors(realm, enterprises, rng) -> List[str]
    # port of root tick_directors: vacant ent.director_id filled by best-industry
    # non-seated adult; directors gain focus progress
def tick_loyalty(realm, enterprises, rng) -> List[str]      # port; disloyalty from
    # low opinion of ruler; returns messages
```

```python
# gilded/society/population.py — port of root population.py
def bulk_pass(realm, turn: int, rng) -> Tuple[List[str], List[Character]]
    # aging/mortality/births; RETURNS new children instead of appending to game.characters
def relevance_set(realm, scheme_agent_ids: Set[str]) -> Set[str]
def promote(realm, char)
```

**Smoke:**

```python
import random
from gilded.society.realm import Realm, create_house_realm, tick_directors
from gilded.society.population import bulk_pass, relevance_set
from gilded.society.court import CourtPosition
from gilded.enterprises import Enterprise
rng = random.Random(11)
realm = create_house_realm("Vantrell", rng)
assert realm.ruler.is_alive and 28 <= realm.ruler.age <= 45
assert len(realm.characters) >= 40
assert sum(1 for p in CourtPosition if realm.court.positions[p]) == 6
ent = Enterprise(eid=1, kind="bank", name="Vantrell Trust", house="Vantrell", province=0)
tick_directors(realm, [ent], rng)
assert ent.director_id != ""
msgs, born = bulk_pass(realm, 5, rng)
assert isinstance(born, list)
rs = relevance_set(realm, set()); assert realm.ruler.id in rs
r2 = create_house_realm("Vantrell", random.Random(11))
assert r2.ruler.name == realm.ruler.name          # rng-threaded determinism
print("G8 smoke OK")
```

**Steps:**
- [ ] Author `G8_brief.md` (read root `realms.py`/`population.py` fresh), `G8_smoke.py`, `G8_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G9: Schemes (`gilded/society/schemes.py`)

**Files:**
- Create: `gilded/society/schemes.py`
- Test: `gilded/tests/test_schemes.py`
- Sources (read-only): repo root `schemes.py`

**Contract:** Port root `schemes.py` — every verb survives. Surgery replaces game-global touches with parameters:

```python
class SchemeManager:
    def start_scheme(self, agent, target, scheme_type, target_house) -> Scheme
    def scheming(self, char) -> bool
    def advance_all(self, realms: Dict[str, Realm], legitimacy: Dict[str, float], rng) -> List[str]
def expose_secret(publisher, secret, subject, house, legitimacy, tide) -> List[str]
def blackmail(agent, secret, victim, realm, enterprises, rng) -> List[str]   # extort_shares over list
def sabotage(agent, ent, province, victim_realm, rng, tide) -> List[str]     # calls labor.resolve_accident
def sway(agent, target) -> List[str]                                          # verbatim
def seduce(agent, target, rng) -> List[str]
def compromise(agent, target, rng) -> List[str]
class Takeover:   # advance(realms, enterprises, rng) — buys shares from disloyal holders
class Conspiracy: # advance(realms, rng) — betrayal risk + staged accident, verbatim logic
def start_conspiracy(mastermind, target, target_house, conspirators) -> Optional[Conspiracy]
```

Ruler-death consequences (`game.rulers` mutation in root) become return values: `advance_all` returns messages AND appends `("ruler_dead", house)` markers to a `self.pending_successions: List[str]` list the chassis consumes.

**Smoke:**

```python
import random
from gilded.society.schemes import SchemeManager, sway, start_conspiracy
from gilded.society.realm import create_house_realm
rng = random.Random(5)
ra, rb = create_house_realm("Vantrell", rng), create_house_realm("Karsgate", rng)
mgr = SchemeManager()
s = mgr.start_scheme(ra.characters[10], rb.ruler, "assassination", "Karsgate")
assert mgr.scheming(ra.characters[10])
legit = {"Vantrell": 50.0, "Karsgate": 50.0}
for _ in range(30): mgr.advance_all({"Vantrell": ra, "Karsgate": rb}, legit, rng)
msgs = sway(ra.ruler, rb.ruler); assert isinstance(msgs, list)
c = start_conspiracy(ra.ruler, rb.ruler, "Karsgate", ra.characters[5:9])
print("G9 smoke OK")
```

**Steps:**
- [ ] Author `G9_brief.md` (read root `schemes.py` fresh; verb bodies byte-identical modulo the parameter surgery), `G9_smoke.py`, `G9_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G10: Marriages (`gilded/society/marriages.py`)

**Files:**
- Create: `gilded/society/marriages.py`
- Test: `gilded/tests/test_marriages.py`
- Sources (read-only): repo root `marriages.py`

**Contract:** Port root `marriages.py` with module-level state encapsulated:

```python
class MarriageRegistry:
    marriages: List[tuple]                  # (char_a_id, house_a, char_b_id, house_b)
    contracts: Dict[tuple, MarriageContract]
    married_ids: set
    wedding_count: int
    def tick(self, realms, houses, enterprises_by_house, rng) -> List[str]
        # ambient arrangement (skips pairs at war via houses[x].at_war_with) + blood ties
        # (existing marriages nudge houses[a].relations[b] upward)
    def arrange_match_between(self, house_a, house_b, realms, houses, enterprises_by_house, rng) -> Optional[str]
@dataclass
class MarriageContract:  # verbatim: alliance, dowry_gold, dowry_shares_pct, matrilineal, board_seat
def bloodline_quality(char) -> float        # verbatim
def house_power(enterprises: List[Enterprise]) -> float   # sum of base_gold * tier
def asking_price(char, enterprises) -> float
```

`game.diplomacy_manager` calls are replaced by `houses[x].relations` / `at_war_with` reads-writes. Character transfer between realms is unchanged (append to new realm.characters, dynasty add).

**Smoke:**

```python
import random
from gilded.society.marriages import MarriageRegistry, bloodline_quality, asking_price
from gilded.society.realm import create_house_realm
from gilded.houses import House
rng = random.Random(9)
ra, rb = create_house_realm("Vantrell", rng), create_house_realm("Karsgate", rng)
houses = {"Vantrell": House(name="Vantrell", capital=0), "Karsgate": House(name="Karsgate", capital=1)}
reg = MarriageRegistry()
assert bloodline_quality(ra.ruler) == bloodline_quality(ra.ruler)
assert asking_price(ra.ruler, []) >= 0
msg = reg.arrange_match_between("Vantrell", "Karsgate", {"Vantrell": ra, "Karsgate": rb}, houses, {"Vantrell": [], "Karsgate": []}, rng)
if msg: assert reg.wedding_count == 1 and len(reg.married_ids) == 2
for _ in range(20): reg.tick({"Vantrell": ra, "Karsgate": rb}, houses, {"Vantrell": [], "Karsgate": []}, rng)
print("G10 smoke OK")
```

**Steps:**
- [ ] Author `G10_brief.md` (read root `marriages.py` fresh), `G10_smoke.py`, `G10_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G11: Relationships & Character Actions (`gilded/society/relationships.py`, `gilded/society/house_ai.py`)

**Files:**
- Create: `gilded/society/relationships.py`, `gilded/society/house_ai.py`
- Test: `gilded/tests/test_relationships.py`
- Sources (read-only): repo root `relationships.py`, `character_ai.py`

**Contract:**

```python
# gilded/society/relationships.py — port; opinion matrix stays module state with
# get_state()/set_state() for saves; ALL player-civ special cases removed
def opinion_of(a, b) -> int; def modify_opinion(a, b, delta); def get_relation(a, b) -> str
def tick_relationships(realms, scheme_mgr, turn, rng) -> List[str]
    # succession grievances, ambient decay, secret discovery, plot starts (via scheme_mgr)

# gilded/society/house_ai.py — port of character_ai.py tick, decoupled from game
def tick_realm(realm, turn, rng, tide, succession_law="PRIMOGENITURE") -> Tuple[List[str], List[Character]]
    # phases verbatim: bulk pass (via population), succession on ruler death
    # (partition_shares is called by chassis, which owns enterprises), births,
    # guardians, court replenishment, tier-1 actions. Returns (messages, new_chars).
```

**Smoke:**

```python
import random
from gilded.society.relationships import modify_opinion, opinion_of, tick_relationships
from gilded.society.schemes import SchemeManager
from gilded.society.house_ai import tick_realm
from gilded.society.realm import create_house_realm
rng = random.Random(13)
ra = create_house_realm("Vantrell", rng); rb = create_house_realm("Karsgate", rng)
a, b = ra.characters[0], ra.characters[1]
modify_opinion(a, b, -50); assert opinion_of(a, b) <= -50
mgr = SchemeManager()
msgs = tick_relationships({"Vantrell": ra, "Karsgate": rb}, mgr, 3, rng)
class StubTide:
    def drift_multiplier(self): return 1.0
    def movement_multiplier(self): return 1.0
before = len(ra.characters)
for t in range(1, 15):
    out, born = tick_realm(ra, t, rng, StubTide())
    ra.characters.extend(born)
assert ra.ruler.is_alive or True     # succession may have replaced the ruler
assert all(c.age >= 0 for c in ra.characters)
print("G11 smoke OK")
```

**Steps:**
- [ ] Author `G11_brief.md` (read root `relationships.py` + `character_ai.py` fresh), `G11_smoke.py`, `G11_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

---

## Wave C — The Turn

### Task G12: The Docket (`gilded/docket.py`)

**Files:**
- Create: `gilded/docket.py`
- Test: `gilded/tests/test_docket.py`

**Contract:**

```python
FESTER_TURNS = 2                  # unattended + no seat -> auto-resolution after this

@dataclass
class PetitionOption:
    key: str                      # "grant", "refuse", "compromise", ...
    text: str
    stance_bias: int              # -100..100; used by unattended resolution & AI
    apply: Callable[["RulingContext"], List[str]]   # returns TurnEvent texts

@dataclass
class Petition:
    pid: int
    kind: str                     # generator id, e.g. "capital_request"
    domain: str                   # key of DOMAIN_SEAT or "family"
    house: str
    text: str                     # rendered situation prose
    actors: Dict[str, object]     # slot -> Character
    options: List[PetitionOption]
    turns_waiting: int = 0
    escalated: bool = False

@dataclass
class RulingContext:              # everything an option's apply() may touch
    game: object                  # GildedGame (chassis) — single handle, YAGNI
    house: str
    executor: object              # Character actually carrying it out
    rng: random.Random

def generate_petitions(game, house_name: str) -> List[Petition]
    # Generators, each a small function returning Optional[Petition]:
    #  capital_request  — a Director with tier<5 enterprise begs expansion capital (capital)
    #  seat_vacancy     — an empty council seat: candidates as options (its own domain)
    #  union_ultimatum  — striking province movement demands dial cut / buy-off / break (labor)
    #  betrothal_offer  — another house proposes a match w/ contract terms (diplomacy)
    #  heir_demand      — adult heir demands a seat or capital (family)
    #  disaster_inquiry — accident last turn: cover up / compensate / prosecute director (press)
    #  rail_proposal    — Chief Engineer proposes a rail link upgrade (expansion)
    #  war_council      — active front crisis: reinforce / hold / seek terms (war)  [wired in G16]
    # Cap: at most 6 petitions per house per turn, priority by domain urgency.

def rule(game, petition, option_key, executor) -> List[str]
    # costs 1 attention (chassis tracks); executor competence and dispositions modulate:
    # success roll = 0.5 + executor.get_effective_stat(seat stat)/40 (clamped .2-.95);
    # failed rolls apply the option at half effect and add stress; convictions vs
    # stance_bias -> contradiction_stress + drift via society.dispositions

def resolve_unattended(game, house_name, petitions) -> List[str]
    # for each unruled petition: seated holder of DOMAIN_SEAT[domain] picks the option
    # whose stance_bias is closest to (directive stance + holder conviction)/2, executes
    # via rule() with themselves as executor; no seat/domain "family" -> turns_waiting += 1,
    # after FESTER_TURNS apply the option with lowest stance_bias at half effect ("festered")

INITIATIVES = {           # proactive verbs, each costs 1 attention; routed through a person
    "propose_marriage":  ("diplomacy",  ...),   # -> MarriageRegistry.arrange_match_between
    "found_enterprise":  ("capital",    ...),   # -> enterprises.found_enterprise
    "expand_enterprise": ("capital",    ...),
    "build_rail":        ("expansion",  ...),   # link.rail = True after cost+turns
    "start_scheme":      ("press",      ...),   # -> SchemeManager.start_scheme
    "tour_province":     ("family",     ...),   # ruler personally: -unrest, +stress
    "adjust_garrison":   ("war",        ...),
    "acquire_minor":     ("expansion",  ...),   # buy a bordering MINOR_OWNER province:
                                                # cost = 300 * development + 100 * total
                                                # endowment richness; owner flips
}
def initiative(game, house_name, verb, executor, **kwargs) -> List[str]
```

**Smoke** (G12 precedes G13, so the smoke builds the game context by hand — docket must not import chassis; it only *receives* the game object):

```python
import random
from gilded import docket
from gilded.world import generate_atlas
from gilded.houses import assign_houses
from gilded.society.realm import create_house_realm
from gilded.society.schemes import SchemeManager
from gilded.society.marriages import MarriageRegistry
from gilded.society.ideology import IdeologicalTide
class FakeGame: pass
g = FakeGame(); g.rng = random.Random(21)
g.atlas = generate_atlas(42); g.houses = assign_houses(g.atlas, 42)
hname = next(iter(g.houses))
g.realms = {hname: create_house_realm(hname, g.rng)}
g.enterprises = []; g.wars = []; g.events = []; g.turn = 3
g.marriages = MarriageRegistry(); g.scheme_mgr = SchemeManager()
g.legitimacy = {hname: 50.0}; g.tide = IdeologicalTide()
pets = docket.generate_petitions(g, hname)
assert isinstance(pets, list) and len(pets) <= 6
# force a seat vacancy petition
from gilded.society.court import CourtPosition
g.realms[hname].court.positions[CourtPosition.MARSHAL] = None
pets = docket.generate_petitions(g, hname)
vac = [p for p in pets if p.kind == "seat_vacancy"]
assert vac and vac[0].options
msgs = docket.rule(g, vac[0], vac[0].options[0].key, g.realms[hname].ruler)
assert isinstance(msgs, list)
leftover = [p for p in docket.generate_petitions(g, hname)]
out = docket.resolve_unattended(g, hname, leftover)
assert isinstance(out, list)
print("G12 smoke OK")
```

**Steps:**
- [ ] Author `G12_brief.md` (all eight generators implemented; INITIATIVES fully wired to G4/G6/G9/G10 calls, `war_council`/`adjust_garrison` no-op until G16 with a clear "no active war" message), `G12_smoke.py`, `G12_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G13: The Chassis (`gilded/chassis.py`)

**Files:**
- Create: `gilded/chassis.py`
- Test: `gilded/tests/test_chassis.py`

**Contract:** The anti-`game.py`: it calls systems and owns only wiring + the event log.

```python
class GildedGame:
    def __init__(self, seed: int, player_house: Optional[str] = None):
        self.seed, self.rng = seed, random.Random(seed)
        self.turn = 1
        self.atlas = generate_atlas(seed)
        self.houses = assign_houses(self.atlas, seed)      # player_house flag set if given
        self.realms = {h: create_house_realm(h, self.rng) for h in self.houses}
        self.enterprises: List[Enterprise] = []            # seeded: 2 per house on best endowments
        self.directives = {h: Directives() for h in self.houses}
        self.tide = IdeologicalTide()
        self.legitimacy = {h: 50.0 for h in self.houses}
        self.scheme_mgr = SchemeManager()
        self.marriages = MarriageRegistry()
        self.wars: List[object] = []                       # fronts.War from G15
        self.events: List[TurnEvent] = []                  # this turn's record
        self.docket_by_house: Dict[str, List[Petition]] = {}
        self.attention: Dict[str, int] = {}
        self.game_over: Optional[str] = None               # ending key when finished
    def ents_of(self, house) -> List[Enterprise]
    def provinces_of(self, house) -> List[Province]
    def open_turn(self):        # phase I: clears events? NO — events accumulate during
        # end_turn resolution and are read at the START of next turn (the papers report
        # what happened). open_turn: generate docket for every house, reset attention.
    def end_turn(self) -> List[TurnEvent]:
        # 1. resolve_unattended for every house's remaining petitions
        # 2. construction ticks; strategic-capacity tally per house (Dict[str, Dict[str,
        #    float]], consumed by raise_regiments); dividends (shares.pay_dividends ->
        #    treasury + ledgers). Prices are constants swayed by the tide: colliery gold
        #    x (1 + 0.05 * provinces striking worldwide) — a great strike raises coal
        #    prices everywhere.
        # 3. labor: tick_extraction per enterprise, tick_movement per province
        # 4. society: tick_realm per house (house_ai), tick_relationships, scheme_mgr
        #    .advance_all, marriages.tick, tick_directors, tick_loyalty
        # 5. directives friction: tick_friction per house (seats from DOMAIN_SEAT)
        # 6. war resolution (G15/G16 hook; no-op while self.wars empty)
        # 7. tide.tick; legitimacy per house (contentment formula from G7)
        # 8. revolution checks (brewing -> trigger or transform), successions pending
        # 9. endings check (G17 hook; absent until then), turn += 1, open_turn()
```

Every phase converts its message strings into `TurnEvent`s with sensible registers (dividends → ledger; strikes/wars/scandals → gazette; spy/secret/family → letters, house-scoped).

**Smoke:**

```python
from gilded.chassis import GildedGame, TurnEvent
g = GildedGame(seed=42)
assert len(g.houses) == 7 and len(g.realms) == 7 and len(g.enterprises) >= 14
for _ in range(10): g.end_turn()
assert g.turn == 11
assert any(e.register == "ledger" for e in g.events)   # dividends flowed last turn
g2 = GildedGame(seed=42)
for _ in range(10): g2.end_turn()
assert [e.text for e in g.events] == [e.text for e in g2.events]        # deterministic
assert all(h in g.attention for h in g.houses)
print("G13 smoke OK")
```

**Steps:**
- [ ] Author `G13_brief.md`, `G13_smoke.py`, `G13_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G14: The Morning Papers (`gilded/papers.py`)

**Files:**
- Create: `gilded/papers.py`
- Test: `gilded/tests/test_papers.py`

**Contract:**

```python
@dataclass
class TurnReport:
    turn: int
    year: int
    gazette: List[str]            # world news, all houses' public events
    ledger: List[str]             # this house's business
    letters: List[str]            # this house's private matters

def compose(game, house_name: str) -> TurnReport
    # gazette: events with register "gazette" (any house), slanted: if the reading
    #   house's MASTER_OF_PRESS is seated with intrigue >= 12, own-house scandal
    #   items get a softened prefix ("It is rumoured, no doubt falsely, that ...")
    # ledger: register "ledger" AND event.house == house_name, plus a standing
    #   summary line: treasury, dividend total, enterprise count, strikes active
    # letters: register "letters" AND event.house == house_name
def format_broadsheet(report: TurnReport) -> str
    # plain-text masthead ("THE CONTINENTAL GAZETTE — <year>"), section headers,
    # wrapped columns via textwrap; used by console and tests
```

**Smoke:**

```python
from gilded.chassis import GildedGame
from gilded.papers import compose, format_broadsheet
g = GildedGame(seed=42)
for _ in range(5): g.end_turn()
h = next(iter(g.houses))
rep = compose(g, h)
assert rep.turn == g.turn and rep.year >= 1900
assert isinstance(rep.gazette, list) and isinstance(rep.ledger, list)
assert any("treasury" in line.lower() for line in rep.ledger)
sheet = format_broadsheet(rep)
assert "GAZETTE" in sheet and str(rep.year) in sheet
print("G14 smoke OK")
```

**Steps:**
- [ ] Author `G14_brief.md`, `G14_smoke.py`, `G14_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

---

## Wave D — War

### Task G15: Fronts (`gilded/fronts.py`)

**Files:**
- Create: `gilded/fronts.py`
- Test: `gilded/tests/test_fronts.py`

**Contract:**

```python
REGIMENT_POP_COST = 5          # thousands of workforce per regiment raised
REGIMENT_STEEL_COST = 2        # steel capacity per regiment
ENTRENCH_MAX = 3
WAR_SCORE_WIN = 100.0

@dataclass
class WarGoal:
    kind: str                  # "seize" | "open_markets" | "humble" | "survive"
    provinces: List[int] = field(default_factory=list)   # for "seize"

@dataclass
class Front:
    fid: int
    border: List[Tuple[int, int]]   # contested (attacker_pid, defender_pid) pairs
    attacker_regiments: int = 0
    defender_regiments: int = 0
    commander_a_id: str = ""
    commander_d_id: str = ""
    entrenchment_a: int = 0
    entrenchment_d: int = 0
    line: float = 0.0               # -1..1, + = attacker advancing

@dataclass
class War:
    aggressor: str
    defender: str
    goal: WarGoal
    fronts: List[Front]
    war_score: float = 0.0          # -100..100, + = aggressor winning
    started_turn: int = 0

def declare_war(game, aggressor, defender, goal) -> War
    # every contested border pair (owner==aggressor adjacent owner==defender) -> fronts
    # grouped by connectivity; sets at_war_with both ways
def raise_regiments(game, house, province_pid, count) -> int
    # drains province.population by REGIMENT_POP_COST each; consumes steel capacity
    # (game tracks capacity produced this turn); returns actually raised
def allocate(war, front, house, regiments); def appoint(war, front, house, commander)
def supply(game, house, front) -> float
    # 1.0 / (1.0 + 0.15 * min rail-weighted atlas.distance from house.capital to front)
def resolve_front(game, war, front) -> List[str]
    # ratio = (att_reg * cmd_a * supply_a) vs (def_reg * cmd_d * supply_d * (1 + 0.2*entrench_d))
    # cmd = 1 + commander.get_effective_stat("command")/30 (1.0 if unappointed)
    # dice = game.rng.uniform(0.8, 1.2) each side; line moves +/- 0.25 steps;
    # |line| >= 1.0 -> frontier province changes owner, line resets, war_score +/- 15;
    # casualties = 2-8% of committed regiments per side -> feed province unrest + tide
def tick_wars(game) -> List[str]     # resolve all fronts, check WAR_SCORE_WIN & goal
```

Commander stress/temperament: after each resolution the commander takes `add_stress(6)`; `bold_craven`/`patient_impulsive` shift the dice window ±0.05 (bold widens up, craven down).

**Smoke:**

```python
from gilded.chassis import GildedGame
from gilded.fronts import declare_war, raise_regiments, allocate, appoint, resolve_front, WarGoal
g = GildedGame(seed=42)
names = list(g.houses)
# find two adjacent houses
pair = None
for a in names:
    for p in g.provinces_of(a):
        for n in p.neighbors:
            o = g.atlas.provinces[n].owner
            if o and o != a: pair = (a, o); break
assert pair
a, d = pair
war = declare_war(g, a, d, WarGoal(kind="humble"))
assert war.fronts and d in g.houses[a].at_war_with
prov = g.provinces_of(a)[0]; pop0 = prov.population
raised = raise_regiments(g, a, prov.pid, 3)
assert raised >= 1 and prov.population < pop0
allocate(war, war.fronts[0], a, raised)
appoint(war, war.fronts[0], a, g.realms[a].ruler)
msgs = resolve_front(g, war, war.fronts[0])
assert isinstance(msgs, list)
assert war.fronts[0].line > 0.0        # armed attacker vs empty line must advance
print("G15 smoke OK")
```

**Steps:**
- [ ] Author `G15_brief.md`, `G15_smoke.py`, `G15_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G16: War in the Turn — petitions, initiatives, peace (`gilded/fronts.py`, `gilded/docket.py`, `gilded/chassis.py`)

**Files:**
- Modify: `gilded/fronts.py` (add peace), `gilded/docket.py` (activate `war_council`, `declare_war`/`negotiate_peace` initiatives), `gilded/chassis.py` (call `tick_wars` in phase 6; casualties → gazette TurnEvents)
- Test: `gilded/tests/test_war_turn.py`

**Contract:**

```python
# fronts.py additions
TRUCE_TURNS = 8
@dataclass
class PeaceTerms:
    provinces: List[int] = field(default_factory=list)   # ceded to winner
    gold: float = 0.0
    shares_pct: float = 0.0        # loser's enterprises signed over (via seize/transfer)
    open_markets: bool = False
def negotiate_peace(game, war, terms: PeaceTerms) -> List[str]
    # applies terms (province owners flip, treasury transfer, seize_enterprises for
    # shares_pct >= 100 of named), removes war, sets truces both ways expiry
    # game.turn + TRUCE_TURNS, clears at_war_with
def ai_acceptable(game, war, terms, for_house) -> bool
    # loser accepts when war_score against them >= 40 and terms cost <= war_score * scale

# docket.py: war_council petition generates when any front |line| >= 0.5 or war_score
# swings 20+ since last turn; options reinforce (raise+allocate) / hold / seek_terms.
# Initiatives "declare_war" (Marshal executes; goal arg) and "negotiate_peace"
# (Foreign Secretary; auto-builds terms from war_score) become live.
```

**Smoke:**

```python
from gilded.chassis import GildedGame
from gilded.fronts import declare_war, negotiate_peace, PeaceTerms, WarGoal, TRUCE_TURNS
g = GildedGame(seed=42)
pair = None
for a in g.houses:
    for p in g.provinces_of(a):
        for n in p.neighbors:
            o = g.atlas.provinces[n].owner
            if o and o != a: pair = (a, o); break
assert pair
a, d = pair
war = declare_war(g, a, d, WarGoal(kind="seize", provinces=[g.provinces_of(d)[0].pid]))
for _ in range(6): g.end_turn()          # tick_wars now runs inside end_turn
target = war.goal.provinces[0]
msgs = negotiate_peace(g, war, PeaceTerms(provinces=[target]))
assert g.atlas.provinces[target].owner == a
assert war not in g.wars and d not in g.houses[a].at_war_with
assert g.houses[a].truces[d] > g.turn
print("G16 smoke OK")
```

**Steps:**
- [ ] Author `G16_brief.md` (**modification brief**: full replacement contents for the three files, produced by reading their HEAD state fresh at authoring time), `G16_smoke.py`, `G16_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

---

## Wave E — Judgment, Minds & Console

### Task G17: Endings (`gilded/endings.py`)

**Files:**
- Create: `gilded/endings.py`
- Modify: `gilded/chassis.py` (phase 9 calls `check_ending`; `game_over` freezes further turns)
- Test: `gilded/tests/test_endings.py`

**Contract:**

```python
@dataclass
class Epilogue:
    ending_key: str               # named ending
    axes: Dict[str, float]        # "capital", "standing", "blood", "world"
    text: str                     # multi-paragraph epilogue prose from templates

def check_ending(game, house_name) -> Optional[str]
    # hard stops, checked every turn for the judged house:
    #  "extinction"  — realm has no living dynasty member
    #  "revolution"  — trigger_revolution fired on this house without transform
    #  "transformed" — transform_house path taken (People's Chairman; game continues
    #                  but ending is recorded)
    #  "century"     — game.turn > TURN_BUDGET
def judge(game, house_name) -> Epilogue
    # capital: treasury + Σ(house-ledger pct × enterprise gold value) vs world total
    # standing: legitimacy + prestige + relations mean
    # blood: living dynasty count, heirs' stress/vice burden (penalty), generations seen
    # world: 100 - tide.level - atrocity weight - Σ unrest; worker welfare = mean dial
    #        distance below 60 rewarded
    # ending_key by profile: "Hegemon of the Age" (capital+standing top), "The Quiet
    # Throne" (standing top, low atrocities), "People's Chairman" (transformed),
    # "A House of Ash" (extinction/revolution), else "The Long Ledger"
    # text: 4 paragraphs, one per axis, from f-string templates naming real characters,
    # provinces, and the tide phase; always states who paid.
```

**Smoke:**

```python
from gilded.chassis import GildedGame, TURN_BUDGET
from gilded.endings import check_ending, judge
g = GildedGame(seed=42)
h = next(iter(g.houses))
assert check_ending(g, h) is None
for c in g.realms[h].characters:
    c.is_alive = False
g.realms[h].ruler.is_alive = False
assert check_ending(g, h) == "extinction"
g2 = GildedGame(seed=43); g2.turn = TURN_BUDGET + 1
assert check_ending(g2, next(iter(g2.houses))) == "century"
ep = judge(g2, next(iter(g2.houses)))
assert set(ep.axes) == {"capital", "standing", "blood", "world"} and len(ep.text) > 200
print("G17 smoke OK")
```

**Steps:**
- [ ] Author `G17_brief.md` (chassis replacement read fresh from HEAD), `G17_smoke.py`, `G17_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G18: AI Houses (`gilded/ai.py`)

**Files:**
- Create: `gilded/ai.py`
- Modify: `gilded/chassis.py` (phase 0 of `end_turn`: every non-player house runs `ai_turn` before unattended resolution)
- Test: `gilded/tests/test_ai.py`

**Contract:** One brain — the AI ruler plays the identical loop: reads its docket, spends ATTENTION_PER_TURN, occasionally takes initiatives.

```python
def ai_turn(game, house_name) -> List[str]
    # 1. score each petition: urgency (escalated 2x) + |ruler conviction on the
    #    domain's DIRECTIVE_CONVICTION spectrum| / 50
    # 2. rule on top petitions until attention exhausted, choosing the option whose
    #    stance_bias is closest to ruler conviction; executor = domain seat holder
    #    if opinion_of(holder, ruler) > -20 else ruler
    # 3. leftover attention (usually 0-1): initiative by disposition —
    #    ambitious_content > 40 & treasury > found_cost -> found/expand enterprise;
    #    militarist conviction > 50 & no war & a bordering weaker house -> declare_war
    #    (strength = regiments possible + treasury; weaker = < 0.7x);
    #    else if unmarried adult heir -> propose_marriage to best-relations house
    # 4. set directives once every 10 turns from ruler convictions via
    #    dial_from_ruler-style mapping (stance = conviction value rounded)
def ai_peace_check(game, war) -> Optional[PeaceTerms]
    # losing side (war_score <= -40) sues: terms from ai_acceptable; chassis applies
```

**Smoke:**

```python
from gilded.chassis import GildedGame
g = GildedGame(seed=42)          # no player_house: all seven are AI
for _ in range(20): g.end_turn()
assert g.turn == 21
# AI actually ruled: attention was spent by at least one house at some point
assert any(v < 3 for v in g.attention.values()) or g.docket_by_house
# determinism holds with AI in the loop
g2 = GildedGame(seed=42)
for _ in range(20): g2.end_turn()
assert [e.text for e in g.events] == [e.text for e in g2.events]
print("G18 smoke OK")
```

**Steps:**
- [ ] Author `G18_brief.md` (chassis replacement read fresh from HEAD), `G18_smoke.py`, `G18_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G19: The Console (`gilded/console.py`, `gilded/__main__.py`)

**Files:**
- Create: `gilded/console.py`, `gilded/__main__.py`
- Test: `gilded/tests/test_console.py`
- Sources (read-only): repo root `play_console.py` (file-bridge pattern reference)

**Contract:** Same file-bridge protocol as `play_console.py`: watch `<dir>/cmd_in.txt` for appended lines, append one JSON reply per command to `<dir>/replies.jsonl`.

```python
COMMANDS = {
    "state":      # {"turn", "year", "house", "attention", "treasury", "legitimacy",
                  #  "provinces": n, "enterprises": n, "wars": [...], "game_over"}
    "papers":     # full format_broadsheet text for the player house
    "docket":     # numbered petition list: pid, kind, domain, text, options (key+text)
    "rule":       # rule <pid> <option_key> [executor <char name>]  -> messages
    "initiative": # initiative <verb> key=value ...                 -> messages
    "dial":       # dial <directive> <value>          (free, no attention)
    "atlas":      # atlas [<pid>] — province ledger: owner, terrain, endowments, pop,
                  #  unrest, garrison, enterprises (name/tier/dial/director), rail links
    "house":      # house [<name>] — ruler, seats, heir, treasury, relations, wars
    "chars":      # top characters of own realm: name, age, stats, stress, seat
    "end_turn":   # runs end_turn; reply includes new turn + game_over key if any
    "epilogue":   # judge() output once game_over
    "save":       # save <name> -> pickle to <dir>/<name>.pkl (game object)
    "load":       # load <name>
    "quit":
}
def run_console(bridge_dir: str, seed: int, player_house: Optional[str]) -> None
# gilded/__main__.py:
#   python -m gilded --console <dir> [--seed N] [--house NAME] [--ai-only]
#   --ai-only: no player house; end_turn free-runs when "run <n>" command is sent
```

**Smoke** (drives the bridge exactly like `C:/tmp/campaign_turns.py` drove M83):

```python
import json, os, subprocess, sys, tempfile, time
d = tempfile.mkdtemp()
proc = subprocess.Popen([sys.executable, "-m", "gilded", "--console", d, "--seed", "42"])
def send(cmd):
    with open(os.path.join(d, "cmd_in.txt"), "a") as f: f.write(cmd + "\n")
def last_reply(prev_count, timeout=30):
    path = os.path.join(d, "replies.jsonl"); t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(path):
            lines = open(path).read().splitlines()
            if len(lines) > prev_count: return json.loads(lines[-1])
        time.sleep(0.2)
    raise TimeoutError("no reply in " + d)
send("state"); r = last_reply(0); assert r["turn"] == 1 and r["year"] == 1900
send("docket"); r = last_reply(1); assert "petitions" in r
send("end_turn"); r = last_reply(2); assert r["turn"] == 2
send("papers"); r = last_reply(3); assert "GAZETTE" in r["text"]
send("quit"); proc.wait(timeout=15)
print("G19 smoke OK")
```

**Steps:**
- [ ] Author `G19_brief.md` (read root `play_console.py` fresh for bridge mechanics), `G19_smoke.py`, `G19_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G20: The Century Soak (`gilded/tests/test_soak.py`)

**Files:**
- Test: `gilded/tests/test_soak.py` (this mission is test-only; if invariants fail, the fix is a follow-up mission, not a test weakening)

**Contract:** The standing regression: a full seeded AI-only century.

```python
import time
from gilded.chassis import GildedGame, TURN_BUDGET
from gilded.endings import judge

def test_century_soak():
    g = GildedGame(seed=2026)
    endings = {}
    for _ in range(TURN_BUDGET + 1):
        g.end_turn()
        # invariants every turn:
        for h, house in g.houses.items():
            assert house.treasury == house.treasury          # no NaN
            assert 0.0 <= g.legitimacy[h] <= 100.0
        for p in g.atlas.provinces.values():
            assert p.population >= 0 and p.unrest >= 0.0
        for e in g.enterprises:
            assert 0.0 <= e.extraction_dial <= 100.0
            assert abs(e.ledger_total() - 100.0) < 1.0 or e.ledger == {}
        if g.game_over: break
    assert g.turn >= 30                                       # world survives to mid-game
    ep = judge(g, next(iter(g.houses)))
    assert ep.ending_key and len(ep.text) > 200

def test_soak_determinism():
    a, b = GildedGame(seed=7), GildedGame(seed=7)
    for _ in range(25): a.end_turn(); b.end_turn()
    assert [e.text for e in a.events] == [e.text for e in b.events]
```

Runtime budget: the two tests together must finish < 120 s (`@pytest.mark.timeout` not available — assert wall time manually with `time.monotonic()` inside the test and fail above 120 s).

**Steps:**
- [ ] Author `G20_brief.md` (the two tests verbatim), `G20_smoke.py` (runs `python -m pytest gilded/tests/test_soak.py -q`), `G20_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

---

## Wave F — The Broadsheet (pygame client)

UI missions render from `GildedGame` + `papers.compose` only — no sim logic in `ui/`. Import-smoke tests use `SDL_VIDEODRIVER=dummy`.

### Task G21: Atlas Renderer (`gilded/ui/atlas_view.py`)

**Files:**
- Create: `gilded/ui/__init__.py`, `gilded/ui/atlas_view.py`
- Test: `gilded/tests/test_ui_atlas.py`

**Contract:**

```python
HOUSE_COLORS = [(122, 74, 58), (58, 90, 122), (74, 106, 74), (140, 120, 60),
                (110, 70, 110), (70, 110, 110), (150, 90, 70), (95, 95, 130)]
# assigned to houses in name order; province fill for MINOR_OWNER:
MINOR_COLOR = (90, 90, 90); OCEAN_COLOR = (26, 35, 51); FRONT_COLOR = (208, 64, 64)
def province_polygons(atlas, scale=8) -> Dict[int, List[Tuple[int, int]]]
    # marching-squares boundary trace of each province's cells -> screen polygon
def draw_atlas(surface, game, selected_pid=None)
    # fill polygons by owner color, black borders, province names at centers,
    # endowment glyphs, rail links as gold dashes between centers,
    # fronts as red lines along contested borders (from game.wars)
def pick_province(atlas, polygons, pos) -> Optional[int]     # point-in-polygon
def province_panel_lines(game, pid) -> List[str]             # the click-through ledger text
```

**Smoke:**

```python
import os; os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame; pygame.init()
from gilded.chassis import GildedGame
from gilded.ui.atlas_view import province_polygons, draw_atlas, pick_province, province_panel_lines
g = GildedGame(seed=42)
polys = province_polygons(g.atlas)
assert set(polys) == set(g.atlas.provinces) and all(len(v) >= 3 for v in polys.values())
surf = pygame.Surface((1280, 900))
draw_atlas(surf, g)
pid = next(iter(g.atlas.provinces))
c = g.atlas.provinces[pid].center
assert pick_province(g.atlas, polys, (int(c[0] * 8), int(c[1] * 8))) == pid  # centroid hit (Voronoi regions ~convex)
lines = province_panel_lines(g, pid); assert any(g.atlas.provinces[pid].name in l for l in lines)
print("G21 smoke OK")
```

**Steps:**
- [ ] Author `G21_brief.md`, `G21_smoke.py`, `G21_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G22: Broadsheet Screens (`gilded/ui/broadsheet.py`)

**Files:**
- Create: `gilded/ui/broadsheet.py`
- Test: `gilded/tests/test_ui_broadsheet.py`

**Contract:**

```python
TABS = ("Gazette", "Ledger", "Letters", "Docket", "Atlas", "House")
class BroadsheetView:
    def __init__(self, game, house_name)
    def draw(self, surface)          # active tab; papers tabs render TurnReport in
                                     # serif columns; Docket renders petition cards
                                     # (text, actor names, option buttons, executor
                                     # cycle button, attention remaining)
    def handle_click(self, pos) -> Optional[dict]
        # returns an action dict: {"rule": (pid, option_key, executor_id)} |
        # {"initiative": ...} | {"tab": name} | {"select_province": pid} |
        # {"end_turn": True} | None
```

Petition card interactions call nothing themselves — `app.py` applies returned actions to the game (UI stays a client).

**Smoke:**

```python
import os; os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame; pygame.init()
from gilded.chassis import GildedGame
from gilded.ui.broadsheet import BroadsheetView, TABS
g = GildedGame(seed=42)
v = BroadsheetView(g, next(iter(g.houses)))
surf = pygame.Surface((1280, 900))
for tab in TABS:
    v.active_tab = tab; v.draw(surf)
action = v.handle_click((5000, 5000))          # off-surface click -> no action
assert action is None
print("G22 smoke OK")
```

**Steps:**
- [ ] Author `G22_brief.md`, `G22_smoke.py`, `G22_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

### Task G23: The App (`gilded/ui/app.py`, `gilded/__main__.py`)

**Files:**
- Create: `gilded/ui/app.py`
- Modify: `gilded/__main__.py` (default mode without `--console` launches the app)
- Test: `gilded/tests/test_ui_app.py`

**Contract:**

```python
def run_app(seed: int, player_house: Optional[str] = None)
    # pygame loop: window "The Gilded Machine", BroadsheetView + atlas_view for the
    # Atlas tab; applies BroadsheetView.handle_click actions to the game (rule /
    # initiative / end_turn); Esc quits; F5 quicksave via console's save format
# __main__.py final:
#   python -m gilded                      -> app, random seed, first house as player
#   python -m gilded --seed N --house X   -> app
#   python -m gilded --console <dir> ...  -> headless (unchanged)
def step_once(app_state) -> bool         # one frame, factored for testability
```

**Smoke:**

```python
import os; os.environ["SDL_VIDEODRIVER"] = "dummy"
from gilded.ui import app
import inspect
assert callable(app.run_app) and "seed" in inspect.signature(app.run_app).parameters
import subprocess, sys
r = subprocess.run([sys.executable, "-c",
    "import os; os.environ['SDL_VIDEODRIVER']='dummy'; import gilded.ui.app"],
    capture_output=True, timeout=60)
assert r.returncode == 0, r.stderr.decode()
print("G23 smoke OK")
```

**Steps:**
- [ ] Author `G23_brief.md` (`__main__.py` replacement read fresh from HEAD), `G23_smoke.py`, `G23_task.json`
- [ ] Pre-validate in scratch worktree; pytest tail `1 failed, N passed`
- [ ] Dispatch
- [ ] Verify all five checks
- [ ] Log

---

## After the last mission

- [ ] Run the full suite one final time: `python -m pytest -q --ignore=test_output.txt` → `1 failed, N passed` (only `test_100_turn_stability`)
- [ ] Played-campaign shakedown via the console bridge (a `C:/tmp/gilded_campaign.py` driver, same pattern as the marathon drivers): 70 turns as a player house, spot-check papers/docket/war/epilogue output
- [ ] Update auto-memory: mission log location, soak baseline, any engine bugs found

