"""Stage 6 — War tab: diplomacy and war reach the player.

Displays active wars (both Houses named together per front), peace/truce
status for Houses at peace, and interactive controls for all four war
verbs: declare war, muster, commit, appoint commander, negotiate peace.
"""

from typing import Any, Dict, List, Optional, Tuple

import pygame

from gilded.ui.widgets import (
    BUTTON_BG, BUTTON_EDGE, BUTTON_TEXT,
    DISABLED_BUTTON_BG, DISABLED_BUTTON_EDGE,
    CARD_BG,
    INK,
    font as _font,
    TYPE_TEXT,
    TYPE_TITLE,
    TONES,
    Region, RegionState,
)

PAD = 8
BUTTON_H = 28
LINE_H = 16


def _war_lines(game, house_name: str) -> List[str]:
    """Build text lines showing war status for the House."""
    lines: List[str] = []
    h = game.houses[house_name]
    wars = [w for w in getattr(game, "wars", [])
            if w.aggressor == house_name or w.defender == house_name]

    if not wars:
        lines.append("WAR & DIPLOMACY")
        lines.append("")
        lines.append(f"The {house_name} House is at peace.")
        lines.append("")
        # List other Houses and their truce status
        lines.append("OTHER HOUSES")
        for other_name in game.houses:
            if other_name == house_name:
                continue
            truce_until = h.truces.get(other_name, 0)
            if truce_until > game.turn:
                lines.append(f"  {other_name} — truce until turn {truce_until}")
            else:
                lines.append(f"  {other_name} — no truce")
        return lines

    lines.append("WAR & DIPLOMACY")
    lines.append("")
    for war in wars:
        enemy = war.defender if war.aggressor == house_name else war.aggressor
        side = "attacker" if war.aggressor == house_name else "defender"
        lines.append(f"At war with House {enemy} ({side})")
        for front in war.fronts:
            a = front.attacker_regiments
            d = front.defender_regiments
            lines.append(f"  Front {front.fid}: {a} vs {d} regiments")
    return lines


def _war_report_lines(game, house_name: str) -> List[str]:
    """Build the war report lines for the War tab."""
    lines: List[str] = []
    h = game.houses[house_name]
    wars = [w for w in getattr(game, "wars", [])
            if w.aggressor == house_name or w.defender == house_name]

    if not wars:
        lines.append("The House is at peace.")
        lines.append("")
        return lines

    for war in wars:
        enemy = war.defender if war.aggressor == house_name else war.aggressor
        side = "attacker" if war.aggressor == house_name else "defender"
        lines.append(f"War with House {enemy} ({side})")
        for front in war.fronts:
            a = front.attacker_regiments
            d = front.defender_regiments
            line_val = front.line
            lines.append(
                f"  Front {front.fid}: {a} vs {d} regiments · Line: {line_val:+.2f}"
            )
    lines.append("")
    return lines


def draw_war_tab(
    surface: pygame.Surface,
    game: Any,
    house_name: str,
    x: int, y: int, w: int, h: int,
    regions,
    font_text=None,
) -> None:
    """Draw the War tab: war report + interactive controls."""
    if font_text is None:
        font_text = _font(TYPE_TEXT)

    # Background
    surface.fill(CARD_BG, (x, y, w, h))

    cur_y = y + PAD
    margin_x = x + PAD

    # Title
    title_font = _font(TYPE_TITLE)
    title = title_font.render("War & Diplomacy", True, INK)
    surface.blit(title, (margin_x, cur_y))
    cur_y += title.get_height() + PAD

    # ── War report ────────────────────────────────────────────────────────
    report_lines = _war_report_lines(game, house_name)
    for line in report_lines:
        txt = font_text.render(line, True, INK)
        surface.blit(txt, (margin_x, cur_y))
        cur_y += LINE_H

    cur_y += 4

    # ── Declare War section ───────────────────────────────────────────────
    wars = [w for w in getattr(game, "wars", [])
            if w.aggressor == house_name or w.defender == house_name]
    other_houses = [n for n in game.houses if n != house_name]
    at_war_with = set()
    for war in wars:
        enemy = war.defender if war.aggressor == house_name else war.aggressor
        at_war_with.add(enemy)

    for target in other_houses:
        if target in at_war_with:
            continue
        btn_x = margin_x + 20
        btn_w = w - 2 * PAD - 20
        btn_y = cur_y

        # Check truce
        h = game.houses[house_name]
        truce_until = h.truces.get(target, 0)
        truce_active = truce_until > game.turn

        label = f"Declare War on House {target}"
        if truce_active:
            label += f" (truce until turn {truce_until})"

        if truce_active:
            pygame.draw.rect(surface, DISABLED_BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, DISABLED_BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, DISABLED_BUTTON_EDGE)
        else:
            pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, BUTTON_TEXT)

        surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
        if truce_active:
            reason = f"A truce with House {target} holds until turn {truce_until}"
        else:
            reason = ""
        regions.add(Region(
            rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
            action={"declare_war": target},
            state=RegionState.DISABLED if truce_active else RegionState.ENABLED,
            reason=reason,
            hint=label,
            group="war_actions",
        ))
        cur_y += BUTTON_H + 4

    # ── Marriage proposals ────────────────────────────────────────────────
    from gilded.ui.actions import ACTIONS
    diplomacy_title = font_text.render("MARRIAGE PROPOSALS", True, INK)
    surface.blit(diplomacy_title, (margin_x, cur_y))
    cur_y += LINE_H + 2
    for other_name in game.houses:
        if other_name == house_name:
            continue
        btn_x = margin_x + 20
        btn_w = w - 2 * PAD - 20
        btn_y = cur_y
        label = f"Propose Marriage to House {other_name}"
        action = {"propose_marriage": other_name}
        ok, reason = ACTIONS["propose_marriage"].eligible(game, house_name, action)
        state = RegionState.ENABLED if ok else RegionState.DISABLED
        if ok:
            pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, BUTTON_TEXT)
        else:
            pygame.draw.rect(surface, DISABLED_BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, DISABLED_BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, DISABLED_BUTTON_EDGE)
        surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
        regions.add(Region(
            rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
            action=action,
            state=state,
            reason=reason if not ok else "",
            hint=label,
            group="war_actions",
        ))
        cur_y += BUTTON_H + 4

    # ── Active war controls ───────────────────────────────────────────────
    for war_idx, war in enumerate(wars):
        enemy = war.defender if war.aggressor == house_name else war.aggressor
        side = "attacker" if war.aggressor == house_name else "defender"

        cur_y += 4
        war_title = font_text.render(f"War with House {enemy} ({side})", True, INK)
        surface.blit(war_title, (margin_x, cur_y))
        cur_y += LINE_H + 2

        # Muster button — one per war, uses first border province owned by the house
        for front in war.fronts[:1]:
            province_pid = None
            for attacker_pid, defender_pid in front.border:
                if war.aggressor == house_name:
                    province_pid = attacker_pid
                else:
                    province_pid = defender_pid
                break
            if province_pid is None:
                continue
            btn_x = margin_x + 20
            btn_w = w - 2 * PAD - 20
            btn_y = cur_y
            label = f"Muster (Front {front.fid})"
            action = {"muster": province_pid, "war_id": war_idx, "front_fid": front.fid}

            # Consult eligible
            from gilded.ui.actions import ACTIONS
            ok, reason = ACTIONS["muster"].eligible(game, house_name, action)
            state = RegionState.ENABLED if ok else RegionState.DISABLED

            if ok:
                pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
                pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
                btn_txt = font_text.render(label, True, BUTTON_TEXT)
            else:
                pygame.draw.rect(surface, DISABLED_BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
                pygame.draw.rect(surface, DISABLED_BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
                btn_txt = font_text.render(label, True, DISABLED_BUTTON_EDGE)
            surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
            regions.add(Region(
                rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
                action=action,
                state=state,
                reason=reason if not ok else "",
                hint=label,
                group="war_actions",
            ))
            cur_y += BUTTON_H + 4

        # Front details + controls
        for front in war.fronts:
            a_reg = front.attacker_regiments
            d_reg = front.defender_regiments
            cmd_a = front.commander_a_id or "none"
            cmd_d = front.commander_d_id or "none"

            front_line = (
                f"Front {front.fid}: {a_reg} vs {d_reg} regiments · "
                f"Line: {front.line:+.2f}"
            )
            txt = font_text.render(front_line, True, INK)
            surface.blit(txt, (margin_x + 20, cur_y))
            cur_y += LINE_H

            # Commit button
            btn_x = margin_x + 20
            btn_w = w - 2 * PAD - 20
            btn_y = cur_y
            label = f"Commit to Front {front.fid}"
            action = {"commit": {"war_id": war_idx, "front_fid": front.fid}}

            # Consult eligible
            from gilded.ui.actions import ACTIONS
            ok, reason = ACTIONS["commit"].eligible(game, house_name, action)
            state = RegionState.ENABLED if ok else RegionState.DISABLED

            if ok:
                pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
                pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
                btn_txt = font_text.render(label, True, BUTTON_TEXT)
            else:
                pygame.draw.rect(surface, DISABLED_BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
                pygame.draw.rect(surface, DISABLED_BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
                btn_txt = font_text.render(label, True, DISABLED_BUTTON_EDGE)
            surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
            regions.add(Region(
                rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
                action=action,
                state=state,
                reason=reason if not ok else "",
                hint=label,
                group="war_actions",
            ))
            cur_y += BUTTON_H + 4

            # Appoint commander button
            btn_x = margin_x + 20
            btn_w = w - 2 * PAD - 20
            btn_y = cur_y
            label = f"Appoint Commander (Front {front.fid})"
            action = {"appoint_commander": {"war_id": war_idx, "front_fid": front.fid, "char_id": None}}

            # Consult eligible
            ok, reason = ACTIONS["appoint_commander"].eligible(game, house_name, action)
            state = RegionState.ENABLED if ok else RegionState.DISABLED

            if ok:
                pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
                pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
                btn_txt = font_text.render(label, True, BUTTON_TEXT)
            else:
                pygame.draw.rect(surface, DISABLED_BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
                pygame.draw.rect(surface, DISABLED_BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
                btn_txt = font_text.render(label, True, DISABLED_BUTTON_EDGE)
            surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
            regions.add(Region(
                rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
                action=action,
                state=state,
                reason=reason if not ok else "",
                hint=label,
                group="war_actions",
            ))
            cur_y += BUTTON_H + 4

        # Negotiate peace button
        btn_x = margin_x + 20
        btn_w = w - 2 * PAD - 20
        btn_y = cur_y
        label = f"Negotiate Peace with House {enemy}"
        action = {"negotiate_peace": enemy}

        # Consult eligible
        ok, reason = ACTIONS["negotiate_peace"].eligible(game, house_name, action)
        state = RegionState.ENABLED if ok else RegionState.DISABLED

        if ok:
            pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, BUTTON_TEXT)
        else:
            pygame.draw.rect(surface, DISABLED_BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, DISABLED_BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, DISABLED_BUTTON_EDGE)
        surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
        regions.add(Region(
            rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
            action=action,
            state=state,
            reason=reason if not ok else "",
            hint=label,
            group="war_actions",
        ))
        cur_y += BUTTON_H + 4

        # Garrison button
        btn_x = margin_x + 20
        btn_w = w - 2 * PAD - 20
        btn_y = cur_y
        label = f"Adjust Garrison"
        action = {"adjust_garrison": True}
        ok, reason = ACTIONS["adjust_garrison"].eligible(game, house_name, action)
        state = RegionState.ENABLED if ok else RegionState.DISABLED
        if ok:
            pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, BUTTON_TEXT)
        else:
            pygame.draw.rect(surface, DISABLED_BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, DISABLED_BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, DISABLED_BUTTON_EDGE)
        surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
        regions.add(Region(
            rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
            action=action,
            state=state,
            reason=reason if not ok else "",
            hint=label,
            group="war_actions",
        ))
        cur_y += BUTTON_H + 8
