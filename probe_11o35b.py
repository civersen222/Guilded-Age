"""Every takeover call over seed-7's 12 turns, full holder context."""
from gilded.chassis import GildedGame
from gilded.society.realm import disloyal_shareholders


def full(g, realm, label):
    ruler = realm.ruler
    print(f"--- {label} target={realm.house_name} ruler={ruler.name} {ruler.id}")
    for ch in realm.characters:
        shares = {e.name: e.ledger.get(ch.id, 0)
                  for e in g.enterprises if e.house == realm.house_name
                  and ch.id in e.ledger}
        if not shares:
            continue
        loy = getattr(ch, "loyalty", None)
        opp = ch._society.opinions.get((ch.id, ruler.id), "NONE")
        sibs = [c.name for c in realm.characters
                if c.id != ch.id and set(c.parent_ids) & set(ch.parent_ids)]
        print(f"  {ch.name:16} {ch.id} age={ch.age:2} loy="
              f"{('%.1f' % loy) if loy is not None else None} opp={opp} "
              f"shares={shares} child={ch.id in ruler.children_ids} sibs={sibs}")
    print(f"   sellers: {[c.name for c in disloyal_shareholders(realm, g.enterprises)]}")


g = GildedGame(seed=7)
for t in range(1, 13):
    for tk in [tk for tk in list(g.takeovers) if not tk.complete]:
        full(g, g.realms[tk.target_house],
             f"turn {t} buyer={tk.buyer_house}")
    g.end_turn()
