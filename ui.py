"""Text-based UI for the game."""

from typing import List, Optional, Dict, Tuple
from game import Game
from map import render_map
from game_data import CIVILIZATIONS, UNIT_TYPES, BUILDINGS, DISTRICTS


COMMAND_HELP = {
    "map": "View the world map",
    "map zoom <n>": "Zoom map to radius n",
    "cities": "List your cities",
    "city <name>": "Show details for a city",
    "units": "List your units",
    "unit <name>": "Show details for a unit",
    "research <tech>": "Start researching a technology",
    "research tree": "Show current tech progress",
    "produce <city> <item>": "Queue production in a city",
    "produce unit <city> <unit>": "Queue a unit",
    "produce building <city> <building>": "Queue a building",
    "build <district> <city>": "Build a district",
    "diplomacy": "Show diplomatic relations",
    "diplomacy <civ> war": "Declare war on a civ",
    "diplomacy <civ> peace": "Propose peace treaty",
    "diplomacy <civ> ally": "Propose alliance",
    "events": "Show recent world events",
    "next": "End your turn",
    "end": "End your turn (alias)",
    "save": "Save the game",
    "help": "Show this help",
    "help <cmd>": "Show help for a command",
    "quit": "Quit the game",
    "q": "Quit the game",
    "status": "Show empire overview",
    "info": "Show character/dynasty info",
}


class CommandParser:
    """Parse typed commands and route to handlers."""

    def __init__(self, ui: 'GameUI'):
        self.ui = ui

    def parse(self, raw: str) -> str:
        """Parse a raw command string and return a message."""
        raw = raw.strip().lower()
        if not raw:
            return ""

        parts = raw.split()
        cmd = parts[0]

        # Dispatch
        if cmd in ("quit", "q"):
            self.ui.running = False
            return "Goodbye!"

        if cmd == "help":
            return self._help(parts[1:] if len(parts) > 1 else None)

        if cmd == "map":
            return self._cmd_map(parts)

        if cmd == "cities":
            self.ui.display_cities()
            return ""

        if cmd == "city":
            return self._cmd_city(parts)

        if cmd == "units":
            self.ui.display_units()
            return ""

        if cmd == "unit":
            return self._cmd_unit(parts)

        if cmd == "research":
            if len(parts) > 1 and parts[1] == "tree":
                self.ui.display_research()
                return ""
            return self._cmd_research(parts[1:])

        if cmd == "produce":
            return self._cmd_produce(parts)

        if cmd == "build":
            return self._cmd_build(parts)

        if cmd == "diplomacy":
            return self._cmd_diplomacy(parts)

        if cmd == "events":
            self.ui.display_events()
            return ""

        if cmd in ("next", "end"):
            self.ui.next_turn()
            return ""

        if cmd == "save":
            self.ui.save_game()
            return ""

        if cmd == "status":
            return self.ui.game.get_game_status()

        if cmd == "info":
            return self._cmd_info()

        return f"Unknown command: '{cmd}'. Type 'help' for available commands."

    def _help(self, sub: Optional[str]) -> str:
        if not sub:
            lines = []
            for cmd, desc in sorted(COMMAND_HELP.items()):
                lines.append(f"  {cmd:<25} {desc}")
            return "\nCommands:\n" + "\n".join(lines) + "\n"
        # Partial match
        matches = [(c, d) for c, d in COMMAND_HELP.items() if sub in c]
        if matches:
            return "\nMatches:\n" + "\n".join(f"  {c:<25} {d}" for c, d in matches) + "\n"
        return f"No help found for '{sub}'."

    def _cmd_map(self, parts: List[str]) -> str:
        zoom = 15
        if len(parts) > 1:
            try:
                zoom = int(parts[1])
            except ValueError:
                return "Invalid zoom value."
        map_str = render_map(
            self.ui.game.map, self.ui.fog,
            list(self.ui.game.cities.values()),
            list(self.ui.game.units.values()),
            show_resources=True
        )
        return map_str

    def _cmd_city(self, parts: List[str]) -> str:
        if len(parts) < 2:
            return "Usage: city <name>"
        player = self.ui.game.state.current_player
        for c in self.ui.game.cities.values():
            if c.name.lower() == parts[1].lower() and c.owner_id == player:
                return (
                    f"\n=== {c.name} ===\n"
                    f"  Population: {c.population}\n"
                    f"  Food: {c.food_reserved} | Production: {c.production} | Gold: {c.gold}\n"
                    f"  Science: {c.science} | Faith: {c.faith} | Happiness: {c.happiness}\n"
                    f"  Districts: {', '.join(d.name for d in c.districts)}\n"
                    f"  Buildings: {', '.join(b.name for b in c.buildings)}\n"
                    f"  Production Queue: {', '.join(p.name for p in c.production_queue)}"
                )
        return f"City '{parts[1]}' not found or not yours."

    def _cmd_unit(self, parts: List[str]) -> str:
        if len(parts) < 2:
            return "Usage: unit <name>"
        player = self.ui.game.state.current_player
        for u in self.ui.game.units.values():
            if u.name.lower() == parts[1].lower() and u.owner_id == player:
                hp = f"{u.hp:.0f}/{u.max_hp}"
                return (
                    f"\n=== {u.name} ===\n"
                    f"  Position: {u.position}\n"
                    f"  HP: {hp}\n"
                    f"  Attack: {u.attack} | Defense: {u.defense}\n"
                    f"  Promotion: {u.promotion}\n"
                    f"  Type: {u.unit_type}"
                )
        return f"Unit '{parts[1]}' not found or not yours."

    def _cmd_research(self, parts: List[str]) -> str:
        if len(parts) < 1:
            return "Usage: research <tech_name>"
        player = self.ui.game.state.current_player
        research = self.ui.game.research[player]
        tech_name = parts[0]
        # Find tech by name
        available = research.get_available_techs()
        for tech in available:
            if tech.name.lower() == tech_name.lower():
                research.start_research(tech)
                return f"Started researching {tech.name}!"
        # Check already researched
        if any(t.name.lower() == tech_name.lower() for t in research.researched_techs):
            return f"Already researched {tech_name}."
        return f"Cannot research '{tech_name}'. Available: {', '.join(t.name for t in available[:10])}"

    def _cmd_produce(self, parts: List[str]) -> str:
        if len(parts) < 3:
            return "Usage: produce <city> <unit|building> <name>"
        city_name = parts[0]
        item_type = parts[1]
        item_name = parts[2]
        player = self.ui.game.state.current_player
        for c in self.ui.game.cities.values():
            if c.name.lower() == city_name.lower() and c.owner_id == player:
                cost = 50
                if item_type == "unit":
                    if item_name in UNIT_TYPES:
                        c.production_queue.append(type('ProductionItem', (), {
                            'name': item_name, 'item_type': 'unit',
                            'cost': cost, 'data': item_name
                        })())
                        return f"Added {item_name} (unit) to {c.name}'s production queue!"
                elif item_type == "building":
                    if item_name in BUILDINGS:
                        c.production_queue.append(type('ProductionItem', (), {
                            'name': item_name, 'item_type': 'building',
                            'cost': cost, 'data': item_name
                        })())
                        return f"Added {item_name} (building) to {c.name}'s production queue!"
                return f"Unknown {item_type}: '{item_name}'."
        return f"City '{city_name}' not found or not yours."

    def _cmd_build(self, parts: List[str]) -> str:
        if len(parts) < 2:
            return "Usage: build <district> <city>"
        district_name = parts[0]
        city_name = parts[1]
        player = self.ui.game.state.current_player
        for c in self.ui.game.cities.values():
            if c.name.lower() == city_name.lower() and c.owner_id == player:
                if district_name in DISTRICTS:
                    c.districts.append(type('District', (), {
                        'name': district_name
                    })())
                    return f"Built {district_name} district in {c.name}!"
                return f"Unknown district: '{district_name}'."
        return f"City '{city_name}' not found or not yours."

    def _cmd_diplomacy(self, parts: List[str]) -> str:
        if len(parts) < 1:
            self.ui.display_diplomacy()
            return ""
        player = self.ui.game.state.current_player
        target = parts[0]
        action = parts[1] if len(parts) > 1 else ""
        if action == "war":
            return self.ui.game.diplomacy.declare_war(player, target)
        if action == "peace":
            return self.ui.game.diplomacy.propose_peace(player, target)
        if action == "ally":
            return self.ui.game.diplomacy.propose_alliance(player, target)
        return f"Unknown diplomacy action: '{action}'. Use war, peace, or ally."

    def _cmd_info(self) -> str:
        player = self.ui.game.state.current_player
        player_civ = self.ui.game.players.get(player)
        if not player_civ:
            return "No player info available."
        return (
            f"\n=== {player}'s Dynasty ===\n"
            f"  Civilization: {player_civ.name if hasattr(player_civ, 'name') else player_civ}\n"
            f"  Treasury: {self.ui.game.gold.get(player, 0)} gold\n"
            f"  Techs Researched: {len(self.ui.game.research.get(player, type('R', (), {'researched_techs': []})()).researched_techs)}\n"
            f"  Cities: {len([c for c in self.ui.game.cities.values() if c.owner_id == player])}\n"
            f"  Units: {len([u for u in self.ui.game.units.values() if u.owner_id == player])}"
        )


class GameUI:
    """Text interface for the game."""

    def __init__(self, game: Game):
        self.game = game
        self.command_parser = CommandParser(self)
        self.running = True

    def show_main_menu(self):
        """Display the main menu."""
        print("\n" + "="*60)
        print("  CIVKINGS - Dynasty & Conquest")
        print("="*60)
        print("\n1. Start New Game")
        print("2. Load Game")
        print("3. Quit")
        print()

    def show_game_menu(self):
        """Display the in-game menu."""
        print("\n" + "-"*40)
        print("  COMMANDS")
        print("-"*40)
        print("1. View Map")
        print("2. View Cities")
        print("3. View Units")
        print("4. Research Tech")
        print("5. Production")
        print("6. Diplomacy")
        print("7. Events")
        print("8. Next Turn")
        print("9. Save Game")
        print("10. Quit")
        print()

    def choose_civilization(self) -> str:
        """Let the player choose their civilization."""
        print("\nChoose your civilization:")
        for i, (name, civ) in enumerate(CIVILIZATIONS.items(), 1):
            print(f"{i}. {name} - {civ.bonus}")
        print()

        while True:
            try:
                choice = int(input("Enter number: "))
                if 1 <= choice <= len(CIVILIZATIONS):
                    return list(CIVILIZATIONS.keys())[choice - 1]
            except:
                pass
            print("Invalid choice. Try again.")

    def display_map(self):
        """Show the current map."""
        map_str = render_map(
            self.game.map,
            self.game.fog,
            list(self.game.cities.values()),
            list(self.game.units.values())
        )
        print(map_str)

    def display_cities(self):
        """Show all cities for the current player."""
        player = self.game.state.current_player
        player_cities = [c for c in self.game.cities.values() if c.owner_id == player]

        if not player_cities:
            print(f"\nNo cities for {player}!")
            return

        print(f"\n=== {player}'s Cities ===")
        for city in player_cities:
            print(f"\n{city.name} (Pop: {city.population})")
            print(f"  Food: {city.food_reserved}, Production: {city.production}, Gold: {city.gold}")
            print(f"  Science: {city.science}, Faith: {city.faith}, Happiness: {city.happiness}")
            print(f"  Districts: {', '.join(d.name for d in city.districts)}")
            print(f"  Buildings: {', '.join(b.name for b in city.buildings)}")

    def display_units(self):
        """Show all units for the current player."""
        player = self.game.state.current_player
        player_units = [u for u in self.game.units.values() if u.owner_id == player]

        if not player_units:
            print(f"\nNo units for {player}!")
            return

        print(f"\n=== {player}'s Units ===")
        for unit in player_units:
            hp = f"{unit.hp:.0f}/{unit.max_hp}"
            print(f"  {unit.name} at {unit.position} (HP: {hp}, Promo: {unit.promotion})")

    def display_research(self):
        """Show research progress."""
        player = self.game.state.current_player
        research = self.game.research[player]
        print(research.get_tech_tree_display())

    def display_diplomacy(self):
        """Show diplomatic relations."""
        player = self.game.state.current_player
        print(f"\n=== Diplomacy for {player} ===")

        for civ_name, civ in self.game.players.items():
            if civ_name != player:
                opinion = self.game.diplomacy.get(player)
                if opinion:
                    op = opinion.get_opinion(civ_name)
                else:
                    op = 0
                print(f"  {civ_name}: Opinion {op}")

    def display_events(self):
        """Show current events."""
        print(self.game.events.get_event_summary())
        print(self.game.events.get_world_state_summary())

    def show_production_menu(self):
        """Show production options for a city."""
        player = self.game.state.current_player
        player_cities = [c for c in self.game.cities.values() if c.owner_id == player]

        if not player_cities:
            print("\nNo cities to produce in!")
            return

        print("\nSelect city to produce:")
        for i, city in enumerate(player_cities, 1):
            print(f"{i}. {city.name}")
        print()

        while True:
            try:
                choice = int(input("Enter city number: "))
                if 1 <= choice <= len(player_cities):
                    city = player_cities[choice - 1]
                    print(f"\nProducing in {city.name}:")
                    print("  1. Unit")
                    print("  2. Building")
                    print("  3. District")
                    sub_choice = input("Choose type (1-3): ")

                    if sub_choice == "1":
                        print("Available units:")
                        for name in UNIT_TYPES:
                            print(f"  - {name}")
                        unit_name = input("Enter unit name: ")
                        item_name = input("Production name: ")
                        cost = int(input("Production cost: ") or "50")
                        city.production_queue.append(
                            type('ProductionItem', (), {
                                'name': item_name,
                                'item_type': 'unit',
                                'cost': cost,
                                'data': unit_name
                            })()
                        )
                        print(f"Added {item_name} to queue!")
                        break
                    elif sub_choice == "2":
                        print("Available buildings:")
                        for name in BUILDINGS:
                            print(f"  - {name}")
                        building_name = input("Enter building name: ")
                        print(f"Added {building_name} to queue!")
                        break
                    elif sub_choice == "3":
                        print("Available districts:")
                        for name in DISTRICTS:
                            print(f"  - {name}")
                        district_name = input("Enter district name: ")
                        print(f"Added {district_name} to queue!")
                        break
            except:
                print("Invalid choice.")

    def next_turn(self):
        """Process the next turn."""
        messages = self.game.process_turn()

        if messages:
            print("\n=== Turn Events ===")
            for msg in messages:
                if msg.startswith("***"):
                    print(f"\n{msg}")
                else:
                    print(f"  {msg}")

        print(self.game.get_game_status())

    def run(self):
        """Main game loop."""
        while self.running:
            choice = input("\n> ").strip().lower()

            # Handle single-letter shortcuts
            if choice == "m":
                self.display_map()
            elif choice == "c":
                self.display_cities()
            elif choice == "u":
                self.display_units()
            elif choice == "r":
                self.display_research()
            elif choice == "p":
                self.show_production_menu()
            elif choice == "d":
                self.display_diplomacy()
            elif choice == "e":
                self.display_events()
            elif choice == "f5" or choice == "n":
                self.next_turn()
            elif choice == "s":
                self.save_game()
            elif choice in ("quit", "q"):
                self.running = False
            else:
                # Try typed command parser
                msg = self.command_parser.parse(choice)
                if msg:
                    print(msg)

    def save_game(self):
        """Save the current game."""
        import json
        try:
            with open("savegame.json", "w") as f:
                json.dump(self.game.to_dict(), f, indent=2, default=str)
            print("Game saved!")
        except Exception as e:
            print(f"Save failed: {e}")

    @staticmethod
    def load_game() -> Optional[Game]:
        """Load a saved game."""
        import json
        try:
            with open("savegame.json", "r") as f:
                data = json.load(f)
            return Game.from_dict(data)
        except:
            return None

    @staticmethod
    def new_game() -> Game:
        """Start a new game."""
        player_civ_name = "Rome"
        player_civ = CIVILIZATIONS[player_civ_name]
        ai_civ_names = ["Greece", "Egypt", "Persia"]
        ai_civs = [CIVILIZATIONS[name] for name in ai_civ_names]
        game = Game(player_civ, ai_civs, map_width=100, map_height=100)
        return game
