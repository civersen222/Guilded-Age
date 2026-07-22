"""AI opponent logic: priority-based decision system that actually plays the game."""

from typing import Dict, List, Optional, Set, Tuple
import random
from game_data import (
    TECHNOLOGIES, UNIT_TYPES, BUILDINGS, CIVILIZATIONS,
    UnitCategory, TechBranch, Era, TerrainType,
)
from military import Unit
from court import Court, CourtPosition
from diplomacy_extended import TreatyType, CasusBelliType


TILES_PER_CITY = 25     # spec 0.1: one city controls ~25 land tiles once borders settle


class AIPlayer:
    """Simulates an opponent civilization's decisions with strategic depth."""

    def __init__(self, civ_name: str, difficulty: str = "medium"):
        self.civ_name = civ_name
        self.civ = CIVILIZATIONS.get(civ_name, CIVILIZATIONS["Rome"])
        self.difficulty = difficulty
        self.aggression: float = self._set_aggression()
        self.priorities: Dict[str, float] = {
            "military": 0.0, "science": 0.0,
            "economy": 0.0, "expansion": 0.0,
        }
        self._set_priorities()
        self.target_research: Optional[str] = None
        self.last_action: str = "idle"

        # State tracking
        self.known_enemy_strength: Dict[str, int] = {}
        self.known_enemy_tech: Dict[str, List[str]] = {}
        self.war_targets: List[str] = []
        self.trade_partners: Set[str] = set()
        self.allied_civs: Set[str] = set()
        self.city_expansion_history: List[Tuple[int, int]] = []
        self.military_build_history: List[Tuple[int, str]] = []
        self.research_path: List[str] = []

        # Treaty & diplomacy state
        self.active_treaties: Dict[str, Dict[str, any]] = {}
        self.desired_cb_types: Dict[str, CasusBelliType] = {}
        self.diplomacy_history: List[Dict[str, str]] = []
        self.preferred_era: Optional[Era] = None
        self.preferred_branch: Optional[TechBranch] = None
        self.aggression_modifiers: List[Tuple[str, float]] = []
        self.trust_level: Dict[str, float] = {}
        self.grudges: Dict[str, int] = {}
        self._takeover = None   # live hostile takeover vs the player (M76)

    # ── Priority evaluation ────────────────────────────────────────────────

    def _set_aggression(self) -> float:
        return {"easy": 0.2, "medium": 0.5, "hard": 0.8}.get(self.difficulty, 0.5)

    def _set_priorities(self):
        if self.difficulty == "easy":
            self.priorities = {"military": 0.2, "science": 0.3, "economy": 0.3, "expansion": 0.2}
        elif self.difficulty == "medium":
            self.priorities = {"military": 0.4, "science": 0.3, "economy": 0.2, "expansion": 0.1}
        else:
            self.priorities = {"military": 0.6, "science": 0.2, "economy": 0.1, "expansion": 0.1}

    def _evaluate_priorities(self, game) -> Dict[str, float]:
        """Set weights for military/science/economy/expansion based on game state."""
        cities = [c for c in game.cities.values() if c.owner == self.civ_name]
        units = [u for u in game.units.values() if u.owner == self.civ_name]
        gold = game.gold.get(self.civ_name, 0)
        r = game.research.get(self.civ_name)
        researched = list(r.researched.keys()) if r else []

        adj = self.priorities.copy()

        # Count threats
        threats = 0
        for civ_name, civ in game.civilizations.items():
            if civ_name == self.civ_name:
                continue
            enemy_units = [u for u in game.units.values() if u.owner == civ_name]
            strength = sum(u.attack for u in enemy_units)
            self.known_enemy_strength[civ_name] = strength
            if strength > 20:
                threats += 1

        if threats > 0 and self.aggression > 0.4:
            adj["military"] += threats * 0.15
        target = self._city_target(game)
        if len(cities) > target:
            adj["economy"] += 0.1
            adj["expansion"] -= 0.1
        if len(cities) < target:
            # Hunger scales with the remaining gap (M85), so mid-game houses
            # below target keep expanding through threat inflation.
            adj["expansion"] += min(0.8, 0.2 * (target - len(cities)))
        if gold > 150:
            adj["science"] += 0.1
        if len(researched) < 3:
            adj["science"] += 0.15

        total = sum(adj.values()) or 1
        return {k: v / total for k, v in adj.items()}

    # ── Research ────────────────────────────────────────────────────────────

    def _choose_next_tech(self, game) -> Optional[str]:
        """Pick tech based on highest priority."""
        tm = game.research.get(self.civ_name)
        if not tm:
            return None
        researched = set(tm.researched.keys())
        adj = self._evaluate_priorities(game)

        # Build candidate list with priorities
        candidates: List[Tuple[str, float]] = []
        for tech in TECHNOLOGIES.values():
            if tech.name in researched:
                continue
            if tech.prerequisites and not all(p in researched for p in tech.prerequisites):
                continue
            weight = 0.0
            if tech.branch == TechBranch.MILITARY:
                weight = adj["military"] * 3
            elif tech.branch == TechBranch.SCIENTIFIC:
                weight = adj["science"] * 3
            elif tech.branch == TechBranch.CIVIC:
                weight = adj["economy"] * 2
            else:
                weight = 1.0
            candidates.append((tech.name, weight))

        if not candidates:
            return None

        # Deterministic targeting (M74): best weight first, cheapest tie-break
        candidates.sort(key=lambda c: (-c[1], TECHNOLOGIES[c[0]].cost, c[0]))
        return candidates[0][0]

    # ── Production ──────────────────────────────────────────────────────────

    def _choose_production_for_city(self, city, game) -> Optional[str]:
        """Decide what a city should produce next."""
        adj = self._evaluate_priorities(game)
        cities = [c for c in game.cities.values() if c.owner == self.civ_name]
        units = [u for u in game.units.values() if u.owner == self.civ_name]
        tm = game.research.get(self.civ_name)
        researched = set(tm.researched.keys()) if tm else set()
        owned_resources = game.get_owned_resources(self.civ_name)

        # Count existing military vs workers/settlers
        military_count = sum(1 for u in units
                             if u.unit_type in UNIT_TYPES
                             and UNIT_TYPES[u.unit_type].category == UnitCategory.MELEE)
        worker_count = sum(1 for u in units
                           if u.unit_type in ("Worker", "Trader"))
        settler_count = sum(1 for u in units if u.unit_type == "Settler")

        # If below the map's fair share and no settler out, build settler
        if adj["expansion"] > 0.15 and len(cities) < self._city_target(game) and settler_count == 0:
            return "Settler"

        # If low on workers, build worker
        if worker_count < len(cities) * 2 and adj["economy"] > 0.2:
            return "Worker"

        # Army cap (M81): a House fields at most 3 + 2 per city; past the
        # cap the forges turn to civic works.
        soldiers = sum(1 for u in units
                       if getattr(u, 'is_alive', True)
                       and u.unit_type in UNIT_TYPES
                       and UNIT_TYPES[u.unit_type].category not in (UnitCategory.WORKER,
                                                                    UnitCategory.SETTLER))
        army_cap = 3 + 2 * len(cities)
        if soldiers < army_cap:
            # If military priority high or threats exist, build military unit
            if adj["military"] > 0.35 or len(self.war_targets) > 0:
                military_pool = self._get_available_military(researched, owned_resources)
                if military_pool:
                    return random.choice(military_pool)

            # Default: balance between production and military
            if adj["military"] > adj["science"] and random.random() < 0.5:
                military_pool = self._get_available_military(researched, owned_resources)
                if military_pool:
                    return random.choice(military_pool)
        return self._choose_building(city, researched)

    BUILD_ORDER = ["Monument", "Granary", "Shrine", "Workshop", "Aqueduct", "Factory"]

    def _choose_building(self, city, researched: Set[str]) -> Optional[str]:
        """The build order (M74): first unbuilt house we can raise without
        a district, gated only by tech."""
        built = getattr(city, "buildings", None) or {}
        for name in self.BUILD_ORDER:
            btype = BUILDINGS[name]
            if name in built:
                continue
            if btype.requires_tech and btype.requires_tech not in researched:
                continue
            return name
        return None

    def _dial_relief(self, city) -> float:
        """Ease the squeeze where the streets are hot (M74, spec 5.1)."""
        unrest = getattr(city, "unrest", 0.0)
        if unrest >= 50.0:
            return 20.0
        if unrest >= 25.0:
            return 10.0
        return 0.0

    def _get_available_military(self, researched: Set[str],
                                owned_resources: Optional[Set[str]] = None) -> List[str]:
        """Get military units available given researched tech and strategic resources (M32)."""
        pool = []
        for name, utype in UNIT_TYPES.items():
            if utype.category not in (UnitCategory.MELEE, UnitCategory.RANGED, UnitCategory.CAVALRY):
                continue
            if utype.requires_tech and utype.requires_tech not in researched:
                continue
            if (utype.resource_required and owned_resources is not None
                    and utype.resource_required not in owned_resources):
                continue
            pool.append(name)
        return pool

    def get_opinion_on_player(self) -> float:
        """Return opinion score of this AI toward the human player (-100 to 100)."""
        base = self.trust_level.get("player", 0.0)
        # Adjust by aggression and history
        if self.aggression > 0.6:
            base -= 10
        elif self.aggression < 0.3:
            base += 10
        # Grudges reduce opinion
        for civ, grudges in self.grudges.items():
            if civ != self.civ_name:
                base -= grudges * 5
        return max(-100, min(100, base))

    def _manage_production(self, game) -> List[str]:
        """For each AI city, assign production based on needs."""
        msgs = []
        cities = [c for c in game.cities.values() if c.owner == self.civ_name]
        if not cities:
            return msgs

        for city in cities:
            # If no current production, assign one
            if city.current_production is None:
                item = self._choose_production_for_city(city, game)
                if item:
                    city.assign_production(item, researched_techs=set(
                        game.research.get(self.civ_name, {}).researched.keys()
                        if game.research.get(self.civ_name) else set()
                    ), owned_resources=game.get_owned_resources(self.civ_name))
                    msgs.append(f"    🏭 {city.name}: producing {item}")

        # Advance production for all cities
        for city in cities:
            if city.current_production is None:
                continue
            cost = city.get_production_cost(city.current_production)
            if cost is None:
                continue
            capacity = city.calculate_production_capacity()
            city.production = min(city.production + capacity, city.production_capacity)

            if city.production >= cost:
                item = city.current_production
                if item in UNIT_TYPES:
                    new_unit = Unit(
                        unit_type=item, owner=self.civ_name,
                        position=city.position,
                        moves_left=UNIT_TYPES[item].movement,
                    )
                    new_unit.name = (f"{self.civ_name} {item} "
                                     f"{len([u for u in game.units.values() if u.owner == self.civ_name and u.unit_type == item])}")
                    game.units[new_unit.name] = new_unit
                    game.map.add_unit(new_unit)
                    self.military_build_history.append((game.state.turn, item))
                    msgs.append(f"    ✅ {city.name} completed: {item}")
                elif item in BUILDINGS:
                    city.add_building(BUILDINGS[item])
                    msgs.append(f"    ✅ {city.name} completed: {item}")
                if item in city.production_queue:
                    city.production_queue.remove(item)  # one order, one delivery (M81)
                city.current_production = None
                city.production = 0

        return msgs

    # ── Research management ─────────────────────────────────────────────────

    def _manage_research(self, game) -> List[str]:
        """Pick tech and advance research progress."""
        msgs = []
        tm = game.research.get(self.civ_name)
        if not tm:
            return msgs

        # If no target, pick one
        if self.target_research is None:
            self.target_research = self._choose_next_tech(game)

        if self.target_research and self.target_research not in tm.researched:
            tech = TECHNOLOGIES.get(self.target_research)
            if tech:
                cost = tech.cost
                # AI researches at 1 turn per cost unit (fast but not instant)
                tm.research_progress[self.target_research] = \
                    tm.research_progress.get(self.target_research, 0) + 1

                if tm.research_progress[self.target_research] >= cost:
                    # Actually complete the research
                    tm.researched[self.target_research] = tech
                    self.research_path.append(self.target_research)
                    msgs.append(f"    🔬 Researched: {self.target_research}")
                    # Pick next target
                    self.target_research = self._choose_next_tech(game)
                else:
                    msgs.append(f"    🔬 Progress on {self.target_research}: "
                                f"{tm.research_progress[self.target_research]}/{cost}")

        return msgs

    # ── Military management ─────────────────────────────────────────────────

    def _army_strength(self, game, civ: str) -> float:
        """Sum of attack across a House's living soldiers (M75)."""
        total = 0.0
        for u in game.units.values():
            if u.owner != civ or not u.is_alive:
                continue
            utype = UNIT_TYPES.get(u.unit_type)
            if utype is None or utype.category in (UnitCategory.WORKER,
                                                   UnitCategory.SETTLER):
                continue
            total += u.attack
        return total

    def _assign_commanders(self, game) -> List[str]:
        """Post the House's best captains on its leaderless soldiers
        (M75, spec 4.4)."""
        realm = getattr(game, "realms", {}).get(self.civ_name)
        if realm is None:
            return []
        busy = set()
        ruler = getattr(realm, "ruler", None)
        if ruler is not None:
            busy.add(ruler.id)
        for u in game.units.values():
            cmd = getattr(u, "commander", None)
            if cmd is not None and cmd.is_alive:
                busy.add(cmd.id)
        for c in game.cities.values():
            d = getattr(c, "director", None)
            if d is not None and d.is_alive:
                busy.add(d.id)
        pool = [ch for ch in getattr(realm, "characters", [])
                if ch.is_alive and ch.age >= 16 and ch.id not in busy]
        pool.sort(key=lambda ch: (-ch.get_effective_stat("command"), ch.id))
        soldiers = []
        for u in game.units.values():
            if u.owner != self.civ_name or not u.is_alive:
                continue
            utype = UNIT_TYPES.get(u.unit_type)
            if utype is None or utype.category in (UnitCategory.WORKER,
                                                   UnitCategory.SETTLER):
                continue
            cmd = getattr(u, "commander", None)
            if cmd is None or not cmd.is_alive:
                soldiers.append(u)
        soldiers.sort(key=lambda u: -u.attack)
        msgs = []
        for unit, captain in zip(soldiers, pool):
            unit.commander = captain
            msgs.append(f"    🎖️ {captain.name} takes command of the {unit.unit_type}")
        return msgs

    def _manage_military(self, game) -> List[str]:
        """Move units toward threats or garrison cities — units actually move."""
        msgs = []
        units = [u for u in game.units.values()
                 if u.owner == self.civ_name and u.is_alive and u.moves_left > 0]
        if not units:
            return msgs

        enemy_units = [u for u in game.units.values()
                       if u.owner != self.civ_name and u.is_alive]
        enemy_cities = [c for c in game.cities.values() if c.owner != self.civ_name]
        enemy_targets = enemy_units + enemy_cities
        # Wars of conquest (M75): while at war, the army marches on the
        # enemy's soldiers and cities - not whoever happens to be nearest.
        dm = getattr(game, "diplomacy_manager", None)
        if dm is not None:
            war_targets = [t for t in enemy_targets
                           if dm.is_at_war(self.civ_name, t.owner)]
            if war_targets:
                enemy_targets = war_targets

        def step_toward(unit, target_pos):
            """Move one land tile toward target_pos. move_unit handles combat."""
            best = None
            best_d = game.map.get_distance(unit.position[0], unit.position[1],
                                           target_pos[0], target_pos[1])
            for n in game.map.get_neighbors(unit.position[0], unit.position[1]):
                if n.terrain in (TerrainType.WATER_COAST, TerrainType.OCEAN):
                    continue
                d = game.map.get_distance(n.x, n.y, target_pos[0], target_pos[1])
                if d < best_d:
                    best_d = d
                    best = (n.x, n.y)
            if best is not None:
                return game.military_manager.move_unit(unit, best)
            return False

        for unit in units:
            utype = UNIT_TYPES.get(unit.unit_type)
            if not utype:
                continue
            if utype.category in (UnitCategory.WORKER, UnitCategory.SETTLER):
                continue

            # Nearest enemy target
            target = None
            target_dist = float('inf')
            for t in enemy_targets:
                d = game.map.get_distance(unit.position[0], unit.position[1],
                                          t.position[0], t.position[1])
                if d < target_dist:
                    target_dist = d
                    target = t

            # Siege (M31): adjacent enemy city while at war -> assault it
            if (target is not None and hasattr(target, "population")
                    and target_dist <= 1
                    and game.diplomacy_manager.is_at_war(self.civ_name, target.owner)):
                result = game.military_manager.attack_city(unit, target)
                if result:
                    msgs.append(f"    {result}")
                    game.state.turn_events.append(result)
                    unit.moves_left = 0
                    continue

            if target is not None and self.aggression > 0.4 and target_dist <= 5:
                if step_toward(unit, target.position):
                    msgs.append(f"    ⚔️ {unit.unit_type} advances toward the enemy")
                unit.moves_left = 0
                continue

            # Garrison nearest own city
            nearest = None
            near_dist = float('inf')
            for c in game.cities.values():
                if c.owner == self.civ_name:
                    d = game.map.get_distance(unit.position[0], unit.position[1],
                                              c.position[0], c.position[1])
                    if d < near_dist:
                        near_dist = d
                        nearest = c
            if nearest is not None and near_dist > 1:
                if step_toward(unit, nearest.position):
                    msgs.append(f"    🏰 {unit.unit_type} moves to garrison {nearest.name}")
            unit.moves_left = 0

        return msgs
    def _manage_diplomacy(self, game) -> List[str]:
        """AI diplomatic decisions based on relation scores each turn."""
        msgs = []
        other_civs = [n for n in game.civilizations if n != self.civ_name]

        for target in other_civs:
            relation = game.diplomacy_manager.get_relation(self.civ_name, target)
            at_war = self._is_at_war(game, target)
            allied = target in self.allied_civs
            trading = target in self.trade_partners

            # War of conquest (M75, spec 5): the House marches only when it
            # is half again as strong as its prey - never on a coin flip.
            if relation < -30 and not at_war:
                mine = self._army_strength(game, self.civ_name)
                theirs = self._army_strength(game, target)
                if (self.aggression >= 0.4 and mine >= 10.0
                        and mine >= 1.5 * theirs
                        and game.diplomacy_manager.declare_war(self.civ_name, target)):
                    if target not in self.war_targets:
                        self.war_targets.append(target)
                    msg = f"⚔️ {self.civ_name} declares war on {target} (relation {relation})"
                    msgs.append(f"    {msg}")
                    game.state.turn_events.append(msg)
                    self.diplomacy_history.append({
                        "action": "declare_war", "target": target,
                        "turn": game.state.turn,
                    })

            # War weariness (M33): weary AIs sue for peace
            elif at_war and game.war_weariness.get(self.civ_name, 0) >= 50:
                if random.random() < 0.25:
                    ruler = game.rulers.get(self.civ_name)
                    result = game.diplomacy_manager.propose_peace(self.civ_name, target, ruler)
                    msgs.append(f"    {result}")
                    game.state.turn_events.append(result)
                    if not game.diplomacy_manager.is_at_war(self.civ_name, target):
                        if target in self.war_targets:
                            self.war_targets.remove(target)

            # Relation > 30 and not allied: 15% chance propose alliance
            elif relation > 30 and not allied and not at_war:
                if random.random() < 0.15:
                    game.diplomacy_manager.propose_alliance(self.civ_name, target)
                    self.allied_civs.add(target)
                    msg = f"🤝 {self.civ_name} forms alliance with {target} (relation {relation})"
                    msgs.append(f"    {msg}")
                    game.state.turn_events.append(msg)
                    self.diplomacy_history.append({
                        "action": "alliance", "target": target,
                        "turn": game.state.turn,
                    })

            # Relation > 10, no trade: 10% chance sign trade
            elif relation > 10 and not trading and not at_war:
                if random.random() < 0.1:
                    game.diplomacy_manager.sign_trade_agreement(self.civ_name, target, 10)
                    self.trade_partners.add(target)
                    msg = f"💰 {self.civ_name} signs trade with {target} (relation {relation})"
                    msgs.append(f"    {msg}")
                    game.state.turn_events.append(msg)
                    self.diplomacy_history.append({
                        "action": "trade", "target": target,
                        "turn": game.state.turn,
                    })

        return msgs

    INTRIGUE_CADENCE = 5    # the character game moves every fifth turn

    def _manage_intrigue(self, game) -> List[str]:
        """The character game (M76, spec 6): knives for war enemies,
        weddings for friends, and the bloodless kill aimed at the
        player's House."""
        msgs = []
        realm = getattr(game, "realms", {}).get(self.civ_name)
        ruler = getattr(realm, "ruler", None)
        if realm is None or ruler is None or not ruler.is_alive:
            return msgs
        # A running takeover is pressed every single turn.
        if self._takeover is not None:
            msgs.extend(f"    🗝️ {m}" for m in self._takeover.advance())
            if self._takeover.complete:
                self._takeover = None
        if game.state.turn % self.INTRIGUE_CADENCE != 0:
            return msgs
        dm = game.diplomacy_manager
        others = [n for n in game.civilizations if n != self.civ_name]
        # 1. The knife: the most hated House's ruler draws a conspiracy.
        sm = getattr(game, "scheme_manager", None)
        enemies = [n for n in others
                   if dm.is_at_war(self.civ_name, n)
                   or dm.get_relation(self.civ_name, n) < -30]
        if sm is not None and enemies:
            enemies.sort(key=lambda n: dm.get_relation(self.civ_name, n))
            target = game.rulers.get(enemies[0])
            pool = [ch for ch in realm.characters
                    if ch.is_alive and ch.age >= 16 and ch.id != ruler.id
                    and not sm.scheming(ch)]
            pool.sort(key=lambda ch: (-ch.get_effective_stat("intrigue"), ch.id))
            if (target is not None and target.is_alive and pool
                    and not any(s.agent in realm.characters for s in sm.schemes)):
                scheme = sm.start_scheme(pool[0], target, "assassination",
                                         enemies[0])
                for ally in pool[1:3]:
                    scheme.add_participant(ally)
                msgs.append(f"    🗡️ Agents of {self.civ_name} move against {target.name}")
        # 2. The wedding: bind the warmest friend by marriage-as-merger.
        friends = [n for n in others
                   if not dm.is_at_war(self.civ_name, n)
                   and dm.get_relation(self.civ_name, n) >= 20]
        if friends:
            friends.sort(key=lambda n: -dm.get_relation(self.civ_name, n))
            from marriages import arrange_match_between
            line = arrange_match_between(game, self.civ_name, friends[0])
            if line:
                msgs.append(f"    💍 {line}")
        # 3. The bloodless kill: a rich, hostile House buys the player out.
        player = getattr(game, "player_civ", None)
        if (self._takeover is None and player is not None
                and player.name != self.civ_name
                and dm.get_relation(self.civ_name, player.name) < 0):
            prealm = getattr(game, "realms", {}).get(player.name)
            if (prealm is not None and getattr(prealm, "enterprises", None)
                    and ruler.gold_reserve >= 150.0):
                from schemes import Takeover
                self._takeover = Takeover(ruler, realm, prealm)
                msgs.append(f"    🗝️ House {self.civ_name} begins quietly buying "
                            f"House {player.name} paper")
        return msgs

    def _is_at_war(self, game, target: str) -> bool:
        return game.diplomacy_manager.is_at_war(self.civ_name, target)

    def _evaluate_diplomacy_stance(self, other_civ: str, game_state) -> str:
        """Evaluate stance toward another civ: 'friendly', 'neutral', or 'hostile'.

        Considers: trust_level, active treaties, military strength comparison, grudges.
        """
        trust = self.trust_level.get(other_civ, 50)
        grudges = self.grudges.get(other_civ, 0)
        relations = game_state.diplomacy_manager.relations.get(self.civ_name, {})
        relation_status = relations.get(other_civ, "neutral")

        # Active treaty overrides
        if relation_status == "war":
            return "hostile"
        if relation_status == "alliance":
            return "friendly"

        # Grudges push toward hostile
        stance_score = 0.0
        stance_score += trust  # trust ranges -100..100, centered at 50 default
        stance_score -= grudges * 25  # each grudge subtracts 25 points

        # Military strength comparison
        our_strength = sum(
            u.hp for u in game_state.units.values()
            if u.owner == self.civ_name
        ) if hasattr(game_state, 'units') else 0
        their_strength = self.known_enemy_strength.get(other_civ, 0)
        if our_strength > 0 and their_strength > 0:
            if our_strength > their_strength * 1.5:
                stance_score += 15  # we're stronger, slightly more aggressive
            elif their_strength > our_strength * 1.5:
                stance_score -= 15  # they're stronger, more cautious

        if stance_score > 30:
            return "friendly"
        elif stance_score < -10:
            return "hostile"
        return "neutral"

    # ── City expansion ──────────────────────────────────────────────────────

    def _city_target(self, game) -> int:
        """This House's fair share of the map (spec 0.1): land / 25 / civs.
        The share is claimed at a human pace (M82): +1 city allowance every
        40 turns, so the land grab is an arc, not a turn-25 sprint."""
        tiles = getattr(getattr(game, "map", None), "tiles", None) or {}
        land = sum(1 for t in tiles.values()
                   if t.terrain not in (TerrainType.WATER_COAST, TerrainType.OCEAN))
        civs = max(1, len(getattr(game, "civilizations", None) or {}))
        fair = max(4, round(land / TILES_PER_CITY / civs))
        state = getattr(game, "state", None)
        if state is None:
            return fair
        return min(fair, 4 + state.turn // 40)

    def _manage_expansion(self, game) -> List[str]:
        """Build settlers and found new cities."""
        msgs = []
        cities = [c for c in game.cities.values() if c.owner == self.civ_name]
        settlers = [u for u in game.units.values()
                    if u.owner == self.civ_name and u.unit_type == "Settler"
                    and u.is_alive and u.moves_left > 0]

        # If we have settlers and land unclaimed, try to found a new city
        if settlers and len(cities) < self._city_target(game):
            settler = settlers[0]
            tile = self._find_expansion_tile(game, settler.position)
            # March the settler toward the chosen frontier (M85).
            if tile and tile != settler.position:
                tx, ty = tile if isinstance(tile, tuple) else (tile.x, tile.y)
                px, py = settler.position if isinstance(settler.position, tuple) else (settler.position.x, settler.position.y)
                dx = tx - px
                dy = ty - py
                steps = min(settler.moves_left, max(abs(dx), abs(dy)))
                for _ in range(steps):
                    nx = px + (1 if dx > 0 else -1 if dx < 0 else 0)
                    ny = py + (1 if dy > 0 else -1 if dy < 0 else 0)
                    target = game.map.tiles.get((nx, ny))
                    if target:
                        settler.position = (nx, ny)
                        settler.moves_left -= 1
                        px, py = nx, ny
                        dx = tx - nx
                        dy = ty - ny
            if tile and tile == settler.position:
                new_city = game.found_city(settler)
                self.city_expansion_history.append((game.state.turn, len(cities) + 1))
                msgs.append(f"    🏛️ Founded {new_city.name} at {tile}")

        return msgs

    def _find_expansion_tile(self, game, current_pos, min_dist: int = 4):
        """Find a valid tile for a new city — nearest good frontier (M85)."""
        city_positions = [c.position for c in game.cities.values()
                          if c.owner == self.civ_name]
        candidates = []
        for t in game.map.tiles.values():
            if t.terrain.value in ("Ocean",):
                continue
            if any(game.map.get_distance(t.x, t.y, cx, cy) < min_dist
                   for cx, cy in city_positions):
                continue
            candidates.append((t.x, t.y))
        if not candidates:
            return None
        # Prefer nearest good land (M85) so settlers don't march across the map.
        def score(pos):
            s = 0
            tile = game.map.tiles.get(pos)
            if tile and tile.terrain.value == "Grassland":
                s += 2
            if tile and tile.terrain.value == "Plains":
                s += 1
            # Tie-break: prefer closer tiles (negate distance for reverse sort)
            dist = game.map.get_distance(pos[0], pos[1], current_pos[0], current_pos[1])
            s -= dist * 0.01
            return s
        candidates.sort(key=score, reverse=True)
        return candidates[0]

    RELIGION_FAITH_COST = 80

    def _manage_religion(self, game) -> List[str]:
        """Found a religion when the faith pool allows (M80): the AI joins
        the faith race instead of hoarding an untouched pool."""
        rm = getattr(game, "religion_manager", None)
        if rm is None:
            return []
        if any(rel.founder == self.civ_name for rel in rm.religions.values()):
            return []
        if game.faith_points.get(self.civ_name, 0) < self.RELIGION_FAITH_COST:
            return []
        game.faith_points[self.civ_name] -= self.RELIGION_FAITH_COST
        name = f"Faith of {self.civ_name}"
        rm.found_religion(name, self.civ_name)
        return [f"    {self.civ_name} founds {name}!"]

    # ── Main entry point ────────────────────────────────────────────────────

    def take_turn(self, game) -> List[str]:
        """Execute one full AI turn: research → production → military → diplomacy → expansion."""
        msgs = []
        msgs.append(f"  === {self.civ_name}'s turn ===")

        # Re-evaluate priorities based on current state
        self._evaluate_priorities(game)
        msgs.append(f"    Strategy: {self.priorities['military']*100:.0f}% military, "
                     f"{self.priorities['science']*100:.0f}% science, "
                     f"{self.priorities['economy']*100:.0f}% economy, "
                     f"{self.priorities['expansion']*100:.0f}% expansion")

        # Extraction dial (M55, spec 5.1): the ruler's convictions set how
        # hard every House city squeezes its labor this turn; hot streets
        # get relief (M74).
        from labor import clamp_dial, dial_from_ruler
        _realm = getattr(game, "realms", {}).get(self.civ_name)
        _dial = dial_from_ruler(getattr(_realm, "ruler", None))
        for _city in game.cities.values():
            if _city.owner == self.civ_name:
                _city.extraction_dial = clamp_dial(
                    _dial - self._dial_relief(_city))

        # 1. Research
        msgs.extend(self._manage_research(game))

        # 2. Production (units, buildings)
        msgs.extend(self._manage_production(game))

        # 3. Military actions: post the captains, then march (M75)
        msgs.extend(self._assign_commanders(game))
        msgs.extend(self._manage_military(game))

        # 3b. Field promotions resolve on the spot (M81)
        for _u in game.units.values():
            if _u.owner == self.civ_name and getattr(_u, "pending_promotion", False):
                _u.accept_promotion("attack")

        # 4. Diplomacy, then the character game (M76)
        msgs.extend(self._manage_diplomacy(game))
        msgs.extend(self._manage_intrigue(game))

        # 4b. Faith: found a religion once the pool overflows (M80)
        msgs.extend(self._manage_religion(game))

        # 5. Expansion
        msgs.extend(self._manage_expansion(game))

        self.last_action = "turn_processed"
        return msgs

    # ── Legacy helper (kept for compatibility) ──────────────────────────────

    def decide_next_action(self, current_tech: List[str], cities_count: int,
                           military_strength: int, available_gold: float,
                           available_tiles: List[Tuple[int, int]] = None) -> Dict[str, any]:
        """Legacy API — kept for compatibility with old callers."""
        action = {
            "type": "research", "target": None, "build": None,
            "expand": False, "attack": False, "diplo_action": None,
            "diplo_target": None, "target_tile": None,
        }
        adj = self.priorities
        if adj["military"] > 0.4 and military_strength < 50:
            action["build"] = self._choose_military_unit(set(current_tech))
        elif adj["economy"] > 0.3:
            action["build"] = "Worker"
        elif adj["expansion"] > 0.3 and cities_count < 5:
            action["expand"] = True
            action["build"] = "Settler"
        if random.random() < self.aggression and military_strength > 30:
            action["attack"] = True
        self.last_action = action["type"]
        return action

    def _choose_military_unit(self, researched: Set[str]) -> str:
        """Choose military unit based on researched tech and current threats."""
        pool = self._get_available_military(researched)
        if not pool:
            pool = ["Swordsman", "Archer"]
        return random.choice(pool)

    # ── State helpers ───────────────────────────────────────────────────────

    def update_enemy_intelligence(self, enemy_name: str, strength: int, tech_list: List[str]):
        self.known_enemy_strength[enemy_name] = strength
        self.known_enemy_tech[enemy_name] = tech_list
        if strength > 60 and enemy_name not in self.war_targets:
            self.war_targets.append(enemy_name)

    def update_trust(self, civ_name: str, change: float):
        self.trust_level[civ_name] = max(-100, min(100,
            self.trust_level.get(civ_name, 50) + change))

    def record_broken_promise(self, civ_name: str):
        self.grudges[civ_name] = self.grudges.get(civ_name, 0) + 1
        self.update_trust(civ_name, -30)

    def get_ai_summary(self) -> str:
        return (f"\n=== AI ({self.civ_name}) ===  Diff: {self.difficulty}  "
                f"Aggro: {self.aggression:.1f}  Last: {self.last_action}")

    def to_dict(self) -> dict:
        return {
            "civ_name": self.civ_name, "difficulty": self.difficulty,
            "aggression": self.aggression, "priorities": self.priorities,
            "last_action": self.last_action,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AIPlayer':
        ai = cls(data["civ_name"], data["difficulty"])
        ai.aggression = data["aggression"]
        ai.priorities = data["priorities"]
        ai.last_action = data["last_action"]
        return ai
