"""Disposition spectrums (character-society spec 3.3).

Every character carries 30 paired-opposite disposition values in -100..+100.
A value past +/-50 surfaces a label in the character's traits list; past
+/-80 the label upgrades to an extreme form. Families:
  - temperament (15): personality; will drift with life events (M38).
  - conviction   (9): ideology; shapes politics and factions.
  - bloodline    (6): genetic; inherited and mostly fixed (M36).
Convention: the spectrum key is "<low>_<high>"; the LOW side is negative.
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class SpectrumPair:
    key: str
    family: str  # "temperament" | "conviction" | "bloodline"
    low_label: str
    high_label: str
    low_extreme: str
    high_extreme: str


PAIRS: Dict[str, SpectrumPair] = {p.key: p for p in [
    # --- Temperament (15) ---
    SpectrumPair("bold_craven", "temperament", "Bold", "Craven", "Fearless", "Spineless"),
    SpectrumPair("cruel_compassionate", "temperament", "Cruel", "Compassionate", "Butcher", "Bleeding Heart"),
    SpectrumPair("ambitious_content", "temperament", "Ambitious", "Content", "Power-Hungry", "Aimless"),
    SpectrumPair("honest_deceitful", "temperament", "Honest", "Deceitful", "Painfully Honest", "Pathological Liar"),
    SpectrumPair("temperate_hedonist", "temperament", "Temperate", "Hedonist", "Ascetic", "Debauched"),
    SpectrumPair("diligent_slothful", "temperament", "Diligent", "Slothful", "Workhorse", "Idle"),
    SpectrumPair("forgiving_vengeful", "temperament", "Forgiving", "Vengeful", "Saintly", "Grudge-Bearer"),
    SpectrumPair("generous_greedy", "temperament", "Generous", "Greedy", "Prodigal", "Miserly"),
    SpectrumPair("gregarious_reclusive", "temperament", "Gregarious", "Reclusive", "Life of the Party", "Hermit"),
    SpectrumPair("humble_arrogant", "temperament", "Humble", "Arrogant", "Self-Effacing", "Insufferable"),
    SpectrumPair("patient_impulsive", "temperament", "Patient", "Impulsive", "Unshakeable", "Reckless"),
    SpectrumPair("stoic_volatile", "temperament", "Stoic", "Volatile", "Iron-Willed", "Powder Keg"),
    SpectrumPair("trusting_paranoid", "temperament", "Trusting", "Paranoid", "Naive", "Conspiracist"),
    SpectrumPair("romantic_cold", "temperament", "Romantic", "Cold", "Lovestruck", "Heartless"),
    SpectrumPair("principled_pragmatic", "temperament", "Principled", "Pragmatic", "Zealous Idealist", "Machiavellian"),
    # --- Conviction (9) ---
    SpectrumPair("traditionalist_modernist", "conviction", "Traditionalist", "Modernist", "Reactionary", "Radical"),
    SpectrumPair("labor_capital", "conviction", "Labor Sympathizer", "Capitalist", "Syndicalist", "Robber Baron"),
    SpectrumPair("pious_secular", "conviction", "Pious", "Secular", "Fanatic", "Godless"),
    SpectrumPair("militarist_pacifist", "conviction", "Militarist", "Pacifist", "Warmonger", "Dove"),
    SpectrumPair("nationalist_cosmopolitan", "conviction", "Nationalist", "Cosmopolitan", "Chauvinist", "Rootless"),
    SpectrumPair("autocrat_constitutionalist", "conviction", "Autocrat", "Constitutionalist", "Absolutist", "Republican"),
    SpectrumPair("protectionist_freetrader", "conviction", "Protectionist", "Free Trader", "Isolationist", "Laissez-Faire"),
    SpectrumPair("paternalist_meritocrat", "conviction", "Paternalist", "Meritocrat", "Dynast", "Self-Made Zealot"),
    SpectrumPair("preservationist_extractionist", "conviction", "Preservationist", "Extractionist", "Conservationist", "Strip-Miner"),
    # --- Bloodline (6) ---
    SpectrumPair("brilliant_dull", "bloodline", "Brilliant", "Dull", "Genius", "Imbecile"),
    SpectrumPair("robust_sickly", "bloodline", "Robust", "Sickly", "Herculean", "Infirm"),
    SpectrumPair("magnetic_repellent", "bloodline", "Magnetic", "Repellent", "Captivating", "Odious"),
    SpectrumPair("fecund_barren", "bloodline", "Fecund", "Barren", "Prolific", "Sterile"),
    SpectrumPair("longlived_shortlived", "bloodline", "Long-Lived", "Short-Lived", "Ageless", "Doomed"),
    SpectrumPair("comely_plain", "bloodline", "Comely", "Plain", "Beautiful", "Hideous"),
]}

LABEL_THRESHOLD = 50
EXTREME_THRESHOLD = 80


def label_for(pair_key: str, value: float) -> Optional[str]:
    """Label surfaced by one spectrum value, or None inside the dead zone."""
    pair = PAIRS[pair_key]
    if value <= -EXTREME_THRESHOLD:
        return pair.low_extreme
    if value <= -LABEL_THRESHOLD:
        return pair.low_label
    if value >= EXTREME_THRESHOLD:
        return pair.high_extreme
    if value >= LABEL_THRESHOLD:
        return pair.high_label
    return None


def labels_for(dispositions: Dict[str, float]) -> List[str]:
    """All labels surfaced by a character's disposition dict."""
    out: List[str] = []
    for key in PAIRS:
        label = label_for(key, dispositions.get(key, 0.0))
        if label is not None:
            out.append(label)
    return out


def initial_dispositions() -> Dict[str, float]:
    """Random starting spectrums: most people sit in the dead zone."""
    disp: Dict[str, float] = {}
    for key, pair in PAIRS.items():
        sigma = 20.0 if pair.family == "bloodline" else 30.0
        disp[key] = max(-100.0, min(100.0, random.gauss(0.0, sigma)))
    return disp


def apply_drift(char, pair_key: str, amount: float, reason: str = "") -> Optional[str]:
    """Push one of a character's spectrums by `amount` (spec 3.4 drift).

    Returns a log line when the move crosses a label boundary (e.g.
    "Livia has become Vengeful (passed over)"), else None."""
    old_v = char.dispositions.get(pair_key, 0.0)
    new_v = max(-100.0, min(100.0, old_v + amount))
    char.dispositions[pair_key] = new_v
    old_label = label_for(pair_key, old_v)
    new_label = label_for(pair_key, new_v)
    if new_label != old_label and new_label is not None:
        why = f" ({reason})" if reason else ""
        return f"{char.name} has become {new_label}{why}"
    return None


def witness_drift(char, pair_key: str, magnitude: float, reason: str = "") -> Optional[str]:
    """A life event pushes a witness along a spectrum, in a direction
    weighted by where they already stand - the entrenched entrench
    (spec 3.4: ignored disaster drifts toward Callous OR snaps toward
    Reformist, weighted by existing temperament)."""
    v = char.dispositions.get(pair_key, 0.0)
    p_high = 0.5 + 0.3 * (v / 100.0)   # 50/50 at 0, 80/20 at +/-100
    direction = 1.0 if random.random() < p_high else -1.0
    return apply_drift(char, pair_key, direction * abs(magnitude), reason)


def inherit_dispositions(parent_a: Dict[str, float],
                         parent_b: Dict[str, float]) -> Dict[str, float]:
    """Conception-time spectrums (spec 3.3): Bloodline blends the parents'
    values with mutation jitter (Houses can breed for talent); Temperament
    and Conviction start near neutral - childhood shapes them (drift, M38)."""
    disp: Dict[str, float] = {}
    for key, pair in PAIRS.items():
        if pair.family == "bloodline":
            mid = (parent_a.get(key, 0.0) + parent_b.get(key, 0.0)) / 2.0
            disp[key] = max(-100.0, min(100.0, mid + random.gauss(0.0, 12.0)))
        else:
            disp[key] = max(-100.0, min(100.0, random.gauss(0.0, 10.0)))
    return disp


# Spec 3.5: acting against your own entrenched nature is what stresses you.
# action -> ((pair_key, conflicting_sign), ...): sign +1 means the HIGH side
# of the spectrum conflicts with the action, -1 the LOW side.
ACTION_CONFLICTS: Dict[str, tuple] = {
    "execute": (("cruel_compassionate", 1),),
    "show_mercy": (("cruel_compassionate", -1), ("forgiving_vengeful", 1)),
    "scheme": (("honest_deceitful", -1),),
    "plot": (("honest_deceitful", -1),),
    "break_treaty": (("honest_deceitful", -1), ("principled_pragmatic", -1)),
    "declare_war": (("militarist_pacifist", 1),),
    "raise_taxes": (("generous_greedy", -1),),
    "accept_unfavorable_peace": (("ambitious_content", -1),),
    "cover_up": (("honest_deceitful", -1), ("cruel_compassionate", 1)),
    "blackmail": (("honest_deceitful", -1), ("cruel_compassionate", 1)),
}


def contradiction_stress(dispositions: Dict[str, float], action_type: str) -> int:
    """Stress from acting against entrenched spectrum positions (spec 3.5).

    Positions past the +/-50 label line on the conflicting side add
    |value|/5 stress each; dead-zone characters act freely."""
    total = 0.0
    for pair_key, sign in ACTION_CONFLICTS.get(action_type, ()):
        v = dispositions.get(pair_key, 0.0)
        if sign > 0 and v >= LABEL_THRESHOLD:
            total += v / 5.0
        elif sign < 0 and v <= -LABEL_THRESHOLD:
            total += -v / 5.0
    return int(total)


# Spec 3.5: a coping vice is lived in private - it shifts the TRUE spectrum
# while the public persona lags behind. vice -> (pair_key, private_drift).
VICE_DRIFTS: Dict[str, tuple] = {
    "Drunkard": ("temperate_hedonist", 15.0),
    "Gambler": ("patient_impulsive", 15.0),
    "Callous": ("cruel_compassionate", -15.0),
    "Recluse": ("gregarious_reclusive", 15.0),
}


RUB_OFF_RATE = 0.05


def guardian_rub_off(child, guardian) -> List[str]:
    """Childhood shaping (M50, spec 3.6): a guardian's temperament and
    convictions rub off on their ward - each turn the child's spectrums
    drift a fraction of the way toward the guardian's. Bloodline is
    genetic and never rubs off."""
    msgs: List[str] = []
    for key, pair in PAIRS.items():
        if pair.family == "bloodline":
            continue
        gv = guardian.dispositions.get(key, 0.0)
        cv = child.dispositions.get(key, 0.0)
        delta = (gv - cv) * RUB_OFF_RATE
        if abs(delta) < 0.01:
            continue
        m = apply_drift(child, key, delta, f"raised by {guardian.name}")
        if m:
            msgs.append(m)
    return msgs


# Spec 6 (M63): an exposé collapses the persona gap - society learns the
# truth all at once, and assumes the worst about what else is hidden.
EXPOSE_SCAR = 0.3   # persona-only push toward Deceitful, per potency point


def expose_persona(char, potency: float) -> float:
    """Snap the public persona to the private truth (spec 6: Expose).

    Every spectrum's public estimate is set to the true value, and the
    exposure leaves a persona-only scar toward Deceitful - the exposed
    are presumed liars. Returns the total gap closed (the shock value)."""
    gap = 0.0
    for key in PAIRS:
        true_v = char.dispositions.get(key, 0.0)
        gap += abs(true_v - char.persona.get(key, true_v))
        char.persona[key] = true_v
    scar = char.persona.get("honest_deceitful", 0.0) + potency * EXPOSE_SCAR
    char.persona["honest_deceitful"] = max(-100.0, min(100.0, scar))
    return gap
