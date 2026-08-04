# Gilded Interaction Model — Implementation Plan

> **For the implementer:** this plan is executed as six dispatched waves, one per
> section. Each wave is briefed from its section here, delivered as a commit, and
> then judged by a **withheld mutation gate that is built after delivery and is
> not in this document**. Do not go looking for it. A wave that tunes itself
> against the gate has measured the gate, not the code.

**Goal:** make every control in the Gilded UI answer the pointer, declare its
cost, explain its refusal, and actually execute — replacing eleven ad-hoc hit
structures and a hand-written dispatch cascade with two registries that the draw
side and the dispatch side both read.

**Architecture:** four models from the spec, built bottom-up. A `RegionSet` in
`widgets.py` collects interactive regions during draw and answers both clicks and
hover from one structure (§2). An `ACTIONS` registry in a new
`gilded/ui/actions.py` declares every verb's cost, eligibility and dispatch, so
the emitter and the handler cannot drift (§4). A pure `gilded/provenance.py`
carries causes alongside values, with a sum check that makes an incomplete
explanation a test failure (§3). A type/space/colour law makes the remaining
literals a lint failure (§5).

**Tech Stack:** Python 3, pygame-ce (custom-drawn — no CSS, no free hover
states), pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-03-gilded-interaction-model-design.md`
**Base:** `e439a3d` on `master` (spec commits on top of `28f57e7`).
**Suite floor:** `pytest gilded/tests` = **1261 passed**. Measured, not assumed.
A wave landing under 1261 has deleted a test and must name it and say why.

---

## How each wave is judged

Identical for all six. Stated once so no wave has to restate it, and so no wave
can quietly adopt a weaker bar.

1. `PYTHONDONTWRITEBYTECODE=1 python -m pytest gilded/tests -q` reports **≥ 1261
   passed, 0 failed**. Never fewer without an explicit account.
2. The wave's own new tests are present and named in the commit message.
3. **A withheld mutation gate is built after the commit lands.** Each rule the
   wave claims to establish is broken one at a time in a scratch checkout; the
   repo's own suite must go red for each. A rule the suite does not notice was
   not established, and the wave is not done.
4. **Every DoD item is gated or deleted.** An item no gate line checks teaches
   that requirements are optional.
5. **Assert the rule, not the constant.** A test that hard-codes a threshold
   proves nothing about the rule that uses it. Fixtures must use two distinct
   non-default inputs so a rule can be told from a constant.

---

## File structure

| File | Status | Responsibility |
|---|---|---|
| `gilded/ui/widgets.py` | modify | + `RegionState`, `Region`, `RegionSet`; + colour roles, type scale, spacing unit |
| `gilded/ui/actions.py` | **create** | `PlayerAction` and the `ACTIONS` registry — the single list both sides read |
| `gilded/ui/app.py` | modify | `MOUSEMOTION` branch; `_apply_action` dispatches through `ACTIONS` |
| `gilded/ui/broadsheet.py` | modify | eleven hit structures → one `RegionSet`; hover rendering |
| `gilded/provenance.py` | **create** | pure `Cause` / `Attributed`, no simulation, no `game.rng` |
| `gilded/society/ideology.py` | modify | `tick_legitimacy` returns its four causes |
| `gilded/dashboard.py` | modify | `MetricDelta` gains `causes` |
| `gilded/society/characters.py` | modify | `modify_opinion`'s reason reaches a bounded ledger |
| `gilded/chassis.py` | modify | `brewing_turns` exposed for render |

New tests: `gilded/tests/test_ui_regions.py`, `test_ui_actions.py`,
`test_provenance.py`, `test_ui_typography.py`.

`gilded/ui/broadsheet.py` is 1866 lines and does both drawing and input handling.
Wave I3 is the natural moment to separate them — the split is a consequence of
the migration, not an independent refactor. It is not a goal of any other wave.

---

## Wave I1 — the pointer, with no consumer

**Files:**
- Modify: `gilded/ui/widgets.py` (append after the palette block, `:21-32`)
- Modify: `gilded/ui/app.py:168-187` (`step_once`)
- Test: `gilded/tests/test_ui_regions.py` (create)

**Built with no consumer on purpose**, exactly as `widgets.py` itself was in
UI-legibility Wave 1. If the first user is one screen, the shape bends around
that screen's accidents and the other ten migrations fight it.

### The contract

```python
class RegionState(Enum):
    ENABLED = "enabled"          # the player may do this now
    DISABLED = "disabled"        # could, but not now — reason REQUIRED
    ACTIVE = "active"            # currently selected (open tab, chosen option)
    UNAVAILABLE = "unavailable"  # never applies to this player — no reason exists


@dataclass(frozen=True)
class Region:
    rect: pygame.Rect
    action: dict | None
    state: RegionState = RegionState.ENABLED
    reason: str = ""      # why DISABLED, in a sentence a player reads
    hint: str = ""        # what this does and what it costs
    group: str = ""       # owning tab or panel

    def __post_init__(self):
        if self.state is RegionState.DISABLED and not self.reason:
            raise ValueError("a DISABLED region must carry a reason")
        if self.state is RegionState.ENABLED and self.action is None:
            raise ValueError("an ENABLED region must carry an action")


class RegionSet:
    def __init__(self) -> None:
        self._regions: list[Region] = []

    def add(self, region: Region) -> None:
        self._regions.append(region)

    def at(self, pos) -> Region | None:
        for region in reversed(self._regions):
            if region.rect.collidepoint(pos):
                return region
        return None

    def clear(self) -> None:
        self._regions.clear()

    def __len__(self) -> int:
        return len(self._regions)
```

**Two decisions that must not be quietly reversed later:**

**`at()` scans in reverse — last added wins.** Regions are added in draw order,
so the last one added is the one drawn on top and the one the player can see. The
current cascade is first-match-wins and gets the modal case right only because
somebody remembered to check `_director_picker_hits` before the lists underneath
it (`broadsheet.py:1847`). Reverse order makes that correctness automatic instead
of remembered.

**`at()` returns DISABLED regions.** It must, or rule 2.4 is unimplementable —
the caller needs the region in hand to surface its `reason`. Filtering disabled
regions out of hit-testing is exactly the silent refusal this whole document
exists to kill. The *caller* checks `state`; `at()` reports what is under the
pointer and nothing more.

`__post_init__` is where rule 2.3 lives. A DISABLED region with no reason is not
defaulted, not logged — it raises. This is the entire silent-refusal defect class,
and it is cheaper to make it impossible to construct than to test for it eleven
times.

### `app.py` — the hover branch

In `step_once`, after the existing `MOUSEBUTTONDOWN` branch (`:180-183`):

```python
        if event.type == pygame.MOUSEMOTION:
            state.view.handle_hover(event.pos)
```

And `BroadsheetView` gains a no-op-safe default this wave — it stores the
position and nothing reads it yet:

```python
    def handle_hover(self, pos: Tuple[int, int]) -> None:
        self.hover_pos = pos
```

### Steps

- [ ] **1. Write the failing tests** — `gilded/tests/test_ui_regions.py`

```python
"""I1: the region registry — one structure answers both click and hover."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from gilded.ui.widgets import Region, RegionSet, RegionState


def _r(x, y, w=40, h=20, **kw):
    kw.setdefault("action", {"k": (x, y)})
    return Region(pygame.Rect(x, y, w, h), **kw)


def test_at_finds_a_region_under_the_point():
    rs = RegionSet()
    rs.add(_r(10, 10))
    assert rs.at((15, 15)).action == {"k": (10, 10)}


def test_at_misses_outside_every_rect():
    rs = RegionSet()
    rs.add(_r(10, 10))
    assert rs.at((500, 500)) is None


def test_last_added_wins_when_regions_overlap():
    """Regions are added in draw order, so the last is the one on top."""
    rs = RegionSet()
    rs.add(Region(pygame.Rect(0, 0, 100, 100), action={"under": True}))
    rs.add(Region(pygame.Rect(0, 0, 100, 100), action={"over": True}))
    assert rs.at((50, 50)).action == {"over": True}


def test_at_still_reports_a_disabled_region():
    """The caller needs it in hand to surface the reason; filtering it out here
    would recreate the silent refusal this registry exists to kill."""
    rs = RegionSet()
    rs.add(Region(pygame.Rect(0, 0, 50, 50), action={"x": 1},
                  state=RegionState.DISABLED, reason="No attention left."))
    hit = rs.at((10, 10))
    assert hit is not None
    assert hit.state is RegionState.DISABLED
    assert hit.reason == "No attention left."


def test_disabled_without_a_reason_is_impossible_to_construct():
    with pytest.raises(ValueError):
        Region(pygame.Rect(0, 0, 10, 10), action={"x": 1},
               state=RegionState.DISABLED)


def test_enabled_without_an_action_is_impossible_to_construct():
    with pytest.raises(ValueError):
        Region(pygame.Rect(0, 0, 10, 10), action=None,
               state=RegionState.ENABLED)


def test_unavailable_needs_no_reason_and_no_action():
    """UNAVAILABLE means no condition would ever turn it on, so there is
    nothing to explain — unlike DISABLED, which always owes a sentence."""
    r = Region(pygame.Rect(0, 0, 10, 10), action=None,
               state=RegionState.UNAVAILABLE)
    assert r.reason == ""


def test_clear_empties_the_set():
    rs = RegionSet()
    rs.add(_r(0, 0))
    rs.add(_r(50, 0))
    assert len(rs) == 2
    rs.clear()
    assert len(rs) == 0
    assert rs.at((5, 5)) is None
```

- [ ] **2. Run them and watch them fail**

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest gilded/tests/test_ui_regions.py -q
```
Expected: collection error, `ImportError: cannot import name 'Region'`. All eight
fail. If any passes, the import resolved to something unexpected — stop and find
out what.

- [ ] **3. Add `RegionState`, `Region`, `RegionSet` to `widgets.py`**, after the
      `COLUMN_GAP` block at `:32`. Exact code above. `widgets.py` imports pygame
      and stdlib only — keep it that way; this module is the bottom of the stack.

- [ ] **4. Run the new tests** — expect 8 passed.

- [ ] **5. Add the `MOUSEMOTION` branch and `handle_hover`.** Add this test to
      `gilded/tests/test_ui_app.py`:

```python
def test_mouse_motion_is_handled_and_records_the_position():
    state = _state()
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(120, 240)))
    assert app.step_once(state) is True
    assert state.view.hover_pos == (120, 240)
```

- [ ] **6. Run the whole suite**

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest gilded/tests -q
```
Expected: **1270 passed** (1261 + 8 + 1), 0 failed.

- [ ] **7. Commit**

```bash
git add gilded/ui/widgets.py gilded/ui/app.py \
        gilded/tests/test_ui_regions.py gilded/tests/test_ui_app.py
git commit -m "I1: a region registry and a pointer that is heard"
```

### Wave I1 Definition of Done

1. `RegionState` has exactly the four members ENABLED / DISABLED / ACTIVE /
   UNAVAILABLE.
2. `Region` carries `rect, action, state, reason, hint, group`.
3. Constructing a DISABLED `Region` with an empty `reason` raises.
4. Constructing an ENABLED `Region` with `action=None` raises.
5. `RegionSet.at()` returns the **last-added** matching region.
6. `RegionSet.at()` returns DISABLED regions rather than skipping them.
7. `app.step_once` handles `pygame.MOUSEMOTION`.
8. **No existing behaviour changes.** No caller uses `RegionSet` this wave.
9. `widgets.py` still imports only pygame and stdlib.

---

## Wave I2 — one registry, three verbs, byte-identical behaviour

**Files:**
- Create: `gilded/ui/actions.py`
- Modify: `gilded/ui/app.py:72-152` (`_apply_action`)
- Test: `gilded/tests/test_ui_actions.py` (create)

**The registry lands before anything is migrated onto it**, and it covers only
the verbs that already work. This wave must change *nothing a player can see*.
That constraint is what makes I3's migration provably behaviour-preserving rather
than a rewrite with a nice story.

### The contract

```python
@dataclass(frozen=True)
class PlayerAction:
    key: str
    label: str
    domain: str                  # "commerce", "diplomacy", ... or "view"
    attention_cost: int
    gold_cost: Callable[..., int] | int
    eligible: Callable[..., tuple[bool, str]]
    dispatch: Callable[..., list[str]]


ACTIONS: dict[str, PlayerAction] = { ... }
```

`eligible(game, house, **kw) -> (bool, reason)`. The `reason` is a **sentence a
player reads**, and it feeds straight into `Region.reason`. This is where §2 and
§4 meet: the same string that greys the button explains it.

**`eligible` must return a reason whenever it returns `False`, and an empty
string when it returns `True`.** A refusal with no sentence is the silent
refusal again, one layer down.

### The three verbs that exist today, and the three that are view-local

This wave's `ACTIONS` holds **six** entries:

| key | domain | attention | today's dispatch lives at |
|---|---|---|---|
| `end_turn` | `turn` | 0 | `app.py:78-84` |
| `expand_enterprise` | from `INITIATIVES["expand_enterprise"][0]` | 1 | `app.py:111-126` |
| `appoint_director` | from `INITIATIVES["appoint_director"][0]` | 1 | `app.py:132-152` |
| `place_informant` | `diplomacy` | 1 | `app.py:85-93` |
| `set_stance` | `policy` | 0 | `app.py:94-98` |
| `rule` | petition's own domain | 1 | `app.py:99-110` |

plus the four **view-local** keys, carried with `domain="view"`,
`attention_cost=0`, and a `dispatch` that returns `[]`:
`tab`, `select_province`, `open_director_picker`, `toggle_narrate`,
`close_director_picker`.

**Why view-local keys are in the registry rather than exempted from it.**
`handle_click` mutates the view and *then* returns these keys;
`_apply_action` receives them and does nothing. They are not dead buttons — the
click already worked. But they are emitted keys, and §4.2 check 1 quantifies over
emitted keys. Granting them an exemption clause reopens exactly the hole the four
real dead buttons came through: "this key is fine to be unhandled" is the
sentence that has to become impossible to write. Carrying them with an explicit
`domain="view"` documents the fact instead of hiding it.

### The two checks

```python
def test_every_emitted_action_key_is_in_the_registry():
    """§4.2 check 1 — the arithmetic difference that produced four dead
    buttons."""
    emitted = _all_emitted_keys()          # walks every tab of a fixture view
    missing = sorted(emitted - set(ACTIONS))
    assert missing == [], f"emitted but unregistered: {missing}"


def test_every_registered_action_dispatches_without_raising():
    """§4.2 check 2 — at a fixture where eligible() is True."""
    for key, act in sorted(ACTIONS.items()):
        game, house, kw = _fixture_for(key)
        ok, why = act.eligible(game, house, **kw)
        assert ok, f"{key}: no fixture makes this eligible ({why})"
        out = act.dispatch(game, house, **kw)
        assert isinstance(out, list)
        assert all(isinstance(line, str) for line in out)
```

Check 1 **fails today by four** — `buy_shares`, `sell_shares`,
`found_enterprise`, `defend_buyout` (spec §1.2). In this wave it is committed as:

```python
@pytest.mark.xfail(
    strict=True,
    reason="I4 wires buy_shares, sell_shares, found_enterprise, defend_buyout; "
           "until then broadsheet emits four keys no registry entry covers",
)
def test_every_emitted_action_key_is_in_the_registry():
    ...
```

**`strict=True` is the whole point.** A non-strict xfail goes on quietly
excusing a defect after the defect is fixed. A strict one turns the suite **red**
the moment I4's wiring makes the check pass, so the marker cannot outlive its
reason. This is the only sanctioned `xfail` in the six waves; a second one is a
design problem to raise, not to add.

For check 2's `_fixture_for(key)`: if some key has no fixture at which
`eligible()` can be made true, it is not "hard to test" — it is unreachable in
play. Spec §6 rule 4 applies: **delete it, do not manufacture the input.** Raise
it rather than skipping the key.

### Steps

- [ ] **1.** Write `gilded/tests/test_ui_actions.py` with both checks, check 1
      marked `xfail(strict=True)`, plus one behaviour-preservation test per verb
      asserting the same post-state as today's `_apply_action` (e.g. `end_turn`
      advances `game.turn` by 1 and sets `view.active_tab == "Briefing"`;
      `rule` decrements `game.attention[house]` by 1 and removes the petition
      from `game.docket_by_house[house]`).
- [ ] **2.** Run: expect the registry import to fail.
- [ ] **3.** Create `gilded/ui/actions.py`. **Move** each verb's body out of
      `_apply_action` into its `dispatch`; do not copy. Two implementations of
      one rule means mutations against the loser always survive, and the
      duplicate becomes unmeasurable.
- [ ] **4.** Rewrite `_apply_action` as a lookup:

```python
def _apply_action(state: AppState, action: dict) -> None:
    for key, act in ((k, ACTIONS[k]) for k in action if k in ACTIONS):
        if act.domain == "view":
            return
        ok, _why = act.eligible(state.game, state.house, **_kw(state, action, key))
        if not ok:
            return
        act.dispatch(state.game, state.house, **_kw(state, action, key))
        return
```
- [ ] **5.** Run the full suite. Expect **≥ 1270 passed, 1 xfailed, 0 failed.**
      Every pre-existing `test_ui_app.py` assertion must still pass **unmodified**
      — if one needs editing, behaviour changed and the wave has missed its bar.
- [ ] **6.** Commit: `I2: one action registry, three verbs, no visible change`

### Wave I2 Definition of Done

1. `gilded/ui/actions.py` exists with `PlayerAction` and `ACTIONS`.
2. `ACTIONS` covers the six wired verbs and the five view-local keys.
3. Every `eligible()` returns a non-empty reason when it returns `False`, and
   `""` when `True`.
4. `_apply_action` contains **no** per-verb `if` branches — dispatch is a lookup.
5. Each verb's logic exists **once**; the old bodies are moved, not copied.
6. §4.2 check 2 passes for every registered key.
7. §4.2 check 1 is present, `xfail(strict=True)`, naming the four missing keys.
8. **Every pre-existing test in `test_ui_app.py` passes unmodified.**
9. Suite ≥ 1270 passed, 1 xfailed.

---

## Wave I3 — eleven structures become one

**Files:**
- Modify: `gilded/ui/broadsheet.py` (eleven populate sites; `handle_click` `:1811-1866`)
- Test: `gilded/tests/test_ui_broadsheet.py` (extend)

Migrate in this order, committing after each so a bisect lands on one tab:

| # | Structure | Populated at | Tab |
|---|---|---|---|
| 1 | `_tab_rects` | `:840, :843` | chrome |
| 2 | `_narrate_rect` | `:899` | chrome |
| 3 | `_end_turn_rect` | `:904` | chrome |
| 4 | `_option_hits` | `:1006` | Docket / Briefing |
| 5 | `_exec_hits` | `:1017` | Docket / Briefing |
| 6 | `_dial_hits` | `:1322` | Policies |
| 7 | `_atlas_polys` | `:1364` | Atlas |
| 8 | `_informant_hits` | `:1457, :1470` | Powers |
| 9 | `_enterprise_hits` | `:1713` | Enterprises |
| 10 | `_appoint_hits` | `:1730` | Enterprises |
| 11 | `_director_picker_hits` | `:1753, :1778` | Enterprises (modal) |

**A partially migrated tree must pass.** `handle_click` consults the `RegionSet`
first and falls through to whatever has not moved yet. The fallback cascade is
deleted only when the last structure is gone — and its deletion is item 11's
proof.

**Two of these are not plain rects and must not be forced into one.**
`_atlas_polys` is hit by `pick_province`, a polygon test, not `collidepoint`.
Region hit-testing stays rectangular; the Atlas registers a region whose action
is resolved by the existing polygon call. Rewriting province picking as
rectangles would be a behaviour change smuggled inside a refactor.
`_dial_hits` computes a *value from the click position within the rect*
(`:1833-1836`) — the region carries the dial key and the same arithmetic runs on
the region's rect. Do not round-trip it through a different formula.

### The two things that must be true after each step

```python
def test_every_registered_region_action_is_a_known_key():
    """The registry cannot become a second place for keys to hide."""
    view = _view()
    view.draw(_surface())
    for region in view.regions:
        if region.action is not None:
            assert set(region.action) & set(ACTIONS), region.action


def test_hover_over_end_turn_reports_the_end_turn_region():
    view = _view()
    view.draw(_surface())
    hit = view.regions.at(view._end_turn_center())
    assert hit is not None and "end_turn" in hit.action
```

Plus, for **every** migrated structure, a click test asserting the identical
return value `handle_click` gives today. These are the regression net; write them
against the current behaviour *before* moving the structure.

### The modal is the one to be careful with

`_director_picker_hits` is checked **first** in today's cascade
(`broadsheet.py:1847`) because it is an overlay. Under the registry it is
correct by construction — it is drawn last, so `at()`'s reverse scan finds it
first. **Add a test that fails if the ordering regresses**, because this is the
one case where "last added wins" is load-bearing rather than incidental:

```python
def test_the_open_director_picker_shadows_the_cards_beneath_it():
    view = _view_with_open_director_picker()
    view.draw(_surface())
    pos = view._a_point_where_picker_overlaps_a_card()
    assert "appoint_director" in view.regions.at(pos).action
```

### Steps

- [ ] **1.** Add `self.regions = RegionSet()` to `BroadsheetView.__init__`; clear
      it at the top of `draw()`. Note there are currently **two** clear sites
      (`:763-775` and `:799-805`) — one registry means one clear. Collapsing them
      is part of this wave.
- [ ] **2.** Rewrite `handle_click` to consult `self.regions.at(pos)` first,
      returning `None` for a region whose `state is RegionState.DISABLED` after
      recording `region.reason` on the view for render.
- [ ] **3.** Point `handle_hover` (from I1) at `self.regions.at(pos)` and store
      the hovered `Region`, not just the position.
- [ ] **4.–14.** One structure per commit, in the table's order. For each: write
      the click-equivalence test, watch it pass against current code, move the
      structure, watch it still pass.
- [ ] **15.** Delete the fallback cascade and every one of the eleven attributes.
- [ ] **16.** Render the hover state: ENABLED regions lighten under the pointer;
      DISABLED regions show their `reason`.
- [ ] **17.** Full suite; commit.

### Wave I3 Definition of Done

1. All eleven structures are gone from `BroadsheetView`. `grep` for each name
   returns nothing outside the git history.
2. `handle_click` consults only `self.regions`; the per-tab cascade is deleted.
3. `handle_hover` resolves a `Region` and stores it.
4. Every click that worked at `e439a3d` still returns the identical action.
5. A hovered ENABLED region renders differently from an unhovered one.
6. A hovered DISABLED region renders its `reason`.
7. The open director picker shadows the cards beneath it, by draw order.
8. `draw()` clears the registry in exactly one place.
9. Atlas province picking still goes through `pick_province`; dial values still
   come from the same arithmetic.

---

## Wave I4 — the wave where the game visibly changes

**Files:**
- Modify: `gilded/ui/actions.py`, `gilded/ui/broadsheet.py`
- Test: `gilded/tests/test_ui_actions.py`

Everything before this was scaffolding. This wave wires the four dead buttons and
the twelve unreachable verbs, and **removes the `xfail`**.

### The four dead buttons first

`buy_shares` (`broadsheet.py:1561`), `sell_shares` (`:1562`),
`found_enterprise` (`:1564`), `defend_buyout` (`:1574`). Their simulation
implementations already exist in `docket.INITIATIVES` — this is wiring, not new
mechanics.

### Then the remaining unreachable verbs

`propose_marriage`, `build_rail`, `start_scheme`, `tour_province`,
`adjust_garrison`, `acquire_minor`, `declare_war`, `negotiate_peace`,
`start_takeover`. Each needs a `PlayerAction` entry and a surface that emits it.
**Where a verb has no natural home in an existing tab, say so and stop** — that
is a Stage 6/7 surface question, and inventing a tab here would be new domain
content, which spec §8 puts out of scope. Wire what has a home; report what does
not.

### The bar for "wired"

Not "the click returns without raising". For each verb, a test at a fixture
asserting the sim **actually moved**:

```python
def test_buy_shares_moves_the_share_register():
    game, house, kw = _fixture_for("buy_shares")
    before = _holding(game, house, kw["eid"])
    ACTIONS["buy_shares"].dispatch(game, house, **kw)
    assert _holding(game, house, kw["eid"]) > before
```

A test asserting only that `dispatch` returned a list would pass against a verb
that does nothing — that is the hollow shape at the file seam that let the share
buttons ship dead in the first place, with tests asserting
`enterprise_actions()` *returned* the dicts and nothing asserting anything could
*execute* them.

### Steps

- [ ] **1.** Add the four dead-button entries to `ACTIONS`, each with a real
      `eligible` (gold, attention, ownership) returning a player-readable refusal.
- [ ] **2.** Run check 1. It now passes — and because the xfail is `strict`, the
      suite goes **red**. That is the marker doing its job.
- [ ] **3.** Remove the `xfail` marker. Suite green.
- [ ] **4.** One commit per remaining verb, each with its sim-moved test.
- [ ] **5.** Every button renders its cost (`"Found Enterprise · 1 attention ·
      250g"`) and greys with its reason when ineligible.
- [ ] **6.** Full suite; commit.

### Wave I4 Definition of Done

1. §4.2 check 1 passes and **the `xfail` marker is deleted**, not left in place.
2. `buy_shares`, `sell_shares`, `found_enterprise`, `defend_buyout` each have a
   test proving the simulation state changed.
3. Every newly wired verb has such a test. No verb is accepted on a
   returns-a-list assertion.
4. Every action button shows its attention and gold cost before commitment.
5. An ineligible button is DISABLED with a reason, never absent and never silent.
6. Any verb with no natural surface is **named in the commit message as
   deferred**, with the reason. Not silently skipped.
7. **No simulation formula changed** (spec §3.4). This wave wires; it does not
   rebalance.

---

## Wave I5 — numbers travel with their causes

**Files:**
- Create: `gilded/provenance.py`
- Modify: `gilded/society/ideology.py:85-97`, `gilded/dashboard.py`,
  `gilded/society/characters.py:333-338`, `gilded/chassis.py:89,357-362`
- Test: `gilded/tests/test_provenance.py` (create)

### The contract

```python
@dataclass(frozen=True)
class Cause:
    label: str      # "Tide pressure" — what a player reads
    amount: float   # -0.53
    source: str     # "ideology.tick_legitimacy" — what a developer reads


@dataclass(frozen=True)
class Attributed:
    value: float
    previous: float
    causes: tuple[Cause, ...] = ()

    @property
    def delta(self) -> float:
        return self.value - self.previous

    def check(self, tol: float = 1e-6) -> bool:
        return abs(sum(c.amount for c in self.causes) - self.delta) <= tol
```

Pure data. No simulation, no `game.rng`, no imports from `gilded.chassis`.

### The rule with teeth

`sum(amount for causes) == delta` within **`1e-6`**. Without it the model is a
decorative label: a number could fall by 3.1 while its stated causes account for
2.4 and nobody would know. The tolerance is fixed here rather than left open,
because a tolerance chosen after the fact is chosen to make the current code
pass. If a real site cannot meet `1e-6`, **raise it as a finding** — do not widen
the bar.

### The four sites

| Site | Today | Required |
|---|---|---|
| `society/ideology.py:85-97 tick_legitimacy` | three concurrent forces + a silent clamp → one float | three named `Cause`s, plus a clamp cause when it bites, summing to the delta |
| `dashboard.py MetricDelta` | `change, direction` | `+ causes` |
| `society/characters.py:333-338 modify_opinion` | reason returned, discarded at **36** call sites | reason lands in a bounded per-character ledger |
| `chassis.py:89,357-362 brewing_turns` | never rendered | a visible countdown naming both preconditions |

**`brewing_turns` is the single highest-priority item in the whole plan.** The
revolution fires on the third consecutive qualifying turn and the player is never
told the count began. A revolution that arrives unannounced after a secret
three-turn counter is the most player-hostile behaviour any of the four
inventories found. If this wave runs short, this is the item that ships.

`modify_opinion`'s ledger is **bounded** — a per-character ring of the last N
reasons. An unbounded log on a century-long game with dozens of characters is a
memory leak wearing an explanation's clothes.

### Read `tick_legitimacy` before decomposing it — two traps

```python
def tick_legitimacy(current, happiness, tide=None, fresh_atrocities=0.0) -> float:
    if happiness >= 0:
        current += (LEGITIMACY_HAPPY_RECOVERY
                    + LEGITIMACY_HAPPY_BONUS * min(happiness, 20) / 20.0)
    else:
        current -= LEGITIMACY_UNHAPPY_DRAIN * float(-happiness)
    current -= LEGITIMACY_ATROCITY_DRAIN * fresh_atrocities
    if tide is not None:
        current -= LEGITIMACY_TIDE_DRAIN * (tide.level / 100.0)
    return max(0.0, min(LEGITIMACY_MAX, current))   # <-- :97
```

**Trap 1 — there are three concurrent causes, not four.** The happy-recovery and
unhappy-drain arms are an `if/else`; they can never both fire. The spec's phrase
"four distinct forces" counts *contentment* as two because it has two arms. At
any single call the causes are: contentment (recovery **or** drain), atrocity
drain, tide drain. **Three.** A test asserting `len(causes) == 4` can never pass,
and the natural repair — emitting a zero-amount cause for the arm that did not
fire — would put a cause on screen reading "Unhappiness: 0.0" for a content
realm, which is worse than the bare number this work exists to replace.

**Trap 2 — the clamp at `:97` breaks the sum check, correctly.** When the result
clamps at `0.0` or `LEGITIMACY_MAX`, the causes sum to more than the delta, by
construction. `check()` will fail, and it *should* — the clamp really is part of
what moved the number. **The clamp is therefore a cause**, emitted only when it
bites:

```python
Cause("Already at the floor", +clamped_away, "ideology.tick_legitimacy:clamp")
```

This is the discovery worth having: a legitimacy that "stops falling" is
something a player currently experiences as the meter lying to them. Naming the
clamp turns a confusing non-event into an explanation.

Both traps were found by reading `:85-97` rather than trusting the spec's prose
summary. Read the site before decomposing any of the four.

### The fixture must discriminate

Two fixtures, because one cannot cover both traps:

```python
def test_causes_sum_to_the_delta_with_every_force_live_and_no_clamp():
    """All three causes non-zero, of different magnitudes, result well inside
    the range so the clamp cannot fire. A fixture where two forces are zero
    cannot tell a three-cause decomposition from a one-cause one."""
    tide = _tide(level=44)
    result = tick_legitimacy(current=52.0, happiness=31, tide=tide,
                             fresh_atrocities=2.0)
    assert len(result.causes) == 3
    assert all(c.amount != 0.0 for c in result.causes)
    assert len({abs(c.amount) for c in result.causes}) == 3   # distinguishable
    assert result.check()
    assert 0.0 < result.value < LEGITIMACY_MAX                # premise: unclamped


def test_the_clamp_is_itself_a_named_cause():
    """A House at 1.0 legitimacy taking a heavy atrocity hit stops at the
    floor. The causes must account for the stop, or they sum to more than
    the delta and check() fails."""
    result = tick_legitimacy(current=1.0, happiness=-40, tide=None,
                             fresh_atrocities=5.0)
    assert result.value == 0.0
    assert any("floor" in c.label.lower() for c in result.causes)
    assert result.check()
```

The `assert 0.0 < result.value < LEGITIMACY_MAX` line in the first test is a
**premise**, not another thing being measured: it states that this fixture is
genuinely unclamped, so that a passing `check()` means the three causes are
right rather than that the clamp happened to absorb the error.

### Steps

- [ ] **1.** Create `gilded/provenance.py` + `test_provenance.py` covering
      `delta`, `check()` passing, `check()` **failing** on an incomplete cause
      list, and the `1e-6` boundary from both sides.
- [ ] **2.** `chassis.brewing_turns` → rendered countdown, naming both
      preconditions. Ship this first.
- [ ] **3.** `tick_legitimacy` returns `Attributed` with four causes.
- [ ] **4.** `MetricDelta` gains `causes`; the dashboard renders them.
- [ ] **5.** `modify_opinion`'s reason reaches a bounded ledger; the 36 call
      sites keep working unchanged.
- [ ] **6.** Full suite; commit.

### Wave I5 Definition of Done

1. `gilded/provenance.py` is pure — no `gilded.chassis` import, no `game.rng`.
2. `Attributed.check()` uses tolerance `1e-6` and has a test that **fails** it.
3. `tick_legitimacy` returns **three** non-zero causes of distinguishable
   magnitude at an unclamped fixture where every force is live, and they sum to
   the delta. It returns an additional named clamp cause when `:97` bites, and
   `check()` passes there too.
4. `brewing_turns` is visible to the player with both preconditions named.
5. `modify_opinion`'s reason is retained in a **bounded** structure.
6. **No simulation formula changed.** This model reports numbers; it does not
   rebalance them. Balance is Stage 8, where it can be argued on its own
   evidence — and a legibility pass that quietly alters behaviour destroys the
   ability to attribute any later change.

---

## Wave I6 — type, space, colour

**Files:**
- Modify: `gilded/ui/widgets.py`, `gilded/ui/broadsheet.py`, `gilded/ui/atlas_view.py`
- Test: `gilded/tests/test_ui_typography.py` (create)

**The floors are measured, not assumed** (spec §9.1):

- **35 literal RGB tuples** outside `widgets.py` — 18 in `broadsheet.py`, 17 in
  `atlas_view.py`, none elsewhere in `gilded/ui/`.
- **12 distinct font sizes** across 30 literal `font(n)` calls: 11, 12, 14, 15,
  16, 17, 18, 19, 22, 24, 26, 30.

Small enough to reach zero in one wave, which is why the lint is stated as an
absolute with no threshold to negotiate. It fails at base by 35.

- [ ] **1.** Add `POSITIVE`, `NEGATIVE`, `WARNING`, `DISABLED`, `HOVER` to the
      `widgets.py` palette alongside the existing `TONES` dict (`:39-45`) —
      reuse those values where they already say the right thing rather than
      inventing a second vocabulary for the same five meanings.
- [ ] **2.** Write the lint test:

```python
RGB = re.compile(r"\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)")

def test_no_literal_rgb_outside_widgets():
    offenders = {}
    for path in glob("gilded/ui/**/*.py", recursive=True):
        if os.path.basename(path) == "widgets.py":
            continue
        hits = [i + 1 for i, line in enumerate(open(path, encoding="utf-8"))
                if RGB.search(line)]
        if hits:
            offenders[path] = hits
    assert offenders == {}, f"literal colours outside the palette: {offenders}"
```

      Run it now: **it must fail, naming 35 lines.** A lint that is green before
      the work exists measures nothing.
- [ ] **3.** Replace all 35, file by file, committing per file.
- [ ] **4.** Collapse the 12 sizes to a named scale. **Derive it**: map the 30
      existing call sites onto the fewest sizes no reviewer can tell apart on
      screen. Do not invent a scale and impose it — a scale chosen before the
      current usage is measured silently redesigns every screen under the banner
      of consistency.
- [ ] **5.** One spacing unit, likewise derived: the value most existing
      paddings are already near, so the migration moves the fewest pixels.
      `MEASURE_CHARS = 66` and `COLUMN_GAP = 24` are the right instinct already —
      generalise, do not replace.
- [ ] **6.** `Meter`, `Chip`, `Panel` gain the four `RegionState` styles so no
      screen hand-rolls its own grey.
- [ ] **7.** Period discipline: rules and hairlines rather than drop shadows,
      small caps for headers, tabular figures for anything in a column. The 1900
      broadsheet framing is the strongest art idea in the project and is
      currently under-committed to.
- [ ] **8.** Full suite; commit.

### Wave I6 Definition of Done

1. Zero literal RGB tuples in `gilded/ui/` outside `widgets.py`. The lint test
   exists and failed by 35 before the wave.
2. The type scale is a named set, derived from the existing 30 call sites, and no
   literal `font(n)` with a bare integer remains at a call site.
3. One spacing constant; paddings and gaps are multiples of it.
4. `Meter`, `Chip`, `Panel` each render all four `RegionState` styles.
5. No layout is redesigned. This wave changes how values are *named*, not what
   the screens look like beyond the state styles.

---

## Out of scope for all six waves

Restated from spec §8 so no wave has to decide it alone:

- **Any simulation formula change.** Balance is Stage 8.
- **Retuning the attention economy** — what three attention points *should* be,
  whether petitions and initiatives share a pool, whether the budget scales
  across the century. Stage 7, after the game is reachable enough to play.
- **New domain content** — new verbs, new events, new systems. These waves make
  the *existing* surface reachable and legible. They add no mechanics.
- **A graphical family tree, animated transitions, sound.**

---

## Order, and why it is this order

**I1 has no consumer** so the registry's shape is not bent around one screen's
accidents. **I2 precedes I3** so the registry exists before anything migrates
onto it, and the migration is provably behaviour-preserving. **I3 precedes I4**
so the dead buttons are wired into a structure that can prove they are wired,
rather than into the cascade that lost them. **I4 is the first wave the player
can feel.** I5 and I6 are independent of each other and of I4; either may run
first if I4 stalls.

If the plan must be cut short, ship **I5 step 2** — the `brewing_turns`
countdown — regardless of where the rest stands. It is one render of a number the
game already computes, and it removes the single most player-hostile behaviour in
the build.
