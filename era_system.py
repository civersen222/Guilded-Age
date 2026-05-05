class EraSystem:
    HISTORIC_MOMENTS = {
        'first_tech': 3,
        'first_wonder': 5,
        'won_battle': 3,
        'founded_religion': 5,
        'met_all_civs': 3,
    }

    THRESHOLDS = {
        'dark_age': 12,
        'golden_age': 24,
    }

    def __init__(self):
        self.era_score = 0
        self.moments = set()
        self.current_era = 'Normal'

    def record_moment(self, moment_type: str) -> int:
        if moment_type in self.HISTORIC_MOMENTS and moment_type not in self.moments:
            points = self.HISTORIC_MOMENTS[moment_type]
            self.era_score += points
            self.moments.add(moment_type)
            return points
        return 0

    def check_era_transition(self) -> str:
        if self.era_score >= self.THRESHOLDS['golden_age']:
            return 'Golden'
        elif self.era_score >= self.THRESHOLDS['dark_age']:
            return 'Normal'
        return 'Dark'

    def get_era_bonuses(self, era_type: str) -> dict:
        bonuses = {
            'Golden': {'loyalty': 3, 'yields': 1.1},
            'Dark': {'loyalty': -3, 'yields': 0.9},
        }
        return bonuses.get(era_type, {})
