"""
CivKings - Tactical Combat Resolver
Handles army-vs-army combat with terrain modifiers, ruler martial bonuses,
casualty tracking, flanking, counters, ranged combat, fortification,
and combat preview.
"""
from __future__ import annotations

import math
import random
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from hex_map import HexTile
from simulation import Character
from game_data import TerrainType, TERRAIN_DEFENSE_BONUS, UNIT_TYPES, UnitCategory

if TYPE_CHECKING:
    from military import Unit

# Re-export CombatResult so callers can import from here
__all__ = ["Casualty", "CombatResult", "resolve_combat", "preview_combat"]

# ── Counter Bonuses ──────────────────────────────────────────────────────────
# {unit_type: {counter_type: bonus_percent}}
COUNTER_BONUSES: Dict[str, Dict[str, int]] = {
    "Spearman": {"Cavalry": 10},
    "Archer": {"Infantry": 5},
    "Cavalry": {"Archer": 5, "Siege": 10},
}

# Map unit type names to category keywords for counter matching
UNIT_CATEGORY_MAP: Dict[str, UnitCategory] = {}
for _name, _utype in UNIT_TYPES.items():
    UNIT_CATEGORY_MAP[_name] = _utype.category

HEX_OFFSETS = [
    (1, 0), (1, -1), (0, -1),
    (-1, 0), (-1, 1), (0, 1),
]


# ── Casualties & Result ──────────────────────────────────────────────────────

class Casualty:
    """Records a unit lost in combat."""

    def __init__(self, unit: "Unit", side: str):
        self.unit = unit
        self.side = side  # "attacker" or "defender"
        self.damage_dealt = 0
        self.damage_taken = 0

    def __repr__(self):
        return (
            f"Casualty({self.unit.unit_type}, {self.side}, "
            f"took={self.damage_taken}, dealt={self.damage_dealt})"
        )


class CombatResult:
    """Summary of a combat engagement."""

    def __init__(self):
        self.attacker_casualties: List[Casualty] = []
        self.defender_casualties: List[Casualty] = []
        self.attacker_remaining_hp: List[int] = []
        self.defender_remaining_hp: List[int] = []
        self.description = ""
        # Single-unit combat convenience attributes
        self.attacker_hp_after = 0
        self.defender_hp_after = 0
        self.attacker_xp = 0
        self.defender_xp = 0
        self.attacker_victory = False
        self.defender_victory = False
        self.bonuses_applied: Dict[str, int] = {}

    def __str__(self):
        lines = [self.description]
        if self.bonuses_applied:
            lines.append(f"  Bonuses: {', '.join(f'{k}+{v}' for k, v in self.bonuses_applied.items())}")
        if self.attacker_casualties:
            lines.append(f"  Attacker lost: {len(self.attacker_casualties)} unit(s)")
        if self.defender_casualties:
            lines.append(f"  Defender lost: {len(self.defender_casualties)} unit(s)")
        return "\n".join(lines)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _terrain_defense_mod(tile: HexTile) -> float:
    """Return the defense multiplier from the defender's tile."""
    base = TERRAIN_DEFENSE_BONUS.get(tile.terrain, 0)
    return 1.0 + base / 100.0


def _hex_neighbors(pos: tuple) -> List[tuple]:
    """Return the 6 hex neighbors of a position."""
    q, r = pos
    return [(q + dq, r + dr) for dq, dr in HEX_OFFSETS]


def _get_unit_at_position(units: List["Unit"], pos: tuple) -> Optional["Unit"]:
    """Get a living unit at a given position."""
    for u in units:
        if u.is_alive and u.position == pos:
            return u
    return None


def calculate_flanking(
    attacker_pos: tuple,
    defender_pos: tuple,
    friendly_units: List["Unit"],
) -> int:
    """Calculate flanking bonus for the attacker.

    +2 per friendly unit adjacent to the defender (max +12).
    The attacker itself is excluded.
    """
    adj_positions = set(_hex_neighbors(defender_pos))
    count = 0
    for unit in friendly_units:
        if unit.is_alive and unit.position != attacker_pos and unit.position in adj_positions:
            count += 1
    return min(count * 2, 12)


def _get_counter_bonus(attacker: "Unit", defender: "Unit") -> int:
    """Return counter bonus percentage if attacker counters defender's category."""
    atk_type = attacker.unit_type
    def_category = UNIT_CATEGORY_MAP.get(defender.unit_type, UnitCategory.MELEE)
    counters = COUNTER_BONUSES.get(atk_type, {})
    for counter_key, bonus in counters.items():
        counter_cat = getattr(UnitCategory, counter_key.upper(), None)
        if counter_cat and def_category == counter_cat:
            return bonus
    return 0


# ── Resolve Combat ───────────────────────────────────────────────────────────

def resolve_combat(
    attacker_army: List[Unit],
    defender_army: List[Unit],
    tile: HexTile,
    attacker_ruler: Character,
    defender_ruler: Character,
) -> CombatResult:
    """Resolve tactical combat between two armies.

    Formula:
        atk_power = Attack * (1 + counter_bonus/100) * Ruler_Martial_Bonus
        def_power = Defense * Terrain_Mod * (1 + fort_bonus) * Ruler_Martial_Bonus
        Damage = max(0, atk_power - def_power)

    Features:
        - Counter bonuses (COUNTER_BONUSES)
        - Flanking (+2 per adjacent friendly unit, max +12)
        - Ranged units deal damage without taking return damage
        - Fortified defenders get +3 (1st turn) or +6 (2+ turns) defense
    """
    result = CombatResult()
    dmg_log: List[str] = []

    terrain_mod = _terrain_defense_mod(tile)
    att_ruler_bonus = 1.0 + attacker_ruler.get_effective_stat("martial") / 100.0
    def_ruler_bonus = 1.0 + defender_ruler.get_effective_stat("martial") / 100.0

    att_units = [u for u in attacker_army if u.is_alive]
    def_units = [u for u in defender_army if u.is_alive]

    while att_units and def_units:
        att = random.choice(att_units)
        def_ = random.choice(def_units)

        if not att.is_alive or not def_.is_alive:
            continue

        # ── Calculate attacker power ──
        atk_power = att.attack * att_ruler_bonus
        bonuses: Dict[str, int] = {}

        # Counter bonus
        counter_bonus = _get_counter_bonus(att, def_)
        if counter_bonus > 0:
            atk_power *= (1 + counter_bonus / 100.0)
            bonuses[f"counter({att.unit_type} vs {def_.unit_type})"] = counter_bonus

        # Flanking bonus
        flank = calculate_flanking(att.position, def_.position, att_units)
        if flank > 0:
            atk_power *= (1 + flank / 100.0)
            bonuses[f"flanking"] = flank

        # ── Calculate defender power ──
        def_power = def_.defense * terrain_mod * def_ruler_bonus

        # Fortification bonus
        if def_.is_fortified:
            fort_turns = getattr(def_, "_fortify_turns", 0)
            if fort_turns >= 1:
                def_power *= 1.06  # +6% defense for 2+ turns
                bonuses["fortified(2+)"] = 6
            else:
                def_power *= 1.03  # +3% defense for 1st turn
                bonuses["fortified(1)"] = 3

        # ── Determine damage ──
        def_is_ranged = UNIT_CATEGORY_MAP.get(def_.unit_type) == UnitCategory.RANGED
        att_is_ranged = UNIT_CATEGORY_MAP.get(att.unit_type) == UnitCategory.RANGED

        raw_dmg_to_def = atk_power - def_power
        dmg_to_def = max(0, raw_dmg_to_def)

        if def_is_ranged:
            # Ranged defender deals no counter-damage
            dmg_to_att = 0
        elif att_is_ranged:
            # Ranged attacker takes no counter-damage
            dmg_to_att = 0
        else:
            raw_dmg_to_att = def_power - atk_power
            dmg_to_att = max(0, raw_dmg_to_att)

        # Apply damage
        if dmg_to_def > 0:
            att.deal_damage(dmg_to_def)
        if dmg_to_att > 0:
            def_.deal_damage(dmg_to_att)

        att.hp = max(0, att.hp)
        def_.hp = max(0, def_.hp)

        # Record casualties
        att.casualty = Casualty(att, "attacker")
        att.casualty.damage_dealt = dmg_to_def
        att.casualty.damage_taken = dmg_to_att
        def_.casualty = Casualty(def_, "defender")
        def_.casualty.damage_dealt = dmg_to_att
        def_.casualty.damage_taken = dmg_to_def

        if att.hp <= 0:
            att.is_alive = False
            result.attacker_casualties.append(att.casualty)
            att_units.remove(att)

        if def_.hp <= 0:
            def_.is_alive = False
            result.defender_casualties.append(def_.casualty)
            def_units.remove(def_)

        dmg_log.append(
            f"  {att.unit_type} vs {def_.unit_type}: "
            f"Attacker dealt {dmg_to_def:.0f} dmg, Defender dealt {dmg_to_att:.0f} dmg"
        )

    # Record remaining HP
    for u in attacker_army:
        if u.is_alive:
            result.attacker_remaining_hp.append(u.hp)
    for u in defender_army:
        if u.is_alive:
            result.defender_remaining_hp.append(u.hp)

    # Single-unit convenience
    if attacker_army:
        alive = [u for u in attacker_army if u.is_alive]
        result.attacker_hp_after = alive[-1].hp if alive else 0
        result.attacker_xp = alive[-1].xp
        result.attacker_victory = not any(u.is_alive for u in defender_army)
    if defender_army:
        alive = [u for u in defender_army if u.is_alive]
        result.defender_hp_after = alive[-1].hp if alive else 0
        result.defender_xp = alive[-1].xp
        result.defender_victory = not any(u.is_alive for u in attacker_army)

    result.bonuses_applied = bonuses

    if result.attacker_casualties:
        total_att_dmg = sum(c.damage_dealt for c in result.attacker_casualties)
        total_def_dmg = sum(c.damage_dealt for c in result.defender_casualties)
        result.description = (
            f"Combat ended: Attacker dealt {total_att_dmg:.0f} total damage, "
            f"Defender dealt {total_def_dmg:.0f} total damage."
        )
    else:
        result.description = "Combat ended with no casualties."

    return result


# ── Combat Preview ───────────────────────────────────────────────────────────

def preview_combat(
    attacker: "Unit",
    defender: "Unit",
    tile: HexTile,
    friendly_units: Optional[List["Unit"]] = None,
    defender_fortified: bool = False,
) -> Dict:
    """Predict combat outcome without modifying any state.

    Returns:
        {
            "attacker_strength": float,
            "defender_strength": float,
            "estimated_damage": float,
            "attacker_win_chance": float,
            "defender_win_chance": float,
            "bonuses": dict,
        }
    """
    friendly_units = friendly_units or []
    terrain_mod = _terrain_defense_mod(tile)
    bonuses: Dict[str, int] = {}

    # Counter bonus
    counter_bonus = _get_counter_bonus(attacker, defender)
    if counter_bonus > 0:
        bonuses[f"counter({attacker.unit_type} vs {defender.unit_type})"] = counter_bonus

    # Flanking bonus
    flank = calculate_flanking(attacker.position, defender.position, friendly_units)
    if flank > 0:
        bonuses[f"flanking"] = flank

    # Fortification
    if defender_fortified:
        bonuses["fortified"] = 3

    # Calculate effective strengths
    atk_power = attacker.attack * (1 + counter_bonus / 100.0) * (1 + flank / 100.0)
    def_mult = 1.03 if defender_fortified else 1.0
    def_power = defender.defense * terrain_mod * def_mult

    # Estimated net damage (attacker vs defender)
    estimated_damage = max(0, atk_power - def_power)

    # Simulate ~1000 combat rounds for win probability
    att_wins = 0
    for _ in range(1000):
        rng = random.randint(-10, 10)
        sim_atk = atk_power + rng
        rng2 = random.randint(-10, 10)
        sim_def = def_power + rng2
        if sim_atk > sim_def:
            att_wins += 1

    win_chance = att_wins / 1000.0

    return {
        "attacker_strength": round(atk_power, 2),
        "defender_strength": round(def_power, 2),
        "estimated_damage": round(estimated_damage, 2),
        "attacker_win_chance": round(win_chance, 4),
        "defender_win_chance": round(1 - win_chance, 4),
        "bonuses": bonuses,
    }
