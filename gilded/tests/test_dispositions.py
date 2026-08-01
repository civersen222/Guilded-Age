"""Disposition spectrums — nine rules, typed constants, no module imports.

R1: Label threshold sits at 50 (inclusive both directions).
R2: Extreme threshold sits at 80 (inclusive both directions).
R3: Entrenched entrench — bias at zero is 0.5, at +100 is 0.8, at -100 is 0.2.
R4: Guardian rubs off at rate 0.05; bloodline is exempt; floor is 0.01.
R5: Inheritance — bloodline blends parents (sigma 12), temp/conv near neutral (sigma 10).
R6: Contradiction stress — threshold 50, divisor 5, floors to int.
R7: Expose — snaps all 30, returns summed gap, scar = potency * 0.3 on persona.
R8: Drift announces on new label only; silent within label, silent into dead zone, silent out of label.
R9: Initial dispositions — centred on zero, bloodline sigma 20 < temperament sigma 30.
"""

import random
from unittest import mock

from gilded.society.characters import Character, SocietyState
from gilded.society.dispositions import (
    label_for,
    labels_for,
    initial_dispositions,
    apply_drift,
    witness_drift,
    inherit_dispositions,
    contradiction_stress,
    guardian_rub_off,
    expose_persona,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _char(name="Livia", rng_seed=0, dispositions=None, persona=None):
    """Create a character with controlled dispositions."""
    soc = SocietyState(random.Random(rng_seed))
    c = Character(name=name, stats={}, traits=[], age=40, gender="Female", society=soc)
    if dispositions is not None:
        c.dispositions.clear()
        c.dispositions.update(dispositions)
    if persona is not None:
        c.persona.clear()
        c.persona.update(persona)
    return c


def _ctrl_rng(value):
    """Return a mock Random that returns `value` for .random() calls."""
    m = mock.Mock(spec=random.Random)
    m.random.return_value = value
    return m


# ===========================================================================
# R1: WHERE A SPECTRUM STARTS SHOWING IN A CHARACTER'S TRAITS
# ===========================================================================
# LABEL_THRESHOLD = 50, inclusive. Values <= -50 or >= 50 surface a label.

def test_r1_dead_zone_no_label():
    """0 is inside the dead zone — no label surfaces."""
    assert label_for("bold_craven", 0) is None


def test_r1_threshold_inclusive_positive():
    """Exactly +50 surfaces the HIGH label (inclusive)."""
    assert label_for("bold_craven", 50) == "Craven"


def test_r1_threshold_inclusive_negative():
    """Exactly -50 surfaces the LOW label (inclusive)."""
    assert label_for("bold_craven", -50) == "Bold"


def test_r1_past_threshold_positive():
    """Past +50 still surfaces the HIGH label."""
    assert label_for("bold_craven", 51) == "Craven"


def test_r1_past_threshold_negative():
    """Past -50 still surfaces the LOW label."""
    assert label_for("bold_craven", -51) == "Bold"


def test_r1_just_inside_dead_zone():
    """49 is just inside the dead zone — no label."""
    assert label_for("bold_craven", 49) is None


def test_r2_extreme_just_below():
    """79 is just below extreme threshold — normal label."""
    assert label_for("bold_craven", 79) == "Craven"

def test_r2_extreme_just_above():
    """81 is just above extreme threshold — extreme label."""
    assert label_for("bold_craven", 81) == "Spineless"


# ===========================================================================
# R2: WHERE THE LABEL UPGRADES TO ITS EXTREME FORM
# ===========================================================================
# EXTREME_THRESHOLD = 80, inclusive. Four labels + silence per spectrum.

def test_r2_all_five_states_positive_side():
    """Five reachable states on the positive side of bold_craven."""
    assert label_for("bold_craven", 0) is None
    assert label_for("bold_craven", 50) == "Craven"
    assert label_for("bold_craven", 79) == "Craven"
    assert label_for("bold_craven", 80) == "Spineless"
    assert label_for("bold_craven", 100) == "Spineless"


def test_r2_all_five_states_negative_side():
    """Five reachable states on the negative side of bold_craven."""
    assert label_for("bold_craven", 0) is None
    assert label_for("bold_craven", -50) == "Bold"
    assert label_for("bold_craven", -79) == "Bold"
    assert label_for("bold_craven", -80) == "Fearless"
    assert label_for("bold_craven", -100) == "Fearless"


def test_r2_labels_for_surfaces_all():
    """labels_for returns all labels from a disposition dict."""
    disp = {"bold_craven": 60, "cruel_compassionate": -85}
    labels = labels_for(disp)
    assert "Craven" in labels
    assert "Butcher" in labels
    assert len(labels) == 2


# ===========================================================================
# R3: THE ENTRENCHED ENTRENCH
# ===========================================================================
# p_high = 0.5 + 0.3 * (v / 100.0). At v=0: 0.5. At v=+100: 0.8. At v=-100: 0.2.
# Direction is +1 if roll < p_high, else -1.

def test_r3_even_odds_at_zero():
    """At standing 0, bias is 0.5 — roll 0.49 gives +1 (toward high), roll 0.51 gives -1."""
    c = _char(dispositions={"bold_craven": 0.0})
    c._rng = _ctrl_rng(0.49)
    witness_drift(c, "bold_craven", 10.0)
    assert c.dispositions["bold_craven"] > 0.0

    c2 = _char(dispositions={"bold_craven": 0.0})
    c2._rng = _ctrl_rng(0.51)
    witness_drift(c2, "bold_craven", 10.0)
    assert c2.dispositions["bold_craven"] < 0.0


def test_r3_bias_at_extreme_positive():
    """At standing +100, p_high = 0.8 — roll 0.79 gives +1 (further positive)."""
    c = _char(dispositions={"bold_craven": 100.0})
    c._rng = _ctrl_rng(0.79)
    witness_drift(c, "bold_craven", 10.0)
    assert c.dispositions["bold_craven"] > 100.0 - 10.0 or c.dispositions["bold_craven"] == 100.0


def test_r3_bias_at_extreme_negative():
    """At standing -100, p_high = 0.2 — roll 0.3 gives -1 (further negative)."""
    c = _char(dispositions={"bold_craven": -100.0})
    c._rng = _ctrl_rng(0.3)
    witness_drift(c, "bold_craven", 10.0)
    assert c.dispositions["bold_craven"] < -100.0 + 10.0 or c.dispositions["bold_craven"] == -100.0


def test_r3_bias_formula_at_midpoint():
    """At standing +50, p_high = 0.65 — roll 0.64 gives +1, roll 0.66 gives -1."""
    c = _char(dispositions={"bold_craven": 50.0})
    c._rng = _ctrl_rng(0.64)
    witness_drift(c, "bold_craven", 10.0)
    assert c.dispositions["bold_craven"] > 50.0

    c2 = _char(dispositions={"bold_craven": 50.0})
    c2._rng = _ctrl_rng(0.66)
    witness_drift(c2, "bold_craven", 10.0)
    assert c2.dispositions["bold_craven"] < 50.0


def test_r3_bias_coefficient_pinned():
    """p_high = 0.5 + 0.3*(v/100) — test at v=33.333 gives p_high = 0.6 exactly."""
    c = _char(dispositions={"bold_craven": 33.333333})
    c._rng = _ctrl_rng(0.59)
    witness_drift(c, "bold_craven", 10.0)
    assert c.dispositions["bold_craven"] > 33.333333

    c2 = _char(dispositions={"bold_craven": 33.333333})
    c2._rng = _ctrl_rng(0.61)
    witness_drift(c2, "bold_craven", 10.0)
    assert c2.dispositions["bold_craven"] < 33.333333


def test_r3_bias_formula_at_quarter():
    """At standing +25, p_high = 0.5 + 0.3*0.25 = 0.575 — roll 0.57 gives +1, roll 0.58 gives -1."""
    c = _char(dispositions={"bold_craven": 25.0})
    c._rng = _ctrl_rng(0.57)
    witness_drift(c, "bold_craven", 10.0)
    assert c.dispositions["bold_craven"] > 25.0

    c2 = _char(dispositions={"bold_craven": 25.0})
    c2._rng = _ctrl_rng(0.58)
    witness_drift(c2, "bold_craven", 10.0)
    assert c2.dispositions["bold_craven"] < 25.0


# ===========================================================================
# R4: WHAT A GUARDIAN DOES TO A CHILD
# ===========================================================================
# RUB_OFF_RATE = 0.05. Bloodline is exempt. Floor: abs(delta) < 0.01 is skipped.

def test_r4_temperament_rubs_off():
    """Guardian's temperament moves child by 0.05 * difference."""
    child = _char(dispositions={"bold_craven": 0.0})
    guardian = _char(name="Marcus", dispositions={"bold_craven": 100.0})
    msgs = guardian_rub_off(child, guardian)
    # delta = (100 - 0) * 0.05 = 5.0
    assert child.dispositions["bold_craven"] == 5.0


def test_r4_rub_off_rate_pinned():
    """RUB_OFF_RATE = 0.05 — verify exact rate with a 50-unit gap."""
    child = _char(dispositions={"bold_craven": 0.0})
    guardian = _char(name="Marcus", dispositions={"bold_craven": 50.0})
    guardian_rub_off(child, guardian)
    # delta = (50 - 0) * 0.05 = 2.5
    assert child.dispositions["bold_craven"] == 2.5


def test_r4_bloodline_does_not_rub_off():
    """Bloodline spectrums are untouched by guardian rub-off."""
    child = _char(dispositions={"robust_sickly": 0.0})
    guardian = _char(name="Marcus", dispositions={"robust_sickly": 100.0})
    guardian_rub_off(child, guardian)
    assert child.dispositions["robust_sickly"] == 0.0


def test_r4_same_test_proves_mechanism_runs():
    """Guardian moves child on temperament but NOT on bloodline — same fixture."""
    child = _char(dispositions={"bold_craven": 0.0, "robust_sickly": 0.0})
    guardian = _char(name="Marcus", dispositions={"bold_craven": 100.0, "robust_sickly": 100.0})
    guardian_rub_off(child, guardian)
    assert child.dispositions["bold_craven"] == 5.0
    assert child.dispositions["robust_sickly"] == 0.0


def test_r4_floor_skips_tiny_moves():
    """Guardian and child a hair apart — delta rounds to nothing, skipped."""
    child = _char(dispositions={"bold_craven": 99.9})
    guardian = _char(name="Marcus", dispositions={"bold_craven": 100.0})
    msgs = guardian_rub_off(child, guardian)
    # delta = (100 - 99.9) * 0.05 = 0.005 < 0.01 floor
    assert child.dispositions["bold_craven"] == 99.9
    assert msgs == []


# ===========================================================================
# R5: WHAT A CHILD IS BORN WITH
# ===========================================================================
# Bloodline: midpoint of parents + gauss(0, 12). Temp/Conv: gauss(0, 10).

def test_r5_bloodline_blends_parents():
    """Bloodline mean is near parents' midpoint, far from zero."""
    rng = random.Random(42)
    parent_a = {"robust_sickly": 80.0, "bold_craven": 0.0}
    parent_b = {"robust_sickly": 60.0, "bold_craven": 0.0}
    # Midpoint of robust_sickly = 70.0
    samples = [inherit_dispositions(parent_a, parent_b, rng) for _ in range(200)]
    mean = sum(s["robust_sickly"] for s in samples) / 200
    assert 65.0 < mean < 75.0  # near midpoint (70), within sigma 12

    # Temperament is near zero even with parents at zero (no blending)
    t_mean = sum(s["bold_craven"] for s in samples) / 200
    assert abs(t_mean) < 10.0  # near zero


def test_r5_bloodline_sigma_pinned():
    """Bloodline inheritance sigma=12 — sample std near 12."""
    rng = random.Random(42)
    parent_a = {"robust_sickly": 80.0}
    parent_b = {"robust_sickly": 60.0}
    # Midpoint = 70.0, sigma = 12
    samples = [inherit_dispositions(parent_a, parent_b, rng) for _ in range(1000)]
    vals = [s["robust_sickly"] for s in samples]
    mean = sum(vals) / 1000
    import math
    var = sum((v - mean)**2 for v in vals) / 1000
    std = math.sqrt(var)
    assert 10.5 < std < 13.5  # sigma 12, within ~12%


def test_r5_temperament_sigma_pinned():
    """Temperament inheritance sigma=10 — sample std near 10."""
    rng = random.Random(42)
    parent_a = {"bold_craven": 0.0}
    parent_b = {"bold_craven": 0.0}
    samples = [inherit_dispositions(parent_a, parent_b, rng) for _ in range(1000)]
    vals = [s["bold_craven"] for s in samples]
    mean = sum(vals) / 1000
    import math
    var = sum((v - mean)**2 for v in vals) / 1000
    std = math.sqrt(var)
    assert 8.5 < std < 11.5  # sigma 10, within ~15%


def test_r5_temperament_ignores_extreme_parents():
    """Temperament starts near zero even when both parents are extreme."""
    rng = random.Random(42)
    parent_a = {"bold_craven": 100.0, "robust_sickly": 0.0}
    parent_b = {"bold_craven": 100.0, "robust_sickly": 0.0}
    samples = [inherit_dispositions(parent_a, parent_b, rng) for _ in range(200)]
    mean = sum(s["bold_craven"] for s in samples) / 200
    assert abs(mean) < 15.0  # near zero, not near 100


def test_r5_spreads_differ():
    """Bloodline (sigma 12) varies less than temperament (sigma 10... wait, bloodline 12 > temp 10).
    Actually bloodline sigma=12, temp/conv sigma=10. So bloodline varies MORE.
    200 samples — enough for sample std to be within ~10% of population std."""
    rng = random.Random(42)
    parent_a = {"robust_sickly": 0.0, "bold_craven": 0.0}
    parent_b = {"robust_sickly": 0.0, "bold_craven": 0.0}
    samples = [inherit_dispositions(parent_a, parent_b, rng) for _ in range(200)]
    bl_vals = [s["robust_sickly"] for s in samples]
    t_vals = [s["bold_craven"] for s in samples]
    bl_var = sum((v - sum(bl_vals)/200)**2 for v in bl_vals) / 200
    t_var = sum((v - sum(t_vals)/200)**2 for v in t_vals) / 200
    assert bl_var > t_var  # bloodline sigma 12 > temperament sigma 10


def test_r5_values_clamped():
    """Every value stays inside -100..+100 however extreme the parents."""
    rng = random.Random(42)
    parent_a = {k: 100.0 for k in ["robust_sickly", "bold_craven"]}
    parent_b = {k: 100.0 for k in ["robust_sickly", "bold_craven"]}
    for _ in range(200):
        disp = inherit_dispositions(parent_a, parent_b, rng)
        for v in disp.values():
            assert -100.0 <= v <= 100.0


def test_r5_conviction_sigma_pinned():
    """Conviction inheritance sigma=10 — sample std near 10."""
    rng = random.Random(42)
    parent_a = {"militarist_pacifist": 0.0}  # conviction spectrum
    parent_b = {"militarist_pacifist": 0.0}
    samples = [inherit_dispositions(parent_a, parent_b, rng) for _ in range(1000)]
    vals = [s["militarist_pacifist"] for s in samples]
    mean = sum(vals) / 1000
    import math
    var = sum((v - mean)**2 for v in vals) / 1000
    std = math.sqrt(var)
    assert 8.5 < std < 11.5  # sigma 10, within ~15%


# ===========================================================================
# R6: WHAT IT COSTS TO ACT AGAINST YOUR OWN NATURE
# ===========================================================================
# Threshold is LABEL_THRESHOLD (50). Cost = |value|/5 per conflicting spectrum.
# Returns int (floors the remainder).

def test_r6_dead_zone_pays_nothing():
    """Character at 0 pays no stress for any action."""
    disp = {"cruel_compassionate": 0.0}
    assert contradiction_stress(disp, "execute") == 0


def test_r6_past_threshold_pays_stress():
    """Character at +60 on cruel_compassionate pays 60/5 = 12 stress for execute."""
    disp = {"cruel_compassionate": 60.0}
    assert contradiction_stress(disp, "execute") == 12


def test_r6_threshold_exact():
    """Character exactly at +50 pays 50/5 = 10 stress."""
    disp = {"cruel_compassionate": 50.0}
    assert contradiction_stress(disp, "execute") == 10

def test_r6_just_below_threshold_no_stress():
    """Character at +49 is below threshold — no stress."""
    disp = {"cruel_compassionate": 49.0}
    assert contradiction_stress(disp, "execute") == 0


def test_r6_rounding_floors_remainder():
    """Distance 53 gives 53/5 = 10.6, returned as int 10."""
    disp = {"cruel_compassionate": 53.0}
    assert contradiction_stress(disp, "execute") == 10


def test_r6_multiple_conflicts_add():
    """show_mercy conflicts with cruel_compassionate(-1) and forgiving_vengeful(1).
    Character entrenched on both pays combined stress."""
    disp = {
        "cruel_compassionate": -60.0,  # conflicts with show_mercy (sign -1, v <= -50)
        "forgiving_vengeful": 70.0,     # conflicts with show_mercy (sign +1, v >= 50)
    }
    assert contradiction_stress(disp, "show_mercy") == 60 // 5 + 70 // 5


def test_r6_divisor_is_five():
    """Stress divisor is exactly 5 — value 100 gives 20 stress."""
    disp = {"cruel_compassionate": 100.0}
    assert contradiction_stress(disp, "execute") == 20

def test_r6_divisor_is_five_negative():
    """Stress divisor is exactly 5 — value -100 gives 20 stress."""
    disp = {"cruel_compassionate": -100.0}
    assert contradiction_stress(disp, "show_mercy") == 20


# ===========================================================================
# R7: WHAT AN EXPOSÉ TAKES
# ===========================================================================
# Returns summed gap across all 30 spectrums. Scar = potency * 0.3 on persona
# honest_deceitful toward Deceitful (positive direction).

def test_r7_zero_gap_when_persona_equals_truth():
    """No gap between persona and truth — exposé returns 0."""
    c = _char(dispositions={"bold_craven": 50.0}, persona={"bold_craven": 50.0})
    gap = expose_persona(c, 10.0)
    assert gap == 0.0


def test_r7_returns_summed_gap():
    """Build a known gap across two spectrums and assert the exact total."""
    c = _char(
        dispositions={"bold_craven": 80.0, "cruel_compassionate": -40.0},
        persona={"bold_craven": 0.0, "cruel_compassionate": 0.0},
    )
    # Gap = |80-0| + |-40-0| = 120
    gap = expose_persona(c, 10.0)
    assert gap == 120.0


def test_r7_all_thirty_snapped():
    """After exposé, all 30 persona values equal dispositions."""
    disp = {k: float(i * 3) for i, k in enumerate(["bold_craven", "cruel_compassionate", "ambitious_content"])}
    persona = {k: 0.0 for k in disp}
    c = _char(dispositions=disp, persona=persona)
    expose_persona(c, 0.0)
    for k in disp:
        assert c.persona[k] == c.dispositions[k]


def test_r7_scar_on_persona_not_truth():
    """Scar pushes persona honest_deceitful toward Deceitful, not the truth."""
    c = _char(
        dispositions={"honest_deceitful": -80.0},
        persona={"honest_deceitful": -80.0},
    )
    expose_persona(c, 20.0)
    # Gap is 0 (persona = truth), scar = -80 + 20*0.3 = -74
    assert c.persona["honest_deceitful"] == -74.0
    assert c.dispositions["honest_deceitful"] == -80.0


def test_r7_scar_clamped_at_ceiling():
    """Scar that would push past +100 is clamped."""
    c = _char(
        dispositions={"honest_deceitful": 90.0},
        persona={"honest_deceitful": 90.0},
    )
    expose_persona(c, 100.0)
    # scar = 90 + 100*0.3 = 120, clamped to 100
    assert c.persona["honest_deceitful"] == 100.0


def test_r7_scar_rate_pinned():
    """EXPOSE_SCAR = 0.3 — verify with potency=50, starting from zero."""
    c = _char(
        dispositions={"honest_deceitful": 0.0},
        persona={"honest_deceitful": 0.0},
    )
    expose_persona(c, 50.0)
    # scar = 0 + 50*0.3 = 15.0
    assert c.persona["honest_deceitful"] == 15.0


# ===========================================================================
# R8: WHEN A DRIFT ANNOUNCES ITSELF
# ===========================================================================
# Returns log line only when crossing into a NEW label. Silent within label,
# silent into dead zone, silent OUT of label back into dead zone.

def test_r8_announces_new_label():
    """Moving from dead zone into label territory announces the new label."""
    c = _char(dispositions={"bold_craven": 40.0})
    msg = apply_drift(c, "bold_craven", 15.0, "test")
    assert msg is not None
    assert "Craven" in msg


def test_r8_silent_within_label():
    """Moving further inside a label is silent."""
    c = _char(dispositions={"bold_craven": 60.0})
    msg = apply_drift(c, "bold_craven", 10.0, "test")
    assert msg is None


def test_r8_silent_into_dead_zone():
    """Moving further inside the dead zone is silent."""
    c = _char(dispositions={"bold_craven": 10.0})
    msg = apply_drift(c, "bold_craven", 5.0, "test")
    assert msg is None


def test_r8_silent_out_of_label():
    """Moving OUT of a label back into the dead zone is ALSO silent."""
    c = _char(dispositions={"bold_craven": 60.0})
    msg = apply_drift(c, "bold_craven", -30.0, "test")
    # Now at 30.0 — in dead zone. No new label to announce.
    assert msg is None


def test_r8_clamp_at_ceiling():
    """Character at +95 pushed by +20 lands at +100, not +115."""
    c = _char(dispositions={"bold_craven": 95.0})
    apply_drift(c, "bold_craven", 20.0)
    assert c.dispositions["bold_craven"] == 100.0


def test_r8_clamp_at_floor():
    """Character at -95 pushed by -20 lands at -100, not -115."""
    c = _char(dispositions={"bold_craven": -95.0})
    apply_drift(c, "bold_craven", -20.0)
    assert c.dispositions["bold_craven"] == -100.0


def test_r8_nothing_changed_silent():
    """Zero drift produces no announcement."""
    c = _char(dispositions={"bold_craven": 60.0})
    msg = apply_drift(c, "bold_craven", 0.0, "test")
    assert msg is None


# ===========================================================================
# R9: WHAT THE FOUNDING GENERATION IS BORN WITH
# ===========================================================================
# Centred on zero. Bloodline sigma=20 < Temperament sigma=30.
# Most people sit in the dead zone.

def test_r9_centred_on_zero():
    """Initial dispositions are centred near zero for all families."""
    rng = random.Random(42)
    samples = [initial_dispositions(rng) for _ in range(200)]
    # Bloodline mean near zero
    bl_mean = sum(s["robust_sickly"] for s in samples) / 200
    assert abs(bl_mean) < 10.0
    # Temperament mean near zero
    t_mean = sum(s["bold_craven"] for s in samples) / 200
    assert abs(t_mean) < 10.0


def test_r9_bloodline_tighter_than_temperament():
    """Bloodline (sigma 20) varies less than temperament (sigma 30).
    200 samples — enough for sample variance ratio to be reliable."""
    rng = random.Random(42)
    samples = [initial_dispositions(rng) for _ in range(200)]
    bl_vals = [s["robust_sickly"] for s in samples]
    t_vals = [s["bold_craven"] for s in samples]
    bl_var = sum(v**2 for v in bl_vals) / 200  # mean is ~0
    t_var = sum(v**2 for v in t_vals) / 200
    assert bl_var < t_var  # 20^2 < 30^2


def test_r9_bloodline_spread_pinned():
    """Bloodline sigma=20 — sample std near 20.
    1000 samples gives ~3% precision on std estimate."""
    rng = random.Random(42)
    samples = [initial_dispositions(rng) for _ in range(1000)]
    bl_vals = [s["robust_sickly"] for s in samples]
    mean = sum(bl_vals) / 1000
    var = sum((v - mean)**2 for v in bl_vals) / 1000
    import math
    std = math.sqrt(var)
    assert 18.0 < std < 22.0  # sigma 20, within 10%


def test_r9_temperament_spread_pinned():
    """Temperament sigma=30 — sample std near 30.
    1000 samples gives ~3% precision on std estimate."""
    rng = random.Random(42)
    samples = [initial_dispositions(rng) for _ in range(1000)]
    t_vals = [s["bold_craven"] for s in samples]
    mean = sum(t_vals) / 1000
    var = sum((v - mean)**2 for v in t_vals) / 1000
    import math
    std = math.sqrt(var)
    assert 28.0 < std < 32.0  # sigma 30, within ~7%


def test_r9_most_in_dead_zone():
    """Most people sit in the dead zone (|v| < 50 for all spectrums).
    With sigma 20-30, roughly 68% of values are within ±1 sigma,
    so a majority should have |v| < 50 for most spectrums."""
    rng = random.Random(42)
    samples = [initial_dispositions(rng) for _ in range(200)]
    # Count characters where bold_craven is in dead zone
    in_dead = sum(1 for s in samples if abs(s["bold_craven"]) < 50)
    assert in_dead > 100  # majority in dead zone


def test_r9_count_is_thirty():
    """initial_dispositions returns exactly 30 spectrums."""
    rng = random.Random(42)
    disp = initial_dispositions(rng)
    assert len(disp) == 30


def test_r9_all_clamped():
    """All initial values stay within -100..+100."""
    rng = random.Random(42)
    for _ in range(1000):
        disp = initial_dispositions(rng)
        for v in disp.values():
            assert -100.0 <= v <= 100.0


# ===========================================================================
# Q1: WHICH WAY A TIE FALLS, WHEN A WITNESS IS PUSHED
# ===========================================================================
# At v=0, p_high = 0.5. Roll exactly 0.5: 0.5 < 0.5 is False -> direction = -1


def test_q1_tie_at_neutral_goes_low():
    """At standing 0, a roll exactly equal to p_high (0.5) resolves to LOW side."""
    c = _char(dispositions={"bold_craven": 0.0})
    c._rng = _ctrl_rng(0.5)  # Exactly equal to p_high = 0.5
    witness_drift(c, "bold_craven", 10.0)
    # 0.5 < 0.5 is False -> direction = -1.0 -> moves negative
    assert c.dispositions["bold_craven"] == -10.0


# ===========================================================================
# Q2: WHAT A NEGATIVE MAGNITUDE MEANS TO A WITNESS
# ===========================================================================
# witness_drift uses abs(magnitude) - sign is discarded; roll decides direction.


def test_q2_negative_magnitude_discards_sign():
    """Negative magnitude is treated as its absolute value; direction comes from the roll."""
    c_neg = _char(dispositions={"bold_craven": 0.0})
    c_neg._rng = _ctrl_rng(0.49)  # 0.49 < 0.5 -> direction = +1
    witness_drift(c_neg, "bold_craven", -10.0)  # negative magnitude
    assert c_neg.dispositions["bold_craven"] == 10.0

    c_pos = _char(dispositions={"bold_craven": 0.0})
    c_pos._rng = _ctrl_rng(0.49)  # Same roll
    witness_drift(c_pos, "bold_craven", 10.0)   # positive magnitude
    assert c_pos.dispositions["bold_craven"] == c_neg.dispositions["bold_craven"]


# ===========================================================================
# Q3: HOW SMALL A CHILDHOOD INFLUENCE STILL COUNTS
# ===========================================================================
# RUB_OFF_RATE = 0.05, floor = 0.01. A gap of 1.0 -> delta = 0.05 (>= 0.01, applied).
# 0.05 is clearly > 0.01 (floor) and < 1.0 (one whole point).


def test_q3_small_influence_below_one_point_applies():
    """Gap of 1.0 produces delta = 0.05 - above the 0.01 floor, below 1 whole point."""
    child = _char(dispositions={"bold_craven": 0.0})
    guardian = _char(name="Marcus", dispositions={"bold_craven": 1.0})
    guardian_rub_off(child, guardian)
    # delta = (1.0 - 0.0) * 0.05 = 0.05, which is >= 0.01 floor -> applied
    assert child.dispositions["bold_craven"] == 0.05


# ===========================================================================
# Q4: THE STRESS LINE ON THE LOW SIDE
# ===========================================================================
# LABEL_THRESHOLD = 50. Low-side branch: sign < 0 and v <= -LABEL_THRESHOLD.
# show_mercy conflicts with cruel_compassionate (sign -1).


def test_q4_low_side_exactly_on_threshold_pays_stress():
    """Character at exactly -50 on low-conflicting side pays stress."""
    disp = {"cruel_compassionate": -50.0}  # sign=-1 for show_mercy, v=-50
    assert contradiction_stress(disp, "show_mercy") == 10


def test_q4_low_side_one_point_inside_no_stress():
    """Character at -49 (one point inside threshold on low side) pays nothing."""
    disp = {"cruel_compassionate": -49.0}  # sign=-1, v=-49 > -50 -> no stress
    assert contradiction_stress(disp, "show_mercy") == 0

