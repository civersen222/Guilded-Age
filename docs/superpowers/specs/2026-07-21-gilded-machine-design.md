# CivKings: The Gilded Machine — Design Spec (2026-07-21)

**Status:** Design source-of-truth for the new chassis. Companion to
`localcode/docs/civkings-character-society-spec.md` (character layer — still authoritative
for dispositions, schemes, marriage, shares, labor, tide, revolution) and SUPERSEDES the
4X frame of `civkings-deep-systems-spec.md` (hex tiles, cities-as-tile-engines, unit
movement, tactical combat are all removed).

All decisions locked one-by-one in a brainstorming session with the owner
(8 questions; decision log at the end). Trigger: the 1000-turn marathon campaign proved
the character layer carries the game and the 4X map layer fights it.

---

## 1. Vision & Frame

A dynasty-management game set in a fictional 1900. You are the mortal head of a Great
House — crown and capital fused — across a ~century arc (**~70 turns at 1-2 years each**).
Thesis unchanged: *the profit motive grinds everyone; the player only decides who pays.*

- **Space as theater, not chessboard.** The map exists with real geography, but the player
  never moves a unit. Characters execute; the player reads dispatches.
- **The mortal ruler.** The player is one person with ~3 personal actions a year, atop a
  House that runs on standing directives interpreted by real characters.
- **The world:** one continent of **~50-70 organic provinces** (irregular, EU-atlas style),
  held by **6-8 Great Houses** plus minor holders (gentry, free towns).
- **Game over:** dynasty extinction, or revolution unridden (transformation path survives
  as specced). Otherwise the century ends and the age judges you (Section 8).

Removed from old CivKings: hex tiles, settlers, build queues, citizen/tile economy, unit
movement, tactical combat, per-tile borders. Transplanted whole: characters/dispositions/
drift/stress/breaks, Persona vs Private Self + secrets, all scheme verbs, marriage-as-
merger, shares + partition succession, guardians/education/Focus, labor movements +
extraction dial, ideological tide + legitimacy, event engine + template pools + signature
chains, tiered-LOD population.

## 2. The Turn

Three movements per turn:

**I. The Morning Papers.** The turn opens as a readable report in three registers:
- **The Gazette** — public world news: wars, crashes, scandals, strikes, obituaries.
  Slanted by whoever runs the presses (a Master of the Press can slant coverage of
  their own House).
- **The House Ledger** — the player's enterprises, dividends, shares, fronts, treasury.
- **Private Letters** — spy reports, family matters, secrets; things only the ruler knows.

**II. The Docket.** The simulation and standing directives generate **petitions** —
matters demanding the ruler: a Director begging capital, the heir demanding a seat, a
union ultimatum, a betrothal offer, a disaster inquiry, a seat vacancy. The ruler has
**3 attention points** per turn (constant `ATTENTION_PER_TURN = 3`).
- Ruling on a petition costs 1 attention.
- Every consequential ruling selects an **executor** as well as a policy: the same matter
  handled by the Head of Security, the heir, or the ruler personally produces different
  outcomes, different drift, and different stress. The cabinet lives *inside* choices as
  executor selection, not as ceremony around every verb.
- **Initiatives** — proactive moves (propose a marriage, found an enterprise, start a
  scheme, tour a province, visit a front) — also cost 1 attention each and route through
  a person (Chairman, Foreign Secretary, spymaster...).

**III. The Unattended.** Petitions not ruled on **do not wait**: the seat-holder for that
domain resolves them by their own convictions and skill, and the result appears in next
turn's papers. An empty seat means the matter festers (escalates or auto-fails).
Delegation is not a feature; it is what happens when a mortal runs out of attention.

**Standing directives** — five domain dials consulted by seat-holders when ruling without
the player: **Capital, Labor, Expansion, Diplomacy, War** (each a −100..+100 stance, e.g.
Labor: conciliate ↔ break them). Adjusting them is free, but a directive violating its
executor's convictions generates friction: stress, foot-dragging, protest petitions,
resignation.

## 3. The Atlas

- **Generator:** seeded and deterministic. Seed points → Voronoi-style regions → coastline
  carve → terrain character (coast, highlands, plains, marsh) → **endowments**: coalfields,
  iron, timber, farmland, harbors. Endowments are uneven by design — geography decides
  what industry is possible where.
- **Province state:** name, polygon, neighbors, terrain, endowments, owner House,
  **population** (the workforce pool), development, unrest + labor movement (transplanted
  from city code), garrison, enterprises located there.
- **Links:** every adjacent pair has a link — road by default, upgradeable to **rail**
  (an investment through the Chief Engineer). Rail multiplies enterprise throughput and
  is the supply line in war. Distance = graph hops weighted by rail.
- Houses hold contiguous-ish clusters; minor holders pad borders as buffer, marriage
  market, and acquisition targets.
- **No fog of war** — it's 1900; there are newspapers. What is hidden is secrets, not
  terrain.

## 4. Enterprises — the Economy

The **enterprise** is the atom of wealth: type (colliery, ironworks, mill, rail company,
bank, estate...), home province, **capital tier 1-5**, workforce drawn from the province
population, **extraction dial**, **Director**.

- **Output** = endowment × capital tier × workforce × dial multiplier × Director Industry
  × tech modifiers. Dial and Director systems transplant unchanged.
- Output pays **dividends to shareholders** (the existing shares/succession system finally
  points at real objects) and produces **strategic capacity** — coal, steel, freight —
  which feeds construction and war.
- **Founding/expanding** an enterprise is an initiative through the Board Chairman: real
  gold, multi-turn construction, and a new Director seat to staff. The org chart grows
  with the economy.
- **Prices** are simple constants swayed by events and the tide (a great strike raises
  coal prices worldwide). No market sim in v1.
- Labor movements, accidents, atrocities, and the tide attach to enterprises/provinces
  exactly as the character-society spec describes.
- No build queues anywhere. Growth = investment decisions, board-level and occasional.

## 5. War — the Fronts

A war opens with a **stated goal** (seize named provinces, force open markets, humble,
survive). Every contested border becomes a **front**. Player war verbs are exactly three:

1. **Allocate** — regiments raised from province populations (draining workforces), armed
   with steel capacity, moved on rail.
2. **Appoint** — one Commander per front; Command stat, temperament, and stress drive
   resolution.
3. **Negotiate** — peace as a brokered deal: provinces, shares, concessions, dials.

Per-turn front resolution: force ratio × supply (rail hops from industrial core) ×
Commander × entrenchment × dice → line holds or moves; provinces change hands; the papers
print the butcher's bill. Casualties feed unrest, the tide, and family drift. Battles are
never shown — only reported. There are no army entities on the map and no tactical layer.

## 6. Characters & the Org Chart

Transplanted whole and pointed at new objects (see Section 1 list). The org chart is the
game's **entire execution layer**:

- **Council (~6 seats):** Board Chairman (capital, enterprise petitions), Chief Engineer
  (construction, rail, tech), Head of Security (strikes, garrisons, spies), Master of the
  Press (persona, expose, Gazette slant), Foreign Secretary (diplomacy, marriages),
  Marshal (fronts, regiments). Seat-holder's attribute → domain modifier; seat-holder's
  convictions → how unattended petitions in that domain get ruled.
- **Directors** per enterprise; **Commanders** per front. The only hands on those levers.
- **AI Houses run the identical loop** — papers (internally), docket, seats — with the AI
  ruler's dispositions picking the rulings. One brain for everyone; no separate 4X AI.

## 7. Interface

**A broadsheet, not a battlemap.**
- Primary surface: the turn report as a period newspaper (masthead, columns); Ledger and
  Letters as adjacent tabs in the same text-forward register.
- **The Docket:** petition cards — the matter, the characters involved, choices generated
  from what those characters can actually do, executor picker.
- **The atlas is a side view:** clickable organic-province map for reference. Click a
  province → its ledger (enterprises, Director, unrest, garrison, rail). Fronts draw as
  red lines that move while you read.
- Existing screens (character sheet, house board, appointments, labor, schemes) port
  their content into text panels.
- **Headless first-class:** a play-console protocol (same file-bridge design as M83) ships
  from day one for tests, soaks, and AI-vs-AI century runs. The pygame broadsheet is a
  client of the sim, never the sim itself.

## 8. Endings — the Judgment of the Age

- Hard stops: **dynasty extinction**; **revolution unridden**. Transformation path
  survives exactly as specced (genuine conviction drift → People's Chairman).
- Otherwise the century ends and the game writes an **epilogue** from four axes:
  - **Capital** — net worth, controlling stakes held across the world's enterprises.
  - **Standing** — legitimacy, prestige, the House's name.
  - **Blood** — the heirs made, and what the machine did to them.
  - **The World You Made** — the tide, the graves, worker welfare. The thesis axis.
- Named endings on top as achievements-of-state: *Hegemon of the Age, The Quiet Throne,
  People's Chairman, A House of Ash...* The epilogue always says who paid.

## 9. Engineering

- **Same repo, new top-level package `gilded/`** — the old game stays untouched and
  runnable at repo root.
- Modules (small, one idea each):
  - `gilded/world.py` — provinces, links, endowments, atlas generator (seeded,
    deterministic)
  - `gilded/enterprises.py` — economy atom; dividends, capacity, construction
  - `gilded/fronts.py` — war resolution
  - `gilded/docket.py` — petition generation, attention, unattended resolution via seats
  - `gilded/papers.py` — composes Gazette / Ledger / Letters from the turn's real events
  - `gilded/directives.py` — five stance dials + conviction-friction
  - `gilded/chassis.py` — lean turn orchestrator (the anti-`game.py`: calls systems, owns
    nothing)
  - `gilded/console.py` — headless protocol; `gilded/ui/` — pygame broadsheet + atlas
    renderer
  - Transplants port with import surgery: every `city` reference becomes a province or an
    enterprise.
- All numeric tunables are named constants grouped per system.
- Testing: pytest per module + a seeded AI-only century soak as the standing regression +
  the console protocol for played campaigns.
- **All implementation lands via CynCo mission briefs** (byte-for-byte, pre-validated in a
  scratch worktree, verified against outcome + byte-diff + smoke re-run + pytest
  baseline). The planning assistant never edits game code directly.

## 10. Decision Log (brainstorm, 2026-07-21)

| # | Question | Decision |
|---|----------|----------|
| 1 | Role of physical space | **A: theater, not chessboard** — map real, player never moves units |
| 2 | Core loop | **C + A: mortal ruler** (~3 actions/turn) over **standing directives** |
| 3 | Economy | **B: enterprise model** — tile economy deleted; growth = investment decisions |
| 4 | War | **B: front model** — allocation + commanders + supply; no army entities |
| 5 | Map representation | **B: organic provinces** (~50-70, Voronoi-based atlas, new renderer) |
| 6 | Code strategy | **B: fresh chassis (`gilded/`), transplant the society layer** |
| 7 | Interface | **C: text-forward broadsheet**; atlas as side view; headless console first-class |
| 8 | Turn shape | **2+3 blend with 1's opening**: Morning Papers → Docket (petitions, executor-routed rulings, unattended matters resolved by seats) + initiatives |
