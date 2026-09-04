"""Event chains (M72, spec 7): authored multi-step story beats.

A chain arms when its trigger reads something true in the live game
state, then plays its steps over the following turns. Deterministic:
no RNG, so seeded runs stay reproducible.

C7.3 branching: a step may carry a `file_petition` callback. When that
step plays, the chain holds at it: the petition is filed onto the house's
docket (kind "chain:<chain_id>", domain "chain") and the chain waits for
the ruling. The ruling's option apply() stores the chosen key in
`ac.ctx["choice"]` and removes the petition; on the next tick
`on_choice(game, ac, key)` runs and redirects the chain (rewriting
`ac.step_idx`). A petition the player never rules festers out: after
FESTER_TURNS it resolves to the step's `fester_key` (the ugliest setting),
mirroring the docket's own unattended-paper rule.
"""

from typing import Any, Callable, Dict, List, Optional

from gilded.docket import FESTER_TURNS, RulingContext


class ChainStep:
    """One beat: a template line, an optional effect, and a delay.

    `file_petition(game, ac) -> Optional[Petition]` files a petition onto
    the player's docket when this step plays and holds the chain here until
    it is ruled. The option's apply() must store the chosen key in
    `ac.ctx["choice"]`. `on_choice(game, ac, key)` then runs (key may be
    None if the petition festered or was lost) and may rewrite `ac.steps` /
    `ac.step_idx` to redirect the chain. `text` may also be a callable
    `ctx -> str` for lines that depend on the choice.
    """

    def __init__(self, text: str,
                 apply: Optional[Callable[[Any, Dict[str, Any]], List[str]]] = None,
                 delay: int = 1,
                 file_petition: Optional[Callable[[Any, "ActiveChain"], Any]] = None,
                 on_choice: Optional[Callable[[Any, "ActiveChain", Optional[str]], None]] = None,
                 fester_key: Optional[str] = None):
        self.text = text
        self.apply = apply
        self.delay = delay          # turns after the previous beat
        self.file_petition = file_petition
        self.on_choice = on_choice
        self.fester_key = fester_key  # ruling the step defaults to if never ruled


class ChainDef:
    """A chain: a trigger over game state and the steps it unleashes."""

    def __init__(self, chain_id: str,
                 trigger: Callable[[Any], Optional[Dict[str, Any]]],
                 steps: List[ChainStep], once: bool = True):
        self.chain_id = chain_id
        self.trigger = trigger      # game -> ctx dict (truthy) or None
        self.steps = steps
        self.once = once


class ActiveChain:
    """A chain in motion: its context and where it stands."""

    def __init__(self, cdef: ChainDef, ctx: Dict[str, Any]):
        self.cdef = cdef
        self.ctx = ctx
        self.step_idx = 0
        self.steps = list(cdef.steps)   # a choice step may redirect these
        self.wait = cdef.steps[0].delay
        self.choice: Optional[str] = None
        self.choice_step: Optional[int] = None
        self.waiting_petition: Optional[int] = None   # pid while a step waits


class ChainManager:
    """Arms triggers and advances active chains one tick at a time."""

    def __init__(self, defs: Optional[List[ChainDef]] = None):
        self.defs: List[ChainDef] = list(defs or [])
        self.active: List[ActiveChain] = []
        self.fired: set = set()
        self.last_steps: List[tuple] = []
        self.pending_petitions: List[tuple] = []    # (house, Petition) to file

    def tick(self, game: Any) -> List[str]:
        """One turn: arm new chains, then advance the ones in motion.

        Also fills `last_steps` with the (chain_id, line, face) tuples for
        every step that played this turn, so the chassis can record them as
        first-class beats (C7) in one place. Branching steps that file a
        petition buffer it in `pending_petitions`; call `file_pending`
        during open_turn to surface it on the docket.
        """
        msgs: List[str] = []
        self.last_steps = []
        if getattr(game, "turn", 0) < 1:
            return msgs
        for cdef in self.defs:
            if cdef.once and cdef.chain_id in self.fired:
                continue
            if any(ac.cdef is cdef for ac in self.active):
                continue
            ctx = cdef.trigger(game)
            if ctx:
                self.fired.add(cdef.chain_id)
                self.active.append(ActiveChain(cdef, ctx))
        done: List[ActiveChain] = []
        for ac in self.active:
            if ac.waiting_petition is not None:
                continue   # held at a choice step; resolve_pending advances it
            ac.wait -= 1
            if ac.wait > 0:
                continue
            step = ac.steps[ac.step_idx]
            line = _line_of(step, ac)
            msgs.append(line)
            self.last_steps.append((ac.cdef.chain_id, line, _face_of(ac.ctx)))
            if step.apply is not None:
                extra = step.apply(game, ac.ctx)
                if extra:
                    msgs.extend(extra)
            if step.file_petition is not None and ac.waiting_petition is None:
                # Hold at this step: the choice is the player's.
                petition = step.file_petition(game, ac)
                if petition is not None:
                    ac.waiting_petition = petition.pid
                    house = ac.ctx.get("house") or (
                        game.player_house if hasattr(game, "player_house") else None)
                    self.pending_petitions.append((house, petition))
                    ac.wait = step.delay
                    continue
            ac.step_idx += 1
            if ac.step_idx >= len(ac.steps):
                done.append(ac)
            else:
                ac.wait = ac.steps[ac.step_idx].delay
        for ac in done:
            self.active.remove(ac)
        return msgs

    def file_pending(self, game: Any) -> None:
        """Surface buffered chain petitions on the docket (call from
        open_turn, after the docket is rebuilt, so they survive)."""
        if not self.pending_petitions:
            return
        player = next((h for h in sorted(game.houses)
                       if game.houses[h].is_player), None)
        if player is None:
            self.pending_petitions.clear()
            return
        docket = game.docket_by_house.setdefault(player, [])
        for house, petition in self.pending_petitions:
            if house is not None:
                petition.house = house      # the matter concerns that house
            if not any(p.pid == petition.pid for p in docket):
                docket.append(petition)
        self.pending_petitions.clear()

    def resolve_pending(self, game: Any) -> List[str]:
        """Chain petitions the player never touched: once they have festered
        as long as the docket's own unattended paper, the step's fester_key
        option runs at the fumbling scale (the ugliest branch) and the chain
        redirects. Also advances chains whose petition the player already
        ruled (the option's apply stores the chosen branch on the
        petition's ref and removes the paper). Called from the chassis
        after resolve_unattended, which skipped chain petitions."""
        msgs: List[str] = []
        for ac in list(self.active):
            if ac.waiting_petition is None:
                continue
            player = next((h for h in sorted(game.houses)
                           if game.houses[h].is_player), None)
            docket = game.docket_by_house.get(player, []) if player else []
            pet = next((p for p in docket if p.pid == ac.waiting_petition),
                       None)
            step = ac.steps[ac.step_idx]
            choice = ac.ctx.get("choice")
            # Ruled by the player: the option's apply already ran (through
            # docket.rule) and left the chosen branch in the chain's ctx.
            # Otherwise wait until the paper has festered as long as the
            # docket's own unattended paper.
            if choice is None and (
                    pet is None or pet.turns_waiting < FESTER_TURNS):
                continue
            if choice is not None:
                key = choice
                if pet is not None:
                    docket.remove(pet)
            else:
                # Festering out: the ugliest branch at the fumbling scale.
                key = step.fester_key
                opt = next((o for o in (pet.options if pet else [])
                            if o.key == key), None)
                if opt is not None and player is not None:
                    realm = game.realms.get(player)
                    if realm is not None:
                        ctx = RulingContext(game, player, realm.ruler,
                                            game.rng, 0.5)
                        msgs.extend(opt.apply(ctx))
            ac.choice = key
            ac.choice_step = ac.step_idx
            ac.waiting_petition = None
            ac.ctx.pop("choice", None)
            if step.on_choice is not None:
                before = ac.step_idx
                step.on_choice(game, ac, key)
                if ac.step_idx == before:
                    # A redirect rewrites ac.steps and lands ac.step_idx on
                    # the new step; only advance when it did not.
                    ac.step_idx += 1
                ac.wait = (ac.steps[ac.step_idx].delay
                           if ac.step_idx < len(ac.steps) else 1)
            else:
                ac.step_idx += 1
                ac.wait = (ac.steps[ac.step_idx].delay
                           if ac.step_idx < len(ac.steps) else 1)
        return [m for m in msgs if m]


def _line_of(step: ChainStep, ac: ActiveChain) -> str:
    if callable(step.text):
        return step.text(ac.ctx)
    return step.text.format(**ac.ctx)


def _face_of(ctx: Dict[str, Any]) -> Optional[str]:
    """The actor a chain beat is about, when its context names one."""
    ch = ctx.get("_char")
    if ch is not None and getattr(ch, "name", None):
        return ch.name
    for key in ("heir", "subject", "ruler", "martyr", "target",
                "leader", "speaker"):
        val = ctx.get(key)
        if isinstance(val, str) and val:
            return val
    return None
