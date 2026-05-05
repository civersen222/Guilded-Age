from typing import Dict, List, Tuple, Set, Optional
import random
import uuid
from character_deepening import (
    LifestyleProgression,
    AgeProgress,
    LifeStage,
    TRAIT_DATABASE as EXTENDED_TRAIT_DATABASE,
    generate_traits,
    get_trait_description,
    get_available_traits,
    apply_traits_to_stats,
)

# Trait Database: Maps traits to stat bonuses
TRAIT_DATABASE = {
    "Industrious": {"stewardship": 2},
    "Brave": {"martial": 2},
    "Charismatic": {"diplomacy": 2},
    "Cunning": {"intrigue": 2},
    "Scholar": {"stewardship": 1, "diplomacy": 1},
    "Warrior": {"martial": 3},
    "Diplomat": {"diplomacy": 3},
    "Spymaster": {"intrigue": 3},
}

# Personality traits (for stress system)
PERSONALITY_TRAITS = {
    'Compassionate', 'Honest', 'Just', 'Peaceful', 'Generous', 'Cruel', 'Ambitious',
}

# Stress triggers: (trait, action) -> stress amount
STRESS_TRIGGERS = {
    ('Compassionate', 'execute'): 30,
    ('Honest', 'plot'): 25,
    ('Just', 'break_treaty'): 20,
    ('Peaceful', 'declare_war'): 25,
    ('Generous', 'raise_taxes'): 10,
    ('Cruel', 'show_mercy'): 15,
    ('Ambitious', 'accept_unfavorable_peace'): 20,
}

# Stress thresholds: {cutoff: (label, fertility_mod, health_mod)}
STRESS_THRESHOLDS = {
    100: ('Stressed', -0.10, 0),
    200: ('Overwhelmed', -0.30, -1),
    300: ('Breaking Point', -0.50, -2),
}

class Character:
    def __init__(self, name: str, stats: Dict[str, int], traits: List[str], parent_ids: List[str] = None, age: int = 18):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.base_stats = stats  # {'diplomacy', 'martial', 'stewardship', 'intrigue'}
        self.traits = traits
        self.parent_ids = parent_ids or []
        self.children_ids: List[str] = []
        self.is_alive = True
        self.gold_reserve = 0.0
        self.age = age
        
        # Stress system
        self.stress = 0  # range 0-300
        
        # Section 6: Character deepening
        self.age_progress = AgeProgress(current_age=age, is_alive=True)
        self.lifestyle = LifestyleProgression()
    
    def age_up(self) -> Optional[str]:
        """Age character by one turn. Returns event message if significant."""
        if not self.is_alive:
            return None
        event = self.age_progress.age_up()
        self.age = self.age_progress.current_age
        return event
    
    def train_skill(self, skill_type, amount: int = 1) -> Optional[str]:
        """Train a skill. Returns new level name if leveled up."""
        new_level = self.lifestyle.train_skill(skill_type, amount)
        if new_level:
            return f"Leveled up {skill_type.value} to {new_level.value}"
        return None
    
    def get_effective_stat(self, stat_name: str) -> int:
        skill_base = self.lifestyle.get_effective_stat(stat_name, self.base_stats.get(stat_name, 0))
        bonus = 0
        for trait in self.traits:
            bonus += TRAIT_DATABASE.get(trait, {}).get(stat_name, 0)
        return skill_base + bonus

    def add_stress(self, amount: int) -> Optional[str]:
        """Increase stress by amount. Returns threshold message if crossed."""
        if not self.is_alive:
            return None
        old_level = self.get_stress_level()
        self.stress = min(self.stress + amount, 300)
        new_level = self.get_stress_level()
        if new_level != old_level and new_level:
            return f"{self.name} is now '{new_level}' (stress: {self.stress})"
        return None

    def reduce_stress(self, amount: int):
        """Decrease stress by amount (min 0)."""
        self.stress = max(self.stress - amount, 0)

    def check_stress_action(self, action_type: str) -> int:
        """Check personality traits against action, return stress gain."""
        for trait in self.traits:
            if trait in PERSONALITY_TRAITS:
                key = (trait, action_type)
                if key in STRESS_TRIGGERS:
                    return STRESS_TRIGGERS[key]
        return 0

    def get_stress_level(self) -> Optional[str]:
        """Return current stress threshold label."""
        for cutoff in sorted(STRESS_THRESHOLDS.keys(), reverse=True):
            if self.stress >= cutoff:
                return STRESS_THRESHOLDS[cutoff][0]
        return None

    def get_stress_fertility_mod(self) -> float:
        """Return fertility modifier based on stress level."""
        for cutoff in sorted(STRESS_THRESHOLDS.keys(), reverse=True):
            if self.stress >= cutoff:
                return STRESS_THRESHOLDS[cutoff][1]
        return 0.0

    def get_stress_health_penalty(self) -> int:
        """Return health penalty based on stress level."""
        for cutoff in sorted(STRESS_THRESHOLDS.keys(), reverse=True):
            if self.stress >= cutoff:
                return STRESS_THRESHOLDS[cutoff][2]
        return 0

    def decay_stress(self):
        """Natural stress decay: -2 per turn."""
        self.stress = max(self.stress - 2, 0)

    def __repr__(self):
        return f"Character({self.name}, ID: {self.id}, Pop: {self.is_alive})"

class Dynasty:
    def __init__(self, root_ancestor: Character, all_characters: Dict[str, Character]):
        self.root = root_ancestor
        self.all_characters = all_characters

    def get_all_members(self) -> List[Character]:
        members = []
        visited = set()
        
        def traverse(char_id: str):
            if char_id in visited:
                return
            visited.add(char_id)
            char = self.all_characters.get(char_id)
            if char:
                members.append(char)
                for child_id in char.children_ids:
                    traverse(child_id)
        
        traverse(self.root.id)
        return members

    def calculate_dynastic_prestige(self) -> float:
        members = self.get_all_members()
        living_members = [m for m in members if m.is_alive]
        
        total_stats = 0
        for m in living_members:
            for stat in ['diplomacy', 'martial', 'stewardship', 'intrigue']:
                total_stats += m.get_effective_stat(stat)
        
        # Prestige = (Living Count * 10) + Sum of all effective stats
        return (len(living_members) * 10) + total_stats

# Global Opinion Matrix
# (char_id_a, char_id_b) -> value
opinion_matrix: Dict[Tuple[str, str], int] = {}

def modify_opinion(char_a: Character, char_b: Character, amount: int, reason: str):
    pair = (char_a.id, char_b.id)
    current = opinion_matrix.get(pair, 0)
    opinion_matrix[pair] = current + amount
    print(f"Opinion: {char_a.name} -> {char_b.name} changed by {amount} ({reason}). New value: {opinion_matrix[pair]}")

def generate_child(name: str, parent_a: Character, parent_b: Character) -> Character:
    # 1. Base stats: Average of parents + random fluctuation
    stats = {}
    for stat in ['diplomacy', 'martial', 'stewardship', 'intrigue']:
        avg = (parent_a.base_stats[stat] + parent_b.base_stats[stat]) / 2
        stats[stat] = int(avg + random.randint(-2, 2))

    # 2. Genetic Inheritance of traits
    child_traits = []
    all_parent_traits = list(set(parent_a.traits + parent_b.traits))
    for trait in all_parent_traits:
        # 30% base chance to inherit any parent trait
        if random.random() < 0.3:
            child_traits.append(trait)
    
    # 3. Stat-based trait probability
    # If parents have high stewardship, higher chance of 'Industrious'
    avg_stew = (parent_a.get_effective_stat('stewardship') + parent_b.get_effective_stat('stewardship')) / 2
    if avg_stew > 12 and "Industrious" not in child_traits:
        if random.random() < 0.4: # 40% chance
            child_traits.append("Industrious")

    child = Character(name, stats, child_traits, parent_ids=[parent_a.id, parent_b.id])
    
    # Update parents' children lists
    parent_a.children_ids.append(child.id)
    parent_b.children_ids.append(child.id)
    
    return child

def print_lineage_tree(char: Character, all_characters: Dict[str, Character], depth: int = 0):
    indent = "  " * depth
    print(f"{indent}|-- {char.name} ({char.id}) - Traits: {', '.join(char.traits)}")
    for child_id in char.children_ids:
        child = all_characters.get(child_id)
        if child:
            print_lineage_tree(child, all_characters, depth + 1)

class DynastyManager:
    def __init__(self):
        self.root: Optional[Character] = None

    def get_all_members(self) -> List[Character]:
        if not self.root:
            return []
        members = []
        visited = set()
        def traverse(char_id: str):
            if char_id in visited:
                return
            visited.add(char_id)
            char = self.root
            if char and char.id == char_id:
                members.append(char)
                for child_id in char.children_ids:
                    traverse(child_id)
        traverse(self.root.id)
        return members

    def add_member(self, char: Character):
        if not self.root:
            self.root = char

if __name__ == "__main__":
    # Registry of all characters
    registry: Dict[str, Character] = {}

    def register(c):
        registry[c.id] = c
        return c

    # Create Root Ancestor
    root = register(Character("Founder", {"diplomacy": 10, "martial": 10, "stewardship": 15, "intrigue": 5}, ["Industrious", "Charismatic"]))
    
    # Create Spouse
    spouse = register(Character("Matriarch", {"diplomacy": 12, "martial": 5, "stewardship": 10, "intrigue": 10}, ["Diplomat"]))
    
    # Generate children
    c1 = register(generate_child("Child 1", root, spouse))
    c2 = register(generate_child("Child 2", root, spouse))
    
    # Next Generation
    c1_spouse = register(Character("In-law 1", {"diplomacy": 10, "martial": 10, "stewardship": 10, "intrigue": 10}, ["Brave"]))
    gc1 = register(generate_child("Grandchild 1", c1, c1_spouse))
    
    # Setup Dynasty
    dynasty = Dynasty(root, registry)
    
    print(f"Dynasty Prestige: {dynasty.calculate_dynastic_prestige()}")
    print("\nLineage Tree:")
    print_lineage_tree(root, registry)
    
    print("\nOpinion Simulation:")
    modify_opinion(c1, root, 10, "Respect for ancestor")
    modify_opinion(root, c1, -5, "Disappointment in lifestyle")
    
    print(f"\n{c1.name} effective stewardship: {c1.get_effective_stat('stewardship')}")
    
    # Test Section 6: Character Deepening
    print("\n--- Character Deepening Test ---")
    
    # Test trait generation
    new_traits = generate_traits(age=25, num_traits=3)
    print(f"Generated traits for age 25: {new_traits}")
    
    # Test age progression
    root.age_up()
    print(f"Founder age: {root.age}, Stage: {root.age_progress.life_stage.value}, Alive: {root.age_progress.is_alive}")
    
    # Test skill training
    from character_deepening import SkillType
    level = root.lifestyle.train_skill(SkillType.MARTIAL, 15)
    print(f"Martial skill level: {root.lifestyle.skills[SkillType.MARTIAL].current_level.value}")
    
    # Test effective stat with skill multiplier
    print(f"Founder effective martial (with skill): {root.get_effective_stat('martial')}")
    
    # Test extended trait database
    print(f"\nExtended traits available (age 30): {len(get_available_traits(30))} traits")
    print(f"'Brave' description: {get_trait_description('Brave')}")
    
    # Test applying traits to stats
    test_stats = {"diplomacy": 5, "martial": 5, "stewardship": 5, "intrigue": 5}
    modified = apply_traits_to_stats(test_stats, ["Brave", "Charismatic", "Scholar"])
    print(f"Base stats {test_stats} -> With traits: {modified}")
    
    # Test aging to elder
    for _ in range(50):
        root.age_up()
    print(f"\nFounder after 50 turns: age={root.age}, stage={root.age_progress.life_stage.value}, alive={root.age_progress.is_alive}")
    
    # Test trait evolution
    print("\n--- Trait Evolution Test ---")
    from character_deepening import (
        TraitEvolutionManager,
        evolve_traits,
        suggest_traits_for_event,
        get_trait_change_probability,
    )
    
    # Simulate events
    manager = TraitEvolutionManager()
    
    # Battle events
    manager.record_event("battle_victory", 22, "Victory at Battle of Red River", "win")
    manager.record_event("battle_victory", 23, "Victory at Siege of Blackwood", "win")
    manager.record_event("battle_victory", 24, "Victory at Battle of Stone Pass", "win")
    manager.record_event("battle_wound", 25, "Wounded by arrow in battle", "injured")
    manager.record_event("battle_command", 26, "Commanded army at Battle of the Plains", "victory")
    
    # Study events
    manager.record_event("study_years", 28, "Years spent studying history", "")
    manager.record_event("study_years", 29, "Years spent studying philosophy", "")
    manager.record_event("study_years", 30, "Years spent studying theology", "")
    manager.record_event("study_years", 31, "Years spent studying mathematics", "")
    manager.record_event("study_years", 32, "Years spent studying law", "")
    
    # Court events
    manager.record_event("coronation", 30, "Crowned king", "")
    manager.record_event("scandal", 35, "Scandal over affair with noblewoman", "exposed")
    manager.record_event("scandal_survived", 35, "Survived scandal and maintained power", "survived")
    
    # Initial traits
    initial_traits = ["Young", "Ambitious"]
    print(f"Initial traits: {initial_traits}")
    
    # Evolve traits at different ages
    for test_age in [25, 30, 40, 50, 60]:
        old_traits = initial_traits.copy()
        new_traits, changes = evolve_traits(initial_traits, test_age, manager.event_log)
        if changes:
            print(f"\nAt age {test_age}:")
            for old_t, new_t, event in changes:
                old_str = old_t if old_t else "(none)"
                print(f"  {old_str} -> {new_t} (triggered by: {event})")
            print(f"  Current traits: {new_traits}")
        
        # Update initial traits for next iteration (in case traits persisted)
        if new_traits != initial_traits:
            initial_traits = new_traits
    
    # Test suggest_traits_for_event
    print("\n--- Trait Suggestions ---")
    suggestions = suggest_traits_for_event("battle_victory")
    print(f"Possible traits from battle victory: {suggestions}")
    
    # Test get_trait_change_probability
    prob = get_trait_change_probability("Young", "reached_prime")
    print(f"Probability of 'Young' changing on 'reached_prime': {prob}")
    
    # Test condition functions
    print("\n--- Condition Tests ---")
    print(f"'multiple_battles' condition met: {any(e.event_type == 'battle_victory' for e in manager.event_log) and sum(1 for e in manager.event_log if e.event_type == 'battle_victory') >= 3}")
    print(f"'decades_study' condition met: {sum(1 for e in manager.event_log if e.event_type == 'study_years') >= 5}")
    
    print("\nTrait evolution test complete!")
