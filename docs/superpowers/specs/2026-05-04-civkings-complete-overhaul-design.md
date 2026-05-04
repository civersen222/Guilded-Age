# CivKings Complete Overhaul: Pygame Migration + Game Completion

**Date**: 2026-05-04
**Status**: Approved
**Scope**: Full GUI rewrite (tkinter -> Pygame-ce), AI art asset pipeline (ComfyUI), and completion of all game mechanics to production quality.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Phase 0: ComfyUI Art Asset Pipeline](#2-phase-0-comfyui-art-asset-pipeline)
3. [Phase 1: Pygame Core Scaffold](#3-phase-1-pygame-core-scaffold)
4. [Phase 2: Hex Map Renderer](#4-phase-2-hex-map-renderer)
5. [Phase 3: UI Panels and Widgets](#5-phase-3-ui-panels-and-widgets)
6. [Phase 4: Popups and Dialogs](#6-phase-4-popups-and-dialogs)
7. [Phase 5: Sound and Visual Effects](#7-phase-5-sound-and-visual-effects)
8. [Phase 6: Game Engine Fixes](#8-phase-6-game-engine-fixes)
9. [Phase 7: Core Missing Mechanics](#9-phase-7-core-missing-mechanics)
10. [Phase 8: Advanced CK-Style Mechanics](#10-phase-8-advanced-ck-style-mechanics)
11. [Phase 9: Advanced Civ-Style Mechanics](#11-phase-9-advanced-civ-style-mechanics)
12. [Phase 10: AI Overhaul](#12-phase-10-ai-overhaul)
13. [Phase 11: Polish, Balance, Tutorial](#13-phase-11-polish-balance-tutorial)
14. [Phase 12: Cleanup and Final Integration](#14-phase-12-cleanup-and-final-integration)
15. [File Manifest](#15-file-manifest)
16. [Integration Verification Checklist](#16-integration-verification-checklist)

---

## 1. Architecture Overview

### Current State

```
Engine Layer (KEEP - 12K lines, works correctly):
  game.py, hex_map.py, city.py, military.py, combat.py, tech.py,
  economy.py, diplomacy.py, diplomacy_extended.py, simulation.py,
  ai.py, events.py, faction_system.py, religion.py, victory.py,
  save_system.py, game_manager.py, court.py, plots.py,
  city_growth.py, unit_enhancements.py, tax_system.py,
  happiness_system.py, stability_system.py, gold_management.py,
  market_simulation.py, external_trade_routes.py, game_data.py,
  tech_policies.py, research_tree.py, character_deepening.py

GUI Layer (DELETE AND REWRITE - 3,900 lines, broken):
  gui.py, gui_map.py, gui_panels.py, gui_popups.py,
  gui_combat.py, victory_ui.py, visual_effects.py, sound_effects.py
```

### Target Architecture

```
Engine Layer (UNCHANGED except new features added):
  [all existing files] + new mechanics files

Pygame GUI Layer (NEW):
  pygame_gui/
    __init__.py          # Package init
    app.py               # Main game loop, window, state machine
    theme.json           # Dark fantasy pygame_gui theme
    screens/
      __init__.py
      main_menu.py       # Title screen, new game, load game
      game_screen.py     # Main gameplay screen (coordinator)
      new_game_dialog.py # Civ/difficulty selection
    map/
      __init__.py
      hex_renderer.py    # Hex tile image rendering with sprites
      camera.py          # Pan, zoom, viewport culling
      minimap.py         # Corner minimap
      fog_of_war.py      # Fog overlay compositing
      tile_atlas.py      # Sprite sheet loading from ComfyUI assets
      highlights.py      # Selection, movement range, attack range
      animations.py      # Unit movement, combat effects on map
    panels/
      __init__.py
      resource_bar.py    # Top bar: food, production, gold, science, faith, turn
      city_panel.py      # City list sidebar
      unit_panel.py      # Unit list sidebar
      event_log.py       # Scrollable event log
      tech_panel.py      # Current research display
      turn_summary.py    # Start-of-turn notification queue
      action_bar.py      # Bottom bar: unit actions (move, attack, fortify, skip)
    popups/
      __init__.py
      production.py      # City production queue management
      tech_tree.py       # Full tech tree visualization
      diplomacy.py       # Diplomatic relations and actions
      dynasty.py         # Character/dynasty info
      combat_result.py   # Combat outcome display
      city_detail.py     # Detailed city view (yields, citizens, buildings)
      victory.py         # Victory screen
      encyclopedia.py    # In-game reference for all concepts
      event_choice.py    # Event popup with player choices
      trade.py           # Trade route management
    effects/
      __init__.py
      particles.py       # Particle effects (combat, celebrations)
      animations.py      # Tweened animations (unit slide, fade)
      transitions.py     # Screen transitions
    audio/
      __init__.py
      sound_manager.py   # Sound effect loading and playback
      music_manager.py   # Era-based background music

  assets/
    tiles/               # ComfyUI-generated hex terrain tiles (PNG)
      atlas.png          # Packed sprite sheet
      atlas.json         # Tile coordinates in atlas
    units/               # Unit icons (PNG with alpha)
    buildings/           # Building/district icons
    ui/                  # UI panel backgrounds, button styles
    sounds/
      ui/                # Click, hover, confirm, cancel
      combat/            # Sword clash, arrow, siege
      events/            # Notification chimes per type
      ambient/           # Wind, birds, water
    music/
      ancient.ogg        # Era-specific background tracks
      medieval.ogg
      renaissance.ogg
      industrial.ogg
      modern.ogg
```

### Key Design Decisions

1. **pygame-ce** (community edition), not upstream pygame. Better performance, active maintenance, Python 3.14 support.
2. **pygame_gui** for all UI widgets. JSON theme file for dark fantasy palette.
3. **Sprite-based hex map** using `LayeredDirty` groups for dirty-rect rendering.
4. **Game loop at 30 FPS** (turn-based game doesn't need 60). Animations interpolated with delta-time.
5. **Engine stays pure Python with zero pygame imports.** GUI calls into engine, never the reverse.
6. **ComfyUI assets generated offline**, stored in `assets/` directory, loaded at startup.

---

## 2. Phase 0: ComfyUI Art Asset Pipeline

### Goal
Generate a complete set of hand-painted dark fantasy hex tile art, unit icons, building icons, and UI elements using ComfyUI on the local RTX 5090.

### Prerequisites
- ComfyUI installed locally
- SDXL checkpoint: Juggernaut XL (best for game art)
- ComfyUI-seamless-tiling node (spinagon/ComfyUI-seamless-tiling)
- ControlNet Canny model for hex structure preservation

### 2.1 Hex Template Generation

Create a Python script `tools/generate_hex_mask.py` that:
1. Draws a single flat-topped hex outline at 1024x1024 on transparent background
2. Saves as `tools/hex_mask_canny.png` (white hex outline on black background for ControlNet)
3. Draws a filled hex at 256x256 for use as a clipping mask
4. Saves as `tools/hex_clip_mask.png`

### 2.2 Terrain Tile Generation

Generate 9 base terrain tiles at 1024x1024 in ComfyUI, then crop/resize to 128x128 hex tiles.

**ComfyUI workflow** (`tools/terrain_workflow.json`):
1. Load SDXL checkpoint (Juggernaut XL)
2. Load custom style LoRA (weight 0.7) — see 2.4 for training
3. SeamlessTile node (enable X and Y)
4. ControlNet Canny with hex_mask_canny.png (strength 0.4 — gentle structure guide)
5. KSampler (steps: 30, cfg: 7, sampler: dpmpp_2m, scheduler: karras)
6. Circular VAE Decode
7. Save Image

**Prompts per terrain type:**

| Terrain | Positive Prompt | Negative Prompt |
|---------|----------------|-----------------|
| PLAINS | `hand-painted dark fantasy grassland, muted olive green, wild grass, medieval, top-down bird's eye view, game tile, seamless texture, painterly brushstrokes` | `modern, photorealistic, bright colors, text, watermark, UI elements` |
| GRASSLAND | `hand-painted dark fantasy lush meadow, deeper green, scattered wildflowers, medieval, top-down bird's eye view, game tile, seamless, painterly` | (same negative) |
| FOREST | `hand-painted dark fantasy dense forest canopy, dark green, ancient trees, mossy, top-down bird's eye view, game tile, seamless, painterly` | (same) |
| HILLS | `hand-painted dark fantasy rolling hills, brown-green, rocky outcrops, elevation, top-down bird's eye view, game tile, seamless, painterly` | (same) |
| MOUNTAIN | `hand-painted dark fantasy mountain peak, grey stone, snow caps, craggy, top-down bird's eye view, game tile, seamless, painterly` | (same) |
| DESERT | `hand-painted dark fantasy arid desert, golden sand, dunes, cracked earth, top-down bird's eye view, game tile, seamless, painterly` | (same) |
| TUNDRA | `hand-painted dark fantasy frozen tundra, snow, ice, sparse vegetation, top-down bird's eye view, game tile, seamless, painterly` | (same) |
| MARSH | `hand-painted dark fantasy swamp marshland, murky water, reeds, bog, top-down bird's eye view, game tile, seamless, painterly` | (same) |
| OCEAN | `hand-painted dark fantasy deep ocean water, dark blue waves, mysterious depths, top-down bird's eye view, game tile, seamless, painterly` | (same) |
| COAST | `hand-painted dark fantasy coastline, sandy beach meets shallow water, tidal, top-down bird's eye view, game tile, seamless, painterly` | (same) |
| RIVER_OVERLAY | `hand-painted dark fantasy river water, blue stream, transparent background, game asset overlay, painterly` | (same) |

Generate 3-5 variants per terrain type (different seeds). Pick best, store in `assets/tiles/`.

### 2.3 Post-Processing Pipeline

Create `tools/process_tiles.py`:
1. Load each 1024x1024 generated tile
2. Apply hex clipping mask (crop to hex shape with alpha)
3. Resize to 128x128 (LANCZOS resampling)
4. Pre-generate zoom variants: 64x64, 96x96, 128x128, 192x192, 256x256
5. Pack all tiles into a single sprite atlas (`assets/tiles/atlas.png`)
6. Generate atlas JSON with coordinates: `{"PLAINS_0": {"x": 0, "y": 0, "w": 128, "h": 128}, ...}`
7. Repeat for each zoom level: `atlas_z0.5.png`, `atlas_z0.75.png`, `atlas_z1.0.png`, `atlas_z1.5.png`, `atlas_z2.0.png`

### 2.4 Style LoRA Training (Optional but Recommended)

For visual consistency across all tiles:
1. Collect 20-30 reference images in target dark fantasy style (Darkest Dungeon terrain, Battle Brothers overworld, dark medieval concept art)
2. Use Kohya-ss or ComfyUI Lora-Training-in-Comfy node
3. Train SDXL LoRA at rank 32, 1500 steps, learning rate 1e-4
4. Save to `tools/civkings_style.safetensors`
5. Use at weight 0.6-0.8 in all generation workflows

### 2.5 Resource Overlay Icons

Generate at 512x512 with transparent background, resize to 32x32 for map overlay:

| Resource | Prompt |
|----------|--------|
| IRON | `dark fantasy iron ore chunk, metallic grey, game icon, transparent background, painterly` |
| GOLD_ORE | `dark fantasy gold nugget, gleaming yellow, game icon, transparent background, painterly` |
| WHEAT | `dark fantasy wheat sheaf, golden brown, game icon, transparent background, painterly` |
| HORSES | `dark fantasy horse head silhouette, brown, game icon, transparent background, painterly` |
| STONE | `dark fantasy carved stone block, grey, game icon, transparent background, painterly` |
| GEMS | `dark fantasy gemstone cluster, purple crystal, game icon, transparent background, painterly` |
| FISH | `dark fantasy fish, silver scales, game icon, transparent background, painterly` |
| SILK | `dark fantasy silk cloth roll, crimson, game icon, transparent background, painterly` |
| INCENSE | `dark fantasy incense burner, smoke wisps, game icon, transparent background, painterly` |

Pack into `assets/resources/atlas.png` + JSON.

### 2.6 Unit Icons

Generate at 512x512, resize to 48x48 for map display:

For each unit type in `game_data.UNIT_TYPES`, generate a top-down or 3/4 view icon.
Key units: Warrior, Archer, Cavalry, Settler, Worker, Catapult, Swordsman, Knight, Musketeer, Galley, Frigate, Spy.

Pack into `assets/units/atlas.png` + JSON.

### 2.7 Building/District Icons

Generate at 512x512, resize to 48x48:

For each building in `game_data.BUILDINGS` and district in `game_data.DISTRICTS`.
Key buildings: Granary, Library, Market, Barracks, Temple, Workshop, Walls, University, Bank, Factory.
Key districts: Campus, Commercial Hub, Holy Site, Encampment, Harbor, Entertainment Complex, Fortress.

Pack into `assets/buildings/atlas.png` + JSON.

### 2.8 UI Elements

Generate panel backgrounds, button frames, and decorative elements:

| Element | Size | Description |
|---------|------|-------------|
| panel_bg.png | 512x512 tileable | Dark stone/parchment texture for panel backgrounds |
| button_normal.png | 256x64 | Gold-bordered dark button, normal state |
| button_hover.png | 256x64 | Lighter gold border, hover state |
| button_pressed.png | 256x64 | Inset/darker, pressed state |
| frame_border.png | 9-slice 64x64 | Ornate border for windows/popups |
| resource_bar_bg.png | 1920x48 tileable | Top bar background texture |
| minimap_frame.png | 256x256 | Ornate frame for minimap corner |
| scroll_bg.png | 32x256 tileable | Scrollbar track texture |
| title_banner.png | 512x128 | "CivKings: Dynasty & Dominion" title art |

### 2.9 Batch Automation Script

Create `tools/batch_generate.py`:
```
Usage: python tools/batch_generate.py --comfyui-url http://127.0.0.1:8188 --output assets/
```
- Loads workflow JSON templates
- Substitutes prompts per asset type
- Calls ComfyUI HTTP API for each generation
- Polls for completion
- Downloads results
- Runs post-processing (clip, resize, pack atlas)
- Generates atlas JSON manifests

### Deliverables for Phase 0
- `assets/tiles/` — 9 terrain types x 5 zoom levels, packed atlases
- `assets/resources/` — 9 resource overlays
- `assets/units/` — 12+ unit icons
- `assets/buildings/` — 10+ building/district icons
- `assets/ui/` — panel backgrounds, button states, frames
- `tools/` — hex mask generator, tile processor, batch generator, workflow JSONs
- All atlas JSON manifests for coordinate lookup

---

## 3. Phase 1: Pygame Core Scaffold

### Goal
Establish the Pygame application skeleton: window, game loop, state machine, pygame_gui manager, theme, and basic screen transitions.

### 3.1 Dependencies

Add `requirements.txt`:
```
pygame-ce>=2.5.0
pygame-gui>=0.6.14
Pillow>=10.0.0
```

### 3.2 Main Application (`pygame_app/app.py`)

```python
# Pseudocode structure — CynCo implements fully

import pygame
import pygame_gui

class GameApp:
    SCREEN_WIDTH = 1400
    SCREEN_HEIGHT = 900
    FPS = 30

    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.screen = pygame.display.set_mode(
            (self.SCREEN_WIDTH, self.SCREEN_HEIGHT),
            pygame.RESIZABLE
        )
        pygame.display.set_caption("CivKings: Dynasty & Dominion")
        self.clock = pygame.time.Clock()
        self.ui_manager = pygame_gui.UIManager(
            (self.SCREEN_WIDTH, self.SCREEN_HEIGHT),
            'pygame_app/theme.json'
        )
        self.state = "main_menu"  # main_menu | playing | victory
        self.game = None  # Engine Game instance
        self.screens = {}  # Screen instances
        self.running = True

    def run(self):
        while self.running:
            dt = self.clock.tick(self.FPS) / 1000.0
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                self.ui_manager.process_events(event)
                self.current_screen.handle_event(event)
            self.ui_manager.update(dt)
            self.current_screen.update(dt)
            self.current_screen.draw(self.screen)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.flip()
        pygame.quit()
```

### 3.3 Theme File (`pygame_app/theme.json`)

Define the dark fantasy palette for all pygame_gui widgets:

```json
{
    "#defaults": {
        "colours": {
            "dark_bg": "#0a0b0d",
            "normal_bg": "#16181d",
            "hovered_bg": "#23262d",
            "selected_bg": "#33363d",
            "disabled_bg": "#111214",
            "normal_text": "#e0e0e0",
            "hovered_text": "#c5a059",
            "selected_text": "#c5a059",
            "disabled_text": "#555555",
            "normal_border": "#33363d",
            "hovered_border": "#c5a059",
            "focused_border": "#c5a059",
            "link_text": "#c5a059",
            "link_hover": "#d4b76a",
            "text_shadow": "#000000"
        },
        "font": {
            "name": "default",
            "size": 14
        }
    },
    "button": {
        "colours": {
            "normal_bg": "#23262d",
            "hovered_bg": "#33363d",
            "active_bg": "#1a1c22",
            "normal_border": "#c5a059",
            "hovered_border": "#d4b76a"
        },
        "misc": {
            "border_width": "1",
            "shape_corner_radius": "3"
        }
    },
    "window": {
        "colours": {
            "dark_bg": "#0a0b0d",
            "normal_bg": "#16181d",
            "normal_border": "#c5a059"
        },
        "misc": {
            "border_width": "2",
            "title_bar_height": "28"
        }
    },
    "text_box": {
        "colours": {
            "dark_bg": "#0a0b0d",
            "normal_bg": "#16181d",
            "normal_border": "#33363d"
        }
    },
    "selection_list": {
        "colours": {
            "dark_bg": "#0a0b0d",
            "normal_bg": "#16181d",
            "selected_bg": "#33363d",
            "normal_border": "#33363d"
        }
    },
    "panel": {
        "colours": {
            "dark_bg": "#16181d",
            "normal_bg": "#16181d",
            "normal_border": "#33363d"
        }
    }
}
```

### 3.4 Screen Base Class

```python
class BaseScreen:
    def __init__(self, app: GameApp):
        self.app = app
        self.ui_manager = app.ui_manager

    def enter(self):
        """Called when this screen becomes active."""
        pass

    def exit(self):
        """Called when leaving this screen. Kill UI elements."""
        pass

    def handle_event(self, event: pygame.event.Event):
        pass

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        pass
```

### 3.5 Main Menu Screen (`pygame_app/screens/main_menu.py`)

- Title banner image (from ComfyUI assets)
- "New Game" button -> opens NewGameDialog
- "Load Game" button -> opens file browser
- "Quit" button
- Background: dark with subtle particle effect (optional)

### 3.6 New Game Dialog (`pygame_app/screens/new_game_dialog.py`)

- Civilization selection (dropdown or grid of civ icons)
- For each civ: show name, bonuses, unique unit/building
- Difficulty selection (Rookie / Easy / Standard / Hard / Immortal)
- Map size selection (Small 12x12 / Medium 16x16 / Large 24x24 / Huge 32x32)
- Number of AI opponents (1-7)
- "Start Game" and "Back" buttons
- Clicking Start creates `Game(civ)` engine instance, transitions to GameScreen

### Deliverables for Phase 1
- `pygame_app/app.py` — main loop, window, state machine
- `pygame_app/theme.json` — dark fantasy theme
- `pygame_app/screens/base.py` — BaseScreen class
- `pygame_app/screens/main_menu.py` — title screen
- `pygame_app/screens/new_game_dialog.py` — game setup
- `requirements.txt` — dependencies
- Game launches, shows menu, creates game, transitions to (empty) game screen

---

## 4. Phase 2: Hex Map Renderer

### Goal
Render the hex map using ComfyUI-generated image tiles with sprite-based rendering, viewport camera, zoom, pan, fog of war, and tile interaction.

### 4.1 Tile Atlas Loader (`pygame_app/map/tile_atlas.py`)

```python
class TileAtlas:
    """Loads packed sprite sheet and provides tile surfaces by terrain type."""

    def __init__(self, atlas_dir: str):
        """
        atlas_dir contains:
          atlas_z1.0.png + atlas_z1.0.json (and other zoom levels)
        JSON format: {"PLAINS_0": {"x": 0, "y": 0, "w": 128, "h": 128}, ...}
        """
        self.zoom_levels = [0.5, 0.75, 1.0, 1.5, 2.0]
        self.atlases = {}  # {zoom: pygame.Surface}
        self.tile_rects = {}  # {zoom: {terrain_name: pygame.Rect}}
        self._load_all(atlas_dir)

    def get_tile(self, terrain_type: TerrainType, zoom: float, variant: int = 0) -> pygame.Surface:
        """Return the pre-rendered tile surface for terrain at given zoom."""
        nearest_zoom = min(self.zoom_levels, key=lambda z: abs(z - zoom))
        key = f"{terrain_type.name}_{variant}"
        rect = self.tile_rects[nearest_zoom][key]
        return self.atlases[nearest_zoom].subsurface(rect)
```

**Fallback**: If atlas doesn't exist yet (ComfyUI not run), generate solid-color hex tiles programmatically using the existing color palette. This ensures the game is playable during development even without art assets.

### 4.2 Camera System (`pygame_app/map/camera.py`)

```python
class Camera:
    """Manages viewport position, zoom, and coordinate transforms."""

    def __init__(self, screen_w: int, screen_h: int):
        self.x = 0.0  # World position of viewport center
        self.y = 0.0
        self.zoom = 1.0
        self.min_zoom = 0.3
        self.max_zoom = 3.0
        self.screen_w = screen_w
        self.screen_h = screen_h
        # Smooth scrolling state
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_zoom = 1.0
        self.lerp_speed = 8.0  # Higher = snappier

    def world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        """Convert world coordinates to screen pixel position."""
        sx = (wx - self.x) * self.zoom + self.screen_w / 2
        sy = (wy - self.y) * self.zoom + self.screen_h / 2
        return int(sx), int(sy)

    def screen_to_world(self, sx: int, sy: int) -> Tuple[float, float]:
        """Convert screen pixel to world coordinates."""
        wx = (sx - self.screen_w / 2) / self.zoom + self.x
        wy = (sy - self.screen_h / 2) / self.zoom + self.y
        return wx, wy

    def get_visible_bounds(self) -> Tuple[float, float, float, float]:
        """Return (min_wx, min_wy, max_wx, max_wy) of visible world area."""
        half_w = (self.screen_w / 2) / self.zoom
        half_h = (self.screen_h / 2) / self.zoom
        return (self.x - half_w, self.y - half_h, self.x + half_w, self.y + half_h)

    def update(self, dt: float):
        """Smooth lerp toward target position/zoom."""
        t = min(1.0, self.lerp_speed * dt)
        self.x += (self.target_x - self.x) * t
        self.y += (self.target_y - self.y) * t
        self.zoom += (self.target_zoom - self.zoom) * t

    def pan(self, dx: float, dy: float):
        self.target_x += dx / self.zoom
        self.target_y += dy / self.zoom

    def zoom_at(self, screen_x: int, screen_y: int, factor: float):
        """Zoom centered on mouse position."""
        # Convert mouse to world before zoom
        wx, wy = self.screen_to_world(screen_x, screen_y)
        self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom * factor))
        # Adjust position so mouse stays over same world point
        # (recalculate after zoom change)
```

**Input handling**:
- Mouse wheel: zoom at cursor position
- Middle mouse drag: pan
- WASD / Arrow keys: pan at constant speed
- Edge scrolling: when mouse is within 20px of screen edge, pan in that direction
- Home key: center on capital city
- Double-click hex: center camera on that hex

### 4.3 Hex Map Renderer (`pygame_app/map/hex_renderer.py`)

```python
class HexMapRenderer:
    """Renders the hex map using sprite-based tile images."""

    HEX_SIZE = 64  # Base hex radius in pixels (at zoom 1.0)

    def __init__(self, hex_map: HexMap, tile_atlas: TileAtlas, camera: Camera):
        self.hex_map = hex_map
        self.atlas = tile_atlas
        self.camera = camera
        self.dirty_tiles = set()  # (q, r) coordinates that need redraw
        self.tile_surfaces = {}  # Cache: (q, r, zoom_level) -> Surface
        self.map_surface = None  # Pre-rendered map at current zoom
        self.needs_full_redraw = True

    def hex_to_world(self, q: int, r: int) -> Tuple[float, float]:
        """Axial hex coordinates to world pixel coordinates (flat-top)."""
        x = self.HEX_SIZE * 1.5 * q
        y = self.HEX_SIZE * math.sqrt(3) * (r + 0.5 * (q & 1))
        return x, y

    def world_to_hex(self, wx: float, wy: float) -> Tuple[int, int]:
        """World pixel to nearest hex axial coordinates."""
        q = (2.0 / 3.0 * wx) / self.HEX_SIZE
        r = (-1.0 / 3.0 * wx + math.sqrt(3) / 3.0 * wy) / self.HEX_SIZE
        return self._axial_round(q, r)

    def render(self, screen: pygame.Surface):
        """Render visible hex tiles to screen."""
        bounds = self.camera.get_visible_bounds()
        visible_hexes = self._get_visible_hexes(bounds)

        for q, r in visible_hexes:
            tile = self.hex_map.get_tile(q, r)
            if tile is None:
                continue

            # Get terrain tile image
            tile_img = self.atlas.get_tile(tile.terrain, self.camera.zoom)

            # Convert hex to screen position
            wx, wy = self.hex_to_world(q, r)
            sx, sy = self.camera.world_to_screen(wx, wy)

            # Blit terrain tile
            rect = tile_img.get_rect(center=(sx, sy))
            screen.blit(tile_img, rect)

            # Draw resource overlay if present
            if tile.resource:
                self._draw_resource_overlay(screen, tile.resource, sx, sy)

            # Draw river edges
            if tile.river:
                self._draw_river(screen, q, r, sx, sy)

        # Draw territory borders after all tiles
        self._draw_borders(screen, visible_hexes)
```

### 4.4 Tile Layers (draw order)

Render in this exact order for correct z-ordering:

1. **Terrain tiles** — base hex images from atlas
2. **River overlays** — blue lines along hex edges where rivers exist
3. **Resource icons** — small overlay icons (32x32) on tiles with resources
4. **Territory borders** — colored dashed lines around owned territory
5. **Improvement overlays** — farm/mine/quarry icons on improved tiles (Phase 7)
6. **City markers** — city name + population badge on city tiles
7. **Unit sprites** — unit icons on their hex positions
8. **Health bars** — small red/green bars below units and cities
9. **Fog of war overlay** — semi-transparent black over unexplored/unseen tiles
10. **Selection highlight** — pulsing golden border on selected unit/city hex
11. **Movement range** — blue-tinted hexes showing where selected unit can move
12. **Attack range** — red-tinted hexes showing where selected unit can attack
13. **Hover tooltip** — info popup at cursor position

### 4.5 Fog of War (`pygame_app/map/fog_of_war.py`)

Three visibility states per tile:
- **Unexplored**: Fully black (never seen)
- **Seen but not visible**: Dark overlay (alpha 180/255) — shows terrain but not units
- **Visible**: Full brightness, shows everything

Implementation: Pre-render a fog surface the same size as the viewport. For each hex, fill with appropriate alpha. Blit fog surface over the map.

### 4.6 Minimap (`pygame_app/map/minimap.py`)

- Fixed 200x200 surface in bottom-left corner
- Each hex = 2-4 pixel colored dot based on terrain
- White rectangle showing current viewport bounds
- City dots in player color
- Unit dots as small markers
- Click minimap to jump camera to that position
- Frame image from ComfyUI UI assets

### 4.7 Tile Interaction

**Left click**:
- On own unit: Select unit, show movement range, show action bar
- On own city: Select city, show city detail panel
- On highlighted movement hex: Move selected unit there
- On enemy unit (in attack range): Attack with selected unit
- On empty hex: Deselect

**Right click**:
- On any tile: Show tile info tooltip (terrain, yields, resource, improvements, defending unit)

**Hover**:
- Show hex coordinates and terrain name in a subtle tooltip
- Highlight hex border with golden outline

### Deliverables for Phase 2
- `pygame_app/map/tile_atlas.py` — sprite sheet loader with fallback
- `pygame_app/map/camera.py` — pan/zoom/viewport
- `pygame_app/map/hex_renderer.py` — terrain, resources, cities, units
- `pygame_app/map/fog_of_war.py` — three-state fog overlay
- `pygame_app/map/minimap.py` — corner minimap
- `pygame_app/map/highlights.py` — selection, move range, attack range
- Hex map renders with image tiles (or colored fallback), click interaction works, camera pans/zooms smoothly

---

## 5. Phase 3: UI Panels and Widgets

### Goal
Implement all persistent UI panels using pygame_gui widgets.

### 5.1 Resource Bar (`pygame_app/panels/resource_bar.py`)

Fixed bar across the top of the screen (full width, 40px height).

| Element | Position | Format |
|---------|----------|--------|
| Civ Name + Era | Left-aligned | "Rome - Ancient Era" |
| Food icon + value | After name | "🌾 3.6" (rounded to 1 decimal, NO floating point garbage) |
| Production icon + value | Next | "⚙ 1.9" |
| Gold icon + value | Next | "💰 100 (+21/turn)" — show per-turn income |
| Science icon + value | Next | "🔬 15 (+8/turn)" |
| Culture icon + value | Next | "🎭 5 (+3/turn)" |
| Faith icon + value | Next | "⛪ 0 (+0/turn)" |
| Turn counter | Right-aligned | "Turn 1 / 300" |
| Game speed | Far right | "1x ▶" button |

**Critical fix**: All yield values MUST be displayed as `f"{value:.1f}"` or `int(value)` — NEVER raw floats. The current GUI shows `Production: 1.920000000000004` which is unacceptable.

### 5.2 City Panel (`pygame_app/panels/city_panel.py`)

Left sidebar (250px wide, collapsible). Shows list of all player cities:

For each city:
- City name (bold)
- Population: "Pop 3 (+0.5 food surplus)"
- Current production: "Building: Granary (3/10)" with progress bar
- If production queue empty: "⚠ IDLE" in red
- Click city name to center camera on it and open city detail popup

### 5.3 Unit Panel (`pygame_app/panels/unit_panel.py`)

Below city panel in left sidebar. Shows all player units:

For each unit:
- Unit type icon + name: "⚔ Warrior"
- HP bar (green/yellow/red gradient)
- Movement remaining: "Moves: 2/2"
- Location: "(5, 3)"
- Status: "Idle" / "Fortified" / "Moving"
- Click to center camera on unit and select it
- Units with remaining movement highlighted differently from spent units

### 5.4 Event Log (`pygame_app/panels/event_log.py`)

Right sidebar or bottom panel (scrollable, 300px wide or 150px tall):

- Scrollable list of game events
- Color-coded by type:
  - Gold: gold/economy events
  - Red: combat/war events
  - Green: growth/production events
  - Blue: science/tech events
  - Purple: dynasty/character events
  - White: general info
- Newest events at top
- Click event to jump to relevant location
- Each entry: "[Turn 5] Rome completed Granary in Roma"

### 5.5 Turn Summary (`pygame_app/panels/turn_summary.py`)

**THIS IS THE MOST IMPORTANT UI FEATURE FOR GAME FEEL.**

At the start of each turn (after process_turn()), collect ALL events and display them as a notification queue:

```
┌─────────────────────────────────┐
│  TURN 12 SUMMARY                │
│─────────────────────────────────│
│  📦 Roma completed Granary      │  [Click to view]
│  🔬 Research complete: Writing  │  [Click to view]
│  ⚔ Warrior defeated Barbarian  │  [Click to view]
│  🌱 Roma grew to Pop 4         │  [Click to view]
│  ⚠ Egypt has declared war!     │  [Click to view]
│  📜 Event: Trade Boom (+25 gold)│  [Click to view]
│                                 │
│         [Dismiss All]           │
└─────────────────────────────────┘
```

Implementation:
- `game.process_turn()` already returns/generates events via EventManager
- Collect all turn events into a list
- Display as a pygame_gui UIWindow that appears at start of each new turn
- Each entry is clickable — camera jumps to relevant hex
- "Dismiss All" closes the summary
- If no events, don't show the popup

### 5.6 Action Bar (`pygame_app/panels/action_bar.py`)

Bottom bar that changes based on what's selected:

**When unit selected**:
| Button | Key | Action |
|--------|-----|--------|
| Move | M | Enter movement mode (show range, click to move) |
| Attack | A | Enter attack mode (show range, click to attack) |
| Fortify | F | Fortify unit (+3 defense) |
| Skip | Space | Skip unit's turn |
| Disband | Del | Disband unit (confirmation dialog) |
| Upgrade | U | Upgrade unit if upgrade available and affordable |

**When city selected**:
| Button | Key | Action |
|--------|-----|--------|
| Production | P | Open production popup |
| Buy | B | Buy current production with gold |
| Manage Citizens | C | Open citizen assignment (future) |

**When nothing selected**:
| Button | Key | Action |
|--------|-----|--------|
| Next Turn | Enter | Process turn (with confirmation if idle cities/units) |
| Next Unit | Tab | Cycle to next unit with movement remaining |
| Tech Tree | T | Open tech tree |
| Diplomacy | D | Open diplomacy |
| Dynasty | Y | Open dynasty info |

### 5.7 End Turn Logic

The "Next Turn" button MUST implement smart warnings:

1. Check if any cities have empty production queues -> "Roma has nothing in production. End turn anyway?"
2. Check if any units have movement remaining -> "2 units have movement remaining. End turn anyway?"
3. Check if no research selected -> "No technology is being researched!"
4. If all checks pass, process turn immediately
5. After processing, show Turn Summary popup

The button should visually indicate state:
- RED pulsing: Units/cities need attention
- GOLD: Ready to end turn (all decisions made)

### Deliverables for Phase 3
- `pygame_app/panels/resource_bar.py` — top bar with formatted yields
- `pygame_app/panels/city_panel.py` — city list sidebar
- `pygame_app/panels/unit_panel.py` — unit list sidebar
- `pygame_app/panels/event_log.py` — scrollable color-coded log
- `pygame_app/panels/turn_summary.py` — start-of-turn notification queue
- `pygame_app/panels/action_bar.py` — context-sensitive bottom bar
- All panels update when game state changes (new turn, selection change)

---

## 6. Phase 4: Popups and Dialogs

### Goal
Implement all modal/popup windows for detailed game interactions.

### 6.1 Production Popup (`pygame_app/popups/production.py`)

Opens when clicking "Start Production" or "Production" button.

Layout:
```
┌── City Production: Roma ─────────────────────────┐
│                                                   │
│  AVAILABLE                    QUEUE               │
│  ┌─────────────────────┐     ┌────────────────┐  │
│  │ UNITS                │     │ 1. Granary (3t)│  │
│  │  ⚔ Warrior    20🔨  │     │ 2. Warrior (4t)│  │
│  │  🏹 Archer     30🔨  │     │                │  │
│  │  🐴 Cavalry    40🔨  │     │                │  │
│  │  🏗 Settler    80🔨  │     │                │  │
│  │  👷 Worker     50🔨  │     │ [▲ Move Up]    │  │
│  │                       │     │ [▼ Move Down]  │  │
│  │ BUILDINGS             │     │ [✕ Remove]     │  │
│  │  🏛 Library    40🔨  │     │                │  │
│  │  🏪 Market     60🔨  │     └────────────────┘  │
│  │  ⛪ Temple     50🔨  │                         │
│  │  🏭 Workshop   70🔨  │     Turns to complete:  │
│  │                       │     3 turns (at 8🔨/t)  │
│  │ DISTRICTS             │                         │
│  │  🎓 Campus    100🔨  │     [💰 Buy: 200g]      │
│  │  💰 Comm Hub  100🔨  │                         │
│  └─────────────────────┘     [Close]              │
└───────────────────────────────────────────────────┘
```

Features:
- Left panel: Available items grouped by category (Units, Buildings, Districts)
- Each item shows: icon, name, production cost, turns to build at current rate
- Items greyed out if prerequisites not met (with tooltip explaining why)
- Right panel: Current production queue
- Queue supports reordering (move up/down) and removal
- "Buy" button to purchase with gold (cost = production remaining * 4)
- Double-click or select+Enter to add to queue
- Show city's production per turn to calculate ETA

### 6.2 Tech Tree Popup (`pygame_app/popups/tech_tree.py`)

Full-screen overlay showing all technologies organized by era.

Layout:
```
ANCIENT ERA          CLASSICAL ERA         MEDIEVAL ERA          ...
┌──────────┐        ┌──────────┐         ┌──────────┐
│ Pottery  │───────>│ Writing  │────────>│ Education │
│ ✅ Done  │        │ 🔬 15/40 │         │ 🔒 Locked │
└──────────┘        └──────────┘         └──────────┘
┌──────────┐        ┌──────────┐
│ Mining   │───────>│ Bronze   │
│ ✅ Done  │        │ Working  │
└──────────┘        └──────────┘
```

Features:
- Horizontal layout: eras as columns, techs as nodes
- Prerequisite arrows connecting nodes
- Color coding:
  - Green: researched
  - Blue: currently researching (with progress bar)
  - White: available to research
  - Grey: locked (prerequisites not met)
- Click available tech to start researching
- Hover shows: name, cost, era, prerequisites, unlocks (units, buildings, abilities)
- Zoom/pan within the tech tree view for large trees
- Current research progress shown prominently at top

### 6.3 Diplomacy Popup (`pygame_app/popups/diplomacy.py`)

Shows all known civilizations and diplomatic options.

Layout:
```
┌── Diplomacy ──────────────────────────────────────┐
│                                                   │
│  CIVILIZATIONS          RELATIONS WITH EGYPT      │
│  ┌─────────────┐       ┌───────────────────────┐ │
│  │ 🏛 Egypt    │       │ Status: Neutral        │ │
│  │   Neutral   │       │ Opinion: +15           │ │
│  │ 🏛 Greece   │       │ Treaties: None         │ │
│  │   Friendly  │       │                        │ │
│  │ 🏛 Persia   │       │ ACTIONS:               │ │
│  │   Hostile   │       │ [Declare War]          │ │
│  └─────────────┘       │ [Propose Alliance]     │ │
│                        │ [Trade Agreement]      │ │
│                        │ [Open Borders]         │ │
│                        │ [Denounce]             │ │
│                        │                        │ │
│                        │ MODIFIERS:             │ │
│                        │ +10 Same religion      │ │
│                        │ -5  Border tension     │ │
│                        │ +20 Trade partner      │ │
│                        └───────────────────────┘ │
│                                          [Close] │
└───────────────────────────────────────────────────┘
```

Features:
- Left: list of known civs with relationship status color
- Right: detailed view of selected civ
- Show all opinion modifiers with explanations
- Action buttons with tooltips explaining consequences
- Treaty proposals show terms before confirming
- War declaration shows casus belli options (if any) and warmongering penalty
- Diplomatic inbox for messages from other civs

### 6.4 Dynasty Popup (`pygame_app/popups/dynasty.py`)

Shows current ruler, heirs, family tree, and dynasty info.

Layout:
```
┌── House of Julius ────────────────────────────────┐
│                                                   │
│  CURRENT RULER          STATS                     │
│  ┌──────────────┐      Diplomacy:  ████████░░ 8  │
│  │  Augustus I   │      Martial:    ██████░░░░ 6  │
│  │  Age: 42      │      Stewardship:████████░░ 8  │
│  │  Era: Ancient  │      Intrigue:   ████░░░░░░ 4  │
│  │  Health: Good  │      Learning:   ██████████ 10 │
│  └──────────────┘                                 │
│                        TRAITS                     │
│  HEIR                  [Ambitious] [Scholar]      │
│  Marcus (age 18)       [Just]                     │
│  Dip:6 Mar:7 Ste:5                              │
│                        STRESS: ██░░░░░░░░ 20/100 │
│  SUCCESSION                                      │
│  Law: Primogeniture    LIFESTYLE                  │
│  Next: Marcus          [Learning: Scholar]        │
│                        Progress: ████████░░ 80%   │
│  DYNASTY PRESTIGE                                │
│  450 (+12/turn)        COURT POSITIONS            │
│                        Marshal: General Brutus    │
│  FAMILY TREE           Spymaster: Livia          │
│  [View Full Tree]      Chancellor: Cicero         │
│                        Steward: Crassus           │
│                        Chaplain: (vacant)         │
│                                          [Close]  │
└───────────────────────────────────────────────────┘
```

### 6.5 City Detail Popup (`pygame_app/popups/city_detail.py`)

Detailed view of a single city (opens when clicking city on map or city list).

Shows:
- City name, population, growth progress bar
- Per-turn yields: food, production, gold, science, culture, faith (with breakdown by source)
- Buildings list (built and available)
- Districts list (built and available)
- Garrison units
- Trade routes to/from this city
- Happiness/amenity status for this city
- Housing status
- Production queue

### 6.6 Combat Preview and Result (`pygame_app/popups/combat_result.py`)

**Combat Preview** (shows BEFORE committing to attack):
```
┌── Combat Preview ──────────────────┐
│                                    │
│  YOUR ARMY        ENEMY ARMY       │
│  ⚔ Warrior x2    ⚔ Warrior x1    │
│  🏹 Archer x1     🐴 Cavalry x1   │
│                                    │
│  Strength: 45     Strength: 38     │
│  Terrain: Plains  Terrain: Hills   │
│  Bonus: +0        Bonus: +5 (def)  │
│                                    │
│  PREDICTED OUTCOME:                │
│  Likely Victory (72% chance)       │
│  Est. casualties: 1-2 units        │
│                                    │
│  [Attack]  [Cancel]                │
└────────────────────────────────────┘
```

**Combat Result** (shows after combat resolves):
```
┌── Battle of the Plains ────────────┐
│                                    │
│  ⚔ VICTORY! ⚔                     │
│                                    │
│  Your losses: 1 Warrior            │
│  Enemy losses: 1 Warrior, 1 Cavalry│
│                                    │
│  XP gained: +15 (Archer promoted!) │
│                                    │
│  [Continue]                        │
└────────────────────────────────────┘
```

### 6.7 Event Choice Popup (`pygame_app/popups/event_choice.py`)

When random events fire, show a popup with narrative text and choices:

```
┌── Event: The Great Plague ─────────┐
│                                    │
│  A terrible plague has swept       │
│  through your lands. Your          │
│  advisors present options:         │
│                                    │
│  [Quarantine the cities]           │
│    -10 gold, -5 happiness          │
│    Reduces plague duration          │
│                                    │
│  [Pray for salvation]              │
│    +5 faith                        │
│    Plague continues normally        │
│                                    │
│  [Burn the infected districts]     │
│    -1 population, -20 happiness    │
│    Ends plague immediately          │
└────────────────────────────────────┘
```

### 6.8 Encyclopedia (`pygame_app/popups/encyclopedia.py`)

In-game reference accessible from menu bar or F1 key.

- Searchable
- Categories: Terrain, Resources, Units, Buildings, Districts, Technologies, Civilizations, Victory Conditions, Game Concepts
- Each entry: name, description, stats, gameplay effects
- Populated from `game_data.py` definitions
- Linked entries (clicking "requires Bronze Working" opens that tech's page)

### 6.9 Trade Route Popup (`pygame_app/popups/trade.py`)

Manage trade routes between cities:
- List of active trade routes with income breakdown
- Available trade partners (domestic cities and foreign civs)
- Create new route: select origin city, destination, see projected income
- Route duration and renewal options

### Deliverables for Phase 4
- All popup files in `pygame_app/popups/`
- Each popup receives engine data, displays it, and sends player actions back to engine
- Popups are modal (pause game interaction behind them)
- All popups use the dark fantasy theme from theme.json

---

## 7. Phase 5: Sound and Visual Effects

### Goal
Add audio feedback and visual polish that transforms game feel from "tech demo" to "real game."

### 7.1 Sound Manager (`pygame_app/audio/sound_manager.py`)

```python
class SoundManager:
    """Manages sound effect loading and categorized playback."""

    CATEGORIES = {
        'ui': ['click', 'hover', 'confirm', 'cancel', 'error', 'notification'],
        'combat': ['sword_clash', 'arrow_fire', 'siege_hit', 'cavalry_charge', 'victory_fanfare', 'defeat'],
        'city': ['production_complete', 'city_founded', 'city_growth', 'building_built'],
        'diplomacy': ['war_declared', 'peace_signed', 'alliance_formed', 'trade_agreed'],
        'turn': ['turn_start', 'turn_end'],
        'character': ['ruler_death', 'heir_born', 'coronation'],
    }

    def play(self, category: str, sound_name: str, volume: float = 0.7):
        """Play a sound effect. Non-blocking, multiple channels."""
        ...
```

**Sound asset sources** (royalty-free):
- Generate with AI sound tools (ElevenLabs sound effects, or Bark)
- Or use free CC0 packs from freesound.org / OpenGameArt
- Store as OGG format (smaller than WAV, better than MP3 for games)

**Required sounds** (minimum viable):
- `click.ogg` — button click (short, crisp)
- `confirm.ogg` — action confirmed (pleasant chime)
- `notification.ogg` — new event/alert (gentle bell)
- `turn_start.ogg` — new turn begins (subtle transition)
- `production_complete.ogg` — city finished building (hammer + chime)
- `combat_start.ogg` — sword unsheathing or war horn
- `victory.ogg` — fanfare
- `war_declared.ogg` — ominous drum beat

### 7.2 Music Manager (`pygame_app/audio/music_manager.py`)

```python
class MusicManager:
    """Streams era-appropriate background music."""

    ERA_TRACKS = {
        Era.ANCIENT: 'assets/music/ancient.ogg',
        Era.CLASSICAL: 'assets/music/classical.ogg',
        Era.MEDIEVAL: 'assets/music/medieval.ogg',
        Era.RENAISSANCE: 'assets/music/renaissance.ogg',
        Era.INDUSTRIAL: 'assets/music/industrial.ogg',
        Era.MODERN: 'assets/music/modern.ogg',
    }

    def update_era(self, era: Era):
        """Cross-fade to new era's music track."""
        if era != self.current_era:
            pygame.mixer.music.fadeout(2000)  # 2 second fadeout
            pygame.mixer.music.load(self.ERA_TRACKS[era])
            pygame.mixer.music.play(-1, fade_ms=2000)  # Loop with 2s fade in
            self.current_era = era
```

**Music sources**: Royalty-free ambient/medieval/strategy game music from:
- Kevin MacLeod (incompetech.com) — CC-BY, excellent medieval/orchestral tracks
- Free Music Archive
- OpenGameArt music packs
- Or generate with Suno/Udio AI music (for truly custom feel)

### 7.3 Visual Effects (`pygame_app/effects/`)

**Unit Movement Animation** (`pygame_app/effects/animations.py`):
- When unit moves, don't teleport — animate slide along hex path
- Duration: 300ms per hex (faster for cavalry)
- Easing: ease-out (starts fast, decelerates)
- Camera follows moving unit if it's the selected unit

**Combat Animation**:
- Units lunge toward each other (50px offset in attack direction, 200ms)
- Flash/shake on impact (screen shake for large battles)
- Damage number floats up from damaged unit (red "-12 HP")
- Death animation: unit fades out over 500ms

**City Growth Animation**:
- Brief golden glow pulse on city when population grows
- "+1 Pop" text floats up

**Production Complete Animation**:
- New unit/building icon pops in with scale animation (0 -> 1.0 over 300ms)
- Accompanied by sound effect

**Tech Complete Animation**:
- Brief "Research Complete!" banner across top of screen (2 seconds)
- Tech name and icon

**Particle System** (`pygame_app/effects/particles.py`):
- Lightweight particle emitter for celebrations, combat debris, weather
- Each particle: position, velocity, lifetime, color, size, alpha
- Update in batch, cull expired particles
- Use for: combat impact sparks, city celebration confetti, fire effects

### Deliverables for Phase 5
- `pygame_app/audio/sound_manager.py` — categorized sound playback
- `pygame_app/audio/music_manager.py` — era-based background music
- `pygame_app/effects/animations.py` — movement, combat, growth animations
- `pygame_app/effects/particles.py` — particle emitter system
- `assets/sounds/` — minimum 8 sound effects
- `assets/music/` — at least 1 background track (more per era ideal)

---

## 8. Phase 6: Game Engine Fixes

### Goal
Fix all known bugs in the existing engine before adding new features.

### 8.1 GUI State Sync (NOW IN PYGAME)

The current engine has a fundamental problem: `process_turn()` updates internal state but the old GUI never reads it back. The new Pygame GUI must read engine state every frame:

```python
# In game_screen.py update():
def update(self, dt):
    # Sync resource bar with current game state
    self.resource_bar.update_from_game(self.game)
    # Sync unit/city panels
    self.city_panel.refresh(self.game.city_manager.cities)
    self.unit_panel.refresh(self.game.military_manager.units)
```

This is architectural — the Pygame rewrite fixes it by design.

### 8.2 Floating Point Display

In `resource_bar.py`, format all yields:
```python
def format_yield(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"
```

### 8.3 AI Player Initialization

In `game.py`, the `__init__` creates `self.ai_players: Dict[str, AIPlayer] = {}` but never populates it unless specific code paths are hit. Fix:

- New game dialog specifies number of AI opponents and their civs
- `Game.__init__` receives list of AI civ names and creates AIPlayer instances
- OR: Add a `game.add_ai_player(civ_name, difficulty)` method called from the new game dialog
- AI players get their own starting city and units placed on the map

### 8.4 AI Turn Processing

Verify `game.process_turn()` actually calls AI decision-making:
- Each AI player should: choose research, set production, move units, make diplomatic decisions
- AI actions should generate events visible in the event log
- AI cities should grow, build, and expand

### 8.5 Multi-Civ Map Placement

Currently the map spawns one civ's starting city. Need:
- Place each civ's starting city with minimum distance between them (at least 5 hexes apart)
- Each civ starts with 1 city + 1 warrior + 1 scout
- Starting locations should be near fresh water and on good terrain
- AI civs are fully placed on the map with visible territory

### 8.6 Save/Load with Pygame

Adapt `save_system.py` to work with the new Pygame GUI:
- Save game state to JSON (engine already does this)
- Load game state and rebuild all managers
- Pygame GUI re-initializes from loaded game state
- File browser dialog for save slot selection

### Deliverables for Phase 6
- AI players spawn with cities and units on the map
- Turn processing runs AI decisions
- All engine state correctly reflected in Pygame GUI
- Save/load works with new GUI
- No floating point display issues
- No orphaned state (every engine change reflected in UI)

---

## 9. Phase 7: Core Missing Mechanics

### Goal
Add the mechanics that are essential for the game to feel like a real strategy game.

### 9.1 Eureka/Inspiration System

**The single most impactful missing feature.** Creates emergent sub-goals that reward natural play.

Add to `tech.py`:

```python
EUREKA_CONDITIONS = {
    'Mining': {'type': 'build_improvement', 'target': 'Quarry', 'description': 'Build a Quarry'},
    'Sailing': {'type': 'found_coastal_city', 'description': 'Found a city on the coast'},
    'Archery': {'type': 'kill_with_unit', 'unit': 'Slinger', 'description': 'Kill a unit with a Slinger'},
    'Writing': {'type': 'meet_civ', 'description': 'Meet another civilization'},
    'Bronze Working': {'type': 'kill_count', 'count': 3, 'description': 'Kill 3 barbarian units'},
    'Apprenticeship': {'type': 'build_count', 'building': 'Mine', 'count': 3, 'description': 'Build 3 Mines'},
    'Masonry': {'type': 'build_improvement', 'target': 'Quarry', 'description': 'Build a Quarry'},
    'Iron Working': {'type': 'build_count', 'building': 'Barracks', 'count': 1, 'description': 'Build a Barracks'},
    'Mathematics': {'type': 'build_count', 'building': 'District', 'count': 3, 'description': 'Build 3 Districts'},
    'Construction': {'type': 'build_improvement', 'target': 'Mine', 'description': 'Build a Mine on Hills'},
    'Engineering': {'type': 'build_building', 'building': 'Aqueduct', 'description': 'Build an Aqueduct'},
    'Currency': {'type': 'trade_route', 'description': 'Establish a trade route'},
    'Military Tactics': {'type': 'kill_count', 'count': 5, 'description': 'Kill 5 enemy units'},
    'Education': {'type': 'build_building', 'building': 'Library', 'description': 'Build a Library'},
    'Printing': {'type': 'build_count', 'building': 'University', 'count': 2, 'description': 'Build 2 Universities'},
    'Gunpowder': {'type': 'build_building', 'building': 'Armory', 'description': 'Build an Armory'},
    'Astronomy': {'type': 'build_building', 'building': 'University', 'description': 'Build a University'},
}
```

When a eureka condition is met:
- Grant 50% of remaining research cost as free progress
- Show notification: "💡 Eureka! Writing — you met another civilization! (+50% research)"
- Visual effect: golden sparkle on tech tree node

Add `EurekaTracker` class in `tech.py`:
- Listens for game events (unit killed, building built, city founded, etc.)
- Checks against conditions
- Applies boost once per tech per game
- Tracked in save file

### 9.2 Worker Improvements

Add tile improvement system. Workers (already a unit type in game_data) can improve tiles:

New file: `improvements.py`:

```python
IMPROVEMENTS = {
    'Farm': {
        'valid_terrain': [TerrainType.PLAINS, TerrainType.GRASSLAND],
        'yields': {'food': 1},
        'tech_required': 'Agriculture',
        'build_turns': 3,
    },
    'Mine': {
        'valid_terrain': [TerrainType.HILLS, TerrainType.MOUNTAIN],
        'yields': {'production': 1},
        'tech_required': 'Mining',
        'build_turns': 3,
    },
    'Quarry': {
        'valid_terrain': [TerrainType.HILLS],
        'valid_resource': [ResourceType.STONE],
        'yields': {'production': 1},
        'tech_required': 'Mining',
        'build_turns': 3,
    },
    'Lumber Mill': {
        'valid_terrain': [TerrainType.FOREST],
        'yields': {'production': 1},
        'tech_required': 'Construction',
        'build_turns': 3,
    },
    'Trading Post': {
        'valid_terrain': 'any',
        'yields': {'gold': 1},
        'tech_required': 'Currency',
        'build_turns': 3,
    },
    'Plantation': {
        'valid_terrain': [TerrainType.PLAINS, TerrainType.GRASSLAND],
        'valid_resource': [ResourceType.SILK, ResourceType.INCENSE],
        'yields': {'gold': 1, 'food': 0.5},
        'tech_required': 'Calendar',
        'build_turns': 3,
    },
    'Fishing Boat': {
        'valid_terrain': [TerrainType.COAST, TerrainType.OCEAN],
        'valid_resource': [ResourceType.FISH],
        'yields': {'food': 1},
        'tech_required': 'Sailing',
        'build_turns': 2,
    },
    'Pasture': {
        'valid_terrain': [TerrainType.PLAINS, TerrainType.GRASSLAND],
        'valid_resource': [ResourceType.HORSES],
        'yields': {'production': 1},
        'tech_required': 'Animal Husbandry',
        'build_turns': 3,
    },
}
```

Worker actions:
- Select worker -> action bar shows available improvements for current tile
- Worker starts building improvement (takes N turns)
- Worker auto-continues to next improvement in queue (or idles)
- Improvements visible on map as overlay icons
- Improvements destroyed when pillaged (enemy unit action)
- Harvesting: Remove a tile feature (forest, marsh) for one-time yield burst (+20 production from chopping forest)

### 9.3 Wonders

Add unique buildings that only one civilization can build. First civ to complete gets it; others lose their progress.

New section in `game_data.py`:

```python
WONDERS = {
    'Pyramids': {
        'era': Era.ANCIENT,
        'cost': 220,
        'terrain_requirement': 'DESERT adjacent',
        'effects': {'worker_build_speed': 1.25, 'free_worker': True},
        'description': 'Workers build improvements 25% faster. Receive a free Worker.',
    },
    'Great Library': {
        'era': Era.ANCIENT,
        'cost': 200,
        'terrain_requirement': 'Campus adjacent',
        'effects': {'eureka_bonus': 0.1, 'free_tech': 'random_ancient'},
        'description': 'Eureka bonuses increased to 60%. Receive a random Ancient tech.',
    },
    'Stonehenge': {
        'era': Era.ANCIENT,
        'cost': 180,
        'terrain_requirement': 'STONE adjacent',
        'effects': {'free_great_prophet': True, 'faith_per_turn': 2},
        'description': 'Found a religion immediately. +2 Faith per turn.',
    },
    'Colosseum': {
        'era': Era.CLASSICAL,
        'cost': 300,
        'terrain_requirement': 'Entertainment adjacent',
        'effects': {'happiness_all_cities': 3},
        'description': '+3 Happiness in all cities within 6 tiles.',
    },
    'Hagia Sophia': {
        'era': Era.MEDIEVAL,
        'cost': 400,
        'terrain_requirement': 'Holy Site adjacent',
        'effects': {'faith_per_turn': 4, 'missionary_spread': 2},
        'description': '+4 Faith. Missionaries can spread religion 2 extra times.',
    },
    'Oxford University': {
        'era': Era.RENAISSANCE,
        'cost': 500,
        'terrain_requirement': 'Campus adjacent',
        'effects': {'free_tech': 'random_current_era', 'science_bonus': 0.2},
        'description': 'Free technology. +20% Science in this city.',
    },
}
```

Implementation:
- Wonders are built in city production queues like buildings
- Only one civ can build each wonder — check globally before allowing
- If another civ completes it first, refund 50% of invested production as gold
- Wonder appears on the map as a special tile marker
- Wonder effects apply immediately on completion
- Show "WONDER COMPLETED" cinematic-style notification

### 9.4 Great People

New file: `great_people.py`:

```python
GREAT_PERSON_TYPES = {
    'Great General': {
        'points_from': 'Encampment',
        'passive_bonus': {'combat_strength': 5, 'range': 2},  # aura effect
        'retire_action': 'Create Citadel (fort + culture bomb)',
    },
    'Great Scientist': {
        'points_from': 'Campus',
        'retire_action': 'Trigger Eureka for all available techs in current era',
    },
    'Great Engineer': {
        'points_from': 'Industrial Zone',
        'retire_action': 'Rush production in a city (+200 production)',
    },
    'Great Merchant': {
        'points_from': 'Commercial Hub',
        'retire_action': 'Create trade route with +4 gold per turn',
    },
    'Great Prophet': {
        'points_from': 'Holy Site',
        'retire_action': 'Found a religion or add a belief',
    },
}
```

Implementation:
- Great Person Points (GPP) generated each turn from districts
- Each civ accumulates GPP separately per type
- First civ to reach threshold recruits the Great Person
- Great Person spawns in the generating city
- Can move on map, has a one-time "retire" action
- Competitive: only one civ gets each Great Person
- Show GPP race progress in a "Great People" panel

### 9.5 Combat Improvements

Enhance `combat.py` with:

**Zone of Control**: Military units exert ZoC on all 6 adjacent hexes. Enemy units cannot move through ZoC hexes without stopping. Forces tactical positioning.

**Flanking Bonus**: +2 combat strength per friendly unit adjacent to the target (max +12). Encourages combined arms.

**Counter System**: Add unit category bonuses:
```python
COUNTER_BONUSES = {
    'Spearman': {'vs_Cavalry': 10},
    'Pikeman': {'vs_Cavalry': 10, 'vs_Knight': 10},
    'Archer': {'vs_Infantry': 5},
    'Cavalry': {'vs_Archer': 5, 'vs_Siege': 10},
    'Siege': {'vs_City': 15, 'vs_Walls': 20},
}
```

**Ranged Combat**: Ranged units can attack without taking return damage, but only within their range. Melee units must be adjacent.

**Fortify Action**: Unit digs in. +3 defense first turn, +6 after 2 turns. Lost when moving.

**Promotion Trees**: Replace flat tier bonuses with branching choices:
```
Warrior promotion tree:
Level 1: [Battlecry: +7 vs melee] OR [Tortoise: +10 vs ranged]
Level 2: [Charge: +5 attack on open terrain] OR [Shield Wall: +5 defense on any]
Level 3: [Elite: +7 all combat] OR [Healer: Heal adjacent allies 10 HP/turn]
```

**Combat Preview**: Before attack, show predicted outcome:
- Attacker strength (base + terrain + flanking + promotion + counter)
- Defender strength (base + terrain + fortify + promotion)
- Estimated damage to both sides
- Win probability percentage

### 9.6 Adjacency Bonus Calculation

Districts in `game_data.py` already have `adjacency_bonus` dicts but they're never calculated. Implement:

When placing a district, calculate bonus from adjacent tiles/districts:
```python
def calculate_adjacency_bonus(city, district_type, hex_q, hex_r, hex_map):
    bonus = 0
    adj_rules = DISTRICTS[district_type]['adjacency_bonus']
    for neighbor_q, neighbor_r in hex_map.get_neighbors(hex_q, hex_r):
        tile = hex_map.get_tile(neighbor_q, neighbor_r)
        # Check terrain bonuses
        if tile.terrain.name in adj_rules:
            bonus += adj_rules[tile.terrain.name]
        # Check if neighbor has a district
        neighbor_district = city.get_district_at(neighbor_q, neighbor_r)
        if neighbor_district and 'District' in adj_rules:
            bonus += adj_rules['District']
    return bonus
```

District placement should show adjacency preview (color-coded numbers on candidate hexes).

### 9.7 Housing and Amenities

**Housing** (limits population growth):
- Base housing: 2 (no fresh water), 3 (coast), 5 (river/lake)
- Granary: +2 housing
- Aqueduct district: +2 housing (must be adjacent to river AND city center)
- Neighborhood district: +4-10 housing based on tile appeal
- When population >= housing: growth rate -50%. At population > housing + 5: growth stops

**Amenities** (per-city happiness replacing empire-wide):
- Each city needs 1 amenity per 2 citizens above 2
- Sources: luxury resources (1 amenity per unique luxury, shared across 4 cities), entertainment buildings, wonders
- At deficit: -10% growth and production per missing amenity
- At surplus: +5% growth per extra amenity (up to +20%)

### Deliverables for Phase 7
- `improvements.py` — worker improvement system
- Eureka system in `tech.py`
- Wonder data in `game_data.py`, wonder logic in `city.py`
- `great_people.py` — GPP generation, recruitment, retire actions
- Combat enhancements in `combat.py` (ZoC, flanking, counters, ranged, fortify, previews, promotion trees)
- Adjacency bonus calculation wired into district placement
- Housing and amenities in `city_growth.py` / `happiness_system.py`
- All new mechanics have corresponding UI in the Pygame GUI

---

## 10. Phase 8: Advanced CK-Style Mechanics

### Goal
Deepen the dynasty/character systems that make CivKings unique — the CK half of the hybrid.

### 10.1 Stress System

Add to `simulation.py`:

```python
class StressSystem:
    """Tracks ruler stress (0-300). Acting against personality triggers stress gain."""

    THRESHOLDS = {
        0: {'name': 'Composed', 'penalties': {}},
        100: {'name': 'Stressed', 'penalties': {'fertility': -0.1}},
        200: {'name': 'Overwhelmed', 'penalties': {'fertility': -0.3, 'health': -1}},
        300: {'name': 'Breaking Point', 'penalties': {'fertility': -0.5, 'health': -2}},
    }

    STRESS_TRIGGERS = {
        # (trait, action) -> stress gain
        ('Compassionate', 'execute_prisoner'): 30,
        ('Honest', 'plot_assassination'): 25,
        ('Just', 'break_treaty'): 20,
        ('Peaceful', 'declare_war'): 25,
        ('Brave', 'retreat_from_battle'): 15,
        ('Generous', 'raise_taxes'): 10,
        ('Cruel', 'show_mercy'): 15,  # Cruel rulers GAIN stress from mercy
        ('Ambitious', 'accept_unfavorable_peace'): 20,
    }

    COPING_MECHANISMS = {
        # At stress thresholds, ruler may develop a coping trait
        'Drunkard': {'stress_loss': -20, 'health': -1, 'diplomacy': -2},
        'Glutton': {'stress_loss': -15, 'health': -1, 'stewardship': -1},
        'Recluse': {'stress_loss': -25, 'diplomacy': -3},
        'Flagellant': {'stress_loss': -30, 'health': -2, 'faith': +2},
        'Confider': {'stress_loss': -10, 'intrigue': -2},  # Reveals secrets
    }
```

Integration:
- Every player action checks against ruler's traits
- If action contradicts a trait, gain stress
- At each threshold, offer coping mechanism choice (popup)
- Stress decays slowly each turn (-2 base)
- Court chaplain/physician can reduce stress
- Creates genuine roleplaying tension: your ruler's personality limits optimal play

### 10.2 Succession That Actually Works

This is THE CK mechanic. When a ruler dies, the realm must deal with succession:

**Primogeniture**: Eldest child inherits everything. Stable but requires managing heirs.

**Gavelkind (Partition)**: Titles/cities split among children.
- If ruler has 3 cities and 2 sons: eldest gets capital + 1 city, second son gets 1 city
- Second son becomes independent AI (or vassal if vassal system exists)
- THIS IS THE KEY ANTI-SNOWBALL MECHANIC
- Player must either: have only one heir, change succession law (costs stability), or reconquer lost cities

**Elective**: Faction leaders vote. Player can influence votes with gold/intrigue but doesn't control outcome.

**Seniority**: Oldest dynasty member inherits. Can lead to very old, about-to-die rulers.

Implementation:
- On ruler death, execute succession law
- For partition: actually split cities to AI-controlled heirs (heirs become new AI civs or vassals)
- Succession crisis event: -25 stability, possible faction demands
- New ruler may have different traits affecting play style
- Heir education: can assign lifestyle focus to children (affects stat growth)

### 10.3 Hooks and Secrets System

New file: `secrets.py`:

```python
class Secret:
    """Something a character wants to hide."""
    def __init__(self, owner: str, secret_type: str, severity: str):
        self.owner = owner  # Character who has the secret
        self.type = secret_type  # 'affair', 'murder', 'heresy', 'embezzlement'
        self.severity = severity  # 'minor', 'major', 'criminal'
        self.known_by = []  # Characters who know this secret

class Hook:
    """Leverage one character has over another."""
    def __init__(self, holder: str, target: str, hook_type: str, source: Secret):
        self.holder = holder
        self.target = target
        self.type = hook_type  # 'weak' (one-time) or 'strong' (permanent)
        self.source = source
        self.used = False
```

Uses:
- Hooks let you force favorable diplomatic actions (demand gold, force alliance, prevent betrayal)
- Secrets are discovered via spy/intrigue actions
- Weak hooks are consumed on use; strong hooks persist
- AI characters also accumulate and use hooks
- Creates a web of political leverage beyond simple opinion numbers

### 10.4 Scheme System Enhancement

Upgrade `plots.py` from simple progress bars to a proper scheme system:

- **Power vs. Resistance**: Scheme has attack power (intrigue skill + agents) vs target's resistance (spymaster skill + court security)
- **Agent recruitment**: Each scheme can recruit up to 5 agents from characters with hooks or who hate the target
- **Secrecy**: Each agent adds power but also increases detection risk
- **Detection**: If discovered, massive opinion penalty, possible war, loss of hooks
- **Scheme types**:
  - Murder: Kill target character. Power from agents' intrigue. Risk: imprisonment/war if caught
  - Fabricate Claim: Create legal justification for war against target. Slow but safe
  - Sway: Improve target's opinion of you. Diplomacy-based
  - Seduce: Romance target for alliance/hooks. Risk: stress if caught, scandal
  - Steal Technology: Copy a tech the target has researched. Intrigue-based

### 10.5 Dynasty Legacies

Add permanent dynasty-wide bonuses earned over generations:

```python
DYNASTY_LEGACIES = {
    'Warfare': [
        {'name': 'Soldiers', 'cost': 250, 'effect': {'military_unit_strength': 2}},
        {'name': 'Captains', 'cost': 500, 'effect': {'military_unit_xp_gain': 0.2}},
        {'name': 'Strategists', 'cost': 750, 'effect': {'combat_width': 1}},
        {'name': 'Generals', 'cost': 1000, 'effect': {'knight_effectiveness': 0.5}},
        {'name': 'Conquerors', 'cost': 1500, 'effect': {'casus_belli_prestige': 0.5}},
    ],
    'Law': [
        {'name': 'Legislators', 'cost': 250, 'effect': {'stability_gain': 0.1}},
        {'name': 'Judges', 'cost': 500, 'effect': {'faction_influence_reduction': 0.1}},
        {'name': 'Chancellors', 'cost': 750, 'effect': {'vassal_opinion': 5}},
        {'name': 'High Justiciars', 'cost': 1000, 'effect': {'succession_crisis_reduction': 0.5}},
        {'name': 'Lawgivers', 'cost': 1500, 'effect': {'government_change_cost': -0.5}},
    ],
    'Blood': [
        {'name': 'Healthy', 'cost': 250, 'effect': {'health_bonus': 0.5}},
        {'name': 'Robust', 'cost': 500, 'effect': {'fertility_bonus': 0.1}},
        {'name': 'Fecund', 'cost': 750, 'effect': {'child_stat_bonus': 1}},
        {'name': 'Strong Blood', 'cost': 1000, 'effect': {'positive_trait_chance': 0.1}},
        {'name': 'Pure Blood', 'cost': 1500, 'effect': {'genius_chance': 0.05}},
    ],
    'Erudition': [
        {'name': 'Scholars', 'cost': 250, 'effect': {'science_bonus': 0.05}},
        {'name': 'Sages', 'cost': 500, 'effect': {'tech_cost_reduction': 0.05}},
        {'name': 'Philosophers', 'cost': 750, 'effect': {'culture_bonus': 0.1}},
        {'name': 'Visionaries', 'cost': 1000, 'effect': {'eureka_bonus': 0.1}},
        {'name': 'Enlightened', 'cost': 1500, 'effect': {'era_score_bonus': 0.2}},
    ],
}
```

- Legacies cost Renown (dynasty currency earned from landed dynasty members)
- Each track has 5 levels, each more expensive
- Bonuses are permanent and apply to all dynasty members
- Creates a multi-generational progression system
- Legacy decisions visible in Dynasty popup

### 10.6 Congenital Traits

Add heritable traits that make breeding/marriage strategic:

```python
CONGENITAL_TRAITS = {
    'Beautiful': {'diplomacy': 3, 'fertility': 0.1, 'tier': 'good', 'inherit_chance': 0.1},
    'Genius': {'all_stats': 2, 'tier': 'good', 'inherit_chance': 0.05},
    'Herculean': {'martial': 3, 'health': 1, 'tier': 'good', 'inherit_chance': 0.1},
    'Fecund': {'fertility': 0.3, 'tier': 'good', 'inherit_chance': 0.15},
    'Albino': {'diplomacy': -1, 'tier': 'neutral', 'inherit_chance': 0.1},
    'Clubfooted': {'martial': -1, 'tier': 'bad', 'inherit_chance': 0.1},
    'Inbred': {'all_stats': -3, 'health': -3, 'fertility': -0.3, 'tier': 'bad', 'inherit_chance': 0.25},
}
```

Marriage system:
- Can arrange marriages with other dynasty members or foreign characters
- Marriage alliances affect diplomacy
- Children inherit traits from both parents
- Blood legacy perks increase good trait inheritance

### Deliverables for Phase 8
- Stress system in `simulation.py`
- Succession mechanics that actually split realms
- `secrets.py` — hooks and secrets
- Enhanced scheme system in `plots.py`
- Dynasty legacies with renown currency
- Congenital traits and marriage system
- All mechanics have corresponding UI popups/panels

---

## 11. Phase 9: Advanced Civ-Style Mechanics

### Goal
Add the Civ-side features that create strategic depth and replayability.

### 11.1 Era Score and Golden/Dark Ages

New file: `era_system.py`:

```python
class EraSystem:
    """Tracks era score and determines Golden/Dark/Normal ages."""

    THRESHOLDS = {
        'dark_age': 12,    # Below this = Dark Age
        'normal': 12,      # At or above = Normal Age
        'golden_age': 24,  # At or above = Golden Age
        'heroic_age': 24,  # Golden after Dark = Heroic
    }

    HISTORIC_MOMENTS = {
        'first_to_research_tech': 3,
        'first_city_on_continent': 4,
        'first_wonder_built': 5,
        'won_battle_against_stronger': 3,
        'founded_religion': 5,
        'met_all_civs': 3,
        'circumnavigated': 5,  # explored entire map edge
        'built_unique_unit': 2,
        'recruited_great_person': 2,
        'golden_age_without_free_inquiry': 2,
    }

    ERA_BONUSES = {
        'Dark': {'loyalty': -3, 'policies': 'dark_age_policies_available'},
        'Normal': {},
        'Golden': {'dedication_slots': 1, 'loyalty': +3},
        'Heroic': {'dedication_slots': 3, 'loyalty': +3},
    }
```

When transitioning between eras:
- Calculate era score from accumulated Historic Moments
- Determine Golden/Normal/Dark Age
- Apply era bonuses for the new era
- Golden Age: choose a "dedication" (focus bonus for the era)
- Dark Age: loyalty penalties BUT unlock special dark-age-only policies (high risk/reward)
- Show era transition cinematic: summary of achievements, new era declared

### 11.2 Loyalty System

Add to `city.py` or new file `loyalty.py`:

- Each city has loyalty (0-100). Below 0 = city revolts and becomes independent
- Loyalty sources:
  - +8 per turn from nearby own cities (within 9 tiles)
  - -3 per turn from nearby foreign cities (their culture pressure)
  - +3 from Golden Age
  - -3 from Dark Age
  - +1 per happiness above 0
  - -2 per happiness below 0
  - +governor bonus (if governor system exists)
- Conquered cities start at 50 loyalty and can flip back if loyalty drops
- Creates natural limit on empire expansion (can't hold cities too far from core)
- Anti-snowball: conquering lots of cities creates loyalty problems everywhere

### 11.3 Policy Card System

Enhance `tech_policies.py`:

```python
POLICY_CARDS = {
    # Military policies
    'Discipline': {'type': 'military', 'effect': {'melee_strength': 5}},
    'Survey': {'type': 'military', 'effect': {'scout_movement': 1}},
    'Conscription': {'type': 'military', 'effect': {'unit_maintenance': -1}},
    'Levee en Masse': {'type': 'military', 'effect': {'unit_production': 0.5}},

    # Economic policies
    'God King': {'type': 'economic', 'effect': {'faith': 1, 'gold': 1}},
    'Urban Planning': {'type': 'economic', 'effect': {'city_production': 1}},
    'Caravansaries': {'type': 'economic', 'effect': {'trade_gold': 2}},
    'Market Economy': {'type': 'economic', 'effect': {'luxury_gold': 2}},

    # Diplomatic policies
    'Diplomatic League': {'type': 'diplomatic', 'effect': {'alliance_points': 1}},
    'Charismatic Leader': {'type': 'diplomatic', 'effect': {'influence': 2}},

    # Wildcard policies
    'Revelation': {'type': 'wildcard', 'effect': {'great_prophet_points': 2}},
    'Inspiration': {'type': 'wildcard', 'effect': {'great_scientist_points': 2}},
}

GOVERNMENTS = {
    'Chiefdom': {'military_slots': 1, 'economic_slots': 1, 'diplomatic_slots': 0, 'wildcard_slots': 0},
    'Autocracy': {'military_slots': 2, 'economic_slots': 1, 'diplomatic_slots': 0, 'wildcard_slots': 1},
    'Oligarchy': {'military_slots': 1, 'economic_slots': 1, 'diplomatic_slots': 1, 'wildcard_slots': 1},
    'Classical Republic': {'military_slots': 0, 'economic_slots': 2, 'diplomatic_slots': 1, 'wildcard_slots': 1},
    'Monarchy': {'military_slots': 2, 'economic_slots': 1, 'diplomatic_slots': 1, 'wildcard_slots': 1},
    'Merchant Republic': {'military_slots': 1, 'economic_slots': 2, 'diplomatic_slots': 1, 'wildcard_slots': 2},
    'Theocracy': {'military_slots': 2, 'economic_slots': 1, 'diplomatic_slots': 1, 'wildcard_slots': 1},
    'Democracy': {'military_slots': 1, 'economic_slots': 1, 'diplomatic_slots': 2, 'wildcard_slots': 2},
    'Fascism': {'military_slots': 4, 'economic_slots': 1, 'diplomatic_slots': 0, 'wildcard_slots': 1},
    'Communism': {'military_slots': 2, 'economic_slots': 3, 'diplomatic_slots': 1, 'wildcard_slots': 0},
}
```

- Governments unlocked via Civic research
- Changing government costs anarchy turns (0 yields for N turns)
- Policy cards can be freely swapped when completing a Civic
- UI: Government screen showing slots and available cards (drag-and-drop)

### 11.4 Trade Routes with Trader Units

Enhance `external_trade_routes.py`:

- Trader is a civilian unit (built in cities with Commercial Hub)
- Select Trader -> choose destination city (domestic or foreign)
- Route lasts 20 turns, then Trader returns to origin
- Domestic route: transfers food/production from rich city to poor city
- International route: gold for both civs, spreads religion, establishes road
- Trader visible on map, moving along route
- Can be pillaged by enemy units during war (Trader captured, route broken)
- Show active routes on map as dotted lines (gold for domestic, colored for international)
- Maximum trade routes: 1 base + 1 per Commercial Hub

### 11.5 Religion Enhancement

Upgrade `religion.py`:

- **Religion founding**: First civ to accumulate 25 Faith can found a religion via Great Prophet
- **Beliefs**: Choose 2 founder beliefs + 2 follower beliefs:
  ```python
  FOUNDER_BELIEFS = {
      'Tithe': {'gold_per_follower': 0.1},
      'Church Property': {'faith_per_city_with_temple': 2},
      'Papal Primacy': {'diplomatic_favor_per_turn': 1},
  }
  FOLLOWER_BELIEFS = {
      'Choral Music': {'culture_from_shrines_temples': True},
      'Religious Community': {'food_production_bonus': 0.1},
      'Zen Meditation': {'happiness_per_shrine': 1},
  }
  ```
- **Missionaries**: Civilian unit that spreads religion (3 charges)
- **Apostles**: Stronger spreaders with promotion abilities
- **Religious combat**: Apostles can engage in theological combat
- **Holy wars**: Casus belli for civs with different religions

### 11.6 Victory Condition Overhaul

Make each victory path require specific gameplay systems:

```python
VICTORY_CONDITIONS = {
    'Domination': {
        'condition': 'Control all original capital cities',
        'systems_required': ['military', 'combat', 'diplomacy'],
    },
    'Science': {
        'condition': 'Complete 3 space projects (Satellite, Moon Landing, Mars Colony)',
        'requires': {
            'Satellite': {'tech': 'Rocketry', 'production': 1500},
            'Moon Landing': {'tech': 'Advanced Flight', 'production': 2000},
            'Mars Colony': {'tech': 'Nanotechnology', 'production': 3000},
        },
    },
    'Culture': {
        'condition': 'Attract more visiting tourists than any civ has domestic tourists',
        'systems_required': ['great_works', 'wonders', 'tourism'],
        'tourism_from': ['great_works', 'wonders', 'national_parks', 'relics'],
    },
    'Religious': {
        'condition': 'Your religion is majority in every civilization',
        'systems_required': ['religion', 'missionaries', 'faith'],
    },
    'Diplomatic': {
        'condition': 'Accumulate 20 Diplomatic Victory Points',
        'points_from': ['world_congress_votes', 'emergencies_won', 'alliances'],
    },
    'Dynasty': {
        'condition': 'Maintain unbroken dynasty for 15 generations with 5+ dynasty legacies',
        'systems_required': ['succession', 'dynasty_legacies', 'character_traits'],
    },
}
```

### Deliverables for Phase 9
- `era_system.py` — era score, golden/dark ages, historic moments
- `loyalty.py` — per-city loyalty with cultural pressure
- Enhanced `tech_policies.py` — policy cards and government system
- Enhanced `external_trade_routes.py` — trader units, route visualization
- Enhanced `religion.py` — beliefs, missionaries, religious combat
- Victory condition overhaul in `victory.py`
- All mechanics have UI panels/popups

---

## 12. Phase 10: AI Overhaul

### Goal
Make AI opponents that actually play the game — build cities, research techs, train armies, declare wars, and pursue victory conditions.

### 10.1 AI Decision Framework

Restructure `ai.py` around a priority-based decision system:

```python
class AIPlayer:
    def take_turn(self, game: Game):
        """Execute all AI decisions for one turn."""
        self._evaluate_priorities(game)
        self._manage_research(game)
        self._manage_production(game)
        self._manage_workers(game)
        self._manage_military(game)
        self._manage_diplomacy(game)
        self._evaluate_expansion(game)
        self._manage_religion(game)

    def _evaluate_priorities(self, game):
        """Assess game state and set strategic priorities."""
        # Military priority: increases when threatened or planning war
        # Science priority: increases when behind in tech
        # Economy priority: increases when gold is low
        # Expansion priority: increases when good land is available
        # Calculate based on: relative power, tech position, available land, threats
```

### 10.2 AI City Management

The AI must:
- Build appropriate buildings (prioritize food early, production mid, science late)
- Build districts when population allows
- Consider adjacency bonuses when placing districts
- Build military units when threatened
- Build settlers when good land is available
- Manage production queues intelligently (not just random)

### 10.3 AI Military

The AI must:
- Build armies proportional to threats
- Move units toward strategic targets
- Declare war when strong enough (2:1 military advantage)
- Retreat when losing
- Fortify defensive positions
- Garrison cities
- Use combined arms (don't send archers alone)

### 10.4 AI Diplomacy

The AI must:
- Propose treaties when beneficial
- Refuse treaties when threatening
- Form alliances against strong opponents
- Declare war with casus belli when available
- Respond to player diplomatic actions
- Have personality (aggressive, peaceful, scientific, religious)
- Remember betrayals (grudge system)

### 10.5 Difficulty Scaling

```python
DIFFICULTY_MODIFIERS = {
    'Rookie':   {'yields': 0.8, 'combat': 0.9, 'starting_units': 0, 'ai_smarts': 0.5},
    'Easy':     {'yields': 0.9, 'combat': 0.95, 'starting_units': 0, 'ai_smarts': 0.7},
    'Standard': {'yields': 1.0, 'combat': 1.0, 'starting_units': 0, 'ai_smarts': 1.0},
    'Hard':     {'yields': 1.1, 'combat': 1.05, 'starting_units': 1, 'ai_smarts': 1.0},
    'Immortal': {'yields': 1.2, 'combat': 1.1, 'starting_units': 2, 'ai_smarts': 1.0},
}
```

### Deliverables for Phase 10
- Complete `ai.py` rewrite with priority-based decisions
- AI builds cities, researches techs, trains armies, fights wars
- AI uses diplomacy (treaties, wars, alliances)
- Difficulty scaling via yield bonuses AND smarter decisions
- AI actions visible in event log ("Egypt declared war on Greece")

---

## 13. Phase 11: Polish, Balance, Tutorial

### Goal
Make the game accessible, balanced, and enjoyable.

### 11.1 Tutorial System

New file: `tutorial.py`:

First-game tutorial that guides through the first 10 turns:

1. **Turn 1**: "Welcome to CivKings! Click your Settler to select it." -> highlight settler
2. **Turn 1**: "Click a green hex to found your capital city." -> show valid settlement spots
3. **Turn 2**: "Your city needs a Warrior for defense. Click Production to start building one." -> highlight production button
4. **Turn 2**: "Select a technology to research. Click the Tech Tree button." -> highlight tech button
5. **Turn 3**: "Move your Warrior to explore. Click the Warrior, then click a blue hex." -> show movement
6. **Turn 5**: "You've met Egypt! Check the Diplomacy panel to see your relations."
7. **Turn 8**: "Your city has grown! Consider building a district for specialized yields."
8. **Turn 10**: "Tutorial complete! Good luck, ruler. Your dynasty depends on you."

Implementation:
- Tutorial checks game state each turn
- Shows contextual hint popup with arrow pointing to relevant UI element
- Can be dismissed or disabled in settings
- Only triggers on "first game" flag

### 11.2 Balance Pass

After all mechanics are implemented, do a balance pass:

**Unit costs and strengths**: Compare unit production cost vs combat value. A unit costing twice as much should be roughly 1.5x stronger (not 2x — expensive units should be efficient but not OP).

**Tech costs**: Ensure each era takes roughly the same number of turns at appropriate science levels. Ancient: 15-25 turns total. Classical: 20-30. Medieval: 25-35.

**Building costs**: Production costs should scale with era. A Granary (Ancient) costs 40 production. A Factory (Industrial) costs 200.

**Growth curves**: Cities should reach pop 3 by turn 15, pop 6 by turn 40, pop 10 by turn 80. Adjust food/housing numbers accordingly.

**Gold economy**: Players should be gold-positive early game, struggling mid-game (military expansion), and rich late-game. Maintenance costs are the lever.

**AI pacing**: AI should found 2nd city by turn 20, have 4 cities by turn 60, declare first war by turn 40-80.

### 11.3 Keyboard Shortcuts

Full keyboard shortcut map:

| Key | Action |
|-----|--------|
| Enter | End Turn |
| Space | Skip unit / Next notification |
| Tab | Next unit with movement |
| Escape | Deselect / Close popup |
| M | Move selected unit |
| A | Attack with selected unit |
| F | Fortify selected unit |
| P | Open Production for selected city |
| T | Open Tech Tree |
| D | Open Diplomacy |
| Y | Open Dynasty |
| G | Toggle tile yield display |
| B | Buy production with gold |
| S | Quick save |
| L | Quick load |
| F1 | Open Encyclopedia |
| F5 | Quick save |
| F9 | Quick load |
| +/- | Zoom in/out |
| Home | Center on capital |
| . (period) | Cycle next city |

### 11.4 Settings Panel

Accessible from main menu and in-game:

- **Audio**: Master volume, Music volume, SFX volume (sliders)
- **Display**: Fullscreen toggle, Resolution selection
- **Gameplay**: Auto-save frequency, Turn timer (optional), Show tile yields, Animation speed
- **Tutorial**: Enable/disable hints
- Stored in `~/.civkings/settings.json`

### Deliverables for Phase 11
- `tutorial.py` — 10-turn guided tutorial
- Balance spreadsheet/pass on all numeric values
- Full keyboard shortcut implementation
- Settings panel with persistence
- Help/encyclopedia content for all game concepts

---

## 14. Phase 12: Cleanup and Final Integration

### Goal
Delete legacy code, verify all systems are wired together, and ensure the game is shippable.

### 12.1 Delete Legacy Files

Remove these files that are no longer needed:

- `gui.py` (old tkinter GUI — replaced by pygame_app/)
- `gui_map.py` (old tkinter map renderer)
- `gui_panels.py` (old tkinter panels)
- `gui_popups.py` (old tkinter popups)
- `gui_combat.py` (old tkinter combat display)
- `victory_ui.py` (old tkinter victory screen — replaced by pygame_app/popups/victory.py)
- `visual_effects.py` (old tkinter particle system)
- `sound_effects.py` (old winsound hack)
- `gui_popups_backup.py` (backup file)
- `gui_popups_original.py` (backup file)
- `fix_canvas.py`, `fix_popup.py`, `fix_popups.py`, `fix_popups2.py` (old fix scripts)
- `map.py` (duplicate of hex_map.py)
- `clean.py` (cleanup utility, no longer needed)
- `ui.py` (old text UI — unless keeping as debug/headless mode)

### 12.2 Update Entry Point

`main.py` should launch the Pygame app:
```python
def main():
    from pygame_app.app import GameApp
    app = GameApp()
    app.run()

if __name__ == "__main__":
    main()
```

### 12.3 Integration Verification

For EVERY new system added, grep for all new symbols and verify they are:
1. Imported where used
2. Called in the correct game loop path
3. Saved/loaded in save_system.py
4. Displayed in the appropriate UI panel/popup
5. Tested with at least one unit test

Specific verification checklist in Section 16.

### Deliverables for Phase 12
- All legacy files deleted
- No dead imports, no unused functions
- Save/load works with all new systems
- Game runs from `python main.py` cleanly
- All tests pass

---

## 15. File Manifest

### New Files to Create

```
pygame_app/
    __init__.py
    app.py
    theme.json
    screens/
        __init__.py
        base.py
        main_menu.py
        game_screen.py
        new_game_dialog.py
    map/
        __init__.py
        hex_renderer.py
        camera.py
        minimap.py
        fog_of_war.py
        tile_atlas.py
        highlights.py
        animations.py
    panels/
        __init__.py
        resource_bar.py
        city_panel.py
        unit_panel.py
        event_log.py
        turn_summary.py
        action_bar.py
    popups/
        __init__.py
        production.py
        tech_tree.py
        diplomacy.py
        dynasty.py
        combat_result.py
        city_detail.py
        victory.py
        encyclopedia.py
        event_choice.py
        trade.py
        government.py
        great_people.py
        era_transition.py
    effects/
        __init__.py
        particles.py
        animations.py
        transitions.py
    audio/
        __init__.py
        sound_manager.py
        music_manager.py

assets/
    tiles/
    resources/
    units/
    buildings/
    ui/
    sounds/
        ui/
        combat/
        events/
    music/

tools/
    generate_hex_mask.py
    process_tiles.py
    batch_generate.py
    terrain_workflow.json
    resource_workflow.json
    unit_workflow.json

# New engine files
improvements.py
great_people.py
era_system.py
loyalty.py
secrets.py
tutorial.py
```

### Files to Modify

```
game.py          — add AI initialization, era system hooks, loyalty hooks
game_data.py     — add wonders, policy cards, eureka conditions, congenital traits
tech.py          — add eureka/inspiration system
city.py          — add housing, adjacency calculation, wonder building
combat.py        — add ZoC, flanking, counters, ranged, fortify, preview
military.py      — add fortification state, ranged flag, promotion trees
simulation.py    — add stress system, succession implementation
plots.py         — enhance scheme system (power vs resistance, agents)
diplomacy.py     — add grievances, warmongering penalty
religion.py      — add beliefs, missionaries, religious combat
victory.py       — overhaul victory conditions
tech_policies.py — add policy card system, government slots
ai.py            — complete rewrite of decision framework
city_growth.py   — add housing cap
happiness_system.py — convert to per-city amenities
save_system.py   — add all new systems to serialization
main.py          — update to launch Pygame app
requirements.txt — add pygame-ce, pygame-gui, Pillow
```

### Files to Delete

```
gui.py
gui_map.py
gui_panels.py
gui_popups.py
gui_combat.py
victory_ui.py
visual_effects.py
sound_effects.py
gui_popups_backup.py
gui_popups_original.py
fix_canvas.py
fix_popup.py
fix_popups.py
fix_popups2.py
map.py
clean.py
```

---

## 16. Integration Verification Checklist

**BLOCKING**: Every phase must pass its verification before the next phase starts.

### Phase 1 Verification
- [ ] `python main.py` opens Pygame window
- [ ] Main menu renders with title, buttons
- [ ] New Game dialog creates Game engine instance
- [ ] Theme.json colors match dark fantasy palette
- [ ] Window resizes correctly
- [ ] Quit button exits cleanly

### Phase 2 Verification
- [ ] Hex map renders with terrain tiles (or colored fallback)
- [ ] Camera pans with WASD/middle mouse drag
- [ ] Camera zooms with mouse wheel
- [ ] Only visible hexes are drawn (viewport culling)
- [ ] Click on hex returns correct (q, r) coordinates
- [ ] Fog of war shows explored vs unexplored
- [ ] Minimap renders and is clickable
- [ ] Cities appear on their hexes
- [ ] Units appear on their hexes

### Phase 3 Verification
- [ ] Resource bar shows all yields with correct formatting (no floating point garbage)
- [ ] City panel lists all player cities
- [ ] Unit panel lists all player units
- [ ] Event log scrolls and shows colored events
- [ ] Turn summary popup appears at start of each new turn
- [ ] Action bar changes based on selection (unit vs city vs nothing)
- [ ] End turn button warns about idle units/cities
- [ ] Tab cycles through units with remaining movement

### Phase 4 Verification
- [ ] Production popup shows available items by category
- [ ] Production queue supports add/remove/reorder
- [ ] Tech tree displays all techs with correct prerequisites
- [ ] Clicking tech starts research
- [ ] Diplomacy popup shows all known civs with relations
- [ ] Dynasty popup shows ruler, heir, traits, stats
- [ ] Combat result popup shows after combat
- [ ] Event choice popup shows when events fire
- [ ] Encyclopedia opens with F1 and has content for all game concepts

### Phase 5 Verification
- [ ] Button clicks produce sound effect
- [ ] Production complete plays chime
- [ ] Combat plays sword/arrow sound
- [ ] Background music plays and changes with era
- [ ] Volume controls work in settings
- [ ] Unit movement is animated (not teleported)
- [ ] Combat shows attack animation + damage numbers
- [ ] City growth shows glow effect

### Phase 6 Verification
- [ ] AI players have cities and units on the map at game start
- [ ] AI takes actions each turn (research, build, move units)
- [ ] AI actions visible in event log
- [ ] Save game preserves all state including AI
- [ ] Load game restores all state correctly
- [ ] 50 turns can be processed without crash

### Phase 7 Verification
- [ ] Eureka boost triggers and shows notification
- [ ] Workers can build improvements on valid tiles
- [ ] Improvements visible on map
- [ ] Wonders can be built (only one civ per wonder)
- [ ] Great People spawn from GPP and have retire actions
- [ ] Combat preview shows before attacking
- [ ] Flanking bonus applies correctly
- [ ] Counter bonuses apply correctly
- [ ] Adjacency bonuses calculated at district placement
- [ ] Housing limits population growth
- [ ] Amenities affect per-city happiness

### Phase 8 Verification
- [ ] Stress increases when acting against ruler traits
- [ ] Stress threshold effects apply (coping mechanisms)
- [ ] Ruler death triggers succession
- [ ] Gavelkind splits cities among heirs
- [ ] Hooks can be gained from secrets
- [ ] Hooks can force diplomatic actions
- [ ] Dynasty legacies purchasable with renown
- [ ] Legacy bonuses apply dynasty-wide
- [ ] Congenital traits inherited by children

### Phase 9 Verification
- [ ] Era score accumulates from historic moments
- [ ] Golden/Dark Age determined at era transition
- [ ] Golden Age dedication provides bonus
- [ ] Loyalty calculated per-city
- [ ] Low loyalty cities can revolt
- [ ] Policy cards slottable in government
- [ ] Government change works with anarchy period
- [ ] Trader units create routes
- [ ] Trade routes visible on map
- [ ] Religion can be founded with beliefs
- [ ] Missionaries spread religion
- [ ] All 6 victory conditions achievable

### Phase 10 Verification
- [ ] AI founds new cities
- [ ] AI researches techs progressively
- [ ] AI builds armies when threatened
- [ ] AI declares war when strong
- [ ] AI proposes peace when losing
- [ ] AI difficulty affects yields and behavior
- [ ] AI pursues at least one victory condition

### Phase 11 Verification
- [ ] Tutorial guides first 10 turns
- [ ] All keyboard shortcuts work
- [ ] Settings persist between sessions
- [ ] No unit costs 0 or negative
- [ ] No tech takes 0 turns
- [ ] Cities grow at reasonable rates
- [ ] AI founds 2nd city by turn 20

### Phase 12 Verification
- [ ] All legacy GUI files deleted
- [ ] `grep -r "import tkinter" *.py` returns nothing (except legacy ui.py if kept)
- [ ] `grep -r "from gui" *.py` returns nothing in non-deleted files
- [ ] All new symbols (functions, classes) are imported and called
- [ ] Save/load round-trips all new systems
- [ ] 100-turn game completes without crash
- [ ] All tests pass
- [ ] `python main.py` launches cleanly on fresh install with `pip install -r requirements.txt`

---

## Summary

This spec transforms CivKings from a broken-GUI tech demo into a fully playable strategy game by:

1. **Replacing the rendering layer** (tkinter -> Pygame-ce) for real game graphics and sound
2. **Generating professional art** (ComfyUI hex tiles, unit icons, UI elements) on local RTX 5090
3. **Adding 20+ missing mechanics** across both Civ and CK pillars
4. **Overhauling the AI** to actually play the game
5. **Polishing everything** with sound, animation, tutorial, and balance

The engine (12K lines) stays untouched except for new feature additions. The GUI (3.9K lines) is completely rewritten. Net new code is estimated at ~8-10K lines of Pygame GUI + ~3-4K lines of new engine features.

Each phase is independently testable with a verification checklist. CynCo can execute one phase at a time, verifying each before moving to the next.
