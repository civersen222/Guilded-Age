# How to Play CivKings

## Starting the Game
Open a terminal in the project folder and run:
```
python main.py
```

## Main Menu
When the game starts, you'll see:
1. Start New Game
2. Load Game
3. Quit

Type `1` to start a new game.

## In-Game Commands
Once playing, you have these commands:

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

## How to Play
1. Type a command number and press Enter
2. Review the information displayed
3. Type `8` to advance to the next turn
4. Repeat — manage your empire's economy, military, research, and diplomacy over time

## Game Systems
- **Map**: Hex-based world with terrain types
- **Cities**: Manage population, production, and districts
- **Economy**: Track food, production, gold, science, and faith
- **Military**: Build units, manage promotions, morale
- **Research**: Unlock 20+ technologies across multiple branches
- **Diplomacy**: Manage relations, alliances, and trade with other factions
- **Victory**: Domination, Science, Culture, Diplomacy, or Dynasty

## File Structure
- `game.py` - Core game engine
- `ui.py` - CLI interface
- `city.py` - City management
- `military.py` - Units and combat
- `diplomacy.py` - Relations and trade
- `tech.py` - Technology research
- `events.py` - Random events
- `ai.py` - AI opponents
- `game_data.py` - All game data (units, buildings, techs, civs)
- `main.py` - Entry point
