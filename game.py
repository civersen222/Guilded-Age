# CivKings Game Engine
"""
CivKings - Main Game Class
Orchestrates the game loop, turn management, and state
"""
import random
from typing import List, Dict, Optional, Tuple, Union, Any
from dataclasses import dataclass
from game_data import (
    TerrainType, VICTORY_CONDITIONS,
    TECHNOLOGIES, Technology, Era, TechBranch,
    TRAIT_DATABASE, CIVILIZATIONS, Civilization,
    COASTLINE_BONUSES, LANDMARKS, LandmarkType, ClimateZone, get_climate_for_row,
    UNIT_TYPES, UnitCategory, BUILDINGS
)
from hex_map import HexMap, HexTile, ExponentialFogOfWar
from city import City
from military import Unit
from simulation import Character, Dynasty, generate_child, modify_opinion, DynastyManager, execute_succession, SUCCESSION_LAWS
from court import Court, CourtPosition
from realms import create_realms
from character_ai import tick_realms
from relationships import tick_relationships
from marriages import tick_marriages
from city import CityManager
from military import MilitaryManager
from economy import EconomyManager
from diplomacy import DiplomacyManager
from religion import ReligionManager
from tech import TechManager, EurekaTracker, EUREKA_CONDITIONS
from events import EventManager
from plots import PlotManager
from victory import VictoryConditionTracker, VictoryType
from tax_system import TaxSystem
from happiness_system import HappinessSystem
from stability_system import StabilitySystem
from market_simulation import MarketSimulation
from gold_management import GoldManagement
from external_trade_routes import ExternalTradeRoutes
from faction_system import FactionManager, FactionEventGenerator
from ai import AIPlayer
from improvements import ImprovementManager
from great_people import GreatPeopleManager
from era_system import EraSystem

RESOURCE_TYPES = {
    "wheat": {"food": 2},
    "iron": {"production": 2},
    "gold_ore": {"gold": 3},
    "gems": {"gold": 2, "happiness": 1},
    "silk": {"gold": 1, "culture": 1},
    "horses": {"production": 1, "military": 1},
}

PANTHEON_BELIEFS = {
    "Ancient Pantheon":      {"faith_per_temple": 1, "description": "+1 Faith per Temple"},
    "Dance of the Dead":     {"faith_per_city": 1, "description": "+1 Faith per city"},
    "God of the Sea":        {"trade_bonus": 0.1, "description": "+10% gold from trade routes"},
    "Hunters and Gatherers": {"food_bonus": 0.1, "description": "+10% food in cities"},
    "Mother Goddess":        {"happiness_bonus": 1, "description": "+1 Happiness per city"},
    "Pastoralism":           {"production_bonus": 0.1, "description": "+10% production"},
    "Zealousness":           {"missionary_strength": 2, "description": "Missionaries have +2 strength"},
}


@dataclass
class GameState:
    turn: int = 1
    phase: str = "Player"
    game_over: bool = False
    victory: Optional[str] = None
    winner: Optional[str] = None
    victory_type: Optional[str] = None
    turn_events: List[str] = None
    current_player: str = "Player"
    pending_ck_event: Any = None

    def __post_init__(self):
        if self.turn_events is None:
            self.turn_events = []


class CKEvent:
    """Structured CK-style event with player choices that have gameplay effects."""

    def __init__(self, name: str, description: str, choices: List[Dict]):
        self.name = name
        self.description = description
        self.choices = choices

    def _set_game(self, game: Any) -> None:
        """Set the game reference for effect evaluation."""
        self._game = game

    def evaluate_choice(self, choice: Dict) -> str:
        """Apply the effects of the chosen option. Returns a feedback message."""
        effects = choice.get("effects", {})
        for effect_type, value in effects.items():
            self._apply_effect(effect_type, value)
        return f"📜 [{self.name}] Chose: {choice.get('name', '')}"
    def _apply_effect(self, effect_type: str, value: Union[int, float]) -> None:
        ruler = self._get_ruler()
        if ruler is None:
            return
        if effect_type == "gold":
            ruler.gold_reserve += value
        elif effect_type == "prestige":
            ruler.prestige = getattr(ruler, "prestige", 0) + value
        elif effect_type == "morale":
            ruler.morale = min(100, getattr(ruler, "morale", 100) + value)
        elif effect_type in ("martial", "stewardship", "intrigue", "diplomacy"):
            ruler.base_stats[effect_type] = ruler.base_stats.get(effect_type, 0) + value

    def _get_ruler(self):
        game = self._game if hasattr(self, "_game") else None
        if game:
            return game.rulers.get(game.player_civ.name)
        return None


WORLD_WONDERS: Dict[str, Dict[str, Union[str, int]]] = {
    "Pyramids of Giza":       {"cost": 300, "production_bonus": 3},
    "Great Library":          {"cost": 300, "science_bonus": 5},
    "Colosseum":              {"cost": 300, "culture_bonus": 3},
    "Stonehenge":             {"cost": 300, "faith_bonus": 3},
    "Hanging Gardens":        {"cost": 300, "gold": 3, "happiness": 2},
    "Great Wall":             {"cost": 300, "military": 3},
}

GOVERNMENT_TYPES: Dict[str, Dict[str, int]] = {
    "Despotism":  {"production": 1, "gold": -1},
    "Monarchy":   {"gold": 1, "military": 1},
    "Republic":   {"science": 2, "gold": 1},
    "Democracy":  {"gold": 2, "happiness": 2, "military": -1},
}


class Game:
    """Main game class that orchestrates all systems"""

    def __init__(self, player_civ: Civilization, ai_civs: Optional[List[Civilization]] = None, map_width: int = 16, map_height: int = 16):
        self.wonders_built: Dict[str, str] = {}  # wonder_name -> civ_name
        if not ai_civs:
            ai_civs = ["Rome", "Greece"]
        
        # Game state
        self.state = GameState()
        
        # Map
        self.map = HexMap(map_width, map_height)
        self.map.generate()

        # Fog of war
        self._fog = ExponentialFogOfWar()
        self._fog.set_tiles(self.map.tiles)

        # Resources on tiles
        self.tile_resources: Dict[Tuple[int, int], str] = {}
        resource_names = list(RESOURCE_TYPES.keys())
        for pos in self.map.tiles:
            if random.random() < 0.2:
                self.tile_resources[pos] = random.choice(resource_names)

        # Player civilization
        self.player_civ = player_civ
        self.civilizations: Dict[str, Civilization] = {player_civ.name: self.player_civ}
        if ai_civs:
            for civ in ai_civs:
                if isinstance(civ, str):
                    civ = CIVILIZATIONS[civ]
                self.civilizations[civ.name] = civ
        
        # Systems
        self.cities: Dict[str, City] = {}
        self.units: Dict[str, Unit] = {}
        self.characters: List[Character] = []
        self.dynasty: Optional[Dynasty] = None
        
        # Per-player state
        self.players: Dict[str, Civilization] = {}
        self.gold: Dict[str, int] = {}
        self.faith_points: Dict[str, int] = {}
        self.pantheons: Dict[str, str] = {}  # civ_name -> pantheon_name
        self.research: Dict[str, TechManager] = {}
        
        # Ruler tracking: civ_name -> Character
        self.rulers: Dict[str, Character] = {}
        # Succession law per civ
        self.succession_laws: Dict[str, str] = {}
        
        # Happiness: civ_name -> happiness value
        self.happiness: Dict[str, int] = {}
        
        # AI players
        self.ai_players: Dict[str, AIPlayer] = {}
        
        # Shared managers (created after cities/units exist)
        self.diplomacy_manager = DiplomacyManager()
        self.religion_manager = ReligionManager()
        self.tech_manager = TechManager()
        self.eureka_tracker = EurekaTracker()
        self.event_manager = EventManager()
        self.plot_manager = PlotManager()
        self.dynasty_manager = DynastyManager()
        self.city_manager = CityManager([])
        self.military_manager = MilitaryManager([])
        self.court: Optional[Court] = None
        self.victory_tracker = VictoryConditionTracker()
        self.improvement_manager = ImprovementManager()
        self.great_people_manager = GreatPeopleManager()
        self.era_system = EraSystem()

        # Era progression: civ_name -> era string
        self.current_era: Dict[str, str] = {}
        self.ERA_ORDER = ["Ancient", "Classical", "Medieval", "Renaissance", "Industrial", "Modern"]
        for civ in self.civilizations:
            self.current_era[civ] = "Ancient"

        # Spy network: {(source_civ, target_civ): level} where level 0-3
        self.spy_network: Dict[Tuple[str, str], int] = {}
        self.trade_routes = []  # list of (city1_name, city2_name, gold_per_turn)
        self.great_people_points = {}  # {civ_name: {"scientist": float, "artist": float, "general": float, "engineer": float}}
        self.golden_ages = {}  # {civ_name: turns_remaining}

        # Economy sub-systems
        self.tax_system = TaxSystem()
        self.happiness_system = HappinessSystem()
        self.stability_system = StabilitySystem()
        self.market = MarketSimulation()
        self.gold_management = GoldManagement()
        self.external_trade = ExternalTradeRoutes()
        self.faction_manager = FactionManager(self.player_civ.name)
        self.war_weariness: Dict[str, int] = {}  # civ_name -> weariness level 0-100
        self.governments: Dict[str, str] = {}  # civ_name -> government type (default: Despotism)
        self.anarchy_turns: Dict[str, int] = {}  # civ_name -> remaining anarchy turns

        # Cultural borders: (x, y) -> civ_name
        self.culture_borders: Dict[Tuple[int, int], str] = {}

        # City-states
        self.city_states: List[Dict] = [
            {"name": "Sparta", "type": "Militaristic", "influence": {}, "relationship": {}},
            {"name": "Athens", "type": "Cultural", "influence": {}, "relationship": {}},
            {"name": "Tyre", "type": "Maritime", "influence": {}, "relationship": {}},
        ]

        # End game statistics
        self.stats = {"cities_founded": 0, "units_trained": 0, "wars_won": 0, "techs_researched": 0, "battles_won": 0, "turns_played": 0}

        # Initialize game
        self._initialize_game()
        
        # Set up AI players with starting cities and units
        self._setup_ai_players()
        
        # Update managers with actual data
        self.city_manager.cities = list(self.cities.values())
        self.military_manager.units = list(self.units.values())
    
    @property
    def fog(self):
        """Expose fog of war."""
        return self._fog

    def build_wonder(self, civ_name: str, wonder_name: str) -> str:
        """Attempt to build a world wonder for a civilization.

        Returns a status message. Wonders can only be built once globally.
        """
        if wonder_name not in WORLD_WONDERS:
            return f"Unknown wonder: {wonder_name}"
        if wonder_name in self.wonders_built:
            owner = self.wonders_built[wonder_name]
            return f"{wonder_name} already built by {owner}"
        if civ_name not in self.civilizations:
            return f"Unknown civilization: {civ_name}"

        civ = self.civilizations[civ_name]
        wonder = WORLD_WONDERS[wonder_name]
        cost = wonder["cost"]

        if civ.gold_reserve < cost:
            return f"{civ_name} needs {cost} gold to build {wonder_name} (has {civ.gold_reserve})"

        civ.gold_reserve -= cost
        self.wonders_built[wonder_name] = civ_name

        # Apply bonuses
        bonus_parts = []
        if "production_bonus" in wonder:
            civ.production_bonus += wonder["production_bonus"]
            bonus_parts.append(f"+{wonder['production_bonus']} production")
        if "science_bonus" in wonder:
            civ.science_bonus += wonder["science_bonus"]
            bonus_parts.append(f"+{wonder['science_bonus']} science")
        if "culture_bonus" in wonder:
            civ.culture_bonus += wonder["culture_bonus"]
            bonus_parts.append(f"+{wonder['culture_bonus']} culture")
        if "faith_bonus" in wonder:
            civ.faith_bonus += wonder["faith_bonus"]
            bonus_parts.append(f"+{wonder['faith_bonus']} faith")

        return f"{civ_name} built {wonder_name}! Bonuses: {', '.join(bonus_parts)}"

    def _find_safe_tile(self, min_dist: int = 5) -> Optional[Tuple[int, int]]:
        """Find a tile at least min_dist hexes away from all existing cities."""
        city_positions = [c.position for c in self.cities.values()]
        candidates = [
            (t.x, t.y)
            for t in self.map.tiles.values()
            if t.terrain not in (TerrainType.OCEAN, TerrainType.WATER_COAST)
            and all(self.map.get_distance(t.x, t.y, cx, cy) >= min_dist for cx, cy in city_positions)
        ]
        return random.choice(candidates) if candidates else None

    def _setup_ai_players(self):
        """Give each AI civ a starting city and a warrior unit."""
        for civ_name in self.ai_players:
            tile = self._find_safe_tile(min_dist=5)
            if not tile:
                continue
            civ = self.civilizations[civ_name]
            is_coastal = self.map.tiles[tile].terrain in (TerrainType.WATER_COAST, TerrainType.OCEAN)
            climate = get_climate_for_row(tile[1], self.map.height)
            city = City(
                name=f"{civ_name} City",
                owner=civ_name,
                position=tile,
                population=3,
                gold=100,
                climate_zone=climate,
                is_coastal=is_coastal,
            )
            self.cities[city.name] = city
            self.map.add_city(city)
            self.gold[civ_name] = 100
            self.faith_points[civ_name] = 0
            self.research[civ_name] = TechManager()
            for tn in civ.starting_tech:
                if tn in TECHNOLOGIES:
                    self.research[civ_name].researched[tn] = TECHNOLOGIES[tn]
            ai_neighbors = self.map.get_neighbors(tile[0], tile[1])
            ai_land_neighbors = [n for n in ai_neighbors if n.terrain not in (TerrainType.WATER_COAST, TerrainType.OCEAN)]
            ai_warrior_pos = (ai_land_neighbors[0].x, ai_land_neighbors[0].y) if ai_land_neighbors else tile
            warrior = Unit(
                unit_type="Militia",
                owner=civ_name,
                position=ai_warrior_pos,
                moves_left=1,
            )
            warrior.name = f"{civ_name} Militia"
            self.units[warrior.name] = warrior
            self.map.add_unit(warrior)

    def change_government(self, civ_name: str, gov_type: str) -> str:
        """Change government type for a civilization. Triggers 1 turn of anarchy.

        Returns a status message.
        """
        if gov_type not in GOVERNMENT_TYPES:
            return f"Unknown government type: {gov_type}"
        if civ_name not in self.civilizations:
            return f"Unknown civilization: {civ_name}"
        if self.anarchy_turns.get(civ_name, 0) > 0:
            return f"{civ_name} is currently in anarchy ({self.anarchy_turns[civ_name]} turns remaining)"

        old_gov = self.governments.get(civ_name, "Despotism")
        if old_gov == gov_type:
            return f"{civ_name} already has {gov_type}"

        self.governments[civ_name] = gov_type
        self.anarchy_turns[civ_name] = 1
        return f"{civ_name} transitions from {old_gov} to {gov_type}. 1 turn of anarchy."

    def _apply_government_bonuses(self, civ_name: str, yields: Dict[str, float]) -> None:
        """Apply a civ's government yield bonuses to a city's yield dict in place.
        During anarchy, production/gold/science are halved and no bonus applies."""
        if self.anarchy_turns.get(civ_name, 0) > 0:
            for key in ("production", "gold", "science"):
                if key in yields:
                    yields[key] = yields.get(key, 0) * 0.5
            return
        bonuses = GOVERNMENT_TYPES.get(self.governments.get(civ_name, ""))
        if not bonuses:
            return
        for key, delta in bonuses.items():
            if key in yields:
                yields[key] = yields.get(key, 0) + delta

    def _initialize_game(self):
        """Set up initial game state"""
        # Create player starting city
        start_tile = self.map.get_starting_tile()
        start_tile_obj = self.map.tiles[start_tile]
        is_coastal = start_tile_obj.terrain in (TerrainType.WATER_COAST, TerrainType.OCEAN)
        climate = get_climate_for_row(start_tile[1], self.map.height)
        starting_city = City(
            name=f"{self.player_civ.name} City",
            owner=self.player_civ.name,
            position=start_tile,
            population=5,
            gold=100,
            climate_zone=climate,
            is_coastal=is_coastal
        )
        self.cities[starting_city.name] = starting_city
        self.map.add_city(starting_city)
        
        # Create starting units on adjacent land tiles
        neighbors = self.map.get_neighbors(start_tile[0], start_tile[1])
        land_neighbors = [n for n in neighbors if n.terrain not in (TerrainType.WATER_COAST, TerrainType.OCEAN)]
        settler_pos = (land_neighbors[0].x, land_neighbors[0].y) if land_neighbors else start_tile
        warrior_pos = (land_neighbors[1].x, land_neighbors[1].y) if len(land_neighbors) > 1 else settler_pos
        settler = Unit(
            unit_type="Settler",
            owner=self.player_civ.name,
            position=settler_pos,
            moves_left=2
        )
        warrior = Unit(
            unit_type="Militia",
            owner=self.player_civ.name,
            position=warrior_pos,
            moves_left=1
        )
        self.units[settler.name] = settler
        self.units[warrior.name] = warrior
        self.map.add_unit(settler)
        self.map.add_unit(warrior)
        
        # Reveal fog around starting city and units
        sources = []
        for city in self.cities.values():
            pos = getattr(city, "position", (0, 0))
            sources.append((pos[0], pos[1], 3))
        for unit in self.units.values():
            pos = getattr(unit, "position", (0, 0))
            sources.append((pos[0], pos[1], 2))
        self._fog.update_visibility(sources)
        
        # Create starting character (ruler)
        root_char = Character(
            name=f"{self.player_civ.name} Founder",
            stats={"diplomacy": 10, "martial": 10, "stewardship": 10, "intrigue": 10},
            traits=["Charismatic"],
            gender="Male"
        )
        self.characters.append(root_char)
        self.dynasty = Dynasty(root_char, {root_char.id: root_char})
        self.dynasty_manager.root = root_char
        self.rulers[self.player_civ.name] = root_char
        self.succession_laws[self.player_civ.name] = 'PRIMOGENITURE'
        
        # Initialize court
        self.court = Court(root_char)
        
        # Initialize factions
        self.faction_manager.initialize_factions()
        
        # Initialize per-player data
        self.players[self.player_civ.name] = self.player_civ
        self.gold[self.player_civ.name] = 100
        self.faith_points[self.player_civ.name] = 0
        # Each player gets their own TechManager instance
        self.research[self.player_civ.name] = TechManager()
        # Player UI and engine share one TechManager
        self.tech_manager = self.research[self.player_civ.name]
        
        # Give player starting tech
        for tech_name in self.player_civ.starting_tech:
            if tech_name in TECHNOLOGIES:
                self.research[self.player_civ.name].researched[tech_name] = TECHNOLOGIES[tech_name]
        
        # Create AI players for each AI civ
        for civ_name, civ in self.civilizations.items():
            if civ_name != self.player_civ.name:
                self.ai_players[civ_name] = AIPlayer(civ_name, "medium")
        
        # Every civ gets a ruler, dynasty, and court (Phase B1)
        self.realms = create_realms(self)

        # Generate initial events
        self.event_manager.generate_events()

    def process_turn(self) -> List[str]:
        """Process one turn and return messages. Does not block on input."""
        self.stats["turns_played"] += 1
        msgs = []
        self.state.turn_events = []
        
        msgs.append(f"\n{'='*60}")
        msgs.append(f"TURN {self.state.turn} - {self.state.phase} PHASE")
        msgs.append(f"{'='*60}")
        
        # --- Dynasty: age up ruler, spawn heirs ---
        civ_name = self.player_civ.name
        ruler = self.rulers.get(civ_name)
        if ruler and ruler.is_alive:
            age_event = ruler.age_up()
            if age_event:
                msgs.append(f"  👑 {ruler.name} has died ({age_event})")
                self.state.turn_events.append(f"Ruler {ruler.name} died: {age_event}")
                succession_events = self._handle_succession(civ_name, msgs)
                msgs.extend(succession_events)
            elif self.dynasty and self.state.turn % 10 == 0:
                living_children = [c for c in self.dynasty.get_all_members() if c.id != ruler.id and c.is_alive]
                if not living_children:
                    potential_spouse = None
                    for char in self.characters:
                        if char.id != ruler.id and char.is_alive and char.gender != ruler.gender:
                            potential_spouse = char
                            break
                    if not potential_spouse:
                        potential_spouse = Character(
                            name=f"{self.player_civ.name} Consort",
                            age=random.randint(18, 30),
                            gender="Female" if ruler.gender == "Male" else "Male",
                            stats={"diplomacy": 8, "martial": 8, "stewardship": 8, "intrigue": 8},
                            traits=[]
                        )
                        self.characters.append(potential_spouse)
                    child_name = f"{self.player_civ.name} Heir {len([c for c in self.dynasty.get_all_members() if 'Heir' in c.name]) + 1}"
                    child = generate_child(child_name, ruler, potential_spouse)
                    self.dynasty.add_member(child, ruler.id)
                    self.dynasty_manager.add_member(child)
                    ruler.children_ids.append(child.id)
                    msgs.append(f"  👶 {ruler.name} has a new child: {child.name}")
                    self.state.turn_events.append(f"New heir born: {child.name}")

        # --- Succession check for player ---
        civ_name = self.player_civ.name
        ruler = self.rulers.get(civ_name)
        if ruler and not ruler.is_alive:
            succession_events = self._handle_succession(civ_name, msgs)
            msgs.extend(succession_events)
        
        # Simulate NPC turns
        for civ_name, civ in self.civilizations.items():
            if civ_name == self.player_civ.name:
                continue
            msgs.append(f"  --- {civ_name}'s turn ---")
            ai_msgs = self._process_ai_turn(civ_name, civ)
            msgs.extend(ai_msgs)
            
            self.state.turn_events.extend(ai_msgs)
        
        # Process golden ages
        self.process_golden_ages()

        # Process war weariness
        self.process_war_weariness(msgs)
        
        # Calculate happiness for all civilizations
        for civ_name in self.civilizations:
            self._calculate_happiness(civ_name, msgs)

        # Pantheon auto-founding: when faith >= 25 and no pantheon yet
        for civ_name in self.civilizations:
            if civ_name not in self.pantheons and self.faith_points.get(civ_name, 0) >= 25:
                available = set(PANTHEON_BELIEFS.keys()) - set(self.pantheons.values())
                if available:
                    chosen = random.choice(list(available))
                    self.pantheons[civ_name] = chosen
                    msgs.append(f"  🏛️ {civ_name} has founded the {chosen} pantheon! ({PANTHEON_BELIEFS[chosen]['description']})")
                    self.state.turn_events.append(f"{civ_name} founded the {chosen} pantheon")

        # Process events
        event = self.event_manager.generate_event(self, self.player_civ.name)
        if event:
            event_name, event_desc = event
            msgs.append(f"\nEvent: {event_name}")
            msgs.append(f"  {event_desc}")
            self.state.turn_events.append(f"⚡ {event_name}: {event_desc}")
        
        # Check era advancement for all civilizations
        self.check_era_advancement(msgs)

        # Check eureka conditions
        civ_name = self.player_civ.name
        eureka_ctx = {
            "tech_manager": self.research.get(civ_name),
            "quarry_built": any(
                "Quarry" in getattr(city, "buildings", [])
                for city in self.cities.values()
                if city.owner == civ_name
            ),
            "coastal_city_founded": any(
                city.is_coastal for city in self.cities.values()
                if city.owner == civ_name
            ),
            "ranged_kill": getattr(self, "_ranged_kill_this_turn", False),
            "met_civilization": any(
                hasattr(self.diplomacy_manager, "_met_civs")
                and civ_name in self.diplomacy_manager._met_civs
                for _ in ()
            ) or hasattr(self.diplomacy_manager, 'alliances')
            or hasattr(self.diplomacy_manager, 'relations'),
            "enemy_kills": getattr(self, "_enemy_kills_this_turn", 0),
            "barracks_built": any(
                "Barracks" in getattr(city, "buildings", [])
                for city in self.cities.values()
                if city.owner == civ_name
            ),
            "trade_route_established": bool(
                getattr(self.external_trade, 'routes', None)
            ),
            "library_built": any(
                "Library" in getattr(city, "buildings", [])
                for city in self.cities.values()
                if city.owner == civ_name
            ),
        }
        for tech_name in EUREKA_CONDITIONS:
            self.eureka_tracker.check_eureka(tech_name, eureka_ctx)
        
        # Process economy systems
        civ_name = self.player_civ.name

        # Government: tick down anarchy for every civ, once per turn
        for _gov_civ in list(self.anarchy_turns.keys()):
            if self.anarchy_turns[_gov_civ] > 0:
                self.anarchy_turns[_gov_civ] -= 1
        
        # --- Gold maintenance for player units ---
        gold_maintenance_total = 0
        for unit in self.units.values():
            if unit.owner == civ_name and unit.is_alive:
                utype = UNIT_TYPES.get(unit.unit_type)
                if utype and utype.gold_maintenance:
                    gold_maintenance_total += utype.gold_maintenance
        if gold_maintenance_total > 0:
            self.gold[civ_name] -= gold_maintenance_total
            msgs.append(f"\n  Gold Maintenance: -{gold_maintenance_total}")
        
        # 1. Tax Income
        ruler = self.rulers.get(civ_name)
        tax_income = self.tax_system.process_tax_income(self.cities, ruler)
        self.gold[civ_name] += tax_income
        msgs.append(f"  Tax Income: +{tax_income} gold")
        
        # 2. Happiness & Stability
        self.happiness_system.update_city_count(len(self.cities))
        self.stability_system.calculate_unrest()
        self.stability_system.calculate_revolt_risk()
        msgs.append(f"  Happiness: {self.happiness_system.current_happiness}%")
        msgs.append(f"  Stability: {self.stability_system.stability}%")
        
        # 3. Gold Expenses
        expense_summary = self.gold_management.process_monthly_expenses(self.gold[civ_name])
        msgs.append(f"  Gold Surplus: {'+' if expense_summary['surplus_deficit'] >= 0 else ''}{expense_summary['surplus_deficit']}")
        
        # 4. Market Simulation
        self.market.update_all_prices()
        msgs.append(f"  Market: Prices updated")
        
        # 5. External Trade (legacy + new visible routes)
        if self.external_trade.routes:
            trade_yields = self.external_trade.process_all_routes()
            for target_civ, yields in trade_yields.items():
                for cargo, amount in yields.items():
                    msgs.append(f"  Trade with {target_civ}: +{amount:.1f} {cargo}")
        
        # New visible trade routes via Trader units
        route_yields = self.external_trade.process_routes()
        active_routes = self.external_trade.get_active_routes(civ_name)
        if active_routes:
            msgs.append(f"\n  🚢 {len(active_routes)} active trade route(s)")
            for route in active_routes:
                dest_civ = route.destination_city.owner
                msgs.append(f"    {route.origin_city.name} → {route.destination_city.name} ({route.turns_remaining} turns left)")
                if route.gold_per_turn > 0:
                    self.gold[civ_name] = self.gold.get(civ_name, 0) + int(route.gold_per_turn)
                    msgs.append(f"      +{route.gold_per_turn:.1f} gold/turn")
                if route.food_per_turn > 0:
                    # Add food to the origin city
                    if route.origin_city_name in self.cities:
                        self.cities[route.origin_city_name].food += route.food_per_turn
                    msgs.append(f"      +{route.food_per_turn:.1f} food/turn")
        
        if route_yields:
            for owner, yields in route_yields.items():
                if owner == civ_name:
                    for cargo, amount in yields.items():
                        if cargo == "gold":
                            self.gold[civ_name] = self.gold.get(civ_name, 0) + int(amount)
                        elif cargo == "food" and civ_name in self.cities:
                            self.cities[civ_name].food += amount
        
        # 6. Faction Effects
        faction_effects = self.faction_manager.get_faction_effects()
        if faction_effects['stability'] != 0:
            msgs.append(f"  Faction Stability Effect: {faction_effects['stability']:+.1f}")
        if self.faction_manager.conflict_level > 50:
            msgs.append(f"  ⚠️ High faction conflict level: {self.faction_manager.conflict_level:.0f}%")
        
        # 7. City Production
        for city in self.cities.values():
            if (owner := city.owner) is not None:
                # Calculate yields
                yields = city.calculate_yields()
                self._apply_government_bonuses(owner, yields)
                civ_obj = self.civilizations.get(owner)
                if civ_obj is not None:
                    civ_obj.culture += yields.get('culture', 0)
                # Building faith (Temples, Shrines, ...) accrues to the owning civ
                self.faith_points[owner] = self.faith_points.get(owner, 0) + yields.get('faith', 0)

                # Science advances the owning civ's research
                owner_mgr = self.research.get(city.owner)
                if owner_mgr is not None:
                    if owner_mgr.current_research is None:
                        available = owner_mgr.get_available_technologies(city.owner)
                        if available:
                            cheapest = min(available, key=lambda t: TECHNOLOGIES[t].cost)
                            owner_mgr.research(cheapest, city.owner)
                            self.state.turn_events.append(
                                f"🧪 {city.owner} began researching {cheapest}")
                    completed = owner_mgr.add_research_progress(city.owner, yields.get('science', 0))
                    if completed:
                        self.state.turn_events.append(
                            f"🔬 {city.owner} completed research: {completed}")
                
                # Population growth
                old_pop = city.population
                city.grow()
                if city.population > old_pop:
                    self.state.turn_events.append(f"{city.name} has grown to population {city.population}!")
                
                # Process production for each city
                if city.production_queue:
                    item = city.production_queue[0]
                    cost = city.get_production_cost(item)
                    if cost is not None:
                        completed_item = city.process_production(
                            yields.get('food', 0),
                            yields.get('gold', 0),
                            yields.get('science', 0),
                            yields.get('production', 0)
                        )
                        if completed_item:
                            # Handle tuple return (wonder) or string (unit/building)
                            is_wonder = False
                            if isinstance(completed_item, tuple):
                                completed_item, is_wonder = completed_item

                            if is_wonder:
                                from game_data import WONDERS
                                city.add_building(completed_item)
                                msgs.append(f"  🏛️ City '{city.name}' completed: {completed_item}")
                                self.era_system.record_moment('first_wonder')
                            elif completed_item in UNIT_TYPES:
                                # Create new unit
                                new_unit = Unit(
                                    unit_type=completed_item,
                                    owner=owner,
                                    position=city.position,
                                    moves_left=UNIT_TYPES[completed_item].movement
                                )
                                new_unit.name = f"{owner} {completed_item} {len([u for u in self.units.values() if u.owner == owner and u.unit_type == completed_item])}"
                                self.units[new_unit.name] = new_unit
                                self.map.add_unit(new_unit)
                                self.stats["units_trained"] += 1
                                msgs.append(f"  🏭 City '{city.name}' completed: {completed_item}")
                            elif completed_item in BUILDINGS:
                                # Add building to city
                                city.add_building(BUILDINGS[completed_item])
                                msgs.append(f"  🏗️ City '{city.name}' completed: {completed_item} built")
                        
                        msgs.append(f"  🏭 '{city.name}' producing: {item} ({city.production}/{cost})")
        
        # 8. Tile Improvements (Worker units)
        worker_positions = {
            (unit.position[0], unit.position[1])
            for unit in self.units.values()
            if unit.owner == civ_name and unit.is_alive
            and UNIT_TYPES.get(unit.unit_type).category == UnitCategory.WORKER
        }
        if worker_positions:
            improvement_msgs = self.improvement_manager.process_turn(
                worker_positions, self.map.tiles
            )
            msgs.extend(improvement_msgs)
        
        # 9. Great People
        gp_msgs = self.great_people_manager.process_turn(self)
        msgs.extend(gp_msgs)
        
        # Era moment checks
        civ_name = self.player_civ.name
        # first_tech
        if civ_name in self.research and len(self.research[civ_name].researched) > 0:
            self.era_system.record_moment('first_tech')
        # met_all_civs
        if civ_name in self.diplomacy_manager.relations and len(self.diplomacy_manager.relations) >= len(self.civilizations) - 1:
            self.era_system.record_moment('met_all_civs')
        # won_battle - check if any player units got kills this turn
        if any(u.kills > 0 for u in self.units.values() if u.owner == civ_name and u.is_alive):
            self.era_system.record_moment('won_battle')
        
        # Random faction events
        if random.random() < 0.15:  # 15% chance of faction event
            faction_event = FactionEventGenerator.generate_faction_event(self.faction_manager)
            if faction_event:
                msgs.append(f"  {faction_event}")
                self.state.turn_events.append(faction_event)
        
        # --- Clean up dead units ---
        dead_units = [name for name, unit in self.units.items() if not unit.is_alive]
        for name in dead_units:
            self.military_manager.remove_unit(self.units[name])
            del self.units[name]
        if dead_units:
            msgs.append(f"\n  💀 {len(dead_units)} dead unit(s) removed from game")

        # --- Expand cultural borders ---
        self.expand_borders(msgs)

        # --- Living world: every character acts (Phase B2) ---
        for _msg in tick_realms(self):
            msgs.append(f"  {_msg}")
            self.state.turn_events.append(_msg)

        # --- Rivals, plots, factions (Phase B3) ---
        for _rmsg in tick_relationships(self):
            msgs.append(f"  {_rmsg}")
            self.state.turn_events.append(_rmsg)

        # --- Cross-civ marriages (Phase B4) ---
        for _mmsg in tick_marriages(self):
            msgs.append(f"  {_mmsg}")
            self.state.turn_events.append(_mmsg)

        # --- CK-style character events ---
        ruler = self.rulers.get(self.player_civ.name)
        if ruler and random.random() < 0.3:
            event = self._generate_ck_event(ruler)
            if event:
                self.state.pending_ck_event = event
                self.state.turn_events.append(f"⚔️  {event.name}: {event.description}")

        # Religion spread: cities with temples/shrines spread to adjacent enemy cities
        religion_spread_msgs = self._process_religion_spread(msgs)
        msgs.extend(religion_spread_msgs)

        # Sync prestige onto civilizations for victory checks
        for cname, civ_obj in self.civilizations.items():
            p = 0
            r = self.rulers.get(cname)
            if r is not None:
                p += getattr(r, 'prestige', 0)
            if cname == self.player_civ.name and self.dynasty is not None:
                p += self.dynasty.calculate_dynastic_prestige()
            civ_obj.prestige = p

        # Check victory conditions
        victory = self._check_victory()
        if victory:
            self.state.game_over = True
            self.state.victory = f"{victory['winner']} wins by {victory['type']}"
            self.state.winner = victory['winner']
            self.state.victory_type = victory['type']
            self.victory_tracker.record_victory(victory['winner'], self.state.victory, self.state.turn)
            self.state.turn_events.append(f"GAME OVER - {victory['winner']} wins by {victory['type']}")
            return self.state.turn_events

        # Era transition check
        new_era = self.era_system.check_era_transition()
        if new_era != self.era_system.current_era:
            old_era = self.era_system.current_era
            self.era_system.current_era = new_era
            self.state.turn_events.append(f"ERA CHANGE: {old_era} Age -> {new_era} Age!")

        self.process_trade_routes()
        self.process_great_people(self.state.turn_events)

        # Increment turn
        self.state.turn += 1
        self.state.phase = "Player"

        return self.state.turn_events

    def expand_borders(self, msgs: List[str] = None) -> None:
        """Expand cultural borders from each city based on culture output."""
        if msgs is None:
            msgs = []
        for civ_name, civ in self.civilizations.items():
            civ_cities = [c for c in self.cities.values() if c.owner == civ_name]
            for city in civ_cities:
                yields = city.calculate_yields()
                culture_output = yields.get("culture", 0)
                if culture_output <= 0:
                    continue
                city_pos = city.position
                # Get adjacent hex tiles
                adjacent = self.map.get_neighbors(city_pos[0], city_pos[1])
                for tile in adjacent:
                    tile_pos = (tile.x, tile.y)
                    if tile_pos in self.culture_borders:
                        continue
                    distance = abs(tile.x - city_pos[0]) + abs(tile.y - city_pos[1])
                    if distance == 0:
                        distance = 1
                    if culture_output > 10 * distance:
                        self.culture_borders[tile_pos] = civ_name
                        msgs.append(f"  🏛️ {city.name} expanded culture to ({tile.x},{tile.y})")

    def _process_religion_spread(self, msgs: List[str]) -> List[str]:
        """Cities with religious buildings spread faith to adjacent cities of other civs."""
        spread_msgs = []
        for city in self.cities.values():
            civ_name = city.owner
            # Check if city has religious buildings
            has_religious = any(b in city.buildings for b in ("Temple", "Shrine", "Cathedral", "Monastery"))
            if not has_religious:
                continue
            # Determine this civ's religion
            civ_religion = None
            for rname, rel in self.religion_manager.religions.items():
                if civ_name in rel.followers:
                    civ_religion = rname
                    break
            if not civ_religion:
                continue
            # Spread to adjacent cities
            adjacent = self.map.get_neighbors(city.position[0], city.position[1])
            for tile in adjacent:
                tile_pos = (tile.x, tile.y)
                target = next((c for c in self.cities.values() if c.position == tile_pos), None)
                if target and target.owner != civ_name:
                    if target.owner not in self.religion_manager.religions[civ_religion].followers:
                        self.religion_manager.spread_religion(civ_religion, target.owner, 5)
                        spread_msgs.append(f"  ✝️ {civ_religion} spread from {city.name} to {target.name} ({target.owner})")
                        self.state.turn_events.append(f"{civ_religion} spread to {target.name}")
        return spread_msgs

    def _generate_ck_event(self, ruler: Character) -> Optional[CKEvent]:
        """Generate a CK-style interactive event with choices."""
        events = [
            self._grand_feast_event(ruler),
            self._rival_courtier_event(ruler),
            self._marriage_proposal_event(ruler),
            self._hunt_event(ruler),
            self._court_intrigue_event(ruler),
        ]
        return random.choice(events)

    def _grand_feast_event(self, ruler: Character) -> CKEvent:
        return CKEvent(
            "Grand Feast",
            f"{ruler.name} considers hosting a grand feast to boost morale and prestige. How lavish should it be?",
            [
                {
                    "name": "Lavish Feast (-50 gold, +10 prestige)",
                    "effects": {"gold": -50, "prestige": 10},
                },
                {
                    "name": "Modest Feast (+5 morale)",
                    "effects": {"morale": 5},
                },
                {
                    "name": "Cancel the feast",
                    "effects": {},
                },
            ],
        )

    def _rival_courtier_event(self, ruler: Character) -> CKEvent:
        rival_names = ["Marcus", "Cassia", "Titus", "Livia", "Drusus", "Octavia"]
        rival = random.choice(rival_names)
        return CKEvent(
            "Rival Courtier",
            f"A rival courtier, {rival}, challenges {ruler.name}'s authority at court. How should {ruler.name} respond?",
            [
                {
                    "name": f"Imprison {rival} (-10 morale, +5 intrigue)",
                    "effects": {"morale": -10, "intrigue": 5},
                },
                {
                    "name": "Negotiate peacefully (+5 diplomacy)",
                    "effects": {"diplomacy": 5},
                },
                {
                    "name": "Ignore the provocation",
                    "effects": {},
                },
            ],
        )

    def _marriage_proposal_event(self, ruler: Character) -> CKEvent:
        suitor_names = ["Princess Helena of Egypt", "Duke Alessandro of Venice", "Lady Yuki of the Eastern Isles"]
        suitor = random.choice(suitor_names)
        return CKEvent(
            "Marriage Proposal",
            f"A noble, {suitor}, proposes marriage to strengthen alliances. How should {ruler.name} respond?",
            [
                {
                    "name": "Accept the proposal (+15 prestige, +10 diplomacy)",
                    "effects": {"prestige": 15, "diplomacy": 10},
                },
                {
                    "name": "Decline politely",
                    "effects": {},
                },
            ],
        )

    def _hunt_event(self, ruler: Character) -> CKEvent:
        return CKEvent(
            "Royal Hunt",
            f"The royal hunt begins. {ruler.name} can either join the chase or remain at court.",
            [
                {
                    "name": "Join the hunt (+3 martial)",
                    "effects": {"martial": 3},
                },
                {
                    "name": "Stay at court (+3 stewardship)",
                    "effects": {"stewardship": 3},
                },
            ],
        )

    def _court_intrigue_event(self, ruler: Character) -> CKEvent:
        return CKEvent(
            "Court Intrigue",
            f"Whispers of conspiracy reach {ruler.name}'s ears. A shadowy plot is unfolding within the court walls.",
            [
                {
                    "name": "Investigate the plot (+5 intrigue, costs a turn)",
                    "effects": {"intrigue": 5},
                },
                {
                    "name": "Ignore the whispers",
                    "effects": {},
                },
            ],
        )

    def found_city(self, settler: Unit) -> City:
        """Found a new city at the settler's position. Removes the settler unit."""
        from city import City
        from game_data import get_climate_for_row
        
        tile = settler.position
        civ_name = settler.owner
        is_coastal = self.map.tiles[tile].terrain.value in ("Coast", "Ocean")
        city_count = len([c for c in self.cities.values() if c.owner == civ_name])
        
        new_city = City(
            name=f"{civ_name} City {city_count + 1}",
            owner=civ_name, position=tile,
            population=3, gold=50,
            climate_zone=get_climate_for_row(tile[1], self.map.height),
            is_coastal=is_coastal,
        )
        self.cities[new_city.name] = new_city
        self.map.add_city(new_city)
        self.gold[civ_name] = self.gold.get(civ_name, 0) - 100
        self.stats["cities_founded"] += 1
        
        # Remove the settler unit
        if settler.name in self.units:
            del self.units[settler.name]
        
        self.state.turn_events.append(f"🏛️  {civ_name} founded {new_city.name} at ({tile[0]}, {tile[1]})")
        return new_city

    def spy_on(self, source_civ: str, target_civ: str) -> str:
        """Send spies to a target civilization. Costs 100 gold, increases spy level 0-3."""
        if source_civ not in self.civilizations:
            return f"Unknown civilization: {source_civ}"
        if target_civ not in self.civilizations:
            return f"Unknown civilization: {target_civ}"
        if source_civ == target_civ:
            return "Cannot spy on yourself."

        if self.gold.get(source_civ, 0) < 100:
            return f"{source_civ} needs 100 gold to fund a spy mission."

        key = (source_civ, target_civ)
        current_level = self.spy_network.get(key, 0)
        if current_level >= 3:
            return f"{source_civ} already has maximum spy coverage on {target_civ} (level 3)."

        self.gold[source_civ] -= 100
        new_level = current_level + 1
        self.spy_network[key] = new_level

        level_names = {1: "Basic", 2: "Enhanced", 3: "Complete"}
        msg = f"🕵️  {source_civ} sends spies to {target_civ} ({level_names[new_level]} coverage, level {new_level}/3)"
        self.state.turn_events.append(msg)
        return msg

    def create_trade_route(self, city1_name, city2_name, gold_per_turn=5):
        """Create a trade route between two cities."""
        route = (city1_name, city2_name, gold_per_turn)
        if route not in self.trade_routes:
            self.trade_routes.append(route)
            self.state.turn_events.append(f"Trade route established: {city1_name} <-> {city2_name} (+{gold_per_turn} gold/turn)")
            return True
        return False

    def process_trade_routes(self):
        """Process trade income from all routes. Call from process_turn."""
        for city1, city2, gold in self.trade_routes:
            owner1 = None
            owner2 = None
            for name, city in self.cities.items():
                if name == city1: owner1 = getattr(city, "owner", None)
                if name == city2: owner2 = getattr(city, "owner", None)
            if owner1: self.gold[owner1] = self.gold.get(owner1, 0) + gold
            if owner2: self.gold[owner2] = self.gold.get(owner2, 0) + gold

    def process_great_people(self, msgs: List[str]):
        """Accumulate great people points per civilization based on city populations.

        Rates per city: scientist +0.5*pop, artist +0.3*pop, general +0.2*pop, engineer +0.4*pop.
        When any category reaches 100 points, spawn a Great Person event and reset that category.
        """
        for civ_name in self.civilizations:
            if civ_name not in self.great_people_points:
                self.great_people_points[civ_name] = {"scientist": 0.0, "artist": 0.0, "general": 0.0, "engineer": 0.0}

            points = self.great_people_points[civ_name]
            total_pop = 0
            for city in self.cities.values():
                if getattr(city, "owner", None) == civ_name:
                    total_pop += getattr(city, "population", 0)

            points["scientist"] += total_pop * 0.5
            points["artist"] += total_pop * 0.3
            points["general"] += total_pop * 0.2
            points["engineer"] += total_pop * 0.4

            for gp_type in ["scientist", "artist", "general", "engineer"]:
                while points[gp_type] >= 100:
                    points[gp_type] -= 100
                    msgs.append(f"  ⭐ Great {gp_type} has appeared in {civ_name}'s civilization!")
                    self.state.turn_events.append(f"Great {gp_type} spawned for {civ_name}")

    def _check_victory(self) -> Optional[Dict[str, str]]:
        """Check if any victory condition is met.

        Returns {"winner": civ_name, "type": victory_type} or None.
        """
        # Conquest: last civilization still owning any cities wins
        civs_with_cities = {c.owner for c in self.cities.values() if c.owner in self.civilizations}
        if len(self.civilizations) > 1 and len(civs_with_cities) == 1:
            return {"winner": next(iter(civs_with_cities)), "type": "Conquest"}

        # Check all civilizations
        for civ_name, civ in self.civilizations.items():
            civ_cities = [c for c in self.cities.values() if c.owner == civ_name]

            # Domination: 12+ cities
            if len(civ_cities) >= 12:
                return {"winner": civ_name, "type": "Domination"}

            # Science: reached Modern era
            if civ_name in self.research:
                try:
                    player_tech = self.research[civ_name]
                    if hasattr(player_tech, 'reached_era'):
                        if player_tech.reached_era(Era.MODERN, civ_name):
                            return {"winner": civ_name, "type": "Science"}
                except Exception:
                    pass

            # Culture: 1000+ culture points
            culture_points = getattr(civ, 'culture', 0)
            if culture_points >= 1000:
                return {"winner": civ_name, "type": "Culture"}

            # Religion: founded a religion followed by 60%+ of civs
            for rname, rel in self.religion_manager.religions.items():
                if getattr(rel, 'founder', None) == civ_name:
                    total_civs = len(self.civilizations)
                    if total_civs > 0 and len(rel.followers) >= total_civs * 0.6:
                        return {"winner": civ_name, "type": "Religion"}

            # Dynasty: 1500+ prestige
            prestige = getattr(civ, 'prestige', 0)
            if prestige >= 1500:
                return {"winner": civ_name, "type": "Dynasty"}

        return None
    def trigger_golden_age(self, civ: str, turns: int = 10):
        """Start or extend a golden age for a civilization."""
        self.golden_ages[civ] = self.golden_ages.get(civ, 0) + turns
        self.state.turn_events.append(f"✨ {civ} has entered a Golden Age for {turns} turns!")

    def process_golden_ages(self):
        """Decrement golden age timers and apply bonuses."""
        to_remove = []
        for civ_name, turns_left in self.golden_ages.items():
            if turns_left > 0:
                self.golden_ages[civ_name] = turns_left - 1
                # Golden age bonus: +10% gold and science
                if civ_name in self.gold:
                    self.gold[civ_name] += int(self.gold[civ_name] * 0.1)
                if turns_left - 1 == 0:
                    self.state.turn_events.append(f"🌅 The Golden Age of {civ_name} has ended.")
            else:
                to_remove.append(civ_name)
        for civ_name in to_remove:
            del self.golden_ages[civ_name]

    def check_era_advancement(self, msgs: List[str]) -> None:
        """Check if any civilization should advance to the next era based on techs researched."""
        for civ_name in self.civilizations:
            if civ_name not in self.current_era:
                self.current_era[civ_name] = "Ancient"
            if civ_name not in self.research:
                continue
            tech_mgr = self.research[civ_name]
            current = self.current_era[civ_name]
            if current not in self.ERA_ORDER:
                continue
            current_idx = self.ERA_ORDER.index(current)
            if current_idx >= len(self.ERA_ORDER) - 1:
                continue
            next_era = self.ERA_ORDER[current_idx + 1]
            # Count researched techs belonging to the next era
            next_era_count = 0
            for tech_name in tech_mgr.researched:
                tech_data = TECHNOLOGIES.get(tech_name)
                if tech_data and tech_data.era == Era(next_era):
                    next_era_count += 1
            if next_era_count >= 3:
                self.current_era[civ_name] = next_era
                msgs.append(f"  🏛️ {civ_name} has advanced to the {next_era} Era!")
                self.state.turn_events.append(f"{civ_name} advanced to the {next_era} Era")
                self.trigger_golden_age(civ_name)

    def process_war_weariness(self, msgs: List[str]) -> None:
        """Process war weariness for all civilizations each turn."""
        for civ_name in self.civilizations:
            # Initialize weariness if not present
            if civ_name not in self.war_weariness:
                self.war_weariness[civ_name] = 0

            # Check if civ is at war
            enemy_list = self.diplomacy_manager.wars.get(civ_name, [])
            is_at_war = len(enemy_list) > 0

            if is_at_war:
                # Increase weariness by 3 per turn while at war
                self.war_weariness[civ_name] = min(100, self.war_weariness[civ_name] + 3)
                msgs.append(f"  ⚔️ {civ_name} war weariness: {self.war_weariness[civ_name]}")
            else:
                # Decrease weariness by 10 per turn when at peace
                self.war_weariness[civ_name] = max(0, self.war_weariness[civ_name] - 10)

    def _calculate_happiness(self, civ_name: str, msgs: List[str]) -> None:
        """Calculate happiness for a civilization each turn and trigger revolts if negative."""
        civ_cities = [city for city in self.cities.values() if city.owner == civ_name]
        
        # +2 per city population
        pop_bonus = sum(city.population for city in civ_cities) * 2
        
        # +1 per luxury resource (count tiles with luxury resources adjacent to cities)
        luxury_count = 0
        for city in civ_cities:
            pos = getattr(city, "position", (0, 0))
            for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]:
                tile = self.map.tiles.get((pos[0] + dx, pos[1] + dy))
                if tile and getattr(tile, "resource", None) in ("ivory", "spices", "silk", "coffee", "sugar", "cocoa", "dyes", "gems"):
                    luxury_count += 1
        luxury_bonus = luxury_count
        
        # -1 per city over 3 cities
        num_cities = len(civ_cities)
        empire_strain = 0
        if num_cities > 3:
            empire_strain = (num_cities - 3) * -1
        
        # +3 per colosseum wonder
        wonder_bonus = 0
        if self.wonders_built.get("Colosseum") == civ_name:
            wonder_bonus = 3
        
        happiness = pop_bonus + luxury_bonus + empire_strain + wonder_bonus
        self.happiness[civ_name] = happiness
        
        if happiness < 0:
            revolt_msg = f"  ⚠️ {civ_name} is in revolt! Happiness: {happiness}"
            msgs.append(revolt_msg)
            self.state.turn_events.append(f"Revolt in {civ_name}: happiness {happiness}")

    def _process_ai_turn(self, civ_name: str, civ: Civilization) -> List[str]:
        """Process one turn for an AI civilization and return messages."""
        ai = self.ai_players.get(civ_name)
        if not ai:
            return []
        return ai.take_turn(self)

    def _handle_succession(self, civ_name: str, msgs: List[str]) -> List[str]:
        """Handle ruler death and succession for a civilization. Returns messages."""
        succession_msgs: List[str] = []
        ruler = self.rulers.get(civ_name)
        if not ruler:
            return succession_msgs

        succession_msgs.append(f"\n  👑 SUCCESSION for {civ_name}: {ruler.name} has died!")

        # Collect all living dynasty members as heirs
        heirs: List[Character] = []
        if self.dynasty:
            for member in self.dynasty.get_all_members():
                if member.is_alive:
                    heirs.append(member)
        # Also add any player characters of this civ
        for char in self.characters:
            if char.is_alive and char not in heirs:
                heirs.append(char)

        # Get player's cities for the succession resolver
        player_cities = {name: city for name, city in self.cities.items() if city.owner == civ_name}

        # Execute succession
        law = self.succession_laws.get(civ_name, 'PRIMOGENITURE')
        result = execute_succession(ruler, law, player_cities, heirs)

        # Apply results
        new_ruler = result['new_ruler']
        if new_ruler:
            self.rulers[civ_name] = new_ruler
            succession_msgs.append(f"  New ruler: {new_ruler.name}")

            # Update dynasty root
            if self.dynasty:
                self.dynasty.root = new_ruler
                self.dynasty_manager.root = new_ruler

            # Update court if exists
            if self.court:
                self.court.ruler = new_ruler

        # Lost cities become AI-controlled
        for city_name in result['lost_cities']:
            city = self.cities.get(city_name)
            if city:
                # Find a random AI civ to take the city
                ai_civs = [n for n in self.civilizations if n != civ_name]
                if ai_civs:
                    new_owner = random.choice(ai_civs)
                    city.owner = new_owner
                    succession_msgs.append(f"  💔 City '{city_name}' lost to {new_owner}!")

        # Apply stability penalty
        succession_msgs.append(f"  Stability: -25 on succession")
        self.stability_system.apply_change(-25)

        # Report events
        for event in result['events']:
            succession_msgs.append(f"  {event}")

        return succession_msgs

    @staticmethod
    def _migrate_save(data: dict) -> dict:
        """Migrate an older save dict up to the current schema version.
        Unversioned (pre-v1) saves are stamped to save_version 1. Future
        format changes add their steps here, gated on the incoming version."""
        if data.get("save_version", 0) < 1:
            data["save_version"] = 1
        return data

    def to_dict(self) -> dict:
        """Serialize game state for saving."""
        def _serialize(obj):
            if obj is None:
                return None
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            if hasattr(obj, '__dict__'):
                return {k: _serialize(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
            if isinstance(obj, dict):
                return {str(k): _serialize(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_serialize(i) for i in obj]
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if hasattr(obj, 'value'):
                return obj.value
            return str(obj)
        return {
            "version": "1.0",
            "save_version": 1,
            "turn": self.state.turn,
            "phase": self.state.phase,
            "game_over": self.state.game_over,
            "victory": self.state.victory,
            "player_civ": self.player_civ.name,
            "civilizations": {n: _serialize(c) for n, c in self.civilizations.items()},
            "cities": {n: _serialize(c) for n, c in self.cities.items()},
            "units": {n: _serialize(u) for n, u in self.units.items()},
            "gold": {k: v for k, v in self.gold.items()},
            "faith_points": {k: v for k, v in self.faith_points.items()},
            "characters": [_serialize(c) for c in self.characters],
            "dynasty": _serialize(self.dynasty),
            "court": _serialize(self.court),
            "map_data": {
                "width": self.map.width,
                "height": self.map.height,
                "tiles": {str(p): _serialize(t) for p, t in self.map.tiles.items()},
            },
        }

    @staticmethod
    def from_dict(data: dict) -> 'Game':
        """Deserialize game state from a dict."""
        data = Game._migrate_save(data)
        civ_name = data.get("player_civ", "Rome")
        civ = CIVILIZATIONS.get(civ_name, list(CIVILIZATIONS.values())[0])
        map_w = data.get("map_data", {}).get("width", 16)
        map_h = data.get("map_data", {}).get("height", 16)
        game = Game(civ, map_width=map_w, map_height=map_h)

        # Restore basic state
        game.state.turn = data.get("turn", 1)
        game.state.phase = data.get("phase", "Player")
        game.state.game_over = data.get("game_over", False)
        game.state.victory = data.get("victory", None)
        game.gold = data.get("gold", {civ_name: 0})

        # Restore civilizations (including AI civs)
        for name, civ_data in data.get("civilizations", {}).items():
            if name == civ_name:
                continue
            ai_civ = CIVILIZATIONS.get(name)
            if ai_civ:
                game.civilizations[name] = ai_civ
                ai_diff = data.get("ai_players", {}).get(name, "medium")
                game.ai_players[name] = AIPlayer(name, ai_diff)
                if name not in game.research:
                    game.research[name] = TechManager()

        # Restore cities
        for city_name, city_data in data.get("cities", {}).items():
            try:
                city = City(
                    name=city_data["name"],
                    owner=city_data["owner"],
                    position=tuple(city_data["position"]) if isinstance(city_data["position"], list) else city_data["position"],
                    population=city_data.get("population", 1),
                    gold=city_data.get("gold", 0),
                    climate_zone=city_data.get("climate_zone"),
                    is_coastal=city_data.get("is_coastal", False),
                )
                # Restore production state
                city.production = city_data.get("production", 0)
                city.current_production = city_data.get("current_production")
                city.production_queue = city_data.get("production_queue", [])
                city.happiness = city_data.get("happiness", 0)
                city.science = city_data.get("science", 0)
                # Restore buildings and districts
                for b in city_data.get("buildings", []):
                    city.add_building(b)
                for d in city_data.get("districts", []):
                    city.add_district(d)
                game.cities[city_name] = city
                if city.position in game.map.tiles:
                    game.map.add_city(city)
            except Exception:
                pass

        # Restore units
        for unit_name, unit_data in data.get("units", {}).items():
            try:
                unit = Unit(
                    unit_type=unit_data["unit_type"],
                    owner=unit_data["owner"],
                    position=tuple(unit_data["position"]) if isinstance(unit_data["position"], list) else unit_data["position"],
                    moves_left=unit_data.get("moves_left"),
                )
                # Restore unit state
                unit.name = unit_data.get("name", unit_name)
                unit.xp = unit_data.get("xp", 0)
                unit.level = unit_data.get("level", 1)
                unit.promotions = unit_data.get("promotions", [])
                unit.hp = unit_data.get("hp", 100)
                unit.max_hp = unit_data.get("max_hp", 100)
                unit.is_alive = unit_data.get("is_alive", True)
                unit.is_fortified = unit_data.get("is_fortified", False)
                unit.kills = unit_data.get("kills", 0)
                game.units[unit.name] = unit
                if unit.position in game.map.tiles:
                    game.map.add_unit(unit)
            except Exception:
                pass

        # Restore research
        for civ_r, research_data in data.get("research", {}).items():
            game.research[civ_r] = TechManager()
            for tech_name in research_data.get("researched", []):
                try:
                    game.research[civ_r].research(tech_name, civ_r)
                except Exception:
                    pass
            if research_data.get("current_research"):
                game.research[civ_r].current_research = research_data["current_research"]
                game.research[civ_r].research_progress = research_data.get("research_progress", 0)

        # Restore diplomacy
        if data.get("diplomacy"):
            dip_data = data["diplomacy"]
            if isinstance(dip_data, dict):
                game.diplomacy_manager.relations = {
                    tuple(k) if isinstance(k, list) else k: v
                    for k, v in dip_data.get("relations", {}).items()
                }
                game.diplomacy_manager.alliances = dip_data.get("alliances", {})
                game.diplomacy_manager.wars = dip_data.get("wars", {})
                game.diplomacy_manager.truces = {
                    tuple(k) if isinstance(k, list) else k: v
                    for k, v in dip_data.get("truces", {}).items()
                }
                game.diplomacy_manager.trade_agreements = {
                    tuple(k) if isinstance(k, list) else k: v
                    for k, v in dip_data.get("trade_agreements", {}).items()
                }

        # Restore religion
        if data.get("religion") and hasattr(game, 'religion_manager'):
            rel_data = data["religion"]
            if isinstance(rel_data, dict):
                for attr in ['founded_religion', 'followers', 'spread_strength', 'doctrine']:
                    if attr in rel_data:
                        setattr(game.religion_manager, attr, rel_data[attr])

        # Restore characters and dynasty
        if data.get("characters"):
            for char_data in data["characters"]:
                try:
                    char = Character(
                        name=char_data.get("name", "Unknown"),
                        stats=char_data.get("stats", {}),
                        traits=char_data.get("traits", []),
                    )
                    char.id = char_data.get("id", char.id)
                    game.characters.append(char)
                except Exception:
                    pass
            # Restore dynasty
            if data.get("dynasty") and game.characters:
                try:
                    dynasty_data = data["dynasty"]
                    founder = game.characters[0]
                    game.dynasty = Dynasty(founder, {founder.id: founder})
                    game.dynasty_manager.root = founder
                except Exception:
                    pass
            # Restore court
            if data.get("court") and game.characters:
                try:
                    game.court = Court(game.characters[0])
                except Exception:
                    pass

        # Restore map tile state (visited, explored, fog)
        if data.get("map_data", {}).get("tiles"):
            for pos_str, tile_data in data["map_data"]["tiles"].items():
                try:
                    pos = tuple(int(x) for x in pos_str.strip("()").split(","))
                    tile = game.map.tiles.get(pos)
                    if tile:
                        if "visited" in tile_data:
                            tile.visited = tile_data["visited"]
                        if "explored" in tile_data:
                            tile.explored = tile_data["explored"]
                        # Restore fog of war state
                        if hasattr(game.map.fog, 'explored'):
                            if pos_str.strip("()") in [f"({x},{y})" for x, y in game.map.fog.explored] or tile.explored:
                                game.map.fog.explored.add(pos)
                        if hasattr(game.map.fog, 'visible') and tile.visited:
                            game.map.fog.visible.add(pos)
                except Exception:
                    pass

        # Update managers with restored data
        game.city_manager.cities = list(game.cities.values())
        game.military_manager.units = list(game.units.values())

        return game

    def save_game(self, filepath):
        """Save game state to JSON file."""
        import json
        state = {
            "turn": self.state.turn,
            "player_civ": self.player_civ.name,
            "cities": {name: {"position": list(c.position), "population": c.population, "owner": c.owner} for name, c in self.cities.items()},
            "units": {name: {"position": list(u.position), "type": u.unit_type, "owner": u.owner, "hp": getattr(u, "hp", 100)} for name, u in self.units.items()},
        }
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)
    @staticmethod
    @classmethod
    def load_game(cls, filepath):
        """Load game state from JSON file. Returns partial state dict."""
        import json
        with open(filepath) as f:
            return json.load(f)

    def get_tile_yield(self, x: int, y: int) -> Dict[str, int]:
        """Return yield bonuses from the resource on tile (x, y)."""
        resource = self.tile_resources.get((x, y))
        if resource:
            return dict(RESOURCE_TYPES[resource])
        return {}

    def get_game_status(self) -> str:
        """Get current game state as a formatted string"""
        player_gold = self.gold.get(self.player_civ.name, 0)
        player_science = len(self.research[self.player_civ.name].researched) if self.player_civ.name in self.research and hasattr(self.research[self.player_civ.name], 'researched') else 0
        prestige = 0
        if self.dynasty:
            try:
                prestige = self.dynasty.calculate_dynastic_prestige()
            except Exception:
                prestige = 0
        
        # Check victory progress
        victory_progress = self.victory_tracker.get_victory_progress(self.player_civ.name)
        
        return (
            f"\n--- Game State (Turn {self.state.turn}) ---\n"
            f"Cities: {len(self.cities)} | Units: {len(self.units)} | Technologies: {player_science}\n"
            f"Gold: {player_gold} | Science: {player_science}\n"
            f"Dynasty Prestige: {prestige}\n"
            f"Victory Progress: {victory_progress}\n"
            f"Phase: {self.state.phase} | Over: {self.state.game_over}"
        )

    def gather_intel(self, spy_unit, target_city):
        """Gather intelligence on a foreign city."""
        return {
            "city": target_city.name,
            "production": [b.name for b in getattr(target_city, 'build_queue', [])],
            "garrison": len([u for u in self.military_manager.units
                           if u.owner == target_city.civ and u.position == target_city.position]),
        }

    def send_envoy(self, civ: str, city_state_name: str) -> str:
        """Send an envoy to a city-state, increasing influence and relationship."""
        city_state = None
        for cs in self.city_states:
            if cs["name"] == city_state_name:
                city_state = cs
                break

        if not city_state:
            return f"No city-state found named {city_state_name}."

        if civ not in self.civilizations:
            return f"No civilization found named {civ}."

        city_state["relationship"].setdefault(civ, 0)
        city_state["relationship"][civ] += 10
        city_state["influence"].setdefault(civ, 0)
        city_state["influence"][civ] += 1

        bonus_type = city_state["type"]
        if bonus_type == "Militaristic":
            return f"Envoy sent to {city_state_name}. {civ} gains +1 Military Power per turn."
        elif bonus_type == "Cultural":
            return f"Envoy sent to {city_state_name}. {civ} gains +1 Culture per turn."
        elif bonus_type == "Maritime":
            return f"Envoy sent to {city_state_name}. {civ} gains +1 Gold per turn."
        return f"Envoy sent to {city_state_name}."


def main():
    """Main game loop"""
    print("Welcome to CivKings!")
    print("="*60)
    
    # Create game
    player_civ_name = input("Choose civilization (default: Rome): ").strip() or "Rome"
    player_civ = CIVILIZATIONS[player_civ_name]
    game = Game(player_civ)
    
    # Main game loop
    while not game.state.game_over:
        msgs = game.process_turn()
        for msg in msgs:
            print(msg)
        
        if game.state.game_over:
            break
        
        # Ask to continue or save
        action = input("\nContinue (y/n) or save (s): ").strip().lower()
        if action in ['n', 'q', 'exit']:
            break
    
    print("Thanks for playing CivKings!")


if __name__ == "__main__":
    main()
