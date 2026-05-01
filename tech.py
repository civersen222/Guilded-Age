"""
CivKings - Technology Management System
Handles technology tree, research, and era progression
"""
from typing import Dict, List, Optional, Set, Union
from game_data import TECHNOLOGIES, Technology, Era, TechBranch


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
