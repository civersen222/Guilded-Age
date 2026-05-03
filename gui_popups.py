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


# ── Dark Fantasy Colours ──
BG = "#0a0b0d"
PANEL_BG = "#16181d"
PANEL_BG2 = "#23262d"
ACCENT = "#23262d"
HIGHLIGHT = "#c5a059"
TEXT = "#e0e0e0"
SUBTLE = "#888"
ALIVE_COLOR = "#c9a84c"
DEAD_COLOR = "#8b3a3a"
BORDER = "#33363d"
GOLD = "#c5a059"


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
            
            color = "#c9a84c" if can_produce else "#8b3a3a"
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
            
            color = "#c9a84c" if can_produce else "#8b3a3a"
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
            
            color = "#c9a84c" if can_produce else "#8b3a3a"
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
            color = "#c9a84c" if info['complete'] else "#f0a030"
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
            color = "#c9a84c" if status == "Allied" else ("#f0a030" if status == "Neutral" else "#8b3a3a")
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
            color = "#c9a84c" if occupant else "#888"
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


# ── Happiness Panel ──
class HappinessPanel(tk.Toplevel):
    """Panel showing empire happiness status."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Happiness")
        self.geometry("400x450")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Empire Happiness", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))

        hs = self.game.happiness_system
        happiness = hs.current_happiness
        color = "#c9a84c" if happiness >= 60 else ("#f0a030" if happiness >= 40 else "#8b3a3a")

        # Big percentage
        tk.Label(self, text=f"{happiness}%", font=("Segoe UI", 36, "bold"),
                 bg=BG, fg=color).pack(pady=(4, 8))

        status = "Happy" if hs.is_happy else ("Unhappy" if hs.is_unhappy else "Rebelling" if hs.is_rebelling else "Moderate")
        tk.Label(self, text=f"Status: {status}", font=("Segoe UI", 11),
                 bg=BG, fg=SUBTLE).pack()

        # Breakdown frame
        frame = tk.Frame(self, bg=ACCENT)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 4))

        inner = tk.Frame(frame, bg=ACCENT)
        inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        lines = [
            ("Base Happiness", f"{hs.base_happiness}"),
            ("Luxury Bonus", f"+{hs.luxury_bonus}"),
            ("Entertainment Bonus", f"+{hs.entertainment_bonus}"),
            ("Overextension Penalty", f"-{hs.overextension_penalty}"),
            ("War Penalty", f"-{hs.war_penalty}"),
            ("Conquest Penalty", f"-{hs.conquest_penalty}"),
            ("Tax Penalty", f"-{int(hs.tax_penalty)}"),
        ]
        for label, value in lines:
            tk.Label(inner, text=f"{label}: {value}", font=("Segoe UI", 10),
                     bg=ACCENT, fg=TEXT).pack(fill=tk.X, pady=1)

        # Effects
        tk.Label(self, text="Effects:", font=("Segoe UI", 10, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(8, 2))
        effects = [
            f"Production Loss: {hs.get_production_loss():.0%}",
            f"Growth Penalty: {hs.get_growth_penalty():.0%}",
            f"Rebellion Chance: {hs.get_rebellion_chance():.0%}",
        ]
        for e in effects:
            tk.Label(self, text=e, font=("Segoe UI", 9),
                     bg=BG, fg=SUBTLE).pack()

        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT,
                  font=("Segoe UI", 10), command=self.destroy).pack(pady=(8, 10))


# ── Stability Panel ──
class StabilityPanel(tk.Toplevel):
    """Panel showing empire stability status."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Stability")
        self.geometry("400x450")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Empire Stability", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))

        ss = self.game.stability_system
        stability = ss.stability
        color = "#c9a84c" if stability >= 60 else ("#f0a030" if stability >= 40 else "#8b3a3a")

        tk.Label(self, text=f"{stability}%", font=("Segoe UI", 36, "bold"),
                 bg=BG, fg=color).pack(pady=(4, 8))

        status = ss._get_status_label()
        tk.Label(self, text=f"Status: {status}", font=("Segoe UI", 11),
                 bg=BG, fg=SUBTLE).pack()

        frame = tk.Frame(self, bg=ACCENT)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 4))

        inner = tk.Frame(frame, bg=ACCENT)
        inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        lines = [
            ("Government Type", ss.government_type),
            ("Government Base", f"{ss.government_base}"),
            ("Unrest", f"{ss.unrest:.0f}"),
            ("Revolt Risk", f"{ss.calculate_revolt_risk():.0%}"),
            ("War Count", f"{ss._war_count}"),
            ("Conquest Count", f"{ss._recent_conquests}"),
        ]
        for label, value in lines:
            tk.Label(inner, text=f"{label}: {value}", font=("Segoe UI", 10),
                     bg=ACCENT, fg=TEXT).pack(fill=tk.X, pady=1)

        trend = ss.get_stability_trend()
        tk.Label(self, text=f"Trend: {trend}", font=("Segoe UI", 10),
                 bg=BG, fg=SUBTLE).pack(pady=(4, 0))

        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT,
                  font=("Segoe UI", 10), command=self.destroy).pack(pady=(8, 10))


# ── Economy Panel ──
class EconomyPanel(tk.Toplevel):
    """Panel showing empire economy/tax status."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Economy")
        self.geometry("420x500")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Empire Economy", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))

        ts = self.game.tax_system
        gold = self.game.gold.get(self.game.player_civ.name, 0)

        # Gold display
        tk.Label(self, text=f"Gold: {gold}", font=("Segoe UI", 20, "bold"),
                 bg=BG, fg="#c9a84c").pack(pady=(4, 4))

        # Tax rate slider
        tax_frame = tk.Frame(self, bg=BG)
        tax_frame.pack(fill=tk.X, padx=16, pady=(4, 8))
        tk.Label(tax_frame, text="Tax Rate:", font=("Segoe UI", 10),
                 bg=BG, fg=TEXT).pack(side=tk.LEFT)
        tk.Label(tax_frame, text=f"{ts.tax_rate}%", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(side=tk.LEFT, padx=(8, 12))

        def on_tax_change(*_):
            ts.set_tax_rate(int(self.tax_var.get()))
            self._update_tax_display()
        self.tax_var = tk.IntVar(value=ts.tax_rate)
        tk.Scale(tax_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.tax_var,
                 command=on_tax_change, bg=BG, fg=TEXT, highlightthickness=0,
                 troughcolor=ACCENT, length=200).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tax_desc = ts.get_tax_description()
        tk.Label(self, text=tax_desc, font=("Segoe UI", 9, "italic"),
                 bg=BG, fg=SUBTLE).pack(pady=(0, 4))

        # Effects frame
        frame = tk.Frame(self, bg=ACCENT)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 4))

        inner = tk.Frame(frame, bg=ACCENT)
        inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        effects = ts.get_effects_summary()
        lines = [
            ("Gold Multiplier", f"{effects['gold_multiplier']:.2f}"),
            ("Happiness Penalty", f"-{effects['happiness_penalty']:.1f}"),
            ("Growth Penalty", f"-{effects['growth_penalty']:.1f}"),
        ]
        for label, value in lines:
            tk.Label(inner, text=f"{label}: {value}", font=("Segoe UI", 10),
                     bg=ACCENT, fg=TEXT).pack(fill=tk.X, pady=1)

        # City production summary
        total_prod = sum(c.production_capacity for c in self.game.cities.values())
        total_gold = sum(c.gold for c in self.game.cities.values())
        tk.Label(self, text=f"Total Production Capacity: {total_prod}",
                 font=("Segoe UI", 9), bg=BG, fg=SUBTLE).pack()
        tk.Label(self, text=f"City Gold Reserves: {total_gold}",
                 font=("Segoe UI", 9), bg=BG, fg=SUBTLE).pack()

        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT,
                  font=("Segoe UI", 10), command=self.destroy).pack(pady=(8, 10))

    def _update_tax_display(self) -> None:
        """Update the tax description label."""
        pass  # Slider handles display directly


# ── Factions Panel ──
class FactionsPanel(tk.Toplevel):
    """Panel showing political factions."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Factions")
        self.geometry("420x480")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Political Factions", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))

        fm = self.game.faction_manager
        factions = getattr(fm, 'factions', {})
        if not factions:
            tk.Label(self, text="No factions initialized.", bg=BG, fg=SUBTLE).pack(pady=20)
            tk.Button(self, text="Close", bg=ACCENT, fg=TEXT,
                      font=("Segoe UI", 10), command=self.destroy).pack(pady=8)
            return

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
      	  	     font=("Segoe UI", 10), selectbackground=HIGHLIGHT,
      	  	     activestyle="none", highlightthickness=0)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.listbox.yview)

        for fname, faction in factions.items():
            if hasattr(faction, 'influence'):
                text = f"  {faction.name} ({faction.faction_type})  [Influence: {faction.influence}]  [Support: {faction.support}]"
                color = "#c9a84c" if faction.influence >= 50 else ("#f0a030" if faction.influence >= 30 else "#8b3a3a")
            else:
                text = f"  {fname}: {faction}"
                color = TEXT
            self.listbox.insert(tk.END, text)
            self.listbox.itemconfig(self.listbox.size() - 1, bg=PANEL_BG2, fg=color)

        # Conflict level
        conflict = getattr(fm, 'conflict_level', None)
        if conflict is not None:
            tk.Label(self, text=f"Conflict Level: {conflict:.0f}%",
                     font=("Segoe UI", 10), bg=BG, fg=SUBTLE).pack(pady=(4, 0))

        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT,
                  font=("Segoe UI", 10), command=self.destroy).pack(pady=(8, 10))


# ── Victory Panel ──
class VictoryPanel(tk.Toplevel):
    """Panel showing victory conditions progress."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Victory Conditions")
        self.geometry("450x520")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Victory Conditions", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))

        tracker = self.game.victory_tracker
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
      	  	     font=("Segoe UI", 10), selectbackground=HIGHLIGHT,
      	  	     activestyle="none", highlightthickness=0)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.listbox.yview)

        for vtype, cond in tracker.conditions.items():
            progress = cond.value / cond.threshold if cond.threshold else 0
            pct = min(100, progress * 100)
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            achieved = "✓" if cond.value >= cond.threshold else " "
            text = f"  [{achieved}] {vtype.value:18s}  [{bar}]  {pct:.0f}%"
            color = "#c9a84c" if pct >= 100 else ("#f0a030" if pct >= 50 else SUBTLE)
            self.listbox.insert(tk.END, text)
            self.listbox.itemconfig(self.listbox.size() - 1, bg=PANEL_BG2, fg=color)

        # Check if any victory achieved
        achieved = tracker.get_victory()
        if achieved:
            tk.Label(self, text=f"Victory: {achieved.value}",
                     font=("Segoe UI", 11, "bold"), bg=BG, fg="#c9a84c").pack(pady=(8, 0))

        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT,
                  font=("Segoe UI", 10), command=self.destroy).pack(pady=(8, 10))


# ── Tech Tree Popup ──
class TechTreePopup(tk.Toplevel):
    """Popup showing the technology tree."""

    def __init__(self, parent, tech_manager: TechManager) -> None:
        super().__init__(parent)
        self.title("Technology Tree")
        self.geometry("500x550")
        self.configure(bg=BG)
        self.tech_manager = tech_manager
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Technology Tree", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))

        # Currently researching
        current = self.tech_manager.current_research
        if current:
            tech = TECHNOLOGIES.get(current)
            if tech:
                tk.Label(self, text=f"Researching: {tech.name}",
                         font=("Segoe UI", 11, "bold"), bg=BG, fg="#f0a030").pack()
                progress = self.tech_manager.current_research_progress / tech.cost * 100 if tech.cost else 0
                bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                tk.Label(self, text=f"[{bar}] {progress:.0f}%",
                         font=("Segoe UI", 9), bg=BG, fg=TEXT).pack(pady=2)
        else:
            tk.Label(self, text="No technology currently researching.",
                     font=("Segoe UI", 10), bg=BG, fg=SUBTLE).pack(pady=4)

        # Available technologies
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
      	  	     font=("Segoe UI", 10), selectbackground=HIGHLIGHT,
      	  	     activestyle="none", highlightthickness=0)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.listbox.yview)

        # Group by era
        eras = {}
        for tech_name, tech in TECHNOLOGIES.items():
            if tech_name not in self.tech_manager.researched:
                if tech.era not in eras:
                    eras[tech.era] = []
                eras[tech.era].append(tech)

        for era, techs in eras.items():
            tk.Label(frame, text=f"  ── {era.value} ──", font=("Segoe UI", 10, "bold"),
                     bg=PANEL_BG, fg=HIGHLIGHT).pack(fill=tk.X, pady=(4, 0))
            for tech in techs:
                prereqs = ", ".join(tech.prerequisites) if tech.prerequisites else "None"
                text = f"    • {tech.name:20s}  Cost: {tech.cost:4d}  Prereq: {prereqs}"
                self.listbox.insert(tk.END, text)
                self.listbox.itemconfig(self.listbox.size() - 1, bg=PANEL_BG2, fg=TEXT)

        # Researched count
        tk.Label(self, text=f"Researched: {len(self.tech_manager.researched)}/{len(TECHNOLOGIES)}",
                 font=("Segoe UI", 9), bg=BG, fg=SUBTLE).pack(pady=(4, 0))

        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT,
                  font=("Segoe UI", 10), command=self.destroy).pack(pady=(8, 10))


# ── Diplomacy Panel ──
class DiplomacyPanel(tk.Toplevel):
    """Panel showing diplomatic relations."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Diplomacy")
        self.geometry("480x480")
        self.configure(bg=BG)
        self.game = game
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Diplomatic Relations", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(10, 4))

        dm = self.game.diplomacy_manager
        player_name = self.game.player_civ.name
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        sb = tk.Scrollbar(frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(frame, yscrollcommand=sb.set, bg=PANEL_BG, fg=TEXT,
      	  	     font=("Segoe UI", 10), selectbackground=HIGHLIGHT,
      	  	     activestyle="none", highlightthickness=0)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.listbox.yview)

        # Show all civs
        for civ_name, civ in self.game.civilizations.items():
            if civ_name == player_name:
                continue

            # Get relation score
            rel_key = (player_name, civ_name)
            rel_score = dm.relations.get(rel_key, 0)
            color = "#c9a84c" if rel_score >= 30 else ("#f0a030" if rel_score >= -10 else "#8b3a3a")

            # Status
            is_allied = civ_name in dm.alliances.get(player_name, [])
            is_at_war = civ_name in dm.wars.get(player_name, [])
            status = "⚔️ War" if is_at_war else ("🤝 Allied" if is_allied else "Neutral")

            text = f"  {civ_name:18s}  Relation: {rel_score:3d}  {status}"
            self.listbox.insert(tk.END, text)
            self.listbox.itemconfig(self.listbox.size() - 1, bg=PANEL_BG2, fg=color)

        # Messages
        messages = getattr(dm, 'messages', [])
        recent_msgs = [m for m in messages if m.turn >= self.game.state.turn - 10]
        if recent_msgs:
            tk.Label(self, text=f"Recent Messages ({len(recent_msgs)}):",
                     font=("Segoe UI", 10, "bold"), bg=BG, fg=HIGHLIGHT).pack(pady=(8, 2))
            for msg in recent_msgs[-5:]:
                icon = TYPE_ICONS.get(msg.msg_type, "📜")
                tk.Label(self, text=f"  {icon} [{msg.turn}] {msg.from_civ} → {msg.to_civ}: {msg.subject}",
                         font=("Segoe UI", 8), bg=BG, fg=SUBTLE).pack(anchor=tk.W, padx=16)

        tk.Button(self, text="Close", bg=ACCENT, fg=TEXT,
                  font=("Segoe UI", 10), command=self.destroy).pack(pady=(8, 10))