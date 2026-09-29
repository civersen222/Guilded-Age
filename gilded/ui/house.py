"""Mission C2 wave 2 - the House screen: the Court in Session.

`banner(game, house)` is the ambition banner on top: family, target,
why-string, and the commit clock in the banner's own words ("turn 3 of
10"). `court_cards(game, house)` is the grid of portrait cards - one per
ADULT member, each carrying name, age, relation, traits, the stance
badge, and the one-line want citing the driving disposition. Both read
the model (game.ambitions.status / character.want) - the cards mirror it
EXACTLY, so a stance you read on a card is the stance the model carries.
"""

from __future__ import annotations

from typing import List

from gilded.chassis import GildedGame


def banner(game: GildedGame, house: str) -> dict:
    """The ambition banner's data: family (the active ambition family),
    target, why, and `clock` == "turn N of 10" at read time ("turn 1 of
    10" immediately after set_ambition, "turn 4 of 10" after three
    end_turns). All keys present even with no stake set."""
    st = game.ambitions.status(house)
    return {
        "family": st["family"],
        "target": st["target"],
        "why": st["why"],
        "clock": st["clock"],
        "turns_left": st["turns_left"],
        "progress": st["progress"],
        "fulfilled": st["fulfilled"],
    }


def court_cards(game: GildedGame, house: str) -> List[dict]:
    """The court grid: one card per ADULT member of the House (age >= 16,
    from game.realms[house].characters). Keys per card: "cid", "name",
    "age", "relation", "traits" (== character.traits), "stance" (==
    character.want["stance"]), "want_text" (== character.want["text"]),
    "disposition" (the want's driving disposition). Adults without a
    want (no active ambition) carry an empty stance/want_text."""
    realm = game.realms[house]
    by_id = {c.id: c for c in realm.characters}
    out: List[dict] = []
    for c in sorted(realm.characters, key=lambda c: c.id):
        if c.age < 16:
            continue
        want = getattr(c, "want", None) or {}
        out.append({
            "cid": c.id,
            "name": c.name,
            "age": c.age,
            "relation": _relation(realm, c, by_id),
            "traits": list(c.traits),
            "stance": want.get("stance", ""),
            "want_text": want.get("text", ""),
            "disposition": want.get("disposition", ""),
        })
    return out


def _relation(realm, character, by_id: dict) -> str:
    """The card's relation line: the ruler, or the parent/child link."""
    if realm.ruler.id == character.id:
        return "the ruler"
    parents = [p for p in (by_id.get(pid)
                            for pid in character.parent_ids) if p]
    if parents:
        return f"child of {parents[0].name}"
    children = [c.name for c in realm.characters
                if character.id in c.parent_ids]
    if children:
        return f"parent of {children[0]}"
    return "of the House"


__all__ = ["banner", "court_cards"]
