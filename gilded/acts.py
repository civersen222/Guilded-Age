"""Mission C1 wave 2 - player acts.

`game.acts` is the single front door for player verbs. Every verb routes
through here, mutates the sim, and immediately records a *signature* beat -
the instant acknowledgement that the player's act registered. The beat names
the act and carries the face of the person acting (the House steward).
"""

from __future__ import annotations

from typing import Optional

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

    def set_ambition(self, family: str, target: Optional[str] = None) -> Beat:
        """Record the player House's stake (wraps
        `game.ambitions.set_ambition`) and return the instant signature
        beat acknowledging the stake."""
        game = self.game
        house = self._player_house()
        game.ambitions.set_ambition(house, family, target)
        return game.beats.log[-1]

    def hold_seat(self, house: str, order_name: str) -> Beat:
        """Take the Order's seat (wraps `game.order_seats`). The Order's
        honest lever then plays in the House's favour through the world."""
        game = self.game
        face = self._steward_name(house)
        beat = Beat(
            turn=game.turn,
            kind="signature",
            house=house,
            text=f"{face} takes the {order_name} seat - the Order listens now",
            source="acts.hold_seat",
            causes=(),
            face=face,
        )
        game.beats.append(beat)
        return beat

    def informant_on_order(self, house: str, order_name: str) -> Beat:
        """Plant an informant on an Order (wraps `game.informants`)."""
        game = self.game
        face = self._steward_name(house)
        game.informants.add((house, order_name))
        beat = Beat(
            turn=game.turn,
            kind="signature",
            house=house,
            text=f"{face} plants an informant within the {order_name}",
            source="acts.informant_on_order",
            causes=(),
            face=face,
        )
        game.beats.append(beat)
        return beat

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
