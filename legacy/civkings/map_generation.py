"""Improved continent generation: jittered-grid placement, area-scaled island
radius, noise-warped ragged coastlines, latitude+moisture climate terrain.

Extends ContinentGenerator from hex_map; wired in via HexMap.generate().
"""
import math
import random
from typing import Dict, Tuple

from hex_map import ContinentGenerator, SimplexNoise2D, TerrainType


class ContinentGeneratorV2(ContinentGenerator):
    """Continent generator with separated landmasses and climate-aware biomes."""

    def _place_continent_centers(self):
        """Jittered-grid placement: always well-separated, spans the whole map."""
        n = self.num_continents
        cols = max(1, round(math.sqrt(n * self.width / max(1, self.height))))
        rows = math.ceil(n / cols)
        cw, ch = self.width / cols, self.height / rows
        cells = [(c, r) for r in range(rows) for c in range(cols)]
        random.shuffle(cells)
        centers = []
        for c, r in cells[:n]:
            jx = random.uniform(0.30, 0.70)
            jy = random.uniform(0.30, 0.70)
            centers.append((int((c + jx) * cw), int((r + jy) * ch)))
        return centers

    def _generate_elevation_map(self) -> Dict[Tuple[int, int], float]:
        """Continent islands with area-scaled radius and ragged noise-warped coasts."""
        elevation_map: Dict[Tuple[int, int], float] = {}
        base_noise = SimplexNoise2D(seed=random.randint(0, 99999))
        detail_noise = SimplexNoise2D(seed=random.randint(0, 99999))
        coast_noise = SimplexNoise2D(seed=random.randint(0, 99999))
        scale = max(self.width, self.height) / 5

        for x in range(self.width):
            for y in range(self.height):
                nx, ny = x / (scale * 4), y / (scale * 4)
                val = base_noise.octave_noise(nx, ny, octaves=2, persistence=0.4)
                val = (val + 1) / 2
                elevation_map[(x, y)] = 0.08 + val * 0.08

        # Radius sized so total island area ~= 35% of the map
        boost_radius = math.sqrt(0.35 * self.width * self.height / (self.num_continents * math.pi)) / 0.8

        for x in range(self.width):
            for y in range(self.height):
                current = elevation_map[(x, y)]
                best_boost = 0.0
                # Ragged coastlines: warp distance to centers by noise
                warp = coast_noise.octave_noise(x / (scale * 0.8), y / (scale * 0.8), octaves=3, persistence=0.55)
                for cx, cy in self.continent_centers:
                    dist = math.dist((x, y), (cx, cy)) * (1.0 + warp * 0.9)
                    if dist < boost_radius:
                        t = dist / boost_radius
                        falloff = 1.0 - t * t * t
                        large = base_noise.octave_noise(x / scale * 1.5, y / scale * 1.5, octaves=3, persistence=0.5)
                        large = min(1.0, max(0.0, 0.5 + large * 1.5))
                        fine = detail_noise.octave_noise(x / scale * 4, y / scale * 4, octaves=4, persistence=0.6)
                        fine = (fine + 1) / 2
                        base_elev = large * 0.60 + 0.35
                        detail = fine * 0.20 - 0.10
                        elevation = (base_elev + detail) * falloff + current * (1 - falloff)
                        if elevation > best_boost:
                            best_boost = elevation
                elevation_map[(x, y)] = max(current, min(best_boost, 1.0))
        return elevation_map

    def _assign_terrain_from_elevation(self, elevation_map: Dict[Tuple[int, int], float]) -> Dict[Tuple[int, int], TerrainType]:
        """Latitude + moisture climate model instead of pure elevation rings."""
        moisture_noise = SimplexNoise2D(seed=random.randint(0, 99999))
        mscale = max(self.width, self.height) / 8
        terrain_map: Dict[Tuple[int, int], TerrainType] = {}
        for (x, y), elevation in elevation_map.items():
            on_continent = any((x, y) in c.tiles for c in self.continents)
            if not on_continent:
                terrain_map[(x, y)] = TerrainType.OCEAN if elevation < 0.15 else TerrainType.WATER_COAST
                continue
            if elevation < 0.35:
                terrain_map[(x, y)] = TerrainType.WATER_COAST
                continue
            lat = abs(y / max(1, self.height - 1) - 0.5) * 2.0  # 0 = equator, 1 = pole
            raw = moisture_noise.octave_noise(x / mscale, y / mscale, octaves=3)
            moisture = min(1.0, max(0.0, 0.5 + raw * 1.6))
            if elevation > 0.74:
                terrain_map[(x, y)] = TerrainType.MOUNTAIN
            elif elevation > 0.65:
                terrain_map[(x, y)] = TerrainType.HILLS
            elif lat > 0.82 or (lat > 0.68 and moisture < 0.5):
                terrain_map[(x, y)] = TerrainType.TUNDRA
            elif moisture < 0.32 and lat < 0.55:
                terrain_map[(x, y)] = TerrainType.DESERT
            elif moisture > 0.62:
                terrain_map[(x, y)] = TerrainType.FOREST
            elif moisture > 0.45:
                terrain_map[(x, y)] = TerrainType.GRASSLAND
            else:
                terrain_map[(x, y)] = TerrainType.PLAINS
        return terrain_map
