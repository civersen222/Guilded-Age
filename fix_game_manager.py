content = open('C:\\Users\\civer\\civkings\\game_manager.py', 'r').read()

old1 = '''        Civilization(
            name="Rome",
            starting_gold=100,
            starting_science=50,
            starting_culture=25,
            starting_diplomacy=25,
            starting_stats={
                "diplomacy": 10,
                "martial": 12,
                "stewardship": 11,
                "intrigue": 8,
            },
            starting_traits=["Warrior", "Diplomat"],
        ),'''

new1 = '''        Civilization(
            "Rome", "Legion", "Wall", "+10% melee combat strength", "Republic",
            ["Iron Working", "Masonry"], "white",
            100, 50, 25,
            {"diplomacy": 10, "martial": 12, "stewardship": 11, "intrigue": 8},
            ["Warrior", "Diplomat"],
        ),'''

old2 = '''        Civilization(
            name="Greece",
            starting_gold=80,
            starting_science=70,
            starting_culture=40,
            starting_diplomacy=30,
            starting_stats={
                "diplomacy": 12,
                "martial": 9,
                "stewardship": 10,
                "intrigue": 11,
            },
            starting_traits=["Scholar", "Diplomat"],
        ),'''

new2 = '''        Civilization(
            "Greece", "Phalanx", "", "+1 science from all tiles", "Republic",
            ["Philosophy", "Pottery"], "lightblue",
            80, 70, 40,
            {"diplomacy": 12, "martial": 9, "stewardship": 10, "intrigue": 11},
            ["Scholar", "Diplomat"],
        ),'''

old3 = '''        Civilization(
            name="Egypt",
            starting_gold=120,
            starting_science=40,
            starting_culture=30,
            starting_diplomacy=20,
            starting_stats={
                "diplomacy": 8,
                "martial": 11,
                "stewardship": 13,
                "intrigue": 9,
            },
            starting_traits=["Industrious", "Warrior"],
        ),'''

new3 = '''        Civilization(
            "Egypt", "", "Pyramid", "Wonders cost 20% less", "Theocracy",
            ["Writing", "Agriculture"], "#f5deb3",
            120, 40, 30,
            {"diplomacy": 8, "martial": 11, "stewardship": 13, "intrigue": 9},
            ["Industrious", "Warrior"],
        ),'''

content = content.replace(old1, new1)
content = content.replace(old2, new2)
content = content.replace(old3, new3)
open('C:\\Users\\civer\\civkings\\game_manager.py', 'w').write(content)
print('Done')
