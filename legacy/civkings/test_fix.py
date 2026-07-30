from game_manager import create_sample_game
try:
    g = create_sample_game()
    g.run_game(10)
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
