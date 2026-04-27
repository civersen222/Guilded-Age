# CivKings - Dynasty & Conquest

A hybrid strategy game combining Civilization's empire-building with Crusader Kings' dynasty mechanics.

## Features

- **Civilization Building**: Expand your empire with cities, districts, and wonders
- **Technology Research**: Progress through eras from Ancient to Information
- **Military Conquest**: Command units, siege cities, and manage logistics
- **Diplomacy**: Form alliances, trade routes, and manage relations
- **Crusader Kings Elements**: Character traits, succession laws, government types
- **AI Opponents**: Multiple difficulty levels with strategic priorities
- **Random Events**: Dynamic world with crises and opportunities

## Installation

No dependencies required. Runs on Python 3.7+.

```bash
python main.py
```

## Game Systems

- **Map**: Hex-based world with terrain types and fog of war
- **Cities**: Population-driven production with district placement
- **Economy**: Food, production, gold, science, and faith
- **Military**: Unit types, promotions, morale, and supply lines
- **Research**: 20+ technologies across multiple branches
- **Diplomacy**: Opinion-based relations with alliances and trade
- **Events**: Random world events affecting gameplay
- **Victory**: Domination, Science, Culture, Diplomacy, or Dynasty

## Controls

| Command | Action |
|---------|--------|
| 1 | View Map |
| 2 | View Cities |
| 3 | View Units |
| 4 | Research Tech |
| 5 | Production |
| 6 | Diplomacy |
| 7 | Events |
| 8 | Next Turn |
| 9 | Save Game |
| 10 | Quit |

## File Structure

```
game.py      - Core game engine
ui.py        - CLI interface
city.py      - City management
military.py  - Units and combat
diplomacy.py - Relations and trade
tech.py      - Technology research
events.py    - Random events
ai.py        - AI opponents
game_data.py - All game data (units, buildings, techs, civs)
main.py      - Entry point
```

## License

Private project.
