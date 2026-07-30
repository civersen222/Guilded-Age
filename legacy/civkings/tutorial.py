"""Guided tutorial system for new players — first 10 turns."""


class Tutorial:
    """Interactive tutorial that guides players through early game."""

    STEPS = [
        {"turn": 1, "trigger": "turn_start", "message": "Welcome to CivKings! Click your city on the map to select it."},
        {"turn": 1, "trigger": "city_selected", "message": "Good! Now click Production to start building a Warrior."},
        {"turn": 2, "trigger": "turn_start", "message": "Open the Tech Tree (T) and select a technology to research."},
        {"turn": 3, "trigger": "turn_start", "message": "Select your military unit and move it to explore."},
        {"turn": 5, "trigger": "turn_start", "message": "Check Diplomacy (D) if you have met other civilizations."},
        {"turn": 8, "trigger": "turn_start", "message": "Your dynasty shapes your empire. Press Y to view your ruler."},
        {"turn": 10, "trigger": "turn_start", "message": "Tutorial complete! Your dynasty awaits. Good luck, ruler."},
    ]

    def __init__(self):
        self.step = 0
        self.active = True
        self.completed = False
        self._processed_triggers: set = set()

    def check_trigger(self, turn: int, event_type: str) -> str | None:
        """Check if a trigger matches the current step. Returns message or None."""
        if not self.active or self.completed:
            return None

        key = (turn, event_type)
        if key in self._processed_triggers:
            return None

        for i in range(self.step, len(self.STEPS)):
            s = self.STEPS[i]
            if s["turn"] == turn and s["trigger"] == event_type:
                self._processed_triggers.add(key)
                self.step = i + 1
                return s["message"]
            if s["turn"] > turn:
                break

        return None

    def advance(self):
        """Move to the next tutorial step without showing a message."""
        if self.step < len(self.STEPS):
            self.step += 1

    def skip(self):
        """Skip the entire tutorial."""
        self.completed = True
        self.active = False

    @property
    def is_done(self) -> bool:
        return self.completed or self.step >= len(self.STEPS)
