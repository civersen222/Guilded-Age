# CivKings - Main Game Screen Layout

## Visual Mockup (1920x1080 Standard)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  HEADER BAR (Height: 60px)                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ [🏰 Dynasty Crest]  House Blackwood          │  📅 Turn 42/250    ⚔️ Phase: Player  │  │
│  │ [✅ Victory Progress] Domination: 6/10 Cities  🏆 Science: Era 3/5                  │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  RESOURCE BAR (Height: 50px)                                                                 │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │ 🍞   │ │ ⚒️   │ │ 💰   │ │ 🔬   │ │ 🙏   │ │ 🎭   │ │ 👑   │ │ 📊   │ │ ⏱️   │       │
│  │ Food │ │Prod  │ │ Gold │ │ Sci  │ │ Faith│ │ Cult │ │ Prest│ │ Army │ │ Turn │       │
│  │ 142  │ │ 87   │ │ 34   │ │ 23   │ │ 12   │ │ 45   │ │ 78   │ │ 8/12 │ │ 5/5  │       │
│  │ +12  │ │ +8   │ │ +5   │ │ +4   │ │ +2   │ │ +3   │ │ +7   │ │ +2   │ │      │       │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘       │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  MAIN CONTENT AREA (Height: ~700px)                                                          │
│                                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │ MAP VIEW (Left: 60%)                    MINIMAP (Right: 10%)     DETAILS PANEL (Right: │  │
│  │                                                                                          │  │
│  │  ┌───────────────────────────────────────────────────┐  ┌───────┐  ┌──────────────────┐  │  │
│  │  │  ┌───┬───┬───┬───┬───┐  [🔍 +]                  │  │       │  │ SELECTED: City   │  │  │
│  │  │  │   │   │🏰 │   │   │  [🔍 -]                  │  │  ●    │  │ of Blackwood   │  │  │
│  │  │  ├───┼───┼───┼───┼───┤  [Terrain]               │  │ ●  ●  │  │ ───────────────  │  │  │
│  │  │  │   │⚔️│   │🌾│   │  [Fog Toggle]              │  │  ●    │  │ 👑 King Aethel   │  │  │
│  │  │  ├───┼───┼───┼───┼───┤  [Zoom: 100%]            │  │●   ●  │  │ Age: 45/80       │  │  │
│  │  │  │   │   │🏭 │   │   │                           │  │  ●    │  │ Health: ❤️❤️❤️  │  │  │
│  │  │  ├───┼───┼───┼───┼───┤  ┌───┐ ┌───┐ ┌───┐      │  │       │  │ Traits: ⚔️🧠💬   │  │  │
│  │  │  │🌲│   │   │   │🏔️│  │🏰 │ │⚔️ │ │🌾 │      │  │  Minimap│  │ ───────────────  │  │  │
│  │  │  └───┴───┴───┴───┴───┘  │   │ │   │ │   │      │  │ (Click│  │ 📊 Resources:    │  │  │
│  │  │  [Hex Info: Plains]     │🏰 │ │⚔️ │ │🌾 │      │  │  to   │  │ ───────────────  │  │  │
│  │  │  🏰 Food: +12/turn      │   │ │   │ │   │      │  │  zoom)│  │ 🍞 Food: 142     │  │  │
│  │  │  ⚒️ Production: +8/turn │   │ │   │ │   │      │  │      │  │ 🏭 Production: 87  │  │  │
│  │  │  💰 Gold: +5/turn       │   │ │   │ │   │      │  │      │  │ 💰 Gold: 34      │  │  │
│  │  │  🔬 Science: +4/turn    │   │ │   │ │   │      │  │      │  │ 🔬 Science: 23   │  │  │
│  │  │  🙏 Faith: +2/turn      │   │ │   │ │   │      │  │      │  │ 🙏 Faith: 12     │  │  │
│  │  └──────────────────────────┴───┴─┴───┴─┴───┴──────┘  │      │  │ 🎭 Culture: 45   │  │  │
│  │                                                        │      │  │ 👑 Prestige: 78  │  │  │
│  │  ┌───────────────────────────────────────────────────┐  │      │  │ 📊 Army: 8/12  │  │  │
│  │  │  EVENT LOG (Bottom Panel - Height: 100px)         │  │      │  └──────────────────┘  │  │
│  │  │  ───────────────────────────────────────────────  │  │      │                       │  │
│  │  │  [Turn 42] 📜 Event: Barbarian raid detected!    │  │      │  ┌──────────────────┐  │  │
│  │  │  [Turn 41] 🏛️ City completed: Temple of Old Gods│  │      │  │ ACTION MENU      │  │  │
│  │  │  [Turn 40] ⚔️ Battle: Defeated Southern Horde    │  │      │  │ ───────────────  │  │  │
│  │  │  [Turn 39] 🤝 Diplomacy: Alliance with Nordmark │  │      │  │                  │  │  │
│  │  │  [Turn 38] 🎭 Event: Festival of the Harvest    │  │      │  │ [🏙️ Manage]    │  │  │
│  │  └───────────────────────────────────────────────────┘  │      │  │ [⚔️ Command]   │  │  │
│  │                                                         │      │  │ [📚 Research]  │  │  │
│  │  ┌───────────────────────────────────────────────────┐  │      │  │ [🤝 Diplomacy] │  │  │
│  │  │  QUICK ACTIONS TOOLBAR (Height: 60px)             │  │      │  │ [👑 Dynasty]   │  │  │
│  │  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │  │      │  │ [🏭 Produce]   │  │  │
│  │  │  │ 🗺️  │ │ 🏙️  │ │ ⚔️  │ │ 📚  │ │ 🤝  │   │  │      │  │ [💾 Save]      │  │  │
│  │  │  │ Map │ │City │ │ Units│ │ Tech │ │Diplo│   │  │      │  │ [📅 Next Turn] │  │  │
│  │  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘   │  │      │  └──────────────────┘  │  │
│  │  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │  │      │                       │  │
│  │  │  │ 👑  │ │ 🏭  │ │ 📊  │ │ 🎯  │ │ 💾  │   │  │      │  │  [Close] [X]         │  │  │
│  │  │  │Dyna │ │Prodc │ │ Stats│ │Event │ │ Save │   │  │      │                       │  │
│  │  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘   │  │      └──────────────────┘  │  │
│  │  └───────────────────────────────────────────────────┘  │                          │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Layout Breakdown

### 1. HEADER BAR (Top - 60px)
- **Left**: Dynasty crest + House name
- **Center**: Turn number + Phase indicator
- **Right**: Victory progress bars (Domination, Science, Culture, etc.)

### 2. RESOURCE BAR (Below Header - 50px)
Horizontal bar with all key resources:
- 🍞 Food (with trend arrow)
- ⚒️ Production
- 💰 Gold
- 🔬 Science
- 🙏 Faith
- 🎭 Culture
- 👑 Prestige
- 📊 Military Strength
- ⏱️ Available Actions

### 3. MAIN CONTENT AREA (Split into 3 panels)

#### A. MAP VIEW (60% width)
- Central hex grid map
- Zoom controls (+/-)
- Terrain toggle
- Fog of war toggle
- Hex info tooltip on hover
- Unit/City selection indicators
- Pathfinding visualization
- **Minimap** (top-right corner of map)
  - Shows overview of entire world
  - Click to zoom/pan
  - Shows unit positions, cities, borders

#### B. DETAILS PANEL (30% width)
- **Contextual based on selection**:
  - If City selected: Population, resources, districts, buildings, production queue
  - If Unit selected: HP, attack/defense, promotion, movement range
  - If Character selected: Portrait, traits, age, health, succession info
  - If Diplomacy selected: Relations, alliances, treaties, trade routes
  - If Empty Map: Region info, terrain, resources

- **Action Menu** (bottom of details panel):
  - Relevant actions for selection
  - e.g., for City: Manage, Produce, Recruit
  - e.g., for Unit: Move, Attack, Fortify, Retreat

#### C. EVENT LOG (Bottom of map area - 100px)
- Scrollable list of recent events
- Color-coded by type (📜 events, ⚔️ combat, 🏛️ construction, 🤝 diplomacy)
- Clickable for context/options
- Auto-scroll to latest

### 4. QUICK ACTIONS TOOLBAR (Bottom - 60px)
8 main buttons for primary operations:
1. 🗺️ Map View
2. 🏙️ City Management
3. ⚔️ Military Command
4. 📚 Technology Tree
5. 🤝 Diplomacy
6. 👑 Dynasty/Family
7. 🏭 Production Queue
8. 📊 Statistics/Overview

Second row:
1. 👑 Dynasty (minimal - shows key info)
2. 🏭 Production
3. 📊 Stats
4. 🎯 Events/Crises
5. 💾 Save Game
6. 📅 Next Turn
7. ❓ Help

### 5. DYNASTY ELEMENTS (Minimal unless accessed)
- **Header**: Shows current ruler's name + dynasty name
- **Dynasty Screen** (when clicked):
  - Family tree visualization
  - Character portraits with traits
  - Succession law display
  - Marriage opportunities
  - Intrigue alerts
  - Heir apparent indicator

## Interactive Behavior

### Selection System
- **Click hex**: Shows terrain/unit/city info in details panel
- **Click unit**: Shows unit details + action menu
- **Click city**: Shows city details + production options
- **Click character**: Shows dynasty info + traits
- **Click minimap**: Zooms map to that location

### Contextual Updates
- Details panel updates instantly on selection change
- Action menu shows only relevant actions
- Resource trends update after each turn
- Event log highlights new events

### Dynasty Integration (Crusader Kings Style)
- **Persistent but minimal**: Dynasty info only visible when hovered/clicked
- **Marriage/Alliance**: Pop-up windows when clicking other rulers
- **Intrigue**: Hidden alerts that appear in event log
- **Succession**: Visual indicator in header (heir apparent)

### Color Coding
- **Resources**: Distinct colors per type
- **Map**: Terrain-based (green=plains, brown=mountains, blue=water)
- **Events**: Color by type (red=combat, blue=diplo, gold=construction)
- **Selection**: Gold highlight on selected item
- **Alerts**: Red flash for important events

## Layout Dimensions (1920x1080)
- Header: 60px
- Resource Bar: 50px
- Map Area: 700px (60% width)
- Minimap: 150x150px (top-right of map)
- Details Panel: 30% width, 700px height
- Event Log: 100px height
- Action Toolbar: 120px height (2 rows)
- Margins: 10px around all edges

## Responsive Design
- **Smaller screens**: Collapse details panel to overlay
- **Tablet**: Stack map and details vertically
- **Mobile**: Show only map + action toolbar

## Key Design Principles
1. **Information Hierarchy**: Most critical info at top, detailed info on demand
2. **Map-Centric**: Central focus is the hex grid map
3. **Contextual**: Details panel changes based on selection
4. **Minimal Dynasty**: Dynasty elements hidden until accessed
5. **Quick Actions**: Primary operations always visible
6. **Visual Feedback**: Color coding, animations, tooltips
7. **Event History**: Persistent log of important events

---

*This layout balances Civilization-style strategy elements with Crusader Kings dynasty mechanics while keeping the interface clean and focused.*
