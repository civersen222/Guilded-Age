"""
CivKings - Additional GUI Popups
Diplomacy, Dynasty, Victory panels, Production queue, Unit info.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Tuple

from game import Game
from game_data import TECHNOLOGIES, Technology, TechBranch, BUILDINGS, DISTRICTS, UNIT_TYPES, BuildingType, DistrictType
from victory import VictoryType, VictoryConditionTracker
from simulation import Character, Dynasty
from city import City
from military import Unit
from court import Court, CourtPosition


# ── Colours ──
BG = "#1a1a2e"
PANEL_BG = "#16213e"
PANEL_BG2 = "#1c2a44"
ACCENT = "#0f3460"
HIGHLIGHT = "#e94560"
TEXT = "#eee"
SUBTLE = "#aab"
ALIVE_COLOR = "#4ecca3"
DEAD_COLOR = "#e94560"


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
        tk.Label(self, text=f"Production: {self.city.production}/{self.city.production_capacity}",
                 bg=BG, fg=TEXT).pack()
        tk.Label(self, text=f"Gold: {self.city.gold}", bg=BG, fg=TEXT).pack()
        # Queue display
        queue_str = " - "
        if self.city.production_queue:
            queue_items = []
            for qitem in self.city.production_queue:
                if qitem in BUILDINGS:
                    queue_items.append(f"[B] {BUILDINGS[qitem].name}")
                elif qitem in DISTRICTS:
                    queue_items.append(f"[D] {DISTRICTS[qitem].name}")
                elif qitem in UNIT_TYPES:
                    queue_items.append(f"[U] {qitem}")
                else:
                    queue_items.append(qitem)
            queue_str = " -> ".join(queue_items)
        tk.Label(self, text=f"Queue: {queue_str}",
                 bg=BG, fg=SUBTLE, wraplength=380, justify=tk.LEFT).pack(pady=(0, 8))

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
      	  	     font=("Segoe UI", 10), selectbackground=HIGHLIGHT,
      	  	     activestyle="none", highlightthickness=0)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.listbox.yview)

        # Store keys for lookup
        self._item_keys: List[str] = []
        
        # Get player's researched techs and owned resources from game state
        player = self.game.players.get(self.city.owner)
        researched_techs = set(player.researched_techs) if player else set()
        owned_resources = set(player.resources) if player else set()

        # Populate production options with real costs & tech requirements
        for bname, btype in BUILDINGS.items():
            req = f"tech:{btype.requires_tech}" if btype.requires_tech else ("district:" + btype.district if btype.requires_district else "none")
            affordable = btype.production_cost <= self.city.production_capacity
            can_produce = affordable
            reason = ""
            if not affordable:
                can_produce = False
                reason = "Too expensive"
            elif btype.requires_tech and btype.requires_tech not in researched_techs:
                can_produce = False
                reason = f"Requires {btype.requires_tech}"
            
            color = "#4ecca3" if can_produce else "#e94560"
            text = f"  [B] {btype.name}  [Cost: {btype.production_cost}]  [Req: {req}]"
            if reason:
                text += f"  ({reason})"
            self.listbox.insert(tk.END, text)
            self.listbox.itemconfig(self.listbox.size() - 1, bg=PANEL_BG2, fg=color)
            self._item_keys.append(bname)

        for dname, dtype in DISTRICTS.items():
            req = "none"
            affordable = dtype.production_cost <= self.city.production_capacity
            can_produce = affordable
            reason = ""
            if not affordable:
                can_produce = False
                reason = "Too expensive"
            elif dtype.requires_tech and dtype.requires_tech not in researched_techs:
                can_produce = False
                reason = f"Requires {dtype.requires_tech}"
            
            color = "#4ecca3" if can_produce else "#e94560"
            text = f"  [D] {dtype.name}  [Cost: {dtype.production_cost}]  [Req: {req}]"
            if reason:
                text += f"  ({reason})"
            self.listbox.insert(tk.END, text)
            self.listbox.itemconfig(self.listbox.size() - 1, bg=PANEL_BG2, fg=color)
            self._item_keys.append(dname)

        for utype_name, utype in UNIT_TYPES.items():
            req = "none"
            cost = getattr(utype, 'production_cost', 40)
            if utype.requires_tech:
                req = f"tech:{utype.requires_tech}"
            if utype.resource_required:
                req += f", res:{utype.resource_required}"
            
            affordable = cost <= self.city.production_capacity
            can_produce = affordable
            reason = ""
            if not affordable:
                can_produce = False
                reason = "Too expensive"
            elif utype.requires_tech and utype.requires_tech not in researched_techs:
                can_produce = False
                reason = f"Requires {utype.requires_tech}"
            elif utype.resource_required and utype.resource_required not in owned_resources:
                can_produce = False
                reason = f"Requires {utype.resource_required}"
            
            color = "#4ecca3" if can_produce else "#e94560"
            text = f"  [U] {utype_name}  [Cost: {cost}]  [Req: {req}]"
            if reason:
                text += f"  ({reason})"
            self.listbox.insert(tk.END, text)
            self.listbox.itemconfig(self.listbox.size() - 1, bg=PANEL_BG2, fg=color)
            self._item_keys.append(utype_name)

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
        key = self._item_keys[sel[0]]

        # Check tech/resource requirements using the city's validation method
        if not self.city.assign_production(key, 
                                           researched_techs=set(self.game.players.get(self.city.owner).researched_techs) if self.city.owner in self.game.players else set(),
                                           owned_resources=set(self.game.players.get(self.city.owner).resources) if self.city.owner in self.game.players else set()):
            messagebox.showwarning("Cannot produce", f"Requirements not met for {key}.")
            return

        self.city.production_queue.append(key)
        if not self.city.current_production:
            self.city.current_production = key
        messagebox.showinfo("Production", f"Added '{key}' to production queue.")
        self.destroy()


# ── Unit Info Popup ──
class UnitInfoPopup(tk.Toplevel):
    """Popup showing unit details."""

    def __init__(self, parent, unit: Unit, game: Game) -> None:
        super().__init__(parent)
        self.title(f"Unit: {unit.unit_type}")
        self.geometry("350x250")
        self.configure(bg=BG)
        self.unit = unit
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text=f"{self.unit.unit_type}", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))
        
        info = f"Owner:     {self.unit.owner}\n" \
               f"Health:    {self.unit.health:.0f}%\n" \
               f"Position:  {self.unit.position}\n" \
               f"Power:     {self.unit.combat_power}\n" \
               f"Terrain:   {self.unit.terrain}\n" \
               f"Status:    {'Alive' if self.unit.is_alive else 'Dead'}"
        
        tk.Label(self, text=info, bg=BG, fg=TEXT, justify=tk.LEFT,
                 font=("Segoe UI", 10)).pack(pady=8)
        
        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT, command=self.destroy).pack(pady=4)


# ── Victory Popup ──
class VictoryPopup(tk.Toplevel):
    """Popup showing victory conditions and progress."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Victory Conditions")
        self.geometry("500x400")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Victory Conditions", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))
        
        tracker = VictoryConditionTracker(self.game)
        conditions = tracker.get_victory_conditions()
        
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
      	  	     font=("Segoe UI", 10), selectbackground=HIGHLIGHT,
      	  	     activestyle="none", highlightthickness=0)
        listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=listbox.yview)

        for vtype, info in conditions.items():
            status = "Complete" if info['complete'] else f"{info['progress']:.0%}"
            color = "#4ecca3" if info['complete'] else "#ffeb3b"
            listbox.insert(tk.END, f"{vtype.value}: {status}")
            listbox.itemconfig(listbox.size() - 1, bg=PANEL_BG2, fg=color)
        
        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT, command=self.destroy).pack(pady=8)


# ── Diplomacy Popup ──
class DiplomacyPopup(tk.Toplevel):
    """Popup for diplomacy actions."""

    def __init__(self, parent, game: Game, player_id: str) -> None:
        super().__init__(parent)
        self.title("Diplomacy")
        self.geometry("400x300")
        self.configure(bg=BG)
        self.game = game
        self.player_id = player_id
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Diplomacy", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))
        
        player = self.game.players.get(self.player_id)
        if not player:
            tk.Label(self, text="No player data", bg=BG, fg=TEXT).pack()
            return

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
      	  	     font=("Segoe UI", 10), selectbackground=HIGHLIGHT,
      	  	     activestyle="none", highlightthickness=0)
        listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=listbox.yview)

        for other_id, relations in player.diplomacy.items():
            status = relations['status']
            color = "#4ecca3" if status == "Allied" else ("#ffeb3b" if status == "Neutral" else "#e94560")
            listbox.insert(tk.END, f"{other_id}: {status}")
            listbox.itemconfig(listbox.size() - 1, bg=PANEL_BG2, fg=color)
        
        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT, command=self.destroy).pack(pady=8)


# ── Dynasty Popup ──
class DynastyPopup(tk.Toplevel):
    """Popup showing dynasty information."""

    def __init__(self, parent, dynasty: Dynasty, game: Game) -> None:
        super().__init__(parent)
        self.title(f"Dynasty: {dynasty.name}")
        self.geometry("450x350")
        self.configure(bg=BG)
        self.dynasty = dynasty
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text=f"Dynasty: {self.dynasty.name}", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))
        
        info = f"Leader:    {self.dynasty.leader}\n" \
               f"Founded:   {self.dynasty.founded}\n" \
               f"Members:   {len(self.dynasty.members)}\n" \
               f"Titles:    {', '.join(self.dynasty.titles) if self.dynasty.titles else 'None'}"
        
        tk.Label(self, text=info, bg=BG, fg=TEXT, justify=tk.LEFT,
                 font=("Segoe UI", 10)).pack(pady=8)
        
        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT, command=self.destroy).pack(pady=4)


# ── Court Popup ──
class CourtPopup(tk.Toplevel):
    """Popup showing court positions and occupants."""

    def __init__(self, parent, court: Court, game: Game) -> None:
        super().__init__(parent)
        self.title("Royal Court")
        self.geometry("500x400")
        self.configure(bg=BG)
        self.court = court
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Royal Court", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))
        
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
      	  	     font=("Segoe UI", 10), selectbackground=HIGHLIGHT,
      	  	     activestyle="none", highlightthickness=0)
        listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=listbox.yview)

        for pos, occupant in self.court.positions.items():
            status = f"{pos.value}: {occupant}" if occupant else f"{pos.value}: Vacant"
            color = "#4ecca3" if occupant else "#888"
            listbox.insert(tk.END, status)
            listbox.itemconfig(listbox.size() - 1, bg=PANEL_BG2, fg=color)
        
        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT, command=self.destroy).pack(pady=8)


# ── Event Log Popup ──
class EventLogPopup(tk.Toplevel):
    """Popup showing recent game events."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Event Log")
        self.geometry("500x400")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Event Log", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))
        
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
      	  	     font=("Segoe UI", 10), selectbackground=HIGHLIGHT,
      	  	     activestyle="none", highlightthickness=0)
        listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=listbox.yview)

        for event in self.game.event_log[-20:]:  # Show last 20 events
            listbox.insert(tk.END, event)
            listbox.itemconfig(listbox.size() - 1, bg=PANEL_BG2, fg=TEXT)
        
        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT, command=self.destroy).pack(pady=8)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Popups")
    root.geometry("200x100")
    
    def test_popup():
        game = Game()
        city = game.cities[0]
        popup = ProductionPopup(root, city, game)
    
    tk.Button(root, text="Test Production Popup", command=test_popup).pack(pady=10)
    root.mainloop()