"""
CivKings - Diplomacy Management System
Handles relations, alliances, wars, and treaties between civilizations
"""
import random
from typing import Dict, List, Optional, Tuple


class DiplomacyManager:
    """Manages diplomatic relations between civilizations"""
    
    def __init__(self):
        self.relations: Dict[Tuple[str, str], int] = {}  # (civ_a, civ_b) -> relation score (-100 to 100)
        self.alliances: Dict[str, List[str]] = {}  # civ -> list of allied civs
        self.wars: Dict[str, List[str]] = {}  # civ -> list of warring civs
        self.truces: Dict[Tuple[str, str], int] = {}  # (civ_a, civ_b) -> turns remaining
        self.trade_agreements: Dict[Tuple[str, str], int] = {}  # (civ_a, civ_b) -> gold per turn
    
    def get_relation(self, civ_a: str, civ_b: str) -> int:
        """Get relation score between two civilizations"""
        pair = tuple(sorted([civ_a, civ_b]))
        return self.relations.get(pair, 0)
    
    def modify_relation(self, civ_a: str, civ_b: str, amount: int):
        """Modify relation score between two civilizations"""
        pair = tuple(sorted([civ_a, civ_b]))
        current = self.relations.get(pair, 0)
        self.relations[pair] = max(-100, min(100, current + amount))
    
    def declare_war(self, aggressor: str, defender: str):
        """Declare war between two civilizations"""
        if aggressor not in self.wars:
            self.wars[aggressor] = []
        if defender not in self.wars[aggressor]:
            self.wars[aggressor].append(defender)
        
        if defender not in self.wars:
            self.wars[defender] = []
        if aggressor not in self.wars[defender]:
            self.wars[defender].append(aggressor)
        
        self.modify_relation(aggressor, defender, -50)
    
    def make_pact(self, civ_a: str, civ_b: str, pact_type: str = "alliance"):
        """Create a diplomatic pact"""
        if pact_type == "alliance":
            if civ_a not in self.alliances:
                self.alliances[civ_a] = []
            if civ_b not in self.alliances[civ_a]:
                self.alliances[civ_a].append(civ_b)
            
            if civ_b not in self.alliances:
                self.alliances[civ_b] = []
            if civ_a not in self.alliances[civ_b]:
                self.alliances[civ_b].append(civ_a)
        
        self.modify_relation(civ_a, civ_b, 30)
    
    def sign_truce(self, civ_a: str, civ_b: str, turns: int = 10):
        """Sign a truce/peace treaty"""
        pair = tuple(sorted([civ_a, civ_b]))
        self.truces[pair] = turns
        self.modify_relation(civ_a, civ_b, 20)
    
    def sign_trade_agreement(self, civ_a: str, civ_b: str, gold_per_turn: int = 5):
        """Sign a trade agreement"""
        pair = tuple(sorted([civ_a, civ_b]))
        self.trade_agreements[pair] = gold_per_turn
    
    def process_truces(self):
        """Process truce expiration"""
        expired = []
        for pair, turns in self.truces.items():
            self.truces[pair] = turns - 1
            if self.truces[pair] <= 0:
                expired.append(pair)
        
        for pair in expired:
            del self.truces[pair]
    
    def is_at_war(self, civ_a: str, civ_b: str) -> bool:
        """Check if two civilizations are at war"""
        if civ_a in self.wars and civ_b in self.wars[civ_a]:
            return True
        if civ_b in self.wars and civ_a in self.wars[civ_b]:
            return True
        return False
    
    def is_allied(self, civ_a: str, civ_b: str) -> bool:
        """Check if two civilizations are allied"""
        if civ_a in self.alliances and civ_b in self.alliances[civ_a]:
            return True
        if civ_b in self.alliances and civ_a in self.alliances[civ_b]:
            return True
        return False
    
    def get_trade_income(self, civ: str) -> int:
        """Get gold income from trade agreements"""
        total = 0
        for pair, gold in self.trade_agreements.items():
            if civ in pair:
                total += gold
        return total
    
    def get_active_wars(self, civ: str) -> List[str]:
        """Get list of civilizations at war with a given civilization"""
        return self.wars.get(civ, [])
    
    def get_active_alliances(self, civ: str) -> List[str]:
        """Get list of allied civilizations"""
        return self.alliances.get(civ, [])
    
    def get(self, civ: str) -> Optional['DiplomacyRelation']:
        """Get diplomacy relation object for a civ (for UI compatibility)."""
        # Return a simple object with get_opinion for UI compatibility
        class DiplomacyRelation:
            def __init__(self, relations_dict, civ_name):
                self.relations = relations_dict
                self.civ_name = civ_name
            
            def get_opinion(self, other_civ):
                pair = tuple(sorted([self.civ_name, other_civ]))
                return self.relations.get(pair, 0)
        return DiplomacyRelation(self.relations, civ)
    
    def propose_peace(self, civ_a: str, civ_b: str) -> str:
        """Propose peace treaty between two civilizations"""
        self.sign_truce(civ_a, civ_b, 20)
        self.modify_relation(civ_a, civ_b, 10)
        return f"{civ_a} proposes peace to {civ_b}"
    
    def propose_alliance(self, civ_a: str, civ_b: str) -> str:
        """Propose alliance between two civilizations"""
        self.make_pact(civ_a, civ_b, "alliance")
        return f"{civ_a} proposes alliance to {civ_b}"
