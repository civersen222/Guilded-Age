"""Mirror the door test: 12 turns, seed 7. Each turn, for each live
takeover target, list every share-holding character in that realm with
measurement state, and the seller set under the ORIGINAL rule
(measured-loyalty OR measured-opinion only)."""
from gilded.chassis import GildedGame
import gilded.society.realm as realm_mod

DISLOYAL_LOYALTY = realm_mod.DISLOYAL_LOYALTY
DISLOYAL_OPINION = realm_mod.DISLOYAL_OPINION


def orig_sellers(realm, ents):
    """Original rule without the unmeasured clause."""
    check = [e for e in ents if e.house == realm.house_name]
    out = []
    for ch in realm.characters:
        if not ch.is_alive or ch.id == realm.ruler.id:
            continue
        if not any(ch.id in ent.ledger for ent in check):
            continue
        opinion = ch._society.opinions.get((ch.id, realm.ruler.id), 0)
        loyalty = getattr(ch, "loyalty", None)
        if (loyalty is not None and loyalty < DISLOYAL_LOYALTY
                or opinion <= DISLOYAL_OPINION):
            out.append(ch)
    return out


def state(ch, ruler, realm, ents):
    loy = getattr(ch, "loyalty", None)
    opp = ch._society.opinions.get((ch.id, ruler.id), "NONE")
    court = any(p is ch for p in realm.court.positions.values())
    dirs = {e.director_id for e in ents if e.house == realm.house_name}
    kin = ch.id in realm.ruler.children_ids or any(
        ch.id in c.parent_ids for c in realm.characters)
    shares = {e.name: e.ledger.get(ch.id, 0) for e in ents
              if e.house == realm.house_name and ch.id in e.ledger}
    return (f"loy={loy} opp={opp} court={court} dir={ch.id in dirs} "
            f"kin={kin} shares={shares}")


g = GildedGame(seed=7)
for turn in range(12):
    targets = {tk.target_house for tk in g.takeovers if not tk.complete}
    if targets:
        print(f"--- turn {turn} targets={targets}")
        for hname in targets:
            r = g.realms[hname]
            for ch in r.characters:
                if not ch.is_alive or ch.id == r.ruler.id:
                    continue
                if not any(ch.id in e.ledger for e in g.enterprises
                           if e.house == hname):
                    continue
                print(f"   {hname} {ch.name:16} {state(ch, r.ruler, r, g.enterprises)}")
        print(f"   orig-rule sellers: {[s.name for s in orig_sellers(g.realms[list(targets)[0]], g.enterprises)]}")
    g.end_turn()

spent = -sum(amt for h in g.houses.values()
             for (_t, l, amt) in h.journal if l == "share purchase")
print(f"total share-purchase debits: {spent:.1f}")
