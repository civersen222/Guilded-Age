"""
CivKings - Tkinter GUI
Full graphical user interface for CivKings.
Wires into existing game.py, city.py, tech.py, military.py without modifying them.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Tuple
import math

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


# ── Colour palette ────────────────────────────────────────────────
BG = "#1a1a2e"
PANEL_BG = "#16213e"
PANEL_BG2 = "#1c2a44"
ACCENT = "#0f3460"
HIGHLIGHT = "#e94560"
TEXT = "#eee"
SUBTLE = "#aab"
TERRAIN_COL: Dict[TerrainType, str] = {
    TerrainType.PLAINS:       "#4a7c3f",
    TerrainType.GRASSLAND:    "#5a9c4f",
    TerrainType.FOREST:       "#2d5a27",
    TerrainType.HILLS:        "#8b7d3c",
    TerrainType.MOUNTAIN:     "#6b6b6b",
    TerrainType.DESERT:       "#d4b84a",
    TerrainType.TUNDRA:       "#c8d8d8",
    TerrainType.WATER_COAST:  "#2e6fb5",
    TerrainType.OCEAN:        "#1a4f8a",
}


# ── New Game dialog ───────────────────────────────────────────────
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

        tk.Label(self.win, text="CivKings — Dynasty & Conquest", font=("Segoe UI", 20, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(20, 10))

        # difficulty
        diff_frame = tk.Frame(self.win, bg=BG)
        diff_frame.pack(pady=(0, 10))
        tk.Label(diff_frame, text="Difficulty:", bg=BG, fg=TEXT, font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(10, 8))
        self.diff_var = tk.StringVar(value="medium")
        for label, val in [("Easy", "easy"), ("Medium", "medium"), ("Hard", "hard")]:
            tk.Radiobutton(diff_frame, label, variable=self.diff_var, value=val,
                           bg=BG, fg=TEXT, selectcolor=BG).pack(side=tk.LEFT, padx=(2, 2))

        # civ listbox
        tk.Label(self.win, text="Choose your civilization:", bg=BG, fg=TEXT, font=("Segoe UI", 11)).pack(pady=(0, 4))

        list_frame = tk.Frame(self.win, bg=BG, bd=1, relief=tk.SOLID)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 16))

        sb = tk.Scrollbar(list_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.civ_list = tk.Listbox(list_frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
                                    selectbackground=HIGHLIGHT, font=("Segoe UI", 10),
                                    activestyle="none", highlightthickness=0)
        for name in sorted(CIVILIZATIONS.keys()):
            civ = CIVILIZATIONS[name]
            self.civ_list.insert(tk.END, f"{civ.name:<14}  {civ.bonus[:50]}")
        self.civ_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.civ_list.bind("<<ListboxSelect>>", self._on_select)
        sb.config(command=self.civ_list.yview)

        # info label (shows civ details on selection)
        self.info_label = tk.Label(self.win, text="Select a civilization", bg=BG, fg=SUBTLE,
                                    font=("Segoe UI", 9), wraplength=640, justify=tk.LEFT)
        self.info_label.pack(pady=(0, 12))

        # buttons
        btn_frame = tk.Frame(self.win, bg=BG)
        btn_frame.pack(pady=(0, 20))
        tk.Button(btn_frame, text="Start Game", command=self._confirm, width=14,
                  bg=HIGHLIGHT, fg="white", font=("Segoe UI", 11, "bold"),
                  active_background=HIGHLIGHT, active_foreground="white").pack(side=tk.LEFT, padx=(10, 5))
        tk.Button(btn_frame, text="Cancel", command=self.win.destroy, width=14,
                  bg=ACCENT, fg=TEXT, font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(5, 10))

        self.win.focus_set()

    def _on_select(self, _event=None) -> None:
        sel = self.civ_list.curselection()
        if not sel:
            return
        idx = sel[0]
        names = sorted(CIVILIZATIONS.keys())
        name = names[idx]
        civ = CIVILIZATIONS[name]
        self.info_label.config(text=(
            f"{civ.name}  —  Unique unit: {civ.unique_unit or 'None'}  |  "
            f"Unique building: {civ.unique_building or 'None'}  |  "
            f"Gov: {civ.preferred_gov}  |  "
            f"Start techs: {', '.join(civ.starting_tech)}"
        ), fg=TEXT)

    def _confirm(self) -> None:
        sel = self.civ_list.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Pick a civilization first.")
            return
        names = sorted(CIVILIZATIONS.keys())
        civ = CIVILIZATIONS[names[sel[0]]]
        self.result = (civ, self.diff_var.get())
        self.win.destroy()


# ── Tech-tree popup ───────────────────────────────────────────────
class TechTreePopup(tk.Toplevel):
    """Shows researched vs available technologies."""

    def __init__(self, parent, tech_manager: TechManager) -> None:
        super().__init__(parent)
        self.tm = tech_manager
        self.title("Technology Tree")
        self.geometry("520x480")
        self.resizable(True, True)
        self.configure(bg=BG)
        self._build()

    def _build(self) -> None:
        # search / filter
        top = tk.Frame(self, bg=BG)
        top.pack(fill=tk.X, padx=8, pady=(6, 0))
        tk.Label(top, text="Filter:", bg=BG, fg=SUBTLE).pack(side=tk.LEFT)
        self.var = tk.StringVar()
        self.var.trace_add("write", self._redraw)
        ttk.Entry(top, textvariable=self.var, width=20).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Checkbutton(top, text="Show researched", variable=tk.BooleanVar(value=True),
                        command=self._redraw).pack(side=tk.LEFT, padx=(10, 0))

        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=BG)
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # bind mousewheel
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 60)), "units"))

        self._redraw()

    def _redraw(self, *_):
        for w in self.scroll_frame.wframes:
            w.destroy()
        self.scroll_frame.wframes = []

        filter_txt = self.var.get().lower()
        researched = set(self.tm.researched.keys())

        for branch in [TechBranch.SCIENTIFIC, TechBranch.MILITARY, TechBranch.CIVIC]:
            header = tk.Frame(self.scroll_frame, bg=ACCENT)
            header.pack(fill=tk.X, pady=(8, 0))
            tk.Label(header, text=branch.value, bg=ACCENT, fg=TEXT, font=("Segoe UI", 11, "bold"),
                     padx=8, pady=2).pack(side=tk.LEFT)

            for tname, tech in sorted(TECHNOLOGIES.items()):
                if tech.branch != branch:
                    continue
                if filter_txt and filter_txt not in tname.lower():
                    continue
                is_done = tname in researched
                is_avail = not is_done and all(p in researched for p in tech.prerequisites)

                row = tk.Frame(self.scroll_frame, bg=BG)
                row.pack(fill=tk.X, padx=4, pady=1)
                icon = "✓" if is_done else ("▶" if is_avail else "🔒")
                clr = "#4caf50" if is_done else ("#ffeb3b" if is_avail else "#555")
                tk.Label(row, text=f"{icon}  {tname}", bg=BG, fg=clr, font=("Segoe UI", 10),
                         padx=6, pady=1, anchor=tk.W).pack(side=tk.LEFT)
                prereq_str = ", ".join(tech.prerequisites) if tech.prerequisites else "None"
                tk.Label(row, text=f"[{prereq_str}]  cost:{tech.cost}", bg=BG, fg=SUBTLE,
                         font=("Segoe UI", 8), padx=6, anchor=tk.W).pack(side=tk.LEFT)
                self.scroll_frame.wframes.append(row)


# ── City detail panel (right side) ────────────────────────────────
class CityDetailPanel(tk.Frame):
    """Shows info about the selected / capital city."""

    def __init__(self, parent) -> None:
        super().__init__(parent, bg=PANEL_BG)
        self.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._build()

    def _build(self) -> None:
        self.title_lbl = tk.Label(self, text="City", font=("Segoe UI", 14, "bold"),
                                   bg=PANEL_BG, fg=HIGHLIGHT, anchor=tk.W)
        self.title_lbl.pack(fill=tk.X, padx=8, pady=(8, 0))

        self.info_text = tk.Text(self, bg=PANEL_BG, fg=TEXT, font=("Consolas", 10),
                                  padx=8, pady=4, relief=tk.FLAT, wrap=tk.NONE,
                                  highlightthickness=0, state=tk.DISABLED)
        sb = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=sb.set)
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        # production queue buttons area
        self.prod_frame = tk.Frame(self, bg=PANEL_BG)
        self.prod_frame.pack(fill=tk.X, padx=8, pady=(4, 0))

    def update(self, city: City) -> None:
        self.title_lbl.config(text=city.name)
        text = (
            f"Owner:       {city.owner}\n"
            f"Position:    {city.position}\n"
            f"Population:  {city.population}\n"
            f"Gold:        {city.gold}\n"
            f"Production:  {city.production}/{city.max_production}\n"
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


# ── Action-log panel (bottom-right) ───────────────────────────────
class ActionLogPanel(tk.Frame):
    """Scrollable event log."""

    def __init__(self, parent) -> None:
        super().__init__(parent, bg=PANEL_BG2)
        self.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        tk.Label(self, text="Event Log", font=("Segoe UI", 11, "bold"),
                 bg=PANEL_BG2, fg=HIGHLIGHT, anchor=tk.W).pack(fill=tk.X, padx=4, pady=(4, 0))

        self.log_text = tk.Text(self, bg=PANEL_BG2, fg=TEXT, font=("Consolas", 9),
                                 padx=6, pady=2, relief=tk.FLAT, wrap=tk.NONE,
                                 highlightthickness=0, state=tk.DISABLED)
        sb = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(2, 0))
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=(2, 0))

    def add(self, msg: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"  {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)


# ── Main GUI controller ───────────────────────────────────────────
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

    # ── UI construction ────────────────────────────────────────
    def _build_ui(self) -> None:
        self.root.title("CivKings")
        self.root.configure(bg=BG)
        self.root.geometry("1200x750")

        self._top_bar()
        self._main_area()
        self._bottom_bar()
        self._center_buttons()

        # select capital city
        for city in self.game.cities:
            if city.name == "Capital":
                self.selected_city = city
                break
        if not self.selected_city and self.game.cities:
            self.selected_city = self.game.cities[0]

    def _top_bar(self) -> None:
        bar = tk.Frame(self.root, bg=ACCENT, height=48)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        items = [
            ("🌾 Food", self.game.city_manager.get_total_yields(self.game.player_civ.name).get("food", 0)),
            ("⚙ Production", self.game.city_manager.get_total_yields(self.game.player_civ.name).get("production", 0)),
            ("💰 Gold", self.game.gold.get(self.game.player_civ.name, 0)),
            ("🔬 Science", self.game.city_manager.get_total_yields(self.game.player_civ.name).get("science", 0)),
            ("😊 Happiness", self.game.city_manager.get_total_yields(self.game.player_civ.name).get("happiness", 0)),
            ("📅 Turn", self.game.state.turn),
        ]
        for label, value in items:
            f = tk.Frame(bar, bg=ACCENT)
            f.pack(side=tk.LEFT, padx=12, pady=6)
            tk.Label(f, text=f"{label}: {value}", bg=ACCENT, fg=TEXT,
                     font=("Segoe UI", 10, "bold")).pack()

    def _main_area(self) -> None:
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=4, pady=(4, 0))

        # map canvas
        self.map_frame = tk.Frame(frame, bg=ACCENT)
        self.map_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        self.canvas = tk.Canvas(self.map_frame, bg="#0d1b2a",
                                 width=700, height=600,
                                 highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_map_click)
        self.canvas.bind("<B1-Motion>", self._on_map_drag)
        self.canvas.bind("<MouseWheel>", self._on_map_wheel)
        self.canvas.bind("<Double-Button-1>", self._on_map_dclick)

        # right panel
        self.right_panel = CityDetailPanel(frame)
        self.right_panel.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

        # log panel
        self.log_panel = ActionLogPanel(frame)
        self.log_panel.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT, pady=(4, 0))
        self.log_panel.add(f"Welcome to CivKings! You play as {self.game.player_civ.name}.")

    def _bottom_bar(self) -> None:
        bar = tk.Frame(self.root, bg=ACCENT, height=36)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Label(bar, text="Click a unit to select | Click a city to view | R-click for production",
                 bg=ACCENT, fg=SUBTLE, font=("Segoe UI", 9)).pack()

    def _center_buttons(self) -> None:
        f = tk.Frame(self.root, bg=BG)
        f.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        btns = [
            ("Next Turn", self.next_turn),
            ("Tech Tree", self.show_tech_tree),
            ("Show Units", self.show_units),
            ("Show Cities", self.show_cities),
            ("Diplomacy", self.show_diplomacy),
            ("Events", self.show_events),
            ("Save Game", self.save_game),
            ("Quit", self.quit),
        ]
        for name, cb in btns:
            tk.Button(f, text=name, bg=ACCENT, fg=TEXT, font=("Segoe UI", 10, "bold"),
                      activebackground=HIGHLIGHT, activeforeground=TEXT,
                      command=cb, width=12).pack(side=tk.LEFT, padx=4, pady=(0, 10))

    # ── map rendering ──────────────────────────────────────────
    def _hex_points(self, cx: float, cy: float, r: float) -> List[Tuple[float, float]]:
        pts = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        return pts

    def render_map(self) -> None:
        self.canvas.delete("all")
        self.hex_items.clear()
        if not self.hex_map.tiles:
            return

        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2

        for tile in self.hex_map.tiles.values():
            hx = cx + tile.q * self.HEX_SIZE * 1.5
            hy = cy + tile.r * self.HEX_SIZE * math.sqrt(3)
            pts = self._hex_points(hx, hy, self.HEX_SIZE - 1)

            col = TERRAIN_COL.get(tile.terrain_type, "#333")
            item = self.canvas.create_polygon(pts, fill=col, outline="#111", width=1,
                                              tags=(str(tile.q), str(tile.r), "tile"))
            self.hex_items[(tile.q, tile.r)] = item

            # city marker
            if tile.city:
                txt = self.canvas.create_text(hx, hy, text="★", font=("Segoe UI", 18, "bold"),
                                              fill="gold", tags=("city", str(tile.q), str(tile.r)))
                self.hex_items[(tile.q, tile.r)] = txt

            # unit marker
            if tile.unit:
                u = next((u for u in self.game.units if u.position == tile.unit), None)
                if u:
                    color = "red" if u.owner != self.game.player_civ.name else "lime"
                    txt = self.canvas.create_text(hx, hy, text="●", font=("Segoe UI", 14, "bold"),
                                                  fill=color, tags=("unit", str(tile.q), str(tile.r)))
                    self.hex_items[(tile.q, tile.r)] = txt

        # fog of war
        if hasattr(self.hex_map, 'fog_of_war') and self.hex_map.fog_of_war:
            for tile in self.hex_map.tiles.values():
                if not self.hex_map.fog_of_war.is_visible(tile.q, tile.r):
                    item = self.hex_items.get((tile.q, tile.r))
                    if item:
                        self.canvas.itemconfig(item, fill="#111", stipple="gray12")

    def _on_map_click(self, event) -> None:
        for (q, r), item in self.hex_items.items():
            bbox = self.canvas.bbox(item)
            if bbox and bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
                tile = self.hex_map.get_tile(q, r)
                if not tile:
                    continue
                if tile.city:
                    city = next((c for c in self.game.cities if c.position == tile.city), None)
                    if city:
                        self.selected_city = city
                        self.right_panel.update(city)
                    return
                if tile.unit:
                    unit = next((u for u in self.game.units if u.position == tile.unit), None)
                    if unit:
                        self.selected_unit = unit
                        UnitInfoPopup(self.root, unit)
                    return

    def _on_map_dclick(self, event) -> None:
        for (q, r), item in self.hex_items.items():
            bbox = self.canvas.bbox(item)
            if bbox and bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
                tile = self.hex_map.get_tile(q, r)
                if not tile:
                    continue
                if tile.city:
                    city = next((c for c in self.game.cities if c.position == tile.city), None)
                    if city:
                        self.selected_city = city
                        self.right_panel.update(city)
                        ProductionPopup(self.root, city, self.game)
                    return

    def _on_map_drag(self, event) -> None:
        pass

    def _on_map_wheel(self, event) -> None:
        pass

    # ── actions ────────────────────────────────────────────────
    def next_turn(self) -> None:
        msgs = self.game.process_turn()
        self.render_map()
        if self.selected_city:
            self.right_panel.update(self.selected_city)
        for msg in msgs:
            self.log_panel.add(msg)
        # Check for victory after every turn
        self._check_victory()

    def show_tech_tree(self) -> None:
        TechTreePopup(self.root, self.game.tech_manager)

    def show_units(self) -> None:
        lines = [f"=== {u.unit_type} ===\n  Owner: {u.owner}  HP: {u.hp:.0f}/{u.max_hp}  "
                 f"Pos: {u.position}\n\n" for u in self.game.units]
        messagebox.showinfo("Your Units", "".join(lines))

    def show_cities(self) -> None:
        lines = [f"=== {c.name} ===\n  Pop: {c.population}  Food: {c.gold}  Prod: {c.production}  Gold: {c.gold}\n\n"
                 for c in self.game.cities]
        messagebox.showinfo("Your Cities", "".join(lines))

    def show_diplomacy(self) -> None:
        rel = self.game.diplomacy_manager.get_all_relations()
        lines = [f"  {civ}: {rel.get(civ, 'Neutral')}\n" for civ in self.game.diplomacy_manager.all_civs]
        messagebox.showinfo("Diplomacy", "".join(lines))

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
