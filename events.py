"""
CivKings - Event Management System
Handles random events, triggered events, and narrative
"""
from typing import List, Dict, Optional, Tuple
import random


class Event:
    """Represents a game event"""
    
    def __init__(self, name: str, description: str, effects: Dict[str, int] = None, 
                 choices: List[Dict] = None, category: str = "generic", weight: int = 1):
        self.name = name
        self.description = description
        self.effects = effects or {}
        self.choices = choices or []
        self.category = category
        self.weight = weight
        self.triggered = False
    
    def apply_effects(self):
        """Apply event effects"""
        for effect_type, value in self.effects.items():
            print(f"  Effect: {effect_type} {value}")
    
    def evaluate_choice(self, choice: Dict) -> bool:
        """Check if a choice is available (prerequisites met)"""
        if 'requirements' not in choice:
            return True
        reqs = choice['requirements']
        if 'min_gold' in reqs and False:  # Would need game context
            return False
        return True


class EventManager:
    """Manages game events and narrative"""
    
    def __init__(self):
        self.event_pool: List[Event] = []
        self.event_history: List[Event] = []
        self.active_events: List[Event] = []
        self.faction_event_pool: List[Event] = []
        self._register_default_events()
    
    def _register_default_events(self):
        """Register the default event pool"""
        self.event_pool = [
            Event("Bumper Crop", "Favorable weather leads to abundant harvests.",
                  {"food": 20, "gold": 5}, category="resource", weight=8),
            Event("Plague", "A terrible plague sweeps through your lands.",
                  {"food": -15, "gold": -10, "happiness": -5}, category="crisis", weight=4),
            Event("Earthquake", "A devastating earthquake strikes your territory.",
                  {"gold": -20, "production": -15}, category="crisis", weight=4),
            Event("Trade Boom", "Trade routes flourish, bringing wealth.",
                  {"gold": 25, "science": 10}, category="resource", weight=6),
            Event("Scholarly Discovery", "Ancient texts reveal new knowledge.",
                  {"science": 30, "culture": 15}, category="culture", weight=6),
            Event("Military Campaign", "Your generals propose an expansionist campaign.",
                  {"gold": -10, "production": 20, "military": 10}, category="military", weight=5),
            Event("Religious Revival", "A spiritual awakening sweeps the land.",
                  {"faith": 25, "happiness": 10}, category="culture", weight=5),
            Event("Diplomatic Summit", "Foreign envoys arrive for negotiations.",
                  {"gold": 15, "diplomacy": 10}, category="diplomacy", weight=5),
            Event("Invention", "A brilliant mind in your realm creates something new.",
                  {"science": 25, "production": 15}, category="culture", weight=6),
            Event("Famine", "Crops fail due to harsh weather. Food stores dwindle.",
                  {"food": -25, "happiness": -10}, category="crisis", weight=3),
            Event("Gold Rush", "A rich vein of gold is discovered in your mines.",
                  {"gold": 40, "production": 10}, category="resource", weight=4),
            Event("Dark Age", "A period of cultural decline grips the realm.",
                  {"science": -15, "culture": -15, "stability": -10}, category="crisis", weight=2),
            Event("Golden Age", "Your civilization enters a period of prosperity.",
                  {"culture": 30, "science": 20, "happiness": 10}, category="culture", weight=3),
        ]
    
    def _register_faction_events(self, faction_manager):
        """Generate events based on faction state"""
        self.faction_event_pool = []
        factions = faction_manager.factions
        if not factions:
            return
        
        for ftype, faction in factions.items():
            if 60 <= faction.influence < 80:
                self.faction_event_pool.append(Event(
                    name=f"Rising {faction.name}",
                    description=f"{faction.name} grows in power, demanding a voice at court.",
                    effects={ftype: 10, "happiness": 5},
                    category="faction",
                    weight=3
                ))
            elif faction.influence >= 80:
                self.faction_event_pool.append(Event(
                    name=f"{faction.name} Seizes Control",
                    description=f"{faction.name} has become dominant, reshaping policy in their favour.",
                    effects={ftype: 20, "stability": -5},
                    choices=[
                        {"name": "Pleas them (+influence)", "effects": {ftype: 15, "gold": -10}},
                        {"name": "Suppress them (-influence)", "effects": {ftype: -20, "stability": -10}}
                    ],
                    category="faction",
                    weight=2
                ))
            elif faction.influence <= 15:
                self.faction_event_pool.append(Event(
                    name=f"Marginalised {faction.name}",
                    description=f"{faction.name} plots rebellion after being ignored for too long.",
                    effects={"stability": -10, "happiness": -5},
                    category="faction",
                    weight=3
                ))
        
        if faction_manager.conflict_level > 60:
            self.faction_event_pool.append(Event(
                name="Court Intrigue",
                description="Factions clash within the palace. The ruler must intervene.",
                effects={"stability": -10, "gold": -5},
                choices=[
                    {"name": "Play them against each other", "effects": {"stability": 5, "gold": 10}},
                    {"name": "Suppress all factions", "effects": {"stability": -15, "military": -5}}
                ],
                category="faction",
                weight=2
            ))
    
    def generate_events(self, faction_manager=None):
        """Generate/refresh event pool, optionally with faction-driven events"""
        self._register_default_events()
        if faction_manager:
            self._register_faction_events(faction_manager)
    
    def generate_event(self) -> Optional[Tuple[str, str]]:
        """Generate a random event, weighted by category and faction state"""
        pool = self.event_pool + self.faction_event_pool
        if not pool:
            return None
        
        weighted = [(e, e.weight) for e in pool]
        total = sum(w for _, w in weighted)
        r = random.uniform(0, total)
        cumulative = 0
        chosen = None
        for event, weight in weighted:
            cumulative += weight
            if r <= cumulative:
                chosen = event
                break
        if chosen is None:
            chosen = weighted[-1][0]
        
        chosen.apply_effects()
        self.event_history.append(chosen)
        return (chosen.name, chosen.description)
    
    def add_event(self, event: Event):
        """Add an event to the pool"""
        self.event_pool.append(event)
    
    def add_faction_event(self, event: Event):
        """Add a faction-specific event"""
        self.faction_event_pool.append(event)
    
    def get_event_history(self) -> List[Event]:
        """Get event history"""
        return self.event_history
    
    def get_recent_events(self, count: int = 5) -> List[Event]:
        """Get recent events"""
        return self.event_history[-count:]
    
    def trigger_event(self, event_name: str) -> Optional[Event]:
        """Trigger a specific event by name"""
        for event in self.event_pool:
            if event.name == event_name and not event.triggered:
                event.triggered = True
                self.active_events.append(event)
                return event
        return None
    
    def process_active_events(self):
        """Process all active events"""
        completed = []
        for event in self.active_events:
            if event.triggered:
                completed.append(event)
        
        for event in completed:
            self.active_events.remove(event)
            self.event_history.append(event)
    
    def get_event_summary(self) -> str:
        """Get a summary of recent events"""
        if not self.event_history:
            return "No events yet."
        lines = ["\n=== Recent Events ==="]
        for event in self.event_history[-5:]:
            lines.append(f"  {event.name}: {event.description}")
        return "\n".join(lines)
    
    def get_world_state_summary(self) -> str:
        """Get a summary of the current world state"""
        return "World state: Stable"
