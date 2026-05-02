"""
CivKings - Religion Management System
Handles religions, faith, holy sites, and religious mechanics
"""
from typing import Dict, List, Optional, Tuple
import random


class Religion:
    """Represents a religion"""
    
    def __init__(self, name: str, founder: str):
        self.name = name
        self.founder = founder
        self.followers: Dict[str, int] = {}  # civ -> number of followers
        self.doctrines: List[str] = []
        self.holy_sites: List[Tuple[int, int]] = []
    
    def add_followers(self, civ: str, count: int):
        """Add followers to a civilization"""
        self.followers[civ] = self.followers.get(civ, 0) + count
    
    def get_followers_count(self) -> int:
        """Get total followers"""
        return sum(self.followers.values())


class ReligionManager:
    """Manages religions and faith"""
    
    def __init__(self):
        self.religions: Dict[str, Religion] = {}
        self.active_religion: Optional[str] = None
        self.faith: Dict[str, int] = {}  # civ -> faith
        self.holy_sites: List[Tuple[str, Tuple[int, int]]] = []  # (religion, position)
    
    def found_religion(self, name: str, founder: str, doctrines: List[str] = None) -> Religion:
        """Found a new religion"""
        religion = Religion(name, founder)
        if doctrines:
            religion.doctrines = doctrines
        self.religions[name] = religion
        self.active_religion = name
        self.faith[founder] = 0
        return religion
    
    def spread_religion(self, religion_name: str, target_civ: str, amount: int = 10):
        """Spread religion to a civilization"""
        if religion_name in self.religions:
            religion = self.religions[religion_name]
            religion.add_followers(target_civ, amount)
            self.faith[target_civ] = self.faith.get(target_civ, 0) + amount
    
    def add_faith(self, civ: str, amount: int):
        """Add faith to a civilization"""
        self.faith[civ] = self.faith.get(civ, 0) + amount
    
    def spend_faith(self, civ: str, amount: int) -> bool:
        """Spend faith, returns True if successful"""
        if self.faith.get(civ, 0) >= amount:
            self.faith[civ] -= amount
            return True
        return False
    
    def add_holy_site(self, religion_name: str, position: Tuple[int, int]):
        """Add a holy site to a religion"""
        if religion_name in self.religions:
            self.holy_sites.append((religion_name, position))
    
    def get_faith_income(self, civ: str) -> int:
        """Get faith income for a civilization"""
        income = 5  # Base faith
        # Add bonus from holy sites
        for religion, _ in self.holy_sites:
            if religion in self.religions:
                if civ in self.religions[religion].followers:
                    income += 3
        return income
    
    def get_religious_bonus(self, civ: str, bonus_type: str = "happiness") -> float:
        """Get religious bonus for a civilization"""
        total_bonus = 0.0
        for religion in self.religions.values():
            if civ in religion.followers:
                if bonus_type == "happiness":
                    total_bonus += 0.1  # 10% happiness bonus per religion
                elif bonus_type == "legitimacy":
                    total_bonus += 0.05  # 5% legitimacy bonus
        return total_bonus
    
    def get_active_religion(self) -> Optional[Religion]:
        """Get the active religion"""
        if self.active_religion and self.active_religion in self.religions:
            return self.religions[self.active_religion]
        return None
    
    def check_heresy(self, civ: str) -> bool:
        """Check if a civilization practices heresy (multiple religions)"""
        religion_count = 0
        for religion in self.religions.values():
            if civ in religion.followers:
                religion_count += 1
        return religion_count > 1
