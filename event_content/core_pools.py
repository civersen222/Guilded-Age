"""Core template pools (M41): prose variants per situation kind.

Every template must only use slots the wiring guarantees for its kind:
    succession:         old, new, civ
    mental_break:       subject
    plot_coup:          mastermind, target, civ
    plot_assassination: target, civ
    plot_uncovered:     target, civ
    plot_executed:      mastermind, civ
M42 grows every pool to 4+ variants.
"""

TEMPLATE_POOLS = {
    "succession": [
        "The bells toll in {civ}: {old} is dead, and {new} takes the throne",
        "{old}'s reign is over; all eyes in {civ} turn to {new}",
        "A crown changes heads in {civ} - {new} succeeds {old}",
    ],
    "mental_break": [
        "{subject} shatters under the strain; the court whispers of a new vice",
        "Something in {subject} gives way - the mask has slipped",
        "{subject} is no longer the ruler they were; the pressure has left its mark",
    ],
    "plot_coup": [
        "COUP in {civ}! {mastermind} seizes the throne from {target}",
        "Steel in the corridors of {civ}: {mastermind} topples {target}",
    ],
    "plot_assassination": [
        "{target} of {civ} has been assassinated!",
        "A cup of wine, a quiet gasp - {target} of {civ} is dead",
    ],
    "plot_uncovered": [
        "A plot against {target} was uncovered",
        "Whispers reach {target} in time - a plot is foiled",
    ],
    "plot_executed": [
        "Plot uncovered in {civ}: {mastermind} executed",
        "{mastermind} gambled against the crown of {civ} and paid with their head",
    ],
}
