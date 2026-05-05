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
- **Dynasty System**: Ruler stats, traits, court positions, and family trees

## Installation

Requires Python 3.10+ with pygame-ce and pygame_gui:

```bash
pip install pygame-ce pygame_gui
python main.py
```

## Game Controls

| Control | Action |
|---------|--------|
| Left Click | Select hex/city/unit |
| Middle Mouse Drag | Pan camera |
| Mouse Wheel | Zoom in/out |
| WASD / Arrow Keys | Pan camera |
| Home | Center camera on capital |
| Enter | Next Turn |
| Tech Tree Button | Open technology tree |
| Diplomacy Button | Open diplomacy panel |

## Game Systems

- **Map**: Hex-based world with terrain types, fog of war, camera pan/zoom
- **Cities**: Population-driven production with district placement and buildings
- **Economy**: Food, production, gold, science, culture, and faith management
- **Military**: Unit types, promotions, morale, and combat resolution
- **Research**: 20+ technologies across multiple branches and eras
- **Diplomacy**: Opinion-based relations with alliances, treaties, and trade
- **Events**: Random world events with choices and consequences
- **Victory**: Domination, Science, Culture, Religious, or Dynasty
- **Audio**: Era-based background music and sound effects

## File Structure

```
game.py              - Core game engine
hex_map.py           - Hex grid and tile generation
city.py              - City management
military.py          - Units and combat
diplomacy.py         - Relations and trade
tech.py              - Technology research
events.py            - Random events
ai.py                - AI opponents
game_data.py         - All game data (units, buildings, techs, civs)
save_system.py       - Save/load with cycle detection
pygame_app/          - Full Pygame GUI
  app.py             - Main application loop
  screens/           - Main menu, game screen
  panels/            - Resource bar, city panel, event log, action bar
  popups/            - Production, tech tree, diplomacy, combat, events
  map/               - Camera, hex renderer, minimap, tile atlas
  audio/             - Sound manager, music manager
  effects/           - Particle effects
main.py              - Entry point
```

## License

Private project.
