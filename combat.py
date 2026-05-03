"""
CivKings - Tactical Combat Resolver
Handles army-vs-army combat with terrain modifiers, ruler martial bonuses,
and casualty tracking.
"""
from __future__ import annotations

import random
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from hex_map import HexTile
from simulation import Character
from game_data import TerrainType, TERRAIN_DEFENSE_BONUS

if TYPE_CHECKING:
    from military import Unit

# Re-export CombatResult so callers can import from here
__all__ = ["Casualty", "CombatResult", "resolve_combat"]


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

    def __str__(self):
        lines = [self.description]
        if self.attacker_casualties:
            lines.append(f"  Attacker lost: {len(self.attacker_casualties)} unit(s)")
        if self.defender_casualties:
            lines.append(f"  Defender lost: {len(self.defender_casualties)} unit(s)")
        return "\n".join(lines)


def _terrain_defense_mod(tile: HexTile) -> float:
    """Return the defense multiplier from the defender's tile.
    
    Mountains give +50% defense (1.5x). Plains and most terrain give 0% (1.0x).
    """
    base = TERRAIN_DEFENSE_BONUS.get(tile.terrain, 0)
    return 1.0 + base / 100.0


def resolve_combat(
    attacker_army: List[Unit],
    defender_army: List[Unit],
    tile: HexTile,
    attacker_ruler: Character,
    defender_ruler: Character,
) -> CombatResult:
    """Resolve tactical combat between two armies.

    Formula:
        atk_power = Attack * Ruler_Martial_Bonus
        def_power = Defense * Terrain_Mod * Ruler_Martial_Bonus
        Damage = max(0, atk_power - def_power)

    - Terrain_Mod comes from the defender's tile (mountains +50%, plains 0%).
    - Ruler_Martial_Bonus = 1 + (ruler.martial / 100).
    - If calculated damage <= 0, the defender takes no damage and the
      attacker instead takes 0 damage (i.e. no wounds; the attacker's
      attack is simply negated).

    Returns a CombatResult summarizing casualties.
    """
    result = CombatResult()
    dmg_log: List[str] = []

    terrain_mod = _terrain_defense_mod(tile)
    att_ruler_bonus = 1.0 + attacker_ruler.get_effective_stat("martial") / 100.0
    def_ruler_bonus = 1.0 + defender_ruler.get_effective_stat("martial") / 100.0

    att_units = [u for u in attacker_army if u.is_alive]
    def_units = [u for u in defender_army if u.is_alive]

    while att_units and def_units:
        # Pick one unit from each side (randomized for variety)
        att = random.choice(att_units)
        def_ = random.choice(def_units)

        # Skip dead units that may have been removed mid-loop
        if not att.is_alive or not def_.is_alive:
            continue

        # Terrain bonus only applies to the defender (standard Civ-style)
        atk_power = att.get_stats()["attack"] * att_ruler_bonus
        def_power = def_.get_stats()["defense"] * terrain_mod * def_ruler_bonus

        raw_dmg_to_def = atk_power - def_power
        dmg_to_def = max(0, raw_dmg_to_def)

        # If defender's defense negates the attack completely, the attacker
        # takes no damage (no wound mechanic on negation).
        # If attack penetrates, defender takes full damage but attacker also
        # takes counter-damage = max(0, def_power - atk_power).
        raw_dmg_to_att = def_power - atk_power
        dmg_to_att = max(0, raw_dmg_to_att)

        # Use deal_damage() for proper death handling
        if dmg_to_def > 0:
            att.deal_damage(dmg_to_def)
        if dmg_to_att > 0:
            def_.deal_damage(dmg_to_att)

        # Clamp HP
        if att.hp < 0:
            att.hp = 0
        if def_.hp < 0:
            def_.hp = 0

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

    # Convenience attributes for single-unit combat (used by CombatUI)
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
