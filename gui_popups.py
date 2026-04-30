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
        options: List[Tuple[str, str, any]] = []
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
    """Shows diplomatic relations between all civs with trade routes and message inbox."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Diplomacy")
        self.geometry("700x550")
        self.configure(bg=BG)
        self.game = game
        self.current_tab = "relations"
        self._build()

    def _build(self) -> None:
        # Title
        tk.Label(self, text="Diplomatic Relations", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(8, 4))

        # Tab buttons
        tab_frame = tk.Frame(self, bg=BG)
        tab_frame.pack(fill=tk.X, padx=12, pady=(0, 6))
        for tab_name in ("Relations", "Trade Routes", "Inbox"):
            tk.Button(tab_frame, text=tab_name, font=("Segoe UI", 10),
                      bg=PANEL_BG2, fg=TEXT, width=14,
                      command=lambda t=tab_name.lower(): self._switch_tab(t)) \
                .pack(side=tk.LEFT, padx=2)

        # Container for tab content
        self.tab_frame = tk.Frame(self, bg=BG)
        self.tab_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        # Text widget for displaying content
        sb = tk.Scrollbar(self.tab_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.text = tk.Text(self.tab_frame, bg=PANEL_BG, fg=TEXT, font=("Consolas", 10),
                            padx=8, pady=4, relief=tk.FLAT, wrap=tk.WORD,
                            highlightthickness=0)
        self.text.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)

        # Action buttons area
        self.action_frame = tk.Frame(self, bg=BG)
        self.action_frame.pack(fill=tk.X, pady=(4, 8))

        # Show relations by default
        self._switch_tab("relations")

    def _switch_tab(self, tab_name: str) -> None:
        self.current_tab = tab_name
        # Clear text widget
        self.text.delete(1.0, tk.END)
        # Clear action buttons
        for w in self.action_frame.winfo_children():
            w.destroy()
        self.text.delete(1.0, tk.END)

        if tab_name == "relations":
            self._show_relations_tab()
        elif tab_name == "trade_routes":
            self._show_trade_tab()
        elif tab_name == "inbox":
            self._show_inbox_tab()

    def _get_status_color(self, status: str) -> str:
        colors = {
            "War": "#e94560",
            "Friendly": "#4ecca3",
            "Allied": "#45b7d1",
            "Neutral": "#aab",
        }
        return colors.get(status, TEXT)

    def _get_type_color(self, msg_type: str) -> str:
        colors = {
            "declaration_war": "#e94560",
            "warning": "#e94560",
            "peace_offer": "#4ecca3",
            "alliance_offer": "#45b7d1",
            "trade_offer": "#f0c040",
            "trade_route": "#f0c040",
            "declaration": "#aab",
        }
        return colors.get(msg_type, TEXT)

    def _show_relations_tab(self) -> None:
        rels = self.game.diplomacy_manager.get_all_relations()
        all_civs = list(self.game.civilizations.keys())
        lines = []
        for civ1 in all_civs:
            for civ2 in all_civs:
                if civ1 >= civ2:
                    continue
                status = rels.get((civ1, civ2), rels.get((civ2, civ1), "Neutral"))
                color = self._get_status_color(status)
                lines.append(f"  {civ1} ↔ {civ2}:")
                lines.append(f"    Status: {status}")
                # Show trade routes
                routes = self.game.diplomacy_manager.get_trade_routes_for(civ1)
                for r in routes:
                    if r['partner'] == civ2:
                        lines.append(f"    Trade: {r['cargo']} → {r['yield']} gold/turn")
                lines.append("")

        self.text.insert(tk.END, "\n".join(lines) if lines else "  No diplomacy data yet.")

    def _show_trade_tab(self) -> None:
        """Show trade route management tab"""
        all_civs = list(self.game.civilizations.keys())
        # Use first civ as the player for UI purposes
        player_civ = all_civs[0] if all_civs else "Player"

        lines = [f"  Trade Routes for {player_civ}:\n"]
        routes = self.game.diplomacy_manager.get_trade_routes_for(player_civ)
        if routes:
            for r in routes:
                lines.append(f"  🚢 {player_civ} ↔ {r['partner']}")
                lines.append(f"     Cargo: {r['cargo']} | Yield: {r['yield']} gold/turn")
                lines.append(f"     [Cancel] [Change Cargo]")
                lines.append("")
        else:
            lines.append("  No active trade routes.\n")

        # Available partners for new routes
        lines.append("  Create New Trade Route:\n")
        existing_partners = {r['partner'] for r in routes}
        for civ in all_civs:
            if civ != player_civ and civ not in existing_partners:
                is_war = self.game.diplomacy_manager.is_at_war(player_civ, civ)
                status = "AT WAR" if is_war else "Available"
                lines.append(f"  • {civ} ({status})")
        lines.append("")

        self.text.insert(tk.END, "\n".join(lines))

        # Add action buttons
        btn_frame = tk.Frame(self.action_frame, bg=BG)
        btn_frame.pack(fill=tk.X)
        if routes:
            tk.Button(btn_frame, text="Cancel Selected Route", bg=HIGHLIGHT, fg="white",
                      font=("Segoe UI", 10, "bold"), width=20) \
                .pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Create Trade Route", bg=ACCENT, fg=TEXT,
                  font=("Segoe UI", 10, "bold"), width=20) \
            .pack(side=tk.LEFT, padx=4)

    def _show_inbox_tab(self) -> None:
        """Show diplomatic message inbox tab"""
        all_civs = list(self.game.civilizations.keys())
        player_civ = all_civs[0] if all_civs else "Player"

        messages = self.game.diplomacy_manager.get_messages_for(player_civ)
        unread = self.game.diplomacy_manager.get_unread_messages_for(player_civ)

        lines = [f"  Diplomatic Inbox for {player_civ}"]
        if unread:
            lines.append(f"  ⚠️ {len(unread)} unread message(s)")
        lines.append("")

        if messages:
            for m in messages:
                icon = TYPE_ICONS.get(m.msg_type, '📬')
                status = "🔴" if not m.read else "🟢"
                lines.append(f"  {status} {icon} [{m.from_civ}] {m.subject}")
                lines.append(f"       Turn {m.turn} | Type: {m.msg_type}")
                lines.append(f"       {m.body}")
                lines.append("")
        else:
            lines.append("  No messages yet.")
            lines.append("")

        self.text.insert(tk.END, "\n".join(lines))

        # Add action buttons
        btn_frame = tk.Frame(self.action_frame, bg=BG)
        btn_frame.pack(fill=tk.X)
        if unread:
            tk.Button(btn_frame, text="Mark All as Read", bg=ACCENT, fg=TEXT,
                      font=("Segoe UI", 10), width=20) \
                .pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Send Message", bg=HIGHLIGHT, fg="white",
                  font=("Segoe UI", 10, "bold"), width=20) \
            .pack(side=tk.LEFT, padx=4)

    def get_all_relations(self) -> Dict[Tuple[str, str], str]:
        """Helper for UI compatibility"""
        # Map numeric scores to text status
        rels = {}
        for pair, score in self.game.diplomacy_manager.relations.items():
            if score >= 70 and self.game.diplomacy_manager.is_allied(pair[0], pair[1]):
                status = "Allied"
            elif score >= 40:
                status = "Friendly"
            elif score <= -70 or any(pair[0] in self.game.diplomacy_manager.wars.get(pair[1], [])
                                     for pair in [pair]):
                status = "War"
            else:
                status = "Neutral"
            rels[pair] = status
        return rels


# ── Dynasty Popup ──
class DynastyPopup(tk.Toplevel):
    """Shows dynasty members, family tree, succession, and court positions."""

    def __init__(self, parent, game: Game) -> None:
        super().__init__(parent)
        self.title("Dynasty & Court")
        self.geometry("800x600")
        self.configure(bg=BG)
        self.game = game
        self.current_tab = "members"
        self._build()

    def _build(self) -> None:
        # Title
        tk.Label(self, text="Royal Dynasty & Court", font=("Segoe UI", 13, "bold"),
                 bg=BG, fg=HIGHLIGHT).pack(pady=(8, 4))

        # Tab buttons
        tab_frame = tk.Frame(self, bg=BG)
        tab_frame.pack(fill=tk.X, padx=12, pady=(0, 6))
        for tab_name in ("Members", "Family Tree", "Succession", "Court", "Intrigue"):
            tk.Button(tab_frame, text=tab_name, font=("Segoe UI", 10),
                      bg=PANEL_BG2, fg=TEXT, width=14,
                      command=lambda t=tab_name.lower(): self._switch_tab(t)) \
                .pack(side=tk.LEFT, padx=2)

        # Container for tab content
        self.tab_frame = tk.Frame(self, bg=BG)
        self.tab_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        # Scrollable text area
        sb = tk.Scrollbar(self.tab_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.text = tk.Text(self.tab_frame, bg=PANEL_BG, fg=TEXT, font=("Consolas", 10),
                            padx=8, pady=4, relief=tk.FLAT, wrap=tk.WORD,
                            highlightthickness=0)
        self.text.pack(fill=tk.BOTH, expand=True, pady=4)
        sb.config(command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)

        # Action buttons area
        self.action_frame = tk.Frame(self, bg=BG)
        self.action_frame.pack(fill=tk.X, pady=(4, 8))

        # Show members by default
        self._switch_tab("members")

    def _switch_tab(self, tab_name: str) -> None:
        self.current_tab = tab_name
        # Clear text widget
        self.text.delete(1.0, tk.END)
        # Clear action buttons
        for w in self.action_frame.winfo_children():
            w.destroy()

        if tab_name == "members":
            self._show_members_tab()
        elif tab_name == "family_tree":
            self._show_family_tree_tab()
        elif tab_name == "succession":
            self._show_succession_tab()
        elif tab_name == "court":
            self._show_court_tab()
        elif tab_name == "intrigue":
            self._show_intrigue_tab()

    def _show_members_tab(self) -> None:
        """Show all dynasty members with stats and status"""
        lines = ["=== Dynasty Members ===\n"]
        
        if self.game.dynasty:
            prestige = self.game.dynasty.calculate_dynastic_prestige()
            lines.append(f"Prestige: {prestige}\n")
            
            for member_id, char in self.game.dynasty.members.items():
                alive = getattr(char, 'is_alive', True)
                status = "Alive" if alive else "Deceased"
                color = ALIVE_COLOR if alive else DEAD_COLOR
                lines.append(f"  {color}● {char.name} ({status}) — Dipl: {char.stats.get('diplomacy', 0):2d}  Mart: {char.stats.get('martial', 0):2d}  Stew: {char.stats.get('stewardship', 0):2d}  Intr: {char.stats.get('intrigue', 0):2d}")
                
                # Show traits if available
                if hasattr(char, 'traits') and char.traits:
                    lines.append(f"      Traits: {', '.join(char.traits)}")
                lines.append("")
        else:
            lines.append("  No dynasty yet.")
            lines.append("")

        self.text.insert(tk.END, "\n".join(lines))

    def _show_family_tree_tab(self) -> None:
        """Show family tree visualization"""
        lines = ["=== Family Tree ===\n"]
        
        if self.game.dynasty:
            def print_tree(char, indent=0, is_last=True):
                prefix = "└── " if is_last else "├── "
                prefix = "    " * indent + prefix
                alive = getattr(char, 'is_alive', True)
                status = "Alive" if alive else "Deceased"
                color = ALIVE_COLOR if alive else DEAD_COLOR
                lines.append(f"{prefix}{color}● {char.name} ({status})")
                
                # Show children
                if hasattr(char, 'children_ids') and char.children_ids:
                    children = []
                    for child_id in char.children_ids:
                        child = self.game.dynasty.members.get(child_id)
                        if child:
                            children.append(child)
                    
                    for i, child in enumerate(children):
                        is_last_child = (i == len(children) - 1)
                        print_tree(child, indent + 1, is_last_child)
            
            if self.game.dynasty.root:
                print_tree(self.game.dynasty.root)
        else:
            lines.append("  No dynasty data.")
            lines.append("")

        self.text.insert(tk.END, "\n".join(lines))

    def _show_succession_tab(self) -> None:
        """Show succession law and heir information"""
        lines = ["=== Succession ===\n"]
        
        if self.game.dynasty and self.game.dynasty.root:
            # Succession laws (placeholder - can be expanded)
            succession_laws = {
                "agnatic": "Male preference primogeniture",
                "cognatic": "Absolute primogeniture",
                "male": "Male-only primogeniture",
                "female": "Female-only primogeniture",
            }
            current_law = "agnatic"  # Default
            
            lines.append(f"Succession Law: {succession_laws.get(current_law, current_law)}\n")
            
            # Find heir apparent
            heir = self._find_heir()
            if heir:
                alive = getattr(heir, 'is_alive', True)
                status = "Alive" if alive else "Deceased"
                color = ALIVE_COLOR if alive else DEAD_COLOR
                lines.append(f"Heir Apparent: {color}● {heir.name} ({status})")
                if hasattr(heir, 'traits') and heir.traits:
                    lines.append(f"  Traits: {', '.join(heir.traits)}")
                lines.append(f"  Stats: Dipl: {heir.stats.get('diplomacy', 0)}  Mart: {heir.stats.get('martial', 0)}  Stew: {heir.stats.get('stewardship', 0)}  Intr: {heir.stats.get('intrigue', 0)}")
            else:
                lines.append("Heir Apparent: None")
            lines.append("")
            
            # List all potential heirs
            lines.append("Potential Heirs:")
            heirs = self._get_potential_heirs()
            for i, heir in enumerate(heirs, 1):
                alive = getattr(heir, 'is_alive', True)
                status = "Alive" if alive else "Deceased"
                color = ALIVE_COLOR if alive else DEAD_COLOR
                lines.append(f"  {i}. {color}● {heir.name} ({status})")
        else:
            lines.append("  No dynasty data.")
            lines.append("")

        self.text.insert(tk.END, "\n".join(lines))

    def _show_court_tab(self) -> None:
        """Show court positions and management"""
        lines = ["=== Court Positions ===\n"]
        
        if self.game.court:
            lines.append(f"Ruler: {self.game.court.ruler.name}\n")
            
            for pos in CourtPosition:
                char = self.game.court.positions.get(pos)
                if char and char.is_alive:
                    bonus = self.game.court.get_bonus(pos)
                    lines.append(f"  {pos.value:12s} <- {char.name:20s} (+{bonus})")
                    if hasattr(char, 'traits') and char.traits:
                        lines.append(f"              Traits: {', '.join(char.traits)}")
                else:
                    lines.append(f"  {pos.value:12s} <- VACANT")
            lines.append("")
            
            lines.append(f"Filled: {self.game.court.filled_count}/5\n")
            
            # Show available candidates
            lines.append("Available Candidates:")
            if self.game.dynasty:
                candidates = [m for m in self.game.dynasty.members.values() 
                             if m.id != self.game.court.ruler.id]
                for char in candidates:
                    alive = getattr(char, 'is_alive', True)
                    status = "Alive" if alive else "Deceased"
                    color = ALIVE_COLOR if alive else DEAD_COLOR
                    lines.append(f"  {color}● {char.name} (Dipl: {char.stats.get('diplomacy', 0)}  Mart: {char.stats.get('martial', 0)}  Stew: {char.stats.get('stewardship', 0)}  Intr: {char.stats.get('intrigue', 0)})")
        else:
            lines.append("  No court data.")
            lines.append("")

        self.text.insert(tk.END, "\n".join(lines))

    def _show_intrigue_tab(self) -> None:
        """Show intrigue and alerts panel"""
        lines = ["=== Intrigue & Alerts ===\n"]
        
        # Sample alerts (can be expanded with actual game events)
        alerts = [
            ("⚠️", "A plot has been discovered against your realm!", "red"),
            ("💰", "Tax collection complete: +50 gold", "gold"),
            ("⚔️", "Border skirmish reported!", "orange"),
            ("🕵️", "Spy network expanded in neighboring realm", "blue"),
            ("🎭", "Cultural festival planned for next month", "purple"),
        ]
        
        if alerts:
            for icon, msg, color in alerts:
                lines.append(f"  {icon} {msg}")
        else:
            lines.append("  No active alerts.")
        lines.append("")

        self.text.insert(tk.END, "\n".join(lines))

    def _find_heir(self) -> Optional[Character]:
        """Find the heir apparent based on succession laws"""
        if not self.game.dynasty or not self.game.dynasty.root:
            return None
        
        # Simple implementation: first living child of ruler with highest martial stat
        candidates = []
        for member_id, char in self.game.dynasty.members.items():
            if char.is_alive and hasattr(char, 'parent_ids'):
                if self.game.dynasty.root.id in char.parent_ids:
                    candidates.append(char)
        
        if not candidates:
            return None
        
        # Sort by martial stat (simplified succession law)
        candidates.sort(key=lambda c: c.stats.get('martial', 0), reverse=True)
        return candidates[0]

    def _get_potential_heirs(self) -> List[Character]:
        """Get all potential heirs sorted by priority"""
        if not self.game.dynasty:
            return []
        
        members = list(self.game.dynasty.members.values())
        # Filter living members
        living = [m for m in members if getattr(m, 'is_alive', True)]
        # Sort by martial stat (simplified)
        living.sort(key=lambda c: c.stats.get('martial', 0), reverse=True)
        return living


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

        # Show victory progress
        progress = self.game.victory_tracker.get_all_progress()
        lines = []
        for vtype, data in progress.items():
            icon = VICTORY_ICONS.get(vtype, "❓")
            progress_val = data.get('progress', 0)
            status = "✅ Complete" if data.get('achieved', False) else f"⬜ {progress_val}%"
            lines.append(f"  {icon} {vtype}: {status}")
        
        self.text.insert(tk.END, "\n".join(lines) if lines else "  No victory data.")


# ── Constants for UI ──
VICTORY_ICONS = {
    "Domination": "★",
    "Science": "⚛",
    "Culture": "🎭",
    "Diplomatic": "🤝",
    "Dynasty": "👑",
}

TYPE_ICONS = {
    "declaration_war": "⚔️",
    "warning": "⚠️",
    "peace_offer": "🕊️",
    "alliance_offer": "🤝",
    "trade_offer": "💰",
    "trade_route": "🚢",
    "declaration": "📜",
}

UNIT_TYPES = {
    "Militia": type('UnitType', (), {'production_cost': 20})(),
    "Infantry": type('UnitType', (), {'production_cost': 40})(),
    "Archers": type('UnitType', (), {'production_cost': 35})(),
}
