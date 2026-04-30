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
    COASTLINE_BONUSES, LANDMARKS, LandmarkType, ClimateZone, get_climate_for_row
)
from hex_map import HexMap, HexTile
from city import City
from military import Unit
from simulation import Character, Dynasty, generate_child, modify_opinion, DynastyManager
from court import Court, CourtPosition
from city import CityManager
from military import MilitaryManager
from economy import EconomyManager
from diplomacy import DiplomacyManager
from religion import ReligionManager
from tech import TechManager
from events import EventManager
from plots import PlotManager


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
        
        # Shared managers (created after cities/units exist)
        self.diplomacy_manager = DiplomacyManager()
        self.religion_manager = ReligionManager()
        self.tech_manager = TechManager()
        self.event_manager = EventManager()
        self.plot_manager = PlotManager()
        self.dynasty_manager = DynastyManager()
        self.city_manager = CityManager([])
        self.military_manager = MilitaryManager([])
        self.court: Optional[Court] = None
        
        # Initialize game
        self._initialize_game()
        
        # Update managers with actual data
        self.city_manager.cities = list(self.cities.values())
        self.military_manager.units = list(self.units.values())
    
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
        
        # Initialize court
        self.court = Court(root_char)
        
        # Initialize per-player data
        self.players[self.player_civ.name] = self.player_civ
        self.gold[self.player_civ.name] = 100
        # Each player gets their own TechManager instance
        self.research[self.player_civ.name] = TechManager()
        
        # Give player starting tech
        for tech_name in self.player_civ.starting_tech:
            if tech_name in TECHNOLOGIES:
                self.research[self.player_civ.name].research(tech_name, self.player_civ.name)
        
        # Generate initial events
        self.event_manager.generate_events()

    def process_turn(self) -> List[str]:
        """Process one turn and return messages. Does not block on input."""
        msgs = []
        self.state.turn_events = []
        
        msgs.append(f"\n{'='*60}")
        msgs.append(f"TURN {self.state.turn} - {self.state.phase} PHASE")
        msgs.append(f"{'='*60}")
        
        # Simulate NPC turns
        for civ_name, civ in self.civilizations.items():
            if civ_name == self.player_civ.name:
                continue
            msgs.append(f"  {civ_name} processes its turn.")
            # TODO: Implement full AI logic here
        
        # Process events
        event = self.event_manager.generate_event()
        if event:
            event_name, event_desc = (event, "") if isinstance(event, str) else event
            msgs.append(f"\nEvent: {event_name}")
            msgs.append(f"  {event_desc}")
            self.state.turn_events.append(f"{event_name}: {event_desc}")
        
        # Check victory conditions
        victory_msg = self._check_victory()
        if victory_msg:
            self.state.game_over = True
            self.state.victory = victory_msg
            msgs.append(f"\n{'='*60}")
            msgs.append(f"GAME OVER - {victory_msg}")
            msgs.append(f"{'='*60}")
            return msgs
        
        # Increment turn
        self.state.turn += 1
        self.state.phase = "Player"
        
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
        game = Game(civ, map_width=data.get("map_data", {}).get("width", 16), map_height=data.get("map_data", {}).get("height", 16))
        game.state.turn = data.get("turn", 1)
        game.state.phase = data.get("phase", "Player")
        game.state.game_over = data.get("game_over", False)
        game.state.victory = data.get("victory", None)
        game.gold = data.get("gold", {civ_name: 0})
        return game

    def save_game(self, filename: Optional[str] = None) -> str:
        """Save game to JSON file. Returns the file path."""
        import save_system
        path = save_system.save_game(self, filename)
        return f"Game saved to {path}"

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
        
        return (
            f"\n--- Game State (Turn {self.state.turn}) ---\n"
            f"Cities: {len(self.cities)} | Units: {len(self.units)} | Technologies: {player_science}\n"
            f"Gold: {player_gold} | Science: {player_science}\n"
            f"Dynasty Prestige: {prestige}\n"
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
