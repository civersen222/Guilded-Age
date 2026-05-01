"""
CivKings - Treaty, Casus Belli & Trade Agreement System
Handles advanced diplomacy mechanics
"""
import random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any


class TreatyType(Enum):
    """Types of treaties between civilizations."""
    DEFENSIVE_PACT = "Defensive Pact"       # Attack on one = war for all
    OPEN_BORDERS = "Open Borders"            # Free movement through territories
    JOINT_RESEARCH = "Joint Research"        # Shared science from researched techs
    NON_AGGRESSION = "Non-Aggression"        # Cannot declare war on each other
    ECONOMIC_PACT = "Economic Pact"          # Shared trade route income
    CULTURAL_EXCHANGE = "Cultural Exchange"  # Shared culture growth bonus
    JOINT_WAR = "Joint War"                  # Coordinated military campaign


class CasusBelliType(Enum):
    """Types of casus belli for declaring war."""
    LIBERATION = "Liberation"          # Liberate a vassal city
    BORDER_DISPUTE = "Border Dispute" # Disputed territory
    RELIGIOUS = "Religious"            # Spread heresy
    SPIES = "Spying"                   # Caught spying
    DEBT = "Debt"                      # Unpaid war reparations
    HONOR = "Honor"                    # Insult/diplomatic slight
    UNIFICATION = "Unification"        # Unite divided ethnic group
    RESOURCE = "Resource"              # Control of strategic resource
    PREEMPTIVE = "Preemptive"          # Prevent enemy buildup
    IDEOLOGICAL = "Ideological"        # Spread vs suppress ideology


class TreatyStatus(Enum):
    """Status of a treaty."""
    ACTIVE = "Active"
    EXPIRING = "Expiring"  # Less than 25% turns remaining
    EXPIRED = "Expired"
    BROKEN = "Broken"      # One party violated terms


@dataclass
class Treaty:
    """A treaty between two civilizations."""
    treaty_type: TreatyType
    civ_a: str
    civ_b: str
    turns_remaining: int
    max_turns: int
    status: TreatyStatus = TreatyStatus.ACTIVE
    terms: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'treaty_type': self.treaty_type.value,
            'civ_a': self.civ_a,
            'civ_b': self.civ_b,
            'turns_remaining': self.turns_remaining,
            'max_turns': self.max_turns,
            'status': self.status.value,
            'terms': self.terms,
        }
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Treaty':
        treaty = Treaty(
            treaty_type=TreatyType(d['treaty_type']),
            civ_a=d['civ_a'],
            civ_b=d['civ_b'],
            turns_remaining=d['turns_remaining'],
            max_turns=d['max_turns'],
            status=TreatyStatus(d['status']),
            terms=d.get('terms', {}),
        )
        return treaty
    
    def process_turn(self) -> bool:
        """Process one turn of the treaty. Returns True if still active."""
        self.turns_remaining -= 1
        if self.turns_remaining <= 0:
            self.status = TreatyStatus.EXPIRED
            return False
        elif self.turns_remaining <= self.max_turns * 0.25:
            self.status = TreatyStatus.EXPIRING
        return True
    
    def get_turns_remaining_str(self) -> str:
        if self.status == TreatyStatus.EXPIRED:
            return "Expired"
        elif self.status == TreatyStatus.BROKEN:
            return "Broken"
        return f"{self.turns_remaining} turns"


@dataclass
class CasusBelli:
    """A justification for declaring war."""
    cb_type: CasusBelliType
    target: str
    validity_turns: int
    strength_modifier: float  # How much this CB boosts war justification
    description: str
    
    def process_turn(self) -> bool:
        """Process one turn. Returns True if still valid."""
        self.validity_turns -= 1
        return self.validity_turns > 0


class CasusBelliManager:
    """Manages casus belli for declaring war."""
    
    # Base strength modifiers for each CB type
    CB_STRENGTH = {
        CasusBelliType.LIBERATION: 0.30,
        CasusBelliType.BORDER_DISPUTE: 0.15,
        CasusBelliType.RELIGIOUS: 0.25,
        CasusBelliType.SPIES: 0.20,
        CasusBelliType.DEBT: 0.10,
        CasusBelliType.HONOR: 0.05,
        CasusBelliType.UNIFICATION: 0.20,
        CasusBelliType.RESOURCE: 0.15,
        CasusBelliType.PREEMPTIVE: 0.10,
        CasusBelliType.IDEOLOGICAL: 0.25,
    }
    
    # Duration in turns for each CB type
    CB_DURATION = {
        CasusBelliType.LIBERATION: 20,
        CasusBelliType.BORDER_DISPUTE: 15,
        CasusBelliType.RELIGIOUS: 30,
        CasusBelliType.SPIES: 10,
        CasusBelliType.DEBT: 15,
        CasusBelliType.HONOR: 10,
        CasusBelliType.UNIFICATION: 25,
        CasusBelliType.RESOURCE: 20,
        CasusBelliType.PREEMPTIVE: 15,
        CasusBelliType.IDEOLOGICAL: 30,
    }
    
    # Descriptions for each CB type
    CB_DESCRIPTIONS = {
        CasusBelliType.LIBERATION: "Liberate the oppressed people of {target}",
        CasusBelliType.BORDER_DISPUTE: "Resolve the border dispute with {target}",
        CasusBelliType.RELIGIOUS: "Purge heretical influence from {target}",
        CasusBelliType.SPIES: "Retaliate for espionage by {target}",
        CasusBelliType.DEBT: "Collect unpaid war reparations from {target}",
        CasusBelliType.HONOR: "Restore honor insulted by {target}",
        CasusBelliType.UNIFICATION: "Unite the divided people of {target}",
        CasusBelliType.RESOURCE: "Secure control of vital resources from {target}",
        CasusBelliType.PREEMPTIVE: "Neutralize the growing threat of {target}",
        CasusBelliType.IDEOLOGICAL: "Suppress the dangerous ideology of {target}",
    }
    
    def __init__(self):
        self.active_cbs: Dict[str, CasusBelli] = {}  # (aggressor, target) -> CasusBelli
    
    def get_available_cbs(self, aggressor: str, target: str) -> List[CasusBelliType]:
        """Get available casus belli between two civs."""
        # Check if a CB already exists
        key = (aggressor, target)
        existing = self.active_cbs.get(key)
        if existing and existing.process_turn():
            return []
        
        # All CBs are theoretically available; filtering would require more context
        return list(CasusBelliType)
    
    def create_casus_belli(self, aggressor: str, target: str,
                           cb_type: CasusBelliType) -> CasusBelli:
        """Create a new casus belli."""
        cb = CasusBelli(
            cb_type=cb_type,
            target=target,
            validity_turns=self.CB_DURATION.get(cb_type, 15),
            strength_modifier=self.CB_STRENGTH.get(cb_type, 0.10),
            description=self.CB_DESCRIPTIONS.get(cb_type, f"War against {target}").format(target=target),
        )
        key = (aggressor, target)
        self.active_cbs[key] = cb
        return cb
    
    def has_valid_cb(self, aggressor: str, target: str) -> Optional[CasusBelli]:
        """Check if a valid casus belli exists."""
        key = (aggressor, target)
        cb = self.active_cbs.get(key)
        if cb and cb.process_turn():
            return cb
        return None
    
    def remove_casus_belli(self, aggressor: str, target: str):
        """Remove a casus belli (e.g., after peace treaty)."""
        key = (aggressor, target)
        self.active_cbs.pop(key, None)
    
    def get_cb_strength(self, aggressor: str, target: str) -> float:
        """Get the total strength modifier from all active CBs."""
        total = 0.0
        for (a, t), cb in self.active_cbs.items():
            if a == aggressor and t == target and cb.process_turn():
                total += cb.strength_modifier
        return total
    
    def process_all(self):
        """Process all active casus belli."""
        expired = []
        for key, cb in self.active_cbs.items():
            if not cb.process_turn():
                expired.append(key)
        for key in expired:
            del self.active_cbs[key]


class TradeAgreementManager:
    """Manages trade agreements between civilizations."""
    
    # Agreement types and their effects
    AGREEMENT_TYPES = {
        'gold': {
            'description': 'Direct gold payment',
            'base_income': 5,
            'scaling': 0.5,  # +0.5 gold per city pair
            'icon': '💰',
        },
        'resources': {
            'description': 'Shared resource access',
            'base_income': 3,
            'scaling': 0.3,
            'icon': '📦',
        },
        'science': {
            'description': 'Shared research',
            'base_income': 2,
            'scaling': 0.4,
            'icon': '🔬',
        },
        'culture': {
            'description': 'Cultural exchange',
            'base_income': 1,
            'scaling': 0.2,
            'icon': '🎨',
        },
        'military': {
            'description': 'Joint military training',
            'base_income': 0,
            'scaling': 0.0,
            'icon': '⚔️',
        },
    }
    
    def __init__(self):
        self.agreements: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.trade_routes: List[Dict[str, Any]] = []
    
    def create_agreement(self, civ_a: str, civ_b: str,
                         agreement_type: str = 'gold',
                         terms: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a trade agreement between two civs."""
        if agreement_type not in self.AGREEMENT_TYPES:
            raise ValueError(f"Unknown agreement type: {agreement_type}")
        
        pair = tuple(sorted([civ_a, civ_b]))
        
        agreement = {
            'type': agreement_type,
            'civ_a': civ_a,
            'civ_b': civ_b,
            'terms': terms or {},
            'turns_remaining': 50,
            'income_per_turn': self._calculate_income(agreement_type, civ_a, civ_b),
        }
        
        self.agreements[pair] = agreement
        return agreement
    
    def _calculate_income(self, agreement_type: str, civ_a: str, civ_b: str) -> float:
        """Calculate income from an agreement type."""
        agreement = self.AGREEMENT_TYPES.get(agreement_type, {})
        base = agreement.get('base_income', 0)
        scaling = agreement.get('scaling', 0)
        
        # Scale by number of cities each civ has
        # In a real implementation, you'd pass city counts
        return base + scaling * 10  # Simplified
    
    def get_income(self, civ: str) -> float:
        """Get total income from all agreements for a civ."""
        total = 0.0
        for pair, agreement in self.agreements.items():
            if civ in pair:
                total += agreement['income_per_turn']
        return total
    
    def process_turn(self):
        """Process one turn of trade agreements."""
        expired = []
        for pair, agreement in self.agreements.items():
            agreement['turns_remaining'] -= 1
            if agreement['turns_remaining'] <= 0:
                expired.append(pair)
        
        for pair in expired:
            del self.agreements[pair]
    
    def add_trade_route(self, civ: str, origin_city: str, destination_city: str,
                        destination_civ: str, route_type: str = 'gold') -> Dict[str, Any]:
        """Add a trade route between cities."""
        route = {
            'civ': civ,
            'origin_city': origin_city,
            'destination_city': destination_city,
            'destination_civ': destination_civ,
            'type': route_type,
            'income': self._get_route_income(route_type),
            'turns_remaining': 10,
        }
        self.trade_routes.append(route)
        return route
    
    def _get_route_income(self, route_type: str) -> float:
        """Get income multiplier for a route type."""
        multipliers = {
            'gold': 1.0,
            'resources': 0.8,
            'science': 1.2,
            'culture': 0.6,
        }
        return multipliers.get(route_type, 0.5)
    
    def get_trade_route_income(self, civ: str) -> float:
        """Get income from trade routes for a civ."""
        total = 0.0
        for route in self.trade_routes:
            if route['civ'] == civ:
                total += route['income']
        return total
    
    def process_trade_routes(self):
        """Process trade route expiration."""
        expired = []
        for i, route in enumerate(self.trade_routes):
            route['turns_remaining'] -= 1
            if route['turns_remaining'] <= 0:
                expired.append(i)
        
        for i in reversed(expired):
            self.trade_routes.pop(i)
    
    def cancel_agreement(self, civ_a: str, civ_b: str) -> bool:
        """Cancel a trade agreement."""
        pair = tuple(sorted([civ_a, civ_b]))
        if pair in self.agreements:
            del self.agreements[pair]
            return True
        return False
    
    def get_agreement_breakdown(self, civ: str) -> List[Dict[str, Any]]:
        """Get breakdown of all agreements for a civ."""
        breakdown = []
        for pair, agreement in self.agreements.items():
            if civ in pair:
                breakdown.append({
                    'partner': agreement['civ_b'] if agreement['civ_a'] == civ else agreement['civ_a'],
                    'type': agreement['type'],
                    'income': agreement['income_per_turn'],
                    'turns_remaining': agreement['turns_remaining'],
                })
        return breakdown


class DiplomacyManager:
    """Enhanced diplomacy manager combining treaties, CBs, and trade."""
    
    def __init__(self):
        self.treaties: Dict[Tuple[str, str], Treaty] = {}
        self.cb_manager = CasusBelliManager()
        self.trade_manager = TradeAgreementManager()
        self.relations: Dict[Tuple[str, str], int] = {}  # -100 to 100
        self.wars: Dict[str, List[str]] = {}
        self.alliances: Dict[str, List[str]] = {}
    
    def get_relation(self, civ_a: str, civ_b: str) -> int:
        """Get relation score."""
        pair = tuple(sorted([civ_a, civ_b]))
        return self.relations.get(pair, 0)
    
    def modify_relation(self, civ_a: str, civ_b: str, amount: int):
        """Modify relation score."""
        pair = tuple(sorted([civ_a, civ_b]))
        current = self.relations.get(pair, 0)
        self.relations[pair] = max(-100, min(100, current + amount))
    
    def sign_treaty(self, civ_a: str, civ_b: str,
                    treaty_type: TreatyType,
                    turns: int = 50,
                    terms: Optional[Dict[str, Any]] = None) -> Treaty:
        """Sign a treaty between two civs."""
        pair = tuple(sorted([civ_a, civ_b]))
        
        treaty = Treaty(
            treaty_type=treaty_type,
            civ_a=civ_a,
            civ_b=civ_b,
            turns_remaining=turns,
            max_turns=turns,
            terms=terms or {},
        )
        
        self.treaties[pair] = treaty
        
        # Apply treaty effects
        self.modify_relation(civ_a, civ_b, 15)
        
        if treaty_type == TreatyType.DEFENSIVE_PACT:
            # Add to alliances
            if civ_a not in self.alliances:
                self.alliances[civ_a] = []
            if civ_b not in self.alliances[civ_a]:
                self.alliances[civ_a].append(civ_b)
            
            if civ_b not in self.alliances:
                self.alliances[civ_b] = []
            if civ_a not in self.alliances[civ_b]:
                self.alliances[civ_b].append(civ_a)
        
        elif treaty_type == TreatyType.OPEN_BORDERS:
            # Grant free movement (handled in movement logic)
            pass
        
        elif treaty_type == TreatyType.JOINT_RESEARCH:
            # Shared science (handled in tech logic)
            pass
        
        return treaty
    
    def create_casus_belli(self, aggressor: str, target: str,
                           cb_type: CasusBelliType) -> CasusBelli:
        """Create a casus belli."""
        cb = self.cb_manager.create_casus_belli(aggressor, target, cb_type)
        self.modify_relation(aggressor, target, -10)
        return cb
    
    def has_valid_casus_belli(self, aggressor: str, target: str) -> bool:
        """Check if a valid casus belli exists."""
        return self.cb_manager.has_valid_cb(aggressor, target) is not None
    
    def get_casus_belli_strength(self, aggressor: str, target: str) -> float:
        """Get CB strength modifier."""
        return self.cb_manager.get_cb_strength(aggressor, target)
    
    def declare_war(self, aggressor: str, defender: str,
                    cb_type: Optional[CasusBelliType] = None) -> bool:
        """Declare war between two civs."""
        if self.is_at_war(aggressor, defender):
            return False
        
        # Create CB if provided
        if cb_type:
            self.create_casus_belli(aggressor, defender, cb_type)
        
        # Add to wars
        if aggressor not in self.wars:
            self.wars[aggressor] = []
        if defender not in self.wars[aggressor]:
            self.wars[aggressor].append(defender)
        
        if defender not in self.wars:
            self.wars[defender] = []
        if aggressor not in self.wars[defender]:
            self.wars[defender].append(aggressor)
        
        # Break relevant treaties
        self._break_treaties(aggressor, defender)
        
        self.modify_relation(aggressor, defender, -50)
        return True
    
    def _break_treaties(self, civ_a: str, civ_b: str):
        """Break treaties between warring civs."""
        for pair, treaty in self.treaties.items():
            if civ_a in pair and civ_b in pair:
                treaty.status = TreatyStatus.BROKEN
                if treaty.treaty_type == TreatyType.DEFENSIVE_PACT:
                    # Remove from alliances
                    if civ_a in self.alliances:
                        self.alliances[civ_a] = [
                            c for c in self.alliances[civ_a] if c != civ_b
                        ]
                    if civ_b in self.alliances:
                        self.alliances[civ_b] = [
                            c for c in self.alliances[civ_b] if c != civ_a
                        ]
    
    def make_pact(self, civ_a: str, civ_b: str, pact_type: str = "alliance"):
        """Create a diplomatic pact."""
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
    
    def is_at_war(self, civ_a: str, civ_b: str) -> bool:
        """Check if two civs are at war."""
        if civ_a in self.wars and civ_b in self.wars[civ_a]:
            return True
        if civ_b in self.wars and civ_a in self.wars[civ_b]:
            return True
        return False
    
    def is_allied(self, civ_a: str, civ_b: str) -> bool:
        """Check if two civs are allied."""
        if civ_a in self.alliances and civ_b in self.alliances[civ_a]:
            return True
        if civ_b in self.alliances and civ_a in self.alliances[civ_b]:
            return True
        return False
    
    def process_turn(self):
        """Process all diplomacy effects for a turn."""
        # Process treaties
        expired_treaties = []
        for pair, treaty in self.treaties.items():
            if not treaty.process_turn():
                expired_treaties.append(pair)
        
        for pair in expired_treaties:
            del self.treaties[pair]
        
        # Process casus belli
        self.cb_manager.process_all()
        
        # Process trade agreements
        self.trade_manager.process_turn()
        self.trade_manager.process_trade_routes()
    
    def get_active_wars(self, civ: str) -> List[str]:
        """Get list of civs at war with a civ."""
        return self.wars.get(civ, [])
    
    def get_active_alliances(self, civ: str) -> List[str]:
        """Get list of allied civs."""
        return self.alliances.get(civ, [])
    
    def get_trade_income(self, civ: str) -> float:
        """Get total trade income."""
        return (self.trade_manager.get_income(civ) +
                self.trade_manager.get_trade_route_income(civ))
