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
from dispositions import initial_dispositions, labels_for, inherit_dispositions

# Six attributes (character-society spec 3.2) and legacy 4-stat compatibility
ATTRIBUTES = ["statecraft", "command", "industry", "intrigue", "science", "resolve"]
STAT_COMPAT = {"diplomacy": "statecraft", "martial": "command", "stewardship": "industry"}


def normalize_stats(stats: Dict[str, int]) -> Dict[str, int]:
    """Map a possibly-legacy stat dict onto the six attributes; seed any
    missing attribute (notably science/resolve) with 8 +/- 3 jitter."""
    norm: Dict[str, int] = {}
    for key, val in (stats or {}).items():
        norm[STAT_COMPAT.get(key, key)] = val
    for attr in ATTRIBUTES:
        if attr not in norm:
            norm[attr] = max(1, 8 + random.randint(-3, 3))
    return norm


# Trait Database: Maps traits to attribute bonuses
TRAIT_DATABASE = {
    "Industrious": {"industry": 2},
    "Brave": {"command": 2, "resolve": 1},
    "Charismatic": {"statecraft": 2},
    "Cunning": {"intrigue": 2},
    "Scholar": {"industry": 1, "statecraft": 1, "science": 2},
    "Warrior": {"command": 3},
    "Diplomat": {"statecraft": 3},
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
    def __init__(self, name: str, stats: Dict[str, int], traits: List[str], parent_ids: List[str] = None, age: int = 18, gender: str = "Male"):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        # Six attributes (spec 3.2); legacy 4-stat dicts are remapped.
        self.base_stats = normalize_stats(stats)
        # Disposition spectrums (spec 3.3): 30 paired values in -100..+100.
        self.dispositions: Dict[str, float] = initial_dispositions()
        self.traits = traits  # goes through the property setter below
        self.parent_ids = parent_ids or []
        self.children_ids: List[str] = []
        self.is_alive = True
        self.gold_reserve = 0.0
        self.age = age
        self.gender = gender
        
        # Stress system
        self.stress = 0  # range 0-300
        
        # Section 6: Character deepening
        self.age_progress = AgeProgress(current_age=age, is_alive=True)
        self.lifestyle = LifestyleProgression()
        self.is_heir = False

    @property
    def traits(self) -> List[str]:
        """Explicit traits plus labels derived live from dispositions."""
        derived = labels_for(self.dispositions)
        return self._explicit_traits + [t for t in derived if t not in self._explicit_traits]

    @traits.setter
    def traits(self, value) -> None:
        self._explicit_traits = list(value or [])

    def add_trait(self, trait: str) -> None:
        """Add an explicit trait (use this instead of traits.append)."""
        if trait not in self._explicit_traits:
            self._explicit_traits.append(trait)

    def age_up(self) -> Optional[str]:
        """Age character by one turn. Returns event message if significant."""
        if not self.is_alive:
            return None
        event = self.age_progress.age_up()
        self.age = self.age_progress.current_age
        if not self.age_progress.is_alive:
            self.is_alive = False
        return event
    
    def train_skill(self, skill_type, amount: int = 1) -> Optional[str]:
        """Train a skill. Returns new level name if leveled up."""
        new_level = self.lifestyle.train_skill(skill_type, amount)
        if new_level:
            return f"Leveled up {skill_type.value} to {new_level.value}"
        return None
    
    def get_effective_stat(self, stat_name: str) -> int:
        stat_name = STAT_COMPAT.get(stat_name, stat_name)  # legacy names OK
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
        self.bonus_prestige = 0

    def add_member(self, character: Character, parent_id: str):
        """Add a new member to the dynasty."""
        self.all_characters[character.id] = character
        parent = self.all_characters.get(parent_id)
        if parent and character.id not in parent.children_ids:
            parent.children_ids.append(character.id)

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

    def add_prestige(self, amount: int):
        self.bonus_prestige += amount

    def calculate_dynastic_prestige(self) -> float:
        members = self.get_all_members()
        living_members = [m for m in members if m.is_alive]
        
        total_stats = 0
        for m in living_members:
            for stat in ATTRIBUTES:
                total_stats += m.get_effective_stat(stat)
        
        # Prestige = (Living Count * 10) + Sum of all effective stats + bonus
        return (len(living_members) * 10) + total_stats + self.bonus_prestige

# Global Opinion Matrix
# (char_id_a, char_id_b) -> value
opinion_matrix: Dict[Tuple[str, str], int] = {}

def modify_opinion(char_a: Character, char_b: Character, amount: int, reason: str):
    pair = (char_a.id, char_b.id)
    current = opinion_matrix.get(pair, 0)
    opinion_matrix[pair] = current + amount
    return f"{char_a.name} -> {char_b.name}: {amount:+d} ({reason})"

def generate_child(name: str, parent_a: Character, parent_b: Character) -> Character:
    # 1. Base stats: Average of parents + random fluctuation (six attributes)
    stats = {}
    for stat in ATTRIBUTES:
        avg = (parent_a.base_stats.get(stat, 8) + parent_b.base_stats.get(stat, 8)) / 2
        stats[stat] = int(avg + random.randint(-2, 2))

    # 2. Genetic Inheritance of traits (explicit only; disposition labels
    # are derived live from the child's own spectrums, never copied).
    child_traits = []
    all_parent_traits = list(set(parent_a._explicit_traits + parent_b._explicit_traits))
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
    # 4. Genetics (spec 3.3): Bloodline spectrums blend from the parents
    # with mutation; Temperament/Conviction re-seed near neutral.
    child.dispositions = inherit_dispositions(parent_a.dispositions, parent_b.dispositions)

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

# Succession laws
SUCCESSION_LAWS = ['PRIMOGENITURE', 'GAVELKIND', 'SENIORITY', 'ELECTIVE']

def execute_succession(
    ruler: Character,
    succession_law: str,
    cities: Dict[str, 'City'],
    heirs: List[Character],
) -> dict:
    """Execute succession when a ruler dies.

    Args:
        ruler: The deceased ruler.
        succession_law: One of PRIMOGENITURE, GAVELKIND, SENIORITY, ELECTIVE.
        cities: Dict of city_name -> City for the realm.
        heirs: List of candidate heir Characters.

    Returns:
        {'new_ruler': Character, 'lost_cities': List[str], 'events': List[str]}
    """
    if not isinstance(ruler, Character):
        # Handle case where ruler is a string name
        ruler = None
    events: List[str] = []
    lost_cities: List[str] = []

    # Filter to living heirs
    living_heirs = [h for h in heirs if h.is_alive]

    new_ruler: Optional[Character] = None

    if succession_law == 'PRIMOGENITURE':
        # Eldest child gets everything
        if living_heirs:
            new_ruler = max(living_heirs, key=lambda h: h.age)
            events.append(f"PRIMOGENITURE: {new_ruler.name} (age {new_ruler.age}) inherits the throne as the eldest child.")
        else:
            # No children — fall back to SENIORITY
            new_ruler = _seniority_pick(living_heirs)
            if new_ruler:
                events.append(f"No heir apparent. SENIORITY picks {new_ruler.name} from the dynasty.")
            else:
                events.append(f"No heir apparent. Dynasty has collapsed.")

    elif succession_law == 'GAVELKIND':
        # Split realm: eldest gets capital, rest distributed
        if living_heirs:
            living_heirs.sort(key=lambda h: h.age, reverse=True)
            new_ruler = living_heirs[0]
            events.append(f"GAVELKIND: {new_ruler.name} inherits the capital and primary lands.")
            # Other heirs get some cities — they become independent
            other_heirs = living_heirs[1:]
            city_list = list(cities.values())
            for idx, heir in enumerate(other_heirs):
                if idx < len(city_list):
                    city = city_list[idx]
                    old_owner = city.owner
                    city.owner = heir.name
                    events.append(f"  {city.name} goes to {heir.name}")
                    # If old_owner != new ruler's civ, it's a lost city
                    if old_owner and old_owner != new_ruler.name:
                        lost_cities.append(city.name)
        else:
            new_ruler = _seniority_pick(living_heirs)
            if new_ruler:
                events.append(f"No heirs. SENIORITY fallback picks {new_ruler.name}.")
            else:
                events.append(f"No heirs. Dynasty has collapsed.")

    elif succession_law == 'SENIORITY':
        # Oldest living dynasty member inherits
        new_ruler = _seniority_pick(living_heirs)
        if new_ruler:
            events.append(f"SENIORITY: {new_ruler.name} (age {new_ruler.age}) is the oldest living dynasty member and inherits.")

    elif succession_law == 'ELECTIVE':
        # Random weighted by combined stats
        if living_heirs:
            weights = []
            for h in living_heirs:
                w = sum(h.get_effective_stat(a) for a in ATTRIBUTES)
                weights.append(max(w, 1))
            total = sum(weights)
            # Weighted random
            r = random.uniform(0, total)
            cumulative = 0
            new_ruler = living_heirs[-1]  # fallback to last
            for h, w in zip(living_heirs, weights):
                cumulative += w
                if r <= cumulative:
                    new_ruler = h
                    break
            events.append(f"ELECTIVE: {new_ruler.name} wins the election of nobles (weight: {weights[living_heirs.index(new_ruler)]}).")
        else:
            new_ruler = _seniority_pick(living_heirs)
            events.append(f"No candidates. SENIORITY fallback picks {new_ruler.name}.")
    else:
        events.append(f"Unknown succession law '{succession_law}'. Using PRIMOGENITURE.")
        if living_heirs:
            new_ruler = max(living_heirs, key=lambda h: h.age)
            events.append(f"PRIMOGENITURE: {new_ruler.name} inherits as eldest.")

    if new_ruler is None:
        events.append(f"No viable heirs for {ruler.name if ruler else 'the throne'}. Realm collapses.")
        lost_cities = list(cities.keys())
        return {'new_ruler': None, 'lost_cities': lost_cities, 'events': events}

    # Update dynasty: new ruler becomes root
    if isinstance(ruler, Character):
        ruler.is_alive = False
        events.append(f"Ruler {ruler.name} has died.")
        events.append(f"Stability: -25 on succession.")

    return {
        'new_ruler': new_ruler,
        'lost_cities': lost_cities,
        'events': events,
    }


def _seniority_pick(living_heirs: List[Character]) -> Optional[Character]:
    """Pick the oldest living character from heirs."""
    if not living_heirs:
        return None
    return max(living_heirs, key=lambda h: h.age)

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
