"""
CivKings - Panel UI Components
City detail panel, production queue, tech tree, diplomacy, dynasty, event log, resource bar, quick actions.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Callable

from game_data import ProductionType, TechBranch
from city import City
from unit import Unit
from research_tree import Technology
from game import Game

BG = "#1a1a2e"
PANEL_BG = "#16213e"
PANEL_BG2 = "#121a30"
HIGHLIGHT = "#e94560"
TEXT = "#eee"
SUBTLE = "#aab"
ACCENT = "#0f3460"


# ── City Detail Panel ──
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


# ── Production Queue Panel ──
class ProductionQueuePanel(tk.Frame):
    """Queue of items being produced in a city."""

    def __init__(self, parent, city: City, on_queue_change: Optional[Callable] = None):
        super().__init__(parent, bg=PANEL_BG)
        self.city = city
        self.on_queue_change = on_queue_change
        self.panel_frame = None
        self._build()

    def _build(self):
        self.panel_frame = tk.Frame(self, bg=PANEL_BG)
        self.panel_frame.pack(fill=tk.X, padx=4, pady=4)

        tk.Label(self.panel_frame, text="Production Queue", bg=PANEL_BG, fg=HIGHLIGHT,
                 font=("Segoe UI", 10, "bold")).pack(fill=tk.X, padx=4, pady=(2, 0))

        self.list_frame = tk.Frame(self.panel_frame, bg=PANEL_BG)
        self.list_frame.pack(fill=tk.X, padx=4, pady=(2, 0))

        self._update()

    def _update(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        queue = self.city.production_queue
        current = self.city.current_production

        if not queue and not current:
            tk.Label(self.list_frame, text="No production", bg=PANEL_BG, fg=SUBTLE,
                     font=("Segoe UI", 9)).pack(pady=4)
            return

        # Current item
        if current:
            f = tk.Frame(self.list_frame, bg=PANEL_BG2, relief=tk.RAISED, bd=1)
            f.pack(fill=tk.X, pady=1)
            tk.Label(f, text=f"▶ {current}", bg=PANEL_BG2, fg=HIGHLIGHT,
                     font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=4, pady=2)
            tk.Label(f, text=f"({self.city.production}/{self.city.max_production})", bg=PANEL_BG2, fg=SUBTLE,
                     font=("Segoe UI", 8)).pack(side=tk.RIGHT, padx=4, pady=2)

        # Queue items
        for i, item in enumerate(queue):
            f = tk.Frame(self.list_frame, bg=PANEL_BG, relief=tk.FLAT, bd=0)
            f.pack(fill=tk.X, pady=1)
            tk.Label(f, text=f"{i+1}. {item}", bg=PANEL_BG, fg=TEXT,
                     font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4, pady=2)
            tk.Label(f, text=f"[{self.city.max_production} prod]", bg=PANEL_BG, fg=SUBTLE,
                     font=("Segoe UI", 8)).pack(side=tk.RIGHT, padx=4, pady=2)

    def refresh(self):
        self._update()


# ── Tech Tree Panel ──
class TechTreePanel(tk.Toplevel):
    """Popup showing researched / available / locked techs."""

    def __init__(self, parent, game: Game):
        super().__init__(parent)
        self.game = game
        self.title("Technology Tree")
        self.geometry("700x600")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.scroll_frame = None
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill=tk.X, padx=8, pady=(6, 0))
        tk.Label(top, text="Technology Tree", bg=BG, fg=HIGHLIGHT, font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        tk.Button(top, text="Close", bg=ACCENT, fg=TEXT, command=self.destroy).pack(side=tk.RIGHT)

        # Filter
        self.var = tk.StringVar()
        self.var.trace_add("write", lambda *_: self._redraw())
        ttk.Entry(top, textvariable=self.var, width=20).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(top, text="Filter", bg=BG, fg=SUBTLE, font=("Segoe UI", 8)).pack(side=tk.LEFT)

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
        for w in self.scroll_frame.wframes:
            w.destroy()
        self.scroll_frame.wframes = []

        filter_txt = self.var.get().lower()
        researched = set(self.game.researched.keys())

        for branch in [TechBranch.SCIENTIFIC, TechBranch.MILITARY, TechBranch.CIVIC]:
            header = tk.Frame(self.scroll_frame, bg=ACCENT)
            header.pack(fill=tk.X, pady=(8, 0))
            tk.Label(header, text=branch.value, bg=ACCENT, fg=TEXT, font=("Segoe UI", 11, "bold"),
                     padx=8, pady=2).pack(side=tk.LEFT)

            for tname, tech in sorted(self.game.technologies.items()):
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


# ── Diplomacy Panel ──
class DiplomacyPanel(tk.Toplevel):
    """Shows civ relationships and alliances."""

    def __init__(self, parent, game: Game):
        super().__init__(parent)
        self.game = game
        self.title("Diplomacy")
        self.geometry("500x400")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill=tk.X, padx=8, pady=(6, 0))
        tk.Label(top, text="Diplomacy", bg=BG, fg=HIGHLIGHT, font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        tk.Button(top, text="Close", bg=ACCENT, fg=TEXT, command=self.destroy).pack(side=tk.RIGHT)

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

    def _redraw(self):
        for w in getattr(self.scroll_frame, "wframes", []):
            w.destroy()
        self.scroll_frame.wframes = []

        player_civ = self.game.player_civ

        for civ in self.game.civs:
            if civ == player_civ:
                continue
            rel = self.game.diplomacy.get_relationship(player_civ, civ)
            status = rel.status.value if rel else "Unknown"
            icon = {"War": "⚔", "Tense": "😠", "Neutral": "😐", "Friendly": "😊", "Allied": "🤝"}.get(status, "❓")
            clr = {"War": "#f44336", "Tense": "#ff9800", "Neutral": "#aab", "Friendly": "#4caf50", "Allied": "#4caf50"}.get(status, "#aab")

            f = tk.Frame(self.scroll_frame, bg=BG)
            f.pack(fill=tk.X, padx=4, pady=2)
            tk.Label(f, text=f"{icon}  {civ}", bg=BG, fg=clr, font=("Segoe UI", 11),
                     padx=6, pady=2, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(f, text=f"Status: {status}", bg=BG, fg=SUBTLE, font=("Segoe UI", 9),
                     padx=6, anchor=tk.W).pack(side=tk.LEFT)
            self.scroll_frame.wframes.append(f)


# ── Dynasty Panel ──
class DynastyPanel(tk.Toplevel):
    """Shows dynasty ruler history."""

    def __init__(self, parent, game: Game):
        super().__init__(parent)
        self.game = game
        self.title("Dynasty")
        self.geometry("400x500")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill=tk.X, padx=8, pady=(6, 0))
        tk.Label(top, text="Dynasty", bg=BG, fg=HIGHLIGHT, font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        tk.Button(top, text="Close", bg=ACCENT, fg=TEXT, command=self.destroy).pack(side=tk.RIGHT)

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

    def _redraw(self):
        for w in getattr(self.scroll_frame, "wframes", []):
            w.destroy()
        self.scroll_frame.wframes = []

        dynasty = self.game.dynasty
        if not dynasty:
            tk.Label(self.scroll_frame, text="No dynasty yet", bg=BG, fg=SUBTLE,
                     font=("Segoe UI", 10)).pack(pady=20)
            return

        f = tk.Frame(self.scroll_frame, bg=BG)
        f.pack(fill=tk.X, padx=8, pady=4)
        tk.Label(f, text=f"Current Ruler: {dynasty.ruler_name}", bg=BG, fg=HIGHLIGHT,
                 font=("Segoe UI", 12, "bold")).pack(pady=4)
        tk.Label(f, text=f"Reign: Turn {dynasty.reign_start} to {dynasty.reign_end or 'Present'}",
                 bg=BG, fg=TEXT, font=("Segoe UI", 10)).pack(pady=2)
        tk.Label(f, text=f"Total Reign: {dynasty.get_reign_length()} turns",
                 bg=BG, fg=SUBTLE, font=("Segoe UI", 9)).pack(pady=2)
        self.scroll_frame.wframes.append(f)

        # Previous rulers
        if dynasty.previous_rulers:
            tk.Label(self.scroll_frame, text="Past Rulers", bg=BG, fg=HIGHLIGHT,
                     font=("Segoe UI", 10, "bold"), padx=8, pady=(8, 0)).pack(fill=tk.X)
            for r in dynasty.previous_rulers:
                f2 = tk.Frame(self.scroll_frame, bg=BG)
                f2.pack(fill=tk.X, padx=8, pady=1)
                tk.Label(f2, text=f"  👑 {r['name']} ({r['turns_in_power']} turns)", bg=BG, fg=TEXT,
                         font=("Segoe UI", 9)).pack(anchor=tk.W)
                self.scroll_frame.wframes.append(f2)


# ── Event Log Panel ──
class EventLogPanel(tk.Frame):
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


# ── Resource Bar (Top) ──
class ResourceBar(tk.Frame):
    """Top bar showing total resources."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent, bg=ACCENT)
        self.pack(fill=tk.X, side=tk.TOP)
        self.pack_propagate(False)
        self.game = game
        self.vars = {}
        self._build()

    def _build(self):
        items = [
            ("🌾 Food", "food"),
            ("⚙ Production", "production"),
            ("💰 Gold", "gold"),
            ("🔬 Science", "science"),
            ("😊 Happiness", "happiness"),
            ("📅 Turn", "turn"),
        ]
        for label, key in items:
            f = tk.Frame(self, bg=ACCENT)
            f.pack(side=tk.LEFT, padx=12, pady=6)
            tk.Label(f, text=f"{label}: 0", bg=ACCENT, fg=TEXT,
                     font=("Segoe UI", 10, "bold")).pack()
            self.vars[key] = f.winfo_children()[-1]

    def update(self):
        yields = self.game.city_manager.get_total_yields(self.game.player_civ.name)
        self.vars["food"].config(text=f"🌾 Food: {yields.get('food', 0)}")
        self.vars["production"].config(text=f"⚙ Production: {yields.get('production', 0)}")
        self.vars["gold"].config(text=f"💰 Gold: {self.game.gold.get(self.game.player_civ.name, 0)}")
        self.vars["science"].config(text=f"🔬 Science: {yields.get('science', 0)}")
        self.vars["happiness"].config(text=f"😊 Happiness: {yields.get('happiness', 0)}")
        self.vars["turn"].config(text=f"📅 Turn: {self.game.state.turn}")


# ── Quick Actions Toolbar ──
class QuickActionsToolbar(tk.Frame):
    """Bottom toolbar with action buttons."""

    def __init__(self, parent) -> None:
        super().__init__(parent, bg=ACCENT)
        self.pack(fill=tk.X, side=tk.BOTTOM)
        self.pack_propagate(False)

    def add_button(self, name: str, command: Callable, width: int = 12):
        tk.Button(self, text=name, bg=ACCENT, fg=TEXT, font=("Segoe UI", 10, "bold"),
                  activebackground=HIGHLIGHT, activeforeground=TEXT,
                  command=command, width=width).pack(side=tk.LEFT, padx=4, pady=(0, 10))
