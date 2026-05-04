"""Comprehensive test suite for CivKings game systems."""
import unittest


class TestDiplomacyManager(unittest.TestCase):
    """Test diplomacy module."""

    def setUp(self):
        from diplomacy import DiplomacyManager
        self.dip = DiplomacyManager()
        self.dip.make_pact("Rome", "Greece", "alliance")
        self.dip.declare_war("Rome", "Persia")
        self.dip.sign_truce("Greece", "Persia", 5)
        self.dip.sign_trade_agreement("Rome", "Greece", 10)

    def test_alliance_creation(self):
        self.assertTrue(self.dip.is_allied("Rome", "Greece"))

    def test_war_status(self):
        self.assertTrue(self.dip.is_at_war("Rome", "Persia"))

    def test_truce_expiration(self):
        key = tuple(sorted(["Greece", "Persia"]))
        self.assertEqual(self.dip.truces[key], 5)
        for _ in range(5):
            self.dip.process_truces()
        self.assertNotIn(key, self.dip.truces)

    def test_trade_income(self):
        income = self.dip.get_trade_income("Rome")
        self.assertGreater(income, 0)


class TestTechManager(unittest.TestCase):
    """Test technology management."""

    def setUp(self):
        from tech import TechManager
        self.tech = TechManager()

    def test_research_availability(self):
        available = self.tech.get_available_technologies("Rome")
        self.assertIn("Agriculture", available)

    def test_research_completion(self):
        self.tech.research("Agriculture", "Rome")
        self.tech.add_research_progress("Rome", 20)
        self.assertIn("Agriculture", self.tech.researched)


class TestEventManager(unittest.TestCase):
    """Test event system."""

    def setUp(self):
        from events import EventManager
        self.em = EventManager()
        self.em.generate_events()

    def test_event_generation(self):
        self.assertGreater(len(self.em.event_pool), 0)

    def test_event_history(self):
        event = self.em.generate_event()
        self.assertIsNotNone(event)
        history = self.em.get_event_history()
        self.assertGreater(len(history), 0)


class TestAIPlayer(unittest.TestCase):
    """Test AI player logic."""

    def test_ai_action_decision(self):
        from ai import AIPlayer
        ai = AIPlayer("Rome", "medium")
        action = ai.decide_next_action([], 1, 50, 100)
        self.assertIn("type", action)
        self.assertIn("build", action)

    def test_ai_opinion_range(self):
        from ai import AIPlayer
        ai = AIPlayer("Greece", "hard")
        opinion = ai.get_opinion_on_player()
        self.assertGreaterEqual(opinion, -100)
        self.assertLessEqual(opinion, 100)


class TestGameCreation(unittest.TestCase):
    """Test game initialization."""

    def test_game_instantiation(self):
        from game_data import CIVILIZATIONS
        from game import Game
        game = Game(CIVILIZATIONS["Rome"], [CIVILIZATIONS["Greece"]])
        self.assertEqual(game.state.turn, 1)
        self.assertEqual(len(game.cities), 1)

    def test_turn_processing(self):
        from game_data import CIVILIZATIONS
        from game import Game
        game = Game(CIVILIZATIONS["Rome"], [CIVILIZATIONS["Greece"]])
        msgs = game.process_turn()
        self.assertIsInstance(msgs, list)
        self.assertGreater(len(msgs), 0)


class TestMapAndFogOfWar(unittest.TestCase):
    """Test map generation and fog of war."""

    def test_map_generation(self):
        from hex_map import HexMap
        wm = HexMap(16, 16)
        wm.generate_map(2)
        self.assertGreater(len(wm.tiles), 0)

    def test_fog_of_war(self):
        from hex_map import ExponentialFogOfWar
        fog = ExponentialFogOfWar()
        self.assertFalse(fog.is_visible(0, 0))
        fog.explored.add((0, 0))
        self.assertTrue(fog.is_explored(0, 0))


class TestCityManager(unittest.TestCase):
    """Test city management."""

    def test_city_creation(self):
        from city import City, CityManager
        cm = CityManager([])
        city = City("Rome", "Rome", (0, 0))
        cm.add_city(city)
        self.assertEqual(len(cm.cities), 1)
        self.assertEqual(city.owner, "Rome")

    def test_city_yields(self):
        from city import City
        city = City("TestCity", "Rome", (1, 1), population=5)
        yields = city.calculate_yields()
        self.assertIn("food", yields)
        self.assertIn("gold", yields)
        self.assertIn("production", yields)


class TestEconomyManager(unittest.TestCase):
    """Test economy module."""

    def test_gold_calculation(self):
        from economy import EconomyManager
        em = EconomyManager()
        em.add_gold(50)
        self.assertEqual(em.gold, 50)

    def test_trade_route_creation(self):
        from economy import EconomyManager
        em = EconomyManager()
        em.create_trade_route("Rome", "Greece", "gold")
        self.assertGreater(len(em.trade_routes), 0)


class TestReligionManager(unittest.TestCase):
    """Test religion module."""

    def test_religion_creation(self):
        from religion import ReligionManager
        rm = ReligionManager()
        religion = rm.found_religion("Monotheism", "Rome")
        self.assertIsNotNone(religion)
        self.assertEqual(religion.founder, "Rome")

    def test_faith_calculation(self):
        from religion import ReligionManager
        rm = ReligionManager()
        rm.add_faith("Rome", 25)
        self.assertEqual(rm.faith["Rome"], 25)


if __name__ == "__main__":
    unittest.main()
