"""Stage 5B — House tab: the men who will betray you, with numbers.

Draws from the peerage read-model (CourtReport).  5C adds interactive
buttons for court seat appointment and dismissal.
"""

from typing import Any, List

import pygame

from gilded.peerage import CourtReport, Kin, CourtSeat, BAND_DISLOYAL, BAND_DUBIOUS

from gilded.ui.widgets import (
    BUTTON_BG, BUTTON_EDGE, BUTTON_TEXT,
    DISABLED_BUTTON_BG, DISABLED_BUTTON_EDGE,
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
            for k in report.kin:
                if k.name == seat.holder_name and k.grievances:
                    line += f"  [{', '.join(k.grievances)}]"
                    break
            rows.append(line)
    rows.append("")

    # ── Heir information ───────────────────────────────────────────────────
    if report.heir_if_ruler_died_now:
        heir_name = None
        for k in report.kin:
            if k.char_id == report.heir_if_ruler_died_now:
                heir_name = k.name
                break
        if heir_name:
            rows.append(f"Heir (if ruler dies): {heir_name}")
        else:
            rows.append(f"Heir (if ruler dies): {report.heir_if_ruler_died_now}")
    else:
        rows.append("Heir (if ruler dies): None")
    rows.append("")

    # ── Succession order ──────────────────────────────────────────────────
    rows.append("SUCCESSION")
    ranked = [(k.succession_rank, k.name, k.loyalty) for k in report.kin
              if k.is_alive and k.succession_rank is not None]
    ranked.sort()
    for rank, name, loyalty in ranked[:10]:
        loyalty_str = f"{loyalty:.0f}" if loyalty is not None else "?"
        rows.append(f"  #{rank} {name}  loyalty {loyalty_str}")
    rows.append("")

    # ── Kin — loyalty and opinion ──────────────────────────────────────────
    rows.append("KIN")
    for k in report.kin:
        if not k.is_alive:
            continue
        loyalty_str = f"{k.loyalty:.0f}" if k.loyalty is not None else "?"
        opinion_str = f"{k.opinion_of_ruler:+d}"
        # Determine loyalty band
        band_str = "DUBIOUS" if k.loyalty is not None and k.loyalty < 60 else ""
        if k.is_heir:
            band_str = "HEIR"

        # Check if seated
        seated = any(seat.holder_name == k.name for seat in report.seats if not seat.vacant)
        seated_str = "" if seated else "  (not seated)"

        grievance_str = f"  [{', '.join(k.grievances)}]" if k.grievances else ""
        shares_str = f"  shares {k.shares_pct:.1f}%" if k.shares_pct > 0 else ""
        if band_str:
            rows.append(f"  {k.name}  loyalty {loyalty_str} ({band_str}){seated_str}{grievance_str}{shares_str}")
        else:
            rows.append(f"  {k.name}  loyalty {loyalty_str}{seated_str}{grievance_str}{shares_str}")
    rows.append("")

    # ── Disloyal kin ───────────────────────────────────────────────────────
    disloyal = [k for k in report.kin if k.is_disloyal]
    if disloyal:
        rows.append("DISLOYAL KIN (loyalty < 50)")
        for k in disloyal:
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

# Position key mapping: seat position -> action key
def _position_key(seat: CourtSeat) -> str:
    """Convert seat position name to a lowercase action key."""
    return seat.position.lower().replace(" ", "_")


def _draw_button(surface: pygame.Surface, text: str, x: int, y: int,
                 btn_w: int, btn_h: int, enabled: bool) -> pygame.Rect:
    """Draw a button and return its rect."""
    if enabled:
        bg = BUTTON_BG
        edge = BUTTON_EDGE
    else:
        bg = DISABLED_BUTTON_BG
        edge = DISABLED_BUTTON_EDGE
    rect = pygame.Rect(x, y, btn_w, btn_h)
    pygame.draw.rect(surface, bg, rect)
    pygame.draw.rect(surface, edge, rect, 2)
    body = _font(TYPE_TEXT)
    surf = body.render(text, True, BUTTON_TEXT)
    surface.blit(surf, (x + 8, y + 4))
    return rect


def draw_house_tab(surface: pygame.Surface, content: pygame.Rect,
                   report: CourtReport, view: Any = None) -> None:
    """Draw the House tab on *surface* within *content* rect.

    When *view* is provided, draws interactive buttons for court seats.
    """
    PAD = 12
    title = _font(TYPE_TITLE, bold=True).render(
        f"HOUSE {report.house.upper()}", True, INK
    )
    surface.blit(title, (PAD, content.y + 6))
    y = content.y + 6 + title.get_height() + 10

    body = _font(TYPE_TEXT)
    lines = _house_tab_lines(report)

    # Reserve space for court seat buttons (6 seats + picker area)
    btn_h = body.get_height() + 8
    reserve_for_buttons = 6 * (btn_h + 2) + 40 if view is not None else 0
    text_bottom = content.bottom - reserve_for_buttons if view is not None else content.bottom

    # Draw text lines
    for line in lines:
        if y > text_bottom:
            break
        color = INK
        if line.startswith("  ?"):
            color = TONES.get("warn", INK)
        elif line.startswith("Ruler:") or line.startswith("COURT") or line.startswith("KIN") or line.startswith("DISLOYAL") or line.startswith("GRIP") or line.startswith("Heir"):
            color = TONES.get("bad", INK)
        elif "* " in line:
            color = TONES.get("good", INK)

        surface.blit(body.render(line, True, color), (PAD, y))
        y += body.get_height() + 4

    # ── Interactive court seat buttons ──────────────────────────────────────
    if view is not None:
        y += 8
        btn_w = 180

        for seat in report.seats:
            if y + btn_h > content.bottom:
                break

            pk = _position_key(seat)

            if seat.vacant:
                # Vacant seat -> "Appoint X" button
                btn_text = f"Appoint {seat.position}"
                btn_rect = _draw_button(surface, btn_text, PAD, y, btn_w, btn_h, True)
                if view is not None:
                    view._court_hits.append((btn_rect, {"open_appointment_picker": pk}))
            else:
                # Occupied seat -> "Dismiss" button
                btn_text = f"Dismiss {seat.holder_name}"
                btn_rect = _draw_button(surface, btn_text, PAD, y, btn_w, btn_h, True)
                if view is not None:
                    view._court_hits.append((btn_rect, {"dismiss_seat": pk}))

            y += btn_h + 4

        # If court picker is open, draw candidate picker
        if view is not None and getattr(view, '_court_picker', None) is not None:
            pk = view._court_picker
            pos_name = pk.replace("_", " ").title()
            y += 4
            surface.blit(body.render(f"Select appointee for {pos_name}:", True, INK), (PAD, y))
            y += body.get_height() + 4

            # Back button
            back_text = "Cancel"
            back_rect = _draw_button(surface, back_text, PAD, y, btn_w, btn_h, True)
            view._court_picker_hits.append((back_rect, {"close_appointment_picker": True}))
            y += btn_h + 4

            # Draw candidate buttons (from _court_picker_hits)
            # Candidates are populated by the caller via view._court_picker_hits


__all__ = ["draw_house_tab", "_house_tab_lines"]
