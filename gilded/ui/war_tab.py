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
                lines.append(f"  House {other_name} — truce until turn {truce_until}")
            else:
                lines.append(f"  House {other_name} — no truce")
        return lines

    lines.append("WAR & DIPLOMACY")
    lines.append("")
    for war in wars:
        side = "attacker" if war.aggressor == house_name else "defender"
        enemy = war.defender if war.aggressor == house_name else war.aggressor
        lines.append(f"War with House {enemy} (we are {side})")
        lines.append(f"  Started turn {war.started_turn} · Score: {war.war_score:+.1f}")
        for front in war.fronts:
            a_reg = front.attacker_regiments
            d_reg = front.defender_regiments
            cmd_a = front.commander_a_id or "none"
            cmd_d = front.commander_d_id or "none"
            lines.append(
                f"  Front {front.fid}: "
                f"Attackers {a_reg} regiments (cmdr: {cmd_a}) · "
                f"Defenders {d_reg} regiments (cmdr: {cmd_d}) · "
                f"Line: {front.line:+.2f}"
            )
        lines.append("")

    # Peace Houses
    at_war = set()
    for war in wars:
        enemy = war.defender if war.aggressor == house_name else war.aggressor
        at_war.add(enemy)

    peaceful = [n for n in game.houses
                if n != house_name and n not in at_war]
    if peaceful:
        lines.append("AT PEACE")
        for other_name in peaceful:
            truce_until = h.truces.get(other_name, 0)
            if truce_until > game.turn:
                lines.append(f"  House {other_name} — truce until turn {truce_until}")
            else:
                lines.append(f"  House {other_name} — no active war")

    return lines


def _war_report_lines(game, house_name: str) -> List[str]:
    """Build a report-style summary for the broadsheet."""
    lines: List[str] = []
    h = game.houses[house_name]
    wars = [w for w in getattr(game, "wars", [])
            if w.aggressor == house_name or w.defender == house_name]

    if not wars:
        lines.append(f"The {house_name} House is at peace.")
        return lines

    for war in wars:
        enemy = war.defender if war.aggressor == house_name else war.aggressor
        side = "attacker" if war.aggressor == house_name else "defender"
        total_a = sum(f.attacker_regiments for f in war.fronts)
        total_d = sum(f.defender_regiments for f in war.fronts)
        lines.append(
            f"War with House {enemy}: {house_name} is {side} · "
            f"Strength: {total_a} vs {total_d} · Score {war.war_score:+.1f}"
        )
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
    h_obj = game.houses[house_name]
    current_wars = [w for w in getattr(game, "wars", [])
                    if w.aggressor == house_name or w.defender == house_name]
    at_war_with = set()
    for war in current_wars:
        enemy = war.defender if war.aggressor == house_name else war.aggressor
        at_war_with.add(enemy)

    # List potential targets for declaring war
    targets = [n for n in game.houses
               if n != house_name and n not in at_war_with]
    if targets:
        sec_title = font_text.render("Declare War:", True, INK)
        surface.blit(sec_title, (margin_x, cur_y))
        cur_y += LINE_H + 2

        for i, target in enumerate(targets):
            btn_x = margin_x + 20
            btn_w = w - 2 * PAD - 20
            btn_y = cur_y
            truce_until = h_obj.truces.get(target, 0)
            truce_active = truce_until > game.turn
            label = f"Declare War on House {target}"
            if truce_active:
                label += f" (truce until {truce_until})"

            # Draw button
            if truce_active:
                pygame.draw.rect(surface, DISABLED_BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
                pygame.draw.rect(surface, DISABLED_BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            else:
                pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
                pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)

            btn_txt = font_text.render(label, True,
                                       BUTTON_TEXT if not truce_active else DISABLED_BUTTON_EDGE)
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

    # ── Active war controls ──────────────────────────────────────────────
    for war in current_wars:
        enemy = war.defender if war.aggressor == house_name else war.aggressor
        side = "attacker" if war.aggressor == house_name else "defender"
        cur_y += 4
        war_title = font_text.render(f"War with House {enemy} ({side}):", True, INK)
        surface.blit(war_title, (margin_x, cur_y))
        cur_y += LINE_H + 2

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

            # Commander info
            cmd_line = f"  Commanders: {cmd_a} vs {cmd_d}"
            txt = font_text.render(cmd_line, True, TONES.get("neutral", INK))
            surface.blit(txt, (margin_x + 20, cur_y))
            cur_y += LINE_H + 2

            # ── Muster button ────────────────────────────────────────────
            btn_x = margin_x + 40
            btn_w = w - 2 * PAD - 40
            btn_y = cur_y
            label = f"Muster (Front {front.fid})"
            pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, BUTTON_TEXT)
            surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
            regions.add(Region(
                rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
                action={"muster": {"war_id": war.war_score, "front_fid": front.fid}},
                state=RegionState.ENABLED,
                hint=label,
                group="war_actions",
            ))
            cur_y += BUTTON_H + 4

            # ── Commit button ────────────────────────────────────────────
            btn_y = cur_y
            label = f"Commit (Front {front.fid})"
            pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, BUTTON_TEXT)
            surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
            regions.add(Region(
                rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
                action={"commit": {"war_id": war.war_score, "front_fid": front.fid}},
                state=RegionState.ENABLED,
                hint=label,
                group="war_actions",
            ))
            cur_y += BUTTON_H + 4

            # ── Appoint Commander button ─────────────────────────────────
            btn_y = cur_y
            label = f"Appoint Commander (Front {front.fid})"
            pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
            pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
            btn_txt = font_text.render(label, True, BUTTON_TEXT)
            surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
            regions.add(Region(
                rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
                action={"appoint_commander": {"war_id": war.war_score, "front_fid": front.fid}},
                state=RegionState.ENABLED,
                hint=label,
                group="war_actions",
            ))
            cur_y += BUTTON_H + 4

        # ── Negotiate Peace button ──────────────────────────────────────
        btn_x = margin_x
        btn_w = w - 2 * PAD
        btn_y = cur_y
        label = f"Negotiate Peace with House {enemy}"
        pygame.draw.rect(surface, BUTTON_BG, (btn_x, btn_y, btn_w, BUTTON_H))
        pygame.draw.rect(surface, BUTTON_EDGE, (btn_x, btn_y, btn_w, BUTTON_H), 1)
        btn_txt = font_text.render(label, True, BUTTON_TEXT)
        surface.blit(btn_txt, (btn_x + 4, btn_y + 4))
        regions.add(Region(
            rect=pygame.Rect(btn_x, btn_y, btn_w, BUTTON_H),
            action={"negotiate_peace": enemy},
            state=RegionState.ENABLED,
            hint=label,
            group="war_actions",
        ))
        cur_y += BUTTON_H + 8
