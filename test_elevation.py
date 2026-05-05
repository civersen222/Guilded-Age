import sys
sys.path.insert(0, '.')
import random
from hex_map import HexMap, ContinentGenerator

random.seed(42)
m = HexMap(40, 30)

# Generate elevation map directly
gen = ContinentGenerator(40, 30, 3)
elev = gen._generate_elevation_map()

vals = sorted(elev.values())
print(f"Elevation range: {min(vals):.4f} to {max(vals):.4f}")
print(f"Percentiles:")
for p in [10, 25, 50, 75, 90, 95, 99]:
    idx = int(len(vals) * p / 100)
    print(f"  {p}th: {vals[idx]:.4f}")

# Count by elevation band
bands = {"<0.20": 0, "0.20-0.35": 0, "0.35-0.45": 0, "0.45-0.52": 0, "0.52-0.58": 0, "0.58-0.65": 0, "0.65-0.72": 0, "0.72-0.80": 0, ">0.80": 0}
for v in elev.values():
    if v < 0.20: bands["<0.20"] += 1
    elif v < 0.35: bands["0.20-0.35"] += 1
    elif v < 0.45: bands["0.35-0.45"] += 1
    elif v < 0.52: bands["0.45-0.52"] += 1
    elif v < 0.58: bands["0.52-0.58"] += 1
    elif v < 0.65: bands["0.58-0.65"] += 1
    elif v < 0.72: bands["0.65-0.72"] += 1
    elif v < 0.80: bands["0.72-0.80"] += 1
    else: bands[">0.80"] += 1

print("\nElevation bands:")
for k, v in bands.items():
    print(f"  {k:>10}: {v}")
