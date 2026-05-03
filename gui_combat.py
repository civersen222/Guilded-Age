"""
CivKings - Combat UI
Handles combat calculations, battle display, and combat result panels.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Tuple

from combat import resolve_combat, CombatResult
from military import Unit
from hex_map import HexTile

BG = "#121212"
PANEL_BG = "#1e1e1e"
HIGHLIGHT = "#c9a84c"
TEXT = "#e0d6c2"
SUBTLE = "#8b7d6b"
ACCENT = "#2a2a2a"


class CombatCalculator:
    """Calculates combat outcomes and displays results."""

    @staticmethod
    def calculate(attacker: Unit, defender: Unit, attacker_tile: HexTile,
                  defender_tile: HexTile) -> Dict:
        """Calculate combat odds and expected outcome."""
        # resolve_combat expects lists for armies; wrap single units
        result = resolve_combat(
            [attacker], [defender],
            defender_tile,  # defender's tile
            None, None,     # ruler params (not used for single-unit)
        )

        return {
            "attacker_win_chance": (100.0 if result.attacker_victory else 0.0),
            "attacker_loss_chance": (100.0 if result.defender_victory else 0.0),
            "defender_loss_chance": (100.0 if result.defender_victory else 0.0),
            "attacker_hp_after": result.attacker_hp_after,
            "defender_hp_after": result.defender_hp_after,
            "attacker_xp": result.attacker_xp,
            "defender_xp": result.defender_xp,
        }

    @staticmethod
    def display_combat_odds(result_dict: Dict) -> str:
        """Format combat odds for display."""
        r = result_dict
        return (
            f"Combat Odds:\n"
            f"  Attacker Win: {r['attacker_win_chance']:.1f}%\n"
            f"  Attacker Loss: {r['attacker_loss_chance']:.1f}%\n"
            f"  Defender Loss: {r['defender_loss_chance']:.1f}%\n"
            f"Attacker HP After: {r['attacker_hp_after']}\n"
            f"Defender HP After: {r['defender_hp_after']}\n"
            f"XP Gained: {r['attacker_xp']}"
        )


class BattleDisplayPanel(tk.Toplevel):
    """Shows a battle in progress with animated feedback."""

    def __init__(self, parent, attacker: Unit, defender: Unit,
                 attacker_pos: Tuple[int, int], defender_pos: Tuple[int, int]):
        super().__init__(parent)
        self.title("Battle!")
        self.geometry("400x300")
        self.configure(bg=BG)
        self.transient(parent)
        self.grab_set()
        self._build(attacker, defender, attacker_pos, defender_pos)

    def _build(self, attacker: Unit, defender: Unit,
               attacker_pos: Tuple[int, int], defender_pos: Tuple[int, int]):

        # Attacker side
        f1 = tk.Frame(self, bg=BG)
        f1.pack(fill=tk.X, pady=(10, 0))
        tk.Label(f1, text=f"⚔ {attacker.unit_type.name}\nAt ({attacker_pos[0]},{attacker_pos[1]})",
                 bg=BG, fg=HIGHLIGHT, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, expand=True)

        # VS
        tk.Label(self, text="VS", bg=BG, fg="#ffd700", font=("Segoe UI", 20, "bold")).pack(pady=10)

        # Defender side
        f2 = tk.Frame(self, bg=BG)
        f2.pack(fill=tk.X, pady=(0, 10))
        tk.Label(f2, text=f"🛡 {defender.unit_type.name}\nAt ({defender_pos[0]},{defender_pos[1]})",
                 bg=BG, fg=HIGHLIGHT, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, expand=True)


class CombatResultPanel(tk.Toplevel):
    """Shows the result of a completed combat."""

    def __init__(self, parent, result: CombatResult):
        super().__init__(parent)
        self.title("Combat Result")
        self.geometry("350x250")
        self.configure(bg=BG)
        self.transient(parent)
        self.grab_set()
        self._build(result)

    def _build(self, result: CombatResult):
        f = tk.Frame(self, bg=BG)
        f.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Result header
        if result.attacker_victory:
            icon = "⚔️ VICTORY! ⚔️"
            clr = "#4caf50"
        else:
            icon = "💀 DEFEAT 💀"
            clr = "#f44336"

        tk.Label(f, text=icon, bg=BG, fg=clr, font=("Segoe UI", 16, "bold")).pack(pady=10)

        # Details
        details = (
            f"Attacker HP: {result.attacker_hp_after}\n"
            f"Defender HP: {result.defender_hp_after}\n"
            f"Attacker XP: {result.attacker_xp}\n"
            f"Defender XP: {result.defender_xp}\n"
            f"Winner: {result.attacker_victory}"
        )
        tk.Label(f, text=details, bg=BG, fg=TEXT, font=("Segoe UI", 10),
                 wraplength=300, justify=tk.CENTER).pack(pady=10)

        tk.Button(f, text="OK", bg=ACCENT, fg=TEXT, command=self.destroy,
                  font=("Segoe UI", 10, "bold")).pack(pady=5)


class CombatUI:
    """Facade for combat UI components."""

    @staticmethod
    def show_battle(attacker: Unit, defender: Unit,
                    attacker_pos: Tuple[int, int], defender_pos: Tuple[int, int]):
        return BattleDisplayPanel(None, attacker, defender, attacker_pos, defender_pos)

    @staticmethod
    def show_result(result: CombatResult):
        return CombatResultPanel(None, result)

    @staticmethod
    def calculate_odds(attacker: Unit, defender: Unit,
                       attacker_tile: HexTile, defender_tile: HexTile) -> str:
        result_dict = CombatCalculator.calculate(attacker, defender, attacker_tile, defender_tile)
        return CombatCalculator.display_combat_odds(result_dict)
