"""
CivKings - Gold Management System
Handles unit maintenance, tribute, bribery costs, and gold expenditure tracking.
"""
from typing import Dict, List, Optional, Tuple


class GoldManagement:
    """Manages gold expenditures beyond basic tax income."""

    # Unit maintenance costs per turn (gold per unit)
    UNIT_MAINTENANCE: Dict[str, float] = {
        "Militia": 0.5,
        "Infantry": 1.0,
        "Ranger": 1.5,
        "Archer": 1.0,
        "Crossbowman": 1.5,
        "Cavalry": 2.0,
        "Knight": 3.0,
        "Galleys": 1.5,
        "Ship_of_the_Line": 3.0,
        "Catapult": 2.0,
        "Trebuchet": 2.5,
        "Settler": 0.0,  # No maintenance for builders
        "Worker": 0.0,
        "Scout": 0.5,
        "Merchant": 1.0,
        "Military_Unit": 1.0,
    }

    # Tribute costs per conquered city
    TRIBUTE_PER_CITY: float = 10.0

    # Bribery costs
    BRIBERY_BASE_COST: float = 50.0
    BRIBERY_PER_CITY: float = 25.0

    def __init__(self):
        self.gold: int = 0
        self.unit_maintenance_total: float = 0.0
        self.tribute_total: float = 0.0
        self.bribery_total: float = 0.0
        self._units: Dict[str, Dict[str, any]] = {}  # unit_name -> {"type": str, ...}
        self._conquered_cities: int = 0
        self._monthly_expenses: List[Dict[str, any]] = []
        self._surplus_history: List[int] = []

    def add_unit(self, unit_name: str, unit_type: str):
        """Register a unit for maintenance tracking."""
        self._units[unit_name] = {
            "type": unit_type,
            "maintenance": self.UNIT_MAINTENANCE.get(unit_type, 1.0),
        }

    def remove_unit(self, unit_name: str):
        """Remove a unit from maintenance tracking."""
        self._units.pop(unit_name, None)

    def add_conquered_city(self, count: int = 1):
        """Record conquered cities (for tribute)."""
        self._conquered_cities += count

    def calculate_unit_maintenance(self) -> float:
        """Calculate total gold cost for unit maintenance."""
        total = 0.0
        for unit_data in self._units.values():
            total += unit_data["maintenance"]
        self.unit_maintenance_total = total
        return total

    def calculate_tribute(self) -> float:
        """Calculate total tribute from conquered cities."""
        self.tribute_total = self._conquered_cities * self.TRIBUTE_PER_CITY
        return self.tribute_total

    def calculate_bribery_cost(self, target_cities: int = 1) -> float:
        """Calculate gold cost to bribe enemy cities."""
        return self.BRIBERY_BASE_COST + (target_cities * self.BRIBERY_PER_CITY)

    def process_monthly_expenses(self, income: int) -> Dict[str, any]:
        """Process all monthly gold expenses."""
        # Calculate all expenses
        unit_maintenance = self.calculate_unit_maintenance()
        tribute = self.calculate_tribute()
        
        total_income = income
        total_expenses = unit_maintenance + tribute + self.bribery_total
        
        surplus = total_income - total_expenses
        
        # Record expense summary
        expense_summary = {
            "income": total_income,
            "unit_maintenance": round(unit_maintenance, 2),
            "tribute": round(tribute, 2),
            "bribery": round(self.bribery_total, 2),
            "total_expenses": round(total_expenses, 2),
            "surplus_deficit": surplus,
        }
        
        self._monthly_expenses.append(expense_summary)
        self._surplus_history.append(surplus)
        
        # Cap history
        if len(self._monthly_expenses) > 12:
            self._monthly_expenses = self._monthly_expenses[-12:]
        if len(self._surplus_history) > 12:
            self._surplus_history = self._surplus_history[-12:]
        
        return expense_summary

    def get_gold_trend(self) -> str:
        """Get gold trend arrow."""
        if len(self._surplus_history) < 2:
            return "SAME"
        
        recent = self._surplus_history[-3:]
        if sum(recent) > 0:
            return "UP"
        elif sum(recent) < 0:
            return "DOWN"
        return "SAME"

    def can_afford(self, amount: float) -> bool:
        """Check if we can afford a purchase."""
        return self.gold >= amount

    def spend_gold(self, amount: float, description: str = "") -> bool:
        """Spend gold if available."""
        if self.gold >= amount:
            self.gold -= amount
            if description:
                self._monthly_expenses[-1]["spending"] = description
            return True
        return False

    def get_expense_breakdown(self) -> Dict[str, float]:
        """Get detailed expense breakdown."""
        return {
            "unit_maintenance": round(self.unit_maintenance_total, 2),
            "tribute": round(self.tribute_total, 2),
            "bribery": round(self.bribery_total, 2),
            "total": round(self.unit_maintenance_total + self.tribute_total + self.bribery_total, 2),
        }

    def get_recent_expenses(self) -> List[Dict[str, any]]:
        """Get recent monthly expense summaries."""
        return self._monthly_expenses[-6:]  # Last 6 months
