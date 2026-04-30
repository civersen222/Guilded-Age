"""
CivKings - Additional GUI Popups
Diplomacy, Dynasty, Victory panels, Production queue, Unit info.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Tuple

from game import Game
from game_data import TECHNOLOGIES, Technology, TechBranch
from victory import VictoryType, VictoryConditionTracker
from simulation import Character, Dynasty
from city import City
from military import Unit


# ── Colours ──
BG = "#1a1a2e"
PANEL_BG = "#16213e"
PANEL_BG2 = "#1c2a44"
ACCENT = "#0f3460"
HIGHLIGHT = "#e94560"
TEXT = "#eee"
SUBTLE = "#aab"


# ── Production Queue Popup ──
class ProductionPopup(tk.Toplevel):
    """Popup for selecting what a city produces next."""

    def __init__(self, parent, city: City, game: Game) -> None:
        super().__init__(parent)
        self.title(f"Produce in {city.name}")
        self.geometry("420x480")
        self.configure(bg=BG)
        self.city = city
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text=f"Produce in {self.city.name}", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))
        tk.Label(self, text=f"Production: {self.city.production}/{self.city.max_production}",
                 bg=BG, fg=TEXT).pack()
        tk.Label(self, text=f"Queue: {self.city.production_queue}",
                 bg=BG, fg=SUBTLE).pack(pady=(0, 8))

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
                                  font=("Segoe UI", 10), selectbackground=HIGHLIGHT,
                                  activestyle="none", highlightthickness=0)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.listbox.yview)

        # Populate production options
        from city import BuildingType, DistrictType
        options: List[Tuple[str, str, int]] = []
        for btype in BuildingType:
            info = btype.value
            cost = getattr(btype, 'cost', 50)
            options.append((f"🏛 {info}", f"cost: {cost}", btype))
        for dtype in DistrictType:
            info = dtype.value
            cost = getattr(dtype, 'cost', 100)
            options.append((f"🏘 {info}", f"cost: {cost}", dtype))
        # Units
        for utype_name, utype in UNIT_TYPES.items():
            cost = getattr(utype, 'production_cost', 40)
            options.append((f"⚔ {utype_name}", f"cost: {cost}", utype_name))

        for label, sub, data in options:
            self.listbox.insert(tk.END, f"{label}  ({sub})")
            self.listbox.itemconfig(self.listbox.size() - 1, bg=PANEL_BG2)

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=(8, 12))
        tk.Button(btn_frame, text="Produce Selected", command=self._produce,
                  bg=HIGHLIGHT, fg="white", font=("Segoe UI", 10, "bold"),
                  width=16).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_frame, text="Cancel", command=self.destroy,
                  bg=ACCENT, fg=TEXT, font=("Segoe UI", 10),
                  width=16).pack(side=tk.LEFT, padx=8)

    def _produce(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Pick something to produce.")
            return
        item = self.listbox.get(sel[0])
        self.city.production_queue.append(item)
        self.log_panel.add(f"Producing: {item}")
        self.destroy()


# ── Unit Info Popup ──
class UnitInfoPopup(tk.Toplevel):
    """Shows detailed info about a selected unit."""

    def __init__(self, parent, unit: Unit) -> None:
        super().__init__(parent)
        self.title(f"{unit.unit_type} Details")
        self.geometry("320x280")
        self.configure(bg=BG)
        self.unit = unit
        self._build()

    def _build(self) -> None:
        tk.Label(self, text=f"{self.unit.unit_type}", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(8, 4))
        info = (
            f"Owner:      {self.unit.owner}\n"
            f"HP:         {self.unit.hp:.0f}/{self.unit.max_hp}\n"
            f"Position:   {self.unit.position}\n"
            f"Moves Left: {self.unit.moves_left}\n"
            f"ATK:        {self.unit.attack}\n"
            f"DEF:        {self.unit.defense}\n"
            f"Range:      {self.unit.range}\n"
            f"Strength:   {self.unit.strength}\n"
            f"XP:         {self.unit.experience}"
        )
        tk.Label(self, text=info, bg=BG, fg=TEXT, font=("Consolas", 10),
                 anchor=tk.W, justify=tk.LEFT).pack(padx=12, pady=8, fill=tk.X)
        tk.Button(self, text="Close", command=self.destroy,
                  bg=ACCENT, fg=TEXT, font=("Segoe UI", 10)).pack(pady=(0, 8))


# ── Diplomacy Popup ──
class DiplomacyPopup(tk.Toplevel):
    """Shows diplomatic relations between all civs."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Diplomacy")
        self.geometry("500x400")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Diplomatic Relations", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(8, 4))

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.text = tk.Text(frame, bg=PANEL_BG, fg=TEXT, font=("Consolas", 10),
                            padx=8, pady=4, relief=tk.FLAT, wrap=tk.WORD,
                            highlightthickness=0)
        self.text.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)

        # Gather relations
        rels = self.game.diplomacy_manager.get_all_relations()
        all_civs = list(self.game.civilizations.keys())
        lines = []
        for civ1 in all_civs:
            for civ2 in all_civs:
                if civ1 >= civ2:
                    continue
                status = rels.get((civ1, civ2), rels.get((civ2, civ1), "Neutral"))
                lines.append(f"  {civ1} ↔ {civ2}: {status}")
        self.text.insert(tk.END, "\n".join(lines) if lines else "  No diplomacy data yet.")


# ── Dynasty Popup ──
class DynastyPopup(tk.Toplevel):
    """Shows dynasty members and prestige."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Dynasty")
        self.geometry("480x500")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Royal Dynasty", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(8, 4))

        prestige = 0
        if self.game.dynasty:
            try:
                prestige = self.game.dynasty.calculate_dynastic_prestige()
            except Exception:
                pass
        tk.Label(self, text=f"Prestige: {prestige}", bg=BG, fg=TEXT,
                 font=("Segoe UI", 11)).pack()

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.text = tk.Text(frame, bg=PANEL_BG, fg=TEXT, font=("Consolas", 10),
                            padx=8, pady=4, relief=tk.FLAT, wrap=tk.WORD,
                            highlightthickness=0)
        self.text.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)

        lines = []
        if self.game.dynasty:
            for member_id, char in self.game.dynasty.members.items():
                alive = getattr(char, 'is_alive', True)
                status = "Alive" if alive else "Deceased"
                lines.append(f"  {char.name} ({status}) — Dipl: {char.stats.get('diplomacy', 0)}  Mart: {char.stats.get('martial', 0)}  Stew: {char.stats.get('stewardship', 0)}  Intr: {char.stats.get('intrigue', 0)}")
        else:
            lines.append("  No dynasty yet.")
        self.text.insert(tk.END, "\n".join(lines))


# ── Victory Panel ──
class VictoryPanel(tk.Toplevel):
    """Shows victory progress and current status."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Victory Conditions")
        self.geometry("400x500")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Victory Conditions", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(8, 4))

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.text = tk.Text(frame, bg=PANEL_BG, fg=TEXT, font=("Consolas", 10),
                            padx=8, pady=4, relief=tk.FLAT, wrap=tk.WORD,
                            highlightthickness=0)
        self.text.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)

        tracker = self.game.victory_tracker
        lines = []
        for vtype in VictoryType:
            pct = tracker.get_percentage(vtype)
            lines.append(f"  {vtype.value}: {pct:.1f}%")
        self.text.insert(tk.END, "\n".join(lines))


# ── Tech Tree Popup (from gui.py, re-imported) ──
class TechTreePopup(tk.Toplevel):
    """Shows researched vs available technologies."""

    def __init__(self, parent, tech_manager, civ_name: str = "Player") -> None:
        super().__init__(parent)
        self.tm = tech_manager
        self.civ_name = civ_name
        self.title("Technology Tree")
        self.geometry("520x480")
        self.resizable(True, True)
        self.configure(bg=BG)
        self._build()

    def _build(self) -> None:
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
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 60)), "units"))
        self._redraw()

    def _redraw(self, *_):
        for w in getattr(self.scroll_frame, 'wframes', []):
            w.destroy()
        self.scroll_frame.wframes = []

        # Update tech manager with current game data
        self.tm = self.game.tech_manager if hasattr(self, 'game') else self.tm
        filter_txt = self.var.get().lower()
        researched = set(self.tm.researched.keys()) if hasattr(self.tm, 'researched') else set()

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
                prereq_str = ", ".join(tech.prerequisites) if tech.prerequisites else "None"
                clr = "#4caf50" if is_done else "#ffeb3b"
                icon = "✓" if is_done else "🔒"
                row = tk.Frame(self.scroll_frame, bg=BG)
                row.pack(fill=tk.X, padx=4, pady=1)
                tk.Label(row, text=f"{icon}  {tname}", bg=BG, fg=clr, font=("Segoe UI", 10),
                         padx=6, pady=1, anchor=tk.W).pack(side=tk.LEFT)
                tk.Label(row, text=f"[{prereq_str}]  cost:{tech.cost}", bg=BG, fg=SUBTLE,
                         font=("Segoe UI", 8), padx=6, anchor=tk.W).pack(side=tk.LEFT)
                self.scroll_frame.wframes.append(row)
