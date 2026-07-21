# Playable Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **OVERRIDING PROJECT RULE:** In this repo, Claude never edits game source directly. Every game-code change is executed by a CynCo mission: Claude authors a byte-for-byte brief + a READ-ONLY smoke test in C:/tmp, pre-validates in a scratch git worktree, dispatches CynCo headlessly, and verifies the commit independently. The tasks below are therefore *mission tasks* run through the Standard Mission Loop (Task 0), not direct-edit tasks. The exact byte-for-byte edit anchors are pinned at brief-authoring time from fresh reads of the then-current code (missions land sequentially and shift line numbers); everything else — design, constants, function shapes, smoke assertions, verification — is pinned here.

**Goal:** Fix CivKings to a genuinely playable, winnable, savable state (missions M77–M82), build a terminal play console (M83), then play a full Huge-map campaign end-to-end with Claude making every decision, producing a screenshot album and campaign log.

**Architecture:** Six fix missions repair the systemic holes found by the 2026-07-21 audit (spec: `docs/superpowers/specs/2026-07-21-play-the-game-design.md`), an exit-gate soak proves the game is playable, then a play-console mission adds a stdin/stdout protocol around the real engine + off-screen GameScreen for the marathon.

**Tech Stack:** Python 3.14, pygame-ce 2.5.7 (SDL dummy driver for off-screen), pickle for checkpoints, CynCo dispatch via `bun engine/main.ts --run-task`.

---

## Task 0: The Standard Mission Loop (procedure used by Tasks 1–6 and 8)

Not a code task — the exact procedure each mission task invokes. All commands run from `C:/Users/civer/civkings` in bash.

- [ ] **Step 0.1 — Fresh reads.** Read the current code of every file the mission touches. Confirm every planned anchor string is present exactly once. If an anchor moved or duplicated, adjust the brief's find-block (never the design).
- [ ] **Step 0.2 — Author the smoke** at `C:/tmp/smoke_mNN.py` using the assertion content given in the mission task. Header always:

```python
import sys, os, random, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.abspath('.'))
random.seed(NN)
import py_compile
```

- [ ] **Step 0.3 — Author the brief** at `C:/tmp/cynco-missionMNN-brief.txt` in the established format: GOAL, RULES (byte-for-byte edits only; C:/tmp smokes are READ-ONLY; must ACTUALLY RUN the git commit and report the `git log -1 --format=%H` hash), numbered `EDIT n — file X / Find this exact code: / Replace with:` blocks, VERIFICATION (the mission smoke, then `smoke_m76.py`, `smoke_m75.py`, `smoke_m74.py`, `smoke_m73.py`, `smoke_m66.py`, `smoke_m61.py`, `smoke_m57.py`, then `PYTHONIOENCODING=utf-8 python -m pytest -q --ignore=test_output.txt` with the expected tail line), COMMIT (exact `git add` file list + message).
- [ ] **Step 0.4 — Worktree pre-validation.**

```bash
git worktree add /c/tmp/wtMNN HEAD
```

Apply the brief's edits programmatically in the worktree (assert each find-block count == 1; write with `encoding='utf-8', newline=''`), run the mission smoke + the full smoke suite + pytest there. Record the pytest tail; if the mission legitimately changes it, write the new expected line into the brief's VERIFICATION. Fix smoke/brief bugs here (game-design bugs mean the design step was wrong — fix the brief, re-validate). Then:

```bash
git worktree remove --force /c/tmp/wtMNN
```

- [ ] **Step 0.5 — Dispatch CynCo.** Build `C:/tmp/cynco-mNN-task.json` from the M76 template (`missionId`, `triggerId: "manual-claude-dispatch"`, `context`, `prompt` = brief text, `allowedTools`, `timeoutMs: 1200000`, `outcomePath`), then:

```bash
rm -f /c/tmp/cynco-mNN-outcome.json
cd /c/Users/civer/localcode && bun engine/main.ts --run-task C:/tmp/cynco-mNN-task.json > /c/tmp/cynco-mNN-run.log 2>&1
```

(run_in_background; wait for completion notification.)
- [ ] **Step 0.6 — Verify independently.** In `C:/Users/civer/civkings`:
  1. `git log -1 --format='%H %s'` and `git show HEAD --name-status --format=` — only the brief's files changed.
  2. Byte-diff every EDIT block against the brief (regex extraction, `src.count(new) == 1` and `old not in src.replace(new, '')`).
  3. Tamper grep: `grep -n "smoke_m" /c/tmp/cynco-mNN-run.log | grep -iE "write|edit|delete"` must exit 1.
  4. Run the mission smoke + full smoke suite: every one prints `SMOKE OK`.
  5. Run pytest; tail must match the brief's expected line.
- [ ] **Step 0.7 — Update memory** (`reference_deep_spec.md`): mission hash + any new lessons. Proceed to the next task.

---

## Task 1: M77 — A winnable game

**Files:**
- Modify: `ideology.py` (constants + `tick_legitimacy`, currently lines 66–89)
- Modify: `game.py` (`_check_victory`, currently lines 1400–1496)
- Smoke: `C:/tmp/smoke_m77.py`

**Design — legitimacy rebalance (`ideology.py`).** Replace the flat recovery with happiness-scaled recovery and soften the tide drain so a content, well-run House nets positive even at full revolutionary tide:

```python
LEGITIMACY_HAPPY_RECOVERY = 0.4   # base per-turn recovery while content
LEGITIMACY_HAPPY_BONUS = 0.6      # extra recovery at happiness >= 20 (scales linearly)
LEGITIMACY_TIDE_DRAIN = 0.35      # per turn at full tide (was 0.6 - always beat recovery)
```

and in `tick_legitimacy`, the recovery branch becomes:

```python
    if happiness >= 0:
        current += LEGITIMACY_HAPPY_RECOVERY + LEGITIMACY_HAPPY_BONUS * min(happiness, 20) / 20.0
```

Net effect: max recovery +1.0/turn vs max tide drain −0.35/turn. Unhappiness and scandal still bite; a neglected House still spirals.

**Design — time victory (`game.py::_check_victory`).** Immediately after the `MIN_VICTORY_TURN` early-return, add:

```python
        # Time victory (M77): when the budget runs out, the age is judged.
        turn_budget = getattr(self.state, "turn_budget", 0)
        if turn_budget and self.state.turn >= turn_budget:
            def _score(name: str) -> float:
                civ_o = self.civilizations[name]
                tm = self.research.get(name)
                return (12.0 * sum(1 for c in self.cities.values() if c.owner == name)
                        + 6.0 * len(getattr(tm, "researched", []) or [])
                        + getattr(civ_o, "culture", 0) / 5.0
                        + getattr(civ_o, "prestige", 0) / 5.0
                        + getattr(self, "legitimacy", {}).get(name, 0.0))
            winner = max(self.civilizations, key=_score)
            return {"winner": winner, "type": "Time"}
```

The Time victory deliberately ignores the legitimacy floor (legitimacy is a score input instead), so the game always ends by the budget.

**Smoke assertions (`smoke_m77.py`):**

```python
py_compile.compile('ideology.py', doraise=True)
py_compile.compile('game.py', doraise=True)
import ideology
assert ideology.LEGITIMACY_TIDE_DRAIN == 0.35
assert ideology.LEGITIMACY_HAPPY_BONUS == 0.6
# A content House outruns a full revolutionary tide.
tide = types.SimpleNamespace(level=100.0)
after = ideology.tick_legitimacy(50.0, 20, tide=tide)
assert after > 50.0 + 0.6   # net >= +0.65/turn
# A neglected House still bleeds.
assert ideology.tick_legitimacy(50.0, -15, tide=tide) < 50.0
# Time victory fires at the budget and returns the top scorer.
# (Build a real small Game, force state.turn to state.turn_budget,
#  call game._check_victory(), assert result["type"] == "Time" and the
#  winner is the civ with the most cities+techs in the constructed state.)
```

The Game-construction section of the smoke follows the audit-script pattern (real `Game(civ, ai_civs=..., map_width=24, map_height=24)`, AIPlayers attached, ~10 process_turns, then `game.state.turn = game.state.turn_budget`).

**Commit:** `git add ideology.py game.py` / `feat: M77 winnable game - legitimacy recovery scales with happiness, tide drain softened, time victory judges the age at the turn budget`

- [ ] Run Task 0 loop for M77.

---

## Task 2: M78 — One true save system (full-fidelity checkpoints)

**Files:**
- Modify: `game.py` (add `checkpoint`/`restore`; retire the `save_game`/`load_game` stubs at lines 1988–2005)
- Modify: `marriages.py` (add module-state get/set)
- Modify: `pygame_app/screens/game_screen.py` (Save action, line ~341)
- Modify: `pygame_app/screens/load_game_screen.py` (load `.pkl` checkpoints)
- Smoke: `C:/tmp/smoke_m78.py`

**Design.** JSON round-tripping the full object graph (realms→courts→characters→schemes→marriages) is a rewrite; pickle round-trips it exactly. Core:

`marriages.py` — module state accessors (the registries are module globals):

```python
def get_state() -> dict:
    """Snapshot the module-level marriage registries (M78)."""
    return {"marriages": list(_marriages), "contracts": dict(_contracts),
            "married_ids": set(_married_ids), "wedding_count": wedding_count}


def set_state(state: dict) -> None:
    """Restore the module-level marriage registries (M78)."""
    global wedding_count
    _marriages[:] = state.get("marriages", [])
    _contracts.clear(); _contracts.update(state.get("contracts", {}))
    _married_ids.clear(); _married_ids.update(state.get("married_ids", set()))
    wedding_count = state.get("wedding_count", 0)
```

`game.py` — replace the two stubs with:

```python
    def checkpoint(self, filepath) -> None:
        """Full-fidelity save (M78): pickle the live game + module registries."""
        import pickle, os
        import marriages as _mar
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump({"save_version": 2, "game": self,
                         "marriages_state": _mar.get_state()}, f)

    @staticmethod
    def restore(filepath) -> 'Game':
        """Load a full-fidelity checkpoint (M78). Returns a running Game."""
        import pickle
        import marriages as _mar
        with open(filepath, "rb") as f:
            blob = pickle.load(f)
        _mar.set_state(blob.get("marriages_state", {}))
        return blob["game"]

    def save_game(self, filepath):
        """Save the game (M78): full checkpoint, no longer a 4-field stub."""
        self.checkpoint(filepath)

    @staticmethod
    def load_game(filepath) -> 'Game':
        """Load the game (M78): fixed decorators, returns a real Game."""
        return Game.restore(filepath)
```

`game_screen.py` — the Save action writes `saves/checkpoint.pkl` via `game.save_game(...)` (path change only; call-site anchor read fresh). `load_game_screen.py` — files ending `.pkl` load via `Game.restore` and enter the game screen; JSON entries keep their legacy path.

**Pre-validation extra (worktree, before dispatch):** prove `Game` is picklable — build a 30-turn game and `pickle.dumps(game)`. If it raises (lambda/surface/module attribute), locate the offending attribute and add the minimal `__getstate__`/`__setstate__` on that class to the brief. This is the mission's main risk; it is settled *before* dispatch, not after.

**Smoke assertions (`smoke_m78.py`):** build a real 4-civ 40x40 game, run 30 turns, record invariants (turn, per-realm courtier counts, `dict(dm.relations)`, per-civ researched-tech counts, legitimacy dict, `len(marriages._married_ids)`), `game.checkpoint('C:/tmp/m78.pkl')`; corrupt the module registries (`marriages.set_state({...empty...})`); `g2 = Game.restore('C:/tmp/m78.pkl')`; assert every invariant matches on `g2` and the registries are back; run `g2.process_turn()` 10 times crash-free; assert `Game.load_game('C:/tmp/m78.pkl')` returns a `Game` (the old `TypeError` is dead).

**Commit:** `git add game.py marriages.py pygame_app/screens/game_screen.py pygame_app/screens/load_game_screen.py` / `feat: M78 one true save system - full-fidelity pickle checkpoints replace the stub save, load returns a running game`

- [ ] Run Task 0 loop for M78.

---

## Task 3: M79 — War friction (relations move, wars happen)

**Files:**
- Modify: `diplomacy.py` (new `tick_relations`; class currently holds `self.relations: Dict[Tuple[str, str], int]`, clamped ±100 by `modify_relation`)
- Modify: `game.py` (call `tick_relations` each turn from `process_turn`)
- Modify: `marriages.py` (cap wedding-bonus stacking)
- Smoke: `C:/tmp/smoke_m79.py`

**Design.** Three pressures, all deterministic:

`diplomacy.py`:

```python
    RELATION_DRIFT = 1          # relations decay toward 0 each turn
    BORDER_FRICTION = 2         # neighbors grind each other every friction tick
    FRICTION_PERIOD = 10        # turns between border-friction applications

    def tick_relations(self, game, turn: int) -> None:
        """Relations are not forever (M79): goodwill decays toward neutral,
        and crowded borders grind."""
        for pair in list(self.relations):
            cur = self.relations[pair]
            if cur > 0:
                self.relations[pair] = cur - min(self.RELATION_DRIFT, cur)
            elif cur < 0:
                self.relations[pair] = cur + min(self.RELATION_DRIFT, -cur)
        if turn % self.FRICTION_PERIOD != 0:
            return
        borders = self._shared_borders(game)
        for pair in borders:
            if not self.is_at_war(*pair):
                self.modify_relation(pair[0], pair[1], -self.BORDER_FRICTION)

    def _shared_borders(self, game) -> set:
        """Pairs of civs whose owned city tiles touch (M79)."""
        owner_tiles = {}
        for city in game.cities.values():
            owner_tiles.setdefault(city.owner, set()).update(
                getattr(city, "owned_tiles", set()))
        pairs = set()
        names = sorted(owner_tiles)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                ta, tb = owner_tiles[a], owner_tiles[b]
                if any((x + dx, y + dy) in tb
                       for (x, y) in ta
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    pairs.add((a, b))
        return pairs
```

`game.py` — inside `process_turn`, adjacent to the existing diplomacy processing: `self.diplomacy_manager.tick_relations(self, self.state.turn)`.

`marriages.py` — in both wedding paths (ambient tick and `arrange_match_between`), the relation bonus applies only while relations are below a ceiling: wrap the `dm.modify_relation(...)` calls with `if dm.get_relation(civ_a, civ_b) < 60:`. Weddings past that point still bind Houses (marriage records, dowries) but goodwill saturates.

Net dynamics: wedding pushes fade (drift 1/turn beats a +25 bonus every 5 turns only while below 60 and only for the AI's single warmest friend); non-friend neighbors grind to −30 in ~150 bordered turns; the M75 strength-gated war check then fires.

**Smoke assertions (`smoke_m79.py`):** unit level — drift moves +40→+39 and −40→−39 in one tick; friction applies only on `turn % 10 == 0` and only to bordered pairs (stub game with two cities owning adjacent `owned_tiles`); wedding bonus suppressed at relation ≥ 60 (stub DM). Integration — real 4-civ 40x40 game soaked 250 turns with a seed chosen during worktree pre-validation: assert `any` war was declared during the run (capture stdout, look for the war declaration line) or `dm.wars` non-empty at some sampled turn; assert relations are NOT all pinned at 67–100 at t250.

**Commit:** `git add diplomacy.py game.py marriages.py` / `feat: M79 war friction - relations drift to neutral, borders grind, wedding goodwill saturates; wars actually happen`

- [ ] Run Task 0 loop for M79.

---

## Task 4: M80 — AI economy, faith, and prestige repair

**Files:**
- Modify: `ai.py` (treasury reserve in `_manage_production`; Temple in `BUILD_ORDER`; found-religion step in `take_turn`)
- Modify: `game.py` (prestige sync at lines ~1081–1089; succession carryover site found at brief time)
- Modify: `realms.py` (add `prestige_legacy` field default 0.0)
- Smoke: `C:/tmp/smoke_m80.py`

**Design.**
- **Treasury:** in `ai.py`, before any gold-spending branch in `_manage_production` (and any rush-buy site found in the fresh read), gate spending on a reserve floor: `reserve = 50.0 + 10.0 * my_city_count`; the AI only spends gold above `reserve`. (Worktree diagnosis step confirms the exact site(s) that currently drain to 0 — the audit showed every AI pinned at exactly 0 gold from turn 1.)
- **Faith:** M74's `BUILD_ORDER` is `Monument→Granary→Workshop→Aqueduct→Factory` — no faith building, hence AI faith pinned at 0 forever. New order: `Monument→Granary→Temple→Workshop→Aqueduct→Factory` (exact building name from `game_data.py` at brief time).
- **Founding religions:** in `ai.py::take_turn`, after diplomacy/intrigue: if `game.faith_points.get(self.civ_name, 0)` exceeds the founding cost and this civ has no religion, found one through the same `religion_manager` call the player path uses (exact API from fresh read of `religion.py`/`religion_popup.py`), naming it deterministically (e.g., `f"Faith of {self.civ_name}"`).
- **Prestige:** `realms.py` Realm gains `prestige_legacy: float = 0.0`. At the succession site (dynasty/realm code that seats a new ruler — located at brief time), add `realm.prestige_legacy += getattr(dead_ruler, "prestige", 0.0)`. The sync in `game.py` becomes, for every civ: `p = realm.prestige_legacy + ruler.prestige` (+ dynastic prestige for the player, as now) — so Houses accumulate across generations and AI civs are no longer stuck at the live ruler's tally.

**Smoke assertions (`smoke_m80.py`):** unit level — AI with gold 40 and reserve 50 buys nothing; AI with gold 400 spends only down to its reserve; `BUILD_ORDER` contains the faith building before Workshop; a stub realm's `prestige_legacy` survives the sync into `civ.prestige`. Integration — real 4-civ 40x40 game, 150 turns, seed picked in pre-validation: at t150 assert `max(game.gold[n] for n in ai_names) > 0`, `max(game.faith_points[n] for n in ai_names) > 0`, `len(game.religion_manager.religions) >= 1`, and some civ's synced prestige exceeds its current ruler's own prestige.

**Commit:** `git add ai.py game.py realms.py` / `feat: M80 AI economy repair - treasury reserves, Temples and founded religions, prestige outlives the ruler`

- [ ] Run Task 0 loop for M80.

---

## Task 5: M81 — Military hygiene (caps, promotions, silence)

**Files:**
- Modify: `ai.py` (army cap in `_manage_production`; auto-resolve promotions in `take_turn`)
- Modify: the file printing `[PROMOTION] ...` (grep at brief time; audit shows it fires per pending unit per turn)
- Modify: `pygame_app/screens/game_screen.py` (drop the `[game_screen]` debug prints in `_process_next_turn`)
- Smoke: `C:/tmp/smoke_m81.py`

**Design.**
- **Army cap:** in `_manage_production`, before queueing/keeping military production: count living soldiers (same WORKER/SETTLER exclusion as M75's `_army_strength`); if `soldiers >= 3 + 2 * my_city_count`, produce buildings instead. (Audit: 6,748 units by t1100 on Huge; cap for a 17-city AI = 37.)
- **Promotions:** in `take_turn`, iterate own living units; where the pending-promotion surface (found in the fresh read of the promotion system) offers choices, apply the first available deterministically. Pending promotions stop accumulating, and the per-turn `[PROMOTION]` reminder goes quiet on its own; the print itself is deleted too.
- **Silence:** delete the `[PROMOTION] ...` print line(s) and the two `[game_screen] _process_next_turn...` prints.

**Smoke assertions (`smoke_m81.py`):** unit level — stub game where an AI with 2 cities and 7 soldiers skips military production; with 6 soldiers it doesn't. Static — `'[game_screen]'` not in `game_screen.py` source; `'[PROMOTION]'` not in the source of the file that printed it. Integration — real 4-civ 56x56 game, 200 turns, capture stdout: no `[PROMOTION]` or `[game_screen]` lines; total living units at t200 ≤ `(3 + 2 * cities) * civs + margin` (exact bound computed from final city counts in the smoke itself).

**Commit:** `git add ai.py <promotion-file> pygame_app/screens/game_screen.py` / `feat: M81 military hygiene - army caps end the unit pileup, AI resolves promotions, debug spam removed`

- [ ] Run Task 0 loop for M81.

---

## Task 6: M82 — Expansion pacing (the land grab becomes an arc)

**Files:**
- Modify: `ai.py` (`_city_target` from M73, plus the settler-production gate that consumes it)
- Smoke: `C:/tmp/smoke_m82.py`

**Design.** M73's fair-share cap (`max(4, round(land / TILES_PER_CITY / civs))`) is correct as a *ceiling* but is reached by turn 25. Make the ceiling rise with time:

```python
    def _city_target(self, game) -> int:
        # fair-share computation as landed by M73 (unchanged) -> fair
        ramp = 4 + game.state.turn // 40   # +1 city allowance every 40 turns
        return min(fair, ramp)
```

(Exact integration with the current `_city_target` body from the fresh read; the M73 smoke `smoke_m73.py` asserts the fair-share formula string — pre-validation confirms it still passes, since the formula remains and only the return is clamped.) On Huge (fair=17) the AI reaches its final size around turn 520 instead of turn 25; on Small (fair=4) behavior is unchanged.

**Smoke assertions (`smoke_m82.py`):** unit level — stub game at turn 10 → target 4; turn 200 → 9; turn 800 → fair-share cap (17 with a stubbed land/civ count). Integration — real Huge-map game (7 AI), 100 turns: no AI owns more than 8 cities at t100 (audit baseline: 17 by t25).

**Commit:** `git add ai.py` / `feat: M82 expansion pacing - the fair-share city cap ramps over the campaign instead of being hit by turn 25`

- [ ] Run Task 0 loop for M82.

---

## Task 7: Phase 1 exit gate — prove the game is playable

No code. Re-run the audit suite against the post-M82 master.

- [ ] **Step 7.1:**

```bash
PYTHONIOENCODING=utf-8 python C:/tmp/audit_soak.py 1 96 1100 > /c/tmp/gate_soak_s1.log 2>&1
PYTHONIOENCODING=utf-8 python C:/tmp/audit_soak.py 2 96 1100 > /c/tmp/gate_soak_s2.log 2>&1
PYTHONIOENCODING=utf-8 python C:/tmp/audit_victory.py > /c/tmp/gate_victory.log 2>&1
PYTHONIOENCODING=utf-8 python C:/tmp/audit_saveload.py > /c/tmp/gate_saveload.log 2>&1
PYTHONIOENCODING=utf-8 python C:/tmp/audit_ui_sweep.py > /c/tmp/gate_ui.log 2>&1
```

- [ ] **Step 7.2 — Required outcomes (all must hold):**
  1. Both Huge soaks end with `[GAME OVER]` and a victory no later than turn 1000 (Time victory at worst).
  2. At least one war is declared somewhere in each soak log.
  3. Living units stay bounded (no monotonic pileup past the army caps).
  4. Some AI holds gold > 0 and faith > 0 at sampled turns; at least one religion exists by mid-game; some House's prestige exceeds its living ruler's.
  5. Legitimacy: at least one House (not necessarily the idle player) holds ≥ 40 in the late game.
  6. Save/load round-trip passes and the loaded game runs on.
  7. UI sweep still reports 0 failures.
- [ ] **Step 7.3:** Any miss becomes a tuning revision to the responsible mission (new brief, same loop) — not new scope. Iterate until the gate holds, then update memory with the gate result.

---

## Task 8: M83 — The play console

**Files:**
- Create: `play_console.py` (repo root, new file — CynCo new-file mission; the brief carries the complete file content, authored against post-gate code)
- Smoke: `C:/tmp/smoke_m83.py`

**Design.** One class, `PlayConsole`, plus `main()`:

- **CLI:** `python play_console.py --civ Rome --difficulty standard --map 96 --ais 7 --seed 42 --run-dir C:/tmp/campaign_X [--resume C:/tmp/campaign_X/autosave.pkl]`
- **Boot:** `SDL_VIDEODRIVER=dummy` / `SDL_AUDIODRIVER=dummy` before `import pygame`; construct `GameApp`, build the `Game` exactly as `NewGameDialog._start_game` does (same AI-civ sampling, `AIPlayer(name, difficulty)`, `TechManager()` per AI), register `GameScreen`, switch to it; on `--resume`, `Game.restore(path)` instead and attach to the app.
- **Frame stepping:** the audit's proven loop-body (`pygame.event.get` → `ui_manager.process_events` → `screen.handle_event` → `update` → `fill` → `draw` → `draw_ui` → `draw_overlay`), 3 frames per command, no `display.flip` needed for capture.
- **Protocol:** read a line from stdin, write one JSON object to stdout (`{"ok": true, ...}` or `{"ok": false, "error": ...}`), flush. Commands:
  - `state` — `{turn, budget, my: {civ, gold, faith, legitimacy, happiness, research: {current, progress, researched_count}, cities: [{name, pos, pop, production, unrest}], units: [{id, type, pos, hp, moves, commander}], characters: [{id, name, age, role, traits}], schemes, treasury_events}, world: {relations, wars, city_counts, victory_progress: {civ: {culture, prestige, techs, legitimacy}}}, events: [...last turn's turn_events...]}` — every field read from the same game attributes the popups read.
  - `build <city> <item>` / `research <tech>` / `move <unitId> <q> <r>` / `attack <unitId> <targetId>` / `fortify <unitId>` / `found <settlerId>` / `war <civ>` / `peace <civ>` / `marry <charA> <charB>` / `scheme <type> <targetCiv>` / `appoint <position> <charId>` / `dial <name> <value>` — each routed to the identical engine call its UI popup makes (call sites pinned in the brief from fresh reads of the popup handlers).
  - `end_turn` — drives the GameScreen turn path, autosaves `<run-dir>/autosave.pkl` via `game.checkpoint`, returns `{turn, events, game_over, victory}`.
  - `shot <name> [popup]` — optionally open the named popup (same `_open_popup` keys the keyboard uses), step frames, `pygame.image.save(app.screen, f"<run-dir>/<name>.png")`, close popup.
  - `save <name>` / `quit`.
- **Robustness:** every command wrapped in try/except returning `{"ok": false, "error": traceback}` — a bad command must never kill the process; the autosave means even a hard crash costs at most one turn.

**Smoke assertions (`smoke_m83.py`):** drive the console via `subprocess.Popen` pipes: boot Small map; `state` parses and shows turn 1 with ≥1 city and a settler; issue one `research`, one `build`, one `move`; `end_turn` x3 advances the turn and writes `autosave.pkl`; `shot t3 diplomacy` writes a PNG > 100KB; `quit`; relaunch with `--resume`, `state` shows turn 4; a garbage command returns `"ok": false` and the next command still works.

**Commit:** `git add play_console.py` / `feat: M83 play console - stdin/stdout protocol over the real engine and off-screen UI for terminal play with screenshots and checkpoints`

- [ ] Run Task 0 loop for M83.

---

## Task 9: The marathon (operational protocol, no code)

- [ ] **Step 9.1 — Setup.** `mkdir C:/tmp/campaign_2026-07/`; launch `play_console.py --civ <chosen> --difficulty standard --map 96 --ais 7 --seed <chosen> --run-dir C:/tmp/campaign_2026-07` as a background process. Create `campaign_log.md` in the run dir (format: `## Turn N — <headline>` entries with decisions + notable events).
- [ ] **Step 9.2 — Play loop (repeat until victory).** Each turn: `state` → decide across all fronts (production per city, research target, unit orders, diplomacy stance, court appointments, schemes/marriages, dials) → issue commands → `end_turn` → append log entry when anything notable happened. `shot tNNN` every 10 turns; extra shots (with relevant popup) at every war declaration/peace, wedding, succession, era change, religion founding, scheme resolution, and the victory screen. Victory-path choice is made in play (~turn 300 review) from the `victory_progress` telemetry.
- [ ] **Step 9.3 — Session cadence.** The run spans multiple work sessions; each session ends by confirming `autosave.pkl` is fresh and the log is current; each session starts with `--resume`.
- [ ] **Step 9.4 — Bug protocol.** On crash or misbehavior: capture traceback + reproduce from the autosave; author a CynCo hotfix mission (Task 0 loop, numbered M84+); resume from `autosave.pkl`; record the incident in the campaign log. Covered by the standing autonomous-dispatch authorization.
- [ ] **Step 9.5 — Deliverable.** The run dir holds the numbered screenshot album and `campaign_log.md` ending at the victory screen shot. Write a closing summary (victory type, turn, arc highlights) and update memory.

---

## Self-review notes

- **Spec coverage:** G1→Task 1, G2→Task 2, G3→Task 3, D1→Task 4, D2/D4→Task 5, D3→Task 6, exit gate→Task 7, console→Task 8, marathon→Task 9. D5/cosmetics ride along per spec (D5's silent-no-op feedback fits Task 8's error-returning protocol; the enum-in-HTML nit is logged for a later cleanup mission — not campaign-blocking).
- **Known deferred risk:** M78 picklability is settled in pre-validation before dispatch (Task 2 explicitly).
- **Baseline drift:** pytest tail may legitimately change per mission (e.g., victory-related tests); Task 0 Step 0.4 pins the new expected line per brief.
