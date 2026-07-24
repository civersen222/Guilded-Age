# The Gilded Machine — Play-Experience Redesign: Stage 4 (Enterprises / the Economy)

**Status:** Approved vision, design settled with the user (2026-07-24). Spec below; plan not yet written.

**Prior stages:** Stage 1 (the Frame, `1d9adf9`), Stage 2 (Living Adversaries, `ea0f7dc`), Stage 3 (Policy Dials, `d2af945`). Stage 4 is the fourth domain stage of the 8-stage experience redesign (spec `2026-07-22-gilded-experience-redesign-design.md`).

---

## 1. The problem

The economy is the deepest system in the simulation and the least visible one. `gilded/enterprises.py` models real ventures (six types, tiers 1–5, an output formula driven by endowment richness, staffing, extraction dial, Director industry, and a `tech_mod`), `gilded/society/shares.py` models shareholding ledgers and dividends, `gilded/society/schemes.py` models a hostile buyout (`Takeover`), and `gilded/society/labor.py` models a genuine labor economy (extraction → unrest → unions → strikes → accidents). The chassis pays per-enterprise dividends and accrues strategic capacity every turn.

Yet the player can barely see or touch any of it. There is no Enterprises tab; the Ledger tab prints only "Dividends: N gold" / "completes its works" event lines; the Atlas province view does not even list the enterprises seated in a province. Founding and expanding exist as docket *initiatives* but `ui/app.py` wires **no UI action** for them — today they fire only when a Director petitions or the AI acts.

Two deeper gaps make the economy feel flat rather than deep:

1. **Strategic capacity is produced but never consumed.** Enterprises emit coal/steel/freight into a per-house `capacity` dict (`chassis.py`), and nothing downstream eats it. That is the supply half of a supply/demand system with no demand half.
2. **A full market simulation is dormant.** `market_simulation.py` (repo root) implements supply/demand tracking and `price = base × (demand / supply)` with an event log, but is never called. `external_trade_routes.py`, the `tech_mod` hook (pinned to `1.0` in `output_gold`), `build_speed_mod`, province `development`, and the rail/road graph are all scaffolded and unused.

**Stage 4 turns the economy from an invisible background process into a legible, agency-rich domain with genuine emergent depth — by connecting and exposing machinery that largely already exists.**

## 2. Vision & design mandates

**North star:** Stage 4 is *Succession* set in 1900 — an industrial dynasty fighting for control of the family company through the shareholding ledger. The drama is ledger warfare: which resentful heir can be flipped, the hostile bid you see coming three moves out, the Directors as proxy fights, the boom that funds your grip and the bust that loosens it.

**Mandates:**

1. **One master spine.** Every economic system pushes on a single legible meter — **Grip on the House** (§3). The player's recurring question each turn is "am I tightening or losing my hold on the House?"
2. **Deep, not bolted-on.** Prices are an *output* of interacting systems (a production chain clearing supply against demand), not a scripted cycle. Depth comes from dependencies between commodities, not from more line-items. (Dwarf-Fortress principle.)
3. **Reuse, don't rebuild.** Prefer reactivating dormant machinery (`market_simulation.py`, the `capacity` dict, `tech_mod`) and wiring existing verbs (`start_takeover`, `transfer_shares`, `found_enterprise`) over new systems. New sim is added only where a genuine gap exists (emergent pricing, priced share trades, Director appointment, disloyal-Director effects).
4. **Legibility is the substrate.** The player must be able to *see* their portfolio, per-enterprise dividends, Director loyalty, the market, and the predator's advance before any of the agency matters.
5. **Hold the action-economy redesign for Stage 7.** Every lever remains **one attention per initiative**, as today. Stage 4 does not redesign how attention is spent.

## 3. The master spine: Grip on the House

A new **pure read-model** `gilded/grip.py` (sibling to `gilded/intel.py` and `gilded/dashboard.py`; no simulation state, no `game.rng`). For a house it reports:

- **loyal bloc** — the ruler plus kin whose opinion of the ruler clears the loyalty line. Reuses the exact test `disloyal_shareholders` (`gilded/society/realm.py`) already uses, inverted, so "loyal" here means the same thing the `Takeover` engine means by "not for sale."
- **controlling stake** — the average across the house's enterprises of the loyal bloc's combined shareholding, computed with the existing `house_stake` yardstick (`shares.py`).
- **top predator** — the outside holder (a rival character) with the single largest average stake across the house's enterprises, reported against `TAKEOVER_THRESHOLD` (`schemes.py`).
- **band** — `IRON_GRIP` → `CONTESTED` → `IMPERILED` → `SEIZED`, derived from the gap between the loyal controlling stake and the top predator's stake relative to the threshold. `SEIZED` corresponds to a completed `Takeover`.
- **per-enterprise breakdown** — for each enterprise: sector, tier, this-turn dividend, Director (id, name, industry, loyalty flag), the player's stake, and the largest single outside holder.

Grip is *derived*, never stored: it is a truthful reading of the ledger, loyalty, and market that already exist. This keeps mid-game meters consistent with the end-game Capital-axis judgment (the Stage 1 principle).

## 4. The Market — a production chain with emergent prices

A new module `gilded/market.py`. Prices are cleared each turn from real supply and demand over a commodity chain; nothing is scripted.

### 4.1 Commodities and the chain

Four commodities, each carrying an endogenous price (a multiplier around a base):

| Commodity | Supplied by | Consumed by (demand) |
|---|---|---|
| **coal** | collieries | **ironworks (input to steel)**, households, rail |
| **steel** | ironworks (consume **coal**) | **war** (regiments/entrenchment), **construction** (expansions), rail cos |
| **freight** | mills, rail cos (consume **steel** to lay track) | **every enterprise's reach** — freight multiplies effective output |
| **farm / food** | estates | **population** (workforce staffing); scarcity feeds unrest |

The chain (coal → steel → freight, with freight and food looping back into everyone's output) is what makes commodities *interact*. An ironworks does not merely "ride the steel price"; it **consumes coal to produce**, so its real cost structure rises when coal is scarce.

### 4.2 Price formation

Each turn `market.py` sums **supply** (enterprise capacity already computed via `capacity_out`, currently discarded into the `capacity` dict) and **demand** (downstream chain consumption + war consumption from `fronts` + construction from in-flight expansions + population food need), then sets `price = base × (demand / supply)` per commodity, bounded to a sane range. This adapts the dormant `market_simulation.py` logic.

Prices react to things the player and rivals actually do: a strike cuts coal supply (generalizing the existing `COAL_STRIKE_PRICE` seam in `chassis.py`), a war spikes steel/freight demand, and a house over-building a sector floods supply and deflates its own price. This is reactive but reproducible — no `game.rng` in the core clearing.

### 4.3 Where the market threads in

1. **Output / dividends** (`chassis.py` dividend loop): the producing enterprise's commodity price becomes a multiplier on `output_gold`, alongside the strike and `policy.output_mod` mods already there. Consuming enterprises (ironworks, rail cos) also carry an **input cost** deducted for the coal/steel they burn, so a scarce input squeezes their margin. Banks have no commodity; they ride **market confidence** (the mean of the four prices).
2. **The `tech_mod` hook** in `output_gold` (currently always `1.0`) is activated so province `development` / technology raises real output over the century.
3. **Valuation** (`market.value(ent)`, §5.2): the same prices set what a stake is worth, feeding share trades and buyout costs.

### 4.4 Legibility

The Enterprises panel (§6) carries a **market ticker** (`coal ▲+22  steel ▲+11  freight ▼-8  farm —`) and per-enterprise dividend deltas, so the boom/bust force is visible rather than a hidden roll.

## 5. The levers (the Capital game)

All four agency levers are in scope. Each is a one-attention initiative.

### 5.1 Found / Expand

Wire the **existing** `found_enterprise` and `expand_enterprise` initiatives (`docket.py`) to real UI actions on the panel (kind + province selection for founding; tier-up for expanding). Mostly UI; the sim exists.

### 5.2 Buy / Sell shares (priced) + valuation

- **Valuation** — `market.value(ent)` = expected annual dividend (which already reflects the commodity price) × a P/E multiple. One function prices everything: a boom makes stakes dear, a crash makes them cheap to grab.
- **Priced transfer** — a new wrapper over the existing `transfer_shares` (`shares.py`) moves gold from buyer to seller at `market.value × pct/100`, then moves the shares. New docket initiatives `buy_shares` and `sell_shares` compute the price, pick the counterparty, and apply a small opinion effect on the seller (a "generous buyer" bump, mirroring the `Takeover`).
- **Buying back your disloyal kin** starves the predator (defense, §5.4); **selling** raises cash now at the cost of diluting control.

### 5.3 Appoint / Sack Directors

A small new initiative `appoint_director`: assign a living house character as an enterprise's `director_id`, chosen from a candidate pool (realm characters ranked by the `industry` stat). Sacking clears or reassigns; removal-by-prosecution after an accident already exists (`docket.py`). A strong, loyal Director lifts output (the existing `director_mod`) and reduces accident/scandal exposure.

**Disloyal Directors actively hurt you** (new behavior): a Director whose loyalty to the ruler is below the line **skims dividends** (a portion of the enterprise's output diverts to the Director's `gold_reserve` instead of the house treasury) and **worsens accident odds** at that enterprise. This makes Director appointment a live tension, not a cosmetic stat, and gives the player a reason to spend attention and shares keeping the right people in the right chairs.

### 5.4 Buyouts — attack & defend

- **Attack:** launch a hostile buyout of a rival with the **existing** `start_takeover` initiative and `Takeover` engine (`schemes.py` / `chassis.py` advance loop), now surfaced as a player UI action and priced through `market.value`.
- **Defend:** defense is **buyback only** (§5.2) — buy your own disloyal kin's stakes back before the predator does. There is no separate "rally the family" verb.

Attack and defense share one currency of control: your disloyal brother's 8% is either the wedge a rival buys to take your House or the stake you buy back to keep it, and the market sets the price.

## 6. The Enterprises panel

A new **"Enterprises"** tab in `ui/broadsheet.py`, wired in `ui/app.py`, following the redesign's collapsed-briefing → deep-panel pattern.

- **Default (collapsed): the Grip banner.** Grip band + controlling stake + the top predator's advance (name, stake, seize threshold, "courting your kin" note) + the market ticker. The Succession question is always the first thing on screen.
- **Expanded: the full ledger.** A table of the house's enterprises (venture, sector, tier, this-turn dividend + delta, Director + loyalty flag, your stake vs. largest outside holder), per-enterprise actions (**Expand**, **Appoint Director**, **Buy/Sell shares**), a **Found** action, and a **Buyouts** section (Defend: buy back a named kin's stake at its price; Attack: launch a takeover of a named rival). Director loyalty flags surface the disloyal-Director case inline (e.g. a `skim` marker).

The panel is a read-model client: it renders `grip.py` + `market.py` and turns clicks into the initiatives above. No simulation logic lives in the UI.

## 7. Module map

**New**
- `gilded/market.py` — commodity price state, per-turn supply/demand clearing, `price(commodity)`, `value(ent)`, market confidence.
- `gilded/grip.py` — pure read-model: loyal bloc, controlling stake, top predator, band, per-enterprise breakdown.
- Tests: `gilded/tests/test_market.py`, `gilded/tests/test_grip.py`.

**Extended**
- `gilded/society/shares.py` — priced buy/sell wrapper over `transfer_shares`.
- `gilded/enterprises.py` — activate `tech_mod`; input-cost accounting for consuming enterprises; disloyal-Director skim/accident hooks.
- `gilded/docket.py` — new initiatives `buy_shares`, `sell_shares`, `appoint_director`.
- `gilded/chassis.py` — advance the market each turn; thread commodity price + input costs + skim into the dividend loop.
- `gilded/ui/broadsheet.py`, `gilded/ui/app.py` — the Enterprises tab and its click-actions.
- Relevant existing tests (`test_chassis.py`, `test_docket.py`, `test_enterprises.py`, `test_soak.py`) updated for the new seams.

## 8. Build layers

The stage builds in shippable layers (each its own CynCo wave, reviewed against this spec), deepest-foundation first:

- **L1 — Market core.** `market.py`: commodity prices from supply/demand over the chain; thread into dividends + input costs + `tech_mod`; ticker data. (No UI yet; verified by tests + smoke.)
- **L2 — Grip read-model.** `grip.py`: loyal bloc, controlling stake, predator, bands, per-enterprise breakdown.
- **L3 — Levers.** Priced buy/sell + valuation; `appoint_director` + candidate pool + disloyal-Director skim/accident; surface `found`/`expand`/`start_takeover` as player initiatives.
- **L4 — The panel.** Enterprises tab: collapsed Grip banner ↔ expanded ledger; wire all click-actions; market ticker; AI parity check (rivals already act through the same initiatives).

## 9. Acceptance criteria

- A coal strike measurably raises the coal price, raises ironworks' input cost, lowers steel supply, and reduces dividends beyond the striking house — demonstrable in a soak/smoke run.
- A house that over-builds one sector depresses that sector's price and its own dividends.
- `market.value` prices both a share trade and a buyout; a boom raises both, a bust lowers both.
- Buying back a disloyal kin's stake reduces the top predator's reachable stake and improves the Grip band; selling raises treasury but lowers controlling stake.
- A disloyal Director diverts dividends from the treasury and raises that enterprise's accident odds; appointing a loyal, high-`industry` Director reverses both.
- The Enterprises panel renders the Grip banner by default and expands to the full ledger; every action button maps to a one-attention initiative; AI houses exercise the same initiatives.
- Full scoped suite green (`GILDED_NARRATE=0 SDL_VIDEODRIVER=dummy python -m pytest gilded/ test_civkings.py -q`), a Stage 4 smoke prints OK over a full century, determinism preserved (no `game.rng` in market clearing or the Grip read-model).

## 10. Out of scope (for Stage 4)

- **Inter-house trade routes / tariffs** (`external_trade_routes.py`, Trader units) — a diplomatic-economic subsystem deferred to a later stage.
- **Action-economy redesign** — Stage 7. Levers stay one-attention-per-initiative.
- **Discrete narrative market shocks** (rail bubble / financial panic fired by the saga layer) — a clean later add on top of the emergent market; not built here.
- **New styling/polish** — Stage 8. Use existing pygame assets.

## 11. Risks & open notes

- **Scope.** The four layers are individually shippable; if L3/L4 overrun, L1–L2 still deliver a deeper, price-alive economy. Keep the chain bounded to four commodities.
- **Balance.** Emergent prices can oscillate; the clearing needs bounding and damping so a single strike does not detonate the whole economy. Tune against the soak run.
- **Determinism.** The market clearing and Grip read-model must be `game.rng`-free (Stage 2/3 discipline); any stochastic texture stays out of the core.
- **`market_simulation.py` reuse.** Adapt its supply/demand/price logic into `gilded/market.py` rather than importing the root module directly, to keep the gilded layer self-contained.
