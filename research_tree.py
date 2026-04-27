"""
CivKings - Research Tree (Directed Graph)
Handles technology tree traversal, science pool, cost calculation,
prerequisite validation, and auto-unlock of dependent technologies.
"""
from typing import Dict, List, Set, Optional, Tuple
from game_data import TECHNOLOGIES, Technology, TechBranch, Era


class ResearchTree:
    """Directed-graph technology research system.

    - Tracks unlocked technologies, current research, and science pool.
    - Validates prerequisites before research.
    - Auto-unlocks technologies whose *all* prerequisites are now met
      (once their cost is paid).
    - Provides era progression and tech modifiers.
    """

    def __init__(self):
        self.unlocked_techs: Set[str] = set()
        self.science_pool: float = 0.0
        self.current_research: Optional[str] = None
        self.research_progress: int = 0
        self._modifiers: Dict[str, float] = {
            "attack_mod": 1.0,
            "production_mod": 1.0,
            "science_mod": 1.0,
            "gold_mod": 1.0,
        }

    # ── Core API ──────────────────────────────────────────────────────

    def add_science(self, amount: float) -> None:
        """Add science to the global science pool."""
        self.science_pool += amount

    def unlock_tech(self, tech_name: str) -> bool:
        """Research and unlock a technology.

        Returns True if unlocked (or already unlocked), False otherwise.
        """
        if tech_name not in TECHNOLOGIES:
            return False

        if tech_name in self.unlocked_techs:
            return True

        tech = TECHNOLOGIES[tech_name]

        # Check prerequisites
        if not self._prerequisites_met(tech):
            return False

        # Check cost
        cost = self.get_cost(tech_name)
        if self.science_pool < cost:
            return False

        # Pay cost and unlock
        self.science_pool -= cost
        self.unlocked_techs.add(tech_name)

        # Apply tech modifiers
        self._apply_modifiers(tech)

        # Auto-unlock dependent techs
        self._auto_unlock_dependents()

        return True

    def get_researchable_techs(self, min_era: Optional[Era] = None) -> List[str]:
        """Return all technologies that can be researched right now.

        A tech is researchable when:
        - It is not already unlocked.
        - All prerequisites are satisfied.
        - Its era is >= min_era (if provided).
        """
        candidates = []
        for name, tech in TECHNOLOGIES.items():
            if name in self.unlocked_techs:
                continue
            if min_era is not None and tech.era < min_era:
                continue
            if self._prerequisites_met(tech):
                candidates.append(name)
        return candidates

    def get_cost(self, tech_name: str) -> int:
        """Get the research cost of a technology."""
        if tech_name not in TECHNOLOGIES:
            return 0
        return TECHNOLOGIES[tech_name].cost

    def get_modifiers(self) -> Dict[str, float]:
        """Return current tech modifiers."""
        return self._modifiers.copy()

    def get_current_era(self) -> Era:
        """Return the current era based on unlocked technologies."""
        if not self.unlocked_techs:
            return Era.ANCIENT

        eras = sorted(
            [TECHNOLOGIES[name].era for name in self.unlocked_techs],
            key=lambda e: list(Era).index(e),
            reverse=True,
        )
        return eras[0]

    def get_techs_in_era(self, era: Era) -> List[str]:
        """Return all technologies belonging to a given era."""
        return [
            name for name, tech in TECHNOLOGIES.items() if tech.era == era
        ]

    def get_tech_branch_count(self, branch: TechBranch) -> int:
        """Return number of unlocked techs in a branch."""
        return sum(
            1 for name in self.unlocked_techs
            if TECHNOLOGIES[name].branch == branch
        )

    # ── Internal Helpers ──────────────────────────────────────────────

    def _prerequisites_met(self, tech: Technology) -> bool:
        """Check if all prerequisites of a tech are unlocked."""
        for prereq in tech.prerequisites:
            if prereq not in self.unlocked_techs:
                return False
        return True

    def _apply_modifiers(self, tech: Technology) -> None:
        """Apply bonus modifiers from a newly unlocked technology."""
        bonus = tech.bonus
        if not bonus:
            return

        # Parse common bonus patterns
        if "attack" in bonus.lower():
            # Extract percentage from "+10% attack" or similar
            if "%" in bonus:
                val = int(bonus.split("%")[0].replace("+", "").strip())
                self._modifiers["attack_mod"] += val / 100.0
            elif "attack" in bonus.lower():
                self._modifiers["attack_mod"] += 0.1

        if "production" in bonus.lower():
            if "%" in bonus:
                val = int(bonus.split("%")[0].replace("+", "").strip())
                self._modifiers["production_mod"] += val / 100.0
            else:
                self._modifiers["production_mod"] += 0.1

        if "science" in bonus.lower():
            if "%" in bonus:
                val = int(bonus.split("%")[0].replace("+", "").strip())
                self._modifiers["science_mod"] += val / 100.0
            else:
                self._modifiers["science_mod"] += 0.1

        if "gold" in bonus.lower():
            if "%" in bonus:
                val = int(bonus.split("%")[0].replace("+", "").strip())
                self._modifiers["gold_mod"] += val / 100.0
            else:
                self._modifiers["gold_mod"] += 0.1

    def _auto_unlock_dependents(self) -> None:
        """Auto-unlock technologies whose prerequisites are now all met.

        This is called after each successful unlock to cascade through the
        dependency graph.
        """
        changed = True
        while changed:
            changed = False
            for name, tech in TECHNOLOGIES.items():
                if name in self.unlocked_techs:
                    continue
                if self._prerequisites_met(tech):
                    cost = self.get_cost(name)
                    if self.science_pool >= cost:
                        self.science_pool -= cost
                        self.unlocked_techs.add(name)
                        self._apply_modifiers(tech)
                        changed = True
                        break  # Restart loop since prerequisites changed

    def reset(self) -> None:
        """Reset the research tree (for game restart)."""
        self.unlocked_techs.clear()
        self.science_pool = 0.0
        self.current_research = None
        self.research_progress = 0
        self._modifiers = {
            "attack_mod": 1.0,
            "production_mod": 1.0,
            "science_mod": 1.0,
            "gold_mod": 1.0,
        }
