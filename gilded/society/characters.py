"""Characters, secrets, dynasties (extracted verbatim from root simulation.py for the Gilded Machine; spec section 4)."""

from typing import Dict, List, Tuple, Set, Optional
import random
import uuid
from gilded.society.character_deepening import (
    Focus,
    FOCUSES,
    AgeProgress,
    LifeStage,
    TRAIT_DATABASE as EXTENDED_TRAIT_DATABASE,
    generate_traits,
    get_trait_description,
    get_available_traits,
    apply_traits_to_stats,
)
from gilded.society.dispositions import initial_dispositions, labels_for, inherit_dispositions, contradiction_stress, apply_drift, VICE_DRIFTS

# Deterministic character identity. uuid4 ids are process-random and make
# same-seed games irreproducible (the AI, replays, and soak tests all need
# determinism); a per-game counter gives opaque-but-reproducible ids instead.
_ID_COUNTER = 0

def _next_character_id() -> str:
    global _ID_COUNTER
    _ID_COUNTER += 1
    return format(_ID_COUNTER, "08x")

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
    # Coping vices (spec 3.5): picked up at a mental break; each drags stats.
    "Drunkard": {"resolve": -2, "command": -1},
    "Gambler": {"industry": -2, "statecraft": -1},
    "Callous": {"statecraft": -2, "resolve": -1},
    "Recluse": {"statecraft": -2, "intrigue": -1},
}

# Vices a character may adopt when stress breaks them (spec 3.5).
COPING_VICES = ("Drunkard", "Gambler", "Callous", "Recluse")

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


class Secret:
    """A fact society doesn't know (spec 3.5): lives in the persona gap.

    Discovered, held, sold or exposed by the intrigue economy (later
    missions); for now created by mental-break vices."""

    def __init__(self, kind: str, subject_id: str, description: str, potency: int):
        self.kind = kind                    # "vice", "affair", "crime"...
        self.subject_id = subject_id        # whose secret it is
        self.description = description
        self.potency = potency              # scandal power when exposed
        self.holders: Set[str] = {subject_id}   # who knows; subject always does

    def is_known_by(self, char_id: str) -> bool:
        return char_id in self.holders


class Character:
    def __init__(self, name: str, stats: Dict[str, int], traits: List[str], parent_ids: List[str] = None, age: int = 18, gender: str = "Male"):
        self.id = _next_character_id()
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

        # Spec 3.5: public persona (what society believes) vs private self
        # (self.dispositions). Secrets live in the gap between the two.
        self.persona: Dict[str, float] = dict(self.dispositions)
        self.secrets: List[Secret] = []
        
        # Section 6: Character deepening
        self.age_progress = AgeProgress(current_age=age, is_alive=True)
        self.focus = Focus()  # one Focus per adult (M51, spec 3.6)
        self.is_heir = False

        # Guardian & education (M50, spec 3.6): childhood slots.
        self.guardian = None                          # guardian character, or None
        self.education_track: Optional[str] = None    # one of ATTRIBUTES
        self.graduated = False

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
    
    def tick_focus(self) -> Optional[str]:
        """Focus (M51, spec 3.6): slow growth along the focused line.
        Returns a themed milestone line every FOCUS_MILESTONE focused
        turns, else None."""
        attr = self.focus.attribute
        if attr is None or not self.is_alive:
            return None
        if not self.focus.advance():
            return None
        self.base_stats[attr] = min(20, self.base_stats.get(attr, 8) + 1)
        from gilded.society.event_engine import Situation, render
        return render(Situation("focus_milestone", actors={"subject": self},
                                data={"focus": FOCUSES[attr], "attr": attr}))
    
    def get_effective_stat(self, stat_name: str) -> int:
        stat_name = STAT_COMPAT.get(stat_name, stat_name)  # legacy names OK
        skill_base = self.base_stats.get(stat_name, 0) + self.focus.passive(stat_name)
        bonus = 0
        for trait in self.traits:
            bonus += TRAIT_DATABASE.get(trait, {}).get(stat_name, 0)
        return skill_base + bonus

    def graduate(self) -> Optional[str]:
        """Education pays out at adulthood (M50, spec 3.6): the tracked
        attribute jumps by an amount set by guardian skill and Bloodline.
        Fires once; returns the event line, or None."""
        if self.graduated or self.age < 16 or self.education_track is None:
            return None
        self.graduated = True
        track = self.education_track
        quality = 1
        g = self.guardian
        if g is not None and getattr(g, "is_alive", False):
            quality += g.get_effective_stat(track) // 6
        bloodline = self.dispositions.get("brilliant_dull", 0.0)
        quality += int(max(0.0, -bloodline) // 25)  # Brilliant blood learns fast
        self.base_stats[track] = self.base_stats.get(track, 8) + quality
        return f"{self.name} completes a {track} education (+{quality} {track})"

    def add_stress(self, amount: int) -> Optional[str]:
        """Increase stress by amount. Returns threshold message if crossed.

        Crossing into Overwhelmed or Breaking Point triggers a mental
        break (spec 3.5): the character adopts a coping vice (once) and
        vents 100 stress."""
        if not self.is_alive:
            return None
        old_level = self.get_stress_level()
        self.stress = min(self.stress + amount, 300)
        new_level = self.get_stress_level()
        if new_level != old_level and new_level:
            if (new_level in ("Overwhelmed", "Breaking Point")
                    and not any(v in self._explicit_traits for v in COPING_VICES)):
                vice = random.choice(COPING_VICES)
                self.add_trait(vice)
                self.stress = max(self.stress - 100, 0)
                # The vice is lived in private (spec 3.5): the true spectrum
                # shifts while the public persona lags - a Secret in the gap.
                pair_key, amt = VICE_DRIFTS[vice]
                apply_drift(self, pair_key, amt, "coping vice")
                self.secrets.append(Secret(
                    "vice", self.id, f"{self.name} has secretly become {vice}", 25))
                return (f"{self.name} suffers a mental break and becomes "
                        f"{vice} (stress: {self.stress})")
            return f"{self.name} is now '{new_level}' (stress: {self.stress})"
        return None

    def reduce_stress(self, amount: int):
        """Decrease stress by amount (min 0)."""
        self.stress = max(self.stress - amount, 0)

    def check_stress_action(self, action_type: str) -> int:
        """Stress cost of an action: disposition contradiction (spec 3.5)
        plus the first matching legacy trait trigger."""
        total = contradiction_stress(self.dispositions, action_type)
        for trait in self.traits:
            if trait in PERSONALITY_TRAITS:
                key = (trait, action_type)
                if key in STRESS_TRIGGERS:
                    total += STRESS_TRIGGERS[key]
                    break
        return total

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

def reset_society_globals() -> None:
    """Return the process-global society state to a clean slate so a fresh
    game is reproducible: restart the character-id counter and drop any
    opinions left behind by a prior game in this process. One live game per
    process (the console, the soak, and the GUI all run a single game)."""
    global _ID_COUNTER
    _ID_COUNTER = 0
    opinion_matrix.clear()
    # the last-ruler memory is the other half of the society save-state
    # (relationships.get_state); a fresh game must not inherit it either.
    from gilded.society.relationships import _last_rulers  # local: avoids cycle
    _last_rulers.clear()

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

    child = Character(name, stats, child_traits, parent_ids=[parent_a.id, parent_b.id], age=0)
    # 4. Genetics (spec 3.3): Bloodline spectrums blend from the parents
    # with mutation; Temperament/Conviction re-seed near neutral.
    child.dispositions = inherit_dispositions(parent_a.dispositions, parent_b.dispositions)
    child.persona = dict(child.dispositions)  # public estimate starts honest (spec 3.5)

    # Update parents' children lists
    parent_a.children_ids.append(child.id)
    parent_b.children_ids.append(child.id)
    
    return child
