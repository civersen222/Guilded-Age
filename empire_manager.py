from typing import Dict, List, Tuple, Optional, Union
from simulation import Character
from hex_map import WorldMap
from city import City
from military import Unit

class SuccessionManager:
    def __init__(self, law: str = 'Primogeniture'):
        self.law = law

    def handle_death(self, ruler: Character, cities: List[City], all_chars: Dict[str, Character]):
        print(f"Ruler {ruler.name} has passed away. Applying {self.law}...")
        ruler.is_alive = False
        
        # Find living children
        heirs = []
        for cid in ruler.children_ids:
            char = all_chars.get(cid)
            if char and char.is_alive:
                heirs.append(char)
        
        if not heirs:
            print(f"Ruler {ruler.name} died without heirs! Empire fragments.")
            # Fragmentation: Cities become independent or go to strongest vassal (simplified: no owner)
            for city in cities:
                if city.owner == ruler:
                    city.owner = None
                    city.governor = None
                    print(f"City {city.name} has become an independent city-state.")
            return

        if self.law == 'Primogeniture':
            # Eldest child inherits all (assuming first in children_ids is eldest)
            heir = heirs[0]
            for city in cities:
                if city.owner == ruler:
                    city.owner = heir
                    city.governor = heir
            print(f"All titles and cities pass to the eldest heir: {heir.name}")
            
        elif self.law == 'Gavelkind':
            # Distribute cities equally
            ruler_cities = [c for c in cities if c.owner == ruler]
            for i, city in enumerate(ruler_cities):
                heir = heirs[i % len(heirs)]
                city.owner = heir
                city.governor = heir
            print(f"Cities have been partitioned among {len(heirs)} heirs.")

class VassalageManager:
    def __init__(self, tax_rate: float = 0.1):
        self.tax_rate = tax_rate

    def collect_taxes(self, cities: List[City], liege: Character):
        total_tax = 0.0
        for city in cities:
            # If city owner is not the liege, they are a vassal
            if city.owner and city.owner != liege:
                # Only collect if the owner's liege is the specified liege
                # (Assuming a simple 1-level vassalage for this simulation)
                yields = city.calculate_total_yields()
                tax = yields['gold'] * self.tax_rate
                city.owner.gold_reserve -= tax
                total_tax += tax
                print(f"Collected {tax:.2f} gold from {city.owner.name} ({city.name})")
        
        liege.gold_reserve += total_tax
        print(f"Liege {liege.name} received total taxes: {total_tax:.2f}")

def found_city(settler_unit: Unit, character: Character, coords: Tuple[int, int], world_map: WorldMap) -> City:
    print(f"Character {character.name} is founding a city at {coords} using {settler_unit.name}!")
    new_city = City(f"{character.name}'s Landing", coords, world_map, character)
    return new_city

if __name__ == "__main__":
    from simulation import Character, generate_child
    
    # Setup
    world = WorldMap()
    world.generate_map(5)
    registry = {}
    def register(c):
        registry[c.id] = c
        return c

    # Create Characters
    king = register(Character("King Highroad", {"diplomacy": 10, "martial": 10, "stewardship": 20, "intrigue": 10}, ["Industrious"]))
    queen = register(Character("Queen Highroad", {"diplomacy": 15, "martial": 5, "stewardship": 10, "intrigue": 10}, ["Charismatic"]))
    
    child1 = register(generate_child("Prince Eldest", king, queen))
    child2 = register(generate_child("Prince Youngest", king, queen))
    
    # Found a city
    settler = Unit("Settler", 50)
    capital = found_city(settler, king, (0, 0), world)
    
    # Setup Vassalage
    vassal_char = register(Character("Duke Lowland", {"diplomacy": 5, "martial": 10, "stewardship": 10, "intrigue": 5}, []))
    vassal_city = found_city(settler, vassal_char, (1, 0), world)
    
    cities = [capital, vassal_city]
    
    # Tax collection
    vm = VassalageManager(tax_rate=0.2)
    vm.collect_taxes(cities, king)
    
    # Succession
    sm = SuccessionManager(law='Primogeniture')
    sm.handle_death(king, cities, registry)
    
    print(f"New owner of capital: {capital.owner.name if capital.owner else 'None'}")
