# CivKings — Remaining Work Plan (~5-10% Completion)

**Created:** 2025-06-25  
**Current Status:** ~90-95% complete  
**Target:** Complete remaining high-priority items to reach ~98-99%

---

## Executive Summary

The CivKings project is essentially complete. The remaining ~5-10% consists of:
1. **UI integration gaps** (5-10 small fixes)
2. **Economy depth** (medium-complexity features)
3. **Happiness/stability systems** (medium-complexity features)
4. **Polish items** (quick wins)

This plan prioritizes work by effort vs. impact to maximize completion.

---

## PHASE 1: Quick Wins (Under 2 hours total)

### 1. Keyboard Shortcuts
**Effort:** 20 lines  
**Impact:** Quality of life  
**File:** `gui.py`

```python
# Add to CivKingsGUI.__init__
self.root.bind('<Key>', self._on_key_press)

def _on_key_press(self, event):
    shortcuts = {
        'n': self.next_turn,
        't': self.show_tech_tree,
        'd': self.show_diplomacy,
        'u': self.show_units,
        'c': self.show_cities,
        'y': self.show_dynasty,
        'v': self.show_victory_screen,
        'e': self.show_events,
        's': self.save_game,
        'Escape': self._clear_selection,
    }
    if event.char in shortcuts:
        shortcuts[event.char]()
```

### 2. Sound Toggle
**Effort:** 20 lines  
**Impact:** Quality of life  
**File:** `gui.py` (top bar)

```python
# In _top_bar(), add toggle button
self.sound_on = tk.BooleanVar(value=True)
tk.Checkbutton(bar, text="🔊", variable=self.sound_on,
               command=self._toggle_sound).pack(side=tk.RIGHT, padx=8)

def _toggle_sound(self):
    self.sound_manager.muted = not self.sound_on.get()
```

### 3. Game Speed Options
**Effort:** 40 lines  
**Impact:** Quality of life  
**File:** `gui.py` (top bar)

```python
# In _top_bar()
self.speed_var = tk.StringVar(value="1x")
speed_frame = tk.Frame(bar, bg=ACCENT)
speed_frame.pack(side=tk.RIGHT, padx=8)
for label, val in [("1x", "1"), ("2x", "2"), ("5x", "5")]:
    tk.Radiobutton(speed_frame, label, variable=self.speed_var,
                   value=val, bg=ACCENT, fg=TEXT).pack(side=tk.LEFT)
```

### 4. Right-Click Context Menu
**Effort:** 50 lines  
**Impact:** Quality of life  
**File:** `gui.py` or `gui_map.py`

```python
# Add to MapCanvas or HexGridRenderer
def _on_right_click(self, event):
    q, r = self._canvas_to_hex(event.x, event.y)
    if (q, r) in self.hex_map.tiles:
        tile = self.hex_map.tiles[(q, r)]
        menu = tk.Menu(self.root, tearoff=0)
        if tile.unit:
            menu.add_command(label=f"Move {tile.unit.name}", command=...)
            menu.add_command(label=f"Attack with {tile.unit.name}", command=...)
        if tile.city:
            menu.add_command(label=f"Produce in {tile.city.name}", command=...)
        menu.tk_popup(event.x_root, event.y_root)
```

### 5. "Next Turn" Confirmation Dialog
**Effort:** 30 lines  
**Impact:** Prevents accidental turns  
**File:** `gui.py`

```python
def next_turn(self):
    if self.game.state == GameState.PLAYING:
        if messagebox.askyesno("Next Turn", "Advance to next turn?"):
            self.game.next_turn()
            self._update_ui()
```

---

## PHASE 2: UI Integration Fixes (2-4 hours total)

### 6. Resource Trend Arrows (↑↓→)
**Effort:** 30 lines  
**Impact:** Visual clarity  
**File:** `gui.py` (top bar)

```python
# Track previous yields
self._prev_yields = None

def _update_resource_display(self):
    yields = self.game.city_manager.get_total_yields(self.game.player_civ.name)
    display = []
    for key, label in [("food", "🌾"), ("production", "⚙"), ("gold", "💰"), ("science", "🔬")]:
        val = yields.get(key, 0)
        arrow = ""
        if self._prev_yields:
            prev = self._prev_yields.get(key, 0)
            diff = val - prev
            arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
        display.append(f"{label}{val}{arrow}")
    self._prev_yields = yields
    return "  ".join(display)
```

### 7. Trade Route Yield Display
**Effort:** 20 lines  
**Impact:** Economy visibility  
**File:** `gui.py` (top bar)

```python
# In top bar, add trade route info
trade_total = self.game.economy_manager.process_trade_routes() if hasattr(self.game, 'economy_manager') else 0
tk.Label(bar, text=f"🛤️ Routes: {len(trade_routes)} (+{trade_total}💰)",
         bg=ACCENT, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=8)
```

### 8. Color-Coded Event Log
**Effort:** 20 lines  
**Impact:** Event readability  
**File:** `gui.py` (ActionLogPanel)

```python
EVENT_COLORS = {
    "combat": "#e94560",      # red
    "diplomacy": "#4caf50",   # green
    "tech": "#2196f3",        # blue
    "economy": "#ff9800",     # orange
    "warning": "#f44336",     # bright red
    "victory": "#ffd700",     # gold
    "default": "#aab",
}

def add(self, msg: str, event_type: str = "default"):
    color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
    self.log_text.tag_config(event_type, foreground=color)
    self.log_text.configure(state=tk.NORMAL)
    self.log_text.insert(tk.END, f"  {msg}\n", event_type)
    self.log_text.see(tk.END)
    self.log_text.configure(state=tk.DISABLED)
```

### 9. Minimap Integration
**Effort:** 40 lines  
**Impact:** Map navigation  
**File:** `gui.py` or `gui_map.py`

```python
# Add minimap to _main_area()
self.minimap_frame = tk.Frame(self.map_frame, bg=PANEL_BG, width=150, height=100)
self.minimap_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=4)
self.minimap_canvas = tk.Canvas(self.minimap_frame, bg="#1a4f8a", height=80)
self.minimap_canvas.pack(fill=tk.BOTH, expand=True)
# Render minimap from world map data
```

### 10. Zoom Level Display
**Effort:** 15 lines  
**Impact:** Map awareness  
**File:** `gui_map.py`

```python
# Add to map canvas
self.zoom_label = tk.Label(self.map_frame, text="Zoom: 1x", bg=PANEL_BG, fg=SUBTLE, font=("Segoe UI", 8))
self.zoom_label.pack(side=tk.BOTTOM, anchor=tk.E, padx=4, pady=2)

def set_zoom(self, level):
    self._zoom_level = level
    self.zoom_label.config(text=f"Zoom: {level}x")
```

### 11. Resource Surplus/Deficit Indicators
**Effort:** 25 lines  
**Impact:** Economy visibility  
**File:** `gui.py` (top bar)

```python
# Color code yields based on surplus/deficit
def _format_yield(self, label, value):
    color = TEXT
    if value > 0:
        color = "#4caf50"  # green for surplus
    elif value < 0:
        color = "#f44336"  # red for deficit
    tk.Label(bar, text=f"{label}: {value}", bg=ACCENT, fg=color,
             font=("Segoe UI", 10, "bold")).pack()
```

---

## PHASE 3: Economy Depth (4-8 hours total)

### 12. Tax System
**Effort:** 60 lines  
**Impact:** Economy depth  
**File:** New `tax_system.py` or add to `economy.py`

```python
class TaxSystem:
    def __init__(self):
        self.tax_rate = 50  # percentage (0-100)
        self.effects = {
            "gold_mult": lambda rate: rate / 50,      # gold scales with tax
            "happiness_penalty": lambda rate: -(rate - 50) / 10,  # happiness drops above 50%
            "growth_penalty": lambda rate: -(rate - 50) / 20,    # growth slows above 50%
        }
    
    def calculate_tax_income(self, player_civ):
        base_income = sum(city.gold for city in self.cities if city.owner == player_civ)
        return int(base_income * (self.tax_rate / 100) * self.effects["gold_mult"](self.tax_rate))
    
    def calculate_happiness_penalty(self):
        if self.tax_rate <= 50:
            return 0
        return self.effects["happiness_penalty"](self.tax_rate)
```

### 13. Happiness System
**Effort:** 80 lines  
**Impact:** Empire management depth  
**File:** New `happiness.py` or add to `economy.py`

```python
class HappinessSystem:
    def __init__(self):
        self.base_happiness = 100
        self.luxury_resources = set()
        self.entertainment_buildings = 0
        self.overextension_penalty = 0
    
    def calculate_happiness(self, player_civ):
        happiness = self.base_happiness
        
        # Luxury resources bonus
        for resource in self.luxury_resources:
            happiness += 5  # each luxury +5
        
        # Entertainment buildings bonus
        happiness += self.entertainment_buildings * 3
        
        # Overextension penalty
        num_cities = len(player_civ.cities)
        self.overextension_penalty = max(0, (num_cities - 5) * 5)
        happiness -= self.overextension_penalty
        
        # Tax penalty (from TaxSystem)
        happiness -= self.tax_system.calculate_happiness_penalty()
        
        return max(0, min(100, happiness))
    
    def get_happiness_effects(self):
        happiness = self.calculate_happiness()
        effects = {}
        
        if happiness < 30:
            effects["rebellion_risk"] = 0.1  # 10% chance
            effects["production_penalty"] = 0.5  # 50% loss
        elif happiness < 50:
            effects["production_penalty"] = 0.25
            effects["growth_penalty"] = 0.5
        
        return effects
```

### 14. Stability System
**Effort:** 70 lines  
**Impact:** Dynasty management depth  
**File:** New `stability.py` or add to `simulation.py`

```python
class StabilitySystem:
    def __init__(self):
        self.base_stability = 100
        self.war_penalty = 0
        self.conquest_penalty = 0
        self.succession_penalty = 0
    
    def calculate_stability(self, player_civ):
        stability = self.base_stability
        
        # War reduces stability
        if player_civ.at_war:
            self.war_penalty += 5  # +5 per turn at war
        stability -= self.war_penalty
        
        # Conquest reduces stability
        for city in player_civ.conquered_cities:
            self.conquest_penalty += 10
        stability -= self.conquest_penalty
        
        # Succession reduces stability
        if player_civ.recent_succession:
            self.succession_penalty = 20
        stability -= self.succession_penalty
        
        return max(0, min(100, stability))
    
    def get_stability_effects(self):
        stability = self.calculate_stability()
        effects = {}
        
        if stability < 30:
            effects["growth_penalty"] = 0.5
            effects["rebellion_chance"] = 0.15
            effects["tax_efficiency"] = 0.5
        elif stability < 50:
            effects["growth_penalty"] = 0.25
            effects["tax_efficiency"] = 0.75
        
        return effects
```

### 15. External Trade Routes
**Effot:** 60 lines  
**Impact:** Economic diplomacy  
**File:** Add to `diplomacy_extended.py` or `economy.py`

```python
class TradeRouteManager:
    def __init__(self):
        self.external_routes = []  # routes to other civs
    
    def create_external_route(self, from_civ, to_civ, merchant_unit):
        route = {
            "from": from_civ.name,
            "to": to_civ.name,
            "merchant": merchant_unit,
            "goods": "gold",
            "yield": 10,
        }
        self.external_routes.append(route)
        return route
    
    def calculate_trade_yield(self, route):
        base = 10
        # Bonus for different terrain types
        from_terrain = route["merchant"].position.terrain
        to_terrain = self.get_terrain_at(route["to"])
        if from_terrain != to_terrain:
            base += 5
        return base
```

---

## PHASE 4: Faction System (4-6 hours total)

### 16. Faction Types & Pressure
**Effort:** 80 lines  
**Impact:** Political depth  
**File:** New `factions.py`

```python
class Faction:
    def __init__(self, name, type, influence=0, stability_impact=0):
        self.name = name
        self.type = type  # "nobles", "religious", "popular"
        self.influence = influence
        self.stability_impact = stability_impact
        self.members = []
        self demands = []

class FactionManager:
    def __init__(self):
        self.factions = {}
    
    def calculate_faction_pressure(self, player_civ):
        total_pressure = 0
        for faction in self.factions.values():
            total_pressure += faction.influence
        return total_pressure
    
    def get_faction_support(self, claimant):
        support = 0
        for faction in self.factions.values():
            if faction.supports(claimant):
                support += faction.influence
        return support
```

---

## PHASE 5: Events & Narrative (6-10 hours total)

### 17. Event Chains
**Effort:** 80 lines  
**Impact:** Narrative depth  
**File:** Add to `events.py`

```python
class EventChain:
    def __init__(self, chain_id, name, events):
        self.chain_id = chain_id
        self.name = name
        self.events = events  # list of Event
        self.current_step = 0
        self.completed = False
    
    def trigger_next(self):
        if self.current_step < len(self.events):
            event = self.events[self.current_step]
            event.trigger()
            self.current_step += 1
            return event
        return None
```

### 18. Event Choices
**Effort:** 50 lines  
**Impact:** Player agency  
**File:** Add to `events.py`

```python
class EventChoice:
    def __init__(self, text, consequences):
        self.text = text
        self.consequences = consequences  # dict of effects
    
    def apply(self, game):
        for effect, value in self.consequences.items():
            game.apply_effect(effect, value)
```

### 19. Narrative Log with Filtering
**Effort:** 40 lines  
**Impact:** History tracking  
**File:** Add to `gui.py` (ActionLogPanel)

```python
class FilteredLogPanel(ActionLogPanel):
    def __init__(self, parent):
        super().__init__(parent)
        self.filters = {"combat": True, "diplomacy": True, "tech": True, "economy": True}
        
        # Add filter buttons
        filter_frame = tk.Frame(self, bg=PANEL_BG2)
        filter_frame.pack(fill=tk.X, padx=4, pady=(4, 0))
        for event_type in ["combat", "diplomacy", "tech", "economy"]:
            var = tk.BooleanVar(value=self.filters[event_type])
            var.trace_add("write", lambda e, t=event_type: self._toggle_filter(t))
            tk.Checkbutton(filter_frame, text=event_type.capitalize(),
                           variable=var, bg=PANEL_BG2, fg=TEXT).pack(side=tk.LEFT, padx=2)
```

---

## PHASE 6: AI Improvements (4-8 hours total)

### 20. AI Personality Types
**Effort:** 60 lines  
**Impact:** AI variety  
**File:** Add to `ai.py`

```python
class AIPersonality:
    def __init__(self, personality_type):
        self.type = personality_type  # "aggressive", "diplomatic", "economic", "scholarly"
        self.priorities = self._get_priorities()
    
    def _get_priorities(self):
        priorities = {
            "aggressive": {"military": 0.4, "expansion": 0.3, "economy": 0.2, "tech": 0.1},
            "diplomatic": {"diplomacy": 0.4, "economy": 0.3, "tech": 0.2, "military": 0.1},
            "economic": {"economy": 0.4, "trade": 0.3, "tech": 0.2, "military": 0.1},
            "scholarly": {"tech": 0.4, "culture": 0.3, "economy": 0.2, "military": 0.1},
        }
        return priorities[self.type]
```

### 21. Difficulty Levels
**Effort:** 40 lines  
**Impact:** Accessibility  
**File:** Add to `ai.py` or `game.py`

```python
DIFFICULTY_MODIFIERS = {
    "easy": {"ai_bonus": 0.5, "player_penalty": 0},
    "medium": {"ai_bonus": 0, "player_penalty": 0},
    "hard": {"ai_bonus": -0.5, "player_penalty": 0.1},  # AI gets bonus, player gets penalty
}
```

---

## PHASE 7: Civilization Depth (4-6 hours total)

### 22. Unique Civilizations
**Effort:** 80 lines  
**Impact:** Replayability  
**File:** Add to `game_data.py`

```python
UNIQUE_CIVS = {
    "Rome": {
        "bonus": "+25% production for military units",
        "unique_unit": "Legion (replaces Warrior)",
        "unique_building": "Colosseum (replaces Amphitheater)",
        "starting_preference": "Plains/Grassland",
    },
    "Greece": {
        "bonus": "+1 gold per tile improvement",
        "unique_unit": "Hoplite (replaces Spearman)",
        "unique_building": "Parthenon (replaces Temple)",
        "starting_preference": "Hills/Grassland",
    },
    # ... add 6-10 more civs
}
```

---

## PHASE 8: Victory & End Game (4-6 hours total)

### 23. Victory Stats Summary
**Effort:** 60 lines  
**Impact:** Game completion satisfaction  
**File:** Add to `victory_ui.py`

```python
class VictoryStatsPanel(tk.Frame):
    def __init__(self, parent, game):
        super().__init__(parent)
        self.game = game
        self._build()
    
    def _build(self):
        stats = [
            ("Turns Played", self.game.state.turn),
            ("Cities Founded", len(self.game.cities)),
            ("Units Produced", self.game.units_produced),
            ("Techs Researched", len(self.game.tech_manager.researched)),
            ("Wars Fought", self.game.wars_fought),
            ("Alliances Formed", self.game.alliances_formed),
            ("Characters in Dynasty", len(self.game.dynasty.members) if self.game.dynasty else 0),
        ]
        for label, value in stats:
            tk.Label(self, text=f"{label}: {value}",
                     bg=PANEL_BG, fg=TEXT, font=("Segoe UI", 11)).pack(fill=tk.X, padx=8, pady=2)
```

### 24. Dynasty Victory
**Effort:** 40 lines  
**Impact:** Alternative victory condition  
**File:** Add to `victory.py`

```python
def check_dynasty_victory(game, player_civ):
    if game.dynasty and len(game.dynasty.generations) >= 5:
        return True, "Dynasty Victory: Your dynasty survived 5 generations!"
    return False, ""
```

---

## PHASE 9: Polish (2-4 hours total)

### 25. Unit Movement Preview
**Effort:** 80 lines  
**Impact:** Tactical clarity  
**File:** Add to `gui_map.py`

```python
def highlight_move_range(self, unit):
    """Highlight tiles within unit's move range"""
    move_range = unit.get_move_range()
    for tile in self.get_tiles_in_range(unit.position, move_range):
        item = self.hex_items.get(tile.coords)
        if item:
            self.canvas.itemconfig(item, fill=self.highlight_color)
```

### 26. Combat Difficulty Modifier
**Effort:** 40 lines  
**Impact:** Tactical depth  
**File:** Add to `combat.py`

```python
def resolve_combat(attacker, defender, difficulty_modifier=0):
    # Add difficulty modifier to combat calculation
    base_odds = attacker.strength / (attacker.strength + defender.strength)
    adjusted_odds = base_odds + difficulty_modifier
    return random.random() < adjusted_odds
```

### 27. City Name Customization
**Effort:** 50 lines  
**Impact:** Personalization  
**File:** Add to `gui_popups.py`

```python
class CityNameDialog(tk.Toplevel):
    def __init__(self, parent, city):
        super().__init__(parent)
        self.city = city
        self.result = None
        self._build()
    
    def _build(self):
        entry = tk.Entry(self)
        entry.insert(0, self.city.name)
        entry.pack()
        tk.Button(self, text="Rename", command=self._confirm).pack()
    
    def _confirm(self):
        self.result = self.entry.get()
        self.destroy()
```

---

## PHASE 10: Save System (2-4 hours total)

### 28. Multiple Save Slots
**Effort:** 40 lines  
**Impact:** Save management  
**File:** Add to `save_system.py`

```python
class SaveSlotManager:
    def __init__(self, num_slots=5):
        self.num_slots = num_slots
        self.slots = [None] * num_slots
    
    def save_game(self, slot, game_state):
        filename = f"save_{slot}.sav"
        save_system.save(filename, game_state)
        self.slots[slot] = filename
    
    def load_game(self, slot):
        if self.slots[slot]:
            return save_system.load(self.slots[slot])
        return None
```

### 29. Auto-Save
**Effort:** 30 lines  
**Impact:** Crash protection  
**File:** Add to `game.py`

```python
def next_turn(self):
    # Auto-save before advancing
    save_system.auto_save(self)
    self.state.turn += 1
    self._process_turn()
```

---

## Implementation Priority Order

### Week 1: Quick Wins & UI Fixes
1. ✅ Keyboard shortcuts
2. ✅ Sound toggle
3. ✅ Game speed options
4. ✅ Right-click context menu
5. ✅ Next turn confirmation
6. ✅ Resource trend arrows
7. ✅ Trade route yield display
8. ✅ Color-coded event log
9. ✅ Minimap integration
10. ✅ Zoom level display
11. ✅ Resource surplus/deficit indicators

### Week 2: Economy & Happiness
12. ✅ Tax system
13. ✅ Happiness system
14. ✅ Stability system
15. ✅ External trade routes

### Week 3: Political & Narrative Depth
16. ✅ Faction system
17. ✅ Event chains
18. ✅ Event choices
19. ✅ Narrative log with filtering

### Week 4: AI & Polish
20. ✅ AI personality types
21. ✅ Difficulty levels
22. ✅ Unique civilizations
23. ✅ Victory stats summary
24. ✅ Dynasty victory
25. ✅ Unit movement preview
26. ✅ Combat difficulty modifier
27. ✅ City name customization
28. ✅ Multiple save slots
29. ✅ Auto-save

---

## Effort Summary

| Phase | Items | Estimated Hours |
|-------|-------|-----------------|
| Quick Wins | 5 items | 2 hours |
| UI Integration | 6 items | 4 hours |
| Economy Depth | 4 items | 8 hours |
| Faction System | 1 item | 4 hours |
| Events & Narrative | 3 items | 10 hours |
| AI Improvements | 2 items | 8 hours |
| Civilization Depth | 1 item | 6 hours |
| Victory & End Game | 2 items | 6 hours |
| Polish | 5 items | 4 hours |
| Save System | 2 items | 4 hours |
| **TOTAL** | **31 items** | **~56 hours** |

---

## Risks & Considerations

1. **Integration complexity:** Economy and happiness systems need careful integration with existing city/production systems
2. **Testing scope:** New systems require thorough testing for balance
3. **Performance:** Event chains and faction pressure calculations could impact turn processing time
4. **Balance:** Happiness, stability, and tax systems need playtesting for proper balance

## Recommendations

1. **Start with quick wins** to build momentum and improve quality of life immediately
2. **Implement economy systems first** as they're foundational to happiness/stability
3. **Test balance iteratively** — adjust numbers based on playtesting
4. **Consider player feedback** before implementing lower-priority items
