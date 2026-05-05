"""
CivKings - Technology Management System
Handles technology tree, research, and era progression
"""
from typing import Dict, List, Optional, Set, Union
from game_data import TECHNOLOGIES, Technology, Era, TechBranch


# Eureka conditions: maps tech name -> human-readable condition description
EUREKA_CONDITIONS: Dict[str, str] = {
    'Mining': 'Build a Quarry',
    'Sailing': 'Found a coastal city',
    'Archery': 'Kill a unit with a ranged unit',
    'Writing': 'Meet another civilization',
    'Bronze Working': 'Kill 3 enemy units',
    'Iron Working': 'Build a Barracks',
    'Currency': 'Establish a trade route',
    'Education': 'Build a Library',
}


class EurekaTracker:
    """Tracks eureka triggers that give 50% research discount on related technologies."""

    def __init__(self):
        self.triggered: Set[str] = set()

    def check_eureka(self, tech_name: str, game_context: Dict) -> bool:
        """Check if the eureka condition for a tech is met.
        If so, add 50% of the tech's cost as free progress to tech_manager
        and record the trigger. Returns True if triggered."""
        if tech_name in self.triggered:
            return False

        condition_text = EUREKA_CONDITIONS.get(tech_name)
        if not condition_text:
            return False

        # Evaluate condition against game_context
        met = self._evaluate_condition(tech_name, condition_text, game_context)
        if not met:
            return False

        # Trigger eureka: add 50% of cost as free progress
        tech = TECHNOLOGIES.get(tech_name)
        if tech:
            boost = tech.cost // 2
            tech_manager = game_context.get("tech_manager")
            if tech_manager:
                # If this tech is currently being researched, add progress directly
                if tech_manager.current_research == tech_name:
                    tech_manager.current_research_progress += boost
                    if tech_manager.current_research_progress >= tech.cost:
                        tech_manager.complete_research()
                # Otherwise add to science_pool as a general boost
                else:
                    tech_manager.science_pool += boost
            self.triggered.add(tech_name)
            print(f"⚡ Eureka! {tech_name} — {condition_text} → +{boost} research")
        return True

    def _evaluate_condition(self, tech_name: str, condition: str, ctx: Dict) -> bool:
        """Evaluate whether a condition is satisfied by the game context."""
        # Build-in checks using game_context keys
        if condition == 'Build a Quarry':
            return ctx.get("quarry_built", False)
        elif condition == 'Found a coastal city':
            return ctx.get("coastal_city_founded", False)
        elif condition == 'Kill a unit with a ranged unit':
            return ctx.get("ranged_kill", False)
        elif condition == 'Meet another civilization':
            return ctx.get("met_civilization", False)
        elif condition == 'Kill 3 enemy units':
            return ctx.get("enemy_kills", 0) >= 3
        elif condition == 'Build a Barracks':
            return ctx.get("barracks_built", False)
        elif condition == 'Establish a trade route':
            return ctx.get("trade_route_established", False)
        elif condition == 'Build a Library':
            return ctx.get("library_built", False)
        return False

    def get_status(self, tech_name: str) -> str:
        """Return 'triggered' or the condition text."""
        if tech_name in self.triggered:
            return "triggered"
        return EUREKA_CONDITIONS.get(tech_name, "Unknown")


class TechManager:
    """Manages technology research and progression"""
    
    def __init__(self):
        self.researched: Dict[str, Technology] = {}
        self.current_research: Optional[str] = None
        self.current_research_progress: int = 0
        self.science_pool: float = 0.0
    
    @property
    def unlocked_techs(self):
        """Alias for researched (set of unlocked tech names)"""
        return set(self.researched.keys())
    
    def get_available_technologies(self, civ: str) -> List[str]:
        """Get list of available technologies to research"""
        available = []
        for tech_name, tech in TECHNOLOGIES.items():
            if tech_name in self.researched:
                continue
            
            # Check prerequisites
            prereqs_met = True
            for prereq in tech.prerequisites:
                if prereq not in self.researched:
                    prereqs_met = False
                    break
            
            if prereqs_met:
                available.append(tech_name)
        
        return available
    
    def can_research(self, tech: Union[Technology, str]) -> bool:
        """Check if a technology can be researched right now"""
        if isinstance(tech, str):
            tech = TECHNOLOGIES.get(tech)
            if not tech:
                return False
        if tech.name in self.researched:
            return False
        for prereq in tech.prerequisites:
            if prereq not in self.researched:
                return False
        return True
    
    def get_cost(self, tech: Union[Technology, str]) -> int:
        """Get the research cost of a technology"""
        if isinstance(tech, str):
            tech = TECHNOLOGIES.get(tech)
            if not tech:
                return 0
        return tech.cost
    
    def research(self, tech_name: str, civ: str = ""):
        """Start researching a technology"""
        if tech_name in TECHNOLOGIES:
            self.current_research = tech_name
            self.current_research_progress = 0
            print(f"Started researching: {tech_name}")
    
    def add_research_progress(self, civ: str = "", amount: int = 0):
        """Add research progress toward current technology"""
        if self.current_research:
            self.current_research_progress += amount
            tech = TECHNOLOGIES[self.current_research]
            
            if self.current_research_progress >= tech.cost:
                self.complete_research()
    
    def complete_research(self):
        """Complete current research"""
        if self.current_research:
            tech = TECHNOLOGIES[self.current_research]
            self.researched[self.current_research] = tech
            self.science_pool += tech.cost // 2
            print(f"Researched: {self.current_research}")
            self.current_research = None
            self.current_research_progress = 0
    
    def auto_research(self, civ):
        """Automatically research the next available technology"""
        available = self.get_available_technologies(civ.name if hasattr(civ, 'name') else civ)
        if available:
            # Pick the one with lowest cost
            for tech_name in sorted(available, key=lambda t: TECHNOLOGIES[t].cost):
                tech = TECHNOLOGIES[tech_name]
                if self.science_pool >= tech.cost:
                    self.science_pool -= tech.cost
                    self.researched[tech_name] = tech
                    print(f"Auto-researched: {tech_name}")
                    self.complete_research()
                    break
    
    def reached_era(self, era: Era, civ: str = "") -> bool:
        """Check if a civilization has reached a specific era"""
        for tech in self.researched.values():
            if tech.era == era:
                return True
        return False
    
    def get_current_era(self, civ: str = "") -> Era:
        """Get the current era of a civilization"""
        max_era = Era.ANCIENT
        for tech in self.researched.values():
            if tech.era.value > max_era.value:
                max_era = tech.era
        return max_era
    
    def get_tech_bonus(self, civ: str = "", bonus_type: str = "production") -> float:
        """Get bonus from researched technologies"""
        total_bonus = 0.0
        for tech in self.researched.values():
            if bonus_type in tech.bonus.lower():
                total_bonus += 0.1
        return total_bonus
    
    def has_tech(self, tech_name: str) -> bool:
        """Check if a technology has been researched"""
        return tech_name in self.researched
    
    def get_technology_count(self) -> int:
        """Get number of researched technologies"""
        return len(self.researched)
    
    @property
    def researched_techs(self):
        """Get list of researched technologies (for UI compatibility)"""
        return list(self.researched.values())
    
    def get_available_techs(self):
        """Get available technologies to research (for UI compatibility)"""
        return [tech for tech_name, tech in TECHNOLOGIES.items() if tech_name not in self.researched]
    
    def start_research(self, tech):
        """Start researching a technology (for UI compatibility)"""
        if isinstance(tech, Technology):
            tech_name = tech.name
        else:
            tech_name = tech
        self.current_research = tech_name
        self.current_research_progress = 0
    
    def get_tech_tree_display(self) -> str:
        """Get a display of the tech tree (for UI compatibility)"""
        lines = ["\n=== Technology Tree ==="]
        lines.append(f"Researched: {', '.join(t.name for t in self.researched.values()) or 'None'}")
        available = self.get_available_techs()
        lines.append(f"Available: {', '.join(t.name for t in available[:10])}")
        if self.current_research:
            lines.append(f"Currently researching: {self.current_research}")
        return "\n".join(lines)
    
    # --- Additional attributes for tech_policies integration ---
    _current_turn: int = 0
    _districts: Dict[str, int] = {}
    _policies: List = []
    
    def _get_district_count(self, district_type: str) -> int:
        """Get count of a specific district type."""
        return self._districts.get(district_type, 0)
    
    def _get_war_count(self) -> int:
        """Get number of cities currently at war."""
        return 0  # Placeholder - depends on diplomacy integration
    
    def _get_trade_route_count(self) -> int:
        """Get number of active trade routes."""
        return len(self._trade_routes) if hasattr(self, '_trade_routes') else 0
    
    def _get_total_culture(self) -> int:
        """Get total culture points."""
        return self._culture if hasattr(self, '_culture') else 0
    
    def _get_production_to_science_ratio(self) -> float:
        """Get the ratio of production being converted to science."""
        return self._prod_to_science_ratio if hasattr(self, '_prod_to_science_ratio') else 0.0
