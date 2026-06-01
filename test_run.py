from game_manager import create_sample_game

g = create_sample_game()
g.run_game(500)
s = g.get_state()
print(f"OK: {g.state.turn} turns")
for c in s.get('civilizations', []):
    print(f'  {c["name"]}: {len(c.get("cities", []))} cities, {c.get("gold", 0)} gold')
