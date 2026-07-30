# CivKings Implementation Plan

## Phase 1: Map & Terrain System (Foundation)

### 1.1 Map Resources & Terrain Depth
- [ ] **1.1.1** Add resource yield data to `game_data.py`
  - Add `RESOURCE_YIELDS` dict mapping each `ResourceType` to its yields
  - Add `resource_terrain_requirements` mapping (which terrains each resource can appear on)
  - Add `resource_tech_requirements` (tech needed to "see/use" each resource)

- [ ] **1.1.2** Implement river system
  - Add `RiverType` enum (River, Lake, Swamp, Marsh)
  - Create `RiverNetwork` class that generates rivers across the map
  - Add `has_river` property to `HexTile`
  - Rivers provide: +1 food, +1 gold for adjacent districts, movement cost -1 for workers
  - Rivers blocked by mountains (cannot cross)

- [ ] **1.1.3** Add climate zones
  - Add `ClimateType` enum (Temperate, Tropical, Arid, Cold, Polar)
  - Create `ClimateZone` class with climate regions
  - Climate affects: crop yields, movement penalties, happiness modifiers
  - Temperate: standard yields
  - Tropical: +50% food, -10% production
  - Arid: -30% food, +20% gold from trade
  - Cold: -20% food, +10% defense, +20% movement cost
  - Polar: -50% food, +50% movement cost, -2 happiness

- [ ] **1.1.4** Implement coastline bonuses
  - Detect tiles adjacent to ocean/coast
  - Coastal tiles get +1 gold for harbors within 2 tiles
  - Naval production bonuses on coast tiles
  - Coastal trade routes get +20% yield

- [ ] **1.1.5** Add landmarks & ruins
  - Create `LandmarkType` enum (Ancient Ruins, Holy Site, Wonder, Trade Hub)
  - Add `Landmark` class with discovery mechanics
  - Landmarks provide: one-time bonuses, ongoing yields, or strategic value
  - Ruins give science/gold when discovered
  - Wonders provide unique global bonuses

- [ ] **1.1.6** Implement exponential fog of war
  - Modify `FogOfWar` class to use distance-based visibility
  - Fog expands exponentially with distance from cities/units
  - Fog of war radius: city (5), unit (3), naval unit (4)
  - Fog reduces: trade route effectiveness, diplomacy influence
  - Fog clears gradually over time

### 1.2 Map Generation Improvements
- [ ] **1.2.1** Add continent generation
  - Generate landmasses using noise-based continent algorithm
  - Ensure all starting positions have adequate resources
  - Prevent landlocked cities where possible

- [ ] **1.2.2** Add terrain smoothing
  - Apply smoothing passes to reduce terrain fragmentation
  - Preserve natural-looking boundaries

## Phase 2: City & District System

### 2.1 City Core
- [ ] **2.1.1** Enhance `City` class
  - Add `population` tracking with growth mechanics
  - Add `walls` and `fortification` levels
  - Add `specialization` (food, production, gold, science, faith)
  - Add `district_slots` (max districts based on population)

- [ ] **2.1.2** Implement district adjacency bonuses
  - Calculate adjacency bonuses for each district
  - Apply bonuses based on terrain and adjacent districts
  - Update yields when adjacency changes

- [ ] **2.1.3** Add district production queue
  - Each district can produce one item at a time
  - Production carries over between turns
  - Priority system for multiple production queues

### 2.2 Building System
- [ ] **2.2.1** Enhance building requirements
  - Add `requires_district` validation
  - Add `requires_tech` validation
  - Add `requires_civic` validation
  - Add `requires_building` (prerequisite buildings)

- [ ] **2.2.2** Add building effects
  - Each building provides specific yields
  - Some buildings provide unique effects (e.g., Granary: +50% food storage)
  - Some buildings provide maintenance costs

### 2.3 City Management
- [ ] **2.3.1** Implement city work management
  - Cities can work adjacent tiles
  - Population determines max tiles worked
  - Workers improve tiles (increase yields)
  - Workers can be assigned to specific tasks

- [ ] **2.3.2** Add city specialization system
  - Cities can specialize in food, production, gold, science, or faith
  - Specialists provide bonuses to the specialized yield
  - Specialists can be assigned to buildings

## Phase 3: Military System

### 3.1 Unit System
- [ ] **3.1.1** Enhance unit properties
  - Add `hp` tracking with damage
  - Add `stamina` for movement
  - Add `experience` and `promotion` system
  - Add ` veterancy` levels (Novice, Veteran, Elite)

- [ ] **3.1.2** Implement unit promotions
  - Units earn XP from combat
  - Promotions provide bonuses (attack, defense, movement)
  - Promotions unlock new abilities

- [ ] **3.1.3** Add unit stacking rules
  - Units can stack in cities
  - Limited stacking on tiles (max 2 units)
  - Stacking provides defensive bonuses

### 3.2 Combat System
- [ ] **3.2.1** Implement detailed combat
  - Calculate attack/defense based on unit stats, terrain, adjacency
  - Add combat odds calculation
  - Add combat results (victory, defeat, retreat, stalemate)
  - Add casualty calculations

- [ ] **3.2.2** Add siege mechanics
  - Siege units can attack city walls
  - Walls provide defense bonuses
  - Siege weapons have special rules

- [ ] **3.2.3** Implement naval combat
  - Naval units can only move on water
  - Naval combat has different rules
  - Naval units can blockade cities

### 3.3 Military Organization
- [ ] **3.3.1** Add army formation system
  - Groups of units can form armies
  - Armies provide bonuses (defense, attack, movement)
  - Armies have a commander who provides leadership bonuses

- [ ] **3.3.2** Implement fortification system
  - Units can build forts on tiles
  - Forts provide defense bonuses
  - Forts can train units

## Phase 4: Technology & Civics System

### 4.1 Technology Tree
- [ ] **4.1.1** Implement tech research
  - Each civ researches one tech at a time
  - Research speed based on science yields
  - Tech provides unlocks (units, buildings, districts)

- [ ] **4.1.2** Add tech dependencies
  - Some techs require other techs
  - Tech branches (Military, Civic, Wonder, Naval)
  - Era progression (Ancient, Classical, Medieval, Renaissance, Industrial, Modern)

- [ ] **4.1.3** Add tech bonuses
  - Each tech provides specific bonuses
  - Some techs unlock new yields (e.g., Agriculture: +1 food)
  - Some techs enable new gameplay mechanics

### 4.2 Civic System
- [ ] **4.2.1** Implement civic government
  - Each civ has a government type
  - Governments provide policies (bonuses)
  - Policies can be changed with civic cost

- [ ] **4.2.2** Add civic tree
  - Civics provide different bonuses than techs
  - Civics affect diplomacy, religion, culture
  - Some civics enable new gameplay mechanics

### 4.3 Era System
- [ ] **4.3.1** Implement era progression
  - Eras unlock new units, buildings, districts
  - Eras provide era-specific bonuses
  - Eras affect diplomacy (era score)

## Phase 5: Economy & Resources

### 5.1 Gold System
- [ ] **5.1.1** Implement gold income
  - Cities generate gold from trade routes, buildings, specialists
  - Gold can be spent on units, buildings, diplomacy
  - Gold maintenance costs for units and buildings

- [ ] **5.1.2** Add trade route system
  - Trade routes provide gold and science
  - Trade routes can be established between cities
  - Trade routes can be with other civs

- [ ] **5.1.3** Implement gold spending
  - Gold can purchase units, buildings, tiles
  - Gold can bribe units or cities
  - Gold can be used for diplomacy

### 5.2 Resource System
- [ ] **5.2.1** Add resource management
  - Resources provide yields when worked
  - Resources can be traded
  - Strategic resources required for units/buildings

- [ ] **5.2.2** Implement resource improvement
  - Workers can improve resource tiles
  - Improved tiles provide more yields
  - Improved tiles can be worked by cities

### 5.3 Science System
- [ ] **5.3.1** Implement science generation
  - Cities generate science from buildings, districts, specialists
  - Science is used to research technologies

- [ ] **5.3.2** Add science bonuses
  - Some buildings provide science bonuses
  - Some districts provide science bonuses
  - Some civics provide science bonuses

### 5.4 Faith System
- [ ] **5.4.1** Implement faith generation
  - Cities generate faith from buildings, districts, specialists
  - Faith is used to found religions, buy units/buildings

- [ ] **5.4.2** Add religion system
  - Religions provide bonuses to followers
  - Religions can spread to other cities
  - Religions can have beliefs (bonuses)

### 5.5 Culture System
- [ ] **5.5.1** Implement culture generation
  - Cities generate culture from buildings, districts, wonders
  - Culture unlocks civics and era milestones

- [ ] **5.5.2** Add cultural victories
  - Culture can be used to attract tourists
  - Tourism determines cultural victory

## Phase 6: Character & Dynasty System

### 6.1 Leader System
- [ ] **6.1.1** Enhance leader properties
  - Leaders have personal stats (diplomacy, military, science, faith)
  - Leaders have personality traits
  - Leaders have unique abilities

- [ ] **6.1.2** Add leader aging
  - Leaders age over time
  - Aging affects leader stats
  - Leaders can die and be succeeded

- [ ] **6.1.3** Implement leader succession
  - Leaders can pass power to heirs
  - Heirs may have different traits
  - Succession can cause civil wars

### 6.2 Marriage System
- [ ] **6.2.1** Implement marriage alliances
  - Leaders can marry for alliances
  - Marriages provide diplomatic bonuses
  - Marriages can produce heirs

- [ ] **6.2.2** Add marriage mechanics
  - Marriage negotiations require diplomacy
  - Marriages can be dissolved (divorce)
  - Divorce affects diplomacy

### 6.3 Dynasty System
- [ ] **6.3.1** Implement dynasty tracking
  - Track ruling families across generations
  - Dynasties provide legacy bonuses
  - Dynasties can fall and be replaced

## Phase 7: Court & Factions

### 7.1 Court System
- [ ] **7.1.1** Add courtiers
  - Courtiers have skills and personalities
  - Courtiers provide bonuses to the ruler
  - Courtiers can be assigned to tasks

- [ ] **7.1.2** Implement court politics
  - Courtiers have opinions of the ruler
  - Courtiers can plot against the ruler
  - Courtiers can be promoted or dismissed

### 7.2 Faction System
- [ ] **7.2.1** Add factions within civs
  - Factions have ideologies and goals
  - Factions affect policy decisions
  - Factions can rebel if ignored

- [ ] **7.2.2** Implement faction management
  - Ruler can appease or suppress factions
  - Faction support affects stability
  - Faction opposition can cause civil wars

## Phase 8: Plots & Intrigue

### 8.1 Plot System
- [ ] **8.1.1** Implement plot generation
  - Plots can be generated against the ruler
  - Plots have risk and reward
  - Plots can be discovered or foiled

- [ ] **8.1.2** Add plot mechanics
  - Plots require resources to execute
  - Plots can succeed or fail
  - Plot success depends on skill and resources

### 8.2 Espionage System
- [ ] **8.2.1** Implement spy network
  - Spies can be sent to other civs
  - Spies can gather intelligence
  - Spies can sabotage enemy cities

- [ ] **8.2.2** Add counter-espionage
  - Civs can detect foreign spies
  - Civs can counter-espionage operations
  - Spies can be captured or executed

## Phase 9: Happiness & Stability

### 9.1 Happiness System
- [ ] **9.1.1** Implement happiness calculation
  - Happiness based on luxury resources, buildings, culture
  - Happiness affects productivity
  - Unhappiness can cause revolts

- [ ] **9.1.2** Add happiness modifiers
  - Buildings provide happiness bonuses
  - Luxury resources provide happiness
  - Culture provides happiness

### 9.2 Stability System
- [ ] **9.2.1** Implement stability tracking
  - Stability based on happiness, military, economy
  - Low stability can cause revolts
  - High stability provides bonuses

- [ ] **9.2.2** Add stability mechanics
  - Revolts can be suppressed or negotiated
  - Revolts can lead to civil wars
  - Stability affects diplomacy

## Phase 10: Events & Narrative

### 10.1 Event System
- [ ] **10.1.1** Implement event generation
  - Events occur based on game state
  - Events provide choices with consequences
  - Events can be historical or random

- [ ] **10.1.2** Add event types
  - Natural disasters (famine, plague, earthquake)
  - Diplomatic events (alliances, treaties, wars)
  - Economic events (prosperity, depression)
  - Cultural events (renaissance, enlightenment)

### 10.2 Narrative System
- [ ] **10.2.1** Implement narrative tracking
  - Track major events in history
  - Generate historical narratives
  - Provide player with historical context

## Phase 11: AI Improvements

### 11.1 AI Decision Making
- [ ] **11.1.1** Enhance AI decision making
  - AI considers multiple factors in decisions
  - AI adapts to player actions
  - AI has long-term strategy

- [ ] **11.1.2** Add AI personalities
  - Different AI personalities (aggressive, diplomatic, scientific)
  - Personalities affect AI behavior
  - Personalities can be mixed

### 11.2 AI Diplomacy
- [ ] **11.2.1** Implement AI diplomacy
  - AI can form alliances, trade, declare war
  - AI considers player relationship
  - AI has diplomatic goals

- [ ] **11.2.2** Add AI negotiation
  - AI can negotiate treaties
  - AI can make offers and accept/reject offers
  - AI can lie or deceive

## Phase 12: Civilizations

### 12.1 Additional Civilizations
- [ ] **12.1.1** Add 12 total civilizations
  - Each civ has unique units, buildings, districts
  - Each civ has unique bonuses and penalties
  - Each civ has unique leader abilities

- [ ] **12.1.2** Implement civ balancing
  - Balance civs for fair gameplay
  - Test civs in various scenarios
  - Adjust civs based on playtesting

## Phase 13: Win Conditions & End Game

### 13.1 Win Conditions
- [ ] **13.1.1** Implement multiple win conditions
  - Domination: Control all starting cities
  - Science: Build spaceship and escape
  - Culture: Attract most tourists
  - Diplomacy: Win world congress
  - Religion: Have followers in all civs
  - Time: Have highest score when time runs out

- [ ] **13.1.2** Add victory conditions
  - Track progress toward each victory
  - Notify player when victory is possible
  - Provide victory screen with stats

### 13.2 End Game
- [ ] **13.2.1** Implement end game sequence
  - Track game statistics
  - Provide victory/defeat screen
  - Allow replay with stats comparison

## Phase 14: Save/Load & Scenarios

### 14.1 Save/Load System
- [ ] **14.1.1** Implement save/load
  - Save game state to file
  - Load game state from file
  - Multiple save slots

- [ ] **14.1.2** Add save formats
  - Save in JSON format
  - Compress save files
  - Version control for save files

### 14.2 Scenario System
- [ ] **14.2.1** Implement scenarios
  - Scenarios provide specific starting conditions
  - Scenarios have specific victory conditions
  - Scenarios can be historical or custom

## Implementation Order

### Week 1-2: Map & Terrain
1. Resource yields and requirements
2. River system
3. Climate zones
4. Coastline bonuses
5. Landmarks and ruins
6. Exponential fog of war

### Week 3-4: City & Districts
1. City enhancements
2. District adjacency bonuses
3. Building requirements
4. City work management
5. City specialization

### Week 5-6: Military
1. Unit improvements
2. Combat system
3. Naval combat
4. Army formations
5. Fortification system

### Week 7-8: Technology & Civics
1. Tech research
2. Tech dependencies
3. Civic governments
4. Era system

### Week 9-10: Economy
1. Gold income and spending
2. Trade routes
3. Resource management
4. Science generation
5. Faith and religion
6. Culture and tourism

### Week 11-12: Characters & Diplomacy
1. Leader enhancements
2. Marriage system
3. Dynasty tracking
4. Court system
5. Faction management

### Week 13-14: Plots & Happiness
1. Plot system
2. Espionage
3. Happiness calculation
4. Stability system

### Week 15-16: Events & AI
1. Event generation
2. Narrative system
3. AI improvements
4. AI diplomacy

### Week 17-18: Civilizations & End Game
1. Additional civilizations
2. Win conditions
3. End game sequence
4. Save/load system
5. Scenario system

## Testing Strategy

### Unit Tests
- Test each system independently
- Test edge cases
- Test balance

### Integration Tests
- Test systems working together
- Test full game flow
- Test save/load

### Playtesting
- Test with multiple players
- Test different scenarios
- Test balance

## Risk Assessment

### High Risk
- Map generation (complex algorithm)
- Combat system (many variables)
- AI decision making (complex logic)

### Medium Risk
- Religion system (complex mechanics)
- Espionage system (complex interactions)
- Dynasty system (complex tracking)

### Low Risk
- Gold system (straightforward)
- Technology tree (tree structure)
- Trade routes (simple paths)

## Success Criteria

### Minimum Viable Product
- [ ] Map generation with resources
- [ ] City and district system
- [ ] Basic combat
- [ ] Technology research
- [ ] Gold economy
- [ ] One civilization playable

### Complete Product
- [ ] All map features implemented
- [ ] All city and district features
- [ ] All military features
- [ ] All technology and civic features
- [ ] All economy features
- [ ] All character features
- [ ] All event features
- [ ] All AI features
- [ ] 12 civilizations
- [ ] All win conditions
- [ ] Save/load system
- [ ] Scenarios

### Quality Criteria
- [ ] All systems tested
- [ ] All systems balanced
- [ ] All systems documented
- [ ] All systems performant
- [ ] All systems user-friendly
