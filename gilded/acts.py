"""Mission C1 wave 2 - player acts.

`game.acts` is the single front door for player verbs. Every verb routes
through here, mutates the sim, and immediately records a *signature* beat -
the instant acknowledgement that the player's act registered. The beat names
the act and carries the face of the person acting (the House steward).
"""

from __future__ import annotations

from gilded.beats import Beat
from gilded.society.labor import clamp_dial


class Acts:
    """`game.acts` - all player verbs, each emitting an instant signature
    beat on `game.beats.log` the moment it fires (no end_turn needed)."""

    def __init__(self, game):
        self.game = game

    def _player_house(self) -> str:
        return next((h for h in self.game.houses
                     if self.game.houses[h].is_player),
                    sorted(self.game.houses)[0])

    def _steward_name(self, house: str) -> str:
        h = self.game.houses[house]
        return getattr(h, "steward", None) or house

    def set_dial(self, eid: str, value: float) -> Beat:
        """Set an enterprise's extraction dial (wraps
        `Enterprise.extraction_dial`, clamped to 0-100) and emit the
        signature beat acknowledging the squeeze."""
        game = self.game
        ent = next(e for e in game.enterprises if e.eid == eid)
        before = ent.extraction_dial
        after = clamp_dial(value)
        ent.extraction_dial = after
        prov = game.atlas.provinces.get(ent.province)
        prov_name = prov.name if prov is not None else f"province {ent.province}"
        house = ent.house
        face = self._steward_name(house)
        beat = Beat(
            turn=game.turn,
            kind="signature",
            house=house,
            text=(f"{face} sets the {prov_name} extraction dial to "
                  f"{after:.0f} (was {before:.0f})"),
            source="acts.set_dial",
            causes=(),
            face=face,
        )
        game.beats.append(beat)
        return beat
