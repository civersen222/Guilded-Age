"""The Docket (mission G12, spec 6): the turn arrives as paper.

Petitions rise from the simulation; the ruler spends attention ruling on
them or launching initiatives. Everything is routed through a person - an
executor whose competence sets the odds and whose convictions grind against
the order. Unattended petitions fall to the seated minister of their
domain; matters with no seat fester and resolve themselves badly.

The docket never imports the chassis - it only receives the game object
(anything with atlas/houses/realms/enterprises/rng/... attributes)."""

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from gilded.world import MINOR_OWNER
from gilded.enterprises import (
    ENTERPRISE_TYPES, EXPAND_COST, EXPAND_TURNS, KIND_TITLES, TIER_MAX,
    found_enterprise,
)
from gilded.directives import DIRECTIVE_CONVICTION, friction
from gilded.fronts import (ENTRENCH_MAX, PeaceTerms, WarGoal, ai_acceptable,
                           allocate, declare_war, negotiate_peace,
                           raise_regiments)
from gilded.society.court import Court, CourtPosition
from gilded.society.characters import modify_opinion
from gilded.society.dispositions import apply_drift
from gilded.society.labor import buy_off_leader, cover_up, martyr_leader
from gilded.society.realm import DIRECTOR_SALARY_PCT
from gilded.society.shares import initial_ledger, transfer_shares

FESTER_TURNS = 2                  # unattended + no seat -> auto-resolution after this
MAX_PETITIONS = 6                 # per house per turn
BETROTHAL_CHANCE = 0.25
HEIR_DEMAND_CHANCE = 0.2
RAIL_COST = 250.0
BUYOFF_COST = 150.0
COMPENSATE_COST = 100.0
HEIR_ALLOWANCE = 100.0
TOUR_UNREST_RELIEF = 10.0
TOUR_STRESS = 8
FUMBLE_STRESS = 6
WAR_SWING = 20.0                  # war-score movement that convenes the council
LINE_CRISIS = 0.5                 # a front this deep in motion is a crisis
REINFORCE_REGIMENTS = 3
PEACE_GOLD_PER_SCORE = 5.0        # auto-terms reparations per score point
PEACE_LAND_SCORE = 40.0           # auto-terms demand land from this score up

DOMAIN_SEAT = {
    "capital": CourtPosition.BOARD_CHAIRMAN,
    "expansion": CourtPosition.CHIEF_ENGINEER,
    "labor": CourtPosition.HEAD_OF_SECURITY,
    "press": CourtPosition.MASTER_OF_PRESS,
    "diplomacy": CourtPosition.FOREIGN_SECRETARY,
    "war": CourtPosition.MARSHAL,
}
SEAT_DOMAIN = {seat: domain for domain, seat in DOMAIN_SEAT.items()}

DOMAIN_PRIORITY = {               # lower = more urgent when the docket overflows
    "war": 0, "labor": 1, "family": 2, "capital": 3,
    "press": 4, "diplomacy": 5, "expansion": 6,
}


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
    game: object                  # GildedGame (chassis) - single handle, YAGNI
    house: str
    executor: object              # Character actually carrying it out
    rng: random.Random
    scale: float = 1.0            # 0.5 when the executor fumbled the ruling


def _next_pid(game) -> int:
    game._docket_pid = getattr(game, "_docket_pid", 0) + 1
    return game._docket_pid


def _ents_of(game, house_name: str) -> List:
    return [e for e in game.enterprises if e.house == house_name]


def _ents_by_house(game) -> Dict[str, List]:
    out: Dict[str, List] = {h: [] for h in game.houses}
    for e in game.enterprises:
        out.setdefault(e.house, []).append(e)
    return out


def _house_provinces(game, house_name: str) -> List:
    return [p for p in game.atlas.provinces.values() if p.owner == house_name]


# --- generators --------------------------------------------------------------

def _gen_capital_request(game, house_name, realm, rng) -> Optional[Petition]:
    """A Director with an enterprise below top tier begs expansion capital."""
    by_id = {c.id: c for c in realm.characters}
    candidates = [e for e in _ents_of(game, house_name)
                  if e.tier < TIER_MAX and e.under_construction == 0
                  and e.director_id and by_id.get(e.director_id) is not None
                  and by_id[e.director_id].is_alive]
    if not candidates:
        return None
    ent = min(candidates, key=lambda e: (e.tier, e.eid))
    director = by_id[ent.director_id]
    from gilded import policy
    _eff = policy.effects(game, house_name)
    cost = EXPAND_COST[ent.tier + 1] * _eff.expand_cost_mod

    def _grant(ctx) -> List[str]:
        # Stale guard: the venture may have reached TIER_MAX by another road
        # (initiative or an earlier petition) between request and ruling.
        # A House cannot be billed for a tier that does not exist.
        if ent.tier >= TIER_MAX or ent.target_tier >= TIER_MAX:
            return [f"{ent.name} has already reached the top tier; request withdrawn"]
        house = ctx.game.houses[ctx.house]
        if house.treasury < cost:
            return [f"The treasury cannot meet {director.name}'s request ({cost:.0f} gold)"]
        house.debit(ctx.game.turn, "expansion", cost)
        _turns = EXPAND_TURNS[ent.tier + 1]
        if _eff.build_speed_mod > 0:
            _turns = max(1, int(round(_turns / _eff.build_speed_mod)))
        ent.under_construction = _turns
        ent.target_tier = ent.tier + 1
        modify_opinion(director, realm.ruler, int(10 * ctx.scale), "expansion capital")
        return [f"{ent.name} breaks ground on tier {ent.tier + 1} ({cost:.0f} gold)"]

    def _refuse(ctx) -> List[str]:
        modify_opinion(director, realm.ruler, -int(8 * ctx.scale), "refused capital")
        return [f"{director.name} is sent away empty-handed"]

    return Petition(
        pid=_next_pid(game), kind="capital_request", domain="capital",
        house=house_name,
        text=f"{director.name} begs capital to expand {ent.name} (tier {ent.tier}, {cost:.0f} gold)",
        actors={"director": director, "enterprise": ent},
        options=[
            PetitionOption("grant", f"Fund the expansion ({cost:.0f} gold)", 60, _grant),
            PetitionOption("refuse", "The House's gold stays in the vault", -40, _refuse),
        ])


def _gen_seat_vacancies(game, house_name, realm, rng) -> List[Petition]:
    """Every empty (or dead-held) council seat asks for a name."""
    pets: List[Petition] = []
    taken = {c.id for c in realm.court.positions.values() if c is not None and c.is_alive}
    for seat, holder in realm.court.positions.items():
        if holder is not None and holder.is_alive:
            continue
        stat = Court.POSITION_STATS[seat]
        pool = [c for c in realm.characters
                if c.is_alive and c.age >= 16 and c.id != realm.ruler.id
                and c.id not in taken]
        pool.sort(key=lambda c: -c.get_effective_stat(stat))
        if not pool:
            continue
        options = []
        for i, cand in enumerate(pool[:3]):
            def _appoint(ctx, seat=seat, cand=cand) -> List[str]:
                for pos, ch in realm.court.positions.items():
                    if ch is not None and ch.id == cand.id:
                        realm.court.positions[pos] = None
                realm.court.positions[seat] = None
                realm.court.appoint(seat, cand, getattr(ctx.game, "turn", 0))
                modify_opinion(cand, realm.ruler, int(15 * ctx.scale), "given a seat")
                return [f"{cand.name} is sworn in as {seat.value}"]
            options.append(PetitionOption(
                f"appoint_{i + 1}",
                f"Appoint {cand.name} ({stat} {cand.get_effective_stat(stat)})",
                0, _appoint))
        pets.append(Petition(
            pid=_next_pid(game), kind="seat_vacancy",
            domain=SEAT_DOMAIN[seat], house=house_name,
            text=f"The seat of {seat.value} stands empty",
            actors={"candidates": pool[:3]},
            options=options))
    return pets


def _gen_union_ultimatum(game, house_name, realm, rng) -> Optional[Petition]:
    """A striking province's movement puts its demands on the desk."""
    striking = [p for p in _house_provinces(game, house_name)
                if getattr(p, "movement", None) is not None
                and p.movement.state == "striking"]
    if not striking:
        return None
    province = min(striking, key=lambda p: p.pid)
    mv = province.movement
    ents_here = [e for e in _ents_of(game, house_name) if e.province == province.pid]

    def _concede(ctx) -> List[str]:
        for e in ents_here:
            e.extraction_dial = max(0.0, e.extraction_dial - 20.0 * ctx.scale)
        province.unrest = max(0.0, province.unrest - 10.0 * ctx.scale)
        return [f"The dials at {province.name} are wound back; the union claims victory"]

    def _buy_off(ctx) -> List[str]:
        house = ctx.game.houses[ctx.house]
        if house.treasury < BUYOFF_COST:
            return [f"The House cannot raise the {BUYOFF_COST:.0f} gold to buy peace"]
        house.debit(ctx.game.turn, "strike buyoff", BUYOFF_COST)
        return buy_off_leader(mv, province)

    def _break(ctx) -> List[str]:
        out = martyr_leader(mv, province, _house_provinces(ctx.game, ctx.house),
                            realm, ctx.rng, getattr(ctx.game, "tide", None))
        return out or [f"The {province.name} strike is broken by force"]

    leader_name = mv.leader.name if mv.leader is not None else "the strike committee"
    return Petition(
        pid=_next_pid(game), kind="union_ultimatum", domain="labor",
        house=house_name,
        text=f"{leader_name} of {province.name} demands relief - the works stand silent",
        actors={"movement": mv, "province": province},
        options=[
            PetitionOption("concede", "Cut the extraction dials", -60, _concede),
            PetitionOption("buy_off", f"Buy off the leadership ({BUYOFF_COST:.0f} gold)", 0, _buy_off),
            PetitionOption("break", "Break the strike", 80, _break),
        ])


def _gen_betrothal_offer(game, house_name, realm, rng) -> Optional[Petition]:
    """Another House proposes a match, with the usual merger terms."""
    if rng.random() >= BETROTHAL_CHANCE:
        return None
    house = game.houses[house_name]
    suitors = [n for n in game.houses
               if n != house_name and n in game.realms
               and n not in house.at_war_with
               and house.relations.get(n, 0) > -50]
    if not suitors:
        return None
    other = rng.choice(sorted(suitors))

    def _accept(ctx) -> List[str]:
        msg = ctx.game.marriages.arrange_match_between(
            ctx.house, other, ctx.game.realms, ctx.game.houses,
            _ents_by_house(ctx.game), ctx.rng)
        return [msg] if msg else [f"The match with {other} falls through at the altar"]

    def _decline(ctx) -> List[str]:
        a, b = ctx.game.houses[ctx.house], ctx.game.houses[other]
        a.relations[other] = a.relations.get(other, 0) - int(5 * ctx.scale)
        b.relations[ctx.house] = b.relations.get(ctx.house, 0) - int(5 * ctx.scale)
        return [f"{other}'s envoy is sent home without a bride"]

    return Petition(
        pid=_next_pid(game), kind="betrothal_offer", domain="diplomacy",
        house=house_name,
        text=f"House {other} proposes a marriage between the houses",
        actors={"other_house": other},
        options=[
            PetitionOption("accept", "Accept the match", -30, _accept),
            PetitionOption("decline", "Decline politely", 30, _decline),
        ])


def _gen_heir_demand(game, house_name, realm, rng) -> Optional[Petition]:
    """An adult of the blood with no seat wants what they're owed."""
    seated = {c.id for c in realm.court.positions.values() if c is not None}
    heirs = [c for c in realm.dynasty.all_characters.values()
             if c.is_alive and c.age >= 16 and c.id != realm.ruler.id
             and c.id not in seated]
    if not heirs or rng.random() >= HEIR_DEMAND_CHANCE:
        return None
    heir = max(heirs, key=lambda c: c.age)

    def _grant_seat(ctx) -> List[str]:
        for seat, holder in realm.court.positions.items():
            if holder is None or not holder.is_alive:
                realm.court.positions[seat] = None
                realm.court.appoint(seat, heir, getattr(ctx.game, "turn", 0))
                modify_opinion(heir, realm.ruler, int(20 * ctx.scale), "given a seat")
                return [f"{heir.name} takes the seat of {seat.value}"]
        modify_opinion(heir, realm.ruler, -int(5 * ctx.scale), "empty promise")
        return [f"There is no seat to give {heir.name}; the promise rings hollow"]

    def _allowance(ctx) -> List[str]:
        house = ctx.game.houses[ctx.house]
        if house.treasury < HEIR_ALLOWANCE:
            return [f"The treasury cannot spare {heir.name}'s allowance"]
        house.debit(ctx.game.turn, "heir allowance", HEIR_ALLOWANCE)
        modify_opinion(heir, realm.ruler, int(10 * ctx.scale), "an allowance")
        return [f"{heir.name} is granted an allowance of {HEIR_ALLOWANCE:.0f} gold"]

    def _refuse(ctx) -> List[str]:
        modify_opinion(heir, realm.ruler, -int(12 * ctx.scale), "refused their due")
        d = apply_drift(heir, "ambitious_content", 5.0, "denied their due")
        out = [f"{heir.name} is refused, and does not forget it"]
        if d:
            out.append(d)
        return out

    return Petition(
        pid=_next_pid(game), kind="heir_demand", domain="family",
        house=house_name,
        text=f"{heir.name} demands a seat at the table or capital of their own",
        actors={"heir": heir},
        options=[
            PetitionOption("grant_seat", "Give them a vacant seat", -20, _grant_seat),
            PetitionOption("allowance", f"Grant an allowance ({HEIR_ALLOWANCE:.0f} gold)", 0, _allowance),
            PetitionOption("refuse", "They will wait their turn", 40, _refuse),
        ])


def _gen_disaster_inquiry(game, house_name, realm, rng) -> Optional[Petition]:
    """The press smells blood after an accident (chassis records them in
    game.last_accidents as (enterprise, province) pairs)."""
    accidents = [(e, p) for e, p in getattr(game, "last_accidents", [])
                 if e.house == house_name]
    if not accidents:
        return None
    ent, province = accidents[0]
    by_id = {c.id: c for c in realm.characters}
    director = by_id.get(ent.director_id)

    def _cover(ctx) -> List[str]:
        return cover_up(realm.ruler, province, getattr(ctx.game, "tide", None))

    def _compensate(ctx) -> List[str]:
        house = ctx.game.houses[ctx.house]
        if house.treasury < COMPENSATE_COST:
            return ["The widows' fund is promised money the House does not have"]
        house.debit(ctx.game.turn, "compensation", COMPENSATE_COST)
        province.unrest = max(0.0, province.unrest - 8.0 * ctx.scale)
        return [f"The families of {province.name} are compensated ({COMPENSATE_COST:.0f} gold)"]

    def _prosecute(ctx) -> List[str]:
        if director is None or not director.is_alive:
            return [f"The inquiry into {ent.name} finds no one left to blame"]
        ent.director_id = ""
        modify_opinion(director, realm.ruler, -int(30 * ctx.scale), "prosecuted")
        province.unrest = max(0.0, province.unrest - 5.0 * ctx.scale)
        return [f"{director.name} is prosecuted for the disaster at {ent.name}"]

    return Petition(
        pid=_next_pid(game), kind="disaster_inquiry", domain="press",
        house=house_name,
        text=f"The papers demand answers for the disaster at {ent.name}",
        actors={"enterprise": ent, "province": province, "director": director},
        options=[
            PetitionOption("cover_up", "Suppress the story", 50, _cover),
            PetitionOption("compensate", f"Compensate the families ({COMPENSATE_COST:.0f} gold)", -50, _compensate),
            PetitionOption("prosecute", "Prosecute the Director", 0, _prosecute),
        ])


def _gen_rail_proposal(game, house_name, realm, rng) -> Optional[Petition]:
    """The Chief Engineer wants iron roads between the House's provinces."""
    engineer = realm.court.positions.get(CourtPosition.CHIEF_ENGINEER)
    if engineer is None or not engineer.is_alive:
        return None
    owned = {p.pid for p in _house_provinces(game, house_name)}
    link = None
    for key in sorted(game.atlas.links):
        ln = game.atlas.links[key]
        if not ln.rail and ln.a in owned and ln.b in owned:
            link = ln
            break
    if link is None:
        return None
    pa = game.atlas.provinces[link.a].name
    pb = game.atlas.provinces[link.b].name

    def _fund(ctx) -> List[str]:
        house = ctx.game.houses[ctx.house]
        if house.treasury < RAIL_COST:
            return [f"The {pa}-{pb} line stays on the drawing board ({RAIL_COST:.0f} gold short)"]
        house.debit(ctx.game.turn, "railway", RAIL_COST)
        link.rail = True
        return [f"Iron roads: the {pa}-{pb} line opens ({RAIL_COST:.0f} gold)"]

    def _defer(ctx) -> List[str]:
        modify_opinion(engineer, realm.ruler, -int(5 * ctx.scale), "shelved proposal")
        return [f"{engineer.name}'s rail survey is filed away"]

    return Petition(
        pid=_next_pid(game), kind="rail_proposal", domain="expansion",
        house=house_name,
        text=f"{engineer.name} proposes a rail link: {pa} to {pb} ({RAIL_COST:.0f} gold)",
        actors={"engineer": engineer, "link": link},
        options=[
            PetitionOption("fund", "Lay the track", 50, _fund),
            PetitionOption("defer", "The survey can wait", -50, _defer),
        ])


def _wars_of(game, house_name: str) -> List:
    return [w for w in getattr(game, "wars", [])
            if house_name in (w.aggressor, w.defender)]


def _auto_terms(game, war) -> PeaceTerms:
    """The bill the winner's chancery drafts from the state of the war."""
    terms = PeaceTerms()
    score = abs(war.war_score)
    winner = war.aggressor if war.war_score >= 0.0 else war.defender
    loser = war.defender if winner == war.aggressor else war.aggressor
    if (war.goal.kind == "seize" and winner == war.aggressor
            and score >= PEACE_LAND_SCORE):
        terms.provinces = [pid for pid in war.goal.provinces
                           if pid in game.atlas.provinces
                           and game.atlas.provinces[pid].owner == loser]
    if war.goal.kind == "open_markets" and winner == war.aggressor:
        terms.open_markets = True
    terms.gold = score * PEACE_GOLD_PER_SCORE
    return terms


def _try_peace(game, house_name: str, war) -> List[str]:
    """Draft auto-terms and put them to the losing signature."""
    terms = _auto_terms(game, war)
    loser = war.defender if war.war_score >= 0.0 else war.aggressor
    if ai_acceptable(game, war, terms, loser):
        return negotiate_peace(game, war, terms)
    other = war.defender if house_name == war.aggressor else war.aggressor
    return [f"House {other}'s envoys will not yield - the war goes on"]


def _gen_war_council(game, house_name, realm, rng) -> Optional[Petition]:
    """The Marshal convenes when a front is in motion or the score swings."""
    for war in _wars_of(game, house_name):
        seen = getattr(war, "_council_scores", {})
        last = seen.get(house_name, 0.0)
        hot = [f for f in war.fronts if abs(f.line) >= LINE_CRISIS]
        if not hot and abs(war.war_score - last) < WAR_SWING:
            continue
        if not hasattr(war, "_council_scores"):
            war._council_scores = {}
        war._council_scores[house_name] = war.war_score
        other = war.defender if house_name == war.aggressor else war.aggressor
        front = hot[0] if hot else (war.fronts[0] if war.fronts else None)

        def _reinforce(ctx, war=war, front=front) -> List[str]:
            if front is None:
                return ["There is no front left to reinforce"]
            owned = _house_provinces(ctx.game, ctx.house)
            if not owned:
                return ["The House has no province left to muster from"]
            src = max(owned, key=lambda p: (p.population, -p.pid))
            raised = raise_regiments(ctx.game, ctx.house, src.pid,
                                     REINFORCE_REGIMENTS)
            if raised <= 0:
                return [f"{src.name} can spare no men for the front"]
            allocate(war, front, ctx.house, raised)
            return [f"{raised} fresh regiments march to front {front.fid}"]

        def _hold(ctx, war=war, front=front) -> List[str]:
            if front is not None:
                if ctx.house == war.aggressor:
                    front.entrenchment_a = min(ENTRENCH_MAX,
                                               front.entrenchment_a + 1)
                else:
                    front.entrenchment_d = min(ENTRENCH_MAX,
                                               front.entrenchment_d + 1)
            return ["The order is to hold; the lines deepen"]

        def _seek_terms(ctx, war=war) -> List[str]:
            return _try_peace(ctx.game, ctx.house, war)

        return Petition(
            pid=_next_pid(game), kind="war_council", domain="war",
            house=house_name,
            text=f"The Marshal convenes the war council on the war with House {other}",
            actors={"war": war},
            options=[
                PetitionOption("reinforce", "Reinforce the front", 60, _reinforce),
                PetitionOption("hold", "Hold the line", 0, _hold),
                PetitionOption("seek_terms", "Seek terms", -60, _seek_terms),
            ])
    return None


def generate_petitions(game, house_name: str) -> List[Petition]:
    """The turn's paper for one House, most urgent first, at most six."""
    realm = game.realms.get(house_name)
    if realm is None:
        return []
    rng = game.rng
    pets: List[Petition] = []
    pets.extend(_gen_seat_vacancies(game, house_name, realm, rng))
    for gen in (_gen_war_council, _gen_union_ultimatum, _gen_heir_demand,
                _gen_capital_request, _gen_disaster_inquiry,
                _gen_betrothal_offer, _gen_rail_proposal):
        p = gen(game, house_name, realm, rng)
        if p is not None:
            pets.append(p)
    pets.sort(key=lambda p: (DOMAIN_PRIORITY.get(p.domain, 9), p.pid))
    return pets[:MAX_PETITIONS]


# --- ruling ------------------------------------------------------------------

def _domain_stat(domain: str) -> str:
    seat = DOMAIN_SEAT.get(domain)
    return Court.POSITION_STATS[seat] if seat is not None else "statecraft"


def _conviction_grind(executor, domain: str, bias: int) -> List[str]:
    """Orders against conviction cost stress and bend the soul (spec 6.2)."""
    pair = DIRECTIVE_CONVICTION.get(domain)
    if pair is None:
        return []
    conviction = executor.dispositions.get(pair, 0.0)
    f = friction(bias, conviction)
    if f <= 0:
        return []
    out = []
    m = executor.add_stress(int(f / 5))
    if m:
        out.append(m)
    d = apply_drift(executor, pair, 3.0 if bias > conviction else -3.0,
                    "carrying out orders")
    if d:
        out.append(d)
    return out


def rule(game, petition, option_key, executor) -> List[str]:
    """Execute one option through one person. The chassis spends the
    attention point; this spends the person."""
    option = next((o for o in petition.options if o.key == option_key), None)
    if option is None:
        return [f"No such ruling '{option_key}' on the docket"]
    msgs: List[str] = []
    chance = 0.5 + executor.get_effective_stat(_domain_stat(petition.domain)) / 40.0
    chance = max(0.2, min(0.95, chance))
    scale = 1.0
    if game.rng.random() >= chance:
        scale = 0.5
        m = executor.add_stress(FUMBLE_STRESS)
        msgs.append(f"{executor.name} botches the execution of the ruling")
        if m:
            msgs.append(m)
    msgs.extend(_conviction_grind(executor, petition.domain, option.stance_bias))
    ctx = RulingContext(game, petition.house, executor, game.rng, scale)
    msgs.extend(option.apply(ctx))
    return msgs


def resolve_unattended(game, house_name: str, petitions) -> List[str]:
    """What happens to paper the ruler never touched: the seated minister
    rules by stance and conviction; seatless matters fester and then
    resolve themselves at the ugliest setting."""
    msgs: List[str] = []
    realm = game.realms.get(house_name)
    if realm is None:
        return msgs
    directives = getattr(game, "directives", {}).get(house_name)
    for p in petitions:
        seat = DOMAIN_SEAT.get(p.domain)
        holder = realm.court.positions.get(seat) if seat is not None else None
        if holder is not None and holder.is_alive:
            stance = directives.stances.get(p.domain, 0) if directives else 0
            pair = DIRECTIVE_CONVICTION.get(p.domain)
            conviction = holder.dispositions.get(pair, 0.0) if pair else 0.0
            want = (stance + conviction) / 2
            option = min(p.options, key=lambda o: abs(o.stance_bias - want))
            msgs.append(f"{holder.name} rules on the {p.kind.replace('_', ' ')} unprompted")
            msgs.extend(rule(game, p, option.key, holder))
        else:
            p.turns_waiting += 1
            if p.turns_waiting >= FESTER_TURNS:
                p.escalated = True
                option = min(p.options, key=lambda o: o.stance_bias)
                ctx = RulingContext(game, house_name, realm.ruler, game.rng, 0.5)
                msgs.append(f"Left to fester, the {p.kind.replace('_', ' ')} resolves itself")
                msgs.extend(option.apply(ctx))
    return msgs


# --- initiatives -------------------------------------------------------------

def director_candidates(game, house, eid) -> List:
    """Return eligible characters who could take a Director chair at enterprise eid,
    ranked by effective industry descending."""
    realm = game.realms[house]
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return []
    by_id = {ch.id: ch for ch in realm.characters}
    court_ids = {ch.id for ch in realm.court.positions.values() if ch}
    # Already-directing characters (any house enterprise)
    taken = set()
    for e in game.enterprises:
        d = by_id.get(e.director_id)
        if d is not None and d.is_alive:
            taken.add(d.id)
    pool = [ch for ch in realm.characters
            if ch.is_alive and ch.age >= 16 and ch.id != realm.ruler.id
            and ch.id not in taken and ch.id not in court_ids]
    pool.sort(key=lambda ch: ch.get_effective_stat("industry"), reverse=True)
    return pool


def _init_propose_marriage(ctx, target_house=None, **kw) -> List[str]:
    msg = ctx.game.marriages.arrange_match_between(
        ctx.house, target_house, ctx.game.realms, ctx.game.houses,
        _ents_by_house(ctx.game), ctx.rng)
    return [msg] if msg else [f"House {target_house} declines the proposal"]


def _init_found_enterprise(ctx, kind=None, province_pid=None, **kw) -> List[str]:
    house = ctx.game.houses[ctx.house]
    cost = ENTERPRISE_TYPES[kind][3]
    if house.treasury < cost:
        return [f"The House cannot raise the {cost:.0f} gold to charter a {KIND_TITLES[kind]}"]
    province = ctx.game.atlas.provinces[province_pid]
    eid = max((e.eid for e in ctx.game.enterprises), default=0) + 1
    ent = found_enterprise(kind, ctx.house, province, eid, ctx.rng)
    if ent is None:
        return [f"{province.name} lacks what a {KIND_TITLES[kind]} needs"]
    house.debit(ctx.game.turn, "charter", cost)
    initial_ledger(ent, ctx.game.realms[ctx.house])
    ctx.game.enterprises.append(ent)
    return [f"{ent.name} is chartered ({cost:.0f} gold)"]


def _init_expand_enterprise(ctx, eid=None, **kw) -> List[str]:
    ent = next((e for e in ctx.game.enterprises
                if e.eid == eid and e.house == ctx.house), None)
    if ent is None or ent.tier >= TIER_MAX or ent.under_construction > 0:
        return ["There is nothing there to expand"]
    house = ctx.game.houses[ctx.house]
    cost = EXPAND_COST[ent.tier + 1]
    if house.treasury < cost:
        return [f"The expansion of {ent.name} wants {cost:.0f} gold the House lacks"]
    house.debit(ctx.game.turn, "expansion", cost)
    ent.under_construction = EXPAND_TURNS[ent.tier + 1]
    ent.target_tier = ent.tier + 1
    return [f"{ent.name} breaks ground on tier {ent.tier + 1} ({cost:.0f} gold)"]


def _init_build_rail(ctx, a=None, b=None, **kw) -> List[str]:
    link = ctx.game.atlas.link(a, b)
    if link is None or link.rail:
        return ["No track to lay there"]
    house = ctx.game.houses[ctx.house]
    if house.treasury < RAIL_COST:
        return [f"The line wants {RAIL_COST:.0f} gold the House lacks"]
    house.debit(ctx.game.turn, "railway", RAIL_COST)
    link.rail = True
    pa = ctx.game.atlas.provinces[link.a].name
    pb = ctx.game.atlas.provinces[link.b].name
    return [f"Iron roads: the {pa}-{pb} line opens ({RAIL_COST:.0f} gold)"]


def _init_start_scheme(ctx, target=None, scheme_type=None, target_house=None, **kw) -> List[str]:
    ctx.game.scheme_mgr.start_scheme(ctx.executor, target, scheme_type, target_house)
    ctx.executor.add_stress(5 + ctx.executor.check_stress_action("scheme"))
    return [f"{ctx.executor.name} sets something in motion against {target.name}"]


def _init_tour_province(ctx, province_pid=None, **kw) -> List[str]:
    province = ctx.game.atlas.provinces[province_pid]
    province.unrest = max(0.0, province.unrest - TOUR_UNREST_RELIEF * ctx.scale)
    ruler = ctx.game.realms[ctx.house].ruler
    out = [f"{ruler.name} tours {province.name}; the crowds are managed carefully"]
    m = ruler.add_stress(TOUR_STRESS)
    if m:
        out.append(m)
    return out


def _init_adjust_garrison(ctx, **kw) -> List[str]:
    return ["The Marshal has no active war to garrison against (fronts arrive in G16)"]


def _init_declare_war(ctx, target_house=None, goal=None, **kw) -> List[str]:
    house = ctx.game.houses[ctx.house]
    if target_house not in ctx.game.houses or target_house == ctx.house:
        return [f"There is no House {target_house} to declare against"]
    if target_house in house.at_war_with:
        return [f"The House is already at war with House {target_house}"]
    truce = house.truces.get(target_house, 0)
    if truce > ctx.game.turn:
        return [f"A truce with House {target_house} holds until turn {truce}"]
    war = declare_war(ctx.game, ctx.house, target_house,
                      goal if goal is not None else WarGoal("humble"))
    out = [f"House {ctx.house} declares war on House {target_house}!"]
    if not war.fronts:
        out.append("No shared border: the war exists only on paper")
    return out


def _init_negotiate_peace(ctx, target_house=None, **kw) -> List[str]:
    war = next((w for w in ctx.game.wars
                if {w.aggressor, w.defender} == {ctx.house, target_house}),
               None)
    if war is None:
        return [f"There is no war with House {target_house} to end"]
    return _try_peace(ctx.game, ctx.house, war)


def _init_acquire_minor(ctx, province_pid=None, **kw) -> List[str]:
    province = ctx.game.atlas.provinces[province_pid]
    if province.owner != MINOR_OWNER:
        return [f"{province.name} already flies a Great House's colors"]
    owned = {p.pid for p in ctx.game.atlas.provinces.values() if p.owner == ctx.house}
    if not (province.neighbors & owned):
        return [f"{province.name} shares no border with the House's lands"]
    richness = sum(province.endowments.values())
    cost = 300.0 * province.development + 100.0 * richness
    house = ctx.game.houses[ctx.house]
    if house.treasury < cost:
        return [f"{province.name} would cost {cost:.0f} gold; the vault says no"]
    house.debit(ctx.game.turn, "province purchase", cost)
    province.owner = ctx.house
    return [f"{province.name} is bought into the House for {cost:.0f} gold"]


def _init_start_takeover(ctx, target_house=None, **kw) -> List[str]:
    from gilded.society.schemes import Takeover
    if target_house not in ctx.game.houses or target_house == ctx.house:
        return [f"There is no House {target_house} to buy into"]
    if any(t.buyer_house == ctx.house and t.target_house == target_house
           and not t.complete for t in ctx.game.takeovers):
        return [f"A quiet buying campaign against House {target_house} is already under way"]
    ctx.game.takeovers.append(Takeover(ctx.executor, ctx.house, target_house))
    return [f"{ctx.executor.name} begins quietly buying into House {target_house}"]


def _init_establish_informant(ctx, target_house=None, **kw) -> List[str]:
    if target_house not in ctx.game.houses or target_house == ctx.house:
        return [f"There is no House {target_house} to watch"]
    ctx.game.informants.add((ctx.house, target_house))
    return [f"{ctx.executor.name} places an informant inside House {target_house}"]


def _fmt_gold(x: float) -> str:
    """Format gold so that small sums never round to zero."""
    if x < 10:
        return f"{x:.2f}"
    return f"{x:.0f}"


def _exec_share_trade(ctx, seller, buyer, ent, pct: float, verb: str) -> List[str]:
    """Shared handler for buy_shares / sell_shares.

    *seller* is the current owner of the shares; *buyer* is the purchaser.
    *pct* is the requested percentage (already scaled by ctx.scale).
    *verb* is "buy" or "sell" — controls the wording of the result line.
    """
    from gilded.society.shares import priced_transfer
    market = ctx.game.market
    available = ent.ledger.get(seller.id, 0.0)
    actual_pct = min(pct, available)

    if actual_pct <= 0:
        return [f"{seller.name} has no stake in {ent.name}"]

    quote = priced_transfer(ent, seller, buyer, actual_pct, market, ctx.game, dry_run=True)
    if buyer.gold_reserve < quote:
        return [f"{buyer.name} cannot afford the stake ({_fmt_gold(quote)} gold)"]

    cost = priced_transfer(ent, seller, buyer, actual_pct, market, ctx.game)
    if verb == "sell":
        return [f"{seller.name} sells {actual_pct:.1f}% of {ent.name} to {buyer.name} for {_fmt_gold(cost)} gold"]
    return [f"{buyer.name} buys {actual_pct:.1f}% of {ent.name} from {seller.name} for {_fmt_gold(cost)} gold"]


def _init_buy_shares(ctx, eid=None, seller_id=None, pct=0.0, **kw) -> List[str]:
    ent = next((e for e in ctx.game.enterprises if e.eid == eid), None)
    if ent is None:
        return ["There is no such enterprise to buy from"]
    if pct <= 0:
        return ["Nothing to buy: the percentage is zero"]
    by_id = {c.id: c for r in ctx.game.realms.values() for c in r.characters}
    seller = by_id.get(seller_id)
    if seller is None:
        return ["There is no such person to trade with"]
    buyer = ctx.executor
    pct = pct * ctx.scale
    return _exec_share_trade(ctx, seller, buyer, ent, pct, "buy")


def _init_sell_shares(ctx, eid=None, buyer_id=None, pct=0.0, **kw) -> List[str]:
    ent = next((e for e in ctx.game.enterprises if e.eid == eid), None)
    if ent is None:
        return ["There is no such enterprise to sell from"]
    if pct <= 0:
        return ["Nothing to sell: the percentage is zero"]
    by_id = {c.id: c for r in ctx.game.realms.values() for c in r.characters}
    buyer = by_id.get(buyer_id)
    if buyer is None:
        return ["There is no such person to trade with"]
    seller = ctx.executor
    pct = pct * ctx.scale
    return _exec_share_trade(ctx, seller, buyer, ent, pct, "sell")


def _init_appoint_director(ctx, eid=None, char_id=None, **kw) -> List[str]:
    """Seat char_id as Director of enterprise eid, pay salary from ruler's stake."""
    game = ctx.game
    realm = game.realms[ctx.house]
    ent = next((e for e in game.enterprises if e.eid == eid), None)
    if ent is None:
        return ["There is no such enterprise to appoint a Director for"]
    # Consult the candidate pool — refuse anyone not offered
    pool = director_candidates(game, ctx.house, eid)
    pool_ids = {c.id for c in pool}
    if char_id not in pool_ids:
        return ["There is no such person to appoint as Director"]
    pick = next(c for c in pool if c.id == char_id)
    ent.director_id = pick.id
    moved = transfer_shares(ent, realm.ruler.id, pick.id, DIRECTOR_SALARY_PCT)
    modify_opinion(pick, realm.ruler, int(15 * ctx.scale), "made Director")
    if moved > 0:
        pct = f"{moved:g}"
        return [f"{pick.name} is appointed Director of {ent.name} ({pct}% shares salary)"]
    else:
        return [f"{pick.name} is appointed Director of {ent.name}"]


INITIATIVES = {           # verb -> (domain, handler); each costs 1 attention
    "propose_marriage": ("diplomacy", _init_propose_marriage),
    "found_enterprise": ("capital", _init_found_enterprise),
    "expand_enterprise": ("capital", _init_expand_enterprise),
    "build_rail": ("expansion", _init_build_rail),
    "start_scheme": ("press", _init_start_scheme),
    "tour_province": ("family", _init_tour_province),
    "adjust_garrison": ("war", _init_adjust_garrison),
    "acquire_minor": ("expansion", _init_acquire_minor),
    "declare_war": ("war", _init_declare_war),
    "negotiate_peace": ("diplomacy", _init_negotiate_peace),
    "start_takeover": ("capital", _init_start_takeover),
    "establish_informant": ("diplomacy", _init_establish_informant),
    "buy_shares": ("capital", _init_buy_shares),
    "sell_shares": ("capital", _init_sell_shares),
    "appoint_director": ("capital", _init_appoint_director),
}


def initiative(game, house_name: str, verb: str, executor, **kwargs) -> List[str]:
    """A proactive verb, routed through a person like any ruling."""
    if verb not in INITIATIVES:
        return [f"No such initiative '{verb}'"]
    domain, handler = INITIATIVES[verb]
    msgs: List[str] = []
    chance = 0.5 + executor.get_effective_stat(_domain_stat(domain)) / 40.0
    chance = max(0.2, min(0.95, chance))
    scale = 1.0
    if game.rng.random() >= chance:
        scale = 0.5
        m = executor.add_stress(FUMBLE_STRESS)
        msgs.append(f"{executor.name} botches the {verb.replace('_', ' ')}")
        if m:
            msgs.append(m)
    ctx = RulingContext(game, house_name, executor, game.rng, scale)
    msgs.extend(handler(ctx, **kwargs))
    return msgs
