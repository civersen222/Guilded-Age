"""Tests for economy.py — TradeRoute and EconomyManager."""
import unittest


class TestTradeRoutes(unittest.TestCase):
    """Test trade route creation and processing."""

    def setUp(self):
        from economy import EconomyManager
        self.economy = EconomyManager()

    def test_trade_routes(self):
        """Test that creating and processing trade routes adds gold correctly."""
        # Create a trade route
        result = self.economy.create_trade_route("Rome", "Athens", gold=10)
        self.assertTrue(result)

        # Verify the route was added
        self.assertEqual(len(self.economy.trade_routes), 1)
        route = self.economy.trade_routes[0]
        self.assertEqual(route.source_city, "Rome")
        self.assertEqual(route.dest_city, "Athens")
        self.assertEqual(route.gold_per_turn, 10)
        self.assertEqual(route.turns_active, 1)

        # Process trade routes — should collect gold
        total = self.economy.process_trade_routes()
        self.assertEqual(total, 10)
        self.assertEqual(self.economy.gold, 10)
        self.assertEqual(route.turns_active, 2)

        # Process again — another 10 gold
        total = self.economy.process_trade_routes()
        self.assertEqual(total, 10)
        self.assertEqual(self.economy.gold, 20)
        self.assertEqual(route.turns_active, 3)

    def test_multiple_trade_routes(self):
        """Test multiple trade routes accumulate gold correctly."""
        self.economy.create_trade_route("Rome", "Athens", gold=10)
        self.economy.create_trade_route("Rome", "Carthage", gold=15)

        total = self.economy.process_trade_routes()
        self.assertEqual(total, 25)
        self.assertEqual(self.economy.gold, 25)

    def test_trade_route_tick(self):
        """Test that tick() increments turns_active."""
        from economy import TradeRoute
        route = TradeRoute("Rome", "Athens", gold_per_turn=5)
        self.assertEqual(route.turns_active, 0)
        route.tick()
        self.assertEqual(route.turns_active, 1)
        route.tick()
        self.assertEqual(route.turns_active, 2)


if __name__ == "__main__":
    unittest.main()
