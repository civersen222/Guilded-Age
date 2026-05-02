"""AI opponent logic: expansion, research, military strategy, diplomacy."""

from typing import Dict, List, Optional, Tuple, Set
import random
from game_data import TECHNOLOGIES, TechBranch, Era, CIVILIZATIONS, UnitCategory, UnitType
from court import Court, CourtPosition
from diplomacy_extended import TreatyType, CasusBelliType


class AIPlayer:
    """Simulates an opponent civilization's decisions with strategic depth."""

    def __init__(self, civ_name: str, difficulty: str = "medium"):
        self.civ = CIVILIZATIONS.get(civ_name, CIVILIZATIONS["Rome"])
        self.difficulty = difficulty
        self.aggression: float = self._set_aggression()
        self.priorities: Dict[str, float] = {
            "military": 0.0,
            "science": 0.0,
            "economy": 0.0,
            "expansion": 0.0,
        }
        self._set_priorities()
        self.target_research: Optional[str] = None
        self.last_action: str = "idle"
        
        # Enhanced state tracking
        self.known_enemy_strength: Dict[str, int] = {}  # civ_name -> strength
        self.known_enemy_tech: Dict[str, List[str]] = {}  # civ_name -> tech list
        self.war_targets: List[str] = []  # civs we're considering attacking
        self.trade_partners: Set[str] = set()  # civs we trade with
        self.allied_civs: Set[str] = set()  # civs we're allied with
        self.city_expansion_history: List[Tuple[int, int]] = []  # (turn, cities_count)
        self.military_build_history: List[Tuple[int, str]] = []  # (turn, unit_type)
        self.research_path: List[str] = []  # techs we've researched in order
        
        # Treaty & diplomacy state
        self.active_treaties: Dict[str, Dict[str, any]] = {}  # target_civ -> treaty info
        self.desired_cb_types: Dict[str, CasusBelliType] = {}  # target_civ -> preferred CB
        self.diplomacy_history: List[Dict[str, str]] = []  # log of diplomatic actions
        
        # Strategic preferences
        self.preferred_era: Optional[Era] = None
        self.preferred_branch: Optional[TechBranch] = None
        self.aggression_modifiers: List[Tuple[str, float]] = []  # (source, modifier)
        self.trust_level: Dict[str, float] = {}  # civ_name -> trust (-100 to 100)
        self.grudges: Dict[str, int] = {}  # civ_name -> number of broken promises

    def _set_aggression(self) -> float:
        levels = {"easy": 0.2, "medium": 0.5, "hard": 0.8}
        return levels.get(self.difficulty, 0.5)

    def _set_priorities(self):
        if self.difficulty == "easy":
            self.priorities = {"military": 0.2, "science": 0.3, "economy": 0.3, "expansion": 0.2}
        elif self.difficulty == "medium":
            self.priorities = {"military": 0.4, "science": 0.3, "economy": 0.2, "expansion": 0.1}
        else:
            self.priorities = {"military": 0.6, "science": 0.2, "economy": 0.1, "expansion": 0.1}

    def decide_next_action(self, current_tech: List[str], cities_count: int,
                           military_strength: int, available_gold: float) -> Dict[str, any]:
        """AI decides what to do this turn. Returns action dict."""
        action = {
            "type": "research",
            "target": None,
            "build": None,
            "expand": False,
            "attack": False,
            "diplo_action": None,
        }

        # Decide research priority
        action["type"] = self._choose_research_priority(current_tech)

        # Decide production
        if self.priorities["military"] > 0.4 and military_strength < 50:
            action["build"] = self._choose_military_unit()
        elif self.priorities["economy"] > 0.3:
            action["build"] = "Worker"
        elif self.priorities["expansion"] > 0.3 and cities_count < 5:
            action["expand"] = True
            action["build"] = "Settler"

        # Decide military action
        if random.random() < self.aggression and military_strength > 30:
            action["attack"] = True

        # Decide diplomacy
        if self.aggression < 0.3:
            action["diplo_action"] = random.choice(["form_alliance", "trade"])
        elif self.aggression > 0.7:
            action["diplo_action"] = random.choice(["declare_war", "demand_tribute"])

        self.last_action = action["type"]
        return action

    def _choose_research_priority(self, current_tech: List[str]) -> str:
        """Choose research priority based on strategy and current game state."""
        # If we have military tech and high priorities, focus military
        if self.priorities["military"] > 0.5:
            military_techs = [t for t in TECHNOLOGIES.values() 
                            if t.branch == TechBranch.MILITARY 
                            and t.name not in current_tech]
            if military_techs:
                return "military"
        
        # If we have science tech and high priorities, focus science
        if self.priorities["science"] > 0.4:
            science_techs = [t for t in TECHNOLOGIES.values() 
                           if t.branch == TechBranch.SCIENTIFIC 
                           and t.name not in current_tech]
            if science_techs:
                return "science"
        
        # Economy focus with civic tech
        if self.priorities["economy"] > 0.3:
            civic_techs = [t for t in TECHNOLOGIES.values() 
                         if t.branch == TechBranch.CIVIC 
                         and t.name not in current_tech]
            if civic_techs:
                return "economy"
        
        # Fallback: check what would unlock the most new options
        best_tech = None
        best_unlock_count = 0
        for tech_name in current_tech:
            if tech_name in TECHNOLOGIES:
                tech = TECHNOLOGIES[tech_name]
                unlock_count = sum(1 for t in TECHNOLOGIES.values() 
                                 if tech_name in t.prerequisites 
                                 and t.name not in current_tech)
                if unlock_count > best_unlock_count:
                    best_unlock_count = unlock_count
                    best_tech = tech_name
        
        if best_tech:
            return TECHNOLOGIES[best_tech].branch.name.lower()
        
        return "science"

    def _choose_military_unit(self) -> str:
        """Choose military unit based on current threats and era."""
        units_by_category = {
            "infantry": ["Swordsman", "Legion", "Longswordsman"],
            "archery": ["Archer", "Crossbowman", "Arbalest"],
            "cavalry": ["Knight", "Paladin", "Chivalry"],
            "siege": ["Siege Tower", "Trebuchet", "Catapult"],
            "naval": ["Galley", "Trireme", "Dromon"],
        }
        
        # Check era for available units
        era_units = {
            Era.ANCIENT: ["Swordsman", "Archer"],
            Era.CLASSICAL: ["Swordsman", "Archer", "Knight"],
            Era.MEDIEVAL: ["Swordsman", "Archer", "Knight", "Siege Tower"],
            Era.RENAISSANCE: ["Swordsman", "Archer", "Knight", "Siege Tower", "Galley"],
            Era.INDUSTRIAL: ["Swordsman", "Archer", "Knight", "Siege Tower", "Galley"],
            Era.MODERN: ["Swordsman", "Archer", "Knight", "Siege Tower", "Galley"],
        }
        
        # If we have naval tech, prefer naval units
        if "Naval Tradition" in self.research_path or "Maritime Law" in self.research_path:
            return random.choice(units_by_category["naval"])
        
        # If we're under threat, prefer counter-units
        for enemy, strength in self.known_enemy_strength.items():
            if strength > 40:
                # Enemy has strong cavalry, build counter
                return "Archer"
        
        # Default: mix of infantry and archery
        return random.choice(units_by_category["infantry"] + units_by_category["archery"])

    def _choose_city_expansion_target(self, available_tiles: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        """Choose best location for new city based on resources and terrain."""
        if not available_tiles:
            return None
        
        # Score each tile
        best_tile = None
        best_score = -1
        
        for tile in available_tiles:
            score = 0
            
            # Prefer tiles near fresh water
            score += 2
            
            # Prefer tiles with resources
            score += 3
            
            # Prefer tiles with defensible terrain
            score += 1
            
            # Prefer tiles near existing cities (for connectivity)
            score += 0.5
            
            if score > best_score:
                best_score = score
                best_tile = tile
        
        return best_tile

    def evaluate_military_strength(self, cities_count: int, military_strength: int) -> str:
        """Evaluate military strength relative to cities."""
        strength_per_city = military_strength / max(cities_count, 1)
        
        if strength_per_city < 10:
            return "weak"  # Needs military buildup
        elif strength_per_city < 20:
            return "adequate"  # Can defend but not expand
        else:
            return "strong"  # Can expand aggressively

    def adjust_priorities_for_strategy(self, current_tech: List[str], cities_count: int, 
                                       military_strength: int, available_gold: float) -> Dict[str, float]:
        """Dynamically adjust priorities based on current game state."""
        adjusted = self.priorities.copy()
        
        # If we're weak militarily, increase military priority
        if self.evaluate_military_strength(cities_count, military_strength) == "weak":
            adjusted["military"] += 0.2
            adjusted["economy"] -= 0.1
        
        # If we have many cities, focus on economy to support them
        if cities_count > 5:
            adjusted["economy"] += 0.1
            adjusted["expansion"] -= 0.1
        
        # If we have enough gold for research, boost science
        if available_gold > 100:
            adjusted["science"] += 0.1
        
        # If we're close to era advancement, boost research
        if "Advanced Mathematics" in current_tech:
            adjusted["science"] += 0.15
        
        # Normalize priorities
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v/total for k, v in adjusted.items()}
        
        return adjusted

    def decide_next_action(self, current_tech: List[str], cities_count: int,
                           military_strength: int, available_gold: float,
                           available_tiles: List[Tuple[int, int]] = None) -> Dict[str, any]:
        """AI decides what to do this turn with strategic depth."""
        action = {
            "type": "research",
            "target": None,
            "build": None,
            "expand": False,
            "attack": False,
            "diplo_action": None,
            "diplo_target": None,
            "target_tile": None,
        }

        # Dynamically adjust priorities based on game state
        adjusted_priorities = self.adjust_priorities_for_strategy(
            current_tech, cities_count, military_strength, available_gold
        )

        # Decide research priority
        action["type"] = self._choose_research_priority(current_tech)

        # Decide production with strategic context
        military_strength_per_city = self.evaluate_military_strength(cities_count, military_strength)
        
        if adjusted_priorities["military"] > 0.4 or military_strength_per_city == "weak":
            action["build"] = self._choose_military_unit()
        elif adjusted_priorities["economy"] > 0.3:
            action["build"] = "Worker"
        elif adjusted_priorities["expansion"] > 0.2 and cities_count < 8:
            if available_tiles:
                action["expand"] = True
                action["target_tile"] = self._choose_city_expansion_target(available_tiles)
                action["build"] = "Settler"

        # Decide military action with threat assessment
        if military_strength > 40:
            # Check for weak neighbors
            for enemy, strength in list(self.known_enemy_strength.items()):
                if strength < military_strength * 0.7 and self.aggression > 0.5:
                    action["attack"] = True
                    action["diplo_target"] = enemy
                    break
        
        # Enhanced diplomacy decision-making
        diplomacy_context = {
            "our_strength": military_strength,
            "gold_surplus": available_gold,
            "has_spy_intel": False,
            "border_dispute": False,
            "unpaid_debt": False,
            "religious_conflict": False,
            "resource_control": False,
            "divided_ethnicity": False,
            "common_enemy": None,
        }
        
        # Evaluate diplomatic actions for each known civ
        for civ_name, civ_strength in self.known_enemy_strength.items():
            diplo_action = self.decide_diplomatic_action(civ_name, diplomacy_context)
            if diplo_action:
                action["diplo_action"] = diplo_action["action"]
                action["diplo_target"] = diplo_action["target"]
                if "casus_belli" in diplo_action:
                    action["casus_belli"] = diplo_action["casus_belli"]
                if "offer" in diplo_action:
                    action["trade_offer"] = diplo_action["offer"]
                break  # One diplomatic action per turn
        
        # Fallback diplomacy based on aggression if no targeted action
        if not action["diplo_action"]:
            if self.aggression < 0.3:
                action["diplo_action"] = random.choice(["form_alliance", "trade"])
            elif self.aggression > 0.7:
                action["diplo_action"] = random.choice(["declare_war", "demand_tribute"])
            else:
                action["diplo_action"] = random.choice(["trade", "alliance", "non_aggression_pact"])

        # Track research path
        if action["type"] == "research" and action["target"]:
            self.research_path.append(action["target"])

        self.last_action = action["type"]
        return action

    def update_enemy_intelligence(self, enemy_name: str, strength: int, tech_list: List[str]):
        """Update known intelligence about an enemy civilization."""
        self.known_enemy_strength[enemy_name] = strength
        self.known_enemy_tech[enemy_name] = tech_list
        
        # If enemy is strong, consider them as potential threat
        if strength > 60:
            if enemy_name not in self.war_targets:
                self.war_targets.append(enemy_name)
    
    def update_alliance_status(self, civ_name: str, is_allied: bool):
        """Update alliance status with a civilization."""
        if is_allied:
            self.allied_civs.add(civ_name)
            if civ_name in self.war_targets:
                self.war_targets.remove(civ_name)
        else:
            self.allied_civs.discard(civ_name)
    
    def update_trade_relationship(self, civ_name: str, is_trading: bool):
        """Update trade relationship with a civilization."""
        if is_trading:
            self.trade_partners.add(civ_name)
        else:
            self.trade_partners.discard(civ_name)
    
    # ---- Diplomacy Enhancement Methods ----
    
    def update_trust(self, civ_name: str, change: float):
        """Update trust level with a civilization (-100 to 100)."""
        self.trust_level[civ_name] = max(-100, min(100, 
            self.trust_level.get(civ_name, 50) + change))
    
    def record_broken_promise(self, civ_name: str):
        """Track when another civ breaks a treaty or promise."""
        self.grudges[civ_name] = self.grudges.get(civ_name, 0) + 1
        self.update_trust(civ_name, -30)
    
    def select_casus_belli(self, target: str, game_context: Dict) -> Optional[CasusBelliType]:
        """Select the strongest casus belli against a target based on game state."""
        if self.aggression < 0.4:
            return None
        
        available_cb = []
        
        # Check if we have spies caught (SPIES CB)
        if game_context.get("has_spy_intel", False):
            available_cb.append((CasusBelliType.SPIES, 0.20))
        
        # Check for border disputes (BORDER_DISPUTE CB)
        if game_context.get("border_dispute", False):
            available_cb.append((CasusBelliType.BORDER_DISPUTE, 0.15))
        
        # Check for unpaid reparations (DEBT CB)
        if game_context.get("unpaid_debt", False):
            available_cb.append((CasusBelliType.DEBT, 0.10))
        
        # Check for religious conflict (RELIGIOUS CB)
        if game_context.get("religious_conflict", False):
            available_cb.append((CasusBelliType.RELIGIOUS, 0.25))
        
        # Check for honor insult (HONOR CB)
        if self.grudges.get(target, 0) > 0:
            available_cb.append((CasusBelliType.HONOR, 0.05))
        
        # Check for resource control (RESOURCE CB)
        if game_context.get("resource_control", False):
            available_cb.append((CasusBelliType.RESOURCE, 0.15))
        
        # Unification CB if target has divided ethnic groups
        if game_context.get("divided_ethnicity", False):
            available_cb.append((CasusBelliType.UNIFICATION, 0.20))
        
        if not available_cb:
            # Default CB based on aggression level
            if self.aggression > 0.7:
                available_cb.append((CasusBelliType.PREEMPTIVE, 0.10))
            else:
                return None
        
        # Pick the strongest available CB
        available_cb.sort(key=lambda x: x[1], reverse=True)
        chosen_cb = available_cb[0][0]
        self.desired_cb_types[target] = chosen_cb
        return chosen_cb
    
    def decide_diplomatic_action(self, target: str, game_context: Dict) -> Optional[Dict]:
        """Decide diplomatic action toward a target civ with strategic depth."""
        trust = self.trust_level.get(target, 50)
        enemy_strength = self.known_enemy_strength.get(target, 0)
        our_strength = game_context.get("our_strength", 50)
        
        # If allied, prefer maintaining alliance
        if target in self.allied_civs:
            if trust > 30:
                return {"action": "maintain_alliance", "target": target}
        
        # If they have a strong military and we're weak, avoid conflict
        if enemy_strength > our_strength * 1.3 and self.aggression < 0.6:
            if trust < 0:
                return {"action": "seek_defensive_pact", "target": target}
            return None
        
        # If we have a valid CB and are aggressive enough, consider war
        if self.aggression > 0.6 and enemy_strength < our_strength * 0.7:
            cb = self.select_casus_belli(target, game_context)
            if cb:
                return {"action": "declare_war", "target": target, "casus_belli": cb.value}
        
        # Economic pact if we have surplus gold
        if game_context.get("gold_surplus", 0) > 50 and trust > 0:
            return {"action": "propose_trade_agreement", "target": target, 
                    "offer": {"gold": 20, "resources": "surplus_food"}}
        
        # Defend against threat
        if enemy_strength > our_strength * 1.2 and target not in self.allied_civs:
            if trust > 0:
                return {"action": "propose_non_aggression_pact", "target": target}
            else:
                return {"action": "seek_alliance_against_threat", 
                        "target": target, "against": game_context.get("common_enemy")}
        
        # Random diplomatic action based on aggression
        if random.random() < self.aggression * 0.3:
            return {"action": "demand_tribute", "target": target, "amount": 10}
        
        return None
    
    def evaluate_treaty_offer(self, offer: Dict, from_civ: str) -> bool:
        """Evaluate whether to accept a treaty offer from another civ."""
        trust = self.trust_level.get(from_civ, 50)
        action = offer.get("action")
        
        if action == "non_aggression_pact":
            # Accept if we're preparing for war elsewhere or if we're peaceful
            return self.aggression < 0.6 or trust > 30
        
        elif action == "defensive_pact":
            # Accept if we have a common enemy
            return game_context.get("common_enemy") is not None
        
        elif action == "trade_agreement":
            # Accept if we need resources or have surplus to trade
            return offer.get("offer", {}).get("gold", 0) > 10 or trust > 50
        
        elif action == "open_borders":
            # Always good for trade and movement
            return trust > 20
        
        elif action == "research_pact":
            # Accept if we're science-focused
            return self.priorities.get("science", 0) > 0.4
        
        return False
    
    def generate_trade_offer(self, target: str, game_data: Dict) -> Optional[Dict]:
        """Generate a trade offer for resource exchange."""
        if game_data.get("gold", 0) < 20:
            return None
        
        resources_available = []
        if game_data.get("food", 0) > 50:
            resources_available.append(("food", 20))
        if game_data.get("production", 0) > 30:
            resources_available.append(("production", 15))
        if game_data.get("science", 0) > 20:
            resources_available.append(("science", 10))
        
        if not resources_available:
            return {"offer": {"gold": 10}, "demand": {"gold": 15}}
        
        # Create balanced offer
        resource_offer = random.choice(resources_available)
        return {
            "offer": {resource_offer[0]: resource_offer[1]},
            "demand": {"gold": resource_offer[1] * 1.5}
        }
    
    def process_treaty_expirations(self, turn: int, current_treaties: Dict) -> List[str]:
        """Process expired treaties and update relationships."""
        expired = []
        for target, treaty_info in list(current_treaties.items()):
            if treaty_info.get("end_turn", 0) <= turn:
                expired.append(target)
                self.update_trust(target, -10)  # Slight penalty for expired treaties
                if target in self.active_treaties:
                    del self.active_treaties[target]
        return expired
    
    def assess_diplomatic_situation(self, all_civs: List[str], current_turn: int) -> Dict:
        """Get overall diplomatic assessment of the current situation."""
        situation = {
            "threat_level": "low",
            "opportunities": [],
            "recommended_actions": [],
            "alliance_prospects": [],
            "war_prospects": [],
        }
        
        # Calculate average trust and strength
        avg_trust = sum(self.trust_level.values()) / max(len(self.trust_level), 1)
        avg_strength = sum(self.known_enemy_strength.values()) / max(len(self.known_enemy_strength), 1)
        
        # Assess threat level
        if avg_strength > 60 or any(s > 80 for s in self.known_enemy_strength.values()):
            situation["threat_level"] = "high"
            situation["recommended_actions"].append("strengthen_defenses")
        elif avg_strength > 40:
            situation["threat_level"] = "medium"
        else:
            situation["threat_level"] = "low"
        
        # Find alliance prospects
        for civ in all_civs:
            if civ not in self.allied_civs and self.trust_level.get(civ, 50) > 40:
                situation["alliance_prospects"].append(civ)
                if self.known_enemy_strength.get(civ, 0) < 50:
                    situation["war_prospects"].append(civ)
        
        # Find opportunities
        if avg_trust > 50:
            situation["opportunities"].append("trade_expansion")
            situation["opportunities"].append("cultural_exchange")
        if any(s < 30 for s in self.known_enemy_strength.values()):
            situation["opportunities"].append("territorial_expansion")
        
        # Recommend actions based on situation
        if situation["threat_level"] == "high":
            situation["recommended_actions"].append("seek_alliances")
            situation["recommended_actions"].append("military_buildup")
        elif self.aggression > 0.6:
            situation["recommended_actions"].append("prepare_offensive")
        
        return situation

    def decide_court_appointments(self, court: Court, candidates: List[Character], turn: int) -> List[str]:
        """AI decides which court positions to fill based on its priorities."""
        appointed = []

        # Marshal is always valuable for aggressive AIs
        if self.priorities["military"] > 0.3:
            best = court.get_best_candidate(candidates, CourtPosition.MARSHAL)
            if best and court.positions[CourtPosition.MARSHAL] is None:
                court.appoint(CourtPosition.MARSHAL, best, turn)
                appointed.append("Marshal")

        # Steward for economy-focused AIs
        if self.priorities["economy"] > 0.2:
            best = court.get_best_candidate(candidates, CourtPosition.STEWARD)
            if best and court.positions[CourtPosition.STEWARD] is None:
                court.appoint(CourtPosition.STEWARD, best, turn)
                appointed.append("Steward")

        # Spymaster for intrigue-focused AIs
        if self.aggression > 0.5:
            best = court.get_best_candidate(candidates, CourtPosition.SPYMASTER)
            if best and court.positions[CourtPosition.SPYMASTER] is None:
                court.appoint(CourtPosition.SPYMASTER, best, turn)
                appointed.append("Spymaster")

        # Chancellor for diplomatic AIs
        if self.aggression < 0.6:
            best = court.get_best_candidate(candidates, CourtPosition.CHANCELLOR)
            if best and court.positions[CourtPosition.CHANCELLOR] is None:
                court.appoint(CourtPosition.CHANCELLOR, best, turn)
                appointed.append("Chancellor")

        return appointed

    def get_opinion_on_player(self) -> float:
        """Simulate AI's opinion of the player. -100 to 100."""
        base = 50
        if self.aggression > 0.6:
            base -= 20
        elif self.aggression < 0.3:
            base += 10
        return base + random.randint(-10, 10)

    def get_ai_summary(self) -> str:
        lines = [
            f"\n=== AI ({self.civ.name}) Status ===",
            f"Difficulty: {self.difficulty}",
            f"Aggression: {self.aggression:.1f}",
            f"Last Action: {self.last_action}",
            "Priorities:",
        ]
        for p, v in self.priorities.items():
            lines.append(f"  {p}: {v:.1f}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "civ_name": self.civ.name,
            "difficulty": self.difficulty,
            "aggression": self.aggression,
            "priorities": self.priorities,
            "last_action": self.last_action,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AIPlayer':
        ai = cls(data["civ_name"], data["difficulty"])
        ai.aggression = data["aggression"]
        ai.priorities = data["priorities"]
        ai.last_action = data["last_action"]
        return ai
