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
from gilded.enterprises import (Enterprise, capacity_out, director_skim,
                                found_enterprise, tick_construction)
from gilded.market import Market, tech_mod_for
from gilded.directives import DIRECTIVE_KEYS, Directives, tick_friction
from gilded.docket import (DOMAIN_SEAT, MAX_PETITIONS, Petition,
                           generate_petitions, resolve_unattended)
from gilded.fronts import negotiate_peace, tick_wars
from gilded.society.house_ai import tick_realm
from gilded.society.ideology import (REVOLUTION_BREWING_TURNS, IdeologicalTide,
                                     can_transform, revolution_brewing,
                                     tick_legitimacy, transform_house,
                                     trigger_revolution)
from gilded.society.labor import STRIKE_OUTPUT_MULT, tick_extraction, tick_movement
from gilded.society.characters import SocietyState
from gilded.society.marriages import MarriageRegistry
from gilded.society.realm import create_house_realm, tick_directors, tick_loyalty
from gilded.society.relationships import tick_relationships
from gilded.society.schemes import SchemeManager
from gilded.society.shares import initial_ledger, partition_shares, pay_dividends

ATTENTION_PER_TURN = 3
STARTING_ENTERPRISES = 2          # seeded per house, on its best endowments

CAPACITY_KINDS = ("coal", "steel", "freight")
ENDOWMENT_ENTERPRISE = {
    "coalfield": "colliery", "iron": "ironworks", "timber": "mill",
    "farmland": "estate", "harbor": "rail_co",
}
TURN_BUDGET = 70                  # the century, at a year and a half a turn
YEAR_START = 1900


def year_of(turn: int) -> int:
    return YEAR_START + round((turn - 1) * 100 / TURN_BUDGET)


@dataclass
class TurnEvent:
    text: str
    register: str = "gazette"     # "gazette" | "ledger" | "letters"
    house: str = ""               # scoping for ledger/letters; "" = worldwide


class GildedGame:
    def __init__(self, seed: int, player_house: Optional[str] = None):
        self.seed = seed
        random.seed(seed)          # governs narration text (event_engine.render)
        self.rng = random.Random(seed)
        self.society = SocietyState(self.rng)
        self.turn = 1
        self.atlas = generate_atlas(seed)
        self.houses = assign_houses(self.atlas, seed)
        if player_house is not None and player_house in self.houses:
            self.houses[player_house].is_player = True
        self.realms = {h: create_house_realm(h, self.society) for h in self.houses}
        self.enterprises: List[Enterprise] = []
        self.directives = {h: Directives() for h in self.houses}
        self.tide = IdeologicalTide()
        from gilded.saga.director import Director   # local: director imports TurnEvent
        self.director = Director(seed)
        self.legitimacy = {h: 50.0 for h in self.houses}
        self.scheme_mgr = SchemeManager()
        self.marriages = MarriageRegistry()
        self.wars: List[object] = []                       # fronts.War from G15
        self.events: List[TurnEvent] = []                  # last resolved turn's record
        self.docket_by_house: Dict[str, List[Petition]] = {}
        self.attention: Dict[str, int] = {}
        self.game_over: Optional[str] = None               # ending key when finished
        self.fallen: Dict[str, str] = {}                   # house -> "revolution"|"transformed"
        self.market = Market()
        self.capacity: Dict[str, Dict[str, float]] = {}    # strategic capacity per house
        self.last_accidents: List[tuple] = []              # (ent, province) this turn
        self.brewing_turns: Dict[str, int] = {}            # revolution preconditions held
        self.resolved_turn: Optional[int] = None           # last turn fully resolved
        self.agendas: Dict[str, object] = {}   # house -> agenda.Goal (Stage 2)
        self.informants: set = set()           # (viewer_house, target_house) intel lever
        self.takeovers: List[object] = []      # society.schemes.Takeover in flight
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

    # --- helpers ------------------------------------------------------------

    def tech_mod_for(self, province) -> float:
        """Tech modifier based on province development level."""
        return tech_mod_for(province)

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
        if self.game_over is not None:
            return self.events             # the age has closed; the paper stands
        self.events = []
        self.last_accidents = []
        provinces = self.atlas.provinces

        # Stage 3: standing policy — compute once, apply at each seam below.
        from gilded import policy
        self.policy = {h: policy.effects(self, h) for h in self.houses}
        for h in sorted(self.houses):
            lvl = float(self.policy[h].extraction_level)
            for ent in self.ents_of(h):
                ent.extraction_dial = lvl

        # 0. the AI houses read their morning paper (the player's waits)
        from gilded.ai import ai_peace_check, ai_turn   # local: ai imports docket
        for h in sorted(self.houses):
            if not self.houses[h].is_player:
                self._emit(ai_turn(self, h), "letters", h)
        for war in list(self.wars):
            terms = ai_peace_check(self, war)
            if terms is not None:
                self._emit(negotiate_peace(self, war, terms), "gazette")

        # 1. unattended dockets
        for h in sorted(self.houses):
            out = resolve_unattended(self, h, self.docket_by_house.get(h, []))
            self._emit(out, "letters", h)

        # 2. construction, strategic capacity, dividends
        for ent in self.enterprises:
            if tick_construction(ent):
                self._emit([f"{ent.name} completes its works (tier {ent.tier})"],
                           "ledger", ent.house)
        self.market.clear(self)
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
                mod = 1.0
                mv = getattr(province, "movement", None)
                if mv is not None and mv.state == "striking":
                    mod *= STRIKE_OUTPUT_MULT
                mod *= self.policy[h].output_mod
                mod *= self.market.output_mod(ent)
                mod *= tech_mod_for(province)
                take, _ = pay_dividends(realm, [ent], provinces, mod)
                take -= self.market.input_cost(ent)
                director = None
                if hasattr(ent, 'director_id') and ent.director_id:
                    for c in realm.characters:
                        if c.id == ent.director_id:
                            director = c
                            break
                skim_amt = director_skim(take, director, realm.ruler)
                if skim_amt > 0 and director is not None:
                    director.gold_reserve = getattr(director, 'gold_reserve', 0.0) + skim_amt
                    take -= skim_amt
                # Save previous dividend before overwriting
                if ent._last_dividend != 0.0 or ent._prev_dividend is not None:
                    ent._prev_dividend = ent._last_dividend
                ent._last_dividend = take
                take_total += take
            if take_total > 0:
                self.houses[h].credit(self.turn, "dividends", take_total)
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
        for tk in list(self.takeovers):
            self._emit(tk.advance(self.realms, self.enterprises, self.rng, self),
                       "gazette")
            if tk.complete:
                self.takeovers.remove(tk)
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

        # 6. war resolution - the fronts grind and the papers carry the cost
        self._emit(tick_wars(self), "gazette")

        # 6.5 policy effects — happiness, legitimacy, relations, trade income
        for h in sorted(self.houses):
            eff = self.policy[h]
            provs = self.provinces_of(h)
            # Happiness mod from diplomacy (positive = reduces unrest)
            if eff.happiness_mod:
                for p in provs:
                    p.unrest = max(0.0, min(100.0, p.unrest - eff.happiness_mod))
            # Legitimacy mod from diplomacy
            if eff.legitimacy_mod:
                self.legitimacy[h] = max(0, min(100.0,
                    self.legitimacy[h] + eff.legitimacy_mod))
            # Relations drift from diplomacy
            drift = eff.relations_drift
            if drift:
                rel = self.houses[h].relations
                for other in self.houses:
                    if other == h:
                        continue
                    rel[other] = max(-100, min(100, int(round(
                        rel.get(other, 0) + drift))))
            # Trade income from expansion
            if eff.trade_income:
                self.houses[h].credit(self.turn, "trade", eff.trade_income)
            # Unrest add from labor policy
            if eff.unrest_add:
                for p in provs:
                    p.unrest = max(0.0, min(100.0, p.unrest + eff.unrest_add))

        # 7. the tide and the mandate
        self.tide.tick()
        for h in sorted(self.houses):
            provs = self.provinces_of(h)
            unrest = (sum(p.unrest for p in provs) / len(provs)) if provs else 0.0
            happiness = int(50.0 - unrest)
            self.legitimacy[h] = tick_legitimacy(
                self.legitimacy[h], happiness, self.tide,
                self.tide.consume_fresh(h)).value

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
                self.fallen.setdefault(h, "transformed")
                self.directives[h].set_stance("labor", -100)
            else:
                msgs, _flipped = trigger_revolution(h, provs, self.enterprises)
                self.fallen.setdefault(h, "revolution")
                self.directives[h].set_stance("labor", -100)
            self._emit(msgs, "gazette", h)

        # 8.5 the Director reads the resolved turn and chronicles it
        self.events.extend(self.director.observe(self))

        # 9. endings, then the next morning's paper
        self.resolved_turn = self.turn
        self.turn += 1
        from gilded.endings import check_ending    # local: endings imports our constants
        judged = next((h for h in sorted(self.houses)
                       if self.houses[h].is_player), None)
        if judged is not None:
            verdict = check_ending(self, judged)
        else:
            verdict = "century" if self.turn > TURN_BUDGET else None
        if verdict is not None and verdict != "transformed":
            self.game_over = verdict
            self._emit([f"THE AGE CLOSES: {verdict}"], "gazette")
        self.open_turn()
        return self.events