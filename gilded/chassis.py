"""The Chassis (mission G13): the anti-game.py.

GildedGame owns wiring and the event log, nothing else. Every rule lives in
the system modules; the chassis calls them in a fixed order each turn and
converts their message strings into TurnEvents with sensible registers:
dividends and business land in the ledger, public news in the gazette,
family and court matters in house-scoped letters. Events accumulate during
end_turn resolution and are read at the start of the next turn - the papers
report what happened."""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from gilded.world import generate_atlas
from gilded.houses import assign_houses
from gilded.enterprises import (Enterprise, capacity_out, found_enterprise,
                                tick_construction)
from gilded.directives import DIRECTIVE_KEYS, Directives, tick_friction
from gilded.docket import (DOMAIN_SEAT, MAX_PETITIONS, Petition,
                           generate_petitions, resolve_unattended)
from gilded.society.house_ai import tick_realm
from gilded.society.ideology import (REVOLUTION_BREWING_TURNS, IdeologicalTide,
                                     can_transform, revolution_brewing,
                                     tick_legitimacy, transform_house,
                                     trigger_revolution)
from gilded.society.labor import STRIKE_OUTPUT_MULT, tick_extraction, tick_movement
from gilded.society.marriages import MarriageRegistry
from gilded.society.realm import create_house_realm, tick_directors, tick_loyalty
from gilded.society.relationships import tick_relationships
from gilded.society.schemes import SchemeManager
from gilded.society.shares import initial_ledger, partition_shares, pay_dividends

ATTENTION_PER_TURN = 3
STARTING_ENTERPRISES = 2          # seeded per house, on its best endowments
COAL_STRIKE_PRICE = 0.05          # colliery gold x (1 + this per striking province)
CAPACITY_KINDS = ("coal", "steel", "freight")
ENDOWMENT_ENTERPRISE = {
    "coalfield": "colliery", "iron": "ironworks", "timber": "mill",
    "farmland": "estate", "harbor": "rail_co",
}


@dataclass
class TurnEvent:
    text: str
    register: str = "gazette"     # "gazette" | "ledger" | "letters"
    house: str = ""               # scoping for ledger/letters; "" = worldwide


class GildedGame:
    def __init__(self, seed: int, player_house: Optional[str] = None):
        self.seed = seed
        random.seed(seed)          # Character internals draw from module random
        self.rng = random.Random(seed)
        self.turn = 1
        self.atlas = generate_atlas(seed)
        self.houses = assign_houses(self.atlas, seed)
        if player_house is not None and player_house in self.houses:
            self.houses[player_house].is_player = True
        self.realms = {h: create_house_realm(h, self.rng) for h in self.houses}
        self.enterprises: List[Enterprise] = []
        self.directives = {h: Directives() for h in self.houses}
        self.tide = IdeologicalTide()
        self.legitimacy = {h: 50.0 for h in self.houses}
        self.scheme_mgr = SchemeManager()
        self.marriages = MarriageRegistry()
        self.wars: List[object] = []                       # fronts.War from G15
        self.events: List[TurnEvent] = []                  # last resolved turn's record
        self.docket_by_house: Dict[str, List[Petition]] = {}
        self.attention: Dict[str, int] = {}
        self.game_over: Optional[str] = None               # ending key when finished
        self.capacity: Dict[str, Dict[str, float]] = {}    # strategic capacity per house
        self.last_accidents: List[tuple] = []              # (ent, province) this turn
        self.brewing_turns: Dict[str, int] = {}            # revolution preconditions held
        self._seed_enterprises()
        self.open_turn()

    # --- helpers -------------------------------------------------------------

    def ents_of(self, house) -> List[Enterprise]:
        return [e for e in self.enterprises if e.house == house]

    def provinces_of(self, house) -> List:
        return [p for p in sorted(self.atlas.provinces.values(), key=lambda p: p.pid)
                if p.owner == house]

    def _ents_by_house(self) -> Dict[str, List[Enterprise]]:
        out: Dict[str, List[Enterprise]] = {h: [] for h in self.houses}
        for e in self.enterprises:
            out.setdefault(e.house, []).append(e)
        return out

    def _emit(self, texts, register: str, house: str = "") -> None:
        for t in texts:
            if t:
                self.events.append(TurnEvent(t, register, house))

    def _seed_enterprises(self) -> None:
        """Every House opens the century with two ventures on its best endowments."""
        eid = 0
        for h in sorted(self.houses):
            realm = self.realms[h]
            options = []
            for p in self.provinces_of(h):
                for endow, rich in sorted(p.endowments.items()):
                    kind = ENDOWMENT_ENTERPRISE.get(endow)
                    if kind is not None:
                        options.append((-rich, p.pid, kind))
            options.sort()
            made = 0
            for _negrich, pid, kind in options:
                if made >= STARTING_ENTERPRISES:
                    break
                eid += 1
                ent = found_enterprise(kind, h, self.atlas.provinces[pid], eid, self.rng)
                if ent is None:
                    continue
                ent.under_construction = 0                 # operating from turn one
                initial_ledger(ent, realm)
                self.enterprises.append(ent)
                made += 1
            while made < STARTING_ENTERPRISES:             # a Bank needs nothing but money
                eid += 1
                ent = found_enterprise("bank", h,
                                       self.atlas.provinces[self.houses[h].capital],
                                       eid, self.rng)
                ent.under_construction = 0
                initial_ledger(ent, realm)
                self.enterprises.append(ent)
                made += 1

    # --- the turn ------------------------------------------------------------

    def open_turn(self) -> None:
        """Phase I: fresh docket for every house (festering paper carries
        over), attention reset."""
        self.attention = {h: ATTENTION_PER_TURN for h in self.houses}
        for h in sorted(self.houses):
            carried = [p for p in self.docket_by_house.get(h, [])
                       if p.turns_waiting > 0 and not p.escalated]
            kinds = {p.kind for p in carried}
            fresh = [p for p in generate_petitions(self, h) if p.kind not in kinds]
            self.docket_by_house[h] = (carried + fresh)[:MAX_PETITIONS]

    def end_turn(self) -> List[TurnEvent]:
        self.events = []
        self.last_accidents = []
        provinces = self.atlas.provinces

        # 1. unattended dockets
        for h in sorted(self.houses):
            out = resolve_unattended(self, h, self.docket_by_house.get(h, []))
            self._emit(out, "letters", h)

        # 2. construction, strategic capacity, dividends
        for ent in self.enterprises:
            if tick_construction(ent):
                self._emit([f"{ent.name} completes its works (tier {ent.tier})"],
                           "ledger", ent.house)
        striking = sum(1 for p in provinces.values()
                       if getattr(p, "movement", None) is not None
                       and p.movement.state == "striking")
        coal_price = 1.0 + COAL_STRIKE_PRICE * striking
        self.capacity = {h: {k: 0.0 for k in CAPACITY_KINDS} for h in self.houses}
        for h in sorted(self.houses):
            realm = self.realms[h]
            take_total = 0.0
            for ent in self.ents_of(h):
                province = provinces.get(ent.province)
                if province is None:
                    continue
                kind, amt = capacity_out(ent, province)
                if kind is not None:
                    self.capacity[h][kind] += amt
                mod = coal_price if ent.kind == "colliery" else 1.0
                mv = getattr(province, "movement", None)
                if mv is not None and mv.state == "striking":
                    mod *= STRIKE_OUTPUT_MULT
                take, _ = pay_dividends(realm, [ent], provinces, mod)
                take_total += take
            if take_total > 0:
                self.houses[h].treasury += take_total
                self._emit([f"Dividends: {take_total:.0f} gold to the House treasury"],
                           "ledger", h)

        # 3. labor: the squeeze, then the movements
        ent_pids = set()
        for ent in self.enterprises:
            province = provinces.get(ent.province)
            if province is None:
                continue
            ent_pids.add(province.pid)
            realm = self.realms.get(ent.house)
            before = self.tide.house_atrocities.get(ent.house, 0.0)
            msgs = tick_extraction(ent, province, realm, self.rng, self.tide)
            if self.tide.house_atrocities.get(ent.house, 0.0) > before:
                self.last_accidents.append((ent, province))
            self._emit(msgs, "gazette", ent.house)
        for pid in sorted(provinces):
            province = provinces[pid]
            if pid in ent_pids:
                continue           # tick_extraction already ticked its movement
            realm = self.realms.get(province.owner)
            self._emit(tick_movement(province, realm, self.rng),
                       "gazette", province.owner)

        # 4. society
        for h in sorted(self.realms):
            realm = self.realms[h]
            old_ruler = realm.ruler
            msgs, _born = tick_realm(realm, self.turn, self.rng, self.tide)
            self._emit(msgs, "letters", h)
            if realm.ruler is not old_ruler:
                self._emit(partition_shares(realm, self.ents_of(h), old_ruler,
                                            realm.ruler, "PRIMOGENITURE"),
                           "letters", h)
        self._emit(tick_relationships(self.realms, self.scheme_mgr,
                                      self.turn, self.rng), "gazette")
        self._emit(self.scheme_mgr.advance_all(self.realms, self.legitimacy,
                                               self.rng), "gazette")
        for _kind, h in self.scheme_mgr.pending_successions:
            self._emit([f"House {h}'s chair stands empty - the succession is unsettled"],
                       "gazette", h)
        self.scheme_mgr.pending_successions.clear()
        self._emit(self.marriages.tick(self.realms, self.houses,
                                       self._ents_by_house(), self.rng), "gazette")
        for h in sorted(self.realms):
            realm = self.realms[h]
            self._emit(tick_directors(realm, self.enterprises, self.rng), "ledger", h)
            self._emit(tick_loyalty(realm, self.enterprises, self.rng), "letters", h)

        # 5. directives friction
        for h in sorted(self.houses):
            realm = self.realms[h]
            seats = {k: realm.court.positions.get(DOMAIN_SEAT[k])
                     for k in DIRECTIVE_KEYS}
            for key, what in tick_friction(self.directives[h], seats, self.rng):
                if what == "resigned":
                    seat = DOMAIN_SEAT[key]
                    holder = realm.court.positions.get(seat)
                    realm.court.positions[seat] = None
                    name = holder.name if holder is not None else "The minister"
                    self._emit([f"{name} resigns as {seat.value} over the "
                                f"House's {key} policy"], "letters", h)

        # 6. war resolution (G15/G16 hook)
        if self.wars:
            pass

        # 7. the tide and the mandate
        self.tide.tick()
        for h in sorted(self.houses):
            provs = self.provinces_of(h)
            unrest = (sum(p.unrest for p in provs) / len(provs)) if provs else 0.0
            happiness = int(50.0 - unrest)
            self.legitimacy[h] = tick_legitimacy(
                self.legitimacy[h], happiness, self.tide,
                self.tide.consume_fresh(h))

        # 8. revolution checks and pending successions
        for h in sorted(self.houses):
            provs = self.provinces_of(h)
            if not revolution_brewing(self.legitimacy[h], provs):
                self.brewing_turns[h] = 0
                continue
            self.brewing_turns[h] = self.brewing_turns.get(h, 0) + 1
            if self.brewing_turns[h] < REVOLUTION_BREWING_TURNS:
                continue
            self.brewing_turns[h] = 0
            realm = self.realms[h]
            if can_transform(realm.ruler):
                msgs, new_leg = transform_house(h, realm.ruler, provs,
                                                self.enterprises, realm,
                                                self.legitimacy[h])
                self.legitimacy[h] = new_leg
            else:
                msgs, _flipped = trigger_revolution(h, provs, self.enterprises)
            self._emit(msgs, "gazette", h)

        # 9. endings (G17 hook), then the next morning's paper
        self.turn += 1
        self.open_turn()
        return self.events
