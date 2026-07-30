"""The Morning Papers (mission G14): the game's face is a broadsheet.

compose() reads the chassis event log - the record of the last resolved
turn - through one House's eyes: the gazette carries everyone's public
news, the ledger and letters only what belongs to the reading House. A
seated Master of the Press with real cunning slants the record: the
House's own scandals arrive pre-doubted. format_broadsheet() sets the
report in plain text for the console and the tests alike."""

import textwrap
from dataclasses import dataclass
from typing import List

from gilded.society.court import CourtPosition
from gilded.chassis import year_of

PRESS_SLANT_INTRIGUE = 12         # the Master of the Press starts earning it here
SLANT_PREFIX = "It is rumoured, no doubt falsely, that "
SCANDAL_MARKERS = ("Scandal", "scandal", "EXPOSED")
WRAP_WIDTH = 72
MASTHEAD = "THE CONTINENTAL GAZETTE"
SECTIONS = (
    ("THE GAZETTE", "gazette", "A quiet morning on the continent."),
    ("THE LEDGER", "ledger", "No business worth the ink."),
    ("LETTERS", "letters", "The silver tray stands empty."),
)


@dataclass
class TurnReport:
    turn: int
    year: int
    gazette: List[str]            # world news, all houses' public events
    ledger: List[str]             # this house's business
    letters: List[str]            # this house's private matters


def _press_slants(game, house_name: str) -> bool:
    """True when the reading House's press office is sharp enough to spin."""
    realm = game.realms.get(house_name)
    if realm is None:
        return False
    press = realm.court.positions.get(CourtPosition.MASTER_OF_PRESS)
    return (press is not None and press.is_alive
            and press.get_effective_stat("intrigue") >= PRESS_SLANT_INTRIGUE)


def _is_scandal(text: str) -> bool:
    return any(marker in text for marker in SCANDAL_MARKERS)


def compose(game, house_name: str) -> TurnReport:
    """One House's morning paper, from the chassis event log."""
    slant = _press_slants(game, house_name)
    gazette: List[str] = []
    ledger: List[str] = []
    letters: List[str] = []
    dividends = 0.0
    for e in game.events:
        if e.register == "gazette":
            text = e.text
            if slant and e.house == house_name and _is_scandal(text):
                text = SLANT_PREFIX + text[:1].lower() + text[1:]
            gazette.append(text)
        elif e.register == "ledger" and e.house == house_name:
            ledger.append(e.text)
            if e.text.startswith("Dividends: "):
                try:
                    dividends += float(e.text.split()[1])
                except ValueError:
                    pass
        elif e.register == "letters" and e.house == house_name:
            letters.append(e.text)
    house = game.houses[house_name]
    strikes = sum(1 for p in game.provinces_of(house_name)
                  if getattr(p, "movement", None) is not None
                  and p.movement.state == "striking")
    ledger.append(f"Standing: treasury {house.treasury:.0f} gold; "
                  f"dividends {dividends:.0f}; "
                  f"{len(game.ents_of(house_name))} enterprises; "
                  f"{strikes} strikes active")
    return TurnReport(game.turn, year_of(game.turn), gazette, ledger, letters)


def format_broadsheet(report: TurnReport) -> str:
    """Set the report in type: masthead, ruled sections, wrapped columns."""
    rule = "=" * WRAP_WIDTH
    lines = [rule, f"{MASTHEAD} — {report.year}".center(WRAP_WIDTH), rule]
    for header, attr, empty_line in SECTIONS:
        lines.append("")
        lines.append(header)
        lines.append("-" * len(header))
        items = getattr(report, attr) or [empty_line]
        for item in items:
            lines.extend(textwrap.wrap(item, WRAP_WIDTH,
                                       subsequent_indent="   ") or [""])
    return "\n".join(lines)