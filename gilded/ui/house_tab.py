"""Stage 5B — House tab: the men who will betray you, with numbers.

Draws from the peerage read-model (CourtReport).  Adds no verb, no button
and no simulation.  5B is read-only.
"""

from typing import List

import pygame

from gilded.peerage import CourtReport, Kin, CourtSeat, BAND_DISLOYAL, BAND_DUBIOUS

from gilded.ui.widgets import (
    INK,
    font as _font,
    TYPE_TEXT,
    TYPE_TITLE,
    TONES,
)

_BAND_COLOR: dict = {
    BAND_DISLOYAL: TONES["bad"],
    BAND_DUBIOUS: TONES["warn"],
}


# ── Line builder ────────────────────────────────────────────────────────────

def _house_tab_lines(report: CourtReport) -> List[str]:
    """Build the text lines for the House tab from a CourtReport."""
    rows: List[str] = []

    # Header
    rows.append(f"Ruler: {report.ruler_name} (age {report.ruler_age})")
    rows.append("")

    # ── Court seats — loyalty number + band ────────────────────────────────
    rows.append("COURT SEATS")
    for seat in report.seats:
        if seat.vacant:
            rows.append(f"  {seat.position}: (vacant)")
        else:
            loyalty_str = f"{seat.loyalty:.0f}" if seat.loyalty is not None else "?"
            band_str = seat.band or "?"
            line = f"  {seat.position}: {seat.holder_name}  loyalty {loyalty_str} ({band_str})"
            # Show grievances for seated men from kin data
            for kin in report.kin:
                if kin.char_id == seat.holder_id and kin.grievances:
                    line += f"  [{', '.join(kin.grievances)}]"
                    break
            rows.append(line)
    rows.append("")

    # ── Heir / succession ──────────────────────────────────────────────────
    rows.append("SUCCESSION")
    heir_id = report.heir_if_ruler_died_now
    heir_name = "?"
    if heir_id:
        # heir_if_ruler_died_now is a char_id — resolve to name (FACT 2)
        for k in report.kin:
            if k.char_id == heir_id:
                heir_name = k.name
                break
        else:
            heir_name = heir_id  # fallback: print the id if not found in kin
    rows.append(f"  First in line: {heir_name}")

    # Show succession order (only men in line, i.e. succession_rank is not None)
    in_line = [k for k in report.kin if k.succession_rank is not None and k.is_alive]
    in_line.sort(key=lambda k: k.succession_rank)
    for k in in_line[:10]:
        rank_str = f"#{k.succession_rank}"
        loyalty_str = f"{k.loyalty:.0f}"
        prefix = "  * " if k.char_id == heir_id else "    "
        line = f"{prefix}{rank_str} {k.name}  loyalty {loyalty_str}"
        if k.grievances:
            line += f"  [{', '.join(k.grievances)}]"
        rows.append(line)
    if len(in_line) > 10:
        rows.append(f"  ... and {len(in_line) - 10} more in line")
    rows.append("")

    # ── Disloyal / dubious kin (R-B: the man about to break) ───────────────
    disloyal = [k for k in report.kin if k.is_disloyal and k.is_alive]
    dubious = [k for k in report.kin
               if not k.is_disloyal and k.loyalty < 50 and k.is_alive]

    if disloyal or dubious:
        rows.append("LOYALTY RISKS")
        for k in disloyal:
            grievance_str = f"  [{', '.join(k.grievances)}]" if k.grievances else ""
            shares_str = f"  shares {k.shares_pct:.1f}%" if k.shares_pct > 0 else ""
            rows.append(f"  !! {k.name}  loyalty {k.loyalty:.0f} (DISLOYAL){grievance_str}{shares_str}")
        for k in dubious:
            grievance_str = f"  [{', '.join(k.grievances)}]" if k.grievances else ""
            shares_str = f"  shares {k.shares_pct:.1f}%" if k.shares_pct > 0 else ""
            rows.append(f"  ?  {k.name}  loyalty {k.loyalty:.0f} (DUBIOUS){grievance_str}{shares_str}")
        rows.append("")

    # ── Grip risks — shareholders with bad opinion (R-F) ──────────────────
    grip_risks = [k for k in report.kin
                  if k.shares_pct > 0 and k.opinion_of_ruler < 0 and k.is_alive]
    if grip_risks:
        rows.append("GRIP RISKS (shareholders who hate the ruler)")
        for k in grip_risks:
            rows.append(f"  {k.name}  shares {k.shares_pct:.1f}%  opinion {k.opinion_of_ruler:+d}")
        rows.append("")

    return rows


# ── Drawing ─────────────────────────────────────────────────────────────────

def draw_house_tab(surface: pygame.Surface, content: pygame.Rect, report: CourtReport) -> None:
    """Draw the House tab on *surface* within *content* rect.

    Registers NO regions (T6 / FACT 6).  Clips when content is too small
    (FACT 4).
    """
    PAD = 12
    title = _font(TYPE_TITLE, bold=True).render(
        f"HOUSE {report.house.upper()}", True, INK
    )
    surface.blit(title, (PAD, content.y + 6))
    y = content.y + 6 + title.get_height() + 10

    body = _font(TYPE_TEXT)
    lines = _house_tab_lines(report)

    for line in lines:
        if y > content.bottom - 20:
            return
        # Color lines that start with "!!" or "? " in the loyalty risks section
        color = INK
        if line.startswith("  !!"):
            color = TONES.get("bad", INK)
        elif line.startswith("  ?"):
            color = TONES.get("warn", INK)
        elif "* " in line:
            color = TONES.get("good", INK)

        surface.blit(body.render(line, True, color), (PAD, y))
        y += body.get_height() + 4


__all__ = ["draw_house_tab", "_house_tab_lines"]
