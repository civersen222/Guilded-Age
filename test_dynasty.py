import sys
sys.path.insert(0, '.')
from game import Game
from game_data import CIVILIZATIONS

g = Game(CIVILIZATIONS['Rome'])

print(f'Initial dynasty members: {len(g.dynasty.get_all_members())}')
ruler = g.rulers['Rome']
print(f'Ruler: {ruler.name}, age: {ruler.age}, alive: {ruler.is_alive}')

for i in range(30):
    msgs = g.process_turn()
    if g.state.turn % 10 == 0:
        members = g.dynasty.get_all_members()
        living = [m for m in members if m.is_alive]
        print(f'Turn {g.state.turn}: dynasty={len(members)} living={len(living)}')
        for m in members:
            print(f'  {m.name}, age={m.age}, alive={m.is_alive}')
