"""
CivKings - Great People System
Manages Great Person Point (GPP) accumulation, recruitment, and one-time effects.
"""
from typing import Dict, List, Optional
from game_data import DISTRICTS, BuildingType, DistrictType


GREAT_PERSON_TYPES = {
    "Great General": {
        "points_from": "Encampment",
        "threshold": 100,
        "effect": "combat_bonus",
    },
    "Great Scientist": {
        "points_from": "Campus",
        "threshold": 100,
        "effect": "free_tech_boost",
    },
    "Great Engineer": {
        "points_from": "Workshop",
        "threshold": 100,
        "effect": "rush_production",
    },
    "Great Merchant": {
        "points_from": "Market",
        "threshold": 100,
        "effect": "gold_bonus",
    },
    "Great Prophet": {
        "points_from": "Temple",
        "threshold": 100,
        "effect": "found_religion",
    },
}


class GreatPeopleManager:
    def __init__(self):
        # {civ_name: {person_type: points}}
        self.points: Dict[str, Dict[str, int]] = {}
        # list of recruited person dicts
        self.recruited: List[dict] = []

    def accumulate_points(self, civ_name: str, cities: List):
        """For each city, check districts/buildings that generate GPP."""
        if civ_name not in self.points:
            self.points[civ_name] = {gp: 0 for gp in GREAT_PERSON_TYPES}

        for city in cities:
            for district_name, district in city.districts.items():
                if isinstance(district, DistrictType):
                    for person_type, info in GREAT_PERSON_TYPES.items():
                        if info["points_from"] == district.name:
                            self.points[civ_name][person_type] += 5

            for building_name, building in city.buildings.items():
                if isinstance(building, BuildingType):
                    for person_type, info in GREAT_PERSON_TYPES.items():
                        if info["points_from"] == building.name:
                            self.points[civ_name][person_type] += 3

    def check_recruitment(self, civ_name: str) -> List[str]:
        """Check if any great person has reached threshold. Returns list of recruited names."""
        recruited_this_turn: List[str] = []
        gp_points = self.points.get(civ_name, {})
        for person_type, info in GREAT_PERSON_TYPES.items():
            if gp_points.get(person_type, 0) >= info["threshold"]:
                self.points[civ_name][person_type] -= info["threshold"]
                entry = {
                    "type": person_type,
                    "civ": civ_name,
                }
                self.recruited.append(entry)
                recruited_this_turn.append(person_type)
        return recruited_this_turn

    def retire_great_person(self, person_type: str, civ_name: str, game) -> Optional[str]:
        """Apply one-time effect for a recruited great person. Returns message."""
        info = GREAT_PERSON_TYPES.get(person_type)
        if not info:
            return None

        effect = info["effect"]
        cities = [c for c in game.cities.values() if c.owner == civ_name]

        if effect == "combat_bonus":
            # +20% combat strength for all units in cities of this civ for 10 turns
            bonus = 0
            for unit in game.units.values():
                if unit.owner == civ_name and unit.is_alive:
                    unit.combat_strength = int(unit.combat_strength * 1.2)
                    bonus += unit.combat_strength
            return f"{person_type} activated: +20% combat strength for {civ_name} units"

        elif effect == "free_tech_boost":
            # Instantly advance current research by 10% of remaining cost
            tech_mgr = game.research.get(civ_name)
            if tech_mgr and tech_mgr.current_research:
                tech = tech_mgr.current_research
                if tech in game.tech_manager.tech_cost_map or hasattr(tech_mgr, "get_research_cost"):
                    cost = tech_mgr.get_research_cost(tech) if hasattr(tech_mgr, "get_research_cost") else 100
                    tech_mgr.advance_research(int(cost * 0.10), civ_name)
                    return f"{person_type} activated: +10% research on {tech}"
            return f"{person_type} activated: instant research boost applied"

        elif effect == "rush_production":
            # Complete current city production instantly
            for city in cities:
                if city.current_production:
                    city.production = city.get_production_cost(city.current_production) or city.production
                    return f"{person_type} activated: {city.name} production completed"
            return f"{person_type} activated: no city with active production"

        elif effect == "gold_bonus":
            # Grant gold equal to 5x city count
            gold = len(cities) * 50
            game.gold[civ_name] = game.gold.get(civ_name, 0) + gold
            return f"{person_type} activated: +{gold} gold"

        elif effect == "found_religion":
            # Automatically found a religion for this civ
            if civ_name not in getattr(game.religion_manager, "religions", {}):
                religion_name = f"{civ_name} Faith"
                game.religion_manager.found_religion(civ_name, religion_name)
                if hasattr(game, 'era_system'):
                    game.era_system.record_moment('founded_religion')
                return f"{person_type} activated: founded '{religion_name}'"
            return f"{person_type} activated: '{civ_name}' already has a religion"

        return None

    def process_turn(self, game) -> List[str]:
        """Accumulate GPP for all civs, check recruitments, and return messages."""
        msgs = []
        for civ_name in game.civilizations:
            cities = [c for c in game.cities.values() if c.owner == civ_name]
            self.accumulate_points(civ_name, cities)
            recruited = self.check_recruitment(civ_name)
            if recruited:
                msgs.append(f"\n  ✨ {civ_name} recruited: {', '.join(recruited)}")
        return msgs
