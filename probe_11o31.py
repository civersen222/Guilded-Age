"""seed-47 turn 4: full detail on every Vantrell share-holder."""
from gilded.chassis import GildedGame
import gilded.society.realm as realm_mod

g = GildedGame(seed=47)
for _ in range(4):
    g.end_turn()
r = g.realms["Vantrell"]
print("ruler:", r.ruler.name, r.ruler.id)
print("ruler children:", r.ruler.children_ids)
for ch in r.characters:
    shares = {e.name: e.ledger.get(ch.id, 0)
              for e in g.enterprises if e.house == "Vantrell"
              and ch.id in e.ledger}
    if not shares:
        continue
    loy = getattr(ch, "loyalty", None)
    opp = ch._society.opinions.get((ch.id, r.ruler.id), "NONE")
    court = any(p is ch for p in r.court.positions.values())
    dirs = {e.director_id for e in g.enterprises
            if e.house == "Vantrell"}
    print(f"{ch.name:16} {ch.id} parents={ch.parent_ids} "
          f"children={ch.children_ids} loy={loy} opp={opp} "
          f"court={court} dir={ch.id in dirs} age={ch.age} "
          f"heir={ch.is_heir} shares={shares}")

print()
print("sellers:", [s.id for s in realm_mod.disloyal_shareholders(
    r, g.enterprises)])
