from game_manager import create_sample_game

g = create_sample_game()
g.run_game(50)
print('OK:', g.turn_count)
