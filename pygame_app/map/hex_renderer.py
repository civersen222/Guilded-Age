"""Hex tile renderer — draws terrain, resources, cities, units, fog, and highlights."""

from collections import deque
import math
import os
from typing import Set, Tuple, Optional, Dict, Any

import pygame

from pygame_app.constants import (
    TERRAIN_COLORS,
    HEX_SIZE,
    GOLD,
    RED,
    GREEN,
    TEXT,
    SUBTLE,
    BLUE,
)


class HexRenderer:
    """Renders a hex-based game map onto a Pygame surface."""

    # City tiers: (min_pop, max_pop, sprite_key)
    CITY_TIERS = [
        (1, 3, "village"),
        (4, 7, "town"),
        (8, 12, "city"),
        (13, 9999, "metropolis"),
    ]

    def __init__(self, hex_map: Any, tile_atlas: Any, camera: Any):
        self.hex_map = hex_map
        self.tile_atlas = tile_atlas
        self.camera = camera

        # Fonts
        self._font_small = pygame.font.SysFont("consolas", 11, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 14, bold=True)
        self._font_large = pygame.font.SysFont("consolas", 18, bold=True)

        # Selection / hover state
        self.selected_hex: Optional[Tuple[int, int]] = None
        self.move_range: Set[Tuple[int, int]] = set()
        self.attack_range: Set[Tuple[int, int]] = set()
        self.hovered_hex: Optional[Tuple[int, int]] = None

        # Sprite caches
        self._unit_sprites: Dict[str, pygame.Surface] = {}
        self._city_sprites: Dict[str, pygame.Surface] = {}
        # Tile zoom-surface cache: {(terrain_name, zoom_tag): pygame.Surface}
        self._tile_zoom_cache: Dict[Tuple[str, str], pygame.Surface] = {}

        # Movement animations
        self._animations: list = []
        self._prev_unit_positions: Dict[str, Tuple[int, int]] = {}

        self._load_sprites()

    def _load_sprites(self) -> None:
        """Load all unit and city sprite images."""
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets")

        # Load unit icons (48px)
        units_icons_dir = os.path.join(assets_dir, "units", "icons")
        if os.path.isdir(units_icons_dir):
            for fname in os.listdir(units_icons_dir):
                if not fname.endswith("_48.png"):
                    continue
                unit_type = fname.replace("_48.png", "")
                path = os.path.join(units_icons_dir, fname)
                try:
                    surf = pygame.image.load(path).convert_alpha()
                    self._unit_sprites[unit_type] = surf
                except Exception:
                    pass

        # Load city sprites (64px)
        cities_sprites_dir = os.path.join(assets_dir, "cities", "sprites")
        if os.path.isdir(cities_sprites_dir):
            for fname in os.listdir(cities_sprites_dir):
                if not fname.endswith("_64.png"):
                    continue
                tier = fname.replace("_64.png", "")
                path = os.path.join(cities_sprites_dir, fname)
                try:
                    surf = pygame.image.load(path).convert_alpha()
                    self._city_sprites[tier] = surf
                except Exception:
                    pass

    def _get_city_tier(self, population: int) -> str:
        """Determine city sprite tier from population."""
        for min_pop, max_pop, tier in self.CITY_TIERS:
            if min_pop <= population <= max_pop:
                return tier
        return "village"

    def _track_unit_movement(self, game: Any) -> None:
        """Detect unit position changes and create movement animations."""
        units = getattr(game, "units", {})
        current_positions = {}

        for uid, unit in units.items():
            if not getattr(unit, "is_alive", False):
                continue
            pos = getattr(unit, "position", None)
            if pos is None:
                continue
            current_positions[uid] = pos

            prev_pos = self._prev_unit_positions.get(uid)
            if prev_pos is not None and prev_pos != pos:
                # Unit moved — create animation
                self._animations.append({
                    "unit_id": uid,
                    "start_pos": prev_pos,
                    "end_pos": pos,
                    "progress": 0.0,
                    "duration": 0.3,
                })

        self._prev_unit_positions = current_positions

    def update(self, dt: float) -> None:
        """Update all movement animations."""
        for anim in self._animations:
            anim["progress"] += dt / anim["duration"]
            if anim["progress"] >= 1.0:
                anim["progress"] = 1.0

        # Remove completed animations
        self._animations = [a for a in self._animations if a["progress"] < 1.0]

    def _get_animated_position(self, unit_id: str) -> Optional[Tuple[float, float]]:
        """Get interpolated screen position for a unit in animation, or None."""
        for anim in self._animations:
            if anim["unit_id"] == unit_id:
                t = anim["progress"]
                # Smooth easing
                t = t * t * (3 - 2 * t)  # smoothstep
                sx_start, sy_start = self.hex_to_world(anim["start_pos"][0], anim["start_pos"][1])
                sx_end, sy_end = self.hex_to_world(anim["end_pos"][0], anim["end_pos"][1])
                wx = sx_start + (sx_end - sx_start) * t
                wy = sy_start + (sy_end - sy_start) * t
                sx, sy = self.camera.world_to_screen(wx, wy)
                return sx, sy
        return None

    # ── coordinate transforms ──────────────────────────────────────────

    @staticmethod
    def hex_to_world(hx: int, hy: int) -> Tuple[float, float]:
        """Convert flat-top axial hex coords to world pixel position (center)."""
        wx = HEX_SIZE * 1.5 * hx
        wy = HEX_SIZE * math.sqrt(3) * (hy + 0.5 * (hx & 1))
        return wx, wy

    @staticmethod
    def world_to_hex(wx: float, wy: float) -> Tuple[int, int]:
        """Inverse: approximate world pixel → axial hex coords."""
        # Reconstruct axial from offset
        ax = wx / (HEX_SIZE * 1.5)
        ay = wy / (HEX_SIZE * math.sqrt(3))
        # Undo odd-row offset: ay includes 0.5 * ax when ax is odd
        ay_corrected = ay - 0.5 * (ax % 2) if ax >= 0 else ay + 0.5 * ((-ax) % 2)
        hx = round(ax)
        hy = round(ay_corrected)
        return hx, hy

    def screen_to_hex(self, sx: int, sy: int) -> Tuple[int, int]:
        """Screen pixel → hex coords via camera world transform."""
        wx, wy = self.camera.screen_to_world(sx, sy)
        return self.world_to_hex(wx, wy)

    def get_visible_hexes(self) -> Set[Tuple[int, int]]:
        """Return set of hex coords visible in camera viewport (with margin)."""
        margin = 2
        bounds = self.camera.get_visible_bounds()
        min_wx, min_wy, max_wx, max_wy = bounds

        # Expand bounds by margin in hex-space
        margin_wx = HEX_SIZE * 1.5 * margin
        margin_wy = HEX_SIZE * math.sqrt(3) * margin
        min_wx -= margin_wx
        min_wy -= margin_wy
        max_wx += margin_wx
        max_wy += margin_wy

        # Convert world bounds to hex coordinate bounds
        min_hx, min_hy = self.world_to_hex(min_wx, min_wy)
        max_hx, max_hy = self.world_to_hex(max_wx, max_wy)

        hexes: Set[Tuple[int, int]] = set()
        for hx in range(min_hx - margin, max_hx + margin + 1):
            for hy in range(min_hy - margin, max_hy + margin + 1):
                if (hx, hy) in self.hex_map.tiles:
                    wx, wy = self.hex_to_world(hx, hy)
                    sx, sy = self.camera.world_to_screen(wx, wy)
                    if 0 <= sx < self.camera.screen_w and 0 <= sy < self.camera.screen_h:
                        hexes.add((hx, hy))
        return hexes

    # ── hex geometry helpers ───────────────────────────────────────────

    @staticmethod
    def _hex_vertices(cx: float, cy: float, zoom: float = 1.0) -> Tuple[float, ...]:
        """Return 6 vertex coords for a flat-top hex centred at (cx, cy).

        Vertices at angles π/3 * i (i = 0..5). Scaled by zoom to match tile size.
        """
        points: list[float] = []
        for i in range(6):
            angle = math.pi / 3 * i
            points.append(cx + HEX_SIZE * zoom * math.cos(angle))
            points.append(cy + HEX_SIZE * zoom * math.sin(angle))
        return tuple(points)

    def _screen_hex_points(self, hx: int, hy: int) -> Tuple[float, ...]:
        """Screen-space vertex coords for a hex."""
        wx, wy = HexRenderer.hex_to_world(hx, hy)
        sx, sy = self.camera.world_to_screen(wx, wy)
        zoom = getattr(self.camera, "zoom", 1.0)
        return self._hex_vertices(sx, sy, zoom)

    # ── drawing primitives ─────────────────────────────────────────────

    @staticmethod
    def _draw_hex_outline(surface: pygame.Surface, verts: Tuple[float, ...],
                          colour: tuple, width: int = 2):
        """Draw a hex outline using pygame.draw.polygon."""
        points = [(int(verts[i]), int(verts[i + 1])) for i in range(0, len(verts), 2)]
        pygame.draw.polygon(surface, colour, points, width)

    @staticmethod
    def _draw_hex_fill(surface: pygame.Surface, verts: Tuple[float, ...],
                       colour: tuple, alpha: int = 100):
        """Fill a hex with a semi-transparent colour overlay."""
        points = [(int(verts[i]), int(verts[i + 1])) for i in range(0, len(verts), 2)]

        # Compute bounding box from actual points (zoom-aware)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, min_y = min(xs), min(ys)
        max_x, max_y = max(xs), max(ys)
        w = int(max_x - min_x) + 3
        h = int(max_y - min_y) + 3

        hex_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        hex_surf.set_colorkey((0, 0, 0))
        offset_points = [(p[0] - min_x + 1, p[1] - min_y + 1) for p in points]
        pygame.draw.polygon(hex_surf, (*colour, alpha), offset_points)

        surface.blit(hex_surf, (0, 0))

    # ── move / attack range calculation ──────────────────────────────

    def calculate_move_range(
        self, start: Tuple[int, int], moves_left: int,
        units: Dict[Any, Any], game: Any,
    ) -> Set[Tuple[int, int]]:
        """BFS from *start* using terrain costs; returns set of reachable hexes."""
        moveable: Set[Tuple[int, int]] = set()
        queue: deque = deque([(start, moves_left)])
        visited: Set[Tuple[int, int]] = {start}

        while queue:
            (cx, cy), remaining = queue.popleft()
            if remaining <= 0:
                continue

            for dq, dr in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]:
                nx, ny = cx + dq, cy + dr
                if (nx, ny) in visited:
                    continue
                if (nx, ny) not in self.hex_map.tiles:
                    continue

                tile = self.hex_map.get_tile(nx, ny)
                if not tile:
                    continue

                terrain = getattr(tile, "terrain", None)
                if terrain is None:
                    continue

                # Mountains impassable
                from game_data import TerrainType
                if terrain == TerrainType.MOUNTAIN:
                    continue

                # Water — only passable for naval units (simplified: allow coast/ocean)
                cost = 1
                from game_data import TERRAIN_MOVEMENT_COST
                cost = TERRAIN_MOVEMENT_COST.get(terrain, 1)
                if cost == 99:  # mountain sentinel
                    continue

                if remaining >= cost:
                    # Check no enemy unit blocks (allied units block too for simplicity)
                    occupied = False
                    for uid, unit in units.items():
                        if getattr(unit, "is_alive", False) and getattr(unit, "position", None) == (nx, ny):
                            if getattr(unit, "owner", "") != getattr(game, "_player_name", ""):
                                occupied = True
                                break
                    if occupied:
                        continue

                    moveable.add((nx, ny))
                    visited.add((nx, ny))
                    queue.append(((nx, ny), remaining - cost))

        return moveable

    def calculate_attack_range(
        self, attacker_hex: Tuple[int, int],
        units: Dict[Any, Any], game: Any,
    ) -> Set[Tuple[int, int]]:
        """Return all hexes with enemy units reachable by attack (adjacent hexes)."""
        attackable: Set[Tuple[int, int]] = set()
        player_name = getattr(game, "_player_name", "")

        for dq, dr in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]:
            nx, ny = attacker_hex[0] + dq, attacker_hex[1] + dr
            if (nx, ny) not in self.hex_map.tiles:
                continue
            for uid, unit in units.items():
                if (getattr(unit, "is_alive", False)
                        and getattr(unit, "position", None) == (nx, ny)
                        and getattr(unit, "owner", "") != player_name):
                    attackable.add((nx, ny))
                    break

        return attackable

    # ── label helpers ──────────────────────────────────────────────────

    def _blit_text(self, surface: pygame.Surface, text: str,
                   pos: Tuple[int, int], font=None, colour=TEXT,
                   anchor: str = "center") -> None:
        """Blit text at screen position with anchor alignment."""
        f = font or self._font_small
        rendered = f.render(text, True, colour)
        tx, ty = pos

        if "l" in anchor:
            tx -= rendered.get_width()
        if "t" in anchor:
            ty -= rendered.get_height()
        elif "b" in anchor:
            ty -= rendered.get_height()

        surface.blit(rendered, (tx, ty))

    # ── main render ────────────────────────────────────────────────────

    def render(self, surface: pygame.Surface, game: Any, time: float = 0.0) -> None:
        """Draw all map layers onto *surface* in z-order."""
        visible = self.get_visible_hexes()

        # Track unit movement for animations
        self._track_unit_movement(game)

        player_civ = game.player_civ.name

        # --- Build civ ownership map ---
        civ_hexes: Dict[str, set] = {}
        for city in game.cities.values():
            owner = getattr(city, "owner", "")
            if not owner:
                continue
            hex_pos = getattr(city, "hex", None) or getattr(city, "position", None)
            if hex_pos is None:
                continue
            if owner not in civ_hexes:
                civ_hexes[owner] = set()
            civ_hexes[owner].add(hex_pos)

        # Expand ownership to adjacent hexes for territory display
        territory: Dict[str, set] = {}
        for owner, hexes in civ_hexes.items():
            territory[owner] = set(hexes)
            for hx, hy in hexes:
                for dq, dr in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]:
                    territory[owner].add((hx + dq, hy + dr))

        # --- 1. Terrain tiles ---
        zoom = getattr(self.camera, "zoom", 1.0)
        for hx, hy in visible:
            tile = self.hex_map.get_tile(hx, hy)
            wx, wy = self.hex_to_world(hx, hy)
            sx, sy = self.camera.world_to_screen(wx, wy)

            # Skip if outside screen bounds
            if not (0 <= sx < surface.get_width() and 0 <= sy < surface.get_height()):
                continue

            terrain_name = tile.terrain.name
            # Scale tile to match current zoom level
            zoom_tag = self.tile_atlas._nearest_zoom(zoom)
            target_size = int(HEX_SIZE * 2 * zoom)
            if target_size < 4:
                target_size = 4
            cache_key = (terrain_name, zoom_tag)
            if cache_key in self._tile_zoom_cache:
                tile_surface = self._tile_zoom_cache[cache_key]
            else:
                base_tile = self.tile_atlas.get_tile(terrain_name, zoom)
                if base_tile.get_width() < 10:
                    # Error indicator from atlas
                    tile_surface = base_tile
                else:
                    tile_surface = pygame.transform.smoothscale(base_tile, (target_size, target_size))
                self._tile_zoom_cache[cache_key] = tile_surface

            # Center tile on hex center using actual tile dimensions
            csx = sx - tile_surface.get_width() // 2
            csy = sy - tile_surface.get_height() // 2

            # If atlas doesn't have the tile, fallback to colour fill
            if tile_surface.get_width() < 10:  # error indicator
                pygame.draw.polygon(
                    surface,
                    TERRAIN_COLORS.get(terrain_name, (128, 128, 128)),
                    [(int(p[0]), int(p[1])) for p in zip(
                        self._hex_vertices(csx, csy, zoom)[0::2],
                        self._hex_vertices(csx, csy, zoom)[1::2],
                    )],
                )
            else:
                surface.blit(tile_surface, (csx, csy))

        # --- 1b. Hex grid lines (subtle dark outlines) ---
        for hx, hy in visible:
            verts = self._screen_hex_points(hx, hy)
            self._draw_hex_outline(surface, verts, (0, 0, 0), width=1)

        # --- 1c. Territory borders ---
        territory_colors = {
            player_civ: (197, 160, 89),  # gold for player
        }
        for civ_name, civ_obj in game.civilizations.items():
            if civ_name != player_civ:
                territory_colors[civ_name] = (178, 58, 58)  # red for AI

        for hx, hy in visible:
            owner = None
            for civ_name, hex_set in territory.items():
                if (hx, hy) in hex_set:
                    owner = civ_name
                    break
            if owner and owner in territory_colors:
                verts = self._screen_hex_points(hx, hy)
                self._draw_hex_outline(surface, verts, territory_colors[owner], width=1)

        # --- 2. Resource icons ---
        for hx, hy in visible:
            tile = self.hex_map.get_tile(hx, hy)
            resource = getattr(tile, "resource", None)
            if resource is None:
                continue
            wx, wy = self.hex_to_world(hx, hy)
            sx, sy = self.camera.world_to_screen(wx, wy)
            if not (0 <= sx < surface.get_width() and 0 <= sy < surface.get_height()):
                continue

            short = resource.name[:4].lower()
            self._blit_text(surface, short, (sx, sy - HEX_SIZE + 6),
                            font=self._font_small, colour=GOLD)

        # --- 3. River indicators ---
        for hx, hy in visible:
            tile = self.hex_map.get_tile(hx, hy)
            if not getattr(tile, "has_river", False):
                continue
            wx, wy = self.hex_to_world(hx, hy)
            sx, sy = self.camera.world_to_screen(wx, wy)
            if not (0 <= sx < surface.get_width() and 0 <= sy < surface.get_height()):
                continue

            pygame.draw.circle(surface, (70, 130, 180), (sx, sy), 6)

        # --- 4. City markers ---
        player_name = game.player_civ.name
        cities = getattr(game, "cities", {})
        for city_id, city in cities.items():
            city_hex = getattr(city, "hex", (0, 0))
            hx, hy = city_hex
            if (hx, hy) not in visible:
                continue
            wx, wy = self.hex_to_world(hx, hy)
            sx, sy = self.camera.world_to_screen(wx, wy)
            if not (0 <= sx < surface.get_width() and 0 <= sy < surface.get_height()):
                continue

            is_player = getattr(city, "owner", "") == player_name
            city_colour = GREEN if is_player else RED

            # City sprite
            pop = getattr(city, "population", 1)
            tier = self._get_city_tier(pop)
            sprite = self._city_sprites.get(tier)
            if sprite:
                sprite_size = sprite.get_width()
                offset_x = sx - sprite_size // 2
                offset_y = sy - sprite_size // 2
                surface.blit(sprite, (offset_x, offset_y))
            else:
                # Fallback: circle marker
                radius = max(8, HEX_SIZE // 4)
                pygame.draw.circle(surface, city_colour, (sx, sy), radius, 2)

            # Name + pop
            name = getattr(city, "name", city_id)
            self._blit_text(surface, str(name), (sx, sy - HEX_SIZE - 4),
                            font=self._font_med, colour=GOLD)
            self._blit_text(surface, f"P:{pop}", (sx, sy + HEX_SIZE + 8),
                            font=self._font_small, colour=SUBTLE)

        # --- 5. Unit markers ---
        units = getattr(game, "units", {})
        total_units = len(units)
        units_drawn = 0
        for unit_id, unit in units.items():
            unit_hex = getattr(unit, "position", (0, 0))
            hx, hy = unit_hex
            if (hx, hy) not in visible:
                continue
            
            wx, wy = self.hex_to_world(hx, hy)
            sx, sy = self.camera.world_to_screen(wx, wy)
            if not (0 <= sx < surface.get_width() and 0 <= sy < surface.get_height()):
                continue
            
            units_drawn += 1
            wx, wy = self.hex_to_world(hx, hy)
            sx, sy = self.camera.world_to_screen(wx, wy)
            if not (0 <= sx < surface.get_width() and 0 <= sy < surface.get_height()):
                continue

            # Check for animated movement — use interpolated position
            anim_pos = self._get_animated_position(unit_id)
            if anim_pos:
                sx, sy = anim_pos

            is_player = getattr(unit, "owner", "") == player_name
            unit_colour = GREEN if is_player else RED

            # Offset units on same hex slightly
            offset_x = 0
            offset_y = 0
            for other_id, other in units.items():
                if other_id != unit_id and getattr(other, "position", (0, 0)) == unit_hex:
                    offset_x += 8
                    offset_y += 8

            ox, oy = sx + offset_x, sy + offset_y
            size = max(6, HEX_SIZE // 5)

            # Unit sprite
            unit_type = getattr(unit, "unit_type", None) or getattr(unit, "type", "?")
            # Try exact match, then lowercase key lookup
            sprite = self._unit_sprites.get(unit_type) or self._unit_sprites.get(unit_type.lower())
            if sprite:
                sprite_size = sprite.get_width()
                sprite_offset = sprite_size // 2
                surface.blit(sprite, (ox - sprite_offset, oy - sprite_offset))
            else:
                # Fallback: square marker
                pygame.draw.rect(
                    surface, unit_colour,
                    (ox - size, oy - size, size * 2, size * 2),
                )

            # Type label
            type_label = getattr(unit, "unit_type", "?")[:3].upper()
            self._blit_text(surface, type_label, (ox, oy - size - 6),
                            font=self._font_small, colour=TEXT)

            # HP bar
            hp = getattr(unit, "hp", 1)
            max_hp = getattr(unit, "max_hp", 1)
            bar_w = size * 2
            bar_h = 3
            bar_x = ox - size
            bar_y = oy + size + 2
            pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h))
            hp_ratio = max(0, hp / max_hp)
            hp_colour = GREEN if hp_ratio > 0.5 else GOLD if hp_ratio > 0.25 else RED
            pygame.draw.rect(
                surface, hp_colour,
                (bar_x, bar_y, int(bar_w * hp_ratio), bar_h),
            )

 

        # --- 6. Fog of war ---
        fog_surf = pygame.Surface(
            (surface.get_width(), surface.get_height()), pygame.SRCALPHA
        )
        for hx, hy in visible:
            if not game.fog.is_explored(hx, hy):
                wx, wy = self.hex_to_world(hx, hy)
                sx, sy = self.camera.world_to_screen(wx, wy)
                verts = self._screen_hex_points(hx, hy)
                self._draw_hex_fill(fog_surf, verts, (0, 0, 0), alpha=180)
        surface.blit(fog_surf, (0, 0))

        # --- 7. Selection highlight (pulsing gold) ---
        if self.selected_hex:
            hx, hy = self.selected_hex
            if (hx, hy) in visible:
                verts = self._screen_hex_points(hx, hy)
                # Pulsing glow with sin wave
                pulse_alpha = int(120 + 80 * math.sin(time * 4))
                pulse_verts = self._hex_vertices(
                    verts[0] + HEX_SIZE * zoom * 0.15,
                    verts[1] + HEX_SIZE * zoom * 0.15,
                    zoom,
                )
                self._draw_hex_fill(surface, pulse_verts, GOLD, alpha=pulse_alpha)
                self._draw_hex_outline(surface, verts, GOLD, width=3)

        # --- 8. Move range ---
        for hx, hy in self.move_range:
            if (hx, hy) in visible:
                verts = self._screen_hex_points(hx, hy)
                self._draw_hex_fill(surface, verts, BLUE, alpha=50)
                self._draw_hex_outline(surface, verts, BLUE, width=2)

        # --- 9. Attack range ---
        for hx, hy in self.attack_range:
            if (hx, hy) in visible:
                verts = self._screen_hex_points(hx, hy)
                self._draw_hex_fill(surface, verts, RED, alpha=50)
                self._draw_hex_outline(surface, verts, RED, width=2)

        # --- 10. Hover highlight ---
        if self.hovered_hex:
            hx, hy = self.hovered_hex
            if (hx, hy) in visible:
                verts = self._screen_hex_points(hx, hy)
                self._draw_hex_outline(surface, verts, (255, 255, 255), width=2)
