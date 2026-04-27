"""
CivKings - Plot & Spy Management System
Handles plots, conspiracies, spies, and intrigue
"""
from typing import Dict, List, Optional, Tuple
import random


class Plot:
    """Represents a plot or conspiracy"""
    
    def __init__(self, name: str, mastermind: str, target: str, plot_type: str = "assassination"):
        self.name = name
        self.mastermind = mastermind
        self.target = target
        self.plot_type = plot_type
        self.participants: List[str] = []
        self.progress = 0
        self.max_progress = 100
        self.detected = False
        self.successful = False
    
    def add_participant(self, character: str):
        """Add a participant to the plot"""
        if character not in self.participants:
            self.participants.append(character)
    
    def advance_plot(self, amount: int):
        """Advance plot progress"""
        self.progress += amount
        if self.progress >= self.max_progress:
            self.successful = True
    
    def get_success_chance(self) -> float:
        """Get success chance based on plot parameters"""
        base_chance = 0.3  # 30% base chance
        
        # More participants = higher chance
        participant_bonus = len(self.participants) * 0.05
        
        # Plot type bonuses
        type_bonus = {
            "assassination": 0.1,
            "coup": 0.15,
            "rebellion": 0.05,
            "poisoning": 0.2
        }
        
        return min(0.9, base_chance + participant_bonus + type_bonus.get(self.plot_type, 0))


class Spy:
    """Represents a spy agent"""
    
    def __init__(self, name: str, owner: str, target: str):
        self.name = name
        self.owner = owner
        self.target = target
        self.cover_name = f"Merchant from {random.choice(['Greece', 'Egypt', 'Persia', 'India'])}"
        self.infiltration_level = 0
        self.detected = False
        self.skills = {
            "intrigue": random.randint(5, 15),
            "stealth": random.randint(5, 15)
        }
    
    def infiltrate(self, amount: int):
        """Increase infiltration level"""
        self.infiltration_level += amount
        if self.infiltration_level >= 100:
            self.infiltration_level = 100
    
    def get_detection_chance(self) -> float:
        """Get chance of being detected"""
        base_chance = 0.2  # 20% base chance
        detection_reduction = self.infiltration_level * 0.003  # Max 30% reduction at 100
        return max(0.05, base_chance - detection_reduction)


class PlotManager:
    """Manages plots, spies, and intrigue"""
    
    def __init__(self):
        self.plots: List[Plot] = []
        self.spies: List[Spy] = []
        self.intrigue_scores: Dict[str, float] = {}  # civ -> intrigue score
    
    def create_plot(self, name: str, mastermind: str, target: str, plot_type: str = "assassination") -> Plot:
        """Create a new plot"""
        plot = Plot(name, mastermind, target, plot_type)
        self.plots.append(plot)
        return plot
    
    def add_spy(self, spy: Spy):
        """Add a spy to the network"""
        self.spies.append(spy)
    
    def assign_spy(self, spy_name: str, target_civ: str) -> bool:
        """Assign a spy to target a civilization"""
        for spy in self.spies:
            if spy.name == spy_name and not spy.detected:
                spy.target = target_civ
                return True
        return False
    
    def process_plots(self) -> List[Plot]:
        """Process all active plots"""
        completed_plots = []
        
        for plot in self.plots:
            # Advance plot progress
            advancement = random.randint(5, 20)
            plot.advance_plot(advancement)
            
            # Check for success
            if plot.successful:
                # Check for detection
                detection_chance = 0.3
                if random.random() < detection_chance:
                    plot.detected = True
                    print(f"Plot '{plot.name}' detected!")
                else:
                    plot.detected = False
                    completed_plots.append(plot)
                    print(f"Plot '{plot.name}' succeeded!")
        
        # Remove completed plots
        for plot in completed_plots:
            self.plots.remove(plot)
        
        return completed_plots
    
    def process_spies(self) -> List[Spy]:
        """Process all spies"""
        caught_spies = []
        
        for spy in self.spies:
            # Infiltrate
            infiltration = random.randint(5, 15)
            spy.infiltrate(infiltration)
            
            # Check for detection
            detection_chance = spy.get_detection_chance()
            if random.random() < detection_chance:
                spy.detected = True
                caught_spies.append(spy)
                print(f"Spy '{spy.name}' caught!")
            else:
                print(f"Spy '{spy.name}' infiltrating ({spy.infiltration_level}%): {spy.cover_name}")
        
        # Remove caught spies
        for spy in caught_spies:
            self.spies.remove(spy)
        
        return caught_spies
    
    def get_intrigue_bonus(self, civ: str) -> float:
        """Get intrigue bonus for a civilization"""
        return self.intrigue_scores.get(civ, 0.0)
    
    def add_intrigue_score(self, civ: str, score: float):
        """Add intrigue score to a civilization"""
        self.intrigue_scores[civ] = self.intrigue_scores.get(civ, 0.0) + score
    
    def get_active_plots(self, civ: str) -> List[Plot]:
        """Get active plots involving a civilization"""
        return [plot for plot in self.plots if plot.mastermind == civ or plot.target == civ]
    
    def get_active_spies(self, civ: str) -> List[Spy]:
        """Get active spies belonging to a civilization"""
        return [spy for spy in self.spies if spy.owner == civ and not spy.detected]
    
    def get_plot_success_rate(self, plot: Plot) -> float:
        """Get success rate for a plot"""
        return plot.get_success_chance()
