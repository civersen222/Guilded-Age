"""Stage 3: Policy Dials — pure read-model over the five directive stances.

Maps the five stances (capital, labor, expansion, diplomacy, war) to a frozen
`PolicyEffects` struct. The chassis calls `effects(game, house)` once per house
per turn and applies each field at the appropriate seam.

The Policies tab displays the same values. Pure and deterministic: it never mutates
the game and never touches game.rng. The labor dial is realized as a house-wide
extraction level written into each enterprise's existing dial, so all the
society.labor curves (and the endings blood axis) keep working unchanged.
"""

from dataclasses import dataclass

from gilded.society import labor


@dataclass(frozen=True)
class PolicyEffects:
    extraction_level: int    # labor   -> written into each owned enterprise's extraction_dial
    output_mod: float        # capital -> multiplier on enterprise capacity output
    build_speed_mod: float   # capital -> multiplier on construction progress
    expand_cost_mod: float   # expansion -> multiplier on founding cost (lower = cheaper)
    strength_mod: float      # war     -> multiplier on regiment combat power
    happiness_mod: float     # diplomacy -> additive modifier to province happiness
    legitimacy_mod: float    # diplomacy -> additive modifier to legitimacy tick
    relations_drift: float   # diplomacy -> per-turn drift applied to relations
    trade_income: float      # expansion -> additive per-turn income from trade
    unrest_add: float        # labor     -> additive modifier to province unrest


def effects(game, house) -> PolicyEffects:
    """Pure read-model: derive policy effects from the current stances.

    Never mutates the game and never touches game.rng.
    """
    d = game.directives[house]
    stances = d.stances

    capital = stances.get("capital", 0)
    labor_stance = stances.get("labor", 0)
    expansion = stances.get("expansion", 0)
    diplomacy = stances.get("diplomacy", 0)
    war = stances.get("war", 0)

    # --- Labor dial → extraction_level (0..100) ---
    # Maps stance [-100,100] to extraction_level [0,100]
    extraction_level = int(50 + labor_stance * 0.5)
    # Clamp to [0, 100]
    extraction_level = max(0, min(100, extraction_level))

    # Labor unrest add: extractionist stance adds unrest
    unrest_add = labor_stance * 0.001

    # --- Capital dial → output_mod, build_speed_mod ---
    # Industrialist (capital > 0) boosts output and build speed
    capital_t = capital / 100.0
    output_mod = 1.0 + capital_t * 0.3
    build_speed_mod = 1.0 + capital_t * 0.2

    # --- Expansion dial → expand_cost_mod, trade_income ---
    # Expansionism (expansion > 0) lowers founding cost, increases trade income
    expansion_t = expansion / 100.0
    expand_cost_mod = 1.0 - expansion_t * 0.4  # lower = cheaper to found
    trade_income = expansion_t * 2.0

    # --- Diplomacy dial → happiness_mod, legitimacy_mod, relations_drift ---
    # Cosmopolitan (diplomacy > 0) boosts happiness and legitimacy
    diplomacy_t = diplomacy / 100.0
    happiness_mod = diplomacy_t * 2.0
    legitimacy_mod = diplomacy_t * 1.0
    relations_drift = diplomacy_t * 0.5

    # --- War dial → strength_mod ---
    # Militarist (war > 0) boosts regiment combat power
    war_t = war / 100.0
    strength_mod = 1.0 + war_t * 0.5

    return PolicyEffects(
        extraction_level=extraction_level,
        output_mod=output_mod,
        build_speed_mod=build_speed_mod,
        expand_cost_mod=expand_cost_mod,
        strength_mod=strength_mod,
        happiness_mod=happiness_mod,
        legitimacy_mod=legitimacy_mod,
        relations_drift=relations_drift,
        trade_income=trade_income,
        unrest_add=unrest_add,
    )
