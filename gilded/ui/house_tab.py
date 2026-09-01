"""Stage 5B — House tab: the men who will betray you, with numbers.

Draws from the peerage read-model (CourtReport).  5C adds interactive
buttons for court seat appointment and dismissal, registered as proper
Regions in the view's RegionSet.
"""

import math
from typing import Any, List, Optional

import pygame

from gilded.peerage import CourtReport, Kin, CourtSeat, BAND_DISLOYAL, BAND_DUBIOUS

from gilded.ui.widgets import (
    BUTTON_BG, BUTTON_EDGE, BUTTON_TEXT,
    DISABLED_BUTTON_BG, DISABLED_BUTTON_EDGE,
    INK,
    font as _font,
    TYPE_CAPTION,
    TYPE_TEXT,
    TYPE_TITLE,
    TONES,
    Region, RegionState,
    blit_text,
    wrap as _wrap,
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

    # ── Heir designation ───────────────────────────────────────────────────
    if report.heir_designated:
        rows.append(f"Designated Heir: {report.heir_designated}")
    else:
        rows.append("Designated Heir: None")
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
    blit_text(surface, body, text, (x + 8, y + 4), BUTTON_TEXT)
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


def _heir_picker_reason(game, house):
    """Return a refusal reason if opening the heir picker is not allowed, else None."""
    from gilded.ui.court_actions import _open_heir_picker_eligible
    ok, reason = _open_heir_picker_eligible(game, house, {})
    return reason if not ok else None


def _clear_heir_reason(game, house, report):
    """Return a refusal reason if clearing heir is not allowed, else None."""
    from gilded.ui.court_actions import _clear_heir_eligible
    ok, reason = _clear_heir_eligible(game, house, {"clear_heir": True})
    return reason if not ok else None


def _draw_heir_controls(surface, content, y, report, view, body, btn_h, btn_w, PAD):
    """Draw the heir designation and clearing controls."""
    game = getattr(view, 'game', None)
    house = getattr(view, 'house', None)

    if game is None or house is None:
        return y

    # If heir picker is open, draw the picker instead of controls
    if getattr(view, '_heir_picker', None):
        return _draw_heir_picker(surface, content, y, report, view, body, btn_h, btn_w, PAD)

    # "Designate Heir" button
    refuse_designate = _heir_picker_reason(game, house)
    btn_text = "Designate Heir"
    btn_rect = _draw_button(surface, btn_text, PAD, y, btn_w, btn_h, refuse_designate is None)

    if refuse_designate:
        view.regions.add(Region(
            rect=btn_rect,
            action={"open_heir_picker": True},
            state=RegionState.DISABLED,
            reason=refuse_designate,
            hint=refuse_designate,
            group="heir_controls",
        ))
    else:
        view.regions.add(Region(
            rect=btn_rect,
            action={"open_heir_picker": True},
            hint="Open heir designation picker",
            group="heir_controls",
        ))

    y += btn_h + 4

    # "Clear Heir" button
    refuse_clear = _clear_heir_reason(game, house, report)
    btn_text = "Clear Heir"
    btn_rect = _draw_button(surface, btn_text, PAD, y, btn_w, btn_h, refuse_clear is None)

    if refuse_clear:
        view.regions.add(Region(
            rect=btn_rect,
            action={"clear_heir": True},
            state=RegionState.DISABLED,
            reason=refuse_clear,
            hint=refuse_clear,
            group="heir_controls",
        ))
    else:
        view.regions.add(Region(
            rect=btn_rect,
            action={"clear_heir": True},
            hint="Clear the designated heir",
            group="heir_controls",
        ))

    y += btn_h + 4
    return y


def _draw_heir_picker(surface, content, y, report, view, body, btn_h, btn_w, PAD):
    """Draw the heir picker with candidates in succession order."""
    game = getattr(view, 'game', None)
    house = getattr(view, 'house', None)

    if game is None or house is None:
        return y

    realm = game.realms[house]

    # Build succession line (excluding ruler)
    from gilded.society.succession import succession_order
    order = succession_order(realm)
    ruler_id = realm.ruler.id
    candidates = [c for c in order if c.id != ruler_id]

    # Title
    blit_text(surface, body, "Select Heir:", (PAD, y), INK)
    y += body.get_height() + 6

    # Cancel button
    from gilded.ui.widgets import INK as _INK
    cancel_rect = _draw_button(surface, "Cancel", PAD, y, btn_w, btn_h, True)
    view.regions.add(Region(
        rect=cancel_rect,
        action={"close_heir_picker": True},
        hint="Cancel — spends nothing",
        group="heir_picker",
    ))
    y += btn_h + 6

    # Candidate buttons — in succession order
    from gilded.peerage import _get_loyalty
    from gilded.ui.court_actions import _designate_heir_eligible
    for candidate in candidates:
        if y + btn_h > content.bottom:
            break
        loyalty = _get_loyalty(candidate)
        opinion = candidate._society.opinions.get((candidate.id, ruler_id), 0) if ruler_id else 0
        loyalty_str = f"{loyalty:.0f}"
        opinion_str = f"{opinion:+d}"
        row_text = f"{candidate.name}  loyalty {loyalty_str}  opinion {opinion_str}"

        needed_w = body.size(row_text)[0] + 24
        row_w = max(btn_w, needed_w)
        ok, reason = _designate_heir_eligible(game, house, {
            "char_id": candidate.id
        })
        btn_rect = _draw_button(surface, row_text, PAD, y, row_w, btn_h, ok)
        if ok:
            view.regions.add(Region(
                rect=btn_rect,
                action={"designate_heir": True, "char_id": candidate.id},
                hint=row_text,
                group="heir_picker",
            ))
        else:
            view.regions.add(Region(
                rect=btn_rect,
                action={"designate_heir": True, "char_id": candidate.id},
                state=RegionState.DISABLED,
                reason=reason,
                hint=row_text,
                group="heir_picker",
            ))
        y += btn_h + 2

    return y


def draw_house_tab(surface: pygame.Surface, content: pygame.Rect,
                   report: CourtReport, view: Any = None) -> int:
    """Draw the House tab on *surface* within *content* rect.

    When *view* is provided, draws interactive Region controls for court seats
    at the top of the tab, so the text content follows below.

    Returns the y position after the last drawn line so callers can chain
    their sections below without overlapping.
    """
    PAD = 12
    title = blit_text(
        surface, _font(TYPE_TITLE, bold=True),
        f"HOUSE {report.house.upper()}", (PAD, content.y + 6), INK
    )
    y = title.bottom + 1

    body = _font(TYPE_TEXT)
    lines = _house_tab_lines(report)

    # Draw seat controls at the top (when view is provided)
    # The heir controls + heir picker keep their committed shared row height
    # (get_height()+8); the court-seats table gets its OWN compressed height so
    # it can shrink without disturbing the picker's measured 8-rows-per-480px.
    btn_h = body.get_height() + 8
    seat_h = body.get_height() + 4
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
            btn_y = y + row * (seat_h + 2)

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

            btn_rect = _draw_button(surface, btn_text, btn_x, btn_y, col_w - 4, seat_h, refusal is None)
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

        # Advance by the SHARED btn_h pitch (not the thinner seat_h) so the
        # heir controls / heir picker start at exactly the committed y and
        # keep their measured row budget — the seats table compresses its own
        # buttons without shifting the shared controls below it.
        y += math.ceil(len(report.seats) / cols) * (btn_h + 2) + 8
        y = _draw_heir_controls(surface, content, y, report, view, body, btn_h, btn_w, PAD)
        if y > content.bottom - 40:
            return y

     # Compressed dossier: 8 columns x 10 rows at the smallest NAMED scale
    # step (TYPE_CAPTION=12). Each line is wrapped to its column width so
    # no drawn row ever spills into the adjacent column's x-span. Lines
    # that overflow the grid are moved to the right margin (still drawn
    # through blit_text, so text_rows stays complete).
    cols = 8
    per = 10
    small = _font(TYPE_CAPTION)
    col_w = (content.width - PAD * 2) // cols
    non_blank = [l for l in lines if l.strip()]
    line_h = small.get_height()
    cursors = [y] * cols
    cap = content.bottom - 40
    for i, line in enumerate(non_blank):
        c = i // per
        if c >= cols:
            break
        if cursors[c] > cap:
            break
        color = INK
        if line.startswith("  ?") or line.startswith("Ruler:") or line.startswith("COURT") or line.startswith("KIN") or line.startswith("DISLOYAL") or line.startswith("GRIP") or line.startswith("Heir"):
            color = TONES.get("bad", INK)
        elif "* " in line:
            color = TONES.get("good", INK)
        elif line.startswith("  "):
            color = TONES.get("warn", INK)
        x = PAD + c * col_w
        for seg in _wrap(line, small, col_w - 4):
            if cursors[c] > cap:
                break
            blit_text(surface, small, seg, (x, cursors[c]), color)
            cursors[c] += line_h + 2
    overflow_start = cols * per
    if len(non_blank) > overflow_start:
        ox = PAD + cols * col_w + 6
        oy = y
        for line in non_blank[overflow_start:]:
            color = INK
            if line.startswith("  ?") or line.startswith("Ruler:") or line.startswith("COURT") or line.startswith("KIN") or line.startswith("DISLOYAL") or line.startswith("GRIP") or line.startswith("Heir"):
                color = TONES.get("bad", INK)
            elif "* " in line:
                color = TONES.get("good", INK)
            elif line.startswith("  "):
                color = TONES.get("warn", INK)
            blit_text(surface, small, line, (ox, oy), color)
            oy += line_h + 2
        y = max(max(cursors), oy) + 2
    else:
        y = max(cursors) + 2
    return y


__all__ = ["draw_house_tab", "_house_tab_lines"]
