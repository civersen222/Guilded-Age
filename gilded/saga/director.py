"""The Director (Gilded Saga sections 2-4): observes a resolved turn, writes
durable facts, ticks the three beat-sources, advances the spine, and emits
chronicle TurnEvents. Fully deterministic: a dedicated rng (never game.rng),
choices tie-broken by id. It never mutates sim state.

This is the N1 skeleton: facts + advancement + snapshot. The three beat-source
tick methods arrive in Wave N2, routed through _tick_sources()."""

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