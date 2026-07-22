"""The Director (Gilded Saga sections 2-4): observes a resolved turn, writes
durable facts, ticks the three beat-sources, advances the spine, and emits
chronicle TurnEvents. Fully deterministic: a dedicated rng (never game.rng),
choices tie-broken by id. It never mutates sim state.

Wave N2 wires the three beat-sources - the Age (named eras from the tide), the
Rival (a deterministically-bound AI house), and the Chronicle (emergent threads
detected from the FactStore) - through _tick_sources()."""

import random
from typing import Dict, List, Optional

from gilded.chassis import TurnEvent
from gilded.saga.beats import Beat, eval_predicate
from gilded.saga.facts import FactStore, facts_from_turn
from gilded.saga.content.eras import ERAS
from gilded.saga.content.rival_arc import rival_beats
from gilded.saga.content.threads import candidate_threads, MAX_ACTIVE_THREADS


class Director:
    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed ^ 0x5A6A)      # dedicated; never game.rng
        self.facts = FactStore()
        self.beats: Dict[str, Beat] = {}
        self.active: List[str] = []
        self.snapshot: Optional[Dict] = None
        self.rival: Optional[str] = None             # bound by _tick_rival
        self.age_idx: int = -1                        # advanced by _tick_age
        self.threads: Dict[str, str] = {}             # reserved

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
        out: List[TurnEvent] = []
        out += self._tick_age(game)
        out += self._tick_rival(game)
        out += self._tick_chronicle(game)
        return out

    # --- the Age (§4.C) -----------------------------------------------------

    def _tick_age(self, game) -> List[TurnEvent]:
        target = self.age_idx
        for i, era in enumerate(ERAS):
            if game.turn >= era.turn or game.tide.level >= era.tide:
                target = max(target, i)
        out: List[TurnEvent] = []
        while self.age_idx < target:
            self.age_idx += 1
            era = ERAS[self.age_idx]
            b = Beat(bid=era.bid, source="age", title=era.title,
                     load_bearing=False, foreshadow=era.foreshadow, payoff=era.payoff,
                     state="active", opened_turn=game.turn)
            self.beats[b.bid] = b
            out.append(TurnEvent(era.payoff, "gazette"))
        return out

    # --- the Rival (§4.A) ---------------------------------------------------

    def _pick_rival(self, game):
        best = None
        best_key = None
        for name in sorted(game.houses):
            if getattr(game.houses[name], "is_player", False):
                continue
            pop = sum(getattr(p, "population", 0) for p in game.provinces_of(name))
            strength = pop / 100.0 + game.houses[name].treasury
            key = (strength,)
            if best_key is None or key > best_key:
                best_key = key
                best = name
        return best

    def _tick_rival(self, game) -> List[TurnEvent]:
        out: List[TurnEvent] = []
        if self.rival is None:
            self.rival = self._pick_rival(game)
            if self.rival is not None:
                for b in rival_beats(self.rival):
                    self.register(b, game)
        return out

    # --- the Chronicle (§4.B) -----------------------------------------------

    def _tick_chronicle(self, game) -> List[TurnEvent]:
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

    # --- advancement --------------------------------------------------------

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
