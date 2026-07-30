"""Shared number formatter for the UI layer.

This module centralises the display rules that prevent three measured defects:

  (a) 176 of 777 Council briefing lines asserted a movement then printed it as
      "0" (e.g. "Tide rose 0") because float epsilon was treated as news and
      sub-unit magnitudes were rounded to zero.

  (b) The Ledger showed outlays with a "+" prefix (e.g. "Outlay: +1,200")
      because money() signed every non-negative amount as a gain.

  (c) 23 of 223 flow rows rendered a nonzero amount as zero (e.g. "+0" for
      a trade worth 0.22 gold) because money() truncated to whole gold.

The single rule: a number the interface chose to display must not read as zero
unless it is zero. And a sign is a claim about direction, so it must be true.
"""

from __future__ import annotations

DECIMAL_BELOW = 1.0


def figure(value: float) -> str:
    """Render a MAGNITUDE (always non-negative after abs).

    * magnitude of exactly 0        -> "0"
    * magnitude >= DECIMAL_BELOW    -> rounded, comma-grouped: "1,200"
    * magnitude < DECIMAL_BELOW     -> one decimal place: "0.4"
    * so small that one decimal still reads zero -> "<0.1"
    """
    mag = abs(value)
    if mag == 0:
        return "0"
    if mag >= DECIMAL_BELOW:
        return f"{round(mag):,}"
    # Sub-unit: show one decimal place
    rounded = round(mag, 1)
    if rounded == 0:
        return "<0.1"
    return f"{rounded:.1f}"


def signed(amount: float) -> str:
    """Render a FLOW: a sign, then figure() of the magnitude.

    * amount of exactly 0 -> "0" (no sign — zero has no direction)
    * otherwise "+" or "-" followed by figure(abs(amount))
    """
    if amount == 0:
        return "0"
    sign = "+" if amount > 0 else "-"
    return f"{sign}{figure(amount)}"
