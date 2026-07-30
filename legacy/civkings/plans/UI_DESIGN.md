# CivKings GUI Design Document

## 1. Architecture Overview

### Tech Stack
- **GUI Framework**: `tkinter` (Python stdlib, no pip install needed)
- **Game Engine**: Existing `game.py`, `hex_map.py`, `city.py`, `military.py`, etc.
- **Data Layer**: `game_data.py` (all static data), `economy.py`, `tech.py`
- **Entry Point**: `main.py` will launch `CivKingsGUI` instead of the CLI text loop

### Top-Level Widget Structure
```
┌─────────────────────────────────────────────────────────────────┐
│  Menu Bar: File, Edit, View, Help                               │
├──────────────────┬──────────────────────────────────────────────┤
│  Sidebar         │  Main Canvas                                 │
│  (250px)         │  (flexible)                                  │
│                  │                                              │
│  Empire          │  Map / City / Tech / Diplomacy panels        │
│  Overview        │  (context-sensitive)                         │
│                  │                                              │
│  ┌────────────┐  │                                              │
│  │ Economy    │  │                                              │
│  │ Panel      │  │                                              │
│  └──────┬─────┘  │                                              │
│         │        │                                              │
│  ┌──────▼─────┐  │                                              │
│  │ Units      │  │                                              │
│  │ Panel      │  │                                              │
│  └──────┬─────┘  │                                              │
│         │        │                                              │
│  ┌──────▼─────┐  │                                              │
│  │ Character  │  │                                              │
│  │ Panel      │  │                                              │
│  └──────┬─────┘  │                                              │
│         │        │                                              │
│  ┌──────▼─────┐  │                                              │
│  │ Events     │  │                                              │
│  │ Log        │  │                                              │
│  └──────┬─────┘  │                                              │
├──────────┴────────┴──────────────────────────────────────────────┤
│  Status Bar: Turn, Phase, Selected Info, Coordinates              │
├──────────────────────────────────────────────────────────────────┤
│  Action Bar: Context-sensitive action buttons                     │
└──────────────────────────────────────────────────────────────────┘
```

### View Modes
The main canvas switches between these views:
1. **Map View** (default) — hex grid with cities, units, resources, fog
2. **City View** — when a city is selected, show district grid, production queue, yields
3. **Tech View** — technology tree with research progress
4. **Diplomacy View** — relations table between civs
5. **Character View** — character sheet, dynasty tree, traits
6. **Military View** — army composition, unit details

---

## 2. Map Rendering

### Hex Grid on Canvas
- Use `canvas.create_polygon()` for hex tiles (pointy-top hexagons)
- Tile size: ~30px wide, adjustable via zoom slider
- Offset every other row for hex staggering
- Pan via drag, zoom via slider

### Tile Rendering
Each tile draws:
- **Terrain fill color**: Green (plains), dark green (forest), brown (hills), gray (mountain), blue (water), yellow (desert), white (tundra)
- **Terrain symbol**: Small icon or character overlay
- **Resource indicator**: Dot or letter overlay
- **City**: Circle with civ color and city name
- **Unit**: Small rectangle with civ color and unit type abbreviation
- **Fog of war**: Unexplored tiles drawn with `?` on dark background; explored but unvisited tiles drawn with dim

### Tile Color Reference
| Terrain | Fill Color | Symbol |
|---------|-----------|--------|
| Plains | `#4a8f4a` | `·` |
| Grassland | `#5cb85c` | `·` |
| Forest | `#2d5a27` | `F` |
| Hills | `#8b7355` | `^` |
| Mountain | `#6c6c6c` | `▲` |
| Desert | `#d4a843` | `·` |
| Tundra | `#d0e4e8` | `·` |
| Coast | `#4a90a4` | `~` |
| Ocean | `#3a7ca5` | `≈` |

### Interaction
- **Click** on a tile to select it
- **Right-click** on a unit/city for context menu
- **Double-click** on a city to switch to city view
- **Hover** to show tile info tooltip

---

## 3. Sidebar Panels

### Economy Panel
```
Economy
┌──────────────────┐
│ Gold:    1,250   │
│ Science:   890   │
│ Food:    3,420   │
│ Culture:   120   │
│ Faith:     45    │
└──────────────────┘
```
- Labels on left, values on right
- Green text for positive income, red for negative
- Auto-refreshes every turn

### Units Panel
```
Military
┌──────────────────────┐
│ Total Units: 12      │
│ Attack Power: 145    │
│ Defense Power: 128   │
│                      │
│ ┌─Militia────────┐   │
│ │ Att:5 Def:6    │   │
│ │ HP:80/100      │   │
│ │ Pos: (5,7)     │   │
│ └────────────────┘   │
│ ┌─Archer─────────┐   │
│ │ Att:8 Def:5    │   │
│ │ HP:100/100     │   │
│ │ Pos: (6,7)     │   │
│ └────────────────┘   │
└──────────────────────┘
```
- Scrollable list of player's units
- Click a unit to select it on the map
- Shows abbreviated stats

### Character Panel
```
Ruler
┌──────────────────────┐
│ Name: Alexander      │
│ Age: 32              │
│                      │
│ Diplomacy:    ★★★★★  │
│ Martial:      ★★★★   │
│ Stewardship:  ★★★★★  │
│ Intrigue:     ★★★    │
│                      │
│ Traits: Charismatic  │
│         Ambitious    │
└──────────────────────┘
```
- Shows current ruler
- Trait list, stats
- Click to see full dynasty

### Events Log Panel
```
Events
┌──────────────────────────────────────┐
│ [Turn 5]  Barbarians spotted!        │
│ [Turn 8]  New trade route established│
│ [Turn 12] Discovery: Iron!           │
│ [Turn 15] Diplomatic envoy arrived!  │
│ [Turn 18] City founded: New Rome     │
│ [Turn 20] Technology: Archery!       │
│ [Turn 23] Religious schism detected  │
│ [Turn 25] Barbarian raid repelled!   │
└──────────────────────────────────────┘
```
- Auto-scrolling log
- Click an event for more details
- Newest at bottom

---

## 4. Main Canvas Views

### Map View (Default)
```
┌──────────────────────────────────────────────────────┐
│    ▲  F  ·  ·  F  ▲                               │
│    ·  ^  ~  ·  ·  ·                               │
│  C  ·  ·  F  ^  ·  ·  C  ≈  ≈                     │
│    ·  F  ·  ·  ^  ·                               │
│    ▲  ·  ~  ·  ·  ·                               │
│    ·  ·  ·  F  ·  ▲                               │
└──────────────────────────────────────────────────────┘
```
- Hex grid rendering
- Selected tile highlighted with border
- City names shown near city hexes
- Unit names shown near unit hexes
- Zoom slider at bottom-right
- Pan via mouse drag

### City View
```
City: New Rome
┌──────────────────────────────────────────┐
│ Population: 12 | Happiness: 8 | Gold: 120│
│                                          │
│ Districts:                               │
│ ┌─────────┬─────────┬─────────┐         │
│ │ Campus  │ Market  │ Temple  │         │
│ │ (built) │ (built) │ (built) │         │
│ └─────────┴─────────┴─────────┘         │
│                                          │
│ Buildings:                               │
│ • Granary (+3 food)                      │
│ • Library (+3 science)                   │
│ • Barracks (+10 defense)                 │
│                                          │
│ Production Queue:                        │
│ [1] Swordsman (60/100) [▓▓▓▓░░░░]      │
│ [2] Archer (40/100) [▓▓░░░░░░░░]        │
│                                          │
│ Yields: Food:+8 Gold:+5 Sci:+4           │
│                                          │
│ [Build District] [Build Unit] [Build Bldg]│
└──────────────────────────────────────────┘
```
- Grid of district slots
- Progress bars for production
- Action buttons at bottom

### Tech View
```
Technology: Archery
┌──────────────────────────────────────────┐
│ Era: Classical                             │
│ Cost: 60 research points                   │
│ Unlocks: Archers, Crossbowmen              │
│ Prerequisites: Bronze Working              │
│                                          │
│ Research Progress: 45/60 [▓▓▓▓▓░░░░░]    │
│                                          │
│ Available Technologies:                    │
│ [✓] Agriculture (Ancient)                  │
│ [✓] Bronze Working (Ancient)               │
│ [ ] Archery (Classical) [45/60]            │
│ [ ] Pottery (Classical) [0/45]             │
│ [ ] Writing (Classical) [0/55]             │
│ [ ] Bronze Working (Ancient) [✓]           │
│                                          │
│ [Research Archery] [Back to Map]           │
└──────────────────────────────────────────┘
```
- Tree layout or list layout
- Click to select for research
- Progress bars for in-progress techs

### Diplomacy View
```
Diplomacy
┌────────────┬────────┬────────┬───────────┐
│            │ Rome   │ Egypt  │ Greece    │
├────────────┼────────┼────────┼───────────┤
│ Rome       │  —     │ 50     │ 30        │
│ Egypt      │ 45     │  —     │ 20        │
│ Greece     │ 25     │ 35     │  —        │
└────────────┴────────┴────────┴───────────┘

Actions: [Declare War] [Declare Peace] [Trade] [Declare Friendship]
```
- Relations table
- Action buttons depend on selected civ

### Character View
```
Character Sheet
┌──────────────────────────────────────────┐
│ Dynasty: Alexander                       │
│                                          │
│ ┌─Alexander (L)───────┐                  │
│ │ Age: 32  Male        │                 │
│ │ Dipl:5 Mart:4        │                 │
│ │ Traits: Charismatic  │                 │
│ └──────┬───────────────┘                 │
│        │                                 │
│   ┌────▼─────┐  ┌────────┐               │
│   │ Perdiccas│  │ Phil  │                │
│   │ Age:28   │  │ Age:24 │               │
│   │ Dipl:3   │  │ Mart:5 │               │
│   └──────────┘  └────────┘               │
│                                          │
│ [View Dynasty Tree] [View Ruler Sheet]   │
└──────────────────────────────────────────┘
```
- Tree or list of dynasty members
- Click to view full character sheet

### Military View
```
Military Overview
┌──────────────────────────────────────────┐
│ Total Units: 12                          │
│ Attack: 145  Defense: 128                │
│                                          │
│ Unit Type    Count  Total Atk  Total Def │
│ ───────────────────────────────────────  │
│ Militia      4     20         24         │
│ Swordsman    3     30         30         │
│ Archer       3     24         15         │
│ Knight       2     26         20         │
│ Siege Tower  1     14          3         │
│                                          │
│ ┌────────────────────────────────────┐   │
│ │ Selected: Swordsman #3             │   │
│ │ HP: 80/100  XP: 15  Pos: (5,7)    │   │
│ │ Promotions: Veteran                │   │
│ │ [Move] [Attack] [Fortify] [Dismiss]│   │
│ └────────────────────────────────────┘   │
└──────────────────────────────────────────┘
```
- Summary table
- Detailed unit info with actions

---

## 5. Input Handling

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `N` | Next turn |
| `M` | Switch to Map view |
| `C` | Switch to City view (when city selected) |
| `T` | Switch to Tech view |
| `D` | Switch to Diplomacy view |
| `1-6` | Quick-switch between views |
| `Esc` | Deselect / go back |
| `S` | Save game |
| `L` | Load game |
| `+/-` | Zoom in/out |
| `WASD` | Pan map (in map view) |
| `Enter` | Confirm action |

### Mouse Actions
- **Left-click**: Select tile/unit/city
- **Right-click**: Context menu
- **Left-double-click**: Open city view
- **Scroll wheel**: Zoom in/out
- **Drag**: Pan map
- **Click action button**: Execute action

### Context Menu (Right-click)
When right-clicking on:
- **Tile**: Show tile info
- **Unit**: Move, Attack, Fortify, Dismiss
- **City**: Build District, Build Unit, Build Building, Change Production, Found City
- **Map background**: Pan to this location

---

## 6. Action Bar

Context-sensitive button row at the bottom:

| View | Buttons |
|------|---------|
| Map | [Next Turn] [Pan] [Zoom +] [Zoom -] [Select Unit] [Select City] |
| City | [Next Turn] [Build District] [Build Unit] [Build Building] [Change Production] |
| Tech | [Next Turn] [Research Tech] [Back to Map] |
| Diplomacy | [Next Turn] [Declare War] [Declare Peace] [Trade] [Declare Friendship] |
| Character | [Next Turn] [View Dynasty] [View Ruler] |
| Military | [Next Turn] [Move] [Attack] [Fortify] [Dismiss] |

---

## 7. Status Bar

Always visible at the bottom:
```
Turn: 15  |  Phase: Player  |  Selected: Swordsman (5,7)  |  Gold: 120  |  [Next Turn]
```

---

## 8. Color Scheme

### Theme: Dark
```
Background:      #1a1a2e
Sidebar BG:      #16213e
Main BG:         #0f3460
Text:            #e8e8e8
Muted Text:      #a0a0a0
Accent:          #e94560
Highlight:       #533483
Success:         #4caf50
Warning:         #ff9800
Error:           #f44336
Border:          #2a2a4a
```

### Theme: Light
```
Background:      #f5f5f5
Sidebar BG:      #e8e8e8
Main BG:         #ffffff
Text:            #222222
Muted Text:      #666666
Accent:          #d32f2f
Highlight:       #3f51b5
Success:         #388e3c
Warning:         #f57c00
Error:           #d32f2f
Border:          #cccccc
```

---

## 9. File Structure

```
civkings/
├── main.py              # Entry point - launches GUI
├── gui.py               # Main GUI class (CivKingsGUI)
├── gui_map.py           # Map canvas widget
├── gui_city.py          # City view widget
├── gui_tech.py          # Tech tree widget
├── gui_diplomacy.py     # Diplomacy widget
├── gui_character.py     # Character/dynasty widget
├── gui_military.py      # Military overview widget
├── gui_sidebar.py       # Sidebar panels
├── gui_statusbar.py     # Status bar
├── gui_actionbar.py     # Action bar
├── gui_styles.py        # Theme/style definitions
├── gui_events.py        # Event log widget
├── game_data.py         # Static game data
├── game.py              # Game engine
├── hex_map.py           # Hex grid
├── city.py              # City system
├── military.py          # Military system
├── economy.py           # Economy system
├── tech.py              # Tech system
├── diplomacy.py         # Diplomacy system
├── simulation.py        # Character simulation
└── save_system.py       # Save/load system
```

---

## 10. Implementation Order

### Phase 1: Core (Week 1-2)
1. `gui.py` — Main window, menu bar, view switching
2. `gui_map.py` — Hex grid rendering on canvas
3. `gui_sidebar.py` — Economy panel
4. `gui_statusbar.py` — Status bar
5. `gui_actionbar.py` — Action bar

### Phase 2: Core Views (Week 3-4)
6. `gui_city.py` — City view with production
7. `gui_tech.py` — Technology tree
8. `gui_military.py` — Military overview
9. `gui_diplomacy.py` — Diplomacy table

### Phase 3: Polish (Week 5-6)
10. `gui_character.py` — Character/dynasty
11. `gui_events.py` — Event log
12. `gui_styles.py` — Themes
13. Keyboard shortcuts
14. Context menus
15. Save/load integration

---

## 11. Key Implementation Notes

### Hex Grid Math
```python
def hex_to_pixel(hex_x, hex_y, size):
    """Convert hex coordinates to pixel coordinates (pointy-top hex)"""
    x = size * (3/2 * hex_x)
    y = size * (math.sqrt(3) * (hex_y + 0.5 * (hex_x & 1)))
    return x, y

def pixel_to_hex(px, py, size):
    """Convert pixel coordinates to hex coordinates"""
    x = (2/3 * px) / size
    y = (-1/3 * px + math.sqrt(3)/3 * py) / (size * math.sqrt(3))
    return x, y
```

### Canvas Hex Drawing
```python
def draw_hex(self, canvas, x, y, size, fill, outline="white"):
    """Draw a single hex tile"""
    points = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        px = x + size * math.cos(angle)
        py = y + size * math.sin(angle)
        points.extend([px, py])
    return canvas.create_polygon(points, fill=fill, outline=outline, width=1)
```

### View Switching
```python
class CivKingsGUI:
    def __init__(self, game):
        self.game = game
        self.current_view = "map"
        self.selected_tile = None
        self.selected_unit = None
        self.selected_city = None
        
    def switch_view(self, view_name):
        self.current_view = view_name
        self.clear_canvas()
        self.update_action_bar()
        
        if view_name == "map":
            self.render_map()
        elif view_name == "city":
            self.render_city_view()
        elif view_name == "tech":
            self.render_tech_view()
        # etc.
```

### Production Queue Integration
```python
def on_build_item(self, item_name):
    """Add item to production queue"""
    city = self.selected_city
    if city:
        city.production_queue.append(item_name)
        self.update_city_view()
        self.update_sidebar()
```

### Save/Load Integration
```python
def save_game(self):
    """Save current game state"""
    state = {
        "game": self.game,
        "turn": self.game.state.turn,
        "cities": [c.to_dict() for c in self.game.cities],
        "units": [u.to_dict() for u in self.game.units],
        # etc.
    }
    save_system.save("savegame", state)
    self.show_message("Game saved!")

def load_game(self):
    """Load a saved game"""
    state = save_system.load("savegame")
    if state:
        self.game = state["game"]
        self.update_all_views()
        self.show_message("Game loaded!")
```

---

## 12. Dependencies

- **tkinter** — stdlib, no install needed
- **PIL/Pillow** — optional, for better icons (can use text symbols instead)
- **json** — stdlib, for save files

---

## 13. Performance Considerations

- **Tile culling**: Only render tiles within the viewport
- **Canvas optimization**: Use `canvas.create_polygon()` for hexes, not multiple lines
- **Throttled updates**: Only redraw changed portions of the map
- **Deferred rendering**: Batch canvas updates with `canvas.update_idletasks()`
- **Font caching**: Cache fonts for repeated text rendering

---

## 14. Accessibility

- **High contrast mode**: Toggle for colorblind users
- **Large text option**: Scale all text by 1.5x
- **Keyboard navigation**: Tab through all interactive elements
- **Screen reader labels**: Add `aria-label` equivalent via tkinter tooltips

---

## 15. Testing Strategy

### Unit Tests
- `test_gui_styles.py` — Theme color definitions
- `test_gui_math.py` — Hex coordinate conversion
- `test_gui_input.py` — Keyboard/mouse event handling

### Integration Tests
- `test_gui_map_rendering.py` — Verify map renders correctly
- `test_gui_city_view.py` — Verify city view shows correct data
- `test_gui_tech_view.py` — Verify tech tree displays correctly
- `test_gui_save_load.py` — Verify save/load works with GUI

### Manual Testing
- Play through a full game in GUI mode
- Test all view switches
- Test all action buttons
- Test keyboard shortcuts
- Test save/load cycle
- Test different themes

---

## 16. Future Enhancements

- **Animation**: Unit movement animations, combat animations
- **Sound**: City build sounds, combat sounds, music
- **Mod support**: Allow custom terrain, units, techs
- **Multiplayer**: Networked game support
- **Map editor**: Let players create custom maps
- **Achievements**: Track and display achievements
- **Tutorial**: In-game tutorial system
- **AI opponent**: Full AI civilization control
- **Replay system**: Record and replay games
- **Leaderboards**: Track best scores
- **Custom themes**: Let players create custom themes
- **Localization**: Multi-language support
- **Mod API**: Expose game data for modding
- **Cloud save**: Sync saves across devices
- **Analytics**: Track player behavior (opt-in)
- **Accessibility**: More accessibility options
- **VR support**: VR map viewing
- **AR support**: AR map overlay
- **Mobile**: Touch-friendly mobile version
- **Tablet**: Optimized for tablet screens
- **Dark mode**: Already planned
- **Light mode**: Already planned
- **High DPI**: Support for high-DPI displays
- **Retina**: Support for Retina displays
- **Multi-monitor**: Support for multi-monitor setups
- **Fullscreen**: Fullscreen mode
- **Windowed**: Windowed mode
- **Borderless**: Borderless windowed mode
- **Resizable**: Resizable windows
- **Minimizable**: Minimize to tray
- **Auto-save**: Auto-save at intervals
- **Cloud save**: Cloud save integration
- **Version control**: Git integration for saves
- **Backup**: Automatic backups
- **Restore**: Restore from backup
- **Delete**: Delete saves
- **Rename**: Rename saves
- **Export**: Export saves to different formats
- **Import**: Import saves from different formats
- **Share**: Share saves with other players
- **Download**: Download saves from other players
- **Upload**: Upload saves to other players
- **Comment**: Add comments to saves
- **Rate**: Rate saves by other players
- **Review**: Review saves by other players
- **Discuss**: Discuss saves with other players
- **Report**: Report saves with issues
- **Fix**: Fix issues in saves
- **Update**: Update saves to new versions
- **Migrate**: Migrate saves between game versions
- **Backup**: Automatic backups
- **Restore**: Restore from backup
- **Delete**: Delete saves
- **Rename**: Rename saves
- **Export**: Export saves to different formats
- **Import**: Import saves from different formats
- **Share**: Share saves with other players
- **Download**: Download saves from other players
- **Upload**: Upload saves to other players
- **Comment**: Add comments to saves
- **Rate**: Rate saves by other players
- **Review**: Review saves by other players
- **Discuss**: Discuss saves with other players
- **Report**: Report saves with issues
- **Fix**: Fix issues in saves
- **Update**: Update saves to new versions
- **Migrate**: Migrate saves between game versions
- **Backup**: Automatic backups
- **Restore**: Restore from backup
- **Delete**: Delete saves
- **Rename**: Rename saves
- **Export**: Export saves to different formats
- **Import**: Import saves from different formats
- **Share**: Share saves with other players
- **Download**: Download saves from other players
- **Upload**: Upload saves to other players
- **Comment**: Add comments to saves
- **Rate**: Rate saves by other players
- **Review**: Review saves by other players
- **Discuss**: Discuss saves with other players
- **Report**: Report saves with issues
- **Fix**: Fix issues in saves
- **Update**: Update saves to new versions
- **Migrate**: Migrate saves between game versions