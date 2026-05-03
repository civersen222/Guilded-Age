"""
CivKings - Enhanced Map Rendering (gui_map.py)
Handles hex grid rendering, minimap, tooltips, zoom/pan, and selection highlighting.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
import math
from collections import deque

from game_data import TerrainType, TERRAIN_MOVEMENT_COST, ResourceType
from hex_map import HexTile, WorldMap


class TileHighlight(Enum):
    """Highlight states for tiles."""
    NONE = "none"
    SELECTED = "selected"
    HOVER = "hover"
    MOVE_RANGE = "move_range"
    ATTACK_RANGE = "attack_range"
    ENEMY_TERRITORY = "enemy_territory"


class HexGridRenderer:
    """Handles rendering of hex grid tiles with terrain, resources, and features."""
    
    # Terrain color palette - Dark Fantasy theme
    TERRAIN_COLORS = {
        TerrainType.PLAINS: "#3d4d3d",
        TerrainType.GRASSLAND: "#4a5d4a",
        TerrainType.FOREST: "#2d4a2d",
        TerrainType.HILLS: "#5a5a3d",
        TerrainType.MOUNTAIN: "#4a4a4a",
        TerrainType.DESERT: "#6a5a3a",
        TerrainType.TUNDRA: "#5a6a6a",
        TerrainType.WATER_COAST: "#2a4a6a",
        TerrainType.OCEAN: "#1a3a5a",
    }
    
    # Resource icons (unicode)
    RESOURCE_ICONS = {
        ResourceType.BONUS_WHEAT: "🌾",
        ResourceType.BONUS_FISH: "🐟",
        ResourceType.BONUS_GAME: "🦌",
        ResourceType.LUXURY_SILK: "🧣",
        ResourceType.LUXURY_SPICES: "🌶",
        ResourceType.LUXURY_IVORY: "🦴",
        ResourceType.STRATEGIC_IRON: "⚙",
        ResourceType.STRATEGIC_HORSES: "🐴",
        ResourceType.STRATEGIC_OIL: "🛢",
    }
    
    # Highlight overlay colors - Dark Fantasy theme
    HIGHLIGHT_COLORS = {
        TileHighlight.SELECTED: "#c5a059",
        TileHighlight.HOVER: "#ffffff",
        TileHighlight.MOVE_RANGE: "#4caf50",
        TileHighlight.ATTACK_RANGE: "#ff9800",
        TileHighlight.ENEMY_TERRITORY: "#b23a3a",
        TileHighlight.ENEMY_TERRITORY: "#f44336",
    }
    
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.hex_items: Dict[Tuple[int, int], List[int]] = {}
        self.selected_tile: Optional[Tuple[int, int]] = None
        self.hovered_tile: Optional[Tuple[int, int]] = None
        self.highlighted_tiles: Dict[Tuple[int, int], TileHighlight] = {}
        self.rendered_tiles: Set[Tuple[int, int]] = set()
        self.dirty = True
        
    def mark_dirty(self):
        """Mark the map as needing re-render."""
        self.dirty = True
        
    def render_map(self, tiles: Dict[Tuple[int, int], HexTile], 
                   zoom: float = 1.0,
                   camera_offset: Tuple[int, int] = (0, 0)):
        """Render all visible tiles."""
        if not self.dirty:
            return
            
        self.canvas.delete("all")
        self.hex_items.clear()
        self.rendered_tiles.clear()
        
        if not tiles:
            return
        
        # Calculate visible region based on zoom and camera
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width == 0 or canvas_height == 0:
            return
            
        center_x = canvas_width / 2 + camera_offset[0]
        center_y = canvas_height / 2 + camera_offset[1]
        
        # Calculate hex size based on zoom
        hex_size = 20 * zoom  # Base hex radius
        
        # Only render tiles that could be visible
        visible_tiles = self._get_visible_tiles(tiles, center_x, center_y, canvas_width, canvas_height, hex_size)
        
        for tile_coord in visible_tiles:
            tile = tiles.get(tile_coord)
            if not tile:
                continue
                
            q, r = tile_coord
            
            # Calculate pixel position
            hex_x = center_x + q * hex_size * 1.5
            hex_y = center_y + r * hex_size * math.sqrt(3)
            
            # Skip if outside canvas
            if (hex_x < -hex_size or hex_x > canvas_width + hex_size or
                hex_y < -hex_size * 2 or hex_y > canvas_height + hex_size * 2):
                continue
                
            # Draw hex tile
            pts = self._hex_points(hex_x, hex_y, hex_size)
            tile_color = self.TERRAIN_COLORS.get(tile.terrain, "#333333")
            
            # Adjust color for water depth
            if tile.terrain in (TerrainType.WATER_COAST, TerrainType.OCEAN):
                # Make deeper water darker
                depth_factor = 0.7 if tile.terrain == TerrainType.OCEAN else 0.9
                tile_color = self._adjust_color_brightness(tile_color, depth_factor)
            
            # Draw terrain
            tag_id = self.canvas.create_polygon(
                pts, fill=tile_color, outline="#121212", width=1,
                tags=(str(q), str(r), "tile")
            )
            
            # Add resource icon if present
            if tile.resource:
                icon = self.RESOURCE_ICONS.get(tile.resource, "")
                if icon:
                    self.canvas.create_text(
                        hex_x, hex_y - 15,
                        text=icon,
                        font=("Segoe UI", max(8, int(10 * zoom))),
                        fill="#ffffff",
                        tags=(str(q), str(r), "resource")
                    )
            
            # Add city marker
            if tile.city:
                city_marker = self.canvas.create_text(
                    hex_x, hex_y,
                    text="★",
                    font=("Segoe UI", max(14, int(18 * zoom)), "bold"),
                    fill="#ffd700",
                    tags=(str(q), str(r), "city")
                )
            
            # Add unit marker
            if tile.unit:
                unit_marker = self.canvas.create_text(
                    hex_x, hex_y,
                    text="●",
                    font=("Segoe UI", max(10, int(14 * zoom)), "bold"),
                    fill="#ff6b6b",
                    tags=(str(q), str(r), "unit")
                )
            
            # Store the main tile item
            self.hex_items[(q, r)] = [tag_id]
            self.rendered_tiles.add((q, r))
        
        self.dirty = False
        
    def _get_visible_tiles(self, tiles: Dict[Tuple[int, int], HexTile],
                          center_x: float, center_y: float,
                          canvas_width: float, canvas_height: float,
                          hex_size: float) -> Set[Tuple[int, int]]:
        """Calculate which tiles are visible on screen."""
        visible = set()
        
        # Calculate visible hex range
        max_q = (canvas_width / 2 + hex_size) / (hex_size * 1.5)
        max_r = (canvas_height / 2 + hex_size * 2) / (hex_size * math.sqrt(3))
        
        for (q, r), tile in tiles.items():
            hex_x = center_x + q * hex_size * 1.5
            hex_y = center_y + r * hex_size * math.sqrt(3)
            
            if (abs(hex_x - center_x) < max_q * hex_size and
                abs(hex_y - center_y) < max_r * hex_size):
                visible.add((q, r))
                
        return visible
    
    def _hex_points(self, cx: float, cy: float, r: float) -> List[Tuple[float, float]]:
        """Calculate hexagon points for a flat-topped hex."""
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))
        return points
    
    def _adjust_color_brightness(self, color: str, factor: float) -> str:
        """Adjust brightness of a hex color."""
        # Convert hex to RGB
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        
        # Adjust brightness
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def set_highlight(self, tile_coord: Tuple[int, int], highlight: TileHighlight):
        """Set highlight on a tile."""
        self.highlighted_tiles[tile_coord] = highlight
        self.dirty = True
        
    def clear_highlights(self):
        """Clear all highlights."""
        self.highlighted_tiles.clear()
        self.dirty = True
        
    def clear_selection(self):
        """Clear current selection."""
        self.selected_tile = None
        self.clear_highlights()
        self.dirty = True
        
    def select_tile(self, tile_coord: Tuple[int, int]):
        """Select a tile and highlight it."""
        self.clear_highlights()
        self.selected_tile = tile_coord
        self.set_highlight(tile_coord, TileHighlight.SELECTED)
        
    def highlight_tiles(self, tiles: Dict[Tuple[int, int], TileHighlight]):
        """Highlight multiple tiles."""
        self.highlighted_tiles.update(tiles)
        self.dirty = True
        
    def get_tile_at_pixel(self, x: float, y: float) -> Optional[Tuple[int, int]]:
        """Get the hex tile coordinate at a pixel position."""
        # Find the closest hex to the mouse position
        min_dist = float('inf')
        closest_tile = None
        
        for (q, r), item_list in self.hex_items.items():
            if not item_list:
                continue
                
            bbox = self.canvas.bbox(item_list[0])
            if not bbox:
                continue
                
            # Calculate center of hex
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist < min_dist:
                min_dist = dist
                closest_tile = (q, r)
                
        return closest_tile


class MinimapRenderer:
    """Renders a small overview map."""
    
    def __init__(self, canvas: tk.Canvas, map_width: int, map_height: int):
        self.canvas = canvas
        self.map_width = map_width
        self.map_height = map_height
        self.minimap_items: Dict[Tuple[int, int], int] = {}
        self.camera_rect: Optional[int] = None
        
    def render_minimap(self, tiles: Dict[Tuple[int, int], HexTile],
                      camera_view: Tuple[int, int, int, int] = (0, 0, 100, 100)):
        """Render the minimap with camera view rectangle."""
        self.canvas.delete("all")
        self.minimap_items.clear()
        
        # Calculate scaling factor
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width == 0 or canvas_height == 0:
            return
            
        scale_x = canvas_width / self.map_width
        scale_y = canvas_height / self.map_height
        scale = min(scale_x, scale_y) * 0.9
        
        # Draw tiles
        for (q, r), tile in tiles.items():
            if not (0 <= q < self.map_width and 0 <= r < self.map_height):
                continue
                
            x = q * scale
            y = r * scale
            
            color = HexGridRenderer.TERRAIN_COLORS.get(tile.terrain, "#333333")
            self.minimap_items[(q, r)] = self.canvas.create_rectangle(
                x, y, x + scale, y + scale,
                fill=color, outline="#000000", width=0
            )
            
        # Draw camera view rectangle
        cam_q, cam_r, cam_w, cam_h = camera_view
        cam_x = cam_q * scale
        cam_y = cam_r * scale
        cam_w_pixels = cam_w * scale
        cam_h_pixels = cam_h * scale
        
        self.camera_rect = self.canvas.create_rectangle(
            cam_x, cam_y, cam_x + cam_w_pixels, cam_y + cam_h_pixels,
            outline="#ffffff", width=2
        )


class HoverTooltip:
    """Shows tooltip information when hovering over tiles or UI elements."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.tooltip: Optional[tk.Toplevel] = None
        self.hovered_widget: Optional[tk.Widget] = None
        self.tooltip_text: str = ""
        
    def show(self, widget: tk.Widget, text: str):
        """Show tooltip for a widget."""
        self.hide()
        
        self.tooltip_text = text
        self.hovered_widget = widget
        
        # Create tooltip window
        self.tooltip = tk.Toplevel(widget)
        self.tooltip.wm_overrideredirect(True)  # No window decorations
        self.tooltip.wm_geometry(f"+{widget.winfo_rootx() + 10}+{widget.winfo_rooty() + widget.winfo_height() + 5}")
        
        # Add tooltip content
        frame = tk.Frame(self.tooltip, bg="#121212", bd=1, relief=tk.RAISED)
        frame.pack()
        
        tk.Label(frame, text=text, bg="#121212", fg="#e0d6c2",
                font=("Segoe UI", 9), padx=5, pady=2).pack()
        
        # Update tooltip position on mouse move
        def update_position(event):
            if self.tooltip:
                self.tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        
        widget.bind("<Motion>", update_position)
        
    def hide(self):
        """Hide tooltip."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
        self.hovered_widget = None


class ZoomPanController:
    """Handles zoom and pan controls for the map."""
    
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.zoom = 1.0
        self.camera_offset = (0, 0)
        self.is_panning = False
        self.last_mouse_pos = (0, 0)
        
        # Bind events
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<ButtonPress-3>", self._start_pan)
        self.canvas.bind("<B3-Motion>", self._do_pan)
        self.canvas.bind("<ButtonRelease-3>", self._end_pan)
        
    @property
    def zoom_level(self) -> float:
        return self.zoom
        
    @zoom_level.setter
    def zoom_level(self, value: float):
        self.zoom = max(0.2, min(3.0, value))  # Clamp between 0.2x and 3x
        
    def get_camera_view(self) -> Tuple[int, int]:
        """Get current camera position."""
        return self.camera_offset
        
    def set_camera_position(self, offset: Tuple[int, int]):
        """Set camera position."""
        self.camera_offset = offset
        
    def reset_view(self):
        """Reset zoom and camera position."""
        self.zoom = 1.0
        self.camera_offset = (0, 0)
        
    def _on_zoom(self, event):
        """Handle mouse wheel zoom."""
        if event.num == 4:  # Scroll up
            self.zoom *= 1.1
        elif event.num == 5:  # Scroll down
            self.zoom *= 0.9
            
        self.zoom = max(0.2, min(3.0, self.zoom))
        return "break"
        
    def _start_pan(self, event):
        """Start panning."""
        self.is_panning = True
        self.last_mouse_pos = (event.x, event.y)
        self.canvas.config(cursor="fleur")
        
    def _do_pan(self, event):
        """Do panning."""
        if not self.is_panning:
            return
            
        dx = event.x - self.last_mouse_pos[0]
        dy = event.y - self.last_mouse_pos[1]
        
        self.camera_offset = (
            self.camera_offset[0] + dx,
            self.camera_offset[1] + dy
        )
        
        self.last_mouse_pos = (event.x, event.y)
        
    def _end_pan(self, event):
        """End panning."""
        self.is_panning = False
        self.canvas.config(cursor="arrow")
        return "break"


class MapCanvas(tk.Canvas):
    """Main map canvas with integrated rendering and interaction."""
    
    def __init__(self, master, game_state=None):
        super().__init__(master, bg="#0a0b0d", highlightthickness=0)
        
        self.game_state = game_state
        self.renderer = HexGridRenderer(self)
        self.minimap_renderer = None
        self.tooltip = HoverTooltip(master)
        self.zoom_pan = ZoomPanController(self)
        
        # Selection state
        self.selected_tile: Optional[Tuple[int, int]] = None
        self.hovered_tile: Optional[Tuple[int, int]] = None
        
        # Unit selection and movement state
        self.selected_unit_tile: Optional[Tuple[int, int]] = None
        self.selected_unit_name: Optional[str] = None
        self.moveable_tiles: Set[Tuple[int, int]] = set()
        
        # Bind events
        self.bind("<Button-1>", self._on_click)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Double-Button-1>", self._on_double_click)
        
    def set_game_state(self, game_state):
        """Set the game state reference."""
        self.game_state = game_state
        
    def render(self, tiles: Dict[Tuple[int, int], HexTile], 
              zoom: Optional[float] = None,
              camera_offset: Optional[Tuple[int, int]] = None):
        """Render the map."""
        if zoom is not None:
            self.zoom_pan.zoom_level = zoom
        if camera_offset is not None:
            self.zoom_pan.camera_offset = camera_offset
            
        self.renderer.render_map(
            tiles,
            self.zoom_pan.zoom_level,
            self.zoom_pan.camera_offset
        )
        
    def _on_click(self, event):
        """Handle map click."""
        if self.game_state is None:
            return
        
        tile_coord = self.renderer.get_tile_at_pixel(event.x, event.y)
        if tile_coord:
            self.selected_tile = tile_coord
            tile = self.game_state.map.get_tile(tile_coord[0], tile_coord[1])
            
            # If tile has an owned unit, select it for movement
            if tile and tile.unit:
                unit_name = tile.unit
                unit = self.game_state.units.get(unit_name)
                if unit and unit.owner == self.game_state.state.current_player:
                    if unit.moves_left > 0:
                        self.selected_unit_tile = tile_coord
                        self.selected_unit_name = unit_name
                        self.moveable_tiles = self._get_moveable_tiles(
                            tile_coord, unit.moves_left
                        )
                        self._render_with_move_highlight()
                        if hasattr(self.game_state, 'on_unit_selected'):
                            self.game_state.on_unit_selected(tile_coord, unit)
                        return
            
            # If we had a unit selected and clicked a moveable tile, move it
            if self.selected_unit_tile and tile_coord in self.moveable_tiles:
                # Calculate movement cost for the destination tile
                dest_tile = self.game_state.map.get_tile(tile_coord[0], tile_coord[1])
                movement_cost = TERRAIN_MOVEMENT_COST.get(dest_tile.terrain, 1) if dest_tile else 1
                
                old_tile = self.game_state.map.get_tile(
                    self.selected_unit_tile[0], self.selected_unit_tile[1]
                )
                if old_tile:
                    old_tile.unit = None
                tile.unit = self.selected_unit_name
                # Update unit position and consume movement points
                unit = self.game_state.units.get(self.selected_unit_name)
                if unit:
                    unit.position = tile_coord
                    unit.moves_left = max(0, unit.moves_left - movement_cost)
                self.selected_unit_tile = None
                self.selected_unit_name = None
                self.moveable_tiles = set()
                self._render_with_move_highlight()
                if hasattr(self.game_state, 'on_unit_moved'):
                    self.game_state.on_unit_moved(tile_coord)
                return
            
            # Normal tile selection
            self.selected_unit_tile = None
            self.moveable_tiles = set()
            self.renderer.select_tile(tile_coord)
            self.render(self.game_state.map.tiles if self.game_state else {})
            
            # Notify game state
            if hasattr(self.game_state, 'on_tile_selected'):
                self.game_state.on_tile_selected(tile_coord)
    def _on_motion(self, event):
        """Handle mouse motion."""
        tile_coord = self.renderer.get_tile_at_pixel(event.x, event.y)
        if tile_coord:
            self.hovered_tile = tile_coord
            self.renderer.set_highlight(tile_coord, TileHighlight.HOVER)
            self.render(self.game_state.map.tiles if self.game_state else {})
            
            # Show tooltip
            if self.game_state:
                tile = self.game_state.map.get_tile(tile_coord[0], tile_coord[1])
                if tile:
                    tooltip_text = self._get_tile_tooltip(tile)
                    self.tooltip.show(self, tooltip_text)
                    
    def _on_leave(self, event):
        """Handle mouse leaving canvas."""
        self.hovered_tile = None
        self.renderer.clear_highlights()
        self.tooltip.hide()
        self.render(self.game_state.map.tiles if self.game_state else {})
        
    def _on_double_click(self, event):
        """Handle double click."""
        if self.game_state is None:
            return
            
        tile_coord = self.renderer.get_tile_at_pixel(event.x, event.y)
        if tile_coord:
            tile = self.game_state.map.get_tile(tile_coord[0], tile_coord[1])
            if tile and tile.city:
                # Open city management
                if hasattr(self.game_state, 'on_city_double_click'):
                    self.game_state.on_city_double_click(tile.city)
                    
    def _get_tile_tooltip(self, tile: HexTile) -> str:
        """Generate tooltip text for a tile."""
        lines = [f"Tile ({tile.q}, {tile.r})"]
        
        # Terrain type
        terrain_name = tile.terrain.value.replace("_", " ").title()
        lines.append(f"Terrain: {terrain_name}")
        
        # Resources
        if tile.resource:
            resource_name = tile.resource.value.replace("_", " ").title()
            lines.append(f"Resource: {resource_name}")
            
        # City
        if tile.city:
            lines.append(f"City: {tile.city}")
            
        # Unit
        if tile.unit:
            lines.append(f"Unit: {tile.unit}")
            
        # Coordinates
        lines.append(f"Position: {tile.position}")
        
        return "\n".join(lines)
        
    def highlight_move_range(self, tiles: Dict[Tuple[int, int], TileHighlight]):
        """Highlight tiles with move range."""
        self.renderer.highlight_tiles(tiles)
        self.render(self.game_state.map.tiles if self.game_state else {})
        
    def highlight_attack_range(self, tiles: Dict[Tuple[int, int], TileHighlight]):
        """Highlight tiles with attack range."""
        self.renderer.highlight_tiles(tiles)
        self.render(self.game_state.map.tiles if self.game_state else {})
        
    def clear_highlights(self):
        """Clear all highlights."""
        self.renderer.clear_highlights()
        self.render(self.game_state.map.tiles if self.game_state else {})
        
    def _get_moveable_tiles(self, start_coord: Tuple[int, int], moves_left: int) -> Set[Tuple[int, int]]:
        """BFS to find all tiles reachable with the given moves left, respecting terrain costs."""
        moveable = set()
        # (coord, remaining_moves)
        queue = deque([(start_coord, moves_left)])
        visited = {start_coord}
        
        while queue:
            (q, r), remaining = queue.popleft()
            if remaining <= 0:
                continue
            
            # Get neighbors
            for dq, dr in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]:
                nq, nr = q + dq, r + dr
                if (nq, nr) in visited:
                    continue
                
                tile = self.game_state.map.get_tile(nq, nr)
                if not tile:
                    continue
                
                # Check if tile is passable (no mountains for most units)
                if tile.terrain == TerrainType.MOUNTAIN:
                    continue
                
                # Check if tile is water (unless unit can move on water)
                if tile.terrain in (TerrainType.WATER_COAST, TerrainType.OCEAN):
                    continue
                
                # Calculate movement cost
                movement_cost = TERRAIN_MOVEMENT_COST.get(tile.terrain, 1)
                if remaining >= movement_cost:
                    moveable.add((nq, nr))
                    visited.add((nq, nr))
                    queue.append(((nq, nr), remaining - movement_cost))
        
        return moveable
        
    def _render_with_move_highlight(self):
        """Re-render the map with moveable tiles highlighted."""
        self.renderer.clear_highlights()
        
        # Re-add selection highlight
        if self.selected_tile:
            self.renderer.set_highlight(self.selected_tile, TileHighlight.SELECTED)
        
        # Re-add hover highlight
        if self.hovered_tile:
            self.renderer.set_highlight(self.hovered_tile, TileHighlight.HOVER)
        
        # Add move range highlights
        if self.moveable_tiles:
            move_highlights = {coord: TileHighlight.MOVE_RANGE for coord in self.moveable_tiles}
            self.renderer.highlight_tiles(move_highlights)
        
        self.render(self.game_state.map.tiles if self.game_state else {})
        
    def get_selected_tile(self) -> Optional[Tuple[int, int]]:
        """Get currently selected tile."""
        return self.selected_tile
        
    def get_hovered_tile(self) -> Optional[Tuple[int, int]]:
        """Get currently hovered tile."""
        return self.hovered_tile
