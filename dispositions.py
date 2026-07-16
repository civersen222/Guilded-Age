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
