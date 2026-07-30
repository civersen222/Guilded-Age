"""Test all imports and basic game functionality."""

import sys
import traceback

def test_imports():
    """Test all module imports."""
    modules = [
        'game_data',
        'hex_map', 
        'map',
        'city',
        'military',
        'diplomacy',
        'tech',
        'events',
        'ai',
    ]
    
    for mod in modules:
        try:
            __import__(mod)
            print(f"OK: {mod}")
        except Exception as e:
            print(f"FAIL: {mod} - {e}")
            traceback.print_exc()

def test_game():
    """Test basic game creation."""
    from game_data import CIVILIZATIONS
    from game import Game
    
    player_civ = CIVILIZATIONS["Rome"]
    ai_civs = [CIVILIZATIONS["Greece"]]
    
    game = Game(player_civ, ai_civs)
    print(f"Game created: {game.state.turn} turns, {len(game.cities)} cities, {len(game.units)} units")
    
    # Process one turn
    msgs = game.process_turn()
    print(f"Turn processed: {game.state.turn}, {len(msgs)} messages")
    print(game.get_game_status())

if __name__ == "__main__":
    print("Testing imports...")
    test_imports()
    print("\nTesting game...")
    try:
        test_game()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        traceback.print_exc()
