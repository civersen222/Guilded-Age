"""
CivKings - Event Management System
Handles random events, triggered events, and narrative
"""
from typing import List, Dict, Optional, Tuple
import random


class Event:
    """Represents a game event"""
    
    def __init__(self, name: str, description: str, effects: Dict[str, int] = None, choices: List[Dict] = None):
        self.name = name
        self.description = description
        self.effects = effects or {}
        self.choices = choices or []
        self.triggered = False
    
    def apply_effects(self):
        """Apply event effects"""
        for effect_type, value in self.effects.items():
            print(f"  Effect: {effect_type} {value}")


class EventManager:
    """Manages game events and narrative"""
    
    def __init__(self):
        self.event_pool: List[Event] = []
        self.event_history: List[Event] = []
        self.active_events: List[Event] = []
    
    def generate_events(self):
        """Generate initial event pool"""
        # Define event pool
        self.event_pool = [
            Event(
                name="Bumper Crop",
                description="Favorable weather leads to abundant harvests.",
                effects={"food": 20, "gold": 5}
            ),
            Event(
                name="Plague",
                description="A terrible plague sweeps through your lands.",
                effects={"food": -15, "gold": -10}
            ),
            Event(
                name="Golden Age",
                description="Your civilization enters a period of prosperity.",
                effects={"culture": 30, "science": 20}
            ),
            Event(
                name="Earthquake",
                description="A devastating earthquake strikes your territory.",
                effects={"gold": -20, "production": -15}
            ),
            Event(
                name="Trade Boom",
                description="Trade routes flourish, bringing wealth.",
                effects={"gold": 25, "science": 10}
            ),
            Event(
                name="Scholarly Discovery",
                description="Ancient texts reveal new knowledge.",
                effects={"science": 30, "culture": 15}
            ),
            Event(
                name="Military Campaign",
                description="Your generals propose an expansionist campaign.",
                effects={"gold": -10, "production": 20}
            ),
            Event(
                name="Religious Revival",
                description="A spiritual awakening sweeps the land.",
                effects={"faith": 25, "happiness": 10}
            ),
            Event(
                name="Diplomatic Summit",
                description="Foreign envoys arrive for negotiations.",
                effects={"gold": 15, "diplomacy": 10}
            ),
            Event(
                name="Invention",
                description="A brilliant mind in your realm creates something new.",
                effects={"science": 25, "production": 15}
            )
        ]
    
    def generate_event(self) -> Optional[Tuple[str, str]]:
        """Generate a random event"""
        if not self.event_pool:
            return None
        
        # Select random event
        event = random.choice(self.event_pool)
        
        # Apply effects
        event.apply_effects()
        
        # Add to history
        self.event_history.append(event)
        
        return (event.name, event.description)
    
    def add_event(self, event: Event):
        """Add an event to the pool"""
        self.event_pool.append(event)
    
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
