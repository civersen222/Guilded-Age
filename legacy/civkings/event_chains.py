"""Event chains (M72, spec 7): authored multi-step story beats.

A chain arms when its trigger reads something true in the live game
state, then plays its steps over the following turns. Deterministic:
no RNG, so seeded runs stay reproducible.
"""

from typing import Any, Callable, Dict, List, Optional


class ChainStep:
    """One beat: a template line, an optional effect, and a delay."""

    def __init__(self, text: str,
                 apply: Optional[Callable[[Any, Dict[str, Any]], List[str]]] = None,
                 delay: int = 1):
        self.text = text
        self.apply = apply
        self.delay = delay          # turns after the previous beat


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
        self.wait = cdef.steps[0].delay


class ChainManager:
    """Arms triggers and advances active chains one tick at a time."""

    def __init__(self, defs: Optional[List[ChainDef]] = None):
        self.defs: List[ChainDef] = list(defs or [])
        self.active: List[ActiveChain] = []
        self.fired: set = set()

    def tick(self, game: Any) -> List[str]:
        """One turn: arm new chains, then advance the ones in motion."""
        msgs: List[str] = []
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
            ac.wait -= 1
            if ac.wait > 0:
                continue
            step = ac.cdef.steps[ac.step_idx]
            msgs.append(step.text.format(**ac.ctx))
            if step.apply is not None:
                extra = step.apply(game, ac.ctx)
                if extra:
                    msgs.extend(extra)
            ac.step_idx += 1
            if ac.step_idx >= len(ac.cdef.steps):
                done.append(ac)
            else:
                ac.wait = ac.cdef.steps[ac.step_idx].delay
        for ac in done:
            self.active.remove(ac)
        return msgs
