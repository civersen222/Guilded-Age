"""Popup — the living realm: ruler, dynasty, court, rivals, and foreign ties (Phase B5)."""

import random
from typing import Any, List, Optional

import pygame
import pygame_gui

from pygame_app.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from court import CourtPosition
from realms import _make_character
from relationships import get_relation
from simulation import modify_opinion
import marriages as marriage_mod

WIDTH = 640
HEIGHT = 600
MARGIN = 8
BUTTON_H = 30
FEAST_COST = 50
STAT_COLORS = {
    "statecraft": "#4499ff",
    "command": "#ff4444",
    "industry": "#44cc44",
    "intrigue": "#aa44ff",
    "science": "#44cccc",
    "resolve": "#ffaa44",
}


def _player_realm(game: Any):
    realms = getattr(game, "realms", None) or {}
    return realms.get(game.player_civ.name)


def _stat_line(c: Any) -> str:
    return (f"St:{c.get_effective_stat('statecraft')} Cm:{c.get_effective_stat('command')} "
            f"In:{c.get_effective_stat('industry')} Ig:{c.get_effective_stat('intrigue')} "
            f"Sc:{c.get_effective_stat('science')} Rv:{c.get_effective_stat('resolve')}")


def build_realm_html(game: Any) -> str:
    """All living-world data for the player's realm, plus foreign rulers."""
    realm = _player_realm(game)
    if not realm:
        return "<i>No realm established yet.</i>"
    parts: List[str] = []
    ruler = realm.ruler
    parts.append(f"<font size=5><b>=== {ruler.name} ===</b></font><br>")
    parts.append(f"Age: {ruler.age}<br><br><b>Stats:</b><br>")
    for stat in ["statecraft", "command", "industry", "intrigue", "science", "resolve"]:
        color = STAT_COLORS.get(stat, "#cccccc")
        parts.append(f'<font color="{color}">{stat.capitalize()}:</font> {ruler.get_effective_stat(stat)}<br>')
    parts.append("<br><b>Traits:</b> " + (", ".join(ruler.traits) if ruler.traits else "None") + "<br>")
    parts.append(f"<b>Dynasty Prestige:</b> {realm.dynasty.calculate_dynastic_prestige()}<br>")

    members = sorted(realm.dynasty.all_characters.values(), key=lambda c: (not c.is_alive, -c.age))
    parts.append(f"<br><b><u>Dynasty ({sum(1 for m in members if m.is_alive)} living)</u></b><br>")
    for m in members[:12]:
        alive = "✓" if m.is_alive else "✗"
        wed = " ⚭" if m.id in marriage_mod._married_ids else ""
        role = "Ruler" if m.id == ruler.id else "Kin"
        parts.append(f"{alive} <b>{m.name}</b>{wed} (Age {m.age}) — {role} [{_stat_line(m)}]<br>")

    parts.append(f"<br><b><u>Royal Court ({realm.court.filled_count}/5)</u></b><br>")
    for pos in CourtPosition:
        char = realm.court.positions.get(pos)
        if char and char.is_alive:
            parts.append(f"<b>{pos.value}:</b> {char.name} (+{realm.court.get_bonus(pos)})<br>")
        else:
            parts.append(f"<b>{pos.value}:</b> VACANT<br>")

    rivals = [c for c in realm.characters
              if c.is_alive and c.id != ruler.id and get_relation(c, ruler) == "rival"]
    friends = [c for c in realm.characters
               if c.is_alive and c.id != ruler.id and get_relation(c, ruler) == "friend"]
    parts.append("<br><b><u>Standing at Court</u></b><br>")
    parts.append(f'<font color="#44cc44">Friends:</font> ' + (", ".join(c.name for c in friends[:6]) or "none") + "<br>")
    parts.append(f'<font color="#ff4444">Rivals:</font> ' + (", ".join(c.name for c in rivals[:6]) or "none") + "<br>")
    brewing = sum(1 for p in game.plot_manager.plots if p.target == ruler.id)
    if brewing:
        parts.append(f'<font color="#aa44ff">Whispers at court: {brewing} plot(s) rumored against the throne...</font><br>')

    dm = game.diplomacy_manager
    pname = game.player_civ.name
    parts.append("<br><b><u>Foreign Realms</u></b><br>")
    for civ_name, r in (getattr(game, "realms", None) or {}).items():
        if civ_name == pname:
            continue
        fr = r.ruler
        rel = dm.get_relation(pname, civ_name)
        tags = []
        if dm.is_allied(pname, civ_name):
            tags.append("ALLIED")
        if dm.is_at_war(pname, civ_name):
            tags.append("AT WAR")
        if any({civ_a, civ_b} == {pname, civ_name} for _, civ_a, _, civ_b in marriage_mod._marriages):
            tags.append("⚭ blood tie")
        tag_s = (" — " + ", ".join(tags)) if tags else ""
        parts.append(f"<b>{civ_name}:</b> {fr.name} (Age {fr.age}), relation {rel:+d}{tag_s}<br>")
    return "\n".join(parts)


def host_feast(game: Any) -> str:
    """Spend gold on a feast: prestige plus goodwill from the whole realm."""
    realm = _player_realm(game)
    if not realm:
        return "No realm established yet."
    pname = game.player_civ.name
    gold = game.gold.get(pname, 0)
    if gold < FEAST_COST:
        return f"Not enough gold! Need {FEAST_COST}, have {gold}."
    game.gold[pname] -= FEAST_COST
    realm.dynasty.add_prestige(10)
    ruler = realm.ruler
    for c in realm.characters:
        if c.is_alive and c.age >= 16 and c.id != ruler.id:
            modify_opinion(c, ruler, random.randint(3, 8), "feast")
    return f"Feast hosted! -{FEAST_COST} gold, +10 prestige, the realm warms to {ruler.name}."


def appoint_courtier(game: Any) -> str:
    """Fill the first vacant court position with the best candidate."""
    realm = _player_realm(game)
    if not realm:
        return "No realm established yet."
    vacant = [pos for pos in CourtPosition
              if not (realm.court.positions.get(pos) and realm.court.positions[pos].is_alive)]
    if not vacant:
        return "All court positions are filled."
    in_court = {c.id for c in realm.court.positions.values() if c is not None}
    candidates = [c for c in realm.characters
                  if c.is_alive and c.age >= 16 and c.id != realm.ruler.id and c.id not in in_court]
    pos = vacant[0]
    if candidates:
        pick = realm.court.get_best_candidate(candidates, pos) or candidates[0]
    else:
        # Nobody free to serve — recruit new blood, as the AI realms do.
        pick = _make_character(realm.civ_name, realm.ruler.base_stats, [], 18, 35)
        realm.characters.append(pick)
        game.characters.append(pick)
    realm.court.positions[pos] = None
    realm.court.appoint(pos, pick, game.state.turn)
    return f"{pick.name} appointed as {pos.value}!"


def arrange_player_match(game: Any) -> str:
    """Marry one of the player's kin into a foreign realm."""
    realm = _player_realm(game)
    if not realm:
        return "No realm established yet."
    pname = game.player_civ.name
    realms = getattr(game, "realms", None) or {}
    dm = game.diplomacy_manager
    kin = [c for c in marriage_mod._eligible(realm) if c.id in realm.dynasty.all_characters]
    cand_a = kin or marriage_mod._eligible(realm)
    if not cand_a:
        return "No eligible kin to marry off."
    a = random.choice(cand_a)
    want = "Female" if a.gender == "Male" else "Male"
    foreign = [n for n in realms if n != pname and not dm.is_at_war(pname, n)]
    random.shuffle(foreign)
    for civ_b in foreign:
        rb = realms[civ_b]
        cand_b = marriage_mod._eligible(rb, want)
        if not cand_b:
            continue
        b = random.choice(cand_b)
        if b in rb.characters:
            rb.characters.remove(b)
        realm.characters.append(b)
        realm.dynasty.all_characters.setdefault(b.id, b)
        for pos, ch in rb.court.positions.items():
            if ch and ch.id == b.id:
                rb.court.positions[pos] = None
        modify_opinion(a, b, 40, "marriage")
        modify_opinion(b, a, 40, "marriage")
        marriage_mod._marriages.append((a.id, pname, b.id, civ_b))
        marriage_mod._married_ids.update((a.id, b.id))
        marriage_mod.wedding_count += 1
        dm.modify_relation(pname, civ_b, marriage_mod.MARRIAGE_RELATION_BONUS)
        realm.dynasty.add_prestige(5)
        return f"{a.name} weds {b.name}! +5 prestige, {civ_b} grows closer."
    return "No foreign realm has a suitable match."


class RealmPopup:
    """Popup showing the living realm; same contract as the other popups."""

    def __init__(self):
        self.window: Optional[pygame_gui.elements.UIWindow] = None
        self.info_textbox: Optional[pygame_gui.elements.UITextBox] = None
        self.status_label: Optional[pygame_gui.elements.UILabel] = None
        self.host_feast_btn: Optional[pygame_gui.elements.UIButton] = None
        self.appoint_btn: Optional[pygame_gui.elements.UIButton] = None
        self.marriage_btn: Optional[pygame_gui.elements.UIButton] = None
        self._game: Any = None

    @property
    def is_visible(self) -> bool:
        return self.window is not None and self.window.alive()

    def show(self, ui_manager: pygame_gui.UIManager, game: Any) -> None:
        self._game = game
        cx = (SCREEN_WIDTH - WIDTH) // 2
        cy = (SCREEN_HEIGHT - HEIGHT) // 2
        self.window = pygame_gui.elements.UIWindow(
            pygame.Rect(cx, cy, WIDTH, HEIGHT),
            manager=ui_manager,
            window_display_title="Realm",
        )
        content_height = HEIGHT - MARGIN * 2 - BUTTON_H * 4
        self.info_textbox = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect(MARGIN, MARGIN, WIDTH - MARGIN * 2, content_height),
            html_text=build_realm_html(game),
            manager=ui_manager,
            container=self.window,
        )
        btn_w = 150
        total_w = btn_w * 3 + MARGIN * 2
        start_x = (WIDTH - total_w) // 2
        btn_y = MARGIN + content_height + 4
        self.host_feast_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(start_x, btn_y, btn_w, BUTTON_H),
            text="Host Feast", manager=ui_manager, container=self.window)
        self.appoint_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(start_x + btn_w + MARGIN, btn_y, btn_w, BUTTON_H),
            text="Appoint to Court", manager=ui_manager, container=self.window)
        self.marriage_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(start_x + (btn_w + MARGIN) * 2, btn_y, btn_w, BUTTON_H),
            text="Arrange Marriage", manager=ui_manager, container=self.window)
        self.status_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(MARGIN, btn_y + BUTTON_H + 4, WIDTH - MARGIN * 2, BUTTON_H),
            text="", manager=ui_manager, container=self.window)

    def _refresh(self) -> None:
        if self.is_visible and self._game is not None and self.info_textbox is not None:
            self.info_textbox.set_text(build_realm_html(self._game))

    def _set_status(self, message: str) -> None:
        if self.status_label is not None:
            self.status_label.set_text(message[:90])

    def handle_event(self, event) -> bool:
        if event.type == pygame_gui.UI_BUTTON_PRESSED and self._game is not None:
            if event.ui_element == self.host_feast_btn:
                self._set_status(host_feast(self._game))
                self._refresh()
                return True
            if event.ui_element == self.appoint_btn:
                self._set_status(appoint_courtier(self._game))
                self._refresh()
                return True
            if event.ui_element == self.marriage_btn:
                self._set_status(arrange_player_match(self._game))
                self._refresh()
                return True
        return False

    def _kill(self) -> None:
        for elem in [self.info_textbox, self.status_label, self.host_feast_btn,
                     self.appoint_btn, self.marriage_btn]:
            if elem is not None:
                elem.kill()
        if self.window is not None:
            self.window.kill()
            self.window = None
