with open('game_manager.py', 'r') as f:
    content = f.read()

old_city_call = '''            city = City(
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
            )'''

new_city_call = '''            city = City(
                name=f"{civ.name} Capital",
                owner=civ.name,
                position=(0, 0),
                population=10,
                gold=civ.starting_gold,
            )'''

content = content.replace(old_city_call, new_city_call)

with open('game_manager.py', 'w') as f:
    f.write(content)

print("Done!")
