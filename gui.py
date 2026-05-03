"""
CivKings - Tkinter GUI
Full graphical user interface for CivKings.
Wires into existing game.py, city.py, tech.py, military.py without modifying them.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Tuple
import math
import time

from game import Game, GameState
from game_data import CIVILIZATIONS, Civilization, TECHNOLOGIES, Technology, Era, TechBranch, UNIT_TYPES, UnitType, BUILDINGS, DISTRICTS, BuildingType, DistrictType, TerrainType, MAP_WEIGHTS, RESOURCE_WEIGHTS, ResourceType
from hex_map import HexMap, HexTile, WorldMap, FogOfWar
from city import City
from military import Unit
from city import CityManager
from military import MilitaryManager
from tech import TechManager
from diplomacy import DiplomacyManager
from religion import ReligionManager
from events import EventManager
from plots import PlotManager
from simulation import Character, Dynasty
from ai import AIPlayer
from gui_map import HexGridRenderer, HoverTooltip, MapCanvas, TileHighlight, MinimapRenderer
from gui_popups import ProductionPopup, UnitInfoPopup, DiplomacyPopup, DynastyPopup, VictoryPanel, TechTreePopup, FactionsPanel, HappinessPanel, StabilityPanel, EconomyPanel, DiplomacyPanel
from sound_effects import get_sound_manager
from visual_effects import VisualEffects



# ── Dark Fantasy Colour Palette ─────────────────────────────────
BG = "#0a0b0d"
PANEL_BG = "#16181d"
PANEL_BG2 = "#23262d"
ACCENT = "#23262d"
HIGHLIGHT = "#c5a059"
TEXT = "#e0e0e0"
SUBTLE = "#888"
BORDER = "#33363d"
GOLD = "#c5a059"
RED = "#b23a3a"
TERRAIN_COL: Dict[TerrainType, str] = {
    TerrainType.PLAINS:       "#3d4d3d",
    TerrainType.GRASSLAND:    "#4a5d4a",
    TerrainType.FOREST:       "#2d4a2d",
    TerrainType.HILLS:        "#5a5a3d",
    TerrainType.MOUNTAIN:     "#4a4a4a",
    TerrainType.DESERT:       "#6a5a3a",
    TerrainType.TUNDRA:       "#5a6a6a",
    TerrainType.WATER_COAST:  "#2a4a6a",
    TerrainType.OCEAN:        "#1a3a5a",
}


# ── New Game dialog ──────────────────────────────────────────────────
class NewGameDialog:
    """Modal for selecting player civ and difficulty before launching a game."""

    def __init__(self, parent: tk.Tk) -> None:
        self.parent = parent
        self.result: Optional[Tuple[Civilization, str]] = None
        self._build()

    def _civ_color(self, civ: Civilization) -> str:
        return CIVILIZATIONS[civ.name].color if hasattr(civ, "name") else "white"

    def _build(self) -> None:
        self.win = tk.Toplevel(self.parent)
        self.win.title("New Game")
        self.win.geometry("720x520")
        self.win.resizable(False, False)
        self.win.transient(self.parent)
        self.win.grab_set()
        self.win.configure(bg=BG)

        tk.Label(self.win, text="DYNASTY & DOMINION", font=("Segoe UI", 20, "bold"),
                 bg=BG, fg=GOLD).pack(pady=(20, 10))

        # difficulty
        diff_frame = tk.Frame(self.win, bg=BG)
        diff_frame.pack(pady=(0, 10))

        self.diff_var = tk.StringVar(value="Standard")
        for d in ["Rookie", "Easy", "Standard", "Hard", "Immortal"]:
            tk.Radiobutton(diff_frame, text=d, variable=self.diff_var,
                           value=d, bg=BG, fg=TEXT, selectcolor=BG).pack(side=tk.LEFT, padx=6)

        # civ selection
        tk.Label(self.win, text="Choose your civilization:", font=("Segoe UI", 12),
                 bg=BG, fg=TEXT).pack(pady=(10, 4))

        self.sel_civ = tk.StringVar()
        scroll = tk.Frame(self.win, bg=PANEL_BG, width=680, height=200, highlightbackground=BORDER, highlightthickness=1)
        scroll.pack(pady=4)
        scroll.pack_propagate(False)

        cv = tk.Canvas(scroll, bg=PANEL_BG, highlightthickness=0, highlightbackground=BORDER)
        sb = tk.Scrollbar(scroll, orient=tk.VERTICAL, command=cv.yview, bg=PANEL_BG2)
        sf = tk.Frame(cv, bg=PANEL_BG)
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.scroll_frame = sf
        for civ in CIVILIZATIONS.values():
            f = tk.Frame(sf, bg=PANEL_BG, highlightbackground=BORDER, highlightthickness=0)
            f.pack(fill=tk.X, padx=4, pady=2)
            clr = self._civ_color(civ)
            tk.Label(f, text=f"●  {civ.name} ({civ.bonus})", bg=PANEL_BG, fg=clr,
                     font=("Segoe UI", 10), padx=6, anchor=tk.W).pack(side=tk.LEFT)
            tk.Radiobutton(f, variable=self.sel_civ, value=civ.name,
                           bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG).pack(side=tk.RIGHT)

        # start button
        def on_start():
            if not self.sel_civ.get():
                messagebox.showwarning("Warning", "Please select a civilization.")
                return
            civ = CIVILIZATIONS[self.sel_civ.get()]
            self.result = (civ, self.diff_var.get())
            self.win.destroy()

        tk.Button(self.win, text="Start Game!", font=("Segoe UI", 14, "bold"),
                  bg=GOLD, fg="#000", activebackground="#d4af6a", activeforeground="#000",
                  command=on_start).pack(pady=(10, 20))


# ── Tech Tree panel (right side) ────────────────────────
class TechTreePanel(tk.Frame):
    """Shows the technology tree with researched/unlocked states."""

    def __init__(self, parent, tech_mgr: TechManager) -> None:
        super().__init__(parent, bg=BG)
        self.tech_mgr = tech_mgr
        self.pack(fill=tk.BOTH, expand=True)
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Technology Tree", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=GOLD, anchor=tk.W).pack(fill=tk.X, padx=8, pady=(8, 0))

        # search
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter())
        tk.Entry(self, textvariable=self.search_var, bg=PANEL_BG2, fg=TEXT,
                 insertbackground=TEXT, font=("Segoe UI", 10), relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER).pack(fill=tk.X, padx=8, pady=4)

        # branch filter
        self.branch_var = tk.StringVar(value="All")
        branches = ["All"] + list({t.branch for t in TECHNOLOGIES.values()})
        for b in branches:
            tk.Radiobutton(self, text=b, variable=self.branch_var, value=b,
                           bg=BG, fg=TEXT, selectcolor=BG, command=self._filter, padx=4).pack(side=tk.LEFT, padx=4)

        # scrollable tech list
        scroll_frame = tk.Frame(self, bg=BG)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        scroll_frame.pack_propagate(False)

        self.canvas = tk.Canvas(scroll_frame, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(scroll_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=BG)
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._filter()

    def _filter(self) -> None:
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        branch = self.branch_var.get()
        if branch == "All":
            branch = None
        filter_txt = self.search_var.get().lower()
        researched = self.tech_mgr.researched_techs

        for tech in sorted(TECHNOLOGIES.values(), key=lambda t: t.cost):
            if branch and tech.branch != branch:
                continue
            if filter_txt and filter_txt not in tech.name.lower():
                continue
            is_done = tech.name in researched
            is_avail = not is_done and all(p in researched for p in tech.prerequisites)

            row = tk.Frame(self.scroll_frame, bg=BG)
            row.pack(fill=tk.X, padx=4, pady=1)
            icon = "✓" if is_done else ("▶" if is_avail else "🔒")
            clr = "#4caf50" if is_done else ("#ffeb3b" if is_avail else "#555")
            tk.Label(row, text=f"{icon}  {tech.name}", bg=BG, fg=clr, font=("Segoe UI", 10),
                     padx=6, pady=1, anchor=tk.W).pack(side=tk.LEFT)
            prereq_str = ", ".join(tech.prerequisites) if tech.prerequisites else "None"
            tk.Label(row, text=f"[{prereq_str}]  cost:{tech.cost}", bg=BG, fg=SUBTLE,
                     font=("Segoe UI", 8), padx=6, anchor=tk.W).pack(side=tk.LEFT)
            self.scroll_frame.wframes.append(row)


# ── City detail panel (right side) ────────────────────────────
class CityDetailPanel(tk.Frame):
    """Shows info about the selected / capital city."""

    def __init__(self, parent) -> None:
        super().__init__(parent, bg=PANEL_BG)
        self.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._build()

    def _build(self) -> None:
        self.title_lbl = tk.Label(self, text="City", font=("Segoe UI", 14, "bold"),
                                   bg=PANEL_BG, fg=GOLD, anchor=tk.W)
        self.title_lbl.pack(fill=tk.X, padx=8, pady=(8, 0))

        self.info_text = tk.Text(self, bg=PANEL_BG, fg=TEXT, font=("Consolas", 10),
                                 padx=8, pady=4, relief=tk.FLAT, wrap=tk.NONE,
                                 highlightthickness=0, highlightbackground=BORDER, state=tk.DISABLED)
        sb = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=sb.set)
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        # production queue area
        self.prod_frame = tk.Frame(self, bg=PANEL_BG)
        self.prod_frame.pack(fill=tk.X, padx=8, pady=(4, 0))

        # production queue label
        self.prod_label = tk.Label(self.prod_frame, text="Production Queue",
                                 bg=PANEL_BG, fg=GOLD, font=("Segoe UI", 10, "bold"),
                                 anchor=tk.W)
        self.prod_label.pack(fill=tk.X, pady=(0, 2))

        # production queue list
        self.prod_list = tk.Frame(self.prod_frame, bg=PANEL_BG)
        self.prod_list.pack(fill=tk.X)

        # quick start button
        self.start_btn = tk.Button(self.prod_frame, text="\u25b6 Start Production",
                                 bg=GOLD, fg="#000", font=("Segoe UI", 10, "bold"),
                                 activebackground="#d4af6a", activeforeground="#000",
                                 command=self._on_start)
        self.start_btn.pack(fill=tk.X, pady=(4, 0))

    def _on_start(self):
        from gui_popups import ProductionPopup
        if not self._city:
            return
        popup = ProductionPopup(self, self._city)

    def _clear_prod_list(self):
        for w in self.prod_list.winfo_children():
            w.destroy()

    def update(self, city: City) -> None:
        self._city = city
        self.title_lbl.config(text=city.name)
        text = (
            f"Owner:       {city.owner}\n"
            f"Position:    {city.position}\n"
            f"Population:  {city.population}\n"
            f"Gold:        {city.gold}\n"
            f"Production:  {city.production}/{city.production_capacity}\n"
            f"Science:     {city.science}\n"
            f"Happiness:   {city.happiness}\n"
            f"Yields:      {city.calculate_yields()}\n"
            f"Districts:   {list(city.districts.keys())}\n"
            f"Buildings:   {list(city.buildings.keys())}\n"
            f"Queue:       {city.production_queue}\n"
            f"Current:     {city.current_production}\n"
        )
        self.info_text.configure(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert(tk.END, text)
        self.info_text.configure(state=tk.DISABLED)

        # Update production queue display
        self._clear_prod_list()
        if not city.current_production and not city.production_queue:
            tk.Label(self.prod_list, text="No active production",
                   bg=PANEL_BG, fg=SUBTLE, font=("Segoe UI", 9),
                   anchor=tk.W).pack(fill=tk.X, pady=4)
            return

        if city.current_production:
            f = tk.Frame(self.prod_list, bg=PANEL_BG2)
            f.pack(fill=tk.X, pady=1)
            tk.Label(f, text=f"\u25b6 {city.current_production}", bg=PANEL_BG2, fg=HIGHLIGHT,
                   font=("Segoe UI", 9, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=4)
            tk.Label(f, text=f"[{city.production}/{city.production_capacity}]", bg=PANEL_BG2, fg=SUBTLE,
                   font=("Segoe UI", 8), anchor=tk.E).pack(side=tk.RIGHT, padx=4)

        for i, item in enumerate(city.production_queue):
            f = tk.Frame(self.prod_list, bg=PANEL_BG)
            f.pack(fill=tk.X, pady=1)
            tk.Label(f, text=f"{i+1}. {item}", bg=PANEL_BG, fg=TEXT,
                   font=("Segoe UI", 9), anchor=tk.W).pack(side=tk.LEFT, padx=4)
            tk.Label(f, text=f"[{city.production_capacity} prod]", bg=PANEL_BG, fg=SUBTLE,
                   font=("Segoe UI", 8), anchor=tk.E).pack(side=tk.RIGHT, padx=4)


# ── Action-log panel (bottom-right) ──────────────────────────
class ActionLogPanel(tk.Frame):
    """Scrollable event log with color-coded events."""

    EVENT_COLORS = {
        "combat": "#8b3a3a",
        "diplomacy": "#4caf50",
        "tech": "#2196f3",
        "economy": "#ff9800",
        "warning": "#f44336",
        "victory": "#ffd700",
        "default": "#aab",
    }

    def __init__(self, parent) -> None:
        super().__init__(parent, bg=PANEL_BG2)
        self.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        tk.Label(self, text="Event Log", font=("Segoe UI", 11, "bold"),
                 bg=PANEL_BG2, fg=GOLD, anchor=tk.W).pack(fill=tk.X, padx=4, pady=(4, 0))

        self.log_text = tk.Text(self, bg=PANEL_BG2, fg=TEXT, font=("Consolas", 9),
                                padx=6, pady=2, relief=tk.FLAT, wrap=tk.NONE,
                                highlightthickness=0, highlightbackground=BORDER, state=tk.DISABLED)
        sb = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(2, 0))
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=(2, 0))

    def add(self, msg: str, event_type: str = "default") -> None:
        color = self.EVENT_COLORS.get(event_type, self.EVENT_COLORS["default"])
        self.log_text.tag_config(event_type, foreground=color)
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"  {msg}\n", event_type)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)


# ── Main GUI controller ──────────────────────────────────────────────
class CivKingsGUI:
    """Top-level controller wiring the Tkinter UI to the game engine."""

    def __init__(self, root: tk.Tk, game: Game) -> None:
        self.root = root
        self.game: Game = game
        self.selected_city: Optional[City] = None
        self.selected_unit: Optional[Unit] = None
        self.hex_map: WorldMap = game.map  # WorldMap
        self.hex_items: Dict[Tuple[int, int], tk.CanvasItem] = {}  # (q,r) -> canvas item
        self.HEX_SIZE = 28  # hex radius / cell size
        self._build_ui()
        self._init_minimap()
        
        # Initialize sound and visual effects
        self.sound_manager = get_sound_manager()
        self.sound_on = tk.BooleanVar(value=True)
        self.visual_effects = VisualEffects(self.map_canvas.canvas) if hasattr(self.map_canvas, 'canvas') else None
        self._last_effect_time = 0.0
        
        # Keyboard shortcuts
        self.root.bind('<Key>', self._on_key_press)
        self._bind_map_shortcuts()
    
    def _bind_map_shortcuts(self) -> None:
        """Bind keyboard shortcuts for map interaction."""
        self.root.bind('<Control-s>', lambda e: self.save_game())
        self.root.bind('<Control-t>', lambda e: self.show_tech_tree())
        self.root.bind('<Control-d>', lambda e: self.show_diplomacy())
        self.root.bind('<Control-u>', lambda e: self.show_units())
        self.root.bind('<Control-c>', lambda e: self.show_cities())
        self.root.bind('<n>', lambda e: self.next_turn())
        self.root.bind('<Escape>', lambda e: self._clear_selection())
    
    def _on_key_press(self, event: tk.Event) -> None:
        """Handle keyboard shortcuts."""
        shortcuts = {
            'n': self.next_turn,
            't': self.show_tech_tree,
            'd': self.show_diplomacy,
            'u': self.show_units,
            'c': self.show_cities,
            'y': self.show_dynasty,
            'v': self.show_victory_screen,
            'e': self.show_events,
            's': self.save_game,
            'Escape': self._cancel_selection,
        }
        if event.char in shortcuts:
            shortcuts[event.char]()
        if event.keysym == 'F5':
            self.render_map()
            self._update_top_bar()
    
    def _schedule_effect(self, effect_name: str) -> None:
        """Schedule a visual/sound effect to be played."""
        self._last_effect_time = time.time()
        if self.visual_effects:
            self.visual_effects.trigger_effect(effect_name)
        self.sound_manager.play(effect_name)

    # ── UI construction ────────────────────────────────────────────
    def _build_ui(self) -> None:
        self.root.title("DYNASTY & DOMINION")
        self.root.configure(bg=BG)
        self.root.geometry("1200x750")

        self._top_bar()
        self._main_area()
        self._bottom_bar()
        self._center_buttons()
        
        # Speed control
        self.speed_multiplier = 1
        self.speed_var = tk.StringVar(value="1x")
        
        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0, bg=PANEL_BG2, fg=TEXT, font=("Segoe UI", 9), borderwidth=1)
        self.context_menu.add_command(label="Select Unit", command=self._context_select_unit)
        self.context_menu.add_command(label="Select City", command=self._context_select_city)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Production", command=self._context_production)
        self.context_menu.add_command(label="Move Here", command=self._context_move)
        self.context_menu.add_command(label="Attack", command=self._context_attack)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Zoom In", command=self._zoom_in)
        self.context_menu.add_command(label="Zoom Out", command=self._zoom_out)
        self.context_menu.add_command(label="Reset Map", command=self._reset_zoom)
        
        # Bind right-click
        self.root.bind("<Button-3>", self._show_context_menu)
        
        # Track context menu target
        self.context_target_tile = None

        # select capital city
        for city in self.game.cities.values():
            if city.name == "Capital":
                self.selected_city = city
                break
        if not self.selected_city and self.game.cities:
            self.selected_city = next(iter(self.game.cities.values()))

    def _init_minimap(self) -> None:
        """Initialize the minimap canvas in the bottom-right of the map area."""
        if not hasattr(self, 'map_canvas') or not self.map_canvas:
            return
        
        # Create minimap frame
        self.minimap_frame = tk.Frame(self.map_canvas, bg=PANEL_BG2,
                                       width=150, height=150, bd=0, relief=tk.FLAT)
        self.minimap_frame.place(relx=1.0, rely=0, anchor='ne', x=-5)
        self.minimap_frame.config(highlightbackground=BORDER, highlightthickness=1)
        
        # Create minimap canvas
        self.minimap_canvas = tk.Canvas(self.minimap_frame, bg="#0a0b0d",
                                         width=148, height=148,
                                         highlightthickness=0, highlightbackground=BORDER)
        self.minimap_canvas.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Create minimap renderer
        self.minimap_renderer = MinimapRenderer(
            self.minimap_canvas,
            self.hex_map.width,
            self.hex_map.height
        )
    
    def _update_minimap(self) -> None:
        """Update the minimap with current map state."""
        if not hasattr(self, 'minimap_renderer') or not self.minimap_renderer:
            return
        
        tiles = self.hex_map.tiles if self.hex_map else {}
        
        # Get camera view from map canvas
        cam_q, cam_r = 0, 0
        cam_w, cam_h = self.hex_map.width, self.hex_map.height
        if hasattr(self, 'map_canvas') and self.map_canvas:
            if hasattr(self.map_canvas, 'zoom_pan'):
                cam_w = max(1, int(self.hex_map.width / self.map_canvas.zoom_pan.zoom))
                cam_h = max(1, int(self.hex_map.height / self.map_canvas.zoom_pan.zoom))
                if hasattr(self.map_canvas.zoom_pan, 'offset'):
                    cam_q = int(self.map_canvas.zoom_pan.offset[0])
                    cam_r = int(self.map_canvas.zoom_pan.offset[1])
        
        self.minimap_renderer.render_minimap(tiles, (cam_q, cam_r, cam_w, cam_h))
    
    def _top_bar(self) -> None:
        bar = tk.Frame(self.root, bg=PANEL_BG2, height=48)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)
        bar.config(highlightbackground=BORDER, highlightthickness=1)
        self.top_bar_frame = bar  # Store reference for updates

        tk.Label(bar, text="DYNASTY & DOMINION", bg=PANEL_BG2, fg=GOLD,
                 font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=12, pady=6)

        items = [
            ("🌾 Food", self.game.city_manager.get_total_yields(self.game.player_civ.name).get("food", 0)),
            ("⚙ Production", self.game.city_manager.get_total_yields(self.game.player_civ.name).get("production", 0)),
            ("💰 Gold", self.game.gold.get(self.game.player_civ.name, 0)),
            ("🔬 Science", self.game.city_manager.get_total_yields(self.game.player_civ.name).get("science", 0)),
            ("😊 Happiness", self.game.city_manager.get_total_yields(self.game.player_civ.name).get("happiness", 0)),
            ("📅 Turn", self.game.state.turn),
        ]
        for label, value in items:
            f = tk.Frame(bar, bg=PANEL_BG2)
            f.pack(side=tk.LEFT, padx=12, pady=6)
            tk.Label(f, text=f"{label}: {value}", bg=PANEL_BG2, fg=TEXT,
                     font=("Segoe UI", 10, "bold")).pack()
        
        # Sound toggle button
        self.sound_on = tk.BooleanVar(value=True)
        self.sound_btn = tk.Checkbutton(bar, text="🔊", variable=self.sound_on,
                                   command=self._toggle_sound, bg=PANEL_BG2,
                                   fg=TEXT, selectcolor=PANEL_BG2)
        self.sound_btn.pack(side=tk.RIGHT, padx=8)
        
        # Game speed buttons
        self.speed_frame = tk.Frame(bar, bg=PANEL_BG2)
        self.speed_frame.pack(side=tk.RIGHT, padx=8)
        self.speed_var = tk.StringVar(value="1x")
        for label, val in [("1x", "1"), ("2x", "2"), ("5x", "5")]:
            tk.Radiobutton(self.speed_frame, text=label, variable=self.speed_var,
                         value=val, bg=PANEL_BG2, fg=TEXT,
                         selectcolor=PANEL_BG2, command=lambda s=val: self._set_speed(s)).pack(side=tk.LEFT, padx=2)
        
        # Track previous yields for trend arrows
        self._prev_yields: Optional[Dict[str, int]] = None
    
    def _update_top_bar(self) -> None:
        """Update the top bar with current values and trend arrows."""
        yields = self.game.city_manager.get_total_yields(self.game.player_civ.name)
        gold = self.game.gold.get(self.game.player_civ.name, 0)
        turn = self.game.state.turn
        
        items = [
            ("🌾 Food", yields.get("food", 0), "food"),
            ("⚙ Production", yields.get("production", 0), "production"),
            ("💰 Gold", gold, "gold"),
            ("🔬 Science", yields.get("science", 0), "science"),
            ("😊 Happiness", yields.get("happiness", 0), "happiness"),
            ("📅 Turn", turn, "turn"),
        ]
        
        # Clear and rebuild resource labels
        for widget in self.top_bar_frame.winfo_children():
            if isinstance(widget, tk.Frame) and widget not in (self.sound_btn.master, self.speed_frame):
                widget.destroy()
        
        for label, value, key in items:
            f = tk.Frame(self.top_bar_frame, bg=ACCENT)
            f.pack(side=tk.LEFT, padx=12, pady=6)
            
            # Determine color based on surplus/deficit
            fg_color = TEXT
            if key in ("food", "production", "gold", "science", "happiness"):
                if value > 0:
                    fg_color = "#4caf50"  # green for surplus
                elif value < 0:
                    fg_color = "#f44336"  # red for deficit
            
            # Calculate trend arrow
            arrow = ""
            if self._prev_yields and key in self._prev_yields and key != "turn":
                prev = self._prev_yields[key]
                diff = value - prev
                if diff > 0:
                    arrow = "↑"
                elif diff < 0:
                    arrow = "↓"
                else:
                    arrow = "→"
            
            self._prev_yields = {k: v for k, v in yields.items() if k != "happiness"}
            self._prev_yields["gold"] = gold
            
            display_text = f"{label}: {value}{arrow}"
            tk.Label(f, text=display_text, bg=ACCENT, fg=fg_color,
                     font=("Segoe UI", 10, "bold")).pack()
    
    def _toggle_sound(self) -> None:
        """Toggle sound on/off."""
        self.sound_on.set(not self.sound_on.get())
        self.sound_manager.muted = not self.sound_on.get()
        self.sound_btn.config(text="🔊" if self.sound_on.get() else "🔇")
    
    def _set_speed(self, speed: str) -> None:
        """Set game speed multiplier."""
        self.speed_multiplier = int(speed)
        self.speed_var.set(f"{self.speed_multiplier}x")

    def _main_area(self) -> None:
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=4, pady=(4, 0))

        # map canvas
        self.map_frame = tk.Frame(frame, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        self.map_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        self.map_canvas = MapCanvas(self.map_frame, game_state=self.game)
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
        self.game.on_tile_selected = self._on_map_click
        self.game.on_city_double_click = self._on_city_double_click

        # right panel
        self.right_panel = CityDetailPanel(frame)
        self.right_panel.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

        # log panel
        self.log_panel = ActionLogPanel(frame)
        self.log_panel.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT, pady=(4, 0))
        self.log_panel.add(f"Welcome to CivKings! You play as {self.game.player_civ.name}.")

    def _bottom_bar(self) -> None:
        bar = tk.Frame(self.root, bg=PANEL_BG2, height=36)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Label(bar, text="Click a unit to select | Click a city to view | R-click for production",
                 bg=PANEL_BG2, fg=SUBTLE, font=("Segoe UI", 9)).pack()

    def _center_buttons(self) -> None:
        f = tk.Frame(self.root, bg=BG)
        f.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        btns = [
            ("Next Turn", self.next_turn),
            ("Tech Tree", self.show_tech_tree),
            ("Show Units", self.show_units),
            ("Show Cities", self.show_cities),
            ("Diplomacy", self.show_diplomacy),
            ("Dynasty", self.show_dynasty),
            ("Factions", self.show_factions),
            ("Happiness", self.show_happiness),
            ("Stability", self.show_stability),
            ("Victory", self.show_victory_screen),
            ("Events", self.show_events),
            ("Save Game", self.save_game),
            ("Quit", self.quit),
        ]
        for name, cb in btns:
            btn_bg = RED if name == "Next Turn" else GOLD
            btn_fg = "#fff" if name == "Next Turn" else "#000"
            btn_active = "#d44" if name == "Next Turn" else "#d4af6a"
            tk.Button(f, text=name, bg=btn_bg, fg=btn_fg, font=("Segoe UI", 10, "bold") if name == "Next Turn" else ("Segoe UI", 10),
                  activebackground=btn_active, activeforeground=btn_fg,
                  command=cb, width=12, relief=tk.FLAT, highlightthickness=0).pack(side=tk.LEFT, padx=4, pady=(0, 10))

    # ── map rendering ───────────────────────────────────────────

    def render_map(self) -> None:
        """Render the map using MapCanvas."""
        self.map_canvas.render(
            self.game.map.tiles,
            zoom=self.map_canvas.zoom_pan.zoom_level
        )
        self._update_minimap()

    def _on_map_click(self, tile_coord) -> None:
        """Callback from MapCanvas when a tile is clicked."""
        tile = self.game.map.get_tile(tile_coord[0], tile_coord[1])
        if not tile:
            return
        if tile.city:
            city = next((c for c in self.game.cities if c.position == tile.city), None)
            if city:
                self.selected_city = city
                self.right_panel.update(city)
        if tile.unit:
            unit = next((u for u in self.game.units if u.position == tile.unit), None)
            if unit:
                self.selected_unit = unit
                UnitInfoPopup(self.root, unit)

    def _on_city_double_click(self, city) -> None:
        """Callback from MapCanvas when a city tile is double-clicked."""
        self.selected_city = city
        self.right_panel.update(city)
        ProductionPopup(self.root, city, self.game)

    def _on_map_drag(self, event) -> None:
        pass

    def _on_map_wheel(self, event) -> None:
        pass

    # ── actions ──────────────────────────────────────────
    def next_turn(self) -> None:
        if not self.game.state.game_over:
            if not messagebox.askyesno("Next Turn", "Advance to next turn?"):
                return
        msgs = self.game.process_turn()
        self.render_map()
        self._update_top_bar()
        if self.selected_city:
            self.right_panel.update(self.selected_city)
        for msg in msgs:
            self.log_panel.add(msg)
            # Trigger effects for important events
            if "combat" in msg.lower() or "battle" in msg.lower():
                self._schedule_effect("combat")
            elif "tech" in msg.lower() or "research" in msg.lower():
                self._schedule_effect("tech_researched")
            elif "produced" in msg.lower() or "built" in msg.lower():
                self._schedule_effect("build_complete")
        # Check for victory after every turn
        self._check_victory()
        # Schedule next animation update
        self.root.after(16, self._animation_loop)  # ~60 FPS

    def show_tech_tree(self) -> None:
        TechTreePopup(self.root, self.game.tech_manager)

    def show_units(self) -> None:
        lines = [f"=== {u.unit_type} ===\n  Owner: {u.owner}  HP: {u.hp:.0f}/{u.max_hp}  "
                 f"Pos: {u.position}\n\n" for u in self.game.units]
        messagebox.showinfo("Your Units", "".join(lines))

    def show_cities(self) -> None:
        lines = [f"=== {c.name} ===\n  Pop: {c.population}  Food: {c.food}  Prod: {c.production}  Gold: {c.gold}\n\n"
                 for c in self.game.cities]
        messagebox.showinfo("Your Cities", "".join(lines))

    def show_diplomacy(self) -> None:
        DiplomacyPopup(self.root, self.game)

    def show_dynasty(self) -> None:
        DynastyPopup(self.root, self.game)

    def show_factions(self) -> None:
        FactionsPanel(self.root, self.game)

    def show_happiness(self) -> None:
        HappinessPanel(self.root, self.game)

    def show_stability(self) -> None:
        StabilityPanel(self.root, self.game)

    def show_victory_screen(self) -> None:
        VictoryPanel(self.root, self.game)

    def show_events(self) -> None:
        evts = self.game.event_manager.events[-20:]
        lines = [f"  {e}\n" for e in evts]
        messagebox.showinfo("Events", "".join(lines))

    def save_game(self) -> None:
        result = self.game.save_game("savegame.json")
        messagebox.showinfo("Saved", result)

    def quit(self) -> None:
        if self.game.state.game_over:
            self.root.destroy()
            return
        if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
            self.root.destroy()

    def _check_victory(self) -> None:
        """Check and display victory/defeat screen."""
        if self.game.state.game_over and self.game.state.victory:
            self._schedule_effect("victory")
            self.root.destroy()
            winner = self.game.state.victory
            msg = f"🏆 VICTORY! 🏆\n\n{winner}\n\nTurn: {self.game.state.turn}"
            messagebox.showinfo("Game Over", msg)

    def _show_end_game_screen(self) -> None:
        """Show end-of-game summary."""
        if not self.game.state.game_over:
            return
        winner = self.game.state.victory or "No winner"
        lines = [
            "=" * 50,
            "  GAME OVER",
            "=" * 50,
            f"  Winner: {winner}",
            f"  Turns: {self.game.state.turn}",
            f"  Cities: {len(self.game.cities)}",
            f"  Units: {len(self.game.units)}",
            "=" * 50,
        ]
        messagebox.showinfo("Game Over", "\n".join(lines))
    
    def _animation_loop(self) -> None:
        """Update and render visual effects."""
        if self.visual_effects:
            self.visual_effects.update()
            self.visual_effects.render()
        # Continue loop if there are active particles
        if hasattr(self.visual_effects, 'particles') and self.visual_effects.particles:
            self.root.after(16, self._animation_loop)

    def _cancel_selection(self) -> None:
        """Clear the current selection."""
        self.selected_city = None
        self.selected_unit = None
        if hasattr(self, 'right_panel'):
            self.right_panel.update(self.game.cities[0] if self.game.cities else City("Empty", (0, 0)))

    def _clear_selection(self) -> None:
        """Alias for _cancel_selection."""
        self._cancel_selection()

    def _zoom_in(self) -> None:
        """Zoom in the map."""
        if hasattr(self, 'map_canvas') and hasattr(self.map_canvas, 'zoom_pan'):
            self.map_canvas.zoom_pan.zoom_in()
            self.render_map()

    def _zoom_out(self) -> None:
        """Zoom out the map."""
        if hasattr(self, 'map_canvas') and hasattr(self.map_canvas, 'zoom_pan'):
            self.map_canvas.zoom_pan.zoom_out()
            self.render_map()

    def _reset_zoom(self) -> None:
        """Reset map zoom."""
        if hasattr(self, 'map_canvas') and hasattr(self.map_canvas, 'zoom_pan'):
            self.map_canvas.zoom_pan.reset_zoom()
            self.render_map()

    def _show_context_menu(self, event: tk.Event) -> None:
        """Show context menu on right-click."""
        self.context_menu.post(event.x_root, event.y_root)

    def _context_select_unit(self) -> None:
        """Select the unit at the context menu target."""
        pass  # Implementation depends on context target

    def _context_select_city(self) -> None:
        """Select the city at the context menu target."""
        pass  # Implementation depends on context target

    def _context_production(self) -> None:
        """Open production menu for the selected city."""
        if self.selected_city:
            ProductionPopup(self.root, self.selected_city, self.game)

    def _context_move(self) -> None:
        """Move selected unit to context target."""
        pass  # Implementation depends on context target

    def _context_attack(self) -> None:
        """Attack at context target."""
        pass  # Implementation depends on context target


# ── Application entry point ─────────────────────────────────────
def main() -> None:
    root = tk.Tk()
    root.title("CivKings")
    root.configure(bg=BG)
    root.geometry("1200x750")
    root.resizable(True, True)

    dlg = NewGameDialog(root)
    root.wait_window(dlg.win)

    if dlg.result is None:
        root.destroy()
        return

    civ, difficulty = dlg.result
    game = Game(civ)

    gui = CivKingsGUI(root, game)
    gui.render_map()

    root.mainloop()


if __name__ == "__main__":
    main()