"""
CivKings - Main Game Class
Orchestrates the game loop, turn management, and state
"""
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from game_data import (
    TerrainType, VICTORY_CONDITIONS,
    TECHNOLOGIES, Technology, Era, TechBranch,
    TRAIT_DATABASE, CIVILIZATIONS, Civilization,
    COASTLINE_BONUSES, LANDMARKS, LandmarkType, ClimateZone, get_climate_for_row,
    UNIT_TYPES, UnitCategory, BUILDINGS
)
from hex_map import HexMap, HexTile
from city import City
from military import Unit
from simulation import Character, Dynasty, generate_child, modify_opinion, DynastyManager, execute_succession, SUCCESSION_LAWS
from court import Court, CourtPosition
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


@dataclass
class GameState:
    turn: int = 1
    phase: str = "Player"
    game_over: bool = False
    victory: Optional[str] = None
    turn_events: List[str] = None
    current_player: str = "Player"

    def __post_init__(self):
        if self.turn_events is None:
            self.turn_events = []


class Game:
    """Main game class that orchestrates all systems"""
    
    def __init__(self, player_civ: Civilization, ai_civs: Optional[List[Civilization]] = None, map_width: int = 16, map_height: int = 16):
        # Game state
        self.state = GameState()
        
        # Map
        self.map = HexMap(map_width, map_height)
        self.map.generate()
        
        # Player civilization
        self.player_civ = player_civ
        self.civilizations: Dict[str, Civilization] = {player_civ.name: self.player_civ}
        if ai_civs:
            for civ in ai_civs:
                self.civilizations[civ.name] = civ
        
        # Systems
        self.cities: Dict[str, City] = {}
        self.units: Dict[str, Unit] = {}
        self.characters: List[Character] = []
        self.dynasty: Optional[Dynasty] = None
        
        # Per-player state
        self.players: Dict[str, Civilization] = {}
        self.gold: Dict[str, int] = {}
        self.research: Dict[str, TechManager] = {}
        
        # Ruler tracking: civ_name -> Character
        self.rulers: Dict[str, Character] = {}
        # Succession law per civ
        self.succession_laws: Dict[str, str] = {}
        
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
        
        # Economy sub-systems
        self.tax_system = TaxSystem()
        self.happiness_system = HappinessSystem()
        self.stability_system = StabilitySystem()
        self.market = MarketSimulation()
        self.gold_management = GoldManagement()
        self.external_trade = ExternalTradeRoutes()
        self.faction_manager = FactionManager(self.player_civ.name)
        
        # Initialize game
        self._initialize_game()
        
        # Set up AI players with starting cities and units
        self._setup_ai_players()
        
        # Update managers with actual data
        self.city_manager.cities = list(self.cities.values())
        self.military_manager.units = list(self.units.values())
    
    @property
    def fog(self):
        """Expose fog of war from the map."""
        return self.map.fog
    
    def _find_safe_tile(self, min_dist: int = 5) -> Optional[Tuple[int, int]]:
        """Find a tile at least min_dist hexes away from all existing cities."""
        city_positions = [c.position for c in self.cities.values()]
        candidates = [
            (t.x, t.y)
            for t in self.map.tiles.values()
            if t.terrain not in (TerrainType.OCEAN,)
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
            self.research[civ_name] = TechManager()
            for tn in civ.starting_tech:
                if tn in TECHNOLOGIES:
                    self.research[civ_name].research(tn, civ_name)
            warrior = Unit(
                unit_type="Militia",
                owner=civ_name,
                position=tile,
                moves_left=1,
            )
            warrior.name = f"{civ_name} Militia"
            self.units[warrior.name] = warrior
            self.map.add_unit(warrior)

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
        
        # Create starting units
        settler = Unit(
            unit_type="Settler",
            owner=self.player_civ.name,
            position=start_tile,
            moves_left=2
        )
        warrior = Unit(
            unit_type="Militia",
            owner=self.player_civ.name,
            position=start_tile,
            moves_left=1
        )
        self.units[settler.name] = settler
        self.units[warrior.name] = warrior
        self.map.add_unit(settler)
        self.map.add_unit(warrior)
        
        # Create starting character (ruler)
        root_char = Character(
            name=f"{self.player_civ.name} Founder",
            stats={"diplomacy": 10, "martial": 10, "stewardship": 10, "intrigue": 10},
            traits=["Charismatic"]
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
        # Each player gets their own TechManager instance
        self.research[self.player_civ.name] = TechManager()
        
        # Give player starting tech
        for tech_name in self.player_civ.starting_tech:
            if tech_name in TECHNOLOGIES:
                self.research[self.player_civ.name].research(tech_name, self.player_civ.name)
        
        # Create AI players for each AI civ
        for civ_name, civ in self.civilizations.items():
            if civ_name != self.player_civ.name:
                self.ai_players[civ_name] = AIPlayer(civ_name, "medium")
        
        # Generate initial events
        self.event_manager.generate_events()

    def process_turn(self) -> List[str]:
        """Process one turn and return messages. Does not block on input."""
        msgs = []
        self.state.turn_events = []
        
        msgs.append(f"\n{'='*60}")
        msgs.append(f"TURN {self.state.turn} - {self.state.phase} PHASE")
        msgs.append(f"{'='*60}")
        
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
            msgs.extend(self._process_ai_turn(civ_name, civ))
        
        # Process events
        event = self.event_manager.generate_event()
        if event:
            event_name, event_desc = (event, "") if isinstance(event, str) else event
            msgs.append(f"\nEvent: {event_name}")
            msgs.append(f"  {event_desc}")
            self.state.turn_events.append(f"{event_name}: {event_desc}")
        
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
        tax_income = self.tax_system.process_tax_income(self.cities)
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
        
        # 5. External Trade
        if self.external_trade.routes:
            trade_yields = self.external_trade.process_all_routes()
            for target_civ, yields in trade_yields.items():
                for cargo, amount in yields.items():
                    msgs.append(f"  Trade with {target_civ}: +{amount:.1f} {cargo}")
        
        # 6. Faction Effects
        faction_effects = self.faction_manager.get_faction_effects()
        if faction_effects['stability'] != 0:
            msgs.append(f"  Faction Stability Effect: {faction_effects['stability']:+.1f}")
        if self.faction_manager.conflict_level > 50:
            msgs.append(f"  ⚠️ High faction conflict level: {self.faction_manager.conflict_level:.0f}%")
        
        # 7. City Production
        for city in self.cities.values():
            if city.owner == civ_name:
                # Calculate yields
                yields = city.calculate_yields()
                
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
                            elif completed_item in UNIT_TYPES:
                                # Create new unit
                                new_unit = Unit(
                                    unit_type=completed_item,
                                    owner=civ_name,
                                    position=city.position,
                                    moves_left=UNIT_TYPES[completed_item].movement
                                )
                                new_unit.name = f"{civ_name} {completed_item} {len([u for u in self.units.values() if u.owner == civ_name and u.unit_type == completed_item])}"
                                self.units[new_unit.name] = new_unit
                                self.map.add_unit(new_unit)
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
        
        # Random faction events
        if random.random() < 0.15:  # 15% chance of faction event
            faction_event = FactionEventGenerator.generate_faction_event(self.faction_manager)
            if faction_event:
                msgs.append(f"  {faction_event}")
                self.state.turn_events.append(faction_event)
        
        # --- Clean up dead units ---
        dead_units = [name for name, unit in self.units.items() if not unit.is_alive]
        for name in dead_units:
            self.map.remove_unit(self.units[name])
            del self.units[name]
        if dead_units:
            msgs.append(f"\n  💀 {len(dead_units)} dead unit(s) removed from game")
        
        # Check victory conditions
        victory_msg = self._check_victory()
        if victory_msg:
            self.state.game_over = True
            self.state.victory = victory_msg
            self.victory_tracker.record_victory(self.player_civ.name, victory_msg, self.state.turn)
            msgs.append(f"\n{'='*60}")
            msgs.append(f"GAME OVER - {victory_msg}")
            msgs.append(f"{'='*60}")
            return msgs
        
        # Increment turn
        self.state.turn += 1
        self.state.phase = "Player"
        
        # Reset movement points for player units
        for unit in self.units.values():
            if unit.owner == self.player_civ.name:
                utype = UNIT_TYPES.get(unit.unit_type)
                if utype:
                    if utype.category in (UnitCategory.SETTLER, UnitCategory.WORKER):
                        unit.moves_left = 2
                    elif utype.category == UnitCategory.CAVALRY:
                        unit.moves_left = 2
                    elif utype.category == UnitCategory.NAVAL:
                        unit.moves_left = 2
                    else:
                        unit.moves_left = 1
                else:
                    unit.moves_left = 1
        
        return msgs

    def _check_victory(self) -> Optional[str]:
        """Check if any victory condition is met"""
        # Domination victory
        if len(self.cities) >= 10:
            return f"{self.player_civ.name} achieves Domination Victory!"
        
        # Science victory
        if self.player_civ.name in self.research:
            try:
                player_tech = self.research[self.player_civ.name]
                if hasattr(player_tech, 'reached_era'):
                    if player_tech.reached_era(Era.MODERN, self.player_civ.name):
                        return f"{self.player_civ.name} achieves Science Victory!"
            except Exception:
                pass
        
        # Dynasty victory
        if self.dynasty:
            try:
                members = self.dynasty.get_all_members()
                living = [m for m in members if getattr(m, 'is_alive', True)]
                if len(living) >= 10:
                    return f"{self.player_civ.name} achieves Dynasty Victory!"
            except Exception:
                pass
        
        return None

    def _process_ai_turn(self, civ_name: str, civ: Civilization) -> List[str]:
        """Process one turn for an AI civilization and return messages."""
        msgs = []
        ai = self.ai_players.get(civ_name)
        if not ai:
            return msgs
        
        # Get AI state
        cities = [c for c in self.cities.values() if c.owner == civ_name]
        cities_count = len(cities)
        units = [u for u in self.units.values() if u.owner == civ_name]
        military_strength = sum(u.moves_left * 10 for u in units if u.unit_type not in ("Settler", "Worker"))
        current_tech = list(self.research[civ_name].researched_technologies) if civ_name in self.research else []
        available_gold = self.gold.get(civ_name, 0)
        
        # Get AI decision
        available_tiles = [(u.position[0], u.position[1]) for u in units if u.unit_type == "Settler" and u.moves_left > 0]
        action = ai.decide_next_action(current_tech, cities_count, military_strength, available_gold)
        
        msgs.append(f"    AI Strategy: {ai.priorities['military']*100:.0f}% military, {ai.priorities['science']*100:.0f}% science")
        
        # Apply AI decisions
        if action.get("build"):
            msgs.append(f"    Building: {action['build']}")
            # Assign to a city's production queue instead of instant spawn
            available_cities = [c for c in cities if c.owner == civ_name]
            if available_cities:
                target_city = available_cities[0]
                target_city.assign_production(action["build"], researched_techs=set(current_tech))
                msgs.append(f"    -> Assigned to {target_city.name} production queue")
        
        if action.get("expand") and action.get("target_tile"):
            tile = action["target_tile"]
            from city import City
            new_city = City(
                name=f"{civ_name} City {cities_count + 1}",
                owner=civ_name,
                position=tile,
                population=3,
                gold=50,
                climate_zone="temperate",
                is_coastal=False
            )
            self.cities[new_city.name] = new_city
            self.map.add_city(new_city)
            msgs.append(f"    Founded new city at {tile}")
        
        if action.get("attack") and action.get("diplo_target"):
            target_name = action["diplo_target"]
            enemy_units = [u for u in units if u.owner == target_name]
            if enemy_units:
                msgs.append(f"    Attacking {target_name}!")
                # Simplified combat: just report it
                target_city = next((c for c in cities if c.owner == target_name), None)
                if target_city:
                    msgs.append(f"    Targeting city: {target_city.name}")
        
        if action.get("diplo_action"):
            msgs.append(f"    Diplomacy: {action['diplo_action']} ({action.get('diplo_target', '')})")
        
        # Update research priority
        if ai.target_research is None:
            if action["type"] == "military":
                military_techs = [t for t in TECHNOLOGIES.values() 
                                if t.branch.name == "MILITARY" and t.name not in current_tech]
                if military_techs:
                    ai.target_research = military_techs[0].name
            elif action["type"] == "science":
                science_techs = [t for t in TECHNOLOGIES.values() 
                                if t.branch.name == "SCIENTIFIC" and t.name not in current_tech]
                if science_techs:
                    ai.target_research = science_techs[0].name
            else:
                civic_techs = [t for t in TECHNOLOGIES.values() 
                              if t.branch.name == "CIVIC" and t.name not in current_tech]
                if civic_techs:
                    ai.target_research = civic_techs[0].name
        
        if ai.target_research and civ_name in self.research:
            tech = TECHNOLOGIES.get(ai.target_research)
            if tech and ai.target_research not in self.research[civ_name].researched_technologies:
                cost = tech.research_cost if hasattr(tech, 'research_cost') else 100
                self.research[civ_name].research_progress[ai.target_research] = \
                    self.research[civ_name].research_progress.get(ai.target_research, 0) + cost
                msgs.append(f"    Researching: {ai.target_research}")
        
        # Process production for AI cities
        for city in cities:
            if city.production_queue:
                if city.current_production is None and city.production_queue:
                    city.current_production = city.production_queue.pop(0)
                
                item = city.current_production
                cost = city.get_production_cost(item)
                if cost is not None:
                    capacity = city.calculate_production_capacity()
                    city.production = min(city.production + capacity, city.production_capacity)
                    
                    if city.production >= cost:
                        if item in UNIT_TYPES:
                            new_unit = Unit(
                                unit_type=item,
                                owner=civ_name,
                                position=city.position,
                                moves_left=UNIT_TYPES[item].movement
                            )
                            new_unit.name = f"{civ_name} {item} {len([u for u in self.units.values() if u.owner == civ_name and u.unit_type == item])}"
                            self.units[new_unit.name] = new_unit
                            self.map.add_unit(new_unit)
                            msgs.append(f"    🏭 AI '{city.name}' completed: {item}")
                        elif item in BUILDINGS:
                            city.add_building(BUILDINGS[item])
                            msgs.append(f"    🏗️ AI '{city.name}' completed: {item} built")
                        
                        city.current_production = None
                        city.production = 0
                
                if city.production_queue and city.current_production is None:
                    city.current_production = city.production_queue.pop(0)
        
        return msgs

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
            "turn": self.state.turn,
            "phase": self.state.phase,
            "game_over": self.state.game_over,
            "victory": self.state.victory,
            "player_civ": self.player_civ.name,
            "civilizations": {n: _serialize(c) for n, c in self.civilizations.items()},
            "cities": {n: _serialize(c) for n, c in self.cities.items()},
            "units": {n: _serialize(u) for n, u in self.units.items()},
            "gold": {k: v for k, v in self.gold.items()},
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

    def save_game(self, filename: Optional[str] = None) -> str:
        """Save game to JSON file. Returns the file path."""
        import save_system
        return save_system.save_game(self, filename)

    @staticmethod
    def load_game(filepath: str) -> Optional['Game']:
        """Load game from JSON file."""
        import save_system
        data = save_system.load_game(filepath)
        if not data:
            return None
        return Game.from_dict(data)

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
