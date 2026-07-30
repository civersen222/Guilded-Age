"""Entry point for CivKings game."""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main entry point — launches Pygame GUI."""
    try:
        from pygame_app.app import main as pygame_main
        pygame_main()
    except ImportError as e:
        print(f"Pygame GUI not available ({e}). Install with: pip install -r requirements.txt")
        print("Falling back to text mode...")
        from ui import GameUI
        game_ui = GameUI(GameUI.new_game())
        # (legacy text UI loop)


if __name__ == "__main__":
    main()
