from typing import Dict, List, Tuple, Set, Optional
import random
import uuid

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

class Character:
    def __init__(self, name: str, stats: Dict[str, int], traits: List[str], parent_ids: List[str] = None):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.base_stats = stats  # {'diplomacy', 'martial', 'stewardship', 'intrigue'}
        self.traits = traits
        self.parent_ids = parent_ids or []
        self.children_ids: List[str] = []
        self.is_alive = True
        self.gold_reserve = 0.0
        self.age = 18

    def get_effective_stat(self, stat_name: str) -> int:
        bonus = 0
        for trait in self.traits:
            bonus += TRAIT_DATABASE.get(trait, {}).get(stat_name, 0)
        return self.base_stats.get(stat_name, 0) + bonus

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
