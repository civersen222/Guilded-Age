# CivKings Complete Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform CivKings from a broken-GUI tech demo into a fully playable Pygame-based strategy game with AI-generated art, sound, and 20+ new game mechanics.

**Architecture:** The existing Python game engine (~12K lines across 23 files) stays untouched. A new Pygame-ce + pygame_gui rendering layer replaces the broken tkinter GUI. ComfyUI generates hex tile art assets locally. New mechanics are added as new engine files or extensions to existing ones.

**Tech Stack:** Python 3.14, pygame-ce 2.5+, pygame_gui 0.6+, Pillow, ComfyUI (SDXL + Juggernaut XL), existing engine (game.py, hex_map.py, city.py, military.py, combat.py, tech.py, etc.)

**Spec:** `docs/superpowers/specs/2026-05-04-civkings-complete-overhaul-design.md`

**Project Root:** `C:\Users\civer\civkings`

---

## File Structure

### New files to create (Pygame GUI layer)

```
pygame_app/
    __init__.py                    # Package marker
    app.py                         # Main game loop, Pygame window, state machine
    theme.json                     # pygame_gui dark fantasy theme (colors, fonts, borders)
    constants.py                   # Shared color constants, layout sizes, FPS
    screens/
        __init__.py
        base.py                    # BaseScreen abstract class
        main_menu.py               # Title screen with New Game / Load / Quit
        new_game_dialog.py         # Civ selection, difficulty, map size, AI count
        game_screen.py             # Main gameplay coordinator (map + panels + popups)
    map/
        __init__.py
        tile_atlas.py              # Load sprite sheet atlas, fallback to colored hexes
        camera.py                  # Pan, zoom, viewport, smooth lerp, coordinate transforms
        hex_renderer.py            # Render hex tiles, resources, rivers, cities, units
        minimap.py                 # Corner minimap with viewport rect
        fog_overlay.py             # Three-state fog of war rendering
        highlights.py              # Selection glow, movement range, attack range
        map_animations.py          # Unit slide, combat flash, growth glow
    panels/
        __init__.py
        resource_bar.py            # Top bar: yields, turn counter, game speed
        city_panel.py              # Left sidebar: city list
        unit_panel.py              # Left sidebar: unit list
        event_log.py               # Right sidebar: scrollable colored events
        turn_summary.py            # Modal: start-of-turn notification queue
        action_bar.py              # Bottom bar: context-sensitive actions
    popups/
        __init__.py
        production.py              # City production queue management
        tech_tree.py               # Full tech tree visualization
        diplomacy.py               # Diplomatic relations and actions
        dynasty.py                 # Character/dynasty/succession info
        combat_result.py           # Combat preview + outcome display
        city_detail.py             # Detailed city yields, buildings, districts
        victory_popup.py           # Victory/defeat screen
        event_choice.py            # Random event with player choices
        encyclopedia.py            # In-game reference (F1)
    effects/
        __init__.py
        particles.py               # Lightweight particle emitter for combat/celebration
        tweens.py                  # Easing functions for animations
    audio/
        __init__.py
        sound_manager.py           # Sound effect categories and playback
        music_manager.py           # Era-based background music streaming

assets/
    tiles/                         # ComfyUI-generated hex terrain PNGs
    resources/                     # Resource overlay icons
    units/                         # Unit type icons
    buildings/                     # Building/district icons
    ui/                            # Panel backgrounds, button states
    sounds/ui/                     # Click, hover, confirm, cancel, notification
    sounds/combat/                 # Sword, arrow, siege, victory
    sounds/events/                 # Chimes for production, growth, tech
    music/                         # Era-specific background tracks (OGG)

tools/
    generate_hex_mask.py           # Create hex outline PNG for ControlNet
    generate_fallback_tiles.py     # Create colored hex tile PNGs from palette
    process_tiles.py               # Crop, resize, pack into sprite atlas

# New engine files
improvements.py                    # Worker tile improvement system
great_people.py                    # Great Person points, recruitment, retire actions
era_system.py                      # Era score, golden/dark ages, historic moments
loyalty.py                         # Per-city loyalty with cultural pressure
secrets.py                         # Hooks and secrets for intrigue
tutorial.py                        # 10-turn guided tutorial

requirements.txt                   # pygame-ce, pygame-gui, Pillow
```

### Files to modify (engine extensions)

```
game.py           # Add AI initialization params, era hooks, loyalty processing
game_data.py      # Add WONDERS, EUREKA_CONDITIONS, POLICY_CARDS, CONGENITAL_TRAITS
tech.py           # Add EurekaTracker class
city.py           # Add housing calculation, wonder building check
combat.py         # Add ZoC check, flanking calc, counter bonuses, ranged flag, preview
military.py       # Add fortification state, promotion tree branching
simulation.py     # Add StressSystem class, succession implementation
plots.py          # Add power-vs-resistance scheme mechanics, agent recruitment
diplomacy.py      # Add grievance tracking, warmongering penalty
religion.py       # Add beliefs, missionary logic, religious combat
victory.py        # Overhaul conditions to require specific systems
tech_policies.py  # Add policy card slotting, government change with anarchy
ai.py             # Rewrite decision framework with priority evaluation
city_growth.py    # Add housing cap enforcement
happiness_system.py # Convert to per-city amenities
save_system.py    # Add all new systems to serialization
main.py           # Launch Pygame app instead of tkinter
```

### Files to delete (legacy GUI)

```
gui.py, gui_map.py, gui_panels.py, gui_popups.py, gui_combat.py,
victory_ui.py, visual_effects.py, sound_effects.py,
gui_popups_backup.py, gui_popups_original.py,
fix_canvas.py, fix_popup.py, fix_popups.py, fix_popups2.py,
map.py, clean.py
```

---

## Phase 1: Pygame Core Scaffold

### Task 1: Create requirements.txt and install dependencies

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
pygame-ce>=2.5.0
pygame-gui>=0.6.14
Pillow>=10.0.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All three packages install successfully.

- [ ] **Step 3: Verify imports**

Run: `python -c "import pygame; import pygame_gui; from PIL import Image; print(f'pygame-ce {pygame.ver}'); print('All imports OK')"`
Expected: Version printed, no errors.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add Pygame-ce, pygame-gui, Pillow dependencies"
```

---

### Task 2: Create constants and package structure

**Files:**
- Create: `pygame_app/__init__.py`
- Create: `pygame_app/constants.py`
- Create: `pygame_app/screens/__init__.py`
- Create: `pygame_app/map/__init__.py`
- Create: `pygame_app/panels/__init__.py`
- Create: `pygame_app/popups/__init__.py`
- Create: `pygame_app/effects/__init__.py`
- Create: `pygame_app/audio/__init__.py`

- [ ] **Step 1: Create all `__init__.py` files**

Each `__init__.py` is an empty file (just a comment):
```python
# pygame_app package
```

- [ ] **Step 2: Create constants.py**

```python
"""Shared constants for the CivKings Pygame GUI."""

# Window
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
FPS = 30
TITLE = "CivKings: Dynasty & Dominion"

# Colors (dark fantasy palette)
BG = (10, 11, 13)             # #0a0b0d
PANEL_BG = (22, 24, 29)       # #16181d
PANEL_BG2 = (35, 38, 45)      # #23262d
ACCENT = (35, 38, 45)         # #23262d
HIGHLIGHT = (197, 160, 89)    # #c5a059
TEXT = (224, 224, 224)         # #e0e0e0
SUBTLE = (136, 136, 136)      # #888888
BORDER = (51, 54, 61)         # #33363d
GOLD = (197, 160, 89)         # #c5a059
RED = (178, 58, 58)           # #b23a3a
GREEN = (58, 178, 78)         # #3ab24e
BLUE = (58, 120, 178)         # #3a78b2

# Hex map
HEX_SIZE = 64                 # Base hex radius in pixels at zoom 1.0
HEX_HEIGHT_RATIO = 0.866      # sqrt(3)/2

# Layout regions (pixels)
RESOURCE_BAR_HEIGHT = 40
ACTION_BAR_HEIGHT = 50
LEFT_PANEL_WIDTH = 260
RIGHT_PANEL_WIDTH = 280
MINIMAP_SIZE = 200

# Map area (computed from layout)
MAP_X = LEFT_PANEL_WIDTH
MAP_Y = RESOURCE_BAR_HEIGHT
MAP_W = SCREEN_WIDTH - LEFT_PANEL_WIDTH - RIGHT_PANEL_WIDTH
MAP_H = SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT

# Terrain colors (fallback when no tile art exists)
# Keyed by terrain name strings to avoid importing game_data at module level
# (game_data.py is at project root, needs sys.path setup from app.py first)
TERRAIN_COLORS = {
    'PLAINS':      (61, 77, 61),
    'GRASSLAND':   (74, 93, 74),
    'FOREST':      (45, 74, 45),
    'HILLS':       (90, 90, 61),
    'MOUNTAIN':    (74, 74, 74),
    'DESERT':      (106, 90, 58),
    'TUNDRA':      (180, 190, 200),
    'WATER_COAST': (40, 80, 120),
    'OCEAN':       (26, 58, 90),
}
```

- [ ] **Step 3: Commit**

```bash
git add pygame_app/
git commit -m "feat: create pygame_app package structure with constants"
```

---

### Task 3: Create the dark fantasy theme.json

**Files:**
- Create: `pygame_app/theme.json`

- [ ] **Step 1: Create theme.json**

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
            "link_hover": "#d4b76a"
        },
        "font": {
            "name": "default",
            "size": "14"
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
    },
    "label": {
        "colours": {
            "dark_bg": "#16181d",
            "normal_text": "#e0e0e0"
        }
    },
    "horizontal_slider": {
        "colours": {
            "dark_bg": "#0a0b0d",
            "normal_bg": "#23262d",
            "hovered_bg": "#33363d",
            "selected_bg": "#c5a059"
        }
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add pygame_app/theme.json
git commit -m "feat: add dark fantasy pygame_gui theme"
```

---

### Task 4: Create BaseScreen class

**Files:**
- Create: `pygame_app/screens/base.py`

- [ ] **Step 1: Write BaseScreen**

```python
"""Base class for all game screens."""
import pygame
import pygame_gui


class BaseScreen:
    """Abstract base for screens (main menu, game, etc.)."""

    def __init__(self, app):
        """
        Args:
            app: The GameApp instance (provides screen, ui_manager, game).
        """
        self.app = app
        self.ui_manager = app.ui_manager

    def enter(self):
        """Called when this screen becomes active. Create UI elements here."""
        pass

    def exit(self):
        """Called when leaving this screen. Kill UI elements here."""
        pass

    def handle_event(self, event: pygame.event.Event):
        """Handle a single pygame event."""
        pass

    def update(self, dt: float):
        """Update logic each frame. dt is seconds since last frame."""
        pass

    def draw(self, surface: pygame.Surface):
        """Draw this screen's content to the surface."""
        pass
```

- [ ] **Step 2: Commit**

```bash
git add pygame_app/screens/base.py
git commit -m "feat: add BaseScreen abstract class"
```

---

### Task 5: Create the main application loop

**Files:**
- Create: `pygame_app/app.py`

- [ ] **Step 1: Write app.py**

```python
"""CivKings Pygame application — main loop, window, state machine."""
import os
import sys
import pygame
import pygame_gui

# Add project root to path so engine imports work
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pygame_app.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, BG


class GameApp:
    """Top-level application. Manages window, game loop, screen transitions."""

    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE
        )
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        theme_path = os.path.join(os.path.dirname(__file__), 'theme.json')
        self.ui_manager = pygame_gui.UIManager(
            (SCREEN_WIDTH, SCREEN_HEIGHT), theme_path
        )

        self.game = None  # Engine Game instance, set by NewGameDialog
        self.running = True
        self._current_screen = None
        self._screens = {}

        # Import screens lazily to avoid circular imports
        from pygame_app.screens.main_menu import MainMenuScreen
        self._screens['main_menu'] = MainMenuScreen(self)
        self.switch_screen('main_menu')

    def register_screen(self, name: str, screen):
        """Register a screen by name for switching."""
        self._screens[name] = screen

    def switch_screen(self, name: str):
        """Transition to a different screen."""
        if self._current_screen is not None:
            self._current_screen.exit()
        self._current_screen = self._screens[name]
        self._current_screen.enter()

    def handle_resize(self, new_w: int, new_h: int):
        """Handle window resize."""
        self.screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
        self.ui_manager.set_window_resolution((new_w, new_h))

    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue
                if event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event.w, event.h)
                self.ui_manager.process_events(event)
                if self._current_screen:
                    self._current_screen.handle_event(event)

            self.ui_manager.update(dt)
            if self._current_screen:
                self._current_screen.update(dt)

            self.screen.fill(BG)
            if self._current_screen:
                self._current_screen.draw(self.screen)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.flip()

        pygame.quit()


def main():
    app = GameApp()
    app.run()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Verify it compiles**

Run: `cd /c/Users/civer/civkings && python -c "from pygame_app.app import GameApp; print('Import OK')"`
Expected: "Import OK" (will fail until MainMenuScreen exists — that's next task).

- [ ] **Step 3: Commit**

```bash
git add pygame_app/app.py
git commit -m "feat: add main Pygame application loop with state machine"
```

---

### Task 6: Create Main Menu screen

**Files:**
- Create: `pygame_app/screens/main_menu.py`

- [ ] **Step 1: Write main_menu.py**

```python
"""Main menu screen — title, new game, load game, quit."""
import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UILabel

from pygame_app.screens.base import BaseScreen
from pygame_app.constants import SCREEN_WIDTH, SCREEN_HEIGHT, GOLD, TEXT


class MainMenuScreen(BaseScreen):
    """Title screen with New Game / Load Game / Quit buttons."""

    def __init__(self, app):
        super().__init__(app)
        self.buttons = {}
        self.labels = []

    def enter(self):
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2

        # Title
        self.labels.append(UILabel(
            relative_rect=pygame.Rect(cx - 300, cy - 200, 600, 60),
            text="CIVKINGS: DYNASTY & DOMINION",
            manager=self.ui_manager,
        ))

        # Subtitle
        self.labels.append(UILabel(
            relative_rect=pygame.Rect(cx - 200, cy - 140, 400, 30),
            text="A Strategy Game of Empires and Bloodlines",
            manager=self.ui_manager,
        ))

        # Buttons
        btn_w, btn_h = 240, 50
        btn_x = cx - btn_w // 2

        self.buttons['new_game'] = UIButton(
            relative_rect=pygame.Rect(btn_x, cy - 40, btn_w, btn_h),
            text="New Game",
            manager=self.ui_manager,
        )
        self.buttons['load_game'] = UIButton(
            relative_rect=pygame.Rect(btn_x, cy + 30, btn_w, btn_h),
            text="Load Game",
            manager=self.ui_manager,
        )
        self.buttons['quit'] = UIButton(
            relative_rect=pygame.Rect(btn_x, cy + 100, btn_w, btn_h),
            text="Quit",
            manager=self.ui_manager,
        )

    def exit(self):
        for btn in self.buttons.values():
            btn.kill()
        for lbl in self.labels:
            lbl.kill()
        self.buttons.clear()
        self.labels.clear()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.buttons.get('quit'):
                self.app.running = False
            elif event.ui_element == self.buttons.get('new_game'):
                self._open_new_game()
            elif event.ui_element == self.buttons.get('load_game'):
                self._load_game()

    def _open_new_game(self):
        from pygame_app.screens.new_game_dialog import NewGameDialog
        if 'new_game_dialog' not in self.app._screens:
            self.app.register_screen('new_game_dialog', NewGameDialog(self.app))
        self.app.switch_screen('new_game_dialog')

    def _load_game(self):
        # Load game is implemented in Phase 6, Task 38 (save/load popup)
        # For now, show a placeholder message
        from pygame_gui.windows import UIMessageWindow
        UIMessageWindow(
            rect=pygame.Rect(400, 300, 300, 150),
            html_message="Save/Load coming in Phase 6.",
            manager=self.ui_manager,
        )

    def draw(self, surface):
        # Background is already filled by app.py
        pass
```

- [ ] **Step 2: Verify the main menu launches**

Run: `cd /c/Users/civer/civkings && timeout 5 python -c "
from pygame_app.app import GameApp
app = GameApp()
# Just verify it initializes — don't run the loop
print(f'Window: {app.screen.get_size()}')
print(f'Screen: {app._current_screen.__class__.__name__}')
import pygame; pygame.quit()
print('OK')
" 2>&1 || true`

Expected: Shows window size and "MainMenuScreen", then "OK".

- [ ] **Step 3: Commit**

```bash
git add pygame_app/screens/main_menu.py
git commit -m "feat: add main menu screen with new game/load/quit"
```

---

### Task 7: Create New Game Dialog screen

**Files:**
- Create: `pygame_app/screens/new_game_dialog.py`

- [ ] **Step 1: Write new_game_dialog.py**

```python
"""New game setup — civilization, difficulty, map size, AI opponents."""
import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UILabel, UIDropDownMenu, UIHorizontalSlider

from pygame_app.screens.base import BaseScreen
from pygame_app.constants import SCREEN_WIDTH, SCREEN_HEIGHT

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from game_data import CIVILIZATIONS


class NewGameDialog(BaseScreen):
    """Game setup: pick civ, difficulty, map size, number of AI opponents."""

    def __init__(self, app):
        super().__init__(app)
        self.elements = []
        self.civ_dropdown = None
        self.diff_dropdown = None
        self.map_dropdown = None
        self.ai_count_slider = None
        self.ai_count_label = None
        self.start_btn = None
        self.back_btn = None

    def enter(self):
        cx = SCREEN_WIDTH // 2
        y = 120
        lbl_w, lbl_h = 200, 30
        dd_w, dd_h = 250, 35
        spacing = 60

        # Title
        title = UILabel(
            relative_rect=pygame.Rect(cx - 200, 40, 400, 50),
            text="NEW GAME",
            manager=self.ui_manager,
        )
        self.elements.append(title)

        # Civilization
        lbl = UILabel(
            relative_rect=pygame.Rect(cx - 280, y, lbl_w, lbl_h),
            text="Civilization:",
            manager=self.ui_manager,
        )
        self.elements.append(lbl)

        civ_names = sorted(CIVILIZATIONS.keys())
        self.civ_dropdown = UIDropDownMenu(
            options_list=civ_names,
            starting_option=civ_names[0],
            relative_rect=pygame.Rect(cx - 60, y, dd_w, dd_h),
            manager=self.ui_manager,
        )
        self.elements.append(self.civ_dropdown)
        y += spacing

        # Difficulty
        lbl = UILabel(
            relative_rect=pygame.Rect(cx - 280, y, lbl_w, lbl_h),
            text="Difficulty:",
            manager=self.ui_manager,
        )
        self.elements.append(lbl)

        difficulties = ['Rookie', 'Easy', 'Standard', 'Hard', 'Immortal']
        self.diff_dropdown = UIDropDownMenu(
            options_list=difficulties,
            starting_option='Standard',
            relative_rect=pygame.Rect(cx - 60, y, dd_w, dd_h),
            manager=self.ui_manager,
        )
        self.elements.append(self.diff_dropdown)
        y += spacing

        # Map size
        lbl = UILabel(
            relative_rect=pygame.Rect(cx - 280, y, lbl_w, lbl_h),
            text="Map Size:",
            manager=self.ui_manager,
        )
        self.elements.append(lbl)

        map_sizes = ['Small (12x12)', 'Medium (16x16)', 'Large (24x24)', 'Huge (32x32)']
        self.map_dropdown = UIDropDownMenu(
            options_list=map_sizes,
            starting_option='Medium (16x16)',
            relative_rect=pygame.Rect(cx - 60, y, dd_w, dd_h),
            manager=self.ui_manager,
        )
        self.elements.append(self.map_dropdown)
        y += spacing

        # AI opponents (slider: 1-7)
        lbl = UILabel(
            relative_rect=pygame.Rect(cx - 280, y, lbl_w, lbl_h),
            text="AI Opponents:",
            manager=self.ui_manager,
        )
        self.elements.append(lbl)

        self.ai_count_slider = UIHorizontalSlider(
            relative_rect=pygame.Rect(cx - 60, y, 200, lbl_h),
            start_value=3,
            value_range=(1, 7),
            manager=self.ui_manager,
        )
        self.elements.append(self.ai_count_slider)

        self.ai_count_label = UILabel(
            relative_rect=pygame.Rect(cx + 160, y, 60, lbl_h),
            text="3",
            manager=self.ui_manager,
        )
        self.elements.append(self.ai_count_label)
        y += spacing + 40

        # Buttons
        self.start_btn = UIButton(
            relative_rect=pygame.Rect(cx - 140, y, 120, 50),
            text="Start Game",
            manager=self.ui_manager,
        )
        self.elements.append(self.start_btn)

        self.back_btn = UIButton(
            relative_rect=pygame.Rect(cx + 20, y, 120, 50),
            text="Back",
            manager=self.ui_manager,
        )
        self.elements.append(self.back_btn)

    def exit(self):
        for el in self.elements:
            el.kill()
        self.elements.clear()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_btn:
                self.app.switch_screen('main_menu')
            elif event.ui_element == self.start_btn:
                self._start_game()
        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.ai_count_slider:
                self.ai_count_label.set_text(str(int(self.ai_count_slider.get_current_value())))

    def _start_game(self):
        """Create engine Game instance and switch to game screen."""
        civ_name = self.civ_dropdown.selected_option[0] if isinstance(
            self.civ_dropdown.selected_option, tuple
        ) else self.civ_dropdown.selected_option
        civ = CIVILIZATIONS[civ_name]
        difficulty = self.diff_dropdown.selected_option
        if isinstance(difficulty, tuple):
            difficulty = difficulty[0]

        # Parse map size
        map_text = self.map_dropdown.selected_option
        if isinstance(map_text, tuple):
            map_text = map_text[0]
        size_map = {
            'Small (12x12)': 12, 'Medium (16x16)': 16,
            'Large (24x24)': 24, 'Huge (32x32)': 32,
        }
        map_size = size_map.get(map_text, 16)

        ai_count = int(self.ai_count_slider.get_current_value())

        # Pick AI civs (exclude player civ)
        from game_data import CIVILIZATIONS as ALL_CIVS
        ai_civ_names = [n for n in ALL_CIVS if n != civ_name][:ai_count]

        # Create game engine
        from game import Game
        self.app.game = Game(civ, map_width=map_size, map_height=map_size)

        # Add AI players
        from ai import AIPlayer
        for ai_name in ai_civ_names:
            self.app.game.ai_players[ai_name] = AIPlayer(ai_name, difficulty.lower())

        # Switch to game screen
        from pygame_app.screens.game_screen import GameScreen
        if 'game' not in self.app._screens:
            self.app.register_screen('game', GameScreen(self.app))
        self.app.switch_screen('game')

    def draw(self, surface):
        pass
```

- [ ] **Step 2: Commit**

```bash
git add pygame_app/screens/new_game_dialog.py
git commit -m "feat: add new game dialog with civ/difficulty/map/AI selection"
```

---

### Task 8: Create stub GameScreen

**Files:**
- Create: `pygame_app/screens/game_screen.py`

- [ ] **Step 1: Write initial game_screen.py stub**

This is a minimal stub that proves the game launches. It will be filled in during Phase 2-4.

```python
"""Main gameplay screen — coordinates map, panels, popups."""
import pygame
import pygame_gui
from pygame_gui.elements import UILabel

from pygame_app.screens.base import BaseScreen
from pygame_app.constants import SCREEN_WIDTH, SCREEN_HEIGHT, BG, TEXT, GOLD


class GameScreen(BaseScreen):
    """Main gameplay screen. Renders hex map, panels, and manages popups."""

    def __init__(self, app):
        super().__init__(app)
        self.elements = []

    def enter(self):
        game = self.app.game
        civ_name = game.player_civ.name if hasattr(game.player_civ, 'name') else str(game.player_civ)

        # Placeholder label showing game is running
        self.elements.append(UILabel(
            relative_rect=pygame.Rect(20, 20, 600, 40),
            text=f"Playing as {civ_name} — Turn {game.state.turn} — Map {game.map.width}x{game.map.height}",
            manager=self.ui_manager,
        ))

        # Placeholder "Next Turn" button
        from pygame_gui.elements import UIButton
        self.next_turn_btn = UIButton(
            relative_rect=pygame.Rect(SCREEN_WIDTH - 180, SCREEN_HEIGHT - 60, 160, 45),
            text="Next Turn",
            manager=self.ui_manager,
        )
        self.elements.append(self.next_turn_btn)

    def exit(self):
        for el in self.elements:
            el.kill()
        self.elements.clear()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.next_turn_btn:
                self.app.game.process_turn()
                self._refresh_label()

    def _refresh_label(self):
        """Update the turn label after processing."""
        game = self.app.game
        civ_name = game.player_civ.name if hasattr(game.player_civ, 'name') else str(game.player_civ)
        if self.elements:
            self.elements[0].set_text(
                f"Playing as {civ_name} — Turn {game.state.turn} — Map {game.map.width}x{game.map.height}"
            )

    def draw(self, surface):
        # Draw dark background for now; hex map comes in Phase 2
        pass
```

- [ ] **Step 2: Test full flow: launch -> menu -> new game -> game screen -> next turn**

Run: `cd /c/Users/civer/civkings && python pygame_app/app.py`

Expected: Pygame window opens, main menu shows three buttons, clicking "New Game" shows setup screen with dropdowns, clicking "Start Game" creates the engine and shows the game screen with a turn label and Next Turn button. Clicking Next Turn increments the turn counter.

- [ ] **Step 3: Commit**

```bash
git add pygame_app/screens/game_screen.py
git commit -m "feat: add stub game screen with turn processing"
```

---

### Task 9: Update main.py entry point

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Replace main.py to launch Pygame app**

```python
"""Entry point for CivKings game."""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main entry point — launches Pygame GUI."""
    try:
        from pygame_app.app import main as pygame_main
        pygame_main()
    except ImportError as e:
        print(f"Pygame GUI not available ({e}). Install with: pip install -r requirements.txt")
        print("Falling back to text mode...")
        from ui import GameUI
        game_ui = GameUI(GameUI.new_game())
        # (legacy text UI loop)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test**

Run: `cd /c/Users/civer/civkings && python main.py`
Expected: Pygame window launches with main menu.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: update main.py to launch Pygame app (tkinter fallback removed)"
```

---

### Phase 1 Verification

Run: `cd /c/Users/civer/civkings && python main.py`

- [ ] Pygame window opens at 1400x900
- [ ] Main menu shows "CIVKINGS: DYNASTY & DOMINION" title
- [ ] "New Game" button opens setup dialog
- [ ] Civ dropdown shows all civilizations from game_data.py
- [ ] Difficulty dropdown shows 5 levels
- [ ] Map size dropdown shows 4 options
- [ ] AI slider moves between 1-7 with live count display
- [ ] "Start Game" creates Game engine and shows game screen
- [ ] Turn label shows correct civ name, turn number, map size
- [ ] "Next Turn" button increments turn
- [ ] "Back" returns to main menu
- [ ] "Quit" exits cleanly
- [ ] Window resizes without crash

---

## Phase 2: Hex Map Renderer

### Task 10: Create fallback tile generator

**Files:**
- Create: `tools/generate_fallback_tiles.py`

- [ ] **Step 1: Write fallback tile generator**

This creates simple colored hex PNG tiles so the game is playable without ComfyUI.

```python
"""Generate colored hex tile PNGs as fallback when ComfyUI assets don't exist."""
import os
import sys
import math
import json
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game_data import TerrainType

# Same palette as constants.py but as RGB tuples
TERRAIN_COLORS = {
    'PLAINS':      (61, 77, 61),
    'GRASSLAND':   (74, 93, 74),
    'FOREST':      (45, 74, 45),
    'HILLS':       (90, 90, 61),
    'MOUNTAIN':    (74, 74, 74),
    'DESERT':      (106, 90, 58),
    'TUNDRA':      (180, 190, 200),
    'WATER_COAST': (40, 80, 120),
    'OCEAN':       (26, 58, 90),
}

ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.5, 2.0]
BASE_SIZE = 128  # pixels at zoom 1.0


def hex_points(cx, cy, radius):
    """Generate flat-top hex vertices."""
    points = []
    for i in range(6):
        angle = math.pi / 3 * i
        px = cx + radius * math.cos(angle)
        py = cy + radius * math.sin(angle)
        points.append((px, py))
    return points


def generate_tile(color, size):
    """Create a single hex tile PNG with transparency."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = size * 0.48  # slightly smaller than half to leave border
    pts = hex_points(size / 2, size / 2, r)
    draw.polygon(pts, fill=color + (255,), outline=(18, 18, 18, 255))
    return img


def generate_all(output_dir):
    """Generate all terrain tiles at all zoom levels and pack into atlases."""
    os.makedirs(output_dir, exist_ok=True)

    for zoom in ZOOM_LEVELS:
        size = int(BASE_SIZE * zoom)
        atlas_tiles = {}
        images = []

        for terrain_name, color in TERRAIN_COLORS.items():
            tile_img = generate_tile(color, size)
            images.append((terrain_name, tile_img))

        # Pack into atlas (simple horizontal strip)
        cols = len(images)
        atlas_w = cols * size
        atlas_h = size
        atlas = Image.new('RGBA', (atlas_w, atlas_h), (0, 0, 0, 0))

        for i, (name, img) in enumerate(images):
            x = i * size
            atlas.paste(img, (x, 0))
            atlas_tiles[f"{name}_0"] = {"x": x, "y": 0, "w": size, "h": size}

        zoom_tag = f"z{zoom:.1f}".replace('.', '_')
        atlas_path = os.path.join(output_dir, f"atlas_{zoom_tag}.png")
        json_path = os.path.join(output_dir, f"atlas_{zoom_tag}.json")

        atlas.save(atlas_path)
        with open(json_path, 'w') as f:
            json.dump(atlas_tiles, f, indent=2)

        print(f"Generated {atlas_path} ({atlas_w}x{atlas_h}, {len(images)} tiles)")

    print("Done. Fallback tiles generated.")


if __name__ == '__main__':
    output = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'tiles')
    generate_all(output)
```

- [ ] **Step 2: Run the generator**

Run: `cd /c/Users/civer/civkings && python tools/generate_fallback_tiles.py`
Expected: Creates `assets/tiles/atlas_z0_5.png`, `atlas_z0_5.json`, etc. for all 5 zoom levels.

- [ ] **Step 3: Commit**

```bash
git add tools/generate_fallback_tiles.py assets/tiles/
git commit -m "feat: add fallback hex tile generator with colored hexes"
```

---

### Task 11: Create TileAtlas loader

**Files:**
- Create: `pygame_app/map/tile_atlas.py`

- [ ] **Step 1: Write tile_atlas.py**

```python
"""Load hex tile sprite atlases and provide terrain surfaces by type and zoom."""
import os
import json
import pygame


class TileAtlas:
    """Loads sprite sheet atlases and extracts terrain tile surfaces."""

    ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.5, 2.0]

    def __init__(self, tiles_dir: str):
        self.tiles_dir = tiles_dir
        self.atlases = {}       # {zoom_tag: pygame.Surface}
        self.tile_rects = {}    # {zoom_tag: {name: pygame.Rect}}
        self._tile_cache = {}   # {(terrain_name, zoom_tag): pygame.Surface}
        self._load_all()

    def _zoom_tag(self, zoom: float) -> str:
        return f"z{zoom:.1f}".replace('.', '_')

    def _load_all(self):
        for zoom in self.ZOOM_LEVELS:
            tag = self._zoom_tag(zoom)
            atlas_path = os.path.join(self.tiles_dir, f"atlas_{tag}.png")
            json_path = os.path.join(self.tiles_dir, f"atlas_{tag}.json")

            if not os.path.exists(atlas_path):
                continue

            surface = pygame.image.load(atlas_path).convert_alpha()
            self.atlases[tag] = surface

            with open(json_path, 'r') as f:
                rects = json.load(f)
            self.tile_rects[tag] = {
                name: pygame.Rect(r['x'], r['y'], r['w'], r['h'])
                for name, r in rects.items()
            }

    def _nearest_zoom(self, zoom: float) -> str:
        nearest = min(self.ZOOM_LEVELS, key=lambda z: abs(z - zoom))
        return self._zoom_tag(nearest)

    def get_tile(self, terrain_name: str, zoom: float = 1.0) -> pygame.Surface:
        """Get the tile surface for a terrain type at the nearest zoom level.

        Args:
            terrain_name: Terrain enum name (e.g. 'PLAINS', 'OCEAN').
            zoom: Current camera zoom level.

        Returns:
            pygame.Surface with the hex tile image (with alpha).
        """
        tag = self._nearest_zoom(zoom)
        key = f"{terrain_name}_0"
        cache_key = (key, tag)

        if cache_key in self._tile_cache:
            return self._tile_cache[cache_key]

        if tag not in self.atlases or key not in self.tile_rects.get(tag, {}):
            # Return a small red square as error indicator
            s = pygame.Surface((32, 32), pygame.SRCALPHA)
            s.fill((255, 0, 0, 128))
            return s

        rect = self.tile_rects[tag][key]
        tile_surface = self.atlases[tag].subsurface(rect).copy()
        self._tile_cache[cache_key] = tile_surface
        return tile_surface

    @property
    def loaded(self) -> bool:
        return len(self.atlases) > 0
```

- [ ] **Step 2: Test atlas loading**

Run: `cd /c/Users/civer/civkings && python -c "
import pygame; pygame.init()
screen = pygame.display.set_mode((100, 100))
from pygame_app.map.tile_atlas import TileAtlas
atlas = TileAtlas('assets/tiles')
print(f'Loaded: {atlas.loaded}')
print(f'Zoom levels: {list(atlas.atlases.keys())}')
tile = atlas.get_tile('PLAINS', 1.0)
print(f'PLAINS tile size: {tile.get_size()}')
pygame.quit()
print('OK')
"`

Expected: "Loaded: True", shows zoom levels, PLAINS tile size matches base size.

- [ ] **Step 3: Commit**

```bash
git add pygame_app/map/tile_atlas.py
git commit -m "feat: add TileAtlas sprite sheet loader with zoom level support"
```

---

### Task 12: Create Camera system

**Files:**
- Create: `pygame_app/map/camera.py`

- [ ] **Step 1: Write camera.py**

```python
"""Camera system — pan, zoom, viewport culling, coordinate transforms."""
import math
from typing import Tuple


class Camera:
    """Manages the viewport into the hex world."""

    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Current state
        self.x = 0.0           # World center X
        self.y = 0.0           # World center Y
        self.zoom = 1.0

        # Target state (for smooth lerp)
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_zoom = 1.0

        # Limits
        self.min_zoom = 0.3
        self.max_zoom = 3.0
        self.lerp_speed = 10.0

        # Mouse drag state
        self._dragging = False
        self._drag_start = (0, 0)

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
        return (
            self.x - half_w, self.y - half_h,
            self.x + half_w, self.y + half_h,
        )

    def update(self, dt: float):
        """Smooth lerp toward target position/zoom."""
        t = min(1.0, self.lerp_speed * dt)
        self.x += (self.target_x - self.x) * t
        self.y += (self.target_y - self.y) * t
        self.zoom += (self.target_zoom - self.zoom) * t

    def pan(self, dx: float, dy: float):
        """Pan the camera by screen-space delta."""
        self.target_x += dx / self.zoom
        self.target_y += dy / self.zoom

    def zoom_at(self, screen_x: int, screen_y: int, factor: float):
        """Zoom centered on a screen position."""
        # Get world point under cursor before zoom
        wx, wy = self.screen_to_world(screen_x, screen_y)

        new_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom * factor))
        self.target_zoom = new_zoom

        # Adjust target position so the world point stays under cursor
        # new_sx = (wx - target_x) * new_zoom + screen_w/2 = screen_x
        # => target_x = wx - (screen_x - screen_w/2) / new_zoom
        self.target_x = wx - (screen_x - self.screen_w / 2) / new_zoom
        self.target_y = wy - (screen_y - self.screen_h / 2) / new_zoom

    def center_on(self, wx: float, wy: float):
        """Smoothly center camera on a world position."""
        self.target_x = wx
        self.target_y = wy

    def snap_to(self, wx: float, wy: float):
        """Immediately center camera (no lerp)."""
        self.x = self.target_x = wx
        self.y = self.target_y = wy

    def resize(self, new_w: int, new_h: int):
        """Handle window resize."""
        self.screen_w = new_w
        self.screen_h = new_h
```

- [ ] **Step 2: Commit**

```bash
git add pygame_app/map/camera.py
git commit -m "feat: add Camera with pan, zoom, smooth lerp, coordinate transforms"
```

---

### Task 13: Create HexRenderer

**Files:**
- Create: `pygame_app/map/hex_renderer.py`

- [ ] **Step 1: Write hex_renderer.py**

```python
"""Hex map renderer — draws terrain tiles, resources, cities, units, borders."""
import math
from typing import Tuple, Optional, Set
import pygame

from pygame_app.constants import HEX_SIZE, TERRAIN_COLORS, GOLD, RED, GREEN, TEXT, BLUE, SUBTLE
from pygame_app.map.tile_atlas import TileAtlas
from pygame_app.map.camera import Camera


class HexRenderer:
    """Renders the hex map using image tiles from a TileAtlas."""

    def __init__(self, hex_map, tile_atlas: TileAtlas, camera: Camera):
        self.hex_map = hex_map
        self.atlas = tile_atlas
        self.camera = camera
        self.font = None            # Initialized after pygame.init()
        self.small_font = None
        self._init_fonts()

        # Interaction state
        self.selected_hex = None    # (x, y) of selected tile
        self.hovered_hex = None     # (x, y) of hovered tile
        self.move_range = set()     # Set of (x, y) tiles unit can move to
        self.attack_range = set()   # Set of (x, y) tiles unit can attack

    def _init_fonts(self):
        try:
            self.font = pygame.font.SysFont('segoeui', 14)
            self.small_font = pygame.font.SysFont('segoeui', 11)
        except Exception:
            self.font = pygame.font.Font(None, 16)
            self.small_font = pygame.font.Font(None, 12)

    def hex_to_world(self, hx: int, hy: int) -> Tuple[float, float]:
        """Convert hex grid (x, y) to world pixel coordinates (flat-top)."""
        wx = HEX_SIZE * 1.5 * hx
        wy = HEX_SIZE * math.sqrt(3) * (hy + 0.5 * (hx & 1))
        return wx, wy

    def world_to_hex(self, wx: float, wy: float) -> Tuple[int, int]:
        """Convert world pixel to nearest hex (x, y) coordinates."""
        # Approximate: divide by hex spacing, then round
        q = wx / (HEX_SIZE * 1.5)
        r = (wy / (HEX_SIZE * math.sqrt(3))) - 0.5 * (int(round(q)) & 1)
        return self._hex_round(q, r)

    def _hex_round(self, q: float, r: float) -> Tuple[int, int]:
        """Round fractional hex coordinates to nearest integer hex."""
        rq = round(q)
        rr = round(r)
        # Simple rounding — good enough for click detection
        return int(rq), int(rr)

    def screen_to_hex(self, sx: int, sy: int) -> Tuple[int, int]:
        """Convert screen pixel position to hex coordinates."""
        wx, wy = self.camera.screen_to_world(sx, sy)
        return self.world_to_hex(wx, wy)

    def get_visible_hexes(self) -> Set[Tuple[int, int]]:
        """Return set of hex coordinates visible in current viewport."""
        min_wx, min_wy, max_wx, max_wy = self.camera.get_visible_bounds()
        # Add margin of 2 hexes for partially visible tiles
        margin = HEX_SIZE * 3
        min_wx -= margin
        min_wy -= margin
        max_wx += margin
        max_wy += margin

        visible = set()
        for x in range(self.hex_map.width):
            for y in range(self.hex_map.height):
                wx, wy = self.hex_to_world(x, y)
                if min_wx <= wx <= max_wx and min_wy <= wy <= max_wy:
                    visible.add((x, y))
        return visible

    def render(self, surface: pygame.Surface, game):
        """Render the hex map to the given surface.

        Args:
            surface: Pygame surface to draw on.
            game: Engine Game instance (for cities, units, fog).
        """
        visible = self.get_visible_hexes()
        fog = game.fog

        # Layer 1: Terrain tiles
        for hx, hy in visible:
            tile = self.hex_map.get_tile(hx, hy)
            if tile is None:
                continue

            wx, wy = self.hex_to_world(hx, hy)
            sx, sy = self.camera.world_to_screen(wx, wy)

            # Get tile image from atlas
            terrain_name = tile.terrain.name
            tile_img = self.atlas.get_tile(terrain_name, self.camera.zoom)
            rect = tile_img.get_rect(center=(sx, sy))
            surface.blit(tile_img, rect)

            # Layer 2: Resource icons
            if tile.resource and fog.is_visible(hx, hy):
                self._draw_resource(surface, tile.resource.name, sx, sy)

            # Layer 3: River indicator (engine uses tile.has_river — verify attribute name)
            if getattr(tile, 'has_river', False) and fog.is_explored(hx, hy):
                self._draw_river_indicator(surface, sx, sy)

        # Layer 4: City markers
        for city_name, city in game.cities.items():
            cx, cy = city.position
            if (cx, cy) not in visible:
                continue
            if not fog.is_visible(cx, cy):
                continue
            wx, wy = self.hex_to_world(cx, cy)
            sx, sy = self.camera.world_to_screen(wx, wy)
            self._draw_city(surface, city, sx, sy, game)

        # Layer 5: Unit sprites
        for unit_id, unit in game.units.items():
            ux, uy = unit.position
            if (ux, uy) not in visible:
                continue
            if not fog.is_visible(ux, uy):
                continue
            wx, wy = self.hex_to_world(ux, uy)
            sx, sy = self.camera.world_to_screen(wx, wy)
            self._draw_unit(surface, unit, sx, sy, game)

        # Layer 6: Fog of war overlay
        for hx, hy in visible:
            if not fog.is_explored(hx, hy):
                self._draw_fog(surface, hx, hy, alpha=230)
            elif not fog.is_visible(hx, hy):
                self._draw_fog(surface, hx, hy, alpha=140)

        # Layer 7: Selection highlight
        if self.selected_hex:
            self._draw_hex_highlight(surface, self.selected_hex, GOLD, width=3)

        # Layer 8: Move range
        for mhx, mhy in self.move_range:
            if (mhx, mhy) in visible:
                self._draw_hex_highlight(surface, (mhx, mhy), BLUE, width=2)

        # Layer 9: Attack range
        for ahx, ahy in self.attack_range:
            if (ahx, ahy) in visible:
                self._draw_hex_highlight(surface, (ahx, ahy), RED, width=2)

        # Layer 10: Hover highlight
        if self.hovered_hex and self.hovered_hex in visible:
            self._draw_hex_highlight(surface, self.hovered_hex, (255, 255, 255), width=1)

    def _draw_resource(self, surface, resource_name: str, sx: int, sy: int):
        """Draw a small resource label on the tile."""
        # Simple text label for now — replaced with icons in Phase 0
        short = resource_name[:4]
        txt = self.small_font.render(short, True, GOLD)
        surface.blit(txt, (sx - txt.get_width() // 2, sy + 15))

    def _draw_river_indicator(self, surface, sx: int, sy: int):
        """Draw a blue dot indicating river presence."""
        scaled_r = max(2, int(4 * self.camera.zoom))
        pygame.draw.circle(surface, (80, 140, 220), (sx, sy - 20), scaled_r)

    def _draw_city(self, surface, city, sx: int, sy: int, game=None):
        """Draw city marker with name and population."""
        # City circle
        r = max(8, int(12 * self.camera.zoom))
        player_name = game.player_civ.name if game and hasattr(game.player_civ, 'name') else 'Player'
        color = GOLD if city.owner == player_name else RED
        pygame.draw.circle(surface, color, (sx, sy), r)
        pygame.draw.circle(surface, (0, 0, 0), (sx, sy), r, 2)

        # City name
        name_txt = self.font.render(city.name, True, TEXT)
        surface.blit(name_txt, (sx - name_txt.get_width() // 2, sy - r - 18))

        # Population
        pop_txt = self.small_font.render(f"Pop {city.population}", True, SUBTLE if hasattr(city, 'population') else TEXT)
        surface.blit(pop_txt, (sx - pop_txt.get_width() // 2, sy + r + 4))

    def _draw_unit(self, surface, unit, sx: int, sy: int, game=None):
        """Draw unit marker with type and health bar."""
        # Unit icon (colored square — replaced with sprite icons when ComfyUI assets exist)
        size = max(10, int(16 * self.camera.zoom))
        player_name = game.player_civ.name if game and hasattr(game.player_civ, 'name') else 'Player'
        color = GREEN if unit.owner == player_name else RED
        rect = pygame.Rect(sx - size // 2, sy - size // 2, size, size)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, (0, 0, 0), rect, 1)

        # Unit type label
        label = unit.unit_type[:3].upper()
        txt = self.small_font.render(label, True, TEXT)
        surface.blit(txt, (sx - txt.get_width() // 2, sy + size // 2 + 2))

        # Health bar
        if unit.hp < unit.max_hp:
            bar_w = size + 4
            bar_h = 3
            bar_x = sx - bar_w // 2
            bar_y = sy - size // 2 - 5
            hp_ratio = unit.hp / unit.max_hp
            pygame.draw.rect(surface, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
            hp_color = GREEN if hp_ratio > 0.5 else GOLD if hp_ratio > 0.25 else RED
            pygame.draw.rect(surface, hp_color, (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))

    def _draw_fog(self, surface, hx: int, hy: int, alpha: int):
        """Draw fog overlay on a hex tile."""
        wx, wy = self.hex_to_world(hx, hy)
        sx, sy = self.camera.world_to_screen(wx, wy)
        size = int(HEX_SIZE * self.camera.zoom * 1.2)
        fog_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        fog_surf.fill((0, 0, 0, alpha))
        surface.blit(fog_surf, (sx - size // 2, sy - size // 2))

    def _draw_hex_highlight(self, surface, hex_pos: Tuple[int, int], color, width: int = 2):
        """Draw a hex outline highlight."""
        hx, hy = hex_pos
        wx, wy = self.hex_to_world(hx, hy)
        sx, sy = self.camera.world_to_screen(wx, wy)
        r = HEX_SIZE * self.camera.zoom * 0.48
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            px = sx + r * math.cos(angle)
            py = sy + r * math.sin(angle)
            points.append((px, py))
        pygame.draw.polygon(surface, color, points, width)


# SUBTLE is imported from constants at the top of this file
```

- [ ] **Step 2: Commit**

```bash
git add pygame_app/map/hex_renderer.py
git commit -m "feat: add HexRenderer with terrain tiles, cities, units, fog, highlights"
```

---

### Task 14: Wire hex map into GameScreen

**Files:**
- Modify: `pygame_app/screens/game_screen.py`

- [ ] **Step 1: Replace game_screen.py with map rendering**

```python
"""Main gameplay screen — coordinates map, panels, popups."""
import pygame
import pygame_gui
from pygame_gui.elements import UILabel, UIButton

from pygame_app.screens.base import BaseScreen
from pygame_app.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BG, TEXT, GOLD, MAP_X, MAP_Y, MAP_W, MAP_H,
    RESOURCE_BAR_HEIGHT, ACTION_BAR_HEIGHT, LEFT_PANEL_WIDTH, RIGHT_PANEL_WIDTH,
)
from pygame_app.map.tile_atlas import TileAtlas
from pygame_app.map.camera import Camera
from pygame_app.map.hex_renderer import HexRenderer


class GameScreen(BaseScreen):
    """Main gameplay screen. Renders hex map, panels, and manages popups."""

    def __init__(self, app):
        super().__init__(app)
        self.elements = []
        self.hex_renderer = None
        self.camera = None
        self.map_surface = None
        self.next_turn_btn = None
        self._info_label = None
        self._keys_held = set()

    def enter(self):
        game = self.app.game

        # Create map rendering components
        self.camera = Camera(MAP_W, MAP_H)
        atlas = TileAtlas('assets/tiles')
        self.hex_renderer = HexRenderer(game.map, atlas, self.camera)

        # Center camera on player's first city
        if game.cities:
            first_city = list(game.cities.values())[0]
            wx, wy = self.hex_renderer.hex_to_world(*first_city.position)
            self.camera.snap_to(wx, wy)
        else:
            # Center on map middle
            mid_x, mid_y = game.map.width // 2, game.map.height // 2
            wx, wy = self.hex_renderer.hex_to_world(mid_x, mid_y)
            self.camera.snap_to(wx, wy)

        # Create map surface (off-screen buffer for the map area)
        self.map_surface = pygame.Surface((MAP_W, MAP_H))

        # UI elements
        civ_name = game.player_civ.name if hasattr(game.player_civ, 'name') else str(game.player_civ)

        # Resource bar (placeholder label — replaced with proper panel in Phase 3)
        gold_val = game.gold.get(civ_name, 0) if isinstance(game.gold, dict) else game.gold
        self._info_label = UILabel(
            relative_rect=pygame.Rect(10, 5, SCREEN_WIDTH - 250, 30),
            text=self._format_resource_text(game),
            manager=self.ui_manager,
        )
        self.elements.append(self._info_label)

        # Next Turn button
        self.next_turn_btn = UIButton(
            relative_rect=pygame.Rect(SCREEN_WIDTH - 180, SCREEN_HEIGHT - 55, 160, 45),
            text=f"Next Turn (Turn {game.state.turn})",
            manager=self.ui_manager,
        )
        self.elements.append(self.next_turn_btn)

    def exit(self):
        for el in self.elements:
            el.kill()
        self.elements.clear()

    def _format_resource_text(self, game) -> str:
        """Format resource bar text with proper rounding."""
        civ_name = game.player_civ.name if hasattr(game.player_civ, 'name') else str(game.player_civ)
        gold = game.gold.get(civ_name, 0) if isinstance(game.gold, dict) else game.gold

        # Get yields from city manager
        yields = game.city_manager.get_total_yields(
            civ_name, game.map.tiles if hasattr(game.map, 'tiles') else None
        )
        food = yields.get('food', 0)
        prod = yields.get('production', 0)
        sci = yields.get('science', 0)
        culture = yields.get('culture', 0)
        faith = yields.get('faith', 0)

        return (
            f"{civ_name}  |  "
            f"Food: {food:.1f}  |  Prod: {prod:.1f}  |  "
            f"Gold: {int(gold)}  |  Science: {sci:.1f}  |  "
            f"Culture: {culture:.1f}  |  Faith: {faith:.1f}  |  "
            f"Turn {game.state.turn}"
        )

    def handle_event(self, event):
        game = self.app.game

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.next_turn_btn:
                game.process_turn()
                self._refresh_ui()
                return

        # Map interaction — only within map bounds
        mx, my = pygame.mouse.get_pos()
        in_map = (MAP_X <= mx < MAP_X + MAP_W and MAP_Y <= my < MAP_Y + MAP_H)

        if event.type == pygame.MOUSEBUTTONDOWN and in_map:
            local_x = mx - MAP_X
            local_y = my - MAP_Y

            if event.button == 1:  # Left click — select
                hx, hy = self.hex_renderer.screen_to_hex(local_x, local_y)
                tile = game.map.get_tile(hx, hy)
                if tile:
                    self.hex_renderer.selected_hex = (hx, hy)
                else:
                    self.hex_renderer.selected_hex = None
                    self.hex_renderer.move_range.clear()
                    self.hex_renderer.attack_range.clear()

            elif event.button == 2:  # Middle click — start drag
                self.camera._dragging = True
                self.camera._drag_start = (mx, my)

            elif event.button == 4:  # Scroll up — zoom in
                self.camera.zoom_at(local_x, local_y, 1.15)

            elif event.button == 5:  # Scroll down — zoom out
                self.camera.zoom_at(local_x, local_y, 1 / 1.15)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:
                self.camera._dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.camera._dragging:
                dx = event.rel[0]
                dy = event.rel[1]
                self.camera.pan(-dx, -dy)

            if in_map:
                local_x = mx - MAP_X
                local_y = my - MAP_Y
                self.hex_renderer.hovered_hex = self.hex_renderer.screen_to_hex(local_x, local_y)
            else:
                self.hex_renderer.hovered_hex = None

        elif event.type == pygame.KEYDOWN:
            self._keys_held.add(event.key)
            if event.key == pygame.K_RETURN:
                game.process_turn()
                self._refresh_ui()
            elif event.key == pygame.K_HOME:
                # Center on capital
                if game.cities:
                    city = list(game.cities.values())[0]
                    wx, wy = self.hex_renderer.hex_to_world(*city.position)
                    self.camera.center_on(wx, wy)

        elif event.type == pygame.KEYUP:
            self._keys_held.discard(event.key)

    def update(self, dt: float):
        # WASD / arrow key panning
        pan_speed = 400  # pixels per second
        if pygame.K_w in self._keys_held or pygame.K_UP in self._keys_held:
            self.camera.pan(0, -pan_speed * dt)
        if pygame.K_s in self._keys_held or pygame.K_DOWN in self._keys_held:
            self.camera.pan(0, pan_speed * dt)
        if pygame.K_a in self._keys_held or pygame.K_LEFT in self._keys_held:
            self.camera.pan(-pan_speed * dt, 0)
        if pygame.K_d in self._keys_held or pygame.K_RIGHT in self._keys_held:
            self.camera.pan(pan_speed * dt, 0)

        self.camera.update(dt)

    def _refresh_ui(self):
        """Update all UI elements after game state change."""
        game = self.app.game
        if self._info_label:
            self._info_label.set_text(self._format_resource_text(game))
        if self.next_turn_btn:
            self.next_turn_btn.set_text(f"Next Turn (Turn {game.state.turn})")

    def draw(self, surface):
        game = self.app.game

        # Draw map into off-screen buffer
        self.map_surface.fill((10, 11, 13))
        self.hex_renderer.render(self.map_surface, game)

        # Blit map buffer to screen at map region
        surface.blit(self.map_surface, (MAP_X, MAP_Y))

        # Draw panel backgrounds (placeholder rectangles — replaced in Phase 3)
        # Left panel
        pygame.draw.rect(surface, (22, 24, 29), (0, RESOURCE_BAR_HEIGHT, LEFT_PANEL_WIDTH, SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT))
        pygame.draw.line(surface, (51, 54, 61), (LEFT_PANEL_WIDTH, RESOURCE_BAR_HEIGHT), (LEFT_PANEL_WIDTH, SCREEN_HEIGHT - ACTION_BAR_HEIGHT))

        # Right panel
        rx = SCREEN_WIDTH - RIGHT_PANEL_WIDTH
        pygame.draw.rect(surface, (22, 24, 29), (rx, RESOURCE_BAR_HEIGHT, RIGHT_PANEL_WIDTH, SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT))
        pygame.draw.line(surface, (51, 54, 61), (rx, RESOURCE_BAR_HEIGHT), (rx, SCREEN_HEIGHT - ACTION_BAR_HEIGHT))

        # Top bar background
        pygame.draw.rect(surface, (22, 24, 29), (0, 0, SCREEN_WIDTH, RESOURCE_BAR_HEIGHT))
        pygame.draw.line(surface, (51, 54, 61), (0, RESOURCE_BAR_HEIGHT), (SCREEN_WIDTH, RESOURCE_BAR_HEIGHT))

        # Bottom bar background
        by = SCREEN_HEIGHT - ACTION_BAR_HEIGHT
        pygame.draw.rect(surface, (22, 24, 29), (0, by, SCREEN_WIDTH, ACTION_BAR_HEIGHT))
        pygame.draw.line(surface, (51, 54, 61), (0, by), (SCREEN_WIDTH, by))
```

- [ ] **Step 2: Test full flow with hex map**

Run: `cd /c/Users/civer/civkings && python main.py`

Expected: After starting a new game, the hex map renders with colored hex tiles, cities show as gold circles with names, units show as colored squares. WASD pans the camera, mouse wheel zooms, middle-click drag pans. Clicking a hex highlights it in gold. Next Turn advances the game and updates the resource bar with rounded numbers (no floating point garbage).

- [ ] **Step 3: Commit**

```bash
git add pygame_app/screens/game_screen.py
git commit -m "feat: wire hex map rendering into game screen with camera, interaction"
```

---

### Task 14b: Create Minimap

**Files:** Create `pygame_app/map/minimap.py`

- [ ] **Step 1: Write minimap.py**

```python
"""Corner minimap showing full world with viewport rectangle."""
import pygame
from pygame_app.constants import MINIMAP_SIZE, TERRAIN_COLORS, GOLD, TEXT


class Minimap:
    """200x200 minimap in bottom-left corner."""

    def __init__(self, hex_map, camera):
        self.hex_map = hex_map
        self.camera = camera
        self.size = MINIMAP_SIZE
        self.surface = pygame.Surface((self.size, self.size))
        self.rect = pygame.Rect(10, 0, self.size, self.size)  # y set in draw()
        self._dirty = True
        self._base_surface = None  # Pre-rendered terrain

    def _render_base(self):
        """Pre-render the terrain minimap (only when map changes)."""
        self._base_surface = pygame.Surface((self.size, self.size))
        self._base_surface.fill((10, 11, 13))

        scale_x = self.size / max(1, self.hex_map.width)
        scale_y = self.size / max(1, self.hex_map.height)

        for x in range(self.hex_map.width):
            for y in range(self.hex_map.height):
                tile = self.hex_map.get_tile(x, y)
                if tile is None:
                    continue
                color = TERRAIN_COLORS.get(tile.terrain.name, (60, 60, 60))
                px = int(x * scale_x)
                py = int(y * scale_y)
                pw = max(2, int(scale_x))
                ph = max(2, int(scale_y))
                pygame.draw.rect(self._base_surface, color, (px, py, pw, ph))
        self._dirty = False

    def render(self, surface, game, screen_h: int):
        """Draw minimap onto the main surface."""
        if self._dirty or self._base_surface is None:
            self._render_base()

        self.surface.blit(self._base_surface, (0, 0))

        scale_x = self.size / max(1, self.hex_map.width)
        scale_y = self.size / max(1, self.hex_map.height)

        # Draw cities as bright dots
        for city in game.cities.values():
            cx, cy = city.position
            px = int(cx * scale_x)
            py = int(cy * scale_y)
            player_name = game.player_civ.name if hasattr(game.player_civ, 'name') else 'Player'
            color = GOLD if city.owner == player_name else (178, 58, 58)
            pygame.draw.circle(self.surface, color, (px, py), 3)

        # Draw viewport rectangle
        from pygame_app.map.hex_renderer import HexRenderer
        min_wx, min_wy, max_wx, max_wy = self.camera.get_visible_bounds()
        # Approximate: convert world bounds to hex grid fractions
        vx1 = int((min_wx / (64 * 1.5)) * scale_x)
        vy1 = int((min_wy / (64 * 1.732)) * scale_y)
        vx2 = int((max_wx / (64 * 1.5)) * scale_x)
        vy2 = int((max_wy / (64 * 1.732)) * scale_y)
        vw = max(10, vx2 - vx1)
        vh = max(10, vy2 - vy1)
        pygame.draw.rect(self.surface, (255, 255, 255), (vx1, vy1, vw, vh), 1)

        # Position minimap in bottom-left
        self.rect.y = screen_h - self.size - 60
        surface.blit(self.surface, self.rect)

    def handle_click(self, mx: int, my: int, screen_h: int) -> bool:
        """If click is on minimap, center camera there. Returns True if handled."""
        self.rect.y = screen_h - self.size - 60
        if not self.rect.collidepoint(mx, my):
            return False

        # Convert minimap pixel to world position
        local_x = mx - self.rect.x
        local_y = my - self.rect.y
        scale_x = self.size / max(1, self.hex_map.width)
        scale_y = self.size / max(1, self.hex_map.height)
        hx = local_x / scale_x
        hy = local_y / scale_y
        # Convert hex to world
        wx = 64 * 1.5 * hx
        wy = 64 * 1.732 * hy
        self.camera.center_on(wx, wy)
        return True
```

- [ ] **Step 2: Wire minimap into GameScreen**

In `game_screen.py`, import `Minimap`, instantiate in `enter()`, call `self.minimap.render(surface, game, SCREEN_HEIGHT)` at end of `draw()`, and add `self.minimap.handle_click(mx, my, SCREEN_HEIGHT)` to left-click handling.

- [ ] **Step 3: Commit**

```bash
git add pygame_app/map/minimap.py
git commit -m "feat: add corner minimap with terrain dots, cities, viewport rect"
```

---

### Phase 2 Verification

- [ ] Hex map renders with colored hex tiles for all terrain types
- [ ] Camera pans with WASD, arrow keys, and middle-mouse drag
- [ ] Camera zooms with mouse wheel (tiles scale correctly)
- [ ] Clicking hex selects it (gold outline)
- [ ] Cities appear with name and population on their hexes
- [ ] Units appear as colored markers on their hexes
- [ ] Fog of war darkens unexplored tiles
- [ ] Resource bar shows formatted numbers (no `1.920000000000004`)
- [ ] Next Turn processes and updates display
- [ ] Home key centers on capital
- [ ] No crashes on zoom in/out to extremes

---

## Phases 3-12: Remaining Implementation

> **IMPORTANT FOR CYNCO:** Phases 3-12 below provide task outlines with key implementation details. For each task, you MUST:
> 1. Read the corresponding spec section in `docs/superpowers/specs/2026-05-04-civkings-complete-overhaul-design.md`
> 2. Write a failing test FIRST (TDD)
> 3. Implement the minimal code to pass the test
> 4. Verify the test passes
> 5. Commit after each task
>
> **Engine API reference:** The game engine uses these verified attributes:
> - `game.map` (HexMap), `game.state.turn`, `game.state.turn_events` (List[str])
> - `game.cities` (Dict[str, City]), `game.units` (Dict[str, Unit])
> - `game.city_manager`, `game.military_manager`, `game.tech_manager`, `game.diplomacy_manager`
> - `game.gold` (Dict[str, int] keyed by civ name), `game.fog` (ExponentialFogOfWar)
> - `game.player_civ` (Civilization dataclass with `.name` attribute)
> - `city.owner` = civ name string (e.g. "Rome"), `unit.owner` = same
> - `unit.hp`, `unit.max_hp` = int, `tile.has_river` = bool, `tile.resource` = Optional[ResourceType enum]
> - `game.process_turn()` returns List[str] of event messages

---

## Phase 3: UI Panels

### Task 15: Resource Bar panel

**Files:** Create `pygame_app/panels/resource_bar.py`

Implement a `ResourceBar` class that:
- Creates a pygame_gui UIPanel spanning the top 40px of the screen
- Shows labels for: Civ Name, Era, Food, Production, Gold (+per turn), Science (+per turn), Culture, Faith, Turn counter
- Has a `refresh(game)` method that reads current game state and updates all labels
- All float values displayed via `f"{val:.1f}"` or `int(val)` — NEVER raw floats
- Gold shows income: `"Gold: 100 (+21/turn)"` by computing income from `city_manager.get_total_yields()`
- Call `refresh(game)` from `GameScreen.update()` every frame

### Task 16: City Panel (left sidebar)

**Files:** Create `pygame_app/panels/city_panel.py`

Implement a `CityPanel` class using `UIScrollingContainer` in the left sidebar (0, 40, 260, variable height):
- Lists all player cities from `game.city_manager.get_cities_by_owner(civ_name)`
- Each city entry: name (bold), population, current production + progress bar, "IDLE" warning if queue empty
- Clicking a city entry emits a custom event with city reference (GameScreen handles camera centering)
- Has `refresh(cities)` method

### Task 17: Unit Panel (left sidebar, below cities)

**Files:** Create `pygame_app/panels/unit_panel.py`

Implement a `UnitPanel` class:
- Lists all player units from `game.military_manager.get_units_by_owner(civ_name)`
- Each entry: unit type icon/text, HP bar, movement remaining, position, status
- Clicking a unit emits event for camera centering and selection
- Spent units (moves_left == 0) shown with dimmed text

### Task 18: Event Log (right sidebar)

**Files:** Create `pygame_app/panels/event_log.py`

Implement an `EventLog` class using `UITextBox` with HTML subset:
- Scrollable, 280px wide, in right sidebar
- Color-coded entries: gold=economy, red=combat, green=growth, blue=science, purple=dynasty
- `add_event(text, category)` method that prepends colored HTML text
- Receives events from `game.state.turn_events` after each `process_turn()`

### Task 19: Turn Summary popup

**Files:** Create `pygame_app/panels/turn_summary.py`

Implement a `TurnSummary` class that:
- After `process_turn()`, collects all events from `game.state.turn_events`
- Creates a `UIWindow` popup listing all events
- Each event is clickable (emits event with location for camera jump)
- "Dismiss All" button closes the popup
- Only shows if there are events to display

### Task 20: Action Bar (bottom)

**Files:** Create `pygame_app/panels/action_bar.py`

Implement an `ActionBar` class:
- Bottom 50px strip with context-sensitive buttons
- When unit selected: Move (M), Attack (A), Fortify (F), Skip (Space), Disband
- When city selected: Production (P), Buy (B)
- When nothing selected: Next Turn (Enter), Next Unit (Tab), Tech Tree (T), Diplomacy (D)
- End Turn button shows RED pulsing if idle cities/unmoved units exist, GOLD when ready
- Before ending turn: check for idle cities (`production_queue` empty) and units with moves — show warning dialog

### Task 21: Wire all panels into GameScreen

**Files:** Modify `pygame_app/screens/game_screen.py`

- Import and instantiate all panel classes in `GameScreen.enter()`
- Call each panel's `refresh(game)` in `GameScreen.update()`
- Route panel events (city click, unit click) to camera centering and selection
- Remove placeholder labels/buttons that panels replace

---

## Phase 4: Popups and Dialogs

### Task 22: Production Popup
**Files:** Create `pygame_app/popups/production.py`
- UIWindow with two columns: Available items (grouped: Units, Buildings, Districts) and Production Queue
- Items from `game_data.UNIT_TYPES`, `BUILDINGS`, `DISTRICTS` filtered by prerequisites
- Queue supports add (double-click), remove, reorder
- Shows turns-to-complete based on city production rate from `city.calculate_yields()`
- Buy button: cost = remaining production * 4 gold
- Calls `city.assign_production(item)` when item selected

### Task 23: Tech Tree Popup
**Files:** Create `pygame_app/popups/tech_tree.py`
- Full-screen UIWindow overlay with horizontal layout
- Techs from `game_data.TECHNOLOGIES` organized by Era columns
- Prerequisite arrows drawn with `pygame.draw.line()`
- Color: green=researched, blue=current (progress bar), white=available, grey=locked
- Click available tech calls `game.tech_manager.start_research(tech)`
- Hover shows: name, cost, prerequisites, unlocks from `Technology` dataclass

### Task 24: Diplomacy Popup
**Files:** Create `pygame_app/popups/diplomacy.py`
- Left panel: list of known civs from `game.diplomacy_manager.get_all_relations()`
- Right panel: selected civ details — opinion score, treaties, modifiers
- Action buttons: Declare War (`declare_war()`), Propose Alliance (`propose_alliance()`), Trade Agreement, Denounce
- Show war/alliance/truce status from `DiplomacyManager` methods

### Task 25: Dynasty Popup
**Files:** Create `pygame_app/popups/dynasty.py`
- Shows current ruler from `game.characters[0]` (or `game.dynasty.root`)
- Stats display: diplomacy, martial, stewardship, intrigue (bar charts)
- Traits list from `character.traits` mapped to `TRAIT_DATABASE` bonuses
- Heir info from dynasty members
- Court positions from `game.court`
- Succession law from `game_data.SuccessionLaw`

### Task 26: Combat Result Popup
**Files:** Create `pygame_app/popups/combat_result.py`
- Pre-combat preview: show both armies' strength, terrain bonuses, predicted outcome
- Post-combat result: victory/defeat, casualties from `CombatResult` dataclass, XP gained, promotions
- Uses `resolve_combat()` from `combat.py`

### Task 27: Event Choice Popup
**Files:** Create `pygame_app/popups/event_choice.py`
- Shows event name, description from `Event` class
- Renders choice buttons with effect previews from `event.choices`
- Calls `event.evaluate_choice(choice)` on selection

### Task 28: City Detail Popup
**Files:** Create `pygame_app/popups/city_detail.py`
- Detailed city view from `City` object
- Yields breakdown from `city.calculate_yields(tiles)`
- Buildings list from `city.buildings`
- Districts from `city.districts`
- Growth info from `CityGrowthSystem.get_food_needed_for_next_level(city.population)`

### Task 29: Encyclopedia
**Files:** Create `pygame_app/popups/encyclopedia.py`
- Searchable reference opened with F1
- Categories populated from `game_data.py`: TERRAIN_YIELDS, UNIT_TYPES, BUILDINGS, DISTRICTS, TECHNOLOGIES, CIVILIZATIONS
- Each entry: name, stats, description, requirements
- Linked entries (clicking tech name opens that tech's entry)

---

## Phase 5: Sound and Visual Effects

### Task 30: Sound Manager
**Files:** Create `pygame_app/audio/sound_manager.py`
- `SoundManager` class with `play(category, sound_name, volume)` method
- Loads OGG files from `assets/sounds/{category}/`
- Categories: ui, combat, city, diplomacy, turn, character
- Uses `pygame.mixer.Sound` for effects, separate channels per category
- Graceful fallback if sound files don't exist (no crash, just no sound)

### Task 31: Music Manager
**Files:** Create `pygame_app/audio/music_manager.py`
- `MusicManager` with `update_era(era)` method
- Maps `Era` enum to `assets/music/{era}.ogg`
- Cross-fades between tracks using `pygame.mixer.music.fadeout()` + `.play(fade_ms=)`
- Loops background music infinitely
- Graceful fallback if music files don't exist

### Task 32: Create placeholder sound assets
**Files:** Create `tools/generate_placeholder_sounds.py`
- Generates simple sine wave / noise burst OGG files using Python's `wave` module + Pillow
- Creates: click.ogg, confirm.ogg, notification.ogg, turn_start.ogg
- Stores in `assets/sounds/ui/` and `assets/sounds/events/`
- These are temporary — replaced with real sounds later

### Task 33: Unit Movement Animation
**Files:** Create `pygame_app/map/map_animations.py`
- `UnitMoveAnimation` class: slides unit sprite from hex A to hex B over 300ms
- Uses linear interpolation with ease-out curve
- GameScreen checks active animations before processing new input
- Camera follows animated unit if it's the selected unit

### Task 34: Particle System
**Files:** Create `pygame_app/effects/particles.py`
- `ParticleEmitter` class with `emit(x, y, count, color, lifetime, speed)`
- Each particle: position, velocity, alpha, lifetime
- `update(dt)` moves particles and culls expired ones
- `draw(surface)` renders particles as small circles with fading alpha
- Used for: combat impact (red sparks), city celebration (gold confetti), tech complete (blue sparkles)

### Task 35: Wire sound and effects into GameScreen
**Files:** Modify `pygame_app/screens/game_screen.py`
- Instantiate `SoundManager` and `MusicManager` in `enter()`
- Play `ui/click` on button press
- Play `events/notification` on turn summary popup
- Play `combat/sword_clash` on combat result
- Play `city/production_complete` when production finishes
- Call `music_manager.update_era()` when tech manager's current era changes
- Instantiate `ParticleEmitter`, trigger particles on combat/production events
- Instantiate `UnitMoveAnimation` when units move, render in `draw()`

---

## Phase 6: Game Engine Fixes

### Task 36: Fix AI player initialization
**Files:** Modify `game.py`
- Add `ai_civs` parameter handling in `Game.__init__()` — currently accepts but doesn't use it
- When ai_civs provided, create `AIPlayer` instances in `self.ai_players`
- Place AI starting cities on the map with minimum 5-hex separation
- Give each AI civ 1 city + 1 warrior + 1 scout on the map
- Use `hex_map.get_starting_tile()` or implement `find_start_positions(count)` that distributes evenly

### Task 37: Fix AI turn processing
**Files:** Modify `game.py` `process_turn()` method
- Verify each AI player's `decide_next_action()` is called with correct params
- AI actions should: choose research, assign production in cities, move units
- AI-generated events should be added to `game.state.turn_events`
- Test: after 20 turns, AI should have researched techs and built units

### Task 38: Fix save/load for Pygame
**Files:** Modify `save_system.py`, create `pygame_app/popups/save_load.py`
- Verify `save_game()` serializes all manager states correctly
- Verify `load_game()` restores all managers
- Create save/load popup in Pygame with slot selection (UISelectionList of save files)
- Wire "Save Game" button in action bar and "Load Game" in main menu

---

## Phase 7: Core Missing Mechanics

### Task 39: Eureka/Inspiration System
**Files:** Modify `tech.py`, modify `game_data.py`
- Add `EUREKA_CONDITIONS` dict to `game_data.py` mapping tech names to trigger conditions
- Add `EurekaTracker` class to `tech.py` with `check_event(event_type, context)` method
- Hook into `game.process_turn()` — check eureka conditions against turn events
- When triggered: apply 50% research discount, add notification event
- Add eureka status display to tech tree popup (show condition + whether triggered)

### Task 40: Worker Improvements
**Files:** Create `improvements.py`, modify `hex_map.py`, modify `military.py`
- Add `improvement` field to `HexTile` class
- Create `IMPROVEMENTS` dict with terrain compatibility, yields, build turns, tech requirements
- Add `build_improvement(unit, tile, improvement_type)` function
- Worker unit action: select improvement type from valid options, start building
- Improvement progress tracked per-tile, completes after N turns of worker working
- Completed improvements modify tile yields via `HexTile.get_yields()`
- Draw improvement icons on map in `HexRenderer`

### Task 41: Wonders
**Files:** Modify `game_data.py`, modify `city.py`, modify `city_growth.py`
- Add `WONDERS` dict to `game_data.py` (from spec: Pyramids, Great Library, Stonehenge, Colosseum, Hagia Sophia, Oxford University)
- Modify `WonderSystem` in `city_growth.py` — it already has a stub, flesh it out
- Global tracking: `WonderSystem.built_wonders` set — only one civ can build each
- Add wonder items to production popup alongside buildings
- When wonder completed: apply effects, add to `built_wonders`, notify all players
- If another civ completes first: refund 50% as gold, show notification

### Task 42: Great People
**Files:** Create `great_people.py`, modify `game.py`
- `GREAT_PERSON_TYPES` dict: Great General, Scientist, Engineer, Merchant, Prophet
- `GreatPeopleManager` class: tracks GPP per type per civ, recruitment thresholds
- GPP generated from districts: Campus -> Great Scientist points, Encampment -> Great General points
- First civ to reach threshold recruits the Great Person (spawns in district city)
- Great Person is a special unit with a one-time "retire" action
- Create Great People popup showing GPP race progress
- Wire into `game.process_turn()` — accumulate GPP, check thresholds, spawn

### Task 43: Combat Overhaul
**Files:** Modify `combat.py`, modify `military.py`
- Add Zone of Control: `get_zoc_hexes(unit)` returns 6 adjacent hexes. Enemy units stop when entering ZoC
- Add flanking: `calculate_flanking_bonus(attacker_pos, defender_pos, friendly_units)` returns +2 per adjacent friendly
- Add counter bonuses: `COUNTER_BONUSES` dict in `combat.py`, applied in `resolve_combat()`
- Add ranged combat: ranged units attack without return damage, using `unit.attack` within `get_base_stats()` range
- Add fortify action: `unit.is_fortified` already exists, add `fortify_bonus` (+3 first turn, +6 after 2)
- Add promotion tree: replace flat `PROMOTION_TIERS` with branching choices per unit category
- Add combat preview: `preview_combat(attacker_army, defender_army, tile)` returns estimated outcome without modifying state

### Task 44: Adjacency Bonuses
**Files:** Modify `city.py`
- Implement `City.calculate_adjacency()` to actually check neighboring tiles when placing districts
- Use `DISTRICTS[type].adjacency_bonus` dict and `hex_map.get_neighbors()`
- Show adjacency preview numbers when placing districts (highlight candidate hexes with bonus values)
- Apply adjacency bonus to city yields in `calculate_yields()`

### Task 45: Housing and Amenities
**Files:** Modify `city_growth.py`, modify `happiness_system.py`
- Add housing cap to `CityGrowthSystem.process_growth()`:
  - Base: 2 (no water), 3 (coast), 5 (river)
  - Granary: +2, Aqueduct: +2, Neighborhood: +4
  - When pop >= housing: growth rate halved. When pop > housing+5: growth stops
- Convert `HappinessSystem` to per-city amenities:
  - Each city needs 1 amenity per 2 pop above 2
  - Sources: unique luxuries (1 each, shared across 4 cities), entertainment buildings, wonders
  - Deficit: -10% growth/production per missing amenity
  - Surplus: +5% growth per extra (max +20%)

---

## Phase 8: Advanced CK-Style Mechanics

### Task 45b: Congenital Traits and Marriage
**Files:** Modify `game_data.py`, modify `simulation.py`
- Add `CONGENITAL_TRAITS` dict to `game_data.py`: Beautiful (+3 diplomacy, 10% inherit), Genius (+2 all, 5% inherit), Herculean (+3 martial, 10% inherit), Fecund (+30% fertility, 15% inherit), Clubfooted (-1 martial, 10% inherit), Inbred (-3 all, 25% inherit)
- Modify `generate_child()` in `simulation.py` to check both parents' congenital traits and roll inheritance
- Add `arrange_marriage(character_a, character_b)` function: creates alliance bonus with target's civ, children inherit traits from both parents
- Marriage choices affect diplomacy: `diplomacy_manager.modify_relation()` on marriage
- Wire into dynasty popup: show "Arrange Marriage" button when eligible characters exist

### Task 45c: Scheme System Enhancement
**Files:** Modify `plots.py`
- Add `power` and `resistance` attributes to `Plot` class
- Power = sum of agents' intrigue stats + mastermind intrigue
- Resistance = target's spymaster skill + court security rating
- Add `agent` recruitment: `plot.recruit_agent(character)` — each agent adds power but +10% detection risk
- Max 5 agents per scheme. Success chance = power / (power + resistance) * 100, capped at 95%
- 5 detection events = automatic failure
- Add scheme types: Murder, Fabricate Claim, Sway, Seduce, Steal Technology
- Wire into game.process_turn(): advance all active plots, check detection, resolve completed schemes

### Task 46: Stress System
**Files:** Modify `simulation.py`
- Add `StressSystem` class with stress 0-300, thresholds at 100/200/300
- `STRESS_TRIGGERS` dict mapping (trait, action) pairs to stress gain amounts
- `check_action(character, action_type)` method that adds stress if action contradicts traits
- Coping mechanism popup at thresholds (choose Drunkard, Glutton, Recluse, etc.)
- Stress decays -2 per turn base, court physician reduces further
- Wire into game actions: declare_war checks for Peaceful trait, execute checks Compassionate, etc.

### Task 47: Succession Implementation
**Files:** Modify `simulation.py`, modify `game.py`
- `execute_succession(ruler, succession_law, cities, heirs)` function
- Primogeniture: eldest child gets everything
- Gavelkind: split cities among children — extra children's cities become AI-controlled
- Elective: faction leaders vote (weighted by influence from `FactionManager`)
- On ruler death: create succession crisis event (-25 stability), run succession, install new ruler
- New ruler's traits/stats affect gameplay
- Wire into `game.process_turn()` — check ruler health/age each turn

### Task 48: Hooks and Secrets
**Files:** Create `secrets.py`
- `Secret` class: owner, type (affair/murder/heresy/embezzlement), severity, known_by list
- `Hook` class: holder, target, type (weak/strong), source secret, used flag
- `SecretsManager`: create_secret, discover_secret, create_hook, use_hook
- Hooks force diplomatic actions: demand gold, force alliance, prevent betrayal
- Discovered via spy actions (integrate with `PlotManager`)
- Wire into diplomacy popup — show available hooks when interacting with characters

### Task 49: Dynasty Legacies
**Files:** Modify `simulation.py`, modify `game_data.py`
- Add `DYNASTY_LEGACIES` dict to `game_data.py` (Warfare, Law, Blood, Erudition tracks)
- Add renown resource to Dynasty class: earned from landed dynasty members each turn
- `DynastyLegacyManager`: purchase_legacy, get_active_bonuses
- Legacy bonuses apply dynasty-wide via modifier checks in relevant systems
- Create dynasty legacy popup accessible from dynasty panel

---

## Phase 9: Advanced Civ-Style Mechanics

### Task 50: Era Score and Golden/Dark Ages
**Files:** Create `era_system.py`, modify `game.py`
- `EraSystem` class with `HISTORIC_MOMENTS` dict (first to research, first wonder, etc.)
- `record_moment(moment_type)` adds to era score
- `check_era_transition(tech_manager)` when entering new era: evaluate score
- Golden Age: choose dedication bonus for the era
- Dark Age: loyalty penalties but unlock special policies
- Era transition popup with summary of achievements

### Task 51: Loyalty System
**Files:** Create `loyalty.py`, modify `city.py`
- Per-city loyalty 0-100, calculated each turn
- Sources: +8 from nearby own cities, -3 from nearby foreign cities, +/-3 from golden/dark age, happiness effects
- Below 0: city revolts (becomes independent city-state or joins nearest civ)
- `LoyaltyManager.calculate_loyalty(city, game)` method
- Show loyalty bar in city panel and city detail popup
- Wire into `game.process_turn()`

### Task 52: Policy Cards and Government
**Files:** Modify `tech_policies.py`, modify `game_data.py`
- Add `POLICY_CARDS` dict with military/economic/diplomatic/wildcard categories
- Modify `GOVERNMENTS` to include slot counts per policy type
- Government change: costs N turns of anarchy (zero yields)
- Policies swappable when completing a civic/tech
- Create government popup with slot grid — drag cards into slots
- Policy bonuses applied as modifiers in yield/combat/diplomacy calculations

### Task 53: Trade Routes with Trader Units
**Files:** Modify `external_trade_routes.py`, modify `game_data.py`
- Add "Trader" to `UNIT_TYPES` as civilian unit
- Trader unit action: select destination city, create route
- Domestic route: transfer food/production surplus
- International route: gold for both civs, religion spread
- Routes last 20 turns, then trader returns
- Draw trade route lines on map (dotted gold/colored lines between cities)
- Create trade popup showing active routes and available destinations

### Task 54: Religion Enhancement
**Files:** Modify `religion.py`, modify `game_data.py`
- Add `FOUNDER_BELIEFS` and `FOLLOWER_BELIEFS` dicts
- Religion founding: first to 25 faith via Great Prophet, choose beliefs
- Add Missionary civilian unit: spread religion (3 charges)
- `ReligionManager.spread_religion()` enhanced with missionary mechanics
- Religious combat between apostle-type units
- Create religion popup showing founded religions, beliefs, spread map

### Task 55: Victory Condition Overhaul
**Files:** Modify `victory.py`
- Domination: control all original capitals (track `original_capital` per civ)
- Science: complete 3 space projects (new production items with huge costs)
- Culture: tourism from wonders/great works exceeds other civs' domestic tourists
- Religious: your religion majority in every civ
- Diplomatic: accumulate 20 diplomatic victory points from alliances/achievements
- Dynasty: 15 generations with 5+ legacy perks
- Update `VictoryConditionTracker` with new threshold calculations
- Victory progress visible in victory popup for all types

---

## Phase 10: AI Overhaul

### Task 56: AI Decision Framework Rewrite
**Files:** Rewrite `ai.py`
- Priority-based system: `_evaluate_priorities(game)` sets weights for military/science/economy/expansion
- `_manage_research(game)`: pick tech based on priority (military->Iron Working, science->Writing, etc.)
- `_manage_production(game)`: for each city, assign production based on needs (low food->Granary, threatened->Warrior)
- `_manage_military(game)`: move units toward threats or expansion targets, garrison cities
- `_manage_diplomacy(game)`: propose treaties when beneficial, declare war when 2:1 advantage
- AI personality from civ traits affects priority weights
- Test: play 50 turns, verify AI has multiple cities, army, researched techs, and fought wars

### Task 57: Difficulty Scaling
**Files:** Modify `ai.py`
- `DIFFICULTY_MODIFIERS` dict: yield bonuses, combat bonuses, starting unit counts, AI decision quality
- Rookie: AI makes random choices, 80% yields
- Standard: AI uses heuristics, 100% yields
- Immortal: AI uses best heuristics, 120% yields, +2 starting units
- Apply modifiers in AI decision methods and yield calculations

---

## Phase 11: Polish, Balance, Tutorial

### Task 58: Tutorial System
**Files:** Create `tutorial.py`, modify `pygame_app/screens/game_screen.py`
- `Tutorial` class with state machine tracking which step the player is on
- Steps triggered by game state (turn 1: select settler, turn 2: open production, etc.)
- Shows contextual tooltip popup with arrow pointing to relevant UI element
- Can be dismissed or disabled via settings
- Only activates on first game (flag in settings file)

### Task 59: Keyboard Shortcuts
**Files:** Modify `pygame_app/screens/game_screen.py`
- Wire all keyboard shortcuts from spec: M=Move, A=Attack, F=Fortify, Space=Skip, Tab=Next Unit, T=Tech, D=Diplomacy, Y=Dynasty, G=Toggle yields, B=Buy, F1=Encyclopedia, F5=Quick save, F9=Quick load, +/-=Zoom, Home=Capital, .=Next city
- Each shortcut triggers the same action as its corresponding button

### Task 60: Settings Panel
**Files:** Create `pygame_app/popups/settings.py`
- UIWindow with sliders: Master Volume, Music Volume, SFX Volume
- Toggles: Fullscreen, Show Tile Yields, Enable Tutorial
- Dropdown: Animation Speed (Slow/Normal/Fast/Instant)
- Persist to `~/.civkings/settings.json`
- Load settings on app startup, apply to sound/music managers

### Task 61: Balance Pass
**Files:** Modify `game_data.py`
- Review and adjust: unit costs/strengths (2x cost = ~1.5x strength), tech costs per era (Ancient 15-25 turns, Classical 20-30, etc.), building costs scaling with era, food table for growth rates (pop 3 by turn 15, pop 6 by turn 40)
- Verify gold economy: positive early, tight mid-game, rich late-game
- Verify AI pacing: 2nd city by turn 20, 4 cities by turn 60, first war by turn 40-80
- Run automated 100-turn test and log progression milestones

---

## Phase 12: Cleanup and Final Integration

### Task 62: Delete legacy files
**Files:** Delete all files listed in "Files to delete" section above
- `git rm gui.py gui_map.py gui_panels.py gui_popups.py gui_combat.py victory_ui.py visual_effects.py sound_effects.py gui_popups_backup.py gui_popups_original.py fix_canvas.py fix_popup.py fix_popups.py fix_popups2.py map.py clean.py`
- Verify no remaining files import from deleted modules

### Task 63: Integration Verification
**Files:** All
- Run: `grep -r "import tkinter" *.py` — should return nothing (except ui.py if kept)
- Run: `grep -r "from gui" *.py` — should return nothing in active files
- Run: `python -c "from game import Game; from pygame_app.app import GameApp; print('All imports OK')"`
- Run: `python -m pytest tests/` — all existing tests pass
- Run: play 100 turns manually — no crashes, AI plays, events fire, all popups work

### Task 64: Final Commit and Tag
```bash
git add -A
git commit -m "feat: CivKings v2.0 — Pygame migration complete with full game mechanics"
git tag v2.0
```

---

## Wire Check (BLOCKING)

Before marking ANY phase complete, run these verifications:

```bash
# Check no orphaned imports
cd /c/Users/civer/civkings
python -c "
import pygame; pygame.init()
s = pygame.display.set_mode((100, 100))
from pygame_app.app import GameApp
from pygame_app.screens.main_menu import MainMenuScreen
from pygame_app.screens.new_game_dialog import NewGameDialog
from pygame_app.screens.game_screen import GameScreen
from pygame_app.map.tile_atlas import TileAtlas
from pygame_app.map.camera import Camera
from pygame_app.map.hex_renderer import HexRenderer
print('All Pygame imports OK')
pygame.quit()
"

# Check engine still works independently
python -c "
from game import Game
from game_data import CIVILIZATIONS
g = Game(CIVILIZATIONS['Rome'])
g.process_turn()
print(f'Engine OK — Turn {g.state.turn}')
"

# Check no floating point display
python -c "
v = 1.920000000000004
print(f'{v:.1f}')  # Must print '1.9'
assert f'{v:.1f}' == '1.9'
print('Float formatting OK')
"
```

Every new class/function must be:
1. Imported where it's used
2. Called in the correct execution path
3. Included in save_system.py serialization (if it has state)
4. Displayed in a UI panel or popup (if player-facing)
5. Covered by at least one test or manual verification step
