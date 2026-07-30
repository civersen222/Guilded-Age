import sys
sys.path.insert(0, '.')
import random
from hex_map import HexMap

# Test map generation
random.seed(42)
m = HexMap(40, 30)
m.generate()

# Count terrain types
from collections import Counter
terrains = Counter()
for tile in m.tiles.values():
    terrains[tile.terrain.name] += 1

print("Terrain distribution:")
for name, count in sorted(terrains.items(), key=lambda x: -x[1]):
    print(f"  {name}: {count} ({count/len(m.tiles)*100:.1f}%)")
print(f"Total tiles: {len(m.tiles)}")
