"""Core template pools: prose variants per situation kind.

Every template must only use slots the wiring guarantees for its kind:
    succession:         old, new, civ
    mental_break:       subject
    plot_coup:          mastermind, target, civ
    plot_assassination: target, civ
    plot_uncovered:     target, civ
    plot_executed:      mastermind, civ
    focus_milestone:    subject, focus, attr
    industrial_accident: city, house
    cover_up:           ruler, city
Content pack 1 (M42): every pool has 4+ variants.
"""

TEMPLATE_POOLS = {
    "succession": [
        "The bells toll in {civ}: {old} is dead, and {new} takes the throne",
        "{old}'s reign is over; all eyes in {civ} turn to {new}",
        "A crown changes heads in {civ} - {new} succeeds {old}",
        "{new} kneels before the court of {civ} and rises a sovereign; {old} belongs to history now",
        "The banners of {civ} fly at half-mast for {old} - and by nightfall they fly for {new}",
    ],
    "mental_break": [
        "{subject} shatters under the strain; the court whispers of a new vice",
        "Something in {subject} gives way - the mask has slipped",
        "{subject} is no longer the ruler they were; the pressure has left its mark",
        "Behind closed doors, {subject} has stopped pretending to cope",
        "The physicians are discreet, but the servants talk: {subject} has changed",
    ],
    "plot_coup": [
        "COUP in {civ}! {mastermind} seizes the throne from {target}",
        "Steel in the corridors of {civ}: {mastermind} topples {target}",
        "{target} wakes to find the palace guard answers to {mastermind} now",
        "The council of {civ} convenes at dawn - and acclaims {mastermind} while {target} is still in chains",
    ],
    "plot_assassination": [
        "{target} of {civ} has been assassinated!",
        "A cup of wine, a quiet gasp - {target} of {civ} is dead",
        "{target} never saw the blade; {civ} mourns and wonders who paid for it",
        "The candles in {target}'s chamber burned all night; by morning {civ} had no ruler",
    ],
    "plot_uncovered": [
        "A plot against {target} was uncovered",
        "Whispers reach {target} in time - a plot is foiled",
        "{target}'s spymaster earns their keep: a conspiracy dies in the dark",
        "Letters intercepted, doors kicked in - the plot against {target} collapses",
    ],
    "plot_executed": [
        "Plot uncovered in {civ}: {mastermind} executed",
        "{mastermind} gambled against the crown of {civ} and paid with their head",
        "The headsman of {civ} works at dawn; {mastermind}'s conspiracy ends on the block",
        "{mastermind} is dragged before the throne of {civ} - the sentence is death",
    ],
    "focus_milestone": [
        "{subject}'s devotion to {focus} bears fruit - their {attr} sharpens",
        "Years on {focus} leave their mark: {subject} grows in {attr}",
        "{subject} reaches a new plateau on {focus}; the {attr} gains are plain to see",
        "The long hours tell: {subject}'s {attr} climbs another rung on {focus}",
    ],
    "industrial_accident": [
        "Disaster at the {city} works: the machinery of {house} does not stop for the dead",
        "A boiler bursts in {city}; {house} counts the cost in silver, the workers in coffins",
        "Black smoke over {city} - another 'regrettable incident' at the {house} works",
        "The whistle at {city} blows early: an accident on the floor, and {house} ledgers a loss",
    ],
    "cover_up": [
        "{ruler} signs the order: the {city} incident never happened",
        "Ink dries on {ruler}'s desk - the {city} inquest is quietly dissolved",
        "{ruler} buys every column inch in the capital; {city} buries its dead unmentioned",
        "The {city} witnesses recant one by one; {ruler}'s meaning is understood",
    ],
}
