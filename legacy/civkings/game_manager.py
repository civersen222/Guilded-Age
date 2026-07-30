"""
CivKings - Main Game Class
Orchestrates the game loop, turn management, and state
"""
import random
from typing import List, Dict, Optional, Tuple
from types import SimpleNamespace
from dataclasses import dataclass, field
from game_data import (
    TerrainType, VICTORY_CONDITIONS,
    TECHNOLOGIES, Technology, Era, TechBranch,
    TRAIT_DATABASE, CIVILIZATIONS, Civilization
)
from hex_map import HexMap, HexTile
from city import City
from military import Unit
from simulation import Character, Dynasty
from tech import TechManager
from events import EventManager
from plots import PlotManager


class GameManager:
    """Main game class that orchestrates the simulation."""

    def __init__(self, civilizations: List[Civilization]):
        self.civilizations: Dict[str, Civilization] = {civ.name: civ for civ in civilizations}
        self.current_player_index: int = 0
        self.current_player: Civilization = civilizations[0]
        self.turn_count: int = 1
        self.game_over: bool = False
        self.victory: Optional[str] = None
        self.victory_reason: Optional[str] = None

        # Core systems
        self.tech_manager: TechManager = TechManager()
        self.event_manager: EventManager = EventManager()
        self.plot_manager: PlotManager = PlotManager()

        # Game state
        self.logs: List[str] = []
        self.units: List[Unit] = []
        self.cities: List[City] = []
        self.world_map: Optional[HexMap] = None

        # Character management
        self.characters: Dict[str, Character] = {}
        self.dynasty: Optional[Dynasty] = None

        # Initialize
        self._initialize_cities()
        self._initialize_characters()
        self.event_manager.generate_events()

    def _initialize_cities(self):
        """Create starting cities for each civilization."""
        for civ in self.civilizations.values():
            # Create a starting city on a favorable terrain
            starting_terrain = random.choice([TerrainType.PLAINS, TerrainType.GRASSLAND])
            city = City(
                name=f"{civ.name} Capital",
                owner=civ.name,
                position=(0, 0),
                population=10,
                gold=civ.starting_gold,
            )
            self.cities.append(city)
            civ.cities.append(city)

    def _initialize_characters(self):
        """Create starting ruler for each civilization."""
        for civ in self.civilizations.values():
            # Create ruler character
            ruler = Character(
                name=civ.name + " Ruler",
                stats=civ.starting_stats,
                traits=civ.starting_traits,
            )
            self.characters[ruler.id] = ruler
            civ.ruler = ruler

            # Create spouse
            spouse = Character(
                name=civ.name + " Spouse",
                stats={stat: random.randint(8, 12) for stat in civ.starting_stats.keys()},
                traits=random.sample(list(TRAIT_DATABASE.keys()), 2),
            )
            self.characters[spouse.id] = spouse

            # Create children
            for i in range(2):
                child = Character(
                    name=f"{civ.name} Heir {i+1}",
                    stats={stat: random.randint(5, 15) for stat in civ.starting_stats.keys()},
                    traits=random.sample(list(TRAIT_DATABASE.keys()), 1),
                )
                self.characters[child.id] = child
                civ.characters.append(child)

            # Set up dynasty
            if not self.dynasty:
                self.dynasty = Dynasty(ruler, self.characters)

    def _advance_turn(self):
        """Advance to the next turn."""
        self.turn_count += 1

        # Age all characters
        for char in self.characters.values():
            if char.is_alive:
                char.age += 1
                if char.age > 70:
                    # Death chance increases with age
                    if random.random() < (char.age - 70) * 0.02:
                        char.is_alive = False
                        self._log(f"{char.name} has died at age {char.age}")

        # Process plots
        completed_plots = self.plot_manager.process_plots()
        for plot in completed_plots:
            self._log(f"Plot '{plot.name}' succeeded!")
            # Apply plot effects
            if plot.plot_type == "assassination" and plot.target in self.characters:
                self.characters[plot.target].is_alive = False
                self._log(f"  -> {plot.target} was assassinated!")

        # Process spies
        caught_spies = self.plot_manager.process_spies()
        for spy in caught_spies:
            self._log(f"Spy '{spy.name}' was caught!")

        # Generate events
        event = self.event_manager.generate_event()
        if event:
            event_name, description = event
            self._log(f"Event: {event_name} - {description}")

        # Auto-research technologies
        self.tech_manager.auto_research(self.current_player)

        # Check victory conditions
        self._check_victory()

    def _check_victory(self):
        """Check if any civilization has achieved victory. Never crashes — uses try/except around each check."""
        for civ in self.civilizations.values():
            try:
                # Domination victory
                dom_cond = VICTORY_CONDITIONS.get("domination", {})
                dom_value = dom_cond.get("value", 0)
                dom_type = dom_cond.get("type", "")
                if dom_type == "control":
                    try:
                        threshold = int(float(dom_value) * 10)
                        if len(civ.cities) >= threshold:
                            self.victory = "Domination"
                            self.victory_reason = f"{civ.name} controls {len(civ.cities)} cities"
                            self.game_over = True
                            return
                    except (TypeError, ValueError):
                        pass
                elif dom_type == "percent":
                    try:
                        total_cities = sum(len(c.cities) for c in self.civilizations.values())
                        if total_cities > 0:
                            pct = float(dom_value)
                            if len(civ.cities) / total_cities >= pct:
                                self.victory = "Domination"
                                self.victory_reason = f"{civ.name} controls {pct*100:.0f}% of cities"
                                self.game_over = True
                                return
                    except (TypeError, ValueError, ZeroDivisionError):
                        pass

                # Science victory
                sci_cond = VICTORY_CONDITIONS.get("science", {})
                sci_value = sci_cond.get("value")
                sci_type = sci_cond.get("type", "")
                if sci_type == "era":
                    try:
                        target_era = None
                        if isinstance(sci_value, str):
                            # Convert string like "10" or era name to Era enum
                            for era in Era:
                                if str(era.value) == sci_value or era.name == sci_value:
                                    target_era = era
                                    break
                        elif isinstance(sci_value, Era):
                            target_era = sci_value
                        elif isinstance(sci_value, (int, float)):
                            # If it's a number, try to map to era by index
                            era_list = list(Era)
                            idx = int(sci_value)
                            target_era = era_list[idx] if 0 <= idx < len(era_list) else None

                        if target_era and hasattr(civ, 'current_era') and civ.current_era == target_era:
                            self.victory = "Science"
                            self.victory_reason = f"{civ.name} has reached {target_era.name} Era"
                            self.game_over = True
                            return
                    except (TypeError, ValueError, IndexError):
                        pass

                # Cultural victory
                cult_cond = VICTORY_CONDITIONS.get("culture", {})
                cult_value = cult_cond.get("value", 0)
                try:
                    if civ.culture >= float(cult_value):
                        self.victory = "Culture"
                        self.victory_reason = f"{civ.name} has reached {civ.culture} culture"
                        self.game_over = True
                        return
                except (TypeError, ValueError):
                    pass

                # Diplomatic victory
                dip_cond = VICTORY_CONDITIONS.get("diplomacy", {})
                dip_value = dip_cond.get("value", 0)
                try:
                    if civ.diplomacy >= float(dip_value):
                        self.victory = "Diplomacy"
                        self.victory_reason = f"{civ.name} has reached {civ.diplomacy} diplomacy"
                        self.game_over = True
                        return
                except (TypeError, ValueError):
                    pass

            except Exception:
                # If anything unexpected happens, skip this civ and continue
                continue

    def _log(self, message: str):
        """Add a log message."""
        self.logs.append(f"Turn {self.turn_count}: {message}")

    def _print_state(self):
        """Print current game state."""
        print(f"\n=== Turn {self.turn_count} ===")
        for name, civ in self.civilizations.items():
            print(f"  {name}: {len(getattr(civ, 'cities', []))} cities, {getattr(civ, 'gold', 0)} gold")

    def run_turn(self):
        """Run one turn for the current player."""
        if self.game_over:
            return

        print(f"\n{'='*50}")
        print(f"Turn {self.turn_count} - {self.current_player.name}'s Turn")
        print(f"{'='*50}")

        # 1. City production phase
        self._city_production_phase()

        # 2. Character actions phase
        self._character_actions_phase()

        # 3. Research phase
        self._research_phase()

        # 4. Plot/spy phase
        self._plot_phase()

        # 5. Event phase
        self._event_phase()

        # 6. Victory check
        self._check_victory()

        # Advance to next player
        self._advance_turn()

        # Print state
        self._print_state()

    def _city_production_phase(self):
        """Process city production for the current player."""
        print("\n--- City Production Phase ---")
        for city in self.current_player.cities:
            # Food growth
            if city.food >= city.population * 10:
                city.food -= city.population * 10
                city.population += 1
                self._log(f"{city.name} population grew to {city.population}")

            # Production
            production = city.calculate_production()
            city.production += production
            self._log(f"{city.name} produced {production} production")

    def _character_actions_phase(self):
        """Process character actions for the current player."""
        print("\n--- Character Actions Phase ---")
        for char in self.current_player.characters:
            if not char.is_alive:
                continue

            # Random actions based on traits
            if "Warrior" in char.traits and random.random() < 0.3:
                # Martial action
                bonus = char.get_effective_stat("martial")
                self._log(f"{char.name} conducted martial exercises (+{bonus} martial training)")

            if "Diplomat" in char.traits and random.random() < 0.3:
                # Diplomatic action
                bonus = char.get_effective_stat("diplomacy")
                self.current_player.starting_stats["diplomacy"] += bonus
                self._log(f"{char.name} engaged in diplomacy (+{bonus} diplomacy)")

            if "Industrious" in char.traits and random.random() < 0.3:
                # Economic action
                bonus = char.get_effective_stat("stewardship")
                self.current_player.gold += bonus
                self._log(f"{char.name} managed resources (+{bonus} gold)")

            if "Cunning" in char.traits and random.random() < 0.3:
                # Intrigue action
                bonus = char.get_effective_stat("intrigue")
                self.plot_manager.add_intrigue_score(self.current_player.name, bonus)
                self._log(f"{char.name} plotted intrigue (+{bonus} intrigue)")

    def _research_phase(self):
        """Process research for the current player."""
        print("\n--- Research Phase ---")
        if self.current_player.science >= 10:
            # Auto-research a technology
            available_techs = [
                tech for tech in TECHNOLOGIES.values()
                if tech.name not in self.tech_manager.unlocked_techs
                and self.tech_manager.can_research(tech)
            ]
            if available_techs:
                tech = random.choice(available_techs)
                cost = self.tech_manager.get_cost(tech)
                if self.current_player.science >= cost:
                    self.tech_manager.research(tech, self.current_player)
                    self._log(f"Researched {tech.name} for {cost} science")

    def _plot_phase(self):
        """Process plots and spies."""
        print("\n--- Plot & Spy Phase ---")
        # Process active plots
        completed_plots = self.plot_manager.process_plots()
        for plot in completed_plots:
            self._log(f"Plot '{plot.name}' succeeded!")

        # Process spies
        caught_spies = self.plot_manager.process_spies()
        for spy in caught_spies:
            self._log(f"Spy '{spy.name}' was caught!")

    def _event_phase(self):
        """Process random events."""
        print("\n--- Event Phase ---")
        event = self.event_manager.generate_event()
        if event:
            event_name, description = event
            self._log(f"Event: {event_name} - {description}")

    def get_state(self) -> Dict:
        return {
            "turn": self.turn_count,
            "civilizations": [
                {
                    "name": name,
                    "cities": [c.name for c in getattr(civ, "cities", [])],
                    "gold": getattr(civ, "starting_gold", 0),
                }
                for name, civ in self.civilizations.items()
            ],
        }
    def print_state(self):
        print(f"Turn {self.turn_count}")
        for name, civ in self.civilizations.items():
            print(f"  {name}: {len(getattr(civ, 'cities', []))} cities")
    @property
    def state(self):
        from types import SimpleNamespace
        return SimpleNamespace(turn=self.turn_count)

    def run_game(self, turns: int = 10):
        """Run the game for a specified number of turns."""
        print("\n" + "="*50)
        print("Welcome to CivKings!")
        print("="*50)

        for _ in range(turns):
            if self.game_over:
                break
            self.run_turn()

        print("\n" + "="*50)
        print("Game Summary")
        print("="*50)
        self.print_state()

        # Print final logs
        if self.logs:
            print("\nRecent Events:")
            for log in self.logs[-10:]:
                print(f"  {log}")

        return self.get_state()


def create_sample_game() -> GameManager:
    """Create a sample game with default civilizations."""
    from game_data import CIVILIZATIONS
    civs = [CIVILIZATIONS["Rome"], CIVILIZATIONS["Greece"], CIVILIZATIONS["Mesopotamia"]]
    return GameManager(civs)
if __name__ == "__main__":
    game = create_sample_game()
    game.run_game(turns=5)
