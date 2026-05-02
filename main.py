"""Entry point for CivKings game."""

import sys


def main():
    """Main entry point."""
    try:
        from gui import main as gui_main
        gui_main()
    except ImportError:
        print("GUI not available. Starting text mode...")
        from ui import GameUI


        while True:
            game_ui = GameUI(GameUI.new_game())

            while game_ui.running:
                print("\n" + "="*60)
                print("  CIVKINGS - Dynasty & Conquest")
                print("="*60)
                print("\n1. Start New Game")
                print("2. Load Game")
                print("3. Quit")
                print()

                choice = input("Enter choice: ")

                if choice == "1":
                    game_ui = GameUI(GameUI.new_game())
                    game_ui.running = True
                    while game_ui.running:
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

                        cmd = input("Enter command: ")

                        if cmd == "1":
                            game_ui.display_map()
                        elif cmd == "2":
                            game_ui.display_cities()
                        elif cmd == "3":
                            game_ui.display_units()
                        elif cmd == "4":
                            game_ui.display_research()
                        elif cmd == "5":
                            game_ui.show_production_menu()
                        elif cmd == "6":
                            game_ui.display_diplomacy()
                        elif cmd == "7":
                            game_ui.display_events()
                        elif cmd == "8":
                            game_ui.next_turn()
                        elif cmd == "9":
                            game_ui.save_game()
                        elif cmd == "10":
                            game_ui.running = False
                        else:
                            print("Invalid command.")
                elif choice == "2":
                    loaded_game = GameUI.load_game()
                    if loaded_game:
                        game_ui = GameUI(loaded_game)
                        game_ui.running = True
                    else:
                        print("No save game found!")
                elif choice == "3":
                    print("Thanks for playing!")
                    sys.exit(0)
                else:
                    print("Invalid choice.")


if __name__ == "__main__":
    main()
