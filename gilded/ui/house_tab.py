"""Stage 5B — House tab: the men who will betray you, with numbers.

Draws from the peerage read-model (CourtReport).  5C adds interactive
buttons for court seat appointment and dismissal, registered as proper
Regions in the view's RegionSet.
"""

from typing import Any, List, Optional

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
    Region, RegionState,
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
    ranked = [(k.succession_rank, k.name, k.loyalty, k.opinion_of_ruler) for k in report.kin
              if k.is_alive and k.succession_rank is not None]
    ranked.sort()
    for rank, name, loyalty, opinion in ranked[:10]:
        loyalty_str = f"{loyalty:.0f}" if loyalty is not None else "?"
        opinion_str = f"{opinion:+d}"
        rows.append(f"  #{rank} {name}  loyalty {loyalty_str} opinion {opinion_str}")
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
            rows.append(f"  {k.name}  loyalty {loyalty_str} opinion {opinion_str} ({band_str}){seated_str}{grievance_str}{shares_str}")
        else:
            rows.append(f"  {k.name}  loyalty {loyalty_str} opinion {opinion_str}{seated_str}{grievance_str}{shares_str}")
    rows.append("")

    # ── Disloyal kin ───────────────────────────────────────────────────────
    disloyal = [k for k in report.kin if k.is_disloyal]
    if disloyal:
        rows.append("DISLOYAL KIN (loyalty < 50)")
        for k in disloyal:
            grievance_str = f"  [{', '.join(k.grievances)}]" if k.grievances else ""
            rows.append(f"  {k.name}  loyalty {k.loyalty:.0f}{grievance_str}")
        rows.append("")

    # ── Grip risks ─────────────────────────────────────────────────────────
    grip_risks = [k for k in report.kin if k.shares_pct > 0 and k.opinion_of_ruler < -30 and k.is_alive]
    if grip_risks:
        rows.append("GRIP RISKS (shareholders who hate the ruler)")
        for k in grip_risks:
            rows.append(f"  {k.name}  shares {k.shares_pct:.1f}%  opinion {k.opinion_of_ruler:+d}")
        rows.append("")

    return rows


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def _seat_action_label(seat: CourtSeat) -> str:
    """Return the hint text for a seat control."""
    if seat.vacant:
        return f"Appoint a {seat.position.lower()}"
    return f"Dismiss {seat.holder_name} from {seat.position.lower()}"


def _seat_action_key(seat: CourtSeat) -> str:
    """Return the action key for a seat control."""
    if seat.vacant:
        return "open_appointment_picker"
    return "dismiss_seat"


def _seat_action_payload(seat: CourtSeat) -> dict:
    """Return the action dict for a seat control."""
    pk = _position_key(seat)
    key = _seat_action_key(seat)
    return {key: pk}


def _dismissal_reason(game: Any, house: str, seat: CourtSeat) -> Optional[str]:
    """Return a refusal reason if dismissing this seat is not allowed, else None."""
    from gilded.ui.court_actions import _dismiss_seat_eligible
    pk = _position_key(seat)
    action = {"dismiss_seat": pk}
    ok, reason = _dismiss_seat_eligible(game, house, action)
    return reason if not ok else None


def _appointment_reason(game: Any, house: str, seat: CourtSeat) -> Optional[str]:
    """Return a refusal reason if appointing to this seat is not allowed, else None."""
    from gilded.ui.court_actions import _open_appointment_picker_eligible
    pk = _position_key(seat)
    action = {"open_appointment_picker": pk}
    ok, reason = _open_appointment_picker_eligible(game, house, action)
    return reason if not ok else None


def draw_house_tab(surface: pygame.Surface, content: pygame.Rect,
                   report: CourtReport, view: Any = None) -> None:
    """Draw the House tab on *surface* within *content* rect.

    When *view* is provided, draws interactive Region controls for court seats
    at the top of the tab, so the text content follows below.
    """
    PAD = 12
    title = _font(TYPE_TITLE, bold=True).render(
        f"HOUSE {report.house.upper()}", True, INK
    )
    surface.blit(title, (PAD, content.y + 6))
    y = content.y + 6 + title.get_height() + 10

    body = _font(TYPE_TEXT)
    lines = _house_tab_lines(report)

    # Draw seat controls at the top (when view is provided)
    btn_h = body.get_height() + 8
    btn_w = 180

    if view is not None:
        game = getattr(view, 'game', None)
        house = getattr(view, 'house', None)

        # Draw 6 seat buttons in a 3x2 grid at the top
        cols = 3
        col_w = (content.width - PAD * 2) // cols
        for idx, seat in enumerate(report.seats):
            col = idx % cols
            row = idx // cols
            btn_x = PAD + col * col_w
            btn_y = y + row * (btn_h + 2)

            pk = _position_key(seat)

            # Determine eligibility
            refusal = None
            if not seat.vacant and game is not None and house is not None:
                refusal = _dismissal_reason(game, house, seat)
            elif seat.vacant and game is not None and house is not None:
                refusal = _appointment_reason(game, house, seat)

            if seat.vacant:
                btn_text = f"Appoint {seat.position}"
            else:
                btn_text = f"Dismiss {seat.holder_name}"

            btn_rect = _draw_button(surface, btn_text, btn_x, btn_y, col_w - 4, btn_h, refusal is None)
            hint = _seat_action_label(seat)

            if refusal:
                action = _seat_action_payload(seat)
                view.regions.add(Region(
                    rect=btn_rect,
                    action=action,
                    state=RegionState.DISABLED,
                    reason=refusal,
                    hint=hint,
                    group="court_seats",
                ))
            else:
                action = _seat_action_payload(seat)
                view.regions.add(Region(
                    rect=btn_rect,
                    action=action,
                    hint=hint,
                    group="court_seats",
                ))

        y += 2 * (btn_h + 2) + 8

    # Draw text lines
    for line in lines:
        if y > content.bottom:
            break
        color = INK
        if line.startswith("  ?"):
            color = TONES.get("warn", INK)
        elif line.startswith("Ruler:") or line.startswith("COURT") or line.startswith("KIN") or line.startswith("DISLOYAL") or line.startswith("GRIP") or line.startswith("Heir"):
            color = TONES.get("bad", INK)
        elif "* " in line:
            color = TONES.get("good", INK)

        surface.blit(body.render(line, True, color), (PAD, y))
        y += body.get_height() + 2


__all__ = ["draw_house_tab", "_house_tab_lines"]
