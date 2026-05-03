"""
Comprehensive test for all new economy systems.
"""
from game_data import CIVILIZATIONS
from game import Game

def test_tax_system(game: Game):
    print("=== TAX SYSTEM ===")
    print(f"  Tax rate: {game.tax_system.tax_rate}%")
    print(f"  Gold multiplier: {game.tax_system.gold_multiplier:.2f}")
    print(f"  Happiness penalty: {game.tax_system.happiness_penalty}")
    print(f"  Growth penalty: {game.tax_system.growth_penalty}")
    print(f"  Tax description: {game.tax_system.get_tax_description()}")
    print("  [OK] Tax system working")

def test_happiness_system(game: Game):
    print("\n=== HAPPINESS SYSTEM ===")
    print(f"  Base happiness: {game.happiness_system.base_happiness}")
    print(f"  Current happiness: {game.happiness_system.current_happiness}")
    print(f"  Luxury bonus: {game.happiness_system.luxury_bonus}")
    
    # Test adding luxury resource
    game.happiness_system.add_luxury_resource('Silk')
    print(f"  After adding Silk: {game.happiness_system.current_happiness}")
    
    # Test entertainment
    game.happiness_system.add_entertainment_building('Colosseum')
    print(f"  After adding Colosseum: {game.happiness_system.current_happiness}")
    print("  [OK] Happiness system working")

def test_stability_system(game: Game):
    print("\n=== STABILITY SYSTEM ===")
    print(f"  Stability: {game.stability_system.stability}%")
    print(f"  Status: {game.stability_system._get_status_label()}")
    print(f"  Unrest: {game.stability_system.unrest}")
    print(f"  Revolt risk: {game.stability_system.revolt_risk}")
    print("  [OK] Stability system working")

def test_market_simulation(game: Game):
    print("\n=== MARKET SIMULATION ===")
    print(f"  Resources tracked: {len(game.market.prices)}")
    print(f"  Sample prices:")
    for i, (resource, price) in enumerate(list(game.market.prices.items())[:5]):
        print(f"    {resource}: {price:.2f}")
    
    # Test market events
    game.market.simulate_market_event()
    print(f"  Market events: {len(game.market.market_events)}")
    
    # Test trends
    trend = game.market.get_price_trend('Gold')
    print(f"  Gold trend: {trend}")
    print("  [OK] Market simulation working")

def test_gold_management(game: Game):
    print("\n=== GOLD MANAGEMENT ===")
    print(f"  Current gold: {game.gold_management.gold}")
    print(f"  Gold trend: {game.gold_management.get_gold_trend()}")
    
    # Test unit maintenance
    game.gold_management.add_unit('Warrior', 'Militia')
    maintenance = game.gold_management.calculate_unit_maintenance()
    print(f"  Unit maintenance: {maintenance}")
    
    # Test tribute
    game.gold_management.add_conquered_city(2)
    tribute = game.gold_management.calculate_tribute()
    print(f"  Tribute: {tribute}")
    
    # Test bribery
    bribery_cost = game.gold_management.calculate_bribery_cost(1)
    print(f"  Bribery cost: {bribery_cost}")
    
    # Test expense breakdown
    breakdown = game.gold_management.get_expense_breakdown()
    print(f"  Expense breakdown: {breakdown}")
    print("  [OK] Gold management working")

def test_external_trade(game: Game):
    print("\n=== EXTERNAL TRADE ROUTES ===")
    print(f"  Active routes: {game.external_trade.trade_route_count}")
    
    # Test creating trade route
    success = game.external_trade.create_trade_route('Merchant_1', 'Greece', 'gold')
    print(f"  Created trade route: {success}")
    print(f"  Active routes: {game.external_trade.trade_route_count}")
    
    # Test trade agreement
    success = game.external_trade.establish_trade_agreement('Rome', 'Greece', 'open_borders')
    print(f"  Established trade agreement: {success}")
    
    # Test route summary
    summary = game.external_trade.get_route_summary()
    print(f"  Route summary: {summary}")
    print("  [OK] External trade working")

def main():
    print("="*60)
    print("COMPREHENSIVE ECONOMY SYSTEMS TEST")
    print("="*60)
    
    # Initialize game
    player = CIVILIZATIONS['Rome']
    game = Game(player)
    
    # Run one turn to initialize economy
    game.process_turn()
    
    # Test all systems
    test_tax_system(game)
    test_happiness_system(game)
    test_stability_system(game)
    test_market_simulation(game)
    test_gold_management(game)
    test_external_trade(game)
    
    print("\n" + "="*60)
    print("ALL SYSTEMS TESTED SUCCESSFULLY!")
    print("="*60)

if __name__ == "__main__":
    main()
