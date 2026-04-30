"""
CivKings - Victory Condition UI
Displays victory progress and victory screen.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional

from game_data import VictoryType
from victory import VictoryConditionTracker

BG = "#1a1a2e"
PANEL_BG = "#16213e"
HIGHLIGHT = "#e94560"
TEXT = "#eee"
SUBTLE = "#aab"
ACCENT = "#0f3460"


class VictoryPanel(tk.Toplevel):
    """Popup showing all victory conditions and progress."""

    def __init__(self, parent, victory_tracker: VictoryConditionTracker, player_civ: str, turn: int):
        super().__init__(parent)
        self.vt = victory_tracker
        self.player_civ = player_civ
        self.turn = turn
        self.title("Victory Conditions")
        self.geometry("600x500")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill=tk.X, padx=8, pady=(6, 0))
        tk.Label(top, text=f"Victory Conditions - Turn {self.turn}", bg=BG, fg=HIGHLIGHT,
                 font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
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

        for vtype in VictoryType:
            pct = self.vt.get_percentage(vtype)
            achieved = pct >= 100
            desc = self.vt.get_victory_description(vtype)
            bar_color = "#4caf50" if achieved else "#e94560"
            bg_color = "#1a3a1a" if achieved else BG

            row = tk.Frame(self.scroll_frame, bg=bg_color)
            row.pack(fill=tk.X, padx=4, pady=3)

            tk.Label(row, text={"Domination": "★", "Science": "⚛", "Culture": "🎭",
                                "Diplomatic": "🤝", "Dynasty": "👑"}.get(vtype.value[:8], "•"),
                     bg=bg_color, fg=HIGHLIGHT, font=("Segoe UI", 14), padx=(8, 4)).pack(side=tk.LEFT)

            info = tk.Frame(row, bg=bg_color)
            info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

            tk.Label(info, text=f"{vtype.value} - {pct:.1f}%", bg=bg_color, fg=HIGHLIGHT if achieved else TEXT,
                     font=("Segoe UI", 10, "bold"), anchor=tk.W).pack(fill=tk.X)
            tk.Label(info, text=desc, bg=bg_color, fg=SUBTLE, font=("Segoe UI", 8), anchor=tk.W).pack(fill=tk.X)

            # Progress bar
            bar_frame = tk.Frame(info, bg=ACCENT, height=6)
            bar_frame.pack(fill=tk.X, pady=(2, 0))
            bar = tk.Frame(bar_frame, bg=ACCENT, height=6)
            bar.pack(fill=tk.X)
            fill_w = max(1, int(bar_frame.winfo_width() * min(pct / 100, 1.0)))
            tk.Frame(bar, bg=bar_color, width=fill_w, height=6).pack(side=tk.LEFT, fill=tk.Y)

            row.wframes = []
            row.wframes.append(info)
            row.wframes.append(bar_frame)
            self.scroll_frame.wframes.append(row)

    def update(self):
        """Refresh the panel."""
        self._redraw()


class VictoryScreen(tk.Toplevel):
    """Full-screen victory celebration."""

    def __init__(self, parent, victory_type: VictoryType, turn: int):
        super().__init__(parent)
        self.title("VICTORY!")
        self.attributes("-fullscreen", True)
        self.configure(bg=BG)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # Center content
        f = tk.Frame(self, bg=BG)
        f.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        tk.Label(f, text="🎉 VICTORY! 🎉", bg=BG, fg="#ffd700",
                 font=("Segoe UI", 36, "bold"), pady=20).pack()
        tk.Label(f, text=victory_type.value, bg=BG, fg=HIGHLIGHT,
                 font=("Segoe UI", 24), pady=10).pack()
        tk.Label(f, text=f"Achieved on Turn {turn}", bg=BG, fg=SUBTLE,
                 font=("Segoe UI", 14), pady=10).pack()

        tk.Button(f, text="Play Again", bg=ACCENT, fg=TEXT, font=("Segoe UI", 12, "bold"),
                  command=self.destroy, width=15, pady=10).pack(pady=20)


class VictoryManager:
    """Facade for victory UI + logic."""

    def __init__(self, victory_tracker: VictoryConditionTracker):
        self.tracker = victory_tracker

    def show_victory_panel(self, parent, player_civ: str, turn: int):
        return VictoryPanel(parent, self.tracker, player_civ, turn)

    def show_victory_screen(self, parent, victory_type: VictoryType, turn: int):
        return VictoryScreen(parent, victory_type, turn)

    def check_and_show(self, parent, player_civ: str, turn: int):
        vtype = self.tracker.check_victory()
        if vtype:
            self.tracker.victory_turn = turn
            return self.show_victory_screen(parent, vtype, turn)
        return None
