"""
CivKings - Main Game Class
Orchestrates the game loop, turn management, and state
"""
import random
from typing import List, Dict, Optional, Tuple
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
from military import Army


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
        for civ in self.civilizations:
            # Create a starting city on a favorable terrain
            starting_terrain = random.choice([TerrainType.PLAINS, TerrainType.GRASSLAND])
            city = City(
                name=f"{civ.name} Capital",
                owner=civ.name,
                position=(0, 0),
                terrain=starting_terrain,
                population=10,
                gold=civ.starting_gold,
                science=civ.starting_science,
                culture=civ.starting_culture,
                food=0,
                production=0,
            )
            self.cities.append(city)
            civ.cities.append(city)

    def _initialize_characters(self):
        """Create starting ruler for each civilization."""
        for civ in self.civilizations:
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
        """Check if any civilization has achieved victory."""
        for civ in self.civilizations:
            # Domination victory
            if len(civ.cities) >= VICTORY_CONDITIONS["domination"]:
                self.victory = "Domination"
                self.victory_reason = f"{civ.name} controls {len(civ.cities)} cities"
                self.game_over = True
                return

            # Science victory
            if self.tech_manager.science_pool >= VICTORY_CONDITIONS["science"]:
                self.victory = "Science"
                self.victory_reason = f"{civ.name} has collected enough science"
                self.game_over = True
                return

            # Cultural victory
            if civ.culture >= VICTORY_CONDITIONS["culture"]:
                self.victory = "Culture"
                self.victory_reason = f"{civ.name} has reached {civ.culture} culture"
                self.game_over = True
                return

            # Diplomatic victory
            if civ.diplomacy >= VICTORY_CONDITIONS["diplomacy"]:
                self.victory = "Diplomacy"
                self.victory_reason = f"{civ.name} has reached {civ.diplomacy} diplomacy"
                self.game_over = True
                return

    def _log(self, message: str):
        """Add a log message."""
        self.logs.append(f"Turn {self.turn_count}: {message}")

    def _print_state(self):
        """Print the current game state."""
        print(f"\n{'='*50}")
        print(f"Turn {self.turn_count} - {self.current_player.name}'s Turn")
        print(f"{'='*50}")

        # Current player stats
        print(f"\n{self.current_player.name}:")
        print(f"  Gold: {self.current_player.gold}")
        print(f"  Science: {self.current_player.science}")
        print(f"  Culture: {self.current_player.culture}")
        print(f"  Diplomacy: {self.current_player.diplomacy}")
        print(f"  Cities: {len(self.current_player.cities)}")
        print(f"  Unlocked Technologies: {len(self.tech_manager.unlocked_techs)}")

        # Top characters
        print(f"\nTop Characters:")
        sorted_chars = sorted(
            [c for c in self.characters.values() if c.is_alive],
            key=lambda c: sum(c.get_effective_stat(s) for s in ['diplomacy', 'martial', 'stewardship', 'intrigue']),
            reverse=True,
        )[:5]
        for char in sorted_chars:
            total = sum(char.get_effective_stat(s) for s in ['diplomacy', 'martial', 'stewardship', 'intrigue'])
            print(f"  {char.name}: {total} total stats (Age {char.age})")

        # Recent events
        recent_events = self.event_manager.get_recent_events(3)
        if recent_events:
            print(f"\nRecent Events:")
            for event in recent_events:
                print(f"  - {event.name}: {event.description}")

        # Recent plots
        active_plots = self.plot_manager.get_active_plots(self.current_player.name)
        if active_plots:
            print(f"\nActive Plots:")
            for plot in active_plots:
                print(f"  - {plot.name} ({plot.plot_type}): {plot.progress}%")

        print()

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
                self.current_player.diplomacy += bonus
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
        """Get the current game state."""
        return {
            "turn": self.turn_count,
            "current_player": self.current_player.name,
            "game_over": self.game_over,
            "victory": self.victory,
            "victory_reason": self.victory_reason,
            "players": {
                name: {
                    "gold": civ.gold,
                    "science": civ.science,
                    "culture": civ.culture,
                    "diplomacy": civ.diplomacy,
                    "cities": len(civ.cities),
                    "characters": len([c for c in civ.characters if c.is_alive]),
                }
                for name, civ in self.civilizations.items()
            },
            "technology": {
                "unlocked": list(self.tech_manager.unlocked_techs),
                "current_research": self.tech_manager.current_research,
                "science_pool": self.tech_manager.science_pool,
            },
        }

    def print_state(self):
        """Print the current game state."""
        state = self.get_state()
        print(f"\n{'='*50}")
        print(f"Turn {state['turn']} - {state['current_player']}'s Turn")
        print(f"{'='*50}")

        if state['game_over']:
            print(f"\nGame Over! {state['victory']} Victory!")
            print(f"Reason: {state['victory_reason']}")
            return

        print(f"\nPlayers:")
        for name, stats in state['players'].items():
            print(f"  {name}:")
            for stat, value in stats.items():
                print(f"    {stat}: {value}")

        print(f"\nTechnology:")
        print(f"  Unlocked: {', '.join(state['technology']['unlocked'])}")
        print(f"  Current Research: {state['technology']['current_research']}")
        print(f"  Science Pool: {state['technology']['science_pool']}")

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
    # Create civilizations
    civs = [
        Civilization(
            name="Rome",
            starting_gold=100,
            starting_science=50,
            starting_culture=25,
            starting_diplomacy=25,
            starting_stats={
                "diplomacy": 10,
                "martial": 12,
                "stewardship": 11,
                "intrigue": 8,
            },
            starting_traits=["Warrior", "Diplomat"],
        ),
        Civilization(
            name="Greece",
            starting_gold=80,
            starting_science=70,
            starting_culture=40,
            starting_diplomacy=30,
            starting_stats={
                "diplomacy": 12,
                "martial": 9,
                "stewardship": 10,
                "intrigue": 11,
            },
            starting_traits=["Scholar", "Diplomat"],
        ),
        Civilization(
            name="Egypt",
            starting_gold=120,
            starting_science=40,
            starting_culture=30,
            starting_diplomacy=20,
            starting_stats={
                "diplomacy": 8,
                "martial": 11,
                "stewardship": 13,
                "intrigue": 9,
            },
            starting_traits=["Industrious", "Warrior"],
        ),
    ]

    return GameManager(civs)


if __name__ == "__main__":
    game = create_sample_game()
    game.run_game(turns=5)
