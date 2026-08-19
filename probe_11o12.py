from gilded.chassis import GildedGame
import gilded.society.realm as realm_mod

g = GildedGame(seed=47)
# fixture plays to turn 4
for _ in range(4):
    g.end_turn()

import re
src = open("gilded/tests/test_schemes.py").read()
m = re.search(r"I4C1_BUYER_HOUSE = (.*)", src)
print(m.group(0) if m else "no const")
m2 = re.search(r"I4C1_TARGET_HOUSE = (.*)", src)
print(m2.group(0) if m2 else "no const")
