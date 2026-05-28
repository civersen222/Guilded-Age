"""AI opponent logic: priority-based decision system that actually plays the game."""

from typing import Dict, List, Optional, Set, Tuple
import random
from game_data import (
    TECHNOLOGIES, UNIT_TYPES, BUILDINGS, CIVILIZATIONS,
    UnitCategory, TechBranch, Era,
)
from military import Unit
from court import Court, CourtPosition
from diplomacy_extended import TreatyType, CasusBelliType


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
        if len(cities) > 5:
            adj["economy"] += 0.1
            adj["expansion"] -= 0.1
        if len(cities) < 4:
            adj["expansion"] += max(0, 0.8 - 0.2 * len(cities))
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

        # Weighted random pick, fallback to highest weight
        candidates.sort(key=lambda x: x[1], reverse=True)
        if random.random() < 0.6:
            return candidates[0][0]
        top = [c for c in candidates if c[1] >= candidates[0][1] * 0.5]
        if top:
            return random.choice(top)[0]
        return candidates[0][0]

    # ── Production ──────────────────────────────────────────────────────────

    def _choose_production_for_city(self, city, game) -> Optional[str]:
        """Decide what a city should produce next."""
        adj = self._evaluate_priorities(game)
        cities = [c for c in game.cities.values() if c.owner == self.civ_name]
        units = [u for u in game.units.values() if u.owner == self.civ_name]
        tm = game.research.get(self.civ_name)
        researched = set(tm.researched.keys()) if tm else set()

        # Count existing military vs workers/settlers
        military_count = sum(1 for u in units
                             if u.unit_type in UNIT_TYPES
                             and UNIT_TYPES[u.unit_type].category == UnitCategory.MELEE)
        worker_count = sum(1 for u in units
                           if u.unit_type in ("Worker", "Trader"))
        settler_count = sum(1 for u in units if u.unit_type == "Settler")

        # If low on settlers and few cities, build settler
        if adj["expansion"] > 0.15 and len(cities) < 6 and settler_count == 0:
            return "Settler"

        # If low on workers, build worker
        if worker_count < len(cities) * 2 and adj["economy"] > 0.2:
            return "Worker"

        # If military priority high or threats exist, build military unit
        if adj["military"] > 0.35 or len(self.war_targets) > 0:
            military_pool = self._get_available_military(researched)
            if military_pool:
                return random.choice(military_pool)

        # Default: balance between production and military
        if adj["military"] > adj["science"] and random.random() < 0.5:
            military_pool = self._get_available_military(researched)
            if military_pool:
                return random.choice(military_pool)
        return "Barracks" if "Barracks" not in getattr(city, "buildings", []) else "Marketplace"

    def _get_available_military(self, researched: Set[str]) -> List[str]:
        """Get military units available given researched tech."""
        pool = []
        for name, utype in UNIT_TYPES.items():
            if utype.category not in (UnitCategory.MELEE, UnitCategory.RANGED, UnitCategory.CAVALRY):
                continue
            if utype.requires_tech and utype.requires_tech not in researched:
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
                    ))
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

    def _manage_military(self, game) -> List[str]:
        """Move units toward threats, garrison cities."""
        msgs = []
        units = [u for u in game.units.values()
                 if u.owner == self.civ_name and u.is_alive and u.moves_left > 0]
        if not units:
            return msgs

        # Find nearest enemy unit/city for each military unit
        enemy_units = [u for u in game.units.values()
                       if u.owner != self.civ_name and u.is_alive]
        enemy_cities = [c for c in game.cities.values() if c.owner != self.civ_name]
        enemy_targets = enemy_units + enemy_cities

        for unit in units:
            utype = UNIT_TYPES.get(unit.unit_type)
            if not utype:
                continue

            # Workers don't fight, move toward friendly cities for improvements
            if utype.category == UnitCategory.WORKER:
                # Move toward unimproved tiles near cities (simplified: just stay put)
                continue

            # Settlers don't fight, stay near cities
            if utype.category == UnitCategory.SETTLER:
                continue

            # Military units: move toward threats or garrison
            if enemy_targets and self.aggression > 0.4:
                # Find nearest enemy
                best_target = None
                best_dist = float('inf')
                for t in enemy_targets:
                    d = game.map.get_distance(unit.position[0], unit.position[1],
                                              t.position[0], t.position[1])
                    if d < best_dist:
                        best_dist = d
                        best_target = t

                if best_target and best_dist <= 3:
                    # Attack if close enough
                    if best_target in enemy_units:
                        msgs.append(f"    ⚔️ {unit.name} attacks {best_target.name}")
                        # Simplified: just record intent, actual combat in game.py
                    unit.moves_left = 0
                    continue

            # Move one tile toward nearest city or threat
            if enemy_targets and best_dist <= 5:
                # Move toward threat
                pass  # Simplified: don't move for now, just garrison
            else:
                # Garrison nearest city
                nearest = None
                near_dist = float('inf')
                for c in game.cities.values():
                    if c.owner == self.civ_name:
                        d = game.map.get_distance(unit.position[0], unit.position[1],
                                                  c.position[0], c.position[1])
                        if d < near_dist:
                            near_dist = d
                            nearest = c
                if nearest and near_dist > 1:
                    msgs.append(f"    🏰 {unit.name} garrisoning {nearest.name}")

            unit.moves_left = 0

        return msgs

    # ── Diplomacy management ────────────────────────────────────────────────

    def _manage_diplomacy(self, game) -> List[str]:
        """Propose treaties when beneficial, declare war when strong."""
        msgs = []
        other_civs = [n for n in game.civilizations if n != self.civ_name]

        for target in other_civs:
            strength = self.known_enemy_strength.get(target, 0)
            trust = self.trust_level.get(target, 50)

            # Declare war if strong and target is weak
            if (self.aggression > 0.6 and strength < 30
                    and target not in self.allied_civs
                    and not self._is_at_war(game, target)):
                if random.random() < self.aggression * 0.3:
                    game.diplomacy_manager.declare_war(self.civ_name, target)
                    self.war_targets.append(target)
                    msgs.append(f"    ⚔️ {self.civ_name} declares war on {target}!")
                    self.diplomacy_history.append({
                        "action": "declare_war", "target": target,
                        "turn": game.state.turn,
                    })

            # Form alliance if peaceful and trust is high
            elif self.aggression < 0.4 and trust > 40:
                if target not in self.allied_civs:
                    game.diplomacy_manager.propose_alliance(self.civ_name, target)
                    self.allied_civs.add(target)
                    msgs.append(f"    🤝 {self.civ_name} allies with {target}")

            # Trade agreement if gold surplus
            elif game.gold.get(self.civ_name, 0) > 100 and trust > 0:
                game.diplomacy_manager.propose_trade_agreement(self.civ_name, target)
                self.trade_partners.add(target)
                msgs.append(f"    💰 {self.civ_name} trades with {target}")

        return msgs

    def _is_at_war(self, game, target: str) -> bool:
        relations = game.diplomacy_manager.relations.get(self.civ_name, {})
        return relations.get(target) == "war"

    # ── City expansion ──────────────────────────────────────────────────────

    def _manage_expansion(self, game) -> List[str]:
        """Build settlers and found new cities."""
        msgs = []
        cities = [c for c in game.cities.values() if c.owner == self.civ_name]
        settlers = [u for u in game.units.values()
                    if u.owner == self.civ_name and u.unit_type == "Settler"
                    and u.is_alive and u.moves_left > 0]

        # If we have settlers and few cities, try to found a new city
        if settlers and len(cities) < 6:
            settler = settlers[0]
            tile = self._find_expansion_tile(game, settler.position)
            if tile:
                from city import City
                from game_data import get_climate_for_row
                is_coastal = game.map.tiles[tile].terrain.value in ("Coast", "Ocean")
                new_city = City(
                    name=f"{self.civ_name} City {len(cities) + 1}",
                    owner=self.civ_name, position=tile,
                    population=3, gold=50,
                    climate_zone=get_climate_for_row(tile[1], game.map.height),
                    is_coastal=is_coastal,
                )
                game.cities[new_city.name] = new_city
                game.map.add_city(new_city)
                game.gold[self.civ_name] = game.gold.get(self.civ_name, 0) - 100
                settler.moves_left = 0
                self.city_expansion_history.append((game.state.turn, len(cities) + 1))
                msgs.append(f"    🏛️ Founded {new_city.name} at {tile}")

        return msgs

    def _find_expansion_tile(self, game, current_pos, min_dist: int = 4):
        """Find a valid tile for a new city."""
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
        # Prefer tiles near resources/water
        def score(pos):
            s = 0
            tile = game.map.tiles.get(pos)
            if tile and tile.terrain.value == "Grassland":
                s += 2
            if tile and tile.terrain.value == "Plains":
                s += 1
            return s
        candidates.sort(key=score, reverse=True)
        return candidates[0]

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

        # 1. Research
        msgs.extend(self._manage_research(game))

        # 2. Production (units, buildings)
        msgs.extend(self._manage_production(game))

        # 3. Military actions
        msgs.extend(self._manage_military(game))

        # 4. Diplomacy
        msgs.extend(self._manage_diplomacy(game))

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
