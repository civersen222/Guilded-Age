"""Dump share-holders' features for the two discriminating scenarios to find
a rule separating door-test sellers from fixture non-sellers."""
from gilded.chassis import GildedGame
from gilded.society.realm import disloyal_shareholders

DISLOYAL_LOYALTY = 40.0
DISLOYAL_OPINION = -20


def dump(label, seed, turns, target):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    realm = g.realms[target]
    ruler = realm.ruler
    members = {c.id for c in realm.dynasty.get_all_members()}
    check_ents = [e for e in g.enterprises if e.house == target]
    print(f"=== {label} seed={seed} target={target} ===")
    for ch in realm.characters:
        if not ch.is_alive or ch.id == ruler.id:
            continue
        if not any(ch.id in ent.ledger for ent in check_ents):
            continue
        opinion = ch._society.opinions.get((ch.id, ruler.id), 0)
        loyalty = getattr(ch, "loyalty", None)
        is_dyn = ch.id in members
        in_opp = (ch.id, ruler.id) in ch._society.opinions
        base = (loyalty is not None and loyalty < DISLOYAL_LOYALTY
                or opinion <= DISLOYAL_OPINION)
        unmeasured = loyalty is None and not in_opp
        print(f"  {ch.name:18s} loy={loyalty} opp={opinion:5.1f} dyn={int(is_dyn)} "
              f"in_opp={int(in_opp)} unmeas={int(unmeasured)} base={int(base)}")
    sellers = disloyal_shareholders(realm, g.enterprises)
    print(f"  >> sellers: {[s.name for s in sellers]}\n")


dump("i4c1-47", 47, 4, "Vantrell")
g = GildedGame(seed=7)
for _ in range(12):
    g.end_turn()
for name in g.realms:
    if any(t.target_house == name and not t.complete for t in g.takeovers):
        dump("door-7-target", 7, 12, name)
